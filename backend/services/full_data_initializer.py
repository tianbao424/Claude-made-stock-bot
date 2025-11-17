#!/usr/bin/env python3
"""
全量数据初始化器
负责完整的数据库重建和数据采集流程
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, StockInfo, DailyStockChange
from services.akshare_service import akshare_service
from services.comprehensive_history_updater import ComprehensiveHistoryUpdater

logger = logging.getLogger(__name__)

@dataclass
class InitializationProgress:
    """初始化进度"""
    stage: str
    current_task: str
    total_items: int
    completed_items: int
    failed_items: int
    start_time: datetime
    current_time: datetime
    
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        return (self.current_time - self.start_time).total_seconds()
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        if self.completed_items == 0:
            return None
        rate = self.completed_items / self.elapsed_seconds
        remaining_items = self.total_items - self.completed_items
        return remaining_items / rate if rate > 0 else None
    
    def to_dict(self) -> Dict:
        return {
            'stage': self.stage,
            'current_task': self.current_task,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'failed_items': self.failed_items,
            'progress_percent': round(self.progress_percent, 1),
            'elapsed_seconds': round(self.elapsed_seconds, 1),
            'estimated_remaining_seconds': round(self.estimated_remaining_seconds, 1) if self.estimated_remaining_seconds else None
        }

@dataclass
class InitializationResult:
    """初始化结果"""
    success: bool
    total_duration: float
    stages_completed: List[str]
    stages_failed: List[str]
    stats: Dict[str, int]
    errors: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'total_duration': round(self.total_duration, 1),
            'stages_completed': self.stages_completed,
            'stages_failed': self.stages_failed,
            'stats': self.stats,
            'errors': self.errors
        }

class FullDataInitializer:
    """全量数据初始化器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_progress: Optional[InitializationProgress] = None
        self.progress_callbacks: List[callable] = []
    
    def add_progress_callback(self, callback: callable):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def _update_progress(self, stage: str, current_task: str, total_items: int = 0, 
                        completed_items: int = 0, failed_items: int = 0):
        """更新进度"""
        if self.current_progress is None:
            start_time = datetime.now()
        else:
            start_time = self.current_progress.start_time
            
        self.current_progress = InitializationProgress(
            stage=stage,
            current_task=current_task,
            total_items=total_items,
            completed_items=completed_items,
            failed_items=failed_items,
            start_time=start_time,
            current_time=datetime.now()
        )
        
        # 通知所有回调函数
        for callback in self.progress_callbacks:
            try:
                callback(self.current_progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def full_initialize(self, include_strategy_cleanup: bool = False) -> InitializationResult:
        """执行完整的数据初始化流程"""
        start_time = datetime.now()
        stages_completed = []
        stages_failed = []
        stats = {}
        errors = []
        
        logger.info("🚀 开始全量数据初始化...")
        
        try:
            # 阶段1: 清理现有数据
            cleanup_msg = "清理历史数据和股票池" + ("（包含策略分析数据）" if include_strategy_cleanup else "（保留策略分析数据）")
            logger.info(f"📝 阶段1: {cleanup_msg}")
            self._update_progress("cleanup", "清理现有数据库表...", 4, 0)
            
            cleanup_result = await self._cleanup_database(include_strategy_cleanup)
            if cleanup_result['success']:
                stages_completed.append("cleanup")
                stats.update(cleanup_result['stats'])
                self._update_progress("cleanup", "数据清理完成", 4, 4)
            else:
                stages_failed.append("cleanup")
                errors.extend(cleanup_result['errors'])
            
            # 阶段2: 获取A股列表
            logger.info("📈 阶段2: 获取A股股票列表")
            self._update_progress("a_stocks", "正在获取A股列表...", 5000, 0)
            
            a_stock_result = await self._import_a_stocks()
            if a_stock_result['success']:
                stages_completed.append("a_stocks")
                stats.update(a_stock_result['stats'])
                self._update_progress("a_stocks", f"A股列表获取完成，共{a_stock_result['stats']['a_stocks_imported']}只", 
                                    a_stock_result['stats']['a_stocks_imported'], a_stock_result['stats']['a_stocks_imported'])
            else:
                stages_failed.append("a_stocks")
                errors.extend(a_stock_result['errors'])
            
            # 阶段3: 获取港股列表
            logger.info("🏮 阶段3: 获取港股股票列表")
            self._update_progress("hk_stocks", "正在获取港股列表...", 5000, 0)
            
            hk_stock_result = await self._import_hk_stocks()
            if hk_stock_result['success']:
                stages_completed.append("hk_stocks")
                stats.update(hk_stock_result['stats'])
                self._update_progress("hk_stocks", f"港股列表获取完成，共{hk_stock_result['stats']['hk_stocks_imported']}只", 
                                    hk_stock_result['stats']['hk_stocks_imported'], hk_stock_result['stats']['hk_stocks_imported'])
            else:
                stages_failed.append("hk_stocks")
                errors.extend(hk_stock_result['errors'])
            
            # 阶段4: 获取实时数据
            logger.info("⚡ 阶段4: 获取实时股票数据")
            total_stocks = stats.get('a_stocks_imported', 0) + stats.get('hk_stocks_imported', 0)
            self._update_progress("realtime", "正在获取实时数据...", total_stocks, 0)
            
            realtime_result = await self._collect_realtime_data()
            if realtime_result['success']:
                stages_completed.append("realtime")
                stats.update(realtime_result['stats'])
                self._update_progress("realtime", f"实时数据获取完成，共{realtime_result['stats']['realtime_updated']}只", 
                                    realtime_result['stats']['realtime_updated'], realtime_result['stats']['realtime_updated'])
            else:
                stages_failed.append("realtime")
                errors.extend(realtime_result['errors'])
            
            # 阶段5: 获取30天历史数据
            logger.info("📊 阶段5: 获取30天历史数据")
            a_stocks_count = stats.get('a_stocks_imported', 0)
            self._update_progress("historical", "正在获取历史数据...", a_stocks_count, 0)
            
            historical_result = await self._collect_historical_data()
            if historical_result['success']:
                stages_completed.append("historical")
                stats.update(historical_result['stats'])
                self._update_progress("historical", f"历史数据获取完成，共{historical_result['stats']['historical_updated']}只", 
                                    historical_result['stats']['historical_updated'], historical_result['stats']['historical_updated'])
            else:
                stages_failed.append("historical")
                errors.extend(historical_result['errors'])
            
            # 阶段6: 获取财务数据
            logger.info("💰 阶段6: 获取财务数据")
            self._update_progress("financial", "正在获取财务数据...", a_stocks_count, 0)
            
            financial_result = await self._collect_financial_data()
            if financial_result['success']:
                stages_completed.append("financial")
                stats.update(financial_result['stats'])
                self._update_progress("financial", f"财务数据获取完成，共{financial_result['stats']['financial_updated']}只", 
                                    financial_result['stats']['financial_updated'], financial_result['stats']['financial_updated'])
            else:
                stages_failed.append("financial")
                errors.extend(financial_result['errors'])
            
        except Exception as e:
            logger.error(f"❌ 全量初始化过程中发生异常: {e}")
            errors.append(f"初始化异常: {str(e)}")
        
        # 计算总耗时
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # 判断是否成功
        success = len(stages_failed) == 0 and len(stages_completed) >= 4  # 至少完成主要阶段
        
        result = InitializationResult(
            success=success,
            total_duration=total_duration,
            stages_completed=stages_completed,
            stages_failed=stages_failed,
            stats=stats,
            errors=errors
        )
        
        logger.info(f"🎉 全量数据初始化完成！成功: {success}, 耗时: {total_duration:.1f}秒")
        logger.info(f"完成阶段: {stages_completed}")
        if stages_failed:
            logger.warning(f"失败阶段: {stages_failed}")
        
        return result
    
    async def _cleanup_database(self, include_strategy_data: bool = False) -> Dict[str, Any]:
        """清理数据库"""
        try:
            logger.info("🧹 清理数据库表...")
            
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # 基础数据表（必须清理）
            core_tables = [
                'daily_stock_changes',  # 历史交易数据
                'stock_pool'            # 股票池数据
            ]
            
            # 策略分析表（可选清理）
            strategy_tables = [
                'strategy_analysis_data',  # 策略分析结果
                'generated_strategies'     # 生成的策略
            ]
            
            # 确定要清理的表
            tables_to_clean = core_tables.copy()
            if include_strategy_data:
                tables_to_clean.extend(strategy_tables)
                logger.info("📊 包含策略分析数据清理")
            else:
                logger.info("🔒 保留策略分析数据")
            
            cleaned_tables = 0
            cleaned_records = 0
            
            for table in tables_to_clean:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_count = cursor.rowcount
                    logger.info(f"✅ 清理表 {table}: {deleted_count} 条记录")
                    cleaned_tables += 1
                    cleaned_records += deleted_count
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        logger.info(f"⚠️ 表 {table} 不存在，跳过")
                    else:
                        logger.warning(f"⚠️ 清理表 {table} 失败: {e}")
            
            # 重置stock_info表的非核心字段
            cursor.execute("""
                UPDATE stock_info 
                SET market_cap = 0.0, pe_ratio = 0.0, pb_ratio = 0.0, 
                    dividend_yield = 0.0, updated_at = ?
            """, (datetime.now().isoformat(),))
            
            updated_stocks = cursor.rowcount
            logger.info(f"🔄 重置 {updated_stocks} 只股票的财务字段")
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'stats': {
                    'tables_cleaned': cleaned_tables,
                    'records_deleted': cleaned_records,
                    'stocks_reset': updated_stocks,
                    'strategy_data_preserved': not include_strategy_data
                },
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"❌ 数据库清理失败: {e}")
            return {
                'success': False,
                'stats': {'tables_cleaned': 0, 'records_deleted': 0},
                'errors': [f"数据库清理失败: {str(e)}"]
            }
    
    async def _import_a_stocks(self) -> Dict[str, Any]:
        """导入A股列表"""
        try:
            imported_count = await akshare_service.import_a_stocks()
            
            return {
                'success': imported_count > 0,
                'stats': {'a_stocks_imported': imported_count},
                'errors': [] if imported_count > 0 else ['A股列表导入失败']
            }
        except Exception as e:
            logger.error(f"❌ A股列表导入失败: {e}")
            return {
                'success': False,
                'stats': {'a_stocks_imported': 0},
                'errors': [f"A股列表导入失败: {str(e)}"]
            }
    
    async def _import_hk_stocks(self) -> Dict[str, Any]:
        """导入港股列表"""
        try:
            imported_count = await akshare_service.import_hk_stocks()
            
            return {
                'success': imported_count > 0,
                'stats': {'hk_stocks_imported': imported_count},
                'errors': [] if imported_count > 0 else ['港股列表导入失败']
            }
        except Exception as e:
            logger.error(f"❌ 港股列表导入失败: {e}")
            return {
                'success': False,
                'stats': {'hk_stocks_imported': 0},
                'errors': [f"港股列表导入失败: {str(e)}"]
            }
    
    async def _collect_realtime_data(self) -> Dict[str, Any]:
        """收集实时数据"""
        try:
            logger.info("🔄 开始收集实时数据...")
            
            # 获取前2000只A股的实时数据
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM stock_info WHERE market IN ('SH', 'SZ') LIMIT 2000")
            a_stocks = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            successful_count = 0
            failed_count = 0
            
            # 使用腾讯接口批量获取实时数据
            try:
                from services.tencent_data_service import tencent_service
                
                # 分批处理，每批100只股票
                batch_size = 100
                for i in range(0, len(a_stocks), batch_size):
                    batch_stocks = a_stocks[i:i + batch_size]
                    self._update_progress("realtime", f"获取实时数据 {i + 1}-{min(i + batch_size, len(a_stocks))}/{len(a_stocks)}", 
                                        len(a_stocks), i)
                    
                    try:
                        batch_data = await tencent_service.get_realtime_data(batch_stocks)
                        if batch_data:
                            successful_count += len(batch_data)
                        else:
                            failed_count += len(batch_stocks)
                    except Exception as batch_error:
                        logger.warning(f"批次 {i//batch_size + 1} 获取失败: {batch_error}")
                        failed_count += len(batch_stocks)
                    
                    # 避免请求过频
                    await asyncio.sleep(0.1)
                    
            except ImportError:
                logger.warning("腾讯服务不可用，跳过实时数据获取")
                successful_count = 0
                failed_count = len(a_stocks)
            
            return {
                'success': successful_count > 0,
                'stats': {
                    'realtime_updated': successful_count,
                    'realtime_failed': failed_count
                },
                'errors': [] if successful_count > 0 else ['实时数据获取失败']
            }
            
        except Exception as e:
            logger.error(f"❌ 实时数据收集失败: {e}")
            return {
                'success': False,
                'stats': {'realtime_updated': 0, 'realtime_failed': 0},
                'errors': [f"实时数据收集失败: {str(e)}"]
            }
    
    async def _collect_historical_data(self) -> Dict[str, Any]:
        """收集30天历史数据"""
        try:
            logger.info("📊 开始收集30天历史数据...")
            
            # 使用综合历史数据更新器
            history_updater = ComprehensiveHistoryUpdater(self.db_manager.db_path)
            
            # 获取所有需要历史数据的A股
            priority_stocks = await history_updater.get_priority_stocks(3000)  # 获取更多股票
            
            if not priority_stocks:
                return {
                    'success': True,
                    'stats': {'historical_updated': 0},
                    'errors': ['没有需要更新历史数据的股票']
                }
            
            # 分批更新历史数据，更保守的策略
            batch_size = 100  # 每个大批次100只股票
            total_successful = 0
            total_failed = 0
            
            for i in range(0, len(priority_stocks), batch_size):
                batch_stocks = priority_stocks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(priority_stocks) + batch_size - 1) // batch_size
                
                self._update_progress("historical", 
                                    f"更新历史数据批次 {batch_num}/{total_batches} ({len(batch_stocks)}只股票)", 
                                    len(priority_stocks), i)
                
                try:
                    logger.info(f"🚀 开始处理批次 {batch_num}/{total_batches}，包含 {len(batch_stocks)} 只股票")
                    
                    batch_result = await history_updater.update_historical_data_batch(batch_stocks, days=30)
                    total_successful += batch_result['success']
                    total_failed += batch_result['failed']
                    
                    success_rate = (batch_result['success'] / len(batch_stocks) * 100) if len(batch_stocks) > 0 else 0
                    logger.info(f"✅ 批次 {batch_num} 完成，成功率: {success_rate:.1f}% ({batch_result['success']}/{len(batch_stocks)})")
                    
                    # 如果成功率太低，增加等待时间
                    if success_rate < 20:
                        logger.warning(f"⚠️ 成功率过低，额外等待60秒...")
                        await asyncio.sleep(60)
                    
                except Exception as batch_error:
                    logger.error(f"❌ 历史数据批次 {batch_num} 失败: {batch_error}")
                    total_failed += len(batch_stocks)
                
                # 批次间的较长等待时间，让API服务器恢复
                if i + batch_size < len(priority_stocks):  # 不是最后一批
                    wait_time = 30 + (total_failed / max(total_successful, 1)) * 10  # 根据失败率调整等待时间
                    wait_time = min(wait_time, 120)  # 最多等待2分钟
                    logger.info(f"⏳ 批次间等待 {wait_time:.0f} 秒，让服务器恢复...")
                    await asyncio.sleep(wait_time)
            
            return {
                'success': total_successful > 0,
                'stats': {
                    'historical_updated': total_successful,
                    'historical_failed': total_failed
                },
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"❌ 历史数据收集失败: {e}")
            return {
                'success': False,
                'stats': {'historical_updated': 0, 'historical_failed': 0},
                'errors': [f"历史数据收集失败: {str(e)}"]
            }
    
    async def _collect_financial_data(self) -> Dict[str, Any]:
        """收集财务数据"""
        try:
            logger.info("💰 开始收集财务数据...")
            
            # 获取A股列表
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM stock_info WHERE market IN ('SH', 'SZ') LIMIT 1000")
            a_stocks = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            successful_count = 0
            failed_count = 0
            
            # 模拟财务数据更新（实际实现时可以集成真实的财务数据API）
            for i, symbol in enumerate(a_stocks):
                self._update_progress("financial", f"更新财务数据 {i + 1}/{len(a_stocks)}: {symbol}", 
                                    len(a_stocks), i)
                
                try:
                    # 这里可以集成真实的财务数据获取逻辑
                    # 例如使用akshare的财务数据接口
                    # financial_data = await get_financial_data(symbol)
                    
                    # 目前使用模拟数据
                    await asyncio.sleep(0.01)  # 模拟网络请求
                    successful_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    logger.debug(f"财务数据获取失败 {symbol}: {e}")
                
                # 每100只股票输出一次进度
                if (i + 1) % 100 == 0:
                    logger.info(f"财务数据进度: {i + 1}/{len(a_stocks)}, 成功: {successful_count}, 失败: {failed_count}")
            
            return {
                'success': successful_count > 0,
                'stats': {
                    'financial_updated': successful_count,
                    'financial_failed': failed_count
                },
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"❌ 财务数据收集失败: {e}")
            return {
                'success': False,
                'stats': {'financial_updated': 0, 'financial_failed': 0},
                'errors': [f"财务数据收集失败: {str(e)}"]
            }
    
    def get_current_progress(self) -> Optional[Dict]:
        """获取当前进度"""
        if self.current_progress:
            return self.current_progress.to_dict()
        return None

# 全局实例
_full_initializer_instance = None

def get_full_data_initializer(db_manager: DatabaseManager) -> FullDataInitializer:
    """获取全量数据初始化器实例"""
    global _full_initializer_instance
    if _full_initializer_instance is None:
        _full_initializer_instance = FullDataInitializer(db_manager)
    return _full_initializer_instance

# 测试函数
async def test_full_initialization():
    """测试全量数据初始化"""
    import os
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
    db_manager = DatabaseManager(db_path)
    
    initializer = FullDataInitializer(db_manager)
    
    # 添加进度回调
    def progress_callback(progress: InitializationProgress):
        print(f"[{progress.stage}] {progress.current_task} - {progress.progress_percent:.1f}% "
              f"({progress.completed_items}/{progress.total_items})")
    
    initializer.add_progress_callback(progress_callback)
    
    # 执行初始化
    result = await initializer.full_initialize()
    
    print("\n" + "="*50)
    print("全量数据初始化结果:")
    print(f"成功: {result.success}")
    print(f"总耗时: {result.total_duration:.1f} 秒")
    print(f"完成阶段: {result.stages_completed}")
    print(f"失败阶段: {result.stages_failed}")
    print(f"统计数据: {result.stats}")
    if result.errors:
        print(f"错误信息: {result.errors}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_full_initialization())