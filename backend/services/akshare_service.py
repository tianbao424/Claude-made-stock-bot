"""
AkShare数据服务封装模块
负责封装AkShare API调用，提供A股和港股数据获取功能
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import StockInfo, DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AkShareService:
    """AkShare数据服务封装类"""
    
    def __init__(self):
        """初始化AkShare服务"""
        # 使用统一的数据库路径
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
        self.db = DatabaseManager(db_path)
        
        # 尝试导入akshare
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
            logger.info("✅ AkShare模块加载成功")
        except ImportError:
            logger.error("❌ AkShare模块未安装，请运行: pip install akshare")
            self.ak = None
            self.available = False
    
    def _check_availability(self) -> bool:
        """检查AkShare是否可用"""
        if not self.available:
            logger.error("❌ AkShare服务不可用")
            return False
        return True
    
    def generate_pinyin(self, text: str) -> str:
        """生成拼音索引（简化版本）"""
        return text.lower().replace(" ", "")
    
    async def get_a_stock_list(self) -> List[Dict[str, Any]]:
        """获取A股股票列表"""
        if not self._check_availability():
            return []
        
        try:
            logger.info("🔄 正在获取A股股票列表...")
            
            # 获取沪深A股列表
            sh_stocks = self.ak.stock_info_sh_name_code()
            sz_stocks = self.ak.stock_info_sz_name_code()
            
            stocks = []
            
            # 处理上海A股
            for _, row in sh_stocks.iterrows():
                if pd.notna(row.get('证券代码')) and pd.notna(row.get('证券简称')):
                    stock_data = {
                        'symbol': str(row['证券代码']).zfill(6),
                        'name': str(row['证券简称']).strip(),
                        'short_name': str(row['证券简称']).strip(),
                        'market': 'SH',
                        'industry': str(row.get('行业', '其他')).strip() if pd.notna(row.get('行业')) else '其他'
                    }
                    stocks.append(stock_data)
            
            # 处理深圳A股
            for _, row in sz_stocks.iterrows():
                if pd.notna(row.get('A股代码')) and pd.notna(row.get('A股简称')):
                    stock_data = {
                        'symbol': str(row['A股代码']).zfill(6),
                        'name': str(row['A股简称']).strip(),
                        'short_name': str(row['A股简称']).strip(),
                        'market': 'SZ',
                        'industry': str(row.get('行业大类', '其他')).strip() if pd.notna(row.get('行业大类')) else '其他'
                    }
                    stocks.append(stock_data)
            
            logger.info(f"✅ 获取到 {len(stocks)} 只A股")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ 获取A股列表失败: {e}")
            return []
    
    async def get_hk_stock_list(self) -> List[Dict[str, Any]]:
        """获取港股股票列表"""
        if not self._check_availability():
            return []
        
        try:
            logger.info("🔄 正在获取港股股票列表...")
            
            # 尝试多种方式获取港股数据
            try:
                # 方式1: 获取港股实时行情数据
                hk_stocks = self.ak.stock_hk_spot_em()
                if hk_stocks is not None and len(hk_stocks) > 0:
                    stocks = []
                    for _, row in hk_stocks.iterrows():
                        code = row.get('代码')
                        name = row.get('名称')
                        if pd.notna(code) and pd.notna(name):
                            # 港股代码格式化为5位数字
                            symbol = str(code).zfill(5)
                            name = str(name).strip()
                            
                            stock_data = {
                                'symbol': symbol,
                                'name': name,
                                'short_name': name,
                                'market': 'HK',
                                'industry': '其他'
                            }
                            stocks.append(stock_data)
                    
                    logger.info(f"✅ 获取到 {len(stocks)} 只港股")
                    return stocks
                    
            except Exception as e1:
                logger.warning(f"⚠️ 方式1获取港股失败: {e1}")
                
                # 方式2: 使用预设的主要港股列表
                logger.info("🔄 使用预设港股列表...")
                preset_hk_stocks = [
                    {'symbol': '00700', 'name': '腾讯控股', 'industry': '互联网'},
                    {'symbol': '09988', 'name': '阿里巴巴', 'industry': '互联网'},
                    {'symbol': '03690', 'name': '美团', 'industry': '互联网'},
                    {'symbol': '01810', 'name': '小米集团', 'industry': '手机'},
                    {'symbol': '09618', 'name': '京东集团', 'industry': '电商'},
                    {'symbol': '02318', 'name': '中国平安', 'industry': '保险'},
                    {'symbol': '01299', 'name': '友邦保险', 'industry': '保险'},
                    {'symbol': '00388', 'name': '香港交易所', 'industry': '金融'},
                    {'symbol': '00939', 'name': '建设银行', 'industry': '银行'},
                    {'symbol': '03988', 'name': '中国银行', 'industry': '银行'},
                    {'symbol': '01398', 'name': '工商银行', 'industry': '银行'},
                    {'symbol': '00857', 'name': '中国石油', 'industry': '石油'},
                    {'symbol': '00386', 'name': '中国石化', 'industry': '石油'},
                    {'symbol': '00883', 'name': '中国海洋石油', 'industry': '石油'},
                    {'symbol': '00941', 'name': '中国移动', 'industry': '通信'},
                    {'symbol': '00762', 'name': '中国联通', 'industry': '通信'},
                    {'symbol': '00728', 'name': '中国电信', 'industry': '通信'},
                    {'symbol': '01211', 'name': '比亚迪', 'industry': '汽车'},
                    {'symbol': '02015', 'name': '理想汽车', 'industry': '汽车'},
                    {'symbol': '09866', 'name': '蔚来', 'industry': '汽车'},
                    {'symbol': '09868', 'name': '小鹏汽车', 'industry': '汽车'},
                    {'symbol': '01024', 'name': '快手', 'industry': '互联网'},
                    {'symbol': '00175', 'name': '吉利汽车', 'industry': '汽车'},
                    {'symbol': '00016', 'name': '新鸿基地产', 'industry': '房地产'},
                    {'symbol': '01109', 'name': '华润置地', 'industry': '房地产'},
                    {'symbol': '01997', 'name': '九龙仓置业', 'industry': '房地产'},
                    {'symbol': '00003', 'name': '香港中华煤气', 'industry': '公用事业'},
                    {'symbol': '00002', 'name': '中电控股', 'industry': '公用事业'},
                    {'symbol': '00006', 'name': '电能实业', 'industry': '公用事业'},
                    {'symbol': '01093', 'name': '石药集团', 'industry': '医药'},
                ]
                
                stocks = []
                for stock_data in preset_hk_stocks:
                    formatted_stock = {
                        'symbol': stock_data['symbol'],
                        'name': stock_data['name'],
                        'short_name': stock_data['name'],
                        'market': 'HK',
                        'industry': stock_data['industry']
                    }
                    stocks.append(formatted_stock)
                
                logger.info(f"✅ 使用预设港股列表，共 {len(stocks)} 只股票")
                return stocks
            
        except Exception as e:
            logger.error(f"❌ 获取港股列表失败: {e}")
            return []
    
    async def import_a_stocks(self, limit: Optional[int] = None) -> int:
        """批量导入A股数据到数据库"""
        if not self._check_availability():
            return 0
        
        try:
            logger.info("🚀 开始批量导入A股数据...")
            
            stocks_data = await self.get_a_stock_list()
            if not stocks_data:
                logger.warning("⚠️ 未获取到A股数据")
                return 0
            
            # 如果设置了限制，则只导入前N只股票
            if limit:
                stocks_data = stocks_data[:limit]
                logger.info(f"📊 限制导入数量: {limit} 只股票")
            
            imported_count = 0
            for stock_data in stocks_data:
                try:
                    stock_info = StockInfo(
                        symbol=stock_data["symbol"],
                        name=stock_data["name"],
                        short_name=stock_data["short_name"],
                        market=stock_data["market"],
                        industry=stock_data["industry"],
                        pinyin=self.generate_pinyin(stock_data["name"])
                    )
                    
                    stock_id = self.db.add_stock_info(stock_info)
                    if stock_id:
                        imported_count += 1
                        if imported_count % 100 == 0:
                            logger.info(f"📈 已导入 {imported_count} 只A股...")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 跳过A股 {stock_data['symbol']}: {e}")
            
            logger.info(f"🎉 A股数据导入完成! 成功导入 {imported_count} 只股票")
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ A股批量导入失败: {e}")
            return 0
    
    async def import_hk_stocks(self, limit: Optional[int] = None) -> int:
        """批量导入港股数据到数据库"""
        if not self._check_availability():
            return 0
        
        try:
            logger.info("🚀 开始批量导入港股数据...")
            
            stocks_data = await self.get_hk_stock_list()
            if not stocks_data:
                logger.warning("⚠️ 未获取到港股数据")
                return 0
            
            # 如果设置了限制，则只导入前N只股票
            if limit:
                stocks_data = stocks_data[:limit]
                logger.info(f"📊 限制导入数量: {limit} 只港股")
            
            imported_count = 0
            for stock_data in stocks_data:
                try:
                    stock_info = StockInfo(
                        symbol=stock_data["symbol"],
                        name=stock_data["name"],
                        short_name=stock_data["short_name"],
                        market=stock_data["market"],
                        industry=stock_data["industry"],
                        pinyin=self.generate_pinyin(stock_data["name"])
                    )
                    
                    stock_id = self.db.add_stock_info(stock_info)
                    if stock_id:
                        imported_count += 1
                        if imported_count % 50 == 0:
                            logger.info(f"📈 已导入 {imported_count} 只港股...")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 跳过港股 {stock_data['symbol']}: {e}")
            
            logger.info(f"🎉 港股数据导入完成! 成功导入 {imported_count} 只股票")
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ 港股批量导入失败: {e}")
            return 0
    
    async def get_stock_realtime_data(self, symbol: str, market: str = "A") -> Optional[Dict[str, Any]]:
        """获取股票实时数据"""
        if not self._check_availability():
            return None
        
        try:
            logger.info(f"🔄 获取 {symbol} ({market}) 实时数据...")
            
            if market.upper() == "HK":
                # 港股实时数据
                try:
                    data = self.ak.stock_hk_spot_em()
                    # 港股代码可能需要去掉前导零
                    search_symbol = symbol.lstrip('0') if len(symbol) == 5 else symbol
                    stock_data = data[data['代码'].astype(str).str.contains(search_symbol, na=False)]
                    
                    if not stock_data.empty:
                        row = stock_data.iloc[0]
                        realtime_data = {
                            'symbol': symbol,
                            'name': str(row.get('名称', '')),
                            'current_price': float(row.get('最新价', 0)),
                            'change_amount': float(row.get('涨跌额', 0)),
                            'change_percent': float(row.get('涨跌幅', 0)),
                            'volume': int(row.get('成交量', 0)),
                            'turnover': float(row.get('成交额', 0)),
                            'open_price': float(row.get('今开', 0)),
                            'high_price': float(row.get('最高', 0)),
                            'low_price': float(row.get('最低', 0)),
                            'prev_close': float(row.get('昨收', 0)),
                            'market_cap': float(row.get('总市值', 0)),
                            'pe_ratio': float(row.get('市盈率', 0)) if row.get('市盈率') else 0.0,
                            'pb_ratio': float(row.get('市净率', 0)) if row.get('市净率') else 0.0,
                            'timestamp': datetime.now().isoformat()
                        }
                        logger.info(f"✅ 获取港股 {symbol} 实时数据成功")
                        return realtime_data
                        
                except Exception as hk_error:
                    logger.warning(f"⚠️ 港股API获取失败: {hk_error}")
                    
            else:
                # A股实时数据
                try:
                    data = self.ak.stock_zh_a_spot_em()
                    stock_data = data[data['代码'] == symbol]
                    
                    if not stock_data.empty:
                        row = stock_data.iloc[0]
                        realtime_data = {
                            'symbol': symbol,
                            'name': str(row.get('名称', '')),
                            'current_price': float(row.get('最新价', 0)),
                            'change_amount': float(row.get('涨跌额', 0)),
                            'change_percent': float(row.get('涨跌幅', 0)),
                            'volume': int(row.get('成交量', 0)),
                            'turnover': float(row.get('成交额', 0)),
                            'open_price': float(row.get('今开', 0)),
                            'high_price': float(row.get('最高', 0)),
                            'low_price': float(row.get('最低', 0)),
                            'prev_close': float(row.get('昨收', 0)),
                            'market_cap': float(row.get('总市值', 0)),
                            'pe_ratio': float(row.get('市盈率', 0)) if row.get('市盈率') else 0.0,
                            'pb_ratio': float(row.get('市净率', 0)) if row.get('市净率') else 0.0,
                            'timestamp': datetime.now().isoformat()
                        }
                        logger.info(f"✅ 获取A股 {symbol} 实时数据成功")
                        return realtime_data
                        
                except Exception as a_error:
                    logger.warning(f"⚠️ A股API获取失败: {a_error}")
            
            # 如果API获取失败，生成模拟数据用于测试
            logger.info(f"📊 生成 {symbol} 模拟实时数据...")
            import random
            base_price = 100 + random.uniform(-50, 200)
            change = random.uniform(-10, 10)
            
            mock_data = {
                'symbol': symbol,
                'name': f'模拟股票 {symbol}',
                'current_price': round(base_price, 2),
                'change_amount': round(change, 2),
                'change_percent': round((change / base_price) * 100, 2),
                'volume': random.randint(10000, 1000000),
                'turnover': round(base_price * random.randint(10000, 1000000), 2),
                'open_price': round(base_price + random.uniform(-5, 5), 2),
                'high_price': round(base_price + random.uniform(0, 10), 2),
                'low_price': round(base_price - random.uniform(0, 10), 2),
                'prev_close': round(base_price - change, 2),
                'market_cap': round(base_price * 1000000000, 2),
                'pe_ratio': round(random.uniform(5, 50), 2),
                'pb_ratio': round(random.uniform(0.5, 5), 2),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"✅ 生成模拟数据完成")
            return mock_data
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 实时数据失败: {e}")
        
        return None
    
    async def get_stock_history_data(self, symbol: str, market: str = "A", 
                                   start_date: Optional[str] = None, 
                                   end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        if not self._check_availability():
            return None
        
        try:
            if market.upper() == "HK":
                # 港股历史数据
                data = self.ak.stock_hk_daily(symbol=symbol, adjust="")
            else:
                # A股历史数据
                data = self.ak.stock_zh_a_daily(symbol=symbol, start_date=start_date, end_date=end_date, adjust="")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 历史数据失败: {e}")
            return None

# 全局实例
akshare_service = AkShareService()

# 测试和管理函数
async def test_akshare_connection():
    """测试AkShare连接"""
    service = AkShareService()
    
    if not service.available:
        print("❌ AkShare不可用，请先安装: pip install akshare")
        return False
    
    print("✅ AkShare连接正常")
    
    # 测试获取少量A股数据
    print("🔄 测试获取A股数据...")
    a_stocks = await service.get_a_stock_list()
    print(f"📊 可获取 {len(a_stocks)} 只A股")
    
    # 测试获取少量港股数据
    print("🔄 测试获取港股数据...")
    hk_stocks = await service.get_hk_stock_list()
    print(f"📊 可获取 {len(hk_stocks)} 只港股")
    
    return True

async def main():
    """主测试函数"""
    print("🧪 AkShare服务测试")
    
    # 测试连接
    if await test_akshare_connection():
        service = AkShareService()
        
        # 检查当前数据库状态
        count = service.db.get_stock_info_count()
        print(f"📊 当前数据库中股票数量: {count}")
        
        # 询问是否导入数据
        print("\n🤔 是否要导入股票数据？")
        print("1. 导入100只A股 (测试)")
        print("2. 导入50只港股 (测试)")
        print("3. 导入全部A股 (耗时较长)")
        print("4. 导入全部港股 (耗时较长)")
        print("0. 跳过导入")
        
        # 在实际应用中可以根据需要选择导入策略

if __name__ == "__main__":
    asyncio.run(main())