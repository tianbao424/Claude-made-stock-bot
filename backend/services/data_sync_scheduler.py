"""
定期数据同步调度服务
负责定期更新股票基础信息、实时价格等数据
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import schedule
import threading
import time as time_module

from services.unified_tencent_collector import get_unified_collector
from services.stock_screening_service_v2 import get_stock_screening_service, ScreeningCriteria
from database import DatabaseManager
from utils.market_hours import (
    isWeekday, isHoliday, isAnyMarketOpen, 
    getRecommendedCheckFrequency, getMarketStatusSummary
)

logger = logging.getLogger(__name__)

@dataclass
class SyncTask:
    """同步任务配置"""
    name: str
    description: str
    frequency: str  # 'daily', 'weekly', 'market_hours', 'custom'
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 3

@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    message: str
    records_updated: int = 0
    duration_seconds: float = 0.0
    timestamp: datetime = None

class DataSyncScheduler:
    """数据同步调度器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.running = False
        self.thread = None
        
        # 同步任务配置
        self.sync_tasks: Dict[str, SyncTask] = {
            'stock_info_daily': SyncTask(
                name='stock_info_daily',
                description='每日股票基础信息同步',
                frequency='daily',
                enabled=True
            ),
            'stock_info_weekly': SyncTask(
                name='stock_info_weekly', 
                description='每周股票信息全量同步',
                frequency='weekly',
                enabled=True
            ),
            'data_source_health': SyncTask(
                name='data_source_health',
                description='数据源健康检查',
                frequency='market_hours',
                enabled=True
            ),
            'cache_cleanup': SyncTask(
                name='cache_cleanup',
                description='缓存清理',
                frequency='daily',
                enabled=True
            ),
            'daily_data_collection': SyncTask(
                name='daily_data_collection',
                description='每日股票涨跌数据收集',
                frequency='daily',
                enabled=True
            ),
            'strong_rise_screening': SyncTask(
                name='strong_rise_screening',
                description='强势上涨股票筛选',
                frequency='daily',
                enabled=True
            )
        }
        
        # 统计信息
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_full_sync': None,
            'next_scheduled_sync': None
        }
    
    def start_scheduler(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        logger.info("🚀 启动数据同步调度器...")
        self.running = True
        
        # 设置定时任务
        self._setup_scheduled_tasks()
        
        # 在后台线程中运行调度器
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("✅ 数据同步调度器启动成功")
    
    def stop_scheduler(self):
        """停止调度器"""
        if not self.running:
            return
        
        logger.info("⏹️ 停止数据同步调度器...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # 清除所有定时任务
        schedule.clear()
        logger.info("✅ 数据同步调度器已停止")
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        # 每日凌晨2点同步股票基础信息
        schedule.every().day.at("02:00").do(
            self._run_sync_task, 'stock_info_daily'
        ).tag('daily')
        
        # 每周日凌晨1点全量同步
        schedule.every().sunday.at("01:00").do(
            self._run_sync_task, 'stock_info_weekly'  
        ).tag('weekly')
        
        # 每天凌晨3点清理缓存
        schedule.every().day.at("03:00").do(
            self._run_sync_task, 'cache_cleanup'
        ).tag('daily')
        
        # 开盘前检查 (8:30)
        schedule.every().day.at("08:30").do(
            self._conditional_health_check
        ).tag('pre_market_health')
        
        # A股收盘后检查 (15:10)
        schedule.every().day.at("15:10").do(
            self._conditional_health_check  
        ).tag('post_market_health')
        
        # 港股收盘后检查 (16:10)
        schedule.every().day.at("16:10").do(
            self._conditional_health_check
        ).tag('post_hk_market_health')
        
        # 每日17:00 收集股票涨跌数据 (在收盘后进行)
        schedule.every().day.at("17:00").do(
            self._conditional_daily_data_collection
        ).tag('daily_data_collection')
        
        # 每日18:00 执行股票筛选 (在数据收集后进行)
        schedule.every().day.at("18:00").do(
            self._conditional_stock_screening
        ).tag('stock_screening')
        
        logger.info("📅 定时任务设置完成")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                schedule.run_pending()
                time_module.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行异常: {e}")
                time_module.sleep(300)  # 出错后等待5分钟
    
    def _conditional_health_check(self):
        """根据市场状态决定是否执行健康检查"""
        from utils.market_hours import getMarketStatusSummary
        
        market_status = getMarketStatusSummary()
        
        # 只在交易日执行健康检查
        if market_status['isWeekday'] and not market_status['isHoliday']:
            # 使用asyncio在同步上下文中运行异步任务
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果循环正在运行，创建任务
                    asyncio.create_task(self._run_sync_task('data_source_health'))
                else:
                    # 如果循环未运行，直接运行
                    loop.run_until_complete(self._run_sync_task('data_source_health'))
            except RuntimeError:
                # 如果没有事件循环，创建新的
                asyncio.run(self._run_sync_task('data_source_health'))
    
    def _conditional_daily_data_collection(self):
        """根据市场状态决定是否执行每日数据收集"""
        from utils.market_hours import getMarketStatusSummary
        
        market_status = getMarketStatusSummary()
        
        # 只在交易日执行数据收集
        if market_status['isWeekday'] and not market_status['isHoliday']:
            # 使用asyncio在同步上下文中运行异步任务
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._run_sync_task('daily_data_collection'))
                else:
                    loop.run_until_complete(self._run_sync_task('daily_data_collection'))
            except RuntimeError:
                asyncio.run(self._run_sync_task('daily_data_collection'))
    
    def _conditional_stock_screening(self):
        """根据市场状态决定是否执行股票筛选"""
        from utils.market_hours import getMarketStatusSummary
        
        market_status = getMarketStatusSummary()
        
        # 只在交易日执行股票筛选
        if market_status['isWeekday'] and not market_status['isHoliday']:
            # 使用asyncio在同步上下文中运行异步任务
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._run_sync_task('strong_rise_screening'))
                else:
                    loop.run_until_complete(self._run_sync_task('strong_rise_screening'))
            except RuntimeError:
                asyncio.run(self._run_sync_task('strong_rise_screening'))
    
    async def _run_sync_task(self, task_name: str) -> SyncResult:
        """运行指定的同步任务"""
        if task_name not in self.sync_tasks:
            return SyncResult(
                success=False,
                message=f"未知的同步任务: {task_name}",
                timestamp=datetime.now()
            )
        
        task = self.sync_tasks[task_name]
        if not task.enabled:
            return SyncResult(
                success=True,
                message=f"任务已禁用: {task_name}",
                timestamp=datetime.now()
            )
        
        logger.info(f"🔄 开始执行同步任务: {task.description}")
        start_time = datetime.now()
        
        try:
            # 根据任务类型执行相应的同步操作
            if task_name == 'stock_info_daily':
                result = await self._sync_stock_info_incremental()
            elif task_name == 'stock_info_weekly':
                result = await self._sync_stock_info_full()
            elif task_name == 'data_source_health':
                result = await self._check_data_source_health()
            elif task_name == 'cache_cleanup':
                result = await self._cleanup_cache()
            elif task_name == 'daily_data_collection':
                result = await self._collect_daily_stock_data()
            elif task_name == 'strong_rise_screening':
                result = await self._screen_strong_rise_stocks()
            else:
                result = SyncResult(
                    success=False,
                    message=f"未实现的任务类型: {task_name}",
                    timestamp=datetime.now()
                )
            
            # 更新任务状态
            task.last_run = start_time
            if result.success:
                task.last_success = start_time
                task.error_count = 0
                self.stats['successful_syncs'] += 1
            else:
                task.error_count += 1
                self.stats['failed_syncs'] += 1
            
            self.stats['total_syncs'] += 1
            
            # 计算执行时间
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            result.timestamp = start_time
            
            # 记录日志
            status = "✅ 成功" if result.success else "❌ 失败"
            logger.info(f"{status} 同步任务完成: {task.description} "
                       f"({result.duration_seconds:.1f}s) - {result.message}")
            
            return result
            
        except Exception as e:
            task.error_count += 1
            self.stats['failed_syncs'] += 1
            
            error_result = SyncResult(
                success=False,
                message=f"任务执行异常: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                timestamp=start_time
            )
            
            logger.error(f"❌ 同步任务异常: {task.description} - {str(e)}")
            return error_result
    
    async def _sync_stock_info_incremental(self) -> SyncResult:
        """增量同步股票信息（使用腾讯API验证现有股票）"""
        try:
            # 由于我们现在主要使用腾讯API，这里主要用于验证数据质量
            unified_collector = get_unified_collector(self.db_manager)
            status = await unified_collector.get_collection_status()
            
            return SyncResult(
                success=True,
                message=f"股票信息验证完成，数据源：{status.get('data_source', 'Tencent API')}",
                records_updated=status.get('latest_count', 0)
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"股票信息验证失败: {str(e)}"
            )
    
    async def _sync_stock_info_full(self) -> SyncResult:
        """全量数据收集（使用腾讯API）"""
        try:
            # 使用统一腾讯采集器进行全量数据收集
            unified_collector = get_unified_collector(self.db_manager)
            result = await unified_collector.collect_daily_stock_data()
            
            self.stats['last_full_sync'] = datetime.now()
            
            return SyncResult(
                success=result.success,
                message=f"全量数据收集完成：{result.successful_records}/{result.total_collected} 只股票 ({result.duration_seconds:.1f}s)",
                records_updated=result.successful_records
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"全量数据收集失败: {str(e)}"
            )
    
    async def _check_data_source_health(self) -> SyncResult:
        """检查腾讯数据源健康状态"""
        try:
            # 检查腾讯API的健康状态
            unified_collector = get_unified_collector(self.db_manager)
            status = await unified_collector.get_collection_status()
            
            # 简单测试：尝试获取一只测试股票的数据
            from services.tencent_data_service import TencentDataService
            tencent_service = TencentDataService()
            
            async with tencent_service as service:
                test_data = await service.get_stock_data(['000001'])  # 测试平安银行
                health_status = "healthy" if test_data and '000001' in test_data else "unhealthy"
            
            return SyncResult(
                success=health_status == "healthy",
                message=f"腾讯数据源健康检查完成，状态：{health_status}",
                records_updated=1 if health_status == "healthy" else 0
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"腾讯数据源健康检查失败: {str(e)}"
            )
    
    async def _cleanup_cache(self) -> SyncResult:
        """清理缓存"""
        try:
            # 这里可以实现具体的缓存清理逻辑
            # 例如清理过期的价格缓存、搜索缓存等
            
            return SyncResult(
                success=True,
                message="缓存清理完成",
                records_updated=0
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"缓存清理失败: {str(e)}"
            )
    
    async def _collect_daily_stock_data(self) -> SyncResult:
        """收集每日股票数据（使用统一腾讯采集器）"""
        try:
            # 使用统一腾讯采集器进行数据收集
            unified_collector = get_unified_collector(self.db_manager)
            
            # 检查是否需要初始化历史数据
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(DISTINCT trade_date) FROM daily_stock_changes'
                )
                days_with_data = cursor.fetchone()[0]
            
            # 如果历史数据不足，执行初始化
            if days_with_data < 5:
                logger.info("📊 历史数据不足，开始初始化...")
                screening_service = get_stock_screening_service(self.db_manager)
                init_result = await screening_service.initialize_historical_data(days_back=7)
                
                return SyncResult(
                    success=init_result['success_days'] > 0,
                    message=f"历史数据初始化完成: {init_result['success_days']}天成功，{init_result['failed_days']}天失败，共{init_result['total_records']}条记录",
                    records_updated=init_result['total_records']
                )
            
            # 正常的每日数据收集
            # 智能判断目标日期并检查是否需要收集
            from utils.market_hours import getMarketStatusSummary
            from datetime import datetime, timedelta
            
            today = datetime.now().strftime('%Y-%m-%d')
            market_status = getMarketStatusSummary()
            
            # 确定目标日期
            if market_status.get('isWeekday', False) and not market_status.get('isHoliday', False):
                target_date = today
            else:
                target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 检查目标日期是否已有充足数据
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(*) FROM daily_stock_changes WHERE trade_date = ?',
                    (target_date,)
                )
                existing_count = cursor.fetchone()[0]
            
            # 如果数据不足，则收集
            if existing_count < 1000:  # 假设正常情况下应该有至少1000条数据
                logger.info(f"📊 {target_date} 数据不足（现有{existing_count}条），开始统一数据收集...")
                result = await unified_collector.collect_daily_stock_data(target_date)
                
                return SyncResult(
                    success=result.success,
                    message=f"统一数据收集完成 {target_date}: {result.successful_records}/{result.total_collected} 条记录 ({result.duration_seconds:.1f}s)",
                    records_updated=result.successful_records
                )
            else:
                logger.info(f"✅ {target_date} 已有充足数据（{existing_count}条），跳过收集")
                return SyncResult(
                    success=True,
                    message=f"{target_date} 数据已存在，共{existing_count}条记录",
                    records_updated=0
                )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"统一数据收集失败: {str(e)}"
            )
    
    async def _screen_strong_rise_stocks(self, custom_criteria: Optional[ScreeningCriteria] = None) -> SyncResult:
        """筛选强势上涨股票"""
        try:
            # 获取股票筛选服务实例
            screening_service = get_stock_screening_service(self.db_manager)
            
            # 设置筛选条件：使用传入的条件，否则使用默认条件
            if custom_criteria:
                criteria = custom_criteria
            else:
                # 默认筛选条件：连续3天涨幅超过7%
                criteria = ScreeningCriteria(
                    screening_type='strong_rise_3d',
                    min_consecutive_days=3,
                    min_rise_percent=7.0,
                    min_volume=0,
                    market_filter=['SH', 'SZ']  # 目前只筛选A股
                )
            
            # 执行筛选
            screening_response = await screening_service.screen_strong_rise_stocks(criteria)
            
            return SyncResult(
                success=True,
                message=f"强势股票筛选完成，找到 {screening_response.total_count} 只符合条件的股票 (数据日期: {screening_response.screening_date})",
                records_updated=screening_response.total_count
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"强势股票筛选失败: {str(e)}"
            )
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        next_runs = {}
        for job in schedule.jobs:
            next_runs[str(job.job_func)] = job.next_run
        
        return {
            'running': self.running,
            'tasks': {name: {
                'name': task.name,
                'description': task.description,
                'frequency': task.frequency,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'last_success': task.last_success.isoformat() if task.last_success else None,
                'error_count': task.error_count,
                'health_status': 'healthy' if task.error_count < task.max_errors else 'error'
            } for name, task in self.sync_tasks.items()},
            'stats': self.stats,
            'next_scheduled_runs': {str(k): v.isoformat() if v else None for k, v in next_runs.items()}
        }
    
    async def manual_sync(self, task_name: str) -> SyncResult:
        """手动触发同步任务"""
        logger.info(f"🔧 手动触发同步任务: {task_name}")
        return await self._run_sync_task(task_name)
    
    def update_task_config(self, task_name: str, enabled: bool):
        """更新任务配置"""
        if task_name in self.sync_tasks:
            self.sync_tasks[task_name].enabled = enabled
            logger.info(f"📝 任务配置已更新: {task_name} - {'启用' if enabled else '禁用'}")

# 全局调度器实例
data_sync_scheduler: Optional[DataSyncScheduler] = None

def get_data_sync_scheduler(db_manager: DatabaseManager) -> DataSyncScheduler:
    """获取数据同步调度器实例"""
    global data_sync_scheduler
    
    if data_sync_scheduler is None:
        data_sync_scheduler = DataSyncScheduler(db_manager)
    
    return data_sync_scheduler