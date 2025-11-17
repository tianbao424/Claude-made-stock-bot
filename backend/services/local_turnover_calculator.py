#!/usr/bin/env python3
"""
本地换手率计算服务
基于现有数据库数据计算换手率，减少对外部API的依赖
"""
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager

logger = logging.getLogger(__name__)

class LocalTurnoverCalculator:
    """本地换手率计算器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def get_existing_market_cap_data(self) -> Dict[str, float]:
        """获取现有的市值数据"""
        market_cap_data = {}
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT symbol, market_cap 
                FROM stock_info 
                WHERE market_cap > 0
            ''')
            
            for row in cursor.fetchall():
                stock_code, market_cap = row
                market_cap_data[stock_code] = market_cap
        
        logger.info(f"📊 找到 {len(market_cap_data)} 只股票的现有市值数据")
        return market_cap_data
    
    def estimate_circulating_shares(self, stock_code: str, market_cap: float, current_price: float) -> Optional[float]:
        """基于市值和价格估算流通股数"""
        if current_price <= 0:
            return None
        
        # 假设流通股占总股本的70%（A股平均水平）
        estimated_total_shares = market_cap / current_price
        estimated_circulating_shares = estimated_total_shares * 0.7
        
        return estimated_circulating_shares
    
    def calculate_turnover_rate_from_existing_data(self, stock_code: str, trade_date: str) -> Optional[float]:
        """基于现有数据计算换手率"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. 获取交易数据（包括实时市值）
                cursor.execute('''
                    SELECT volume, close_price, circulating_market_cap
                    FROM daily_stock_changes 
                    WHERE stock_code = ? AND trade_date = ? AND circulating_market_cap > 0
                ''', (stock_code, trade_date))
                
                trade_result = cursor.fetchone()
                if not trade_result:
                    return None
                
                volume, close_price, circulating_market_cap = trade_result
                
                # 市值单位是万元，转换为元
                market_cap_yuan = circulating_market_cap * 10000
                
                # 3. 直接根据流通市值和价格计算流通股数
                if close_price > 0:
                    circulating_shares = market_cap_yuan / close_price
                else:
                    return None
                
                if not circulating_shares or circulating_shares <= 0:
                    return None
                
                # 4. 计算换手率
                turnover_rate = (volume / circulating_shares) * 100
                
                logger.debug(f"📊 {stock_code} {trade_date} 换手率计算:")
                logger.debug(f"  - 成交量: {volume:,} 股")
                logger.debug(f"  - 流通市值: {market_cap_yuan:,.0f} 元")
                logger.debug(f"  - 价格: {close_price}")
                logger.debug(f"  - 流通股数: {circulating_shares:,.0f} 股")
                logger.debug(f"  - 换手率: {turnover_rate:.4f}%")
                
                return turnover_rate
                
        except Exception as e:
            logger.error(f"❌ 计算 {stock_code} {trade_date} 换手率失败: {e}")
            return None
    
    def batch_calculate_turnover_rates(self, trade_date: str, limit: int = 100) -> Dict[str, any]:
        """批量计算指定日期的换手率"""
        logger.info(f"🔄 开始计算 {trade_date} 的换手率（本地计算）...")
        
        # 获取有交易数据且有市值数据的股票
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT stock_code, volume, close_price, circulating_market_cap
                FROM daily_stock_changes
                WHERE trade_date = ? 
                  AND volume > 0 
                  AND circulating_market_cap > 0
                ORDER BY volume DESC
                LIMIT ?
            ''', (trade_date, limit))
            
            stock_data = cursor.fetchall()
        
        if not stock_data:
            logger.warning(f"⚠️ {trade_date} 没有找到可计算的股票数据")
            return {'error': '没有找到可计算的股票数据'}
        
        logger.info(f"📊 找到 {len(stock_data)} 只可计算换手率的股票")
        
        success_count = 0
        error_count = 0
        
        for stock_code, volume, close_price, circulating_market_cap in stock_data:
            try:
                # 计算换手率
                turnover_rate = self.calculate_turnover_rate_from_existing_data(stock_code, trade_date)
                
                if turnover_rate is not None:
                    # 更新到数据库
                    with sqlite3.connect(self.db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # 检查是否已存在技术指标记录
                        cursor.execute('''
                            SELECT id FROM stock_technical_indicators 
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (stock_code, trade_date))
                        
                        if cursor.fetchone():
                            # 更新现有记录
                            cursor.execute('''
                                UPDATE stock_technical_indicators 
                                SET turnover_rate = ?, updated_at = ?
                                WHERE stock_code = ? AND trade_date = ?
                            ''', (turnover_rate, datetime.now().isoformat(), stock_code, trade_date))
                        else:
                            # 插入新记录
                            cursor.execute('''
                                INSERT INTO stock_technical_indicators 
                                (stock_code, trade_date, turnover_rate, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                stock_code, trade_date, turnover_rate,
                                datetime.now().isoformat(),
                                datetime.now().isoformat()
                            ))
                        
                        conn.commit()
                    
                    success_count += 1
                    
                    if success_count % 20 == 0:
                        logger.info(f"📊 已处理 {success_count}/{len(stock_data)} 只股票...")
                
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ 处理 {stock_code} 换手率失败: {e}")
                error_count += 1
        
        result = {
            'trade_date': trade_date,
            'total_stocks': len(stock_data),
            'success_count': success_count,
            'error_count': error_count,
            'calculation_method': 'local_estimation',
            'process_time': datetime.now().isoformat()
        }
        
        logger.info(f"✅ {trade_date} 换手率计算完成（本地方法）:")
        logger.info(f"  - 总股票数: {result['total_stocks']}")
        logger.info(f"  - 成功: {result['success_count']}")
        logger.info(f"  - 失败: {result['error_count']}")
        logger.info(f"  - 成功率: {(success_count/len(stock_data)*100):.1f}%")
        
        return result
    
    def update_close_prices_for_screening(self, limit: int = 1000) -> Dict[str, any]:
        """更新筛选结果的收盘价（基于现有数据）"""
        logger.info("🔄 更新筛选结果的收盘价...")
        
        # 获取最近的交易日期
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(trade_date) 
                FROM daily_stock_changes
            ''')
            
            latest_date = cursor.fetchone()[0]
            if not latest_date:
                return {'error': '没有找到交易数据'}
        
        logger.info(f"📅 使用最新交易日期: {latest_date}")
        
        # 获取最新的收盘价数据
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT stock_code, close_price 
                FROM daily_stock_changes 
                WHERE trade_date = ? AND close_price > 0
                ORDER BY volume DESC
                LIMIT ?
            ''', (latest_date, limit))
            
            price_data = cursor.fetchall()
        
        if not price_data:
            return {'error': f'{latest_date} 没有找到价格数据'}
        
        logger.info(f"📊 找到 {len(price_data)} 只股票的价格数据")
        
        # 创建价格映射
        price_map = {stock_code: close_price for stock_code, close_price in price_data}
        
        result = {
            'update_date': latest_date,
            'price_count': len(price_map),
            'price_data': price_map,
            'update_time': datetime.now().isoformat()
        }
        
        logger.info(f"✅ 价格数据准备完成: {len(price_map)} 只股票")
        
        return result

# 创建全局实例
def get_local_turnover_calculator(db_manager: DatabaseManager) -> LocalTurnoverCalculator:
    """获取本地换手率计算器实例"""
    return LocalTurnoverCalculator(db_manager)

# 测试函数
async def test_local_calculator():
    """测试本地计算器"""
    print("🧪 测试本地换手率计算器")
    
    # 初始化
    db_path = "stock_pool.db"
    db_manager = DatabaseManager(db_path)
    calculator = get_local_turnover_calculator(db_manager)
    
    # 获取最新交易日期
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(trade_date) FROM daily_stock_changes')
        latest_date = cursor.fetchone()[0]
    
    if latest_date:
        print(f"📅 测试日期: {latest_date}")
        
        # 测试换手率计算
        result = calculator.batch_calculate_turnover_rates(latest_date, limit=50)
        print(f"📊 换手率计算结果: {result}")
        
        # 测试价格数据更新
        price_result = calculator.update_close_prices_for_screening(limit=100)
        print(f"💰 价格数据结果: 成功获取 {price_result.get('price_count', 0)} 只股票价格")
    else:
        print("❌ 没有找到交易数据")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_local_calculator())