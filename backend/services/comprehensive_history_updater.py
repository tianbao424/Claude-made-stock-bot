#!/usr/bin/env python3
"""
全面历史数据更新器
处理所有9000+股票的历史数据更新需求
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import akshare as ak

logger = logging.getLogger(__name__)

class ComprehensiveHistoryUpdater:
    """全面历史数据更新器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ak = ak
    
    async def analyze_update_needs(self) -> Dict[str, int]:
        """分析历史数据更新需求"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 总股票数
            cursor.execute('SELECT COUNT(*) FROM stock_info')
            total_stocks = cursor.fetchone()[0]
            
            # 2. 没有历史数据的股票
            cursor.execute('''
                SELECT COUNT(*) FROM stock_info si
                LEFT JOIN daily_stock_changes dsc ON si.symbol = dsc.stock_code
                WHERE dsc.stock_code IS NULL
            ''')
            no_history = cursor.fetchone()[0]
            
            # 3. 数据陈旧的股票（超过3天）
            cursor.execute('''
                SELECT COUNT(DISTINCT si.symbol) FROM stock_info si
                LEFT JOIN (
                    SELECT stock_code, MAX(trade_date) as latest_date
                    FROM daily_stock_changes GROUP BY stock_code
                ) dsc ON si.symbol = dsc.stock_code
                WHERE dsc.latest_date < date('now', '-3 days')
            ''')
            stale_data = cursor.fetchone()[0]
            
            # 4. A股数量
            cursor.execute("SELECT COUNT(*) FROM stock_info WHERE market IN ('SH', 'SZ', '')")
            a_stocks = cursor.fetchone()[0]
            
            # 5. 港股数量
            cursor.execute("SELECT COUNT(*) FROM stock_info WHERE market = 'HK'")
            hk_stocks = cursor.fetchone()[0]
            
            analysis = {
                'total_stocks': total_stocks,
                'no_history': no_history,
                'stale_data': stale_data,
                'a_stocks': a_stocks,
                'hk_stocks': hk_stocks,
                'priority_update': no_history + stale_data
            }
            
            logger.info(f"📊 历史数据更新需求分析:")
            logger.info(f"  总股票数: {total_stocks:,}")
            logger.info(f"  A股: {a_stocks:,}, 港股: {hk_stocks:,}")
            logger.info(f"  无历史数据: {no_history:,}")
            logger.info(f"  数据陈旧: {stale_data:,}")
            logger.info(f"  优先更新: {analysis['priority_update']:,}")
            
            return analysis
            
        finally:
            conn.close()
    
    async def get_priority_stocks(self, limit: int = None) -> List[str]:
        """获取优先更新的股票列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建查询，优先处理A股中没有数据或数据陈旧的股票
            query = '''
                SELECT si.symbol, si.market, dsc.latest_date
                FROM stock_info si
                LEFT JOIN (
                    SELECT stock_code, MAX(trade_date) as latest_date
                    FROM daily_stock_changes GROUP BY stock_code
                ) dsc ON si.symbol = dsc.stock_code
                WHERE si.market IN ('SH', 'SZ')  -- 只处理A股
                AND (
                    dsc.latest_date IS NULL  -- 没有历史数据
                    OR dsc.latest_date < date('now', '-1 days')  -- 数据超过1天
                )
                ORDER BY 
                    CASE WHEN dsc.latest_date IS NULL THEN 0 ELSE 1 END,  -- 无数据优先
                    si.symbol
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            stocks = [row[0] for row in results]
            logger.info(f"🎯 筛选出 {len(stocks)} 只优先更新的股票")
            
            return stocks
            
        finally:
            conn.close()
    
    async def update_historical_data_batch(self, symbols: List[str], days: int = 30) -> Dict[str, int]:
        """批量更新历史数据 - 增强版本"""
        results = {
            'total': len(symbols),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        logger.info(f"📈 开始智能批量更新 {len(symbols)} 只股票的历史数据...")
        
        # 使用增强的网络处理器
        from .enhanced_network_handler import NetworkRetryHandler
        retry_handler = NetworkRetryHandler()
        
        # 智能分批处理
        batch_size = 20  # 减小批次大小
        
        for batch_start in range(0, len(symbols), batch_size):
            batch_end = min(batch_start + batch_size, len(symbols))
            batch_symbols = symbols[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            logger.info(f"📦 批次 {batch_num}/{total_batches}: 处理 {len(batch_symbols)} 只股票")
            
            # 检查网络状态
            if retry_handler.should_pause():
                logger.warning("🛑 网络状况不佳，暂停2分钟...")
                await asyncio.sleep(120)
                retry_handler.consecutive_failures = 0
            
            # 处理当前批次
            batch_results = await self._process_batch_with_retry(batch_symbols, days, retry_handler)
            
            results['success'] += batch_results['success']
            results['failed'] += batch_results['failed']
            results['errors'].extend(batch_results['errors'])
            
            # 批次间自适应延迟
            if batch_end < len(symbols):
                delay = min(retry_handler.consecutive_failures * 0.3 + 1, 15)
                logger.info(f"⏳ 批次间等待 {delay:.1f} 秒...")
                await asyncio.sleep(delay)
        
        success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
        logger.info(f"📊 智能批量更新完成，成功率: {success_rate:.1f}% ({results['success']}/{results['total']})")
        
        return results
    
    async def _process_batch_with_retry(self, symbols: List[str], days: int, retry_handler) -> Dict[str, int]:
        """处理单个批次（带重试）"""
        batch_results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"[{i}/{len(symbols)}] 更新 {symbol} 历史数据...")
                
                # 使用多重回退策略获取数据
                hist_data = await self._get_historical_data_with_fallback(symbol, days, retry_handler)
                
                if hist_data is not None and not hist_data.empty:
                    # 保存到数据库
                    await self._save_historical_data(symbol, hist_data)
                    batch_results['success'] += 1
                    retry_handler.consecutive_failures = 0  # 重置失败计数
                    logger.info(f"✅ {symbol} 更新成功，{len(hist_data)} 条记录")
                else:
                    logger.warning(f"⚠️ {symbol} 没有获取到数据")
                    batch_results['failed'] += 1
                    retry_handler.consecutive_failures += 1
                
                # 动态延迟
                delay = 0.3 + min(retry_handler.consecutive_failures * 0.1, 2.0)
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ {symbol} 更新失败: {e}")
                batch_results['failed'] += 1
                batch_results['errors'].append(f"{symbol}: {str(e)}")
                retry_handler.consecutive_failures += 1
        
        return batch_results
    
    async def _get_historical_data_with_fallback(self, symbol: str, days: int, retry_handler):
        """获取历史数据的多重回退策略"""
        
        # 策略1: 标准AkShare历史接口
        try:
            async def fetch_standard():
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                
                return ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )
            
            data = await retry_handler.execute_with_retry(fetch_standard, max_retries=2)
            if data is not None and not data.empty:
                logger.debug(f"🎯 策略1成功: {symbol}")
                return data
        except Exception as e:
            logger.debug(f"🔄 策略1失败 {symbol}: {e}")
        
        # 策略2: 东财接口
        try:
            async def fetch_eastmoney():
                return ak.stock_zh_a_hist_em(symbol=symbol, period="daily", adjust="")
            
            data = await retry_handler.execute_with_retry(fetch_eastmoney, max_retries=1)
            if data is not None and not data.empty:
                # 限制到指定天数
                if len(data) > days:
                    data = data.tail(days)
                logger.debug(f"🎯 策略2成功: {symbol}")
                return data
        except Exception as e:
            logger.debug(f"🔄 策略2失败 {symbol}: {e}")
        
        # 策略3: 简化接口
        try:
            async def fetch_simple():
                return ak.stock_zh_a_daily(symbol=symbol, adjust="")
            
            data = await retry_handler.execute_with_retry(fetch_simple, max_retries=1)
            if data is not None and not data.empty:
                # 限制到指定天数
                if len(data) > days:
                    data = data.tail(days)
                logger.debug(f"🎯 策略3成功: {symbol}")
                return data
        except Exception as e:
            logger.debug(f"🔄 策略3失败 {symbol}: {e}")
        
        # 策略4: 无日期参数接口
        try:
            async def fetch_no_date():
                return ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
            
            data = await retry_handler.execute_with_retry(fetch_no_date, max_retries=1)
            if data is not None and not data.empty:
                # 限制到指定天数
                if len(data) > days:
                    data = data.tail(days)
                logger.debug(f"🎯 策略4成功: {symbol}")
                return data
        except Exception as e:
            logger.debug(f"🔄 策略4失败 {symbol}: {e}")
        
        logger.warning(f"❌ {symbol} 所有数据获取策略都失败")
        return None
    
    async def _save_historical_data(self, symbol: str, hist_data):
        """保存历史数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for _, row in hist_data.iterrows():
                trade_date = row['日期'].strftime('%Y-%m-%d')
                
                # 使用 INSERT OR REPLACE 避免重复数据
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_stock_changes 
                    (stock_code, trade_date, open_price, close_price, high_price, low_price, 
                     volume, turnover, change_percent, market, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    trade_date,
                    float(row['开盘']),
                    float(row['收盘']),
                    float(row['最高']),
                    float(row['最低']),
                    int(row['成交量']),
                    float(row['成交额']),
                    float(row['涨跌幅']),
                    'SH' if symbol.startswith('6') else 'SZ',  # 简单市场判断
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    async def comprehensive_update(self, max_stocks: int = 2000) -> Dict[str, int]:
        """执行全面的历史数据更新"""
        logger.info(f"🚀 开始全面历史数据更新，最多处理 {max_stocks} 只股票")
        
        # 1. 分析需求
        analysis = await self.analyze_update_needs()
        
        # 2. 获取优先股票
        priority_stocks = await self.get_priority_stocks(max_stocks)
        
        if not priority_stocks:
            logger.info("✅ 所有股票的历史数据都是最新的")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # 3. 批量更新
        results = await self.update_historical_data_batch(priority_stocks, days=60)
        
        return results

async def test_comprehensive_updater():
    """测试全面历史数据更新器"""
    import os
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
    updater = ComprehensiveHistoryUpdater(db_path)
    
    # 分析需求
    analysis = await updater.analyze_update_needs()
    print("需求分析:", analysis)
    
    # 获取前10只优先股票进行测试
    priority_stocks = await updater.get_priority_stocks(10)
    print("优先股票:", priority_stocks[:5], "...")
    
    # 测试更新（只更新5只股票）
    if priority_stocks:
        results = await updater.update_historical_data_batch(priority_stocks[:5], days=30)
        print("更新结果:", results)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_comprehensive_updater())