"""
混合数据采集服务
- 使用AkShare获取股票基础信息和列表
- 使用新浪API获取实时行情数据
- 不依赖本地缓存，直接获取最新数据
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sqlite3

from database import DatabaseManager, DailyStockChange, StockInfo
from services.sina_realtime_service import sina_realtime_service, SinaStockData
from services.smart_data_source_manager import smart_data_source_manager, DataSourceType

logger = logging.getLogger(__name__)

@dataclass
class CollectionResult:
    """数据采集结果"""
    success: bool
    total_stocks: int
    collected_stocks: int
    errors: List[str]
    execution_time: float
    data_source: str

class HybridDataCollector:
    """混合数据采集器"""
    
    def __init__(self):
        # 使用统一的数据库路径
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
        self.db = DatabaseManager(db_path)
        
    async def collect_stock_list(self) -> int:
        """使用AkShare收集股票列表数据"""
        logger.info("📋 开始收集股票基础信息...")
        
        try:
            import akshare as ak
            import asyncio
            
            # 并行获取各市场股票列表
            loop = asyncio.get_event_loop()
            
            tasks = [
                loop.run_in_executor(None, ak.stock_info_sh_name_code),  # 上海
                loop.run_in_executor(None, ak.stock_info_sz_name_code),  # 深圳
            ]
            
            try:
                # 尝试获取北京
                tasks.append(loop.run_in_executor(None, ak.stock_info_bj_name_code))
            except:
                logger.warning("北京股票列表接口不可用")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            imported_count = 0
            
            # 处理上海股票
            if not isinstance(results[0], Exception) and not results[0].empty:
                sh_stocks = results[0]
                for _, row in sh_stocks.iterrows():
                    if self._add_stock_info(row, 'SH'):
                        imported_count += 1
                logger.info(f"✅ 导入上海股票: {len(sh_stocks)} 只")
            
            # 处理深圳股票  
            if not isinstance(results[1], Exception) and not results[1].empty:
                sz_stocks = results[1]
                for _, row in sz_stocks.iterrows():
                    if self._add_stock_info(row, 'SZ'):
                        imported_count += 1
                logger.info(f"✅ 导入深圳股票: {len(sz_stocks)} 只")
            
            # 处理北京股票
            if len(results) > 2 and not isinstance(results[2], Exception) and not results[2].empty:
                bj_stocks = results[2]
                for _, row in bj_stocks.iterrows():
                    if self._add_stock_info(row, 'BJ'):
                        imported_count += 1
                logger.info(f"✅ 导入北京股票: {len(bj_stocks)} 只")
            
            logger.info(f"🎉 股票基础信息收集完成: {imported_count} 只股票")
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ 股票列表收集失败: {e}")
            return 0
    
    def _add_stock_info(self, row: Any, market: str) -> bool:
        """添加股票信息到数据库"""
        try:
            # 不同市场的字段名可能不同
            if market == 'SH':
                symbol = str(row.get('证券代码', ''))
                name = str(row.get('证券简称', ''))
            elif market == 'SZ':
                symbol = str(row.get('A股代码', ''))
                name = str(row.get('A股简称', ''))
            elif market == 'BJ':
                symbol = str(row.get('证券代码', ''))
                name = str(row.get('证券简称', ''))
            else:
                return False
            
            if not symbol or not name:
                return False
            
            stock_info = StockInfo(
                symbol=symbol,
                name=name,
                short_name=name,
                market=market,
                industry="",  # 可以后续补充
                pinyin=self._generate_pinyin(name)
            )
            
            stock_id = self.db.add_stock_info(stock_info)
            return stock_id is not None
            
        except Exception as e:
            logger.debug(f"添加股票信息失败: {e}")
            return False
    
    def _generate_pinyin(self, text: str) -> str:
        """生成拼音索引（简化版本）"""
        return text.lower().replace(" ", "")
    
    async def collect_realtime_data(self, trade_date: Optional[str] = None) -> CollectionResult:
        """使用新浪API收集实时行情数据"""
        start_time = time.time()
        
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"📡 开始收集实时行情数据 (交易日期: {trade_date})...")
        
        # 检查新浪API可用性
        if not await sina_realtime_service.test_connectivity():
            error_msg = "新浪财经API不可用"
            logger.error(f"❌ {error_msg}")
            return CollectionResult(
                success=False,
                total_stocks=0,
                collected_stocks=0,
                errors=[error_msg],
                execution_time=time.time() - start_time,
                data_source="sina_realtime"
            )
        
        # 从数据库获取股票列表
        stock_list = self._get_stock_list()
        if not stock_list:
            error_msg = "没有找到股票列表数据"
            logger.error(f"❌ {error_msg}")
            return CollectionResult(
                success=False,
                total_stocks=0,
                collected_stocks=0,
                errors=[error_msg],
                execution_time=time.time() - start_time,
                data_source="sina_realtime"
            )
        
        logger.info(f"📊 准备收集 {len(stock_list)} 只股票的实时数据...")
        
        # 使用新浪API批量获取数据
        sina_data = await sina_realtime_service.get_batch_data(stock_list, batch_size=100)
        
        # 转换为数据库格式并保存
        stocks_data = []
        for data in sina_data:
            try:
                stock_change = DailyStockChange(
                    stock_code=data.code,
                    trade_date=trade_date,
                    change_percent=data.change_percent,
                    close_price=data.current_price,
                    open_price=data.open_price,
                    high_price=data.high_price,
                    low_price=data.low_price,
                    volume=data.volume,
                    turnover=data.turnover,
                    market=data.market,
                    created_at=datetime.now().isoformat()
                )
                stocks_data.append(stock_change)
            except Exception as e:
                logger.debug(f"转换股票数据失败 {data.code}: {e}")
                continue
        
        # 保存到数据库
        saved_count = await self._save_daily_changes(stocks_data, trade_date)
        
        execution_time = time.time() - start_time
        success = saved_count > 0
        
        logger.info(f"✅ 实时数据采集完成: {saved_count}/{len(stock_list)} 只股票, 用时 {execution_time:.2f}s")
        
        return CollectionResult(
            success=success,
            total_stocks=len(stock_list),
            collected_stocks=saved_count,
            errors=[],
            execution_time=execution_time,
            data_source="sina_realtime"
        )
    
    def _get_stock_list(self) -> List[Dict[str, str]]:
        """从数据库获取股票列表"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, market FROM stock_info 
                    WHERE market IN ('SH', 'SZ')
                    ORDER BY symbol
                ''')
                
                results = cursor.fetchall()
                return [{'code': symbol, 'market': market} for symbol, market in results]
                
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    async def _save_daily_changes(self, stocks_data: List[DailyStockChange], trade_date: str) -> int:
        """保存每日涨跌数据"""
        if not stocks_data:
            return 0
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # 清理当天的旧数据
                cursor.execute('''
                    DELETE FROM daily_stock_changes 
                    WHERE trade_date = ?
                ''', (trade_date,))
                
                # 插入新数据
                saved_count = 0
                for stock_data in stocks_data:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO daily_stock_changes 
                            (stock_code, trade_date, change_percent, close_price, open_price, 
                             high_price, low_price, volume, turnover, market, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_data.stock_code,
                            stock_data.trade_date,
                            stock_data.change_percent,
                            stock_data.close_price,
                            stock_data.open_price,
                            stock_data.high_price,
                            stock_data.low_price,
                            stock_data.volume,
                            stock_data.turnover,
                            stock_data.market,
                            stock_data.created_at
                        ))
                        saved_count += 1
                    except Exception as e:
                        logger.debug(f"保存股票数据失败 {stock_data.stock_code}: {e}")
                        continue
                
                conn.commit()
                logger.info(f"💾 保存每日涨跌数据: {saved_count} 只股票")
                return saved_count
                
        except Exception as e:
            logger.error(f"保存每日涨跌数据失败: {e}")
            return 0
    
    async def full_data_collection(self) -> Dict[str, Any]:
        """完整数据采集流程"""
        logger.info("🚀 开始完整数据采集流程...")
        
        start_time = time.time()
        results = {
            'stock_list_count': 0,
            'realtime_result': None,
            'total_time': 0,
            'success': False
        }
        
        try:
            # 1. 更新股票列表
            stock_count = await self.collect_stock_list()
            results['stock_list_count'] = stock_count
            
            if stock_count > 0:
                # 2. 收集实时数据
                realtime_result = await self.collect_realtime_data()
                results['realtime_result'] = realtime_result
                results['success'] = realtime_result.success
            
            results['total_time'] = time.time() - start_time
            
            if results['success']:
                logger.info(f"🎉 完整数据采集成功! 总用时: {results['total_time']:.2f}s")
            else:
                logger.warning(f"⚠️ 数据采集部分失败, 总用时: {results['total_time']:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 完整数据采集失败: {e}")
            results['total_time'] = time.time() - start_time
            return results

# 全局实例
hybrid_data_collector = HybridDataCollector()