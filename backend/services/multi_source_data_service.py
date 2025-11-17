#!/usr/bin/env python3
"""
多数据源融合服务
整合BaoStock、EFinance、AkShare等多个数据源，提供可靠的市值数据获取
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """数据源类型"""
    BAOSTOCK = "baostock"
    EFINANCE = "efinance" 
    AKSHARE = "akshare"
    TUSHARE = "tushare"
    CACHE = "cache"

@dataclass
class DataSourceStatus:
    """数据源状态"""
    source_type: DataSourceType
    available: bool
    last_check: datetime
    error_message: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0

@dataclass
class StockMarketData:
    """股票市值数据标准格式"""
    symbol: str
    name: str
    market_cap: Optional[float] = None
    circulating_market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    current_price: Optional[float] = None
    data_source: DataSourceType = DataSourceType.CACHE
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class MultiSourceDataService:
    """多数据源数据服务"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.data_sources_status: Dict[DataSourceType, DataSourceStatus] = {}
        self._initialize_sources()
        
        # 数据源优先级（按可靠性排序）
        self.source_priority = [
            DataSourceType.BAOSTOCK,    # 最稳定，免费
            DataSourceType.EFINANCE,    # 较新，可能绕过限制
            DataSourceType.AKSHARE,     # 备用
            DataSourceType.TUSHARE,     # 需要token
        ]
    
    def _initialize_sources(self):
        """初始化数据源状态"""
        for source in DataSourceType:
            self.data_sources_status[source] = DataSourceStatus(
                source_type=source,
                available=False,
                last_check=datetime.now()
            )
    
    async def check_baostock_availability(self) -> bool:
        """检查BaoStock可用性"""
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                bs.logout()
                self.data_sources_status[DataSourceType.BAOSTOCK].available = True
                self.data_sources_status[DataSourceType.BAOSTOCK].error_message = None
                return True
            else:
                self.data_sources_status[DataSourceType.BAOSTOCK].error_message = lg.error_msg
                return False
        except Exception as e:
            self.data_sources_status[DataSourceType.BAOSTOCK].error_message = str(e)
            return False
    
    async def check_efinance_availability(self) -> bool:
        """检查EFinance可用性"""
        try:
            import efinance as ef
            # 尝试获取一个简单的数据
            stock_info = ef.stock.get_realtime_quotes()
            if stock_info is not None and len(stock_info) > 0:
                self.data_sources_status[DataSourceType.EFINANCE].available = True
                self.data_sources_status[DataSourceType.EFINANCE].error_message = None
                return True
            else:
                self.data_sources_status[DataSourceType.EFINANCE].error_message = "返回空数据"
                return False
        except ImportError:
            self.data_sources_status[DataSourceType.EFINANCE].error_message = "包未安装"
            return False
        except Exception as e:
            self.data_sources_status[DataSourceType.EFINANCE].error_message = str(e)
            return False
    
    async def check_akshare_availability(self) -> bool:
        """检查AkShare可用性"""
        try:
            import akshare as ak
            # 测试一个简单的功能
            trade_dates = ak.tool_trade_date_hist_sina()
            if trade_dates is not None and len(trade_dates) > 0:
                self.data_sources_status[DataSourceType.AKSHARE].available = True
                self.data_sources_status[DataSourceType.AKSHARE].error_message = None
                return True
            else:
                self.data_sources_status[DataSourceType.AKSHARE].error_message = "功能测试失败"
                return False
        except Exception as e:
            self.data_sources_status[DataSourceType.AKSHARE].error_message = str(e)
            return False
    
    async def check_all_sources(self) -> Dict[DataSourceType, bool]:
        """检查所有数据源可用性"""
        logger.info("🔍 检查所有数据源可用性...")
        
        results = {}
        
        # 并发检查所有数据源
        checks = [
            self.check_baostock_availability(),
            self.check_efinance_availability(), 
            self.check_akshare_availability()
        ]
        
        check_results = await asyncio.gather(*checks, return_exceptions=True)
        
        results[DataSourceType.BAOSTOCK] = check_results[0] if not isinstance(check_results[0], Exception) else False
        results[DataSourceType.EFINANCE] = check_results[1] if not isinstance(check_results[1], Exception) else False
        results[DataSourceType.AKSHARE] = check_results[2] if not isinstance(check_results[2], Exception) else False
        
        # 更新状态时间戳
        for source in results:
            self.data_sources_status[source].last_check = datetime.now()
        
        available_count = sum(1 for available in results.values() if available)
        logger.info(f"✅ 数据源检查完成: {available_count}/{len(results)} 个可用")
        
        return results
    
    async def get_stock_market_data_from_baostock(self, symbol: str) -> Optional[StockMarketData]:
        """从BaoStock获取股票市值数据"""
        try:
            import baostock as bs
            
            # 登录
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"BaoStock登录失败: {lg.error_msg}")
                return None
            
            try:
                # BaoStock的股票代码格式需要添加市场前缀
                if symbol.startswith('6'):
                    bs_symbol = f'sh.{symbol}'
                elif symbol.startswith(('0', '3')):
                    bs_symbol = f'sz.{symbol}'
                else:
                    bs_symbol = symbol
                
                # 获取最近的交易数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                
                rs = bs.query_history_k_data_plus(
                    bs_symbol,
                    'date,code,close,volume,amount',
                    start_date=start_date,
                    end_date=end_date,
                    frequency='d'
                )
                
                if rs.error_code == '0':
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                    
                    if data_list:
                        # 取最新的数据
                        latest_data = data_list[-1]
                        current_price = float(latest_data[2]) if latest_data[2] else None
                        
                        # BaoStock不直接提供市值，需要通过其他方式计算或获取
                        # 这里返回基础数据，市值需要通过股本计算
                        return StockMarketData(
                            symbol=symbol,
                            name=f"股票{symbol}",  # BaoStock需要额外查询获取名称
                            current_price=current_price,
                            data_source=DataSourceType.BAOSTOCK,
                            timestamp=datetime.now()
                        )
                    else:
                        logger.warning(f"BaoStock未获取到{symbol}的数据")
                        return None
                else:
                    logger.error(f"BaoStock查询失败: {rs.error_msg}")
                    return None
                    
            finally:
                bs.logout()
                
        except Exception as e:
            logger.error(f"BaoStock获取{symbol}数据失败: {e}")
            return None
    
    async def get_stock_market_data_from_efinance(self, symbol: str) -> Optional[StockMarketData]:
        """从EFinance获取股票市值数据"""
        try:
            import efinance as ef
            
            # EFinance获取实时数据
            stock_info = ef.stock.get_realtime_quotes(symbol)
            
            if stock_info and len(stock_info) > 0:
                data = stock_info[0] if isinstance(stock_info, list) else stock_info
                
                return StockMarketData(
                    symbol=symbol,
                    name=data.get('股票名称', f"股票{symbol}"),
                    market_cap=data.get('总市值'),
                    circulating_market_cap=data.get('流通市值'),
                    current_price=data.get('最新价'),
                    pe_ratio=data.get('市盈率'),
                    pb_ratio=data.get('市净率'),
                    data_source=DataSourceType.EFINANCE,
                    timestamp=datetime.now()
                )
            else:
                logger.warning(f"EFinance未获取到{symbol}的数据")
                return None
                
        except ImportError:
            logger.error("EFinance包未安装")
            return None
        except Exception as e:
            logger.error(f"EFinance获取{symbol}数据失败: {e}")
            return None
    
    async def get_stock_market_data_multi_source(self, symbol: str) -> Optional[StockMarketData]:
        """多数据源获取股票市值数据"""
        logger.debug(f"🔍 多源获取{symbol}的市值数据...")
        
        # 按优先级尝试各个数据源
        for source_type in self.source_priority:
            if not self.data_sources_status[source_type].available:
                continue
                
            try:
                logger.debug(f"🔄 尝试使用{source_type.value}获取{symbol}数据...")
                
                if source_type == DataSourceType.BAOSTOCK:
                    data = await self.get_stock_market_data_from_baostock(symbol)
                elif source_type == DataSourceType.EFINANCE:
                    data = await self.get_stock_market_data_from_efinance(symbol)
                else:
                    # 其他数据源的实现
                    continue
                
                if data and (data.market_cap or data.current_price):
                    self.data_sources_status[source_type].success_count += 1
                    logger.debug(f"✅ {source_type.value}成功获取{symbol}数据")
                    return data
                else:
                    logger.debug(f"⚠️ {source_type.value}未获取到{symbol}有效数据")
                    
            except Exception as e:
                self.data_sources_status[source_type].failure_count += 1
                logger.warning(f"❌ {source_type.value}获取{symbol}失败: {e}")
                continue
        
        logger.warning(f"⚠️ 所有数据源都无法获取{symbol}的数据")
        return None
    
    async def batch_update_market_cap_data(self, symbols: List[str], max_concurrent: int = 5) -> Dict[str, Any]:
        """批量更新市值数据"""
        logger.info(f"🚀 开始批量更新 {len(symbols)} 只股票的市值数据...")
        
        # 先检查数据源可用性
        await self.check_all_sources()
        
        # 计算可用数据源数量
        available_sources = sum(1 for status in self.data_sources_status.values() if status.available)
        if available_sources == 0:
            return {
                'success': False,
                'error': '没有可用的数据源',
                'updated_count': 0,
                'failed_count': len(symbols)
            }
        
        logger.info(f"📊 可用数据源: {available_sources} 个")
        
        # 信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def update_single_stock(symbol: str) -> Tuple[str, bool, Optional[str]]:
            async with semaphore:
                try:
                    data = await self.get_stock_market_data_multi_source(symbol)
                    if data and data.market_cap:
                        # 更新到数据库
                        # 这里需要实现数据库更新逻辑
                        return symbol, True, None
                    else:
                        return symbol, False, "未获取到有效数据"
                except Exception as e:
                    return symbol, False, str(e)
        
        # 并发执行更新
        tasks = [update_single_stock(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        updated_count = 0
        failed_count = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                errors.append(f"异常: {str(result)[:50]}")
            else:
                symbol, success, error = result
                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                    if error:
                        errors.append(f"{symbol}: {error}")
        
        logger.info(f"✅ 批量更新完成: 成功{updated_count}, 失败{failed_count}")
        
        return {
            'success': updated_count > 0,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'total_count': len(symbols),
            'errors': errors[:10],  # 只返回前10个错误
            'data_source_stats': {
                source.value: {
                    'available': status.available,
                    'success_count': status.success_count,
                    'failure_count': status.failure_count
                }
                for source, status in self.data_sources_status.items()
            }
        }
    
    def get_data_source_report(self) -> Dict[str, Any]:
        """获取数据源状态报告"""
        return {
            'check_time': datetime.now().isoformat(),
            'sources': {
                source.value: {
                    'available': status.available,
                    'last_check': status.last_check.isoformat(),
                    'error_message': status.error_message,
                    'success_count': status.success_count,
                    'failure_count': status.failure_count,
                    'success_rate': (
                        status.success_count / (status.success_count + status.failure_count) * 100
                        if (status.success_count + status.failure_count) > 0 else 0
                    )
                }
                for source, status in self.data_sources_status.items()
            }
        }

# 创建全局实例
def get_multi_source_service(db_manager: DatabaseManager) -> MultiSourceDataService:
    """获取多数据源服务实例"""
    return MultiSourceDataService(db_manager)

# 测试函数
async def test_multi_source_service():
    """测试多数据源服务"""
    print("🧪 测试多数据源数据服务")
    print("=" * 50)
    
    # 初始化
    db_manager = DatabaseManager('stock_pool.db')
    service = get_multi_source_service(db_manager)
    
    # 检查数据源可用性
    print("🔍 检查数据源可用性...")
    availability = await service.check_all_sources()
    
    for source, available in availability.items():
        status = "✅ 可用" if available else "❌ 不可用"
        error = service.data_sources_status[source].error_message
        print(f"  {source.value}: {status}" + (f" ({error})" if error else ""))
    
    # 测试获取单只股票数据
    test_symbols = ['000001', '000002', '600000']
    print(f"\n📊 测试获取股票数据...")
    
    for symbol in test_symbols[:2]:  # 只测试前2只
        print(f"\n🔍 获取 {symbol} 数据:")
        data = await service.get_stock_market_data_multi_source(symbol)
        if data:
            print(f"  ✅ 成功: {data.name}, 价格: {data.current_price}, 数据源: {data.data_source.value}")
        else:
            print(f"  ❌ 失败")
    
    # 显示数据源报告
    print(f"\n📊 数据源状态报告:")
    report = service.get_data_source_report()
    for source_name, stats in report['sources'].items():
        print(f"  {source_name}: 可用={stats['available']}, "
              f"成功率={stats['success_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_multi_source_service())