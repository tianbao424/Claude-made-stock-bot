#!/usr/bin/env python3
"""
外部市值和换手率数据获取服务
支持多种数据源，提供容错和重试机制
"""
import asyncio
import aiohttp
import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sqlite3
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DatabaseManager

logger = logging.getLogger(__name__)

class ExternalMarketDataFetcher:
    """外部市场数据获取器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://finance.sina.com.cn/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def fetch_sina_market_data(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """从新浪财经获取市值和换手率数据"""
        results = {}
        
        try:
            # 将股票代码转换为新浪格式
            sina_codes = []
            for code in stock_codes:
                if code.startswith('6'):
                    sina_codes.append(f'sh{code}')
                else:
                    sina_codes.append(f'sz{code}')
            
            # 分批处理，每批50只股票
            batch_size = 50
            for i in range(0, len(sina_codes), batch_size):
                batch_codes = sina_codes[i:i + batch_size]
                
                try:
                    # 构建新浪财经API URL
                    codes_str = ','.join(batch_codes)
                    url = f'http://hq.sinajs.cn/list={codes_str}'
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.text(encoding='gbk')
                            parsed_data = self._parse_sina_response(content, stock_codes[i:i + batch_size])
                            results.update(parsed_data)
                            
                    # 避免请求过于频繁
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"新浪财经批次 {i//batch_size + 1} 获取失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"新浪财经数据获取失败: {e}")
        
        return results
    
    def _parse_sina_response(self, content: str, stock_codes: List[str]) -> Dict[str, Dict]:
        """解析新浪财经响应数据"""
        results = {}
        
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            if i >= len(stock_codes):
                break
                
            try:
                # 解析新浪财经数据格式
                if 'var hq_str_' in line and '="' in line:
                    data_part = line.split('="')[1].split('";')[0]
                    fields = data_part.split(',')
                    
                    if len(fields) >= 8:
                        stock_code = stock_codes[i]
                        current_price = float(fields[3]) if fields[3] else 0
                        volume = int(float(fields[8])) if fields[8] else 0  # 成交量(股)
                        turnover = float(fields[9]) if len(fields) > 9 and fields[9] else 0  # 成交额(元)
                        
                        # 估算市值 (使用更合理的估算方法)
                        if current_price > 0:
                            # 改进估算：使用成交额反推市值规模
                            estimated_total_shares = self._estimate_total_shares_improved(stock_code, current_price, turnover)
                            total_market_cap = current_price * estimated_total_shares / 10000  # 万元
                            circulating_market_cap = total_market_cap * 0.7  # 假设70%流通
                            
                            # 计算换手率
                            if volume > 0:
                                circulating_shares = circulating_market_cap * 10000 / current_price
                                turnover_rate = (volume / circulating_shares * 100) if circulating_shares > 0 else 0
                            else:
                                turnover_rate = 0
                            
                            results[stock_code] = {
                                'current_price': current_price,
                                'volume': volume,
                                'turnover_amount': turnover,
                                'total_market_cap': total_market_cap,
                                'circulating_market_cap': circulating_market_cap,
                                'turnover_rate': min(turnover_rate, 20),  # 限制最大20%
                                'data_source': 'sina'
                            }
                        else:
                            # 即使价格为0也记录，便于调试
                            logger.debug(f"股票 {stock_code} 价格为0: {fields[:10]}")
                            
            except Exception as e:
                logger.debug(f"解析股票 {stock_codes[i] if i < len(stock_codes) else 'unknown'} 数据失败: {e}")
                continue
        
        return results
    
    def _estimate_total_shares(self, stock_code: str, price: float) -> float:
        """估算总股本(股)"""
        # 根据股票代码前缀和价格区间估算股本规模
        if stock_code.startswith('688'):  # 科创板
            if price > 100:
                return 100000000  # 1亿股
            elif price > 50:
                return 300000000  # 3亿股
            else:
                return 500000000  # 5亿股
        elif stock_code.startswith('30'):  # 创业板
            if price > 50:
                return 200000000  # 2亿股
            elif price > 20:
                return 500000000  # 5亿股
            else:
                return 800000000  # 8亿股
        elif stock_code.startswith('60'):  # 沪市主板
            if price > 50:
                return 500000000  # 5亿股
            elif price > 20:
                return 1000000000  # 10亿股
            else:
                return 2000000000  # 20亿股
        else:  # 深市主板
            if price > 30:
                return 800000000  # 8亿股
            elif price > 10:
                return 1200000000  # 12亿股
            else:
                return 1500000000  # 15亿股
    
    def _estimate_total_shares_improved(self, stock_code: str, price: float, turnover_amount: float) -> float:
        """改进的股本估算方法，结合成交额"""
        # 基础股本估算
        base_shares = self._estimate_total_shares(stock_code, price)
        
        # 如果有成交额数据，可以作为参考调整
        if turnover_amount > 0 and price > 0:
            # 通过成交额推测可能的流通规模
            implied_volume_ratio = turnover_amount / (price * base_shares * 0.7)  # 假设70%流通
            
            # 如果推测的换手率过高，说明股本可能被低估
            if implied_volume_ratio > 0.3:  # 换手率超过30%可能不合理
                adjustment_factor = min(implied_volume_ratio / 0.1, 3)  # 最多调整3倍
                base_shares *= adjustment_factor
            # 如果推测的换手率过低，说明股本可能被高估
            elif implied_volume_ratio < 0.001:  # 换手率低于0.1%
                adjustment_factor = max(implied_volume_ratio / 0.01, 0.3)  # 最少调整到30%
                base_shares *= adjustment_factor
        
        return base_shares
    
    async def fetch_eastmoney_data(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """从东方财富获取数据"""
        results = {}
        
        try:
            # 东方财富API通常需要特定的参数格式
            # 这里使用简化的公开接口
            for code in stock_codes[:10]:  # 先测试少量股票
                try:
                    # 构建东方财富URL (这个需要根据实际可用接口调整)
                    market = '1' if code.startswith('6') else '0'
                    url = f'http://push2.eastmoney.com/api/qt/stock/get?fields=f43,f57,f58,f162,f163&secid={market}.{code}'
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('rc') == 0 and data.get('data'):
                                stock_data = data['data']
                                
                                results[code] = {
                                    'current_price': stock_data.get('f43', 0) / 100,  # 当前价
                                    'turnover_rate': stock_data.get('f168', 0),  # 换手率
                                    'total_market_cap': stock_data.get('f116', 0),  # 总市值
                                    'circulating_market_cap': stock_data.get('f117', 0),  # 流通市值
                                    'data_source': 'eastmoney'
                                }
                    
                    await asyncio.sleep(0.2)  # 控制请求频率
                    
                except Exception as e:
                    logger.debug(f"东方财富获取 {code} 失败: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"东方财富数据获取失败: {e}")
        
        return results
    
    async def fetch_market_data_multi_source(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """从多个数据源获取市值数据"""
        all_results = {}
        
        logger.info(f"🔄 开始从多数据源获取 {len(stock_codes)} 只股票的市值数据...")
        
        # 1. 尝试新浪财经
        logger.info("📡 尝试新浪财经数据源...")
        sina_results = await self.fetch_sina_market_data(stock_codes)
        all_results.update(sina_results)
        logger.info(f"✅ 新浪财经获取到 {len(sina_results)} 只股票数据")
        
        # 2. 对于未获取到的股票，尝试东方财富
        missing_codes = [code for code in stock_codes if code not in all_results]
        if missing_codes:
            logger.info(f"📡 尝试东方财富补充 {len(missing_codes)} 只股票...")
            eastmoney_results = await self.fetch_eastmoney_data(missing_codes)
            all_results.update(eastmoney_results)
            logger.info(f"✅ 东方财富补充 {len(eastmoney_results)} 只股票数据")
        
        return all_results
    
    async def update_database_with_market_data(self, market_data: Dict[str, Dict], trade_date: str):
        """将获取的市值数据更新到数据库"""
        updated_count = 0
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock_code, data in market_data.items():
                    try:
                        # 更新daily_stock_changes表
                        cursor.execute('''
                            UPDATE daily_stock_changes 
                            SET total_market_cap = ?,
                                circulating_market_cap = ?,
                                turnover_rate = ?
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (
                            data.get('total_market_cap', 0),
                            data.get('circulating_market_cap', 0), 
                            data.get('turnover_rate', 0),
                            stock_code,
                            trade_date
                        ))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                            
                        # 同时更新stock_info表的市值
                        if data.get('total_market_cap', 0) > 0:
                            cursor.execute('''
                                UPDATE stock_info 
                                SET market_cap = ?
                                WHERE symbol = ?
                            ''', (
                                data['total_market_cap'] / 10000,  # 转换为亿元
                                stock_code
                            ))
                        
                    except Exception as e:
                        logger.debug(f"更新 {stock_code} 数据失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"数据库更新失败: {e}")
        
        logger.info(f"✅ 成功更新 {updated_count} 只股票的市值数据")
        return updated_count

# 便捷函数
async def supplement_a_stock_market_data(db_manager: DatabaseManager, trade_date: str = None, limit: int = 1000) -> Dict:
    """补充A股市值数据的主函数"""
    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"🚀 开始补充A股市值数据 (日期: {trade_date}, 限制: {limit})")
    
    # 获取需要补充数据的股票列表
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT stock_code 
            FROM daily_stock_changes 
            WHERE trade_date = ? 
              AND (total_market_cap = 0 OR total_market_cap IS NULL)
              AND volume > 0
            ORDER BY volume DESC
            LIMIT ?
        ''', (trade_date, limit))
        
        stock_codes = [row[0] for row in cursor.fetchall()]
    
    if not stock_codes:
        logger.info("✅ 没有找到需要补充市值数据的股票")
        return {'success': True, 'updated_count': 0, 'message': '无需补充'}
    
    logger.info(f"📊 找到 {len(stock_codes)} 只需要补充数据的股票")
    
    # 获取市值数据
    async with ExternalMarketDataFetcher(db_manager) as fetcher:
        market_data = await fetcher.fetch_market_data_multi_source(stock_codes)
        updated_count = await fetcher.update_database_with_market_data(market_data, trade_date)
    
    result = {
        'success': True,
        'trade_date': trade_date,
        'total_stocks_checked': len(stock_codes),
        'data_fetched': len(market_data),
        'updated_count': updated_count,
        'success_rate': f"{len(market_data)/len(stock_codes)*100:.1f}%" if stock_codes else "0%"
    }
    
    logger.info(f"🎉 市值数据补充完成: {result}")
    return result

async def supplement_all_a_stock_market_data(db_manager: DatabaseManager, trade_date: str = None, batch_size: int = 500) -> Dict:
    """补充全部A股市值数据的主函数"""
    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"🚀 开始补充全部A股市值数据 (日期: {trade_date}, 批次大小: {batch_size})")
    
    # 获取所有需要补充数据的股票列表
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT stock_code 
            FROM daily_stock_changes 
            WHERE trade_date = ? 
              AND (total_market_cap = 0 OR total_market_cap IS NULL)
              AND volume > 0
            ORDER BY volume DESC
        ''', (trade_date,))
        
        all_stock_codes = [row[0] for row in cursor.fetchall()]
    
    if not all_stock_codes:
        logger.info("✅ 没有找到需要补充市值数据的股票")
        return {'success': True, 'total_updated': 0, 'message': '无需补充'}
    
    total_stocks = len(all_stock_codes)
    logger.info(f"📊 找到 {total_stocks} 只需要补充数据的股票，开始分批处理...")
    
    total_updated = 0
    total_fetched = 0
    batch_count = 0
    
    # 分批处理
    for i in range(0, total_stocks, batch_size):
        batch_count += 1
        batch_codes = all_stock_codes[i:i + batch_size]
        
        logger.info(f"🔄 处理第 {batch_count} 批 ({len(batch_codes)} 只股票): {i+1}-{min(i+batch_size, total_stocks)}/{total_stocks}")
        
        try:
            # 获取市值数据
            async with ExternalMarketDataFetcher(db_manager) as fetcher:
                market_data = await fetcher.fetch_market_data_multi_source(batch_codes)
                updated_count = await fetcher.update_database_with_market_data(market_data, trade_date)
            
            total_updated += updated_count
            total_fetched += len(market_data)
            
            logger.info(f"📈 第 {batch_count} 批完成: 获取 {len(market_data)} 只, 更新 {updated_count} 只")
            
            # 添加延时以避免过于频繁的请求
            if i + batch_size < total_stocks:
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"❌ 第 {batch_count} 批处理失败: {e}")
            continue
    
    result = {
        'success': True,
        'trade_date': trade_date,
        'total_stocks': total_stocks,
        'total_batches': batch_count,
        'total_fetched': total_fetched,
        'total_updated': total_updated,
        'overall_success_rate': f"{total_fetched/total_stocks*100:.1f}%",
        'update_success_rate': f"{total_updated/total_stocks*100:.1f}%"
    }
    
    logger.info(f"🎉 全部A股市值数据补充完成: {result}")
    return result

# 测试函数
async def test_market_data_fetcher():
    """测试市值数据获取器"""
    print("🧪 测试外部市值数据获取器...")
    
    db_manager = DatabaseManager("stock_pool.db")
    test_codes = ['000001', '000002', '300001', '600519', '688001']
    
    async with ExternalMarketDataFetcher(db_manager) as fetcher:
        results = await fetcher.fetch_market_data_multi_source(test_codes)
        
        print(f"📊 测试结果: 获取到 {len(results)} 只股票数据")
        for code, data in results.items():
            print(f"  {code}: 价格={data.get('current_price', 0):.2f}, "
                  f"市值={data.get('total_market_cap', 0)/10000:.1f}亿, "
                  f"换手率={data.get('turnover_rate', 0):.2f}%")

if __name__ == "__main__":
    asyncio.run(test_market_data_fetcher())