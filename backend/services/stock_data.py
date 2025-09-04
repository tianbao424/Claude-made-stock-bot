"""
股票数据服务模块
负责从AkShare获取股票基础信息并导入数据库
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import StockInfo, DatabaseManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataService:
    """股票数据服务类"""
    
    def __init__(self):
        # 使用统一的数据库路径
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
        self.db = DatabaseManager(db_path)
        
    def generate_pinyin(self, text: str) -> str:
        """生成拼音索引（简化版本，后续可集成python-pinyin）"""
        # 简化版本：返回原文本作为索引
        # 未来可以集成 python-pinyin 库进行拼音转换
        return text.lower().replace(" ", "")
    
    async def import_sample_stocks(self) -> int:
        """导入样例股票数据"""
        try:
            logger.info("🚀 开始导入样例股票数据...")
            
            # 样例A股数据
            sample_stocks = [
                # 知名大盘股
                {"symbol": "000001", "name": "平安银行", "short_name": "平安银行", "market": "SZ", "industry": "银行"},
                {"symbol": "000002", "name": "万科A", "short_name": "万科A", "market": "SZ", "industry": "房地产"},
                {"symbol": "600000", "name": "浦发银行", "short_name": "浦发银行", "market": "SH", "industry": "银行"},
                {"symbol": "600036", "name": "招商银行", "short_name": "招商银行", "market": "SH", "industry": "银行"},
                {"symbol": "600519", "name": "贵州茅台", "short_name": "茅台", "market": "SH", "industry": "白酒"},
                {"symbol": "600887", "name": "伊利股份", "short_name": "伊利股份", "market": "SH", "industry": "食品饮料"},
                
                # 科技股
                {"symbol": "000858", "name": "五粮液", "short_name": "五粮液", "market": "SZ", "industry": "白酒"},
                {"symbol": "002415", "name": "海康威视", "short_name": "海康威视", "market": "SZ", "industry": "安防"},
                {"symbol": "002594", "name": "比亚迪", "short_name": "比亚迪", "market": "SZ", "industry": "汽车"},
                {"symbol": "300750", "name": "宁德时代", "short_name": "宁德时代", "market": "SZ", "industry": "电池"},
                
                # 互联网概念
                {"symbol": "000725", "name": "京东方A", "short_name": "京东方", "market": "SZ", "industry": "面板"},
                {"symbol": "002230", "name": "科大讯飞", "short_name": "科大讯飞", "market": "SZ", "industry": "人工智能"},
                {"symbol": "002460", "name": "赣锋锂业", "short_name": "赣锋锂业", "market": "SZ", "industry": "锂电"},
                {"symbol": "300059", "name": "东方财富", "short_name": "东方财富", "market": "SZ", "industry": "证券"},
                
                # 港股主要股票
                {"symbol": "00700", "name": "腾讯控股", "short_name": "腾讯", "market": "HK", "industry": "互联网"},
                {"symbol": "09988", "name": "阿里巴巴", "short_name": "阿里", "market": "HK", "industry": "互联网"},
                {"symbol": "03690", "name": "美团", "short_name": "美团", "market": "HK", "industry": "互联网"},
                {"symbol": "01810", "name": "小米集团", "short_name": "小米", "market": "HK", "industry": "手机"},
                {"symbol": "09618", "name": "京东集团", "short_name": "京东", "market": "HK", "industry": "电商"},
                {"symbol": "02318", "name": "中国平安", "short_name": "中国平安", "market": "HK", "industry": "保险"},
                
                # 更多A股
                {"symbol": "600276", "name": "恒瑞医药", "short_name": "恒瑞医药", "market": "SH", "industry": "医药"},
                {"symbol": "000596", "name": "古井贡酒", "short_name": "古井贡酒", "market": "SZ", "industry": "白酒"},
                {"symbol": "600570", "name": "恒生电子", "short_name": "恒生电子", "market": "SH", "industry": "金融科技"},
                {"symbol": "300408", "name": "三环集团", "short_name": "三环集团", "market": "SZ", "industry": "电子"},
                {"symbol": "600031", "name": "三一重工", "short_name": "三一重工", "market": "SH", "industry": "工程机械"},
                {"symbol": "002142", "name": "宁波银行", "short_name": "宁波银行", "market": "SZ", "industry": "银行"},
                {"symbol": "000661", "name": "长春高新", "short_name": "长春高新", "market": "SZ", "industry": "生物医药"},
                {"symbol": "600009", "name": "上海机场", "short_name": "上海机场", "market": "SH", "industry": "交通运输"},
                {"symbol": "000333", "name": "美的集团", "short_name": "美的集团", "market": "SZ", "industry": "家电"},
                {"symbol": "600690", "name": "海尔智家", "short_name": "海尔智家", "market": "SH", "industry": "家电"},
            ]
            
            imported_count = 0
            for stock_data in sample_stocks:
                stock_info = StockInfo(
                    symbol=stock_data["symbol"],
                    name=stock_data["name"],
                    short_name=stock_data["short_name"],
                    market=stock_data["market"],
                    industry=stock_data["industry"],
                    pinyin=self.generate_pinyin(stock_data["name"])
                )
                
                try:
                    stock_id = self.db.add_stock_info(stock_info)
                    if stock_id:
                        imported_count += 1
                        logger.info(f"✅ 导入股票: {stock_info.symbol} - {stock_info.name}")
                except Exception as e:
                    logger.warning(f"⚠️ 跳过股票 {stock_info.symbol}: {e}")
                    
            logger.info(f"🎉 样例股票数据导入完成! 成功导入 {imported_count} 只股票")
            return imported_count
            
        except Exception as e:
            logger.error(f"❌ 导入股票数据失败: {e}")
            return 0
    
    async def get_stock_count(self) -> int:
        """获取数据库中股票总数"""
        return self.db.get_stock_info_count()
    
    async def search_stocks(self, query: str, limit: int = 20) -> List[StockInfo]:
        """搜索股票"""
        return self.db.search_stocks(query, limit)
    
    async def get_stock_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """根据代码获取股票信息"""
        return self.db.get_stock_info_by_symbol(symbol)

# 全局实例
stock_data_service = StockDataService()

# 测试函数
async def main():
    """测试函数"""
    service = StockDataService()
    
    # 检查当前股票数量
    count = await service.get_stock_count()
    print(f"📊 当前数据库中股票数量: {count}")
    
    if count == 0:
        # 导入样例数据
        imported = await service.import_sample_stocks()
        print(f"🎯 导入了 {imported} 只股票")
    
    # 测试搜索功能
    print("\n🔍 测试搜索功能:")
    
    # 搜索测试
    test_queries = ["茅台", "600519", "腾讯", "平安", "比亚迪"]
    
    for query in test_queries:
        results = await service.search_stocks(query, 5)
        print(f"\n搜索 '{query}' 结果 ({len(results)} 条):")
        for stock in results:
            print(f"  {stock.symbol} - {stock.name} ({stock.market})")

if __name__ == "__main__":
    asyncio.run(main())