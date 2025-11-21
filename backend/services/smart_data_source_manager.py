"""
智能数据源管理器
负责数据源健康检查、优先级选择和智能切换
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """数据源类型"""
    SINA_REALTIME = "sina_realtime"  # 新浪财经实时接口
    AKSHARE_STOCK_LIST = "akshare_stock_list"  # AkShare股票列表
    AKSHARE_REALTIME_ALL = "akshare_realtime_all"  # 东方财富全量实时接口
    TENCENT = "tencent"
    AKSHARE_INDIVIDUAL = "akshare_individual"
    AKSHARE_HISTORY = "akshare_history"
    LOCAL_CACHE = "local_cache"

@dataclass
class DataSourceHealth:
    """数据源健康状况"""
    source_type: DataSourceType
    is_available: bool
    response_time: float
    success_rate: float
    last_check_time: datetime
    error_message: Optional[str] = None
    consecutive_failures: int = 0

class SmartDataSourceManager:
    """智能数据源管理器"""
    
    def __init__(self):
        self.health_status: Dict[DataSourceType, DataSourceHealth] = {}
        self.check_interval = 300  # 5分钟检查一次
        self.last_full_check = None
        self.preferred_source = None
        
        # 初始化所有数据源状态
        for source_type in DataSourceType:
            self.health_status[source_type] = DataSourceHealth(
                source_type=source_type,
                is_available=False,
                response_time=999.0,
                success_rate=0.0,
                last_check_time=datetime.now() - timedelta(hours=1)
            )
    
    async def check_all_sources(self) -> Dict[DataSourceType, DataSourceHealth]:
        """检查所有数据源的健康状况"""
        logger.info("🔍 开始全面检查数据源健康状况...")
        
        # 并发检查所有数据源
        tasks = []
        for source_type in DataSourceType:
            tasks.append(self._check_single_source(source_type))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 更新健康状态
        for i, source_type in enumerate(DataSourceType):
            if isinstance(results[i], Exception):
                logger.error(f"❌ {source_type.value} 检查失败: {results[i]}")
                self.health_status[source_type].is_available = False
                self.health_status[source_type].error_message = str(results[i])
                self.health_status[source_type].consecutive_failures += 1
            else:
                self.health_status[source_type] = results[i]
        
        self.last_full_check = datetime.now()
        self._update_preferred_source()
        
        # 打印健康报告
        self._print_health_report()
        
        return self.health_status
    
    async def _check_single_source(self, source_type: DataSourceType) -> DataSourceHealth:
        """检查单个数据源"""
        start_time = time.time()
        
        try:
            if source_type == DataSourceType.SINA_REALTIME:
                success = await self._check_sina_realtime()
            elif source_type == DataSourceType.AKSHARE_STOCK_LIST:
                success = await self._check_akshare_stock_list()
            elif source_type == DataSourceType.AKSHARE_REALTIME_ALL:
                success = await self._check_akshare_realtime_all()
            elif source_type == DataSourceType.TENCENT:
                success = await self._check_tencent()
            elif source_type == DataSourceType.AKSHARE_INDIVIDUAL:
                success = await self._check_akshare_individual()
            elif source_type == DataSourceType.AKSHARE_HISTORY:
                success = await self._check_akshare_history()
            elif source_type == DataSourceType.LOCAL_CACHE:
                success = await self._check_local_cache()
            else:
                success = False
            
            response_time = time.time() - start_time
            
            return DataSourceHealth(
                source_type=source_type,
                is_available=success,
                response_time=response_time,
                success_rate=100.0 if success else 0.0,
                last_check_time=datetime.now(),
                consecutive_failures=0 if success else self.health_status[source_type].consecutive_failures + 1
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return DataSourceHealth(
                source_type=source_type,
                is_available=False,
                response_time=response_time,
                success_rate=0.0,
                last_check_time=datetime.now(),
                error_message=str(e),
                consecutive_failures=self.health_status[source_type].consecutive_failures + 1
            )
    
    async def _check_sina_realtime(self) -> bool:
        """检查新浪财经实时接口"""
        try:
            from .sina_realtime_service import sina_realtime_service
            return await sina_realtime_service.test_connectivity()
        except Exception as e:
            logger.debug(f"新浪实时接口检查失败: {e}")
            return False
    
    async def _check_akshare_stock_list(self) -> bool:
        """检查AkShare股票列表接口"""
        try:
            import akshare as ak
            import asyncio
            
            # 测试获取股票列表
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, ak.stock_info_sz_name_code)
            return result is not None and not result.empty and len(result) > 1000
        except Exception as e:
            logger.debug(f"AkShare股票列表接口检查失败: {e}")
            return False
    
    async def _check_akshare_realtime_all(self) -> bool:
        """检查AkShare东方财富实时全量接口"""
        try:
            from .akshare_service import akshare_service
            if not akshare_service._check_availability():
                return False
            
            # 测试获取全量实时数据
            data = await akshare_service.get_all_a_stock_realtime_data()
            return data is not None and len(data) > 4000  # 至少要有4000只股票
        except Exception as e:
            logger.debug(f"AkShare全量实时接口检查失败: {e}")
            return False
    
    async def _check_tencent(self) -> bool:
        """检查腾讯接口"""
        try:
            from .tencent_data_service import tencent_service
            result = await tencent_service.get_single_stock_data("000001", "A")
            return result is not None and 'current_price' in result
        except Exception as e:
            logger.debug(f"腾讯接口检查失败: {e}")
            return False
    
    async def _check_akshare_individual(self) -> bool:
        """检查AkShare个股接口"""
        try:
            from .akshare_service import akshare_service
            if not akshare_service._check_availability():
                return False
            
            # 测试获取单只股票
            individual_data = akshare_service.ak.stock_individual_info_em(symbol="000001")
            return individual_data is not None and not individual_data.empty
        except Exception as e:
            logger.debug(f"AkShare个股接口检查失败: {e}")
            return False
    
    async def _check_akshare_history(self) -> bool:
        """检查AkShare历史数据接口"""
        try:
            from .akshare_service import akshare_service
            if not akshare_service._check_availability():
                return False
            
            # 测试获取历史数据
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=2)).strftime('%Y%m%d')
            
            hist_data = akshare_service.ak.stock_zh_a_hist(
                symbol="000001", 
                period="daily", 
                start_date=start_date, 
                end_date=end_date, 
                adjust=""
            )
            return hist_data is not None and not hist_data.empty
        except Exception as e:
            logger.debug(f"AkShare历史接口检查失败: {e}")
            return False
    
    async def _check_local_cache(self) -> bool:
        """检查本地缓存数据"""
        try:
            import sqlite3
            from database import DatabaseManager
            
            db_manager = DatabaseManager('stock_pool.db')
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM daily_stock_changes 
                    WHERE trade_date >= date('now', '-7 days')
                ''')
                count = cursor.fetchone()[0]
                return count > 1000  # 至少有1000条近期数据
        except Exception as e:
            logger.debug(f"本地缓存检查失败: {e}")
            return False
    
    def _update_preferred_source(self):
        """更新首选数据源"""
        # 按优先级排序数据源  
        priority_order = [
            DataSourceType.SINA_REALTIME,     # 最优：新浪财经实时接口(已验证可用)
            DataSourceType.AKSHARE_STOCK_LIST, # 次选：AkShare股票列表(用于基础信息)
            DataSourceType.AKSHARE_REALTIME_ALL, # 备选：东方财富全量实时接口
            DataSourceType.TENCENT,           # 备选：腾讯接口  
            DataSourceType.AKSHARE_INDIVIDUAL, # 备选：AkShare个股接口
            DataSourceType.AKSHARE_HISTORY,   # 降级：AkShare历史接口
            DataSourceType.LOCAL_CACHE        # 最后：本地缓存
        ]
        
        for source_type in priority_order:
            health = self.health_status[source_type]
            if health.is_available and health.consecutive_failures < 3:
                self.preferred_source = source_type
                logger.info(f"🎯 选择首选数据源: {source_type.value}")
                return
        
        # 如果没有可用数据源，选择错误最少的
        best_source = min(
            self.health_status.values(),
            key=lambda h: h.consecutive_failures
        )
        self.preferred_source = best_source.source_type
        logger.warning(f"⚠️ 所有数据源都有问题，选择最佳: {self.preferred_source.value}")
    
    def _print_health_report(self):
        """打印健康状况报告"""
        logger.info("📊 数据源健康状况报告:")
        logger.info("=" * 50)
        
        for source_type in DataSourceType:
            health = self.health_status[source_type]
            status = "✅" if health.is_available else "❌"
            logger.info(f"{status} {source_type.value:<20} | "
                       f"响应时间: {health.response_time:.2f}s | "
                       f"连续失败: {health.consecutive_failures}次")
        
        logger.info(f"🎯 当前首选数据源: {self.preferred_source.value if self.preferred_source else 'None'}")
        logger.info("=" * 50)
    
    async def get_optimal_collection_strategy(self, stock_count: int) -> Tuple[DataSourceType, Dict[str, Any]]:
        """获取最优的数据采集策略"""
        # 如果需要检查健康状况
        if (self.last_full_check is None or 
            (datetime.now() - self.last_full_check).seconds > self.check_interval):
            await self.check_all_sources()
        
        if not self.preferred_source:
            raise Exception("没有可用的数据源")
        
        # 根据数据源类型返回不同的策略
        strategy = {
            'source_type': self.preferred_source,
            'batch_size': self._get_optimal_batch_size(self.preferred_source, stock_count),
            'delay_between_batches': self._get_optimal_delay(self.preferred_source),
            'timeout': self._get_optimal_timeout(self.preferred_source),
            'retry_count': 3 if self.preferred_source == DataSourceType.TENCENT else 1
        }
        
        logger.info(f"🚀 采用数据采集策略: {self.preferred_source.value}")
        logger.info(f"   批次大小: {strategy['batch_size']}")
        logger.info(f"   批次延迟: {strategy['delay_between_batches']}s")
        
        return self.preferred_source, strategy
    
    def _get_optimal_batch_size(self, source_type: DataSourceType, stock_count: int) -> int:
        """获取最优批次大小"""
        if source_type == DataSourceType.TENCENT:
            return min(100, stock_count)  # 腾讯接口支持大批量
        elif source_type == DataSourceType.AKSHARE_INDIVIDUAL:
            return min(50, stock_count)   # AkShare个股接口中等批量
        elif source_type == DataSourceType.AKSHARE_HISTORY:
            return min(20, stock_count)   # 历史接口小批量
        else:
            return min(200, stock_count)  # 本地缓存大批量
    
    def _get_optimal_delay(self, source_type: DataSourceType) -> float:
        """获取最优延迟时间"""
        if source_type == DataSourceType.TENCENT:
            return 0.1  # 腾讯接口快
        elif source_type == DataSourceType.AKSHARE_INDIVIDUAL:
            return 0.3  # AkShare个股接口需要更多延迟
        elif source_type == DataSourceType.AKSHARE_HISTORY:
            return 0.5  # 历史接口最慢
        else:
            return 0.0  # 本地缓存无延迟
    
    def _get_optimal_timeout(self, source_type: DataSourceType) -> int:
        """获取最优超时时间"""
        if source_type == DataSourceType.TENCENT:
            return 10   # 腾讯接口10秒超时
        elif source_type == DataSourceType.AKSHARE_INDIVIDUAL:
            return 30   # AkShare个股接口30秒
        elif source_type == DataSourceType.AKSHARE_HISTORY:
            return 60   # 历史接口60秒
        else:
            return 5    # 本地缓存5秒
    
    def report_collection_result(self, source_type: DataSourceType, success_count: int, total_count: int):
        """报告采集结果，用于更新健康状况"""
        if source_type in self.health_status:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            health = self.health_status[source_type]
            
            # 更新成功率（使用滑动平均）
            health.success_rate = (health.success_rate * 0.7 + success_rate * 0.3)
            
            # 更新连续失败计数
            if success_rate > 80:  # 成功率超过80%认为成功
                health.consecutive_failures = 0
                health.is_available = True
            else:
                health.consecutive_failures += 1
                if health.consecutive_failures >= 3:
                    health.is_available = False
            
            logger.info(f"📊 {source_type.value} 采集结果: {success_count}/{total_count} "
                       f"成功率: {success_rate:.1f}% 健康度: {health.success_rate:.1f}%")

# 全局实例
smart_data_source_manager = SmartDataSourceManager()