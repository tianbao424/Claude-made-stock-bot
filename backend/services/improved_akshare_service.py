"""
改进的AkShare数据服务 - 支持多数据源备份机制
解决API连接不稳定问题，提供数据状态监控
"""
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import pandas as pd
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import StockInfo, DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    """数据源枚举"""
    EASTMONEY_A = "eastmoney_a"      # 东方财富A股
    EASTMONEY_HK = "eastmoney_hk"    # 东方财富港股
    SINA_A = "sina_a"                # 新浪A股
    SINA_HK = "sina_hk"              # 新浪港股
    INDIVIDUAL_EM = "individual_em"   # 东方财富个股信息
    MOCK = "mock"                    # 模拟数据

@dataclass
class DataSourceStatus:
    """数据源状态"""
    source: DataSource
    available: bool
    last_check: datetime
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None

@dataclass
class StockRealtimeData:
    """股票实时数据标准化格式"""
    symbol: str
    name: str
    current_price: float
    change_amount: float
    change_percent: float
    volume: int
    turnover: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    market_cap: float
    pe_ratio: float
    pb_ratio: float
    timestamp: str
    data_source: DataSource  # 新增：数据来源
    is_simulated: bool = False  # 新增：是否为模拟数据

class ImprovedAkShareService:
    """改进的AkShare数据服务类"""
    
    def __init__(self):
        """初始化服务"""
        # 数据库管理
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
        self.db = DatabaseManager(db_path)
        
        # AkShare模块
        try:
            import akshare as ak
            self.ak = ak
            self.ak_available = True
            logger.info("✅ AkShare模块加载成功")
        except ImportError:
            logger.error("❌ AkShare模块未安装")
            self.ak = None
            self.ak_available = False
        
        # 数据源状态管理
        self.data_source_status: Dict[DataSource, DataSourceStatus] = {}
        self._initialize_data_sources()
    
    def _initialize_data_sources(self):
        """初始化数据源状态"""
        sources = [
            DataSource.EASTMONEY_A,
            DataSource.EASTMONEY_HK, 
            DataSource.SINA_A,
            DataSource.SINA_HK,
            DataSource.INDIVIDUAL_EM,
            DataSource.MOCK
        ]
        
        for source in sources:
            self.data_source_status[source] = DataSourceStatus(
                source=source,
                available=False,
                last_check=datetime.now()
            )
    
    async def _test_data_source(self, source: DataSource) -> DataSourceStatus:
        """测试单个数据源的可用性"""
        start_time = time.time()
        status = DataSourceStatus(
            source=source,
            available=False,
            last_check=datetime.now()
        )
        
        if not self.ak_available:
            status.error_message = "AkShare模块不可用"
            return status
        
        try:
            if source == DataSource.EASTMONEY_A:
                # 测试东方财富A股
                data = self.ak.stock_zh_a_spot_em()
                if data is not None and len(data) > 0:
                    status.available = True
                    
            elif source == DataSource.EASTMONEY_HK:
                # 测试东方财富港股
                data = self.ak.stock_hk_spot_em() 
                if data is not None and len(data) > 0:
                    status.available = True
                    
            elif source == DataSource.SINA_A:
                # 测试新浪A股
                data = self.ak.stock_zh_a_spot()
                if data is not None and len(data) > 0:
                    status.available = True
                    
            elif source == DataSource.SINA_HK:
                # 测试新浪港股
                data = self.ak.stock_hk_spot()
                if data is not None and len(data) > 0:
                    status.available = True
                    
            elif source == DataSource.INDIVIDUAL_EM:
                # 测试东方财富个股信息
                data = self.ak.stock_individual_info_em(symbol="000001")
                if data is not None and len(data) > 0:
                    status.available = True
                    
            elif source == DataSource.MOCK:
                # 模拟数据总是可用
                status.available = True
            
            # 记录响应时间
            response_time = int((time.time() - start_time) * 1000)
            status.response_time_ms = response_time
            
        except Exception as e:
            status.error_message = str(e)[:100]
            logger.warning(f"⚠️ 数据源 {source.value} 测试失败: {status.error_message}")
        
        return status
    
    async def check_all_data_sources(self) -> Dict[DataSource, DataSourceStatus]:
        """检查所有数据源状态"""
        logger.info("🔄 检查所有数据源状态...")
        
        # 并发测试所有数据源
        tasks = []
        for source in DataSource:
            if source != DataSource.MOCK:  # 跳过模拟数据，它总是可用的
                tasks.append(self._test_data_source(source))
        
        # 模拟数据总是可用
        mock_status = DataSourceStatus(
            source=DataSource.MOCK,
            available=True,
            last_check=datetime.now(),
            response_time_ms=1
        )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 更新状态
        source_index = 0
        for source in DataSource:
            if source == DataSource.MOCK:
                self.data_source_status[source] = mock_status
            else:
                if source_index < len(results) and not isinstance(results[source_index], Exception):
                    self.data_source_status[source] = results[source_index]
                else:
                    # 处理异常情况
                    self.data_source_status[source] = DataSourceStatus(
                        source=source,
                        available=False,
                        last_check=datetime.now(),
                        error_message="测试超时或异常"
                    )
                source_index += 1
        
        # 记录结果
        available_sources = [s.source.value for s in self.data_source_status.values() if s.available]
        logger.info(f"✅ 可用数据源: {available_sources}")
        
        return self.data_source_status
    
    def get_data_source_status(self) -> Dict[DataSource, DataSourceStatus]:
        """获取数据源状态"""
        return self.data_source_status.copy()
    
    async def _get_realtime_data_from_source(
        self, 
        symbol: str, 
        market: str, 
        source: DataSource
    ) -> Optional[StockRealtimeData]:
        """从指定数据源获取实时数据"""
        
        try:
            if source == DataSource.SINA_A and market.upper() == "A":
                # 新浪A股数据
                data = self.ak.stock_zh_a_spot()
                stock_data = data[data['代码'] == symbol]
                
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    return StockRealtimeData(
                        symbol=symbol,
                        name=str(row.get('名称', '')),
                        current_price=float(row.get('最新价', 0)),
                        change_amount=float(row.get('涨跌额', 0)),
                        change_percent=float(row.get('涨跌幅', 0)),
                        volume=int(row.get('成交量', 0)),
                        turnover=float(row.get('成交额', 0)),
                        open_price=float(row.get('今开', 0)),
                        high_price=float(row.get('最高', 0)),
                        low_price=float(row.get('最低', 0)),
                        prev_close=float(row.get('昨收', 0)),
                        market_cap=0.0,  # 新浪数据可能没有这个字段
                        pe_ratio=0.0,
                        pb_ratio=0.0,
                        timestamp=datetime.now().isoformat(),
                        data_source=source
                    )
                    
            elif source == DataSource.SINA_HK and market.upper() == "HK":
                # 新浪港股数据（需下载全市场数据，较慢）
                logger.info(f"  ⏳ 下载港股全市场数据中...")
                data = self.ak.stock_hk_spot()
                
                if data is None or data.empty:
                    logger.warning(f"  ❌ 新浪港股数据为空")
                    return None
                
                # 港股代码处理：API返回的是完整5位代码（带前导零），直接使用原代码查找
                search_symbol = symbol  # 直接使用原始代码，如 "02543"
                logger.info(f"  🔍 查找港股代码: {search_symbol}")
                stock_data = data[data['代码'].astype(str) == search_symbol]
                
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    logger.info(f"  ✅ 找到港股数据: {row.get('中文名称', '')}")
                    return StockRealtimeData(
                        symbol=symbol,
                        name=str(row.get('中文名称', '')),
                        current_price=float(row.get('最新价', 0)),
                        change_amount=float(row.get('涨跌额', 0)),
                        change_percent=float(row.get('涨跌幅', 0)),
                        volume=int(row.get('成交量', 0)),
                        turnover=float(row.get('成交额', 0)),
                        open_price=float(row.get('开盘价', 0)),
                        high_price=float(row.get('最高价', 0)),
                        low_price=float(row.get('最低价', 0)),
                        prev_close=float(row.get('昨收价', 0)),
                        market_cap=0.0,
                        pe_ratio=0.0,
                        pb_ratio=0.0,
                        timestamp=datetime.now().isoformat(),
                        data_source=source
                    )
                else:
                    logger.warning(f"  ❌ 未找到港股 {search_symbol} 的数据")
                    
            elif source == DataSource.INDIVIDUAL_EM:
                # 东方财富个股信息
                data = self.ak.stock_individual_info_em(symbol=symbol)
                if data is not None and len(data) > 0:
                    # 解析个股信息数据格式
                    info_dict = {}
                    for _, row in data.iterrows():
                        info_dict[row['item']] = row['value']
                    
                    # 从个股信息中提取股票数据
                    current_price = float(info_dict.get('最新', 0))
                    if current_price > 0:
                        return StockRealtimeData(
                            symbol=symbol,
                            name=info_dict.get('股票简称', f'股票{symbol}'),
                            current_price=current_price,
                            change_amount=float(info_dict.get('涨跌额', 0)),
                            change_percent=float(info_dict.get('涨跌幅', 0)),
                            volume=int(float(info_dict.get('成交量', 0))),
                            turnover=float(info_dict.get('成交额', 0)),
                            open_price=float(info_dict.get('今开', 0)),
                            high_price=float(info_dict.get('最高', 0)),
                            low_price=float(info_dict.get('最低', 0)),
                            prev_close=float(info_dict.get('昨收', 0)),
                            market_cap=float(info_dict.get('总市值', 0)),
                            pe_ratio=float(info_dict.get('市盈率', 0)),
                            pb_ratio=float(info_dict.get('市净率', 0)),
                            timestamp=datetime.now().isoformat(),
                            data_source=source
                        )
                        
            elif source == DataSource.EASTMONEY_A and market.upper() == "A":
                # 东方财富A股（原有逻辑，可能失败）
                data = self.ak.stock_zh_a_spot_em()
                stock_data = data[data['代码'] == symbol]
                
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    return StockRealtimeData(
                        symbol=symbol,
                        name=str(row.get('名称', '')),
                        current_price=float(row.get('最新价', 0)),
                        change_amount=float(row.get('涨跌额', 0)),
                        change_percent=float(row.get('涨跌幅', 0)),
                        volume=int(row.get('成交量', 0)),
                        turnover=float(row.get('成交额', 0)),
                        open_price=float(row.get('今开', 0)),
                        high_price=float(row.get('最高', 0)),
                        low_price=float(row.get('最低', 0)),
                        prev_close=float(row.get('昨收', 0)),
                        market_cap=float(row.get('总市值', 0)),
                        pe_ratio=float(row.get('市盈率', 0)) if row.get('市盈率') else 0.0,
                        pb_ratio=float(row.get('市净率', 0)) if row.get('市净率') else 0.0,
                        timestamp=datetime.now().isoformat(),
                        data_source=source
                    )
                    
        except Exception as e:
            logger.warning(f"⚠️ 从数据源 {source.value} 获取 {symbol} 数据失败: {str(e)[:100]}")
            return None
        
        return None
    
    def _generate_mock_data(self, symbol: str) -> StockRealtimeData:
        """生成模拟数据"""
        import random
        
        base_price = 100 + random.uniform(-50, 200)
        change = random.uniform(-10, 10)
        
        return StockRealtimeData(
            symbol=symbol,
            name=f'模拟股票 {symbol}',
            current_price=round(base_price, 2),
            change_amount=round(change, 2),
            change_percent=round((change / base_price) * 100, 2),
            volume=random.randint(10000, 1000000),
            turnover=round(base_price * random.randint(10000, 1000000), 2),
            open_price=round(base_price + random.uniform(-5, 5), 2),
            high_price=round(base_price + random.uniform(0, 10), 2),
            low_price=round(base_price - random.uniform(0, 10), 2),
            prev_close=round(base_price - change, 2),
            market_cap=round(base_price * 1000000000, 2),
            pe_ratio=round(random.uniform(5, 50), 2),
            pb_ratio=round(random.uniform(0.5, 5), 2),
            timestamp=datetime.now().isoformat(),
            data_source=DataSource.MOCK,
            is_simulated=True
        )
    
    async def get_stock_realtime_data_enhanced(
        self, 
        symbol: str, 
        market: str = "A"
    ) -> Optional[StockRealtimeData]:
        """
        增强版股票实时数据获取，优先使用高效的单股查询
        """
        logger.info(f"🔄 获取 {symbol} ({market}) 实时数据...")
        
        # 优先使用效率最高的数据源（避免全市场数据下载）
        if market.upper() == "A":
            # A股：优先使用东方财富个股信息（最快，无需下载全市场数据）
            priority_sources = [
                DataSource.INDIVIDUAL_EM,   # 首选：东方财富个股信息（单股查询）
                DataSource.MOCK,           # 备选：模拟数据（兜底）
            ]
        else:  # HK
            # 港股：由于需要下载全市场数据较慢，提供选择性支持
            # 生产环境可配置为优先使用真实数据
            use_real_hk_data = True  # 可配置项：是否使用真实港股数据
            
            if use_real_hk_data:
                priority_sources = [
                    DataSource.SINA_HK,        # 首选：新浪港股数据（需下载全市场）
                    DataSource.EASTMONEY_HK,   # 备选：东方财富港股
                    DataSource.MOCK,           # 兜底：模拟数据
                ]
            else:
                priority_sources = [
                    DataSource.MOCK,           # 仅模拟数据（快速响应）
                ]
        
        # 按优先级尝试获取数据
        for source in priority_sources:
            try:
                logger.info(f"  📡 使用数据源: {source.value}")
                data = await self._get_realtime_data_from_source(symbol, market, source)
                
                if data:
                    logger.info(f"  ✅ 获取成功 - 价格: {data.current_price}")
                    # 静默更新数据源状态（不记录详细日志）
                    self.data_source_status[source] = DataSourceStatus(
                        source=source,
                        available=True,
                        last_check=datetime.now()
                    )
                    return data
                    
            except Exception as e:
                logger.debug(f"  数据源 {source.value} 失败: {str(e)[:50]}")
                # 静默记录失败状态
                self.data_source_status[source] = DataSourceStatus(
                    source=source,
                    available=False,
                    last_check=datetime.now(),
                    error_message=str(e)[:100]
                )
        
        # 所有数据源都失败，使用模拟数据
        logger.info(f"📊 生成 {symbol} 模拟数据...")
        mock_data = self._generate_mock_data(symbol)
        return mock_data
    
    def get_data_source_summary(self) -> Dict[str, Any]:
        """获取数据源状态摘要"""
        summary = {
            'total_sources': len(self.data_source_status),
            'available_sources': sum(1 for s in self.data_source_status.values() if s.available),
            'last_check': max(s.last_check for s in self.data_source_status.values()).isoformat(),
            'sources': {}
        }
        
        for source, status in self.data_source_status.items():
            summary['sources'][source.value] = {
                'available': status.available,
                'last_check': status.last_check.isoformat(),
                'error_message': status.error_message,
                'response_time_ms': status.response_time_ms
            }
        
        return summary

# 全局实例
improved_akshare_service = ImprovedAkShareService()

# 测试函数
async def test_improved_service():
    """测试改进的服务"""
    print("🧪 测试改进的AkShare服务")
    
    # 检查数据源状态
    await improved_akshare_service.check_all_data_sources()
    status_summary = improved_akshare_service.get_data_source_summary()
    print(f"📊 数据源状态: {status_summary['available_sources']}/{status_summary['total_sources']} 可用")
    
    # 测试获取股票数据
    test_stocks = [
        ("000001", "A", "平安银行"),
        ("600519", "A", "贵州茅台"),
        ("00700", "HK", "腾讯控股"),
    ]
    
    for symbol, market, name in test_stocks:
        print(f"\n🔄 测试 {name} ({symbol})...")
        data = await improved_akshare_service.get_stock_realtime_data_enhanced(symbol, market)
        if data:
            print(f"✅ 获取成功 - 数据源: {data.data_source.value}, 价格: {data.current_price}")
            if data.is_simulated:
                print("  ⚠️ 注意: 这是模拟数据")
        else:
            print("❌ 获取失败")

if __name__ == "__main__":
    asyncio.run(test_improved_service())