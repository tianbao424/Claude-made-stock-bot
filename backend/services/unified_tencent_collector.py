#!/usr/bin/env python3
"""
统一腾讯数据采集器
替换AkShare，使用腾讯API作为主要数据源，合并所有数据采集功能
"""
import asyncio
import logging
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, DailyStockChange
from services.tencent_data_service import TencentDataService
from services.stock_info_updater import get_stock_info_updater
from utils.market_hours import isWeekday, isHoliday, getMarketStatusSummary

logger = logging.getLogger(__name__)

@dataclass
class CollectionResult:
    """数据收集结果"""
    success: bool
    total_collected: int
    successful_records: int
    failed_records: int
    collection_date: str
    duration_seconds: float
    error_message: str = ""

class UnifiedTencentCollector:
    """统一腾讯数据采集器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.tencent_service = TencentDataService(db_manager)
        
    async def collect_daily_stock_data(self, trade_date: str = None, force_discovery: bool = False) -> CollectionResult:
        """
        统一收集股票数据，包含价格、成交量、换手率、市值等所有信息
        
        Args:
            trade_date: 交易日期，格式YYYY-MM-DD，默认为智能判断的目标日期
            force_discovery: 是否强制执行股票发现更新
            
        Returns:
            CollectionResult: 收集结果
        """
        start_time = datetime.now()
        
        # 智能确定目标日期
        if trade_date is None:
            trade_date = self._determine_target_date()
        
        logger.info(f"🚀 开始统一数据收集 - 目标日期: {trade_date}")
        
        try:
            # 检查是否为交易日
            if not self._is_trading_day(trade_date):
                return CollectionResult(
                    success=False,
                    total_collected=0,
                    successful_records=0,
                    failed_records=0,
                    collection_date=trade_date,
                    duration_seconds=0,
                    error_message=f"{trade_date} 不是交易日"
                )
            
            # 检查是否需要更新股票列表
            should_update = force_discovery or await self._should_update_stock_list()
            if should_update:
                logger.info("🔍 执行全量股票信息更新...")
                updater = get_stock_info_updater(self.db_manager)
                update_result = await updater.full_update_stock_info()
                
                if update_result.get('success'):
                    logger.info(f"✅ 股票信息更新完成: 新增{update_result.get('new_stocks', 0)}只, "
                               f"更新{update_result.get('updated_stocks', 0)}只, "
                               f"移除{update_result.get('removed_stocks', 0)}只")
                else:
                    logger.warning(f"⚠️ 股票信息更新失败: {update_result.get('error', '未知错误')}")
            
            # 获取数据库中的股票列表
            stock_codes = self._get_stock_codes_from_db()
            if not stock_codes:
                return CollectionResult(
                    success=False,
                    total_collected=0,
                    successful_records=0,
                    failed_records=0,
                    collection_date=trade_date,
                    duration_seconds=0,
                    error_message="数据库中没有股票代码"
                )
            
            logger.info(f"📊 准备收集 {len(stock_codes)} 只股票的数据")
            
            # 使用腾讯API批量获取数据
            collected_data = []
            successful_count = 0
            failed_count = 0
            
            # 分批处理，避免单次请求过大
            batch_size = 50
            total_batches = (len(stock_codes) + batch_size - 1) // batch_size
            
            async with self.tencent_service as service:
                for i in range(0, len(stock_codes), batch_size):
                    batch_codes = stock_codes[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    logger.info(f"📥 处理第 {batch_num}/{total_batches} 批: {len(batch_codes)} 只股票")
                    
                    try:
                        # 获取批次数据
                        batch_data = await service.get_stock_data(batch_codes)
                        
                        # 处理每只股票的数据
                        for stock_code in batch_codes:
                            if stock_code in batch_data:
                                tencent_data = batch_data[stock_code]
                                
                                # 创建DailyStockChange对象
                                stock_change = self._create_daily_stock_change(
                                    stock_code=stock_code,
                                    trade_date=trade_date,
                                    tencent_data=tencent_data
                                )
                                
                                if stock_change:
                                    collected_data.append(stock_change)
                                    successful_count += 1
                                else:
                                    failed_count += 1
                                    logger.debug(f"❌ 处理 {stock_code} 数据失败")
                            else:
                                failed_count += 1
                                logger.debug(f"❌ {stock_code} 未获取到数据")
                        
                        # 添加小延迟，避免请求过快
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"❌ 处理第 {batch_num} 批数据失败: {e}")
                        failed_count += len(batch_codes)
            
            # 保存到数据库
            if collected_data:
                saved_count = await self._save_daily_changes(collected_data, trade_date)
                logger.info(f"💾 成功保存 {saved_count} 条记录到数据库")
            else:
                saved_count = 0
                logger.warning("⚠️ 没有数据需要保存")
            
            # 计算执行时间
            duration = (datetime.now() - start_time).total_seconds()
            
            # 返回结果
            result = CollectionResult(
                success=successful_count > 0,
                total_collected=len(stock_codes),
                successful_records=successful_count,
                failed_records=failed_count,
                collection_date=trade_date,
                duration_seconds=duration
            )
            
            logger.info(f"✅ 数据收集完成: 成功 {successful_count}/{len(stock_codes)} "
                       f"({successful_count/len(stock_codes)*100:.1f}%) 用时 {duration:.1f}s")
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ 统一数据收集失败: {e}")
            
            return CollectionResult(
                success=False,
                total_collected=0,
                successful_records=0,
                failed_records=0,
                collection_date=trade_date,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    async def _should_update_stock_list(self) -> bool:
        """判断是否需要更新股票列表"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查最后更新时间
                cursor.execute('SELECT MAX(updated_at) FROM stock_info WHERE LENGTH(symbol) = 6')
                last_updated_str = cursor.fetchone()[0]
                
                if not last_updated_str:
                    logger.info("📅 stock_info表没有更新时间记录，需要更新")
                    return True
                
                # 解析最后更新时间
                try:
                    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                    days_since_update = (datetime.now() - last_updated).days
                    
                    # 如果超过7天没有更新，则需要更新
                    if days_since_update >= 7:
                        logger.info(f"📅 stock_info表已 {days_since_update} 天没有更新，需要更新")
                        return True
                    
                    # 检查是否为周一（通常新股在周一上市）
                    today = datetime.now()
                    if today.weekday() == 0:  # 周一
                        logger.info("📅 今天是周一，检查新上市股票")
                        return True
                        
                except ValueError:
                    logger.warning("📅 无法解析更新时间，执行更新")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ 检查股票列表更新状态失败: {e}")
            return False
    
    def _determine_target_date(self) -> str:
        """智能确定目标收集日期"""
        today = datetime.now().strftime('%Y-%m-%d')
        market_status = getMarketStatusSummary()
        
        # 如果今天是交易日，优先收集今天的数据；否则收集最近交易日数据
        if market_status.get('isWeekday', False) and not market_status.get('isHoliday', False):
            return today
        else:
            # 如果今天不是交易日，则收集昨天的数据
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def _is_trading_day(self, date_str: str) -> bool:
        """判断是否为交易日"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # 简单判断：周一到周五且非节假日
            # 这里可以根据需要扩展更复杂的节假日判断
            return date_obj.weekday() < 5  # 0-6, 0是周一，6是周日
        except:
            return False
    
    def _get_stock_codes_from_db(self) -> List[str]:
        """从数据库获取股票代码列表（从stock_info表获取A股）"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol 
                    FROM stock_info 
                    WHERE (symbol LIKE '6%' OR symbol LIKE '0%' OR symbol LIKE '3%') 
                        AND LENGTH(symbol) = 6
                        AND is_active = 1
                    ORDER BY symbol
                ''')
                stock_codes = [row[0] for row in cursor.fetchall()]
                logger.info(f"📊 从stock_info表获取到 {len(stock_codes)} 只A股代码")
                return stock_codes
        except Exception as e:
            logger.error(f"❌ 获取股票代码失败: {e}")
            return []
    
    def _create_daily_stock_change(self, stock_code: str, trade_date: str, tencent_data: Dict[str, Any]) -> Optional[DailyStockChange]:
        """将腾讯API数据转换为DailyStockChange对象"""
        try:
            # 确定市场
            market = self._get_market_from_code(stock_code)
            
            # 创建DailyStockChange对象
            stock_change = DailyStockChange(
                stock_code=stock_code,
                trade_date=trade_date,
                change_percent=float(tencent_data.get('change_percent', 0)),
                close_price=float(tencent_data.get('current_price', 0)),
                open_price=float(tencent_data.get('open_price', 0)),
                high_price=float(tencent_data.get('high_price', 0)),
                low_price=float(tencent_data.get('low_price', 0)),
                volume=int(tencent_data.get('volume', 0)),
                turnover=float(tencent_data.get('turnover', 0)),
                market=market,
                # 新增：市值和技术指标数据（腾讯API直接提供）
                total_market_cap=float(tencent_data.get('total_market_cap', 0)),  # 已经是万元
                circulating_market_cap=float(tencent_data.get('circulating_market_cap', 0)),  # 已经是万元
                turnover_rate=float(tencent_data.get('turnover_rate', 0)),
                pe_ratio=float(tencent_data.get('pe_ratio', 0)),
                pb_ratio=float(tencent_data.get('pb_ratio', 0)),
                created_at=datetime.now().isoformat()
            )
            
            return stock_change
            
        except Exception as e:
            logger.error(f"❌ 创建 {stock_code} 股票变动记录失败: {e}")
            logger.debug(f"腾讯数据: {tencent_data}")
            return None
    
    def _get_market_from_code(self, stock_code: str) -> str:
        """根据股票代码确定市场"""
        if stock_code.startswith('6'):
            return 'SH'  # 上海
        elif stock_code.startswith(('0', '3')):
            return 'SZ'  # 深圳
        else:
            return 'OTHER'
    
    async def _save_daily_changes(self, stock_changes: List[DailyStockChange], trade_date: str) -> int:
        """保存股票变动数据到数据库"""
        if not stock_changes:
            return 0
        
        saved_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock_change in stock_changes:
                    try:
                        # 使用UPSERT操作，如果记录已存在则更新，否则插入
                        cursor.execute('''
                            INSERT OR REPLACE INTO daily_stock_changes 
                            (stock_code, trade_date, change_percent, close_price, open_price, 
                             high_price, low_price, volume, turnover, market, 
                             total_market_cap, circulating_market_cap, turnover_rate, 
                             pe_ratio, pb_ratio, created_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_change.stock_code,
                            stock_change.trade_date,
                            stock_change.change_percent,
                            stock_change.close_price,
                            stock_change.open_price,
                            stock_change.high_price,
                            stock_change.low_price,
                            stock_change.volume,
                            stock_change.turnover,
                            stock_change.market,
                            stock_change.total_market_cap,
                            stock_change.circulating_market_cap,
                            stock_change.turnover_rate,
                            stock_change.pe_ratio,
                            stock_change.pb_ratio,
                            stock_change.created_at
                        ))
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"❌ 保存 {stock_change.stock_code} 数据失败: {e}")
                        continue
                
                conn.commit()
                logger.info(f"💾 成功保存 {saved_count}/{len(stock_changes)} 条记录")
                
        except Exception as e:
            logger.error(f"❌ 数据库保存操作失败: {e}")
            
        return saved_count
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """获取数据收集状态"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取最新数据日期
                cursor.execute('''
                    SELECT MAX(trade_date) FROM daily_stock_changes
                ''')
                latest_date = cursor.fetchone()[0]
                
                # 获取最新日期的记录数
                if latest_date:
                    cursor.execute('''
                        SELECT COUNT(*) FROM daily_stock_changes 
                        WHERE trade_date = ?
                    ''', (latest_date,))
                    latest_count = cursor.fetchone()[0]
                    
                    # 计算数据新鲜度
                    today = datetime.now().strftime('%Y-%m-%d')
                    days_behind = (datetime.strptime(today, '%Y-%m-%d') - 
                                 datetime.strptime(latest_date, '%Y-%m-%d')).days
                    
                    # 检查市值数据完整性
                    cursor.execute('''
                        SELECT COUNT(*) FROM daily_stock_changes 
                        WHERE trade_date = ? AND total_market_cap > 0
                    ''', (latest_date,))
                    market_cap_count = cursor.fetchone()[0]
                    
                    return {
                        'latest_date': latest_date,
                        'latest_count': latest_count,
                        'days_behind': days_behind,
                        'market_cap_coverage': market_cap_count / latest_count * 100 if latest_count > 0 else 0,
                        'data_source': 'Tencent API',
                        'unified_collection': True
                    }
                else:
                    return {
                        'latest_date': None,
                        'latest_count': 0,
                        'days_behind': None,
                        'market_cap_coverage': 0,
                        'data_source': 'Tencent API',
                        'unified_collection': True
                    }
                    
        except Exception as e:
            logger.error(f"❌ 获取收集状态失败: {e}")
            return {
                'error': str(e),
                'data_source': 'Tencent API',
                'unified_collection': True
            }

# 全局实例
unified_collector: Optional[UnifiedTencentCollector] = None

def get_unified_collector(db_manager: DatabaseManager) -> UnifiedTencentCollector:
    """获取统一数据收集器实例"""
    global unified_collector
    
    if unified_collector is None:
        unified_collector = UnifiedTencentCollector(db_manager)
    
    return unified_collector