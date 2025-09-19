"""
股票甄选服务
实现强势股识别、连续涨幅筛选等功能
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, StockScreening, DailyStockChange
from services.akshare_service import akshare_service

logger = logging.getLogger(__name__)

@dataclass
class ScreeningCriteria:
    """筛选条件"""
    screening_type: str
    min_consecutive_days: int = 3
    min_rise_percent: float = 7.0
    min_volume: int = 0
    market_filter: List[str] = None  # ['SH', 'SZ', 'HK']
    
    def to_dict(self) -> Dict:
        return {
            'screening_type': self.screening_type,
            'min_consecutive_days': self.min_consecutive_days,
            'min_rise_percent': self.min_rise_percent,
            'min_volume': self.min_volume,
            'market_filter': self.market_filter or ['SH', 'SZ', 'HK']
        }

@dataclass
class ScreeningResult:
    """筛选结果"""
    stock_code: str
    stock_name: str
    market: str
    consecutive_days: int
    avg_rise_percent: float
    total_volume: int
    avg_volume: int
    daily_changes: List[Dict]  # 每日涨跌详情

class StockScreeningService:
    """股票甄选服务"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def collect_daily_data(self, trade_date: str = None) -> int:
        """
        收集指定日期的股票涨跌数据
        
        Args:
            trade_date: 交易日期，格式YYYY-MM-DD，默认为前一个交易日
            
        Returns:
            收集到的股票数量
        """
        if trade_date is None:
            # 默认收集前一个交易日数据
            trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"🔄 开始收集 {trade_date} 的股票涨跌数据...")
        
        collected_count = 0
        
        try:
            # 获取A股数据
            a_stocks_data = await self._collect_a_stock_data(trade_date)
            collected_count += await self._save_daily_changes(a_stocks_data, trade_date)
            
            # 获取港股数据（如果需要）
            # hk_stocks_data = await self._collect_hk_stock_data(trade_date)
            # collected_count += await self._save_daily_changes(hk_stocks_data, trade_date)
            
            logger.info(f"✅ 完成数据收集，共收集 {collected_count} 只股票的数据")
            
        except Exception as e:
            logger.error(f"❌ 数据收集失败: {e}")
            
        return collected_count
    
    async def _collect_a_stock_data(self, trade_date: str) -> List[DailyStockChange]:
        """收集A股涨跌数据"""
        stocks_data = []
        
        try:
            # 检查日期是否是今天，如果是今天则使用实时数据
            today = datetime.now().strftime('%Y-%m-%d')
            
            if trade_date == today:
                # 使用实时数据接口
                df = akshare_service.ak.stock_zh_a_spot_em()
                
                if df is None or df.empty:
                    logger.warning("未获取到A股实时数据")
                    return stocks_data
                
                logger.info(f"获取到 {len(df)} 只A股实时数据")
                
                for _, row in df.iterrows():
                    try:
                        stock_data = DailyStockChange(
                            stock_code=str(row.get('代码', '')),
                            trade_date=trade_date,
                            change_percent=float(row.get('涨跌幅', 0)),
                            close_price=float(row.get('最新价', 0)),
                            open_price=float(row.get('今开', 0)),
                            high_price=float(row.get('最高', 0)),
                            low_price=float(row.get('最低', 0)),
                            volume=int(row.get('成交量', 0)),
                            turnover=float(row.get('成交额', 0)),
                            market=self._get_market_from_code(str(row.get('代码', ''))),
                            created_at=datetime.now().isoformat()
                        )
                        stocks_data.append(stock_data)
                        
                    except Exception as e:
                        logger.debug(f"处理股票数据失败: {row.get('代码', 'unknown')}, {e}")
                        continue
            else:
                # 历史数据：收集主要股票的历史数据
                await self._collect_historical_stock_data(trade_date, stocks_data)
                    
        except Exception as e:
            logger.error(f"获取A股数据失败: {e}")
            
        return stocks_data
    
    async def _collect_historical_stock_data(self, trade_date: str, stocks_data: List[DailyStockChange]):
        """收集历史股票数据"""
        try:
            # 获取主要股票列表（可以从数据库中获取已知的股票代码）
            import sqlite3
            stock_codes = []
            
            try:
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    # 获取最近有数据的股票代码
                    cursor.execute('''
                        SELECT DISTINCT stock_code 
                        FROM daily_stock_changes 
                        WHERE trade_date >= date('now', '-7 days')
                        LIMIT 200
                    ''')
                    stock_codes = [row[0] for row in cursor.fetchall()]
            except:
                # 如果数据库中没有数据，使用一些主要股票代码
                stock_codes = [
                    '000001', '000002', '000858', '002594', '300750',  # 深圳主要股票
                    '600519', '600036', '601318', '600000', '601166',  # 上海主要股票
                    '688981', '688599', '688036', '688561', '688012'   # 科创板主要股票
                ]
            
            if not stock_codes:
                logger.warning("没有找到股票代码，使用默认股票列表")
                # 使用沪深300成分股的一部分作为默认
                stock_codes = ['000001', '000002', '600519', '600036', '601318']
            
            # 逐个获取历史数据
            collected_count = 0
            for stock_code in stock_codes[:100]:  # 限制数量以避免请求过多
                try:
                    # 使用akshare获取单只股票的历史数据
                    # 注意：这里使用的是历史数据接口
                    hist_df = akshare_service.ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=trade_date.replace('-', ''),
                        end_date=trade_date.replace('-', ''),
                        adjust=""
                    )
                    
                    if hist_df is not None and not hist_df.empty:
                        for _, row in hist_df.iterrows():
                            try:
                                # 计算涨跌幅
                                change_percent = 0
                                if '涨跌幅' in row.index:
                                    change_percent = float(row['涨跌幅'])
                                elif '收盘' in row.index and '开盘' in row.index:
                                    open_price = float(row['开盘'])
                                    close_price = float(row['收盘'])
                                    if open_price > 0:
                                        change_percent = ((close_price - open_price) / open_price) * 100
                                
                                stock_data = DailyStockChange(
                                    stock_code=stock_code,
                                    trade_date=trade_date,
                                    change_percent=change_percent,
                                    close_price=float(row.get('收盘', 0)),
                                    open_price=float(row.get('开盘', 0)),
                                    high_price=float(row.get('最高', 0)),
                                    low_price=float(row.get('最低', 0)),
                                    volume=int(row.get('成交量', 0)),
                                    turnover=float(row.get('成交额', 0)),
                                    market=self._get_market_from_code(stock_code),
                                    created_at=datetime.now().isoformat()
                                )
                                stocks_data.append(stock_data)
                                collected_count += 1
                                
                            except Exception as e:
                                logger.debug(f"处理历史数据失败 {stock_code}: {e}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"获取 {stock_code} 历史数据失败: {e}")
                    continue
            
            logger.info(f"📊 收集到 {collected_count} 条 {trade_date} 的历史数据")
            
        except Exception as e:
            logger.error(f"收集历史数据失败: {e}")
    
    def _get_market_from_code(self, stock_code: str) -> str:
        """根据股票代码判断市场"""
        if stock_code.startswith('6'):
            return 'SH'  # 上海
        elif stock_code.startswith(('0', '2', '3')):
            return 'SZ'  # 深圳
        elif len(stock_code) == 5:
            return 'HK'  # 港股
        else:
            return 'OTHER'
    
    async def _save_daily_changes(self, stocks_data: List[DailyStockChange], trade_date: str) -> int:
        """保存每日涨跌数据到数据库"""
        if not stocks_data:
            return 0
            
        import sqlite3
        
        saved_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
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
                        logger.debug(f"保存股票数据失败: {stock_data.stock_code}, {e}")
                        continue
                
                conn.commit()
                logger.info(f"💾 成功保存 {saved_count} 条每日涨跌数据")
                
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            
        return saved_count
    
    async def screen_strong_rise_stocks(self, criteria: ScreeningCriteria, screening_date: str = None) -> List[ScreeningResult]:
        """
        筛选连续强势上涨股票
        
        Args:
            criteria: 筛选条件
            screening_date: 筛选日期，默认为当前日期
            
        Returns:
            符合条件的股票列表
        """
        if screening_date is None:
            screening_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"🔍 开始筛选强势股票 - 条件: 连续{criteria.min_consecutive_days}天涨幅超过{criteria.min_rise_percent}%")
        
        results = []
        
        try:
            # 查询符合条件的股票
            stocks_with_consecutive_rises = await self._find_consecutive_rise_stocks(criteria, screening_date)
            
            for stock_data in stocks_with_consecutive_rises:
                # 获取股票名称
                stock_name = await self._get_stock_name(stock_data['stock_code'])
                
                result = ScreeningResult(
                    stock_code=stock_data['stock_code'],
                    stock_name=stock_name,
                    market=stock_data['market'],
                    consecutive_days=stock_data['consecutive_days'],
                    avg_rise_percent=stock_data['avg_rise_percent'],
                    total_volume=stock_data['total_volume'],
                    avg_volume=stock_data['avg_volume'],
                    daily_changes=stock_data['daily_changes']
                )
                results.append(result)
            
            logger.info(f"✅ 筛选完成，找到 {len(results)} 只符合条件的强势股票")
            
            # 保存筛选结果
            await self._save_screening_results(results, criteria, screening_date)
            
        except Exception as e:
            logger.error(f"❌ 股票筛选失败: {e}")
            
        return results
    
    async def _find_consecutive_rise_stocks(self, criteria: ScreeningCriteria, screening_date: str) -> List[Dict]:
        """查找连续上涨的股票"""
        import sqlite3
        
        result_stocks = []
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算查询的日期范围（向前推N个交易日）
                end_date = datetime.strptime(screening_date, '%Y-%m-%d')
                start_date = end_date - timedelta(days=criteria.min_consecutive_days * 2)  # 多取一些数据
                
                # 查询最近N天的数据
                market_filter = "','".join(criteria.market_filter or ['SH', 'SZ', 'HK'])
                
                cursor.execute(f'''
                    SELECT stock_code, market, trade_date, change_percent, volume, close_price
                    FROM daily_stock_changes 
                    WHERE trade_date BETWEEN ? AND ?
                    AND market IN ('{market_filter}')
                    AND change_percent >= ?
                    ORDER BY stock_code, trade_date DESC
                ''', (start_date.strftime('%Y-%m-%d'), screening_date, criteria.min_rise_percent))
                
                rows = cursor.fetchall()
                
                # 按股票代码分组
                stocks_data = {}
                for row in rows:
                    stock_code = row[0]
                    if stock_code not in stocks_data:
                        stocks_data[stock_code] = []
                    
                    stocks_data[stock_code].append({
                        'trade_date': row[2],
                        'change_percent': row[3],
                        'volume': row[4],
                        'close_price': row[5],
                        'market': row[1]
                    })
                
                # 检查每只股票是否满足连续上涨条件
                for stock_code, daily_data in stocks_data.items():
                    # 按日期排序（最新的在前）
                    daily_data.sort(key=lambda x: x['trade_date'], reverse=True)
                    
                    # 检查连续涨幅
                    consecutive_count = 0
                    total_rise = 0
                    total_volume = 0
                    
                    for data in daily_data:
                        if data['change_percent'] >= criteria.min_rise_percent:
                            consecutive_count += 1
                            total_rise += data['change_percent']
                            total_volume += data['volume']
                            
                            if consecutive_count >= criteria.min_consecutive_days:
                                # 满足条件
                                avg_rise_percent = total_rise / consecutive_count
                                avg_volume = total_volume // consecutive_count
                                
                                result_stocks.append({
                                    'stock_code': stock_code,
                                    'market': daily_data[0]['market'],
                                    'consecutive_days': consecutive_count,
                                    'avg_rise_percent': avg_rise_percent,
                                    'total_volume': total_volume,
                                    'avg_volume': avg_volume,
                                    'daily_changes': daily_data[:consecutive_count]
                                })
                                break
                        else:
                            break  # 连续性中断
                
        except Exception as e:
            logger.error(f"查询连续上涨股票失败: {e}")
            
        return result_stocks
    
    async def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM stock_info WHERE symbol = ?', (stock_code,))
                result = cursor.fetchone()
                return result[0] if result else stock_code
        except:
            return stock_code
    
    async def _save_screening_results(self, results: List[ScreeningResult], criteria: ScreeningCriteria, screening_date: str):
        """保存筛选结果"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 先删除当天同类型的旧结果
                cursor.execute('''
                    DELETE FROM stock_screening 
                    WHERE screening_date = ? AND screening_type = ?
                ''', (screening_date, criteria.screening_type))
                
                logger.info(f"🗑️ 清理了 {cursor.rowcount} 条当天旧的筛选结果")
                
                # 插入新的筛选结果
                for result in results:
                    cursor.execute('''
                        INSERT INTO stock_screening
                        (stock_code, stock_name, market, screening_date, screening_type,
                         criteria_met, consecutive_days, avg_rise_percent, total_volume, 
                         avg_volume, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.stock_code,
                        result.stock_name,
                        result.market,
                        screening_date,
                        criteria.screening_type,
                        json.dumps(criteria.to_dict()),
                        result.consecutive_days,
                        result.avg_rise_percent,
                        result.total_volume,
                        result.avg_volume,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"💾 保存了 {len(results)} 条筛选结果")
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")
    
    async def get_screening_history(self, screening_type: str = None, limit: int = 100) -> List[StockScreening]:
        """获取筛选历史记录"""
        import sqlite3
        
        results = []
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                if screening_type:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, market, screening_date, screening_type,
                               criteria_met, consecutive_days, avg_rise_percent, total_volume,
                               avg_volume, created_at
                        FROM stock_screening 
                        WHERE screening_type = ?
                        ORDER BY screening_date DESC, avg_rise_percent DESC 
                        LIMIT ?
                    ''', (screening_type, limit))
                else:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, market, screening_date, screening_type,
                               criteria_met, consecutive_days, avg_rise_percent, total_volume,
                               avg_volume, created_at
                        FROM stock_screening 
                        ORDER BY screening_date DESC, avg_rise_percent DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    screening = StockScreening(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        market=row[3],
                        screening_date=row[4],
                        screening_type=row[5],
                        criteria_met=row[6],
                        consecutive_days=row[7],
                        avg_rise_percent=row[8],
                        total_volume=row[9],
                        avg_volume=row[10],
                        created_at=row[11]
                    )
                    results.append(screening)
                    
        except Exception as e:
            logger.error(f"获取筛选历史失败: {e}")
            
        return results

# 全局实例
_stock_screening_service = None

def get_stock_screening_service(db_manager: DatabaseManager) -> StockScreeningService:
    """获取股票筛选服务实例"""
    global _stock_screening_service
    if _stock_screening_service is None:
        _stock_screening_service = StockScreeningService(db_manager)
    return _stock_screening_service