#!/usr/bin/env python3
"""
更新测试股票的实时数据
"""
import asyncio
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.tencent_data_service import TencentDataService

async def update_test_stocks():
    """更新测试股票的实时数据"""
    print("🔄 开始更新测试股票的实时数据...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_manager = DatabaseManager('stock_pool.db')
    
    # 测试股票
    test_stocks = ['000001', '600519', '300750', '688981', '002594']
    trade_date = '2025-11-14'  # 使用数据库中的交易日期
    
    print(f"📊 准备更新股票: {test_stocks}")
    print(f"📅 目标日期: {trade_date}")
    
    # 1. 从腾讯API获取最新数据
    print("\n🌐 从腾讯财经API获取实时数据...")
    
    async with TencentDataService(db_manager) as service:
        market_data = await service.get_stock_data(test_stocks)
        
        print(f"✅ 成功获取 {len(market_data)} 只股票数据")
        
        # 2. 更新数据库
        print("\n💾 更新数据库...")
        
        updated_count = 0
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            for stock_code, data in market_data.items():
                try:
                    # 检查记录是否存在
                    cursor.execute('''
                        SELECT COUNT(*) FROM daily_stock_changes 
                        WHERE stock_code = ? AND trade_date = ?
                    ''', (stock_code, trade_date))
                    
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        # 更新现有记录
                        cursor.execute('''
                            UPDATE daily_stock_changes 
                            SET close_price = ?,
                                total_market_cap = ?, 
                                circulating_market_cap = ?, 
                                turnover_rate = ?,
                                pe_ratio = ?,
                                pb_ratio = ?,
                                volume = ?,
                                turnover = ?
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (
                            data['current_price'],
                            data['total_market_cap'],
                            data['circulating_market_cap'],
                            data['turnover_rate'],
                            data['pe_ratio'],
                            data['pb_ratio'],
                            data['volume'],
                            data['turnover_amount'],
                            stock_code,
                            trade_date
                        ))
                        action = "更新"
                    else:
                        # 插入新记录
                        cursor.execute('''
                            INSERT INTO daily_stock_changes 
                            (stock_code, trade_date, close_price, open_price, high_price, low_price,
                             volume, turnover, market, change_percent, total_market_cap, 
                             circulating_market_cap, turnover_rate, pe_ratio, pb_ratio, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_code,
                            trade_date,
                            data['current_price'],
                            data.get('open_price', data['current_price']),
                            data.get('high_price', data['current_price']),
                            data.get('low_price', data['current_price']),
                            data['volume'],
                            data['turnover_amount'],
                            'SZ' if not stock_code.startswith('6') else 'SH',
                            data.get('change_percent', 0),
                            data['total_market_cap'],
                            data['circulating_market_cap'],
                            data['turnover_rate'],
                            data['pe_ratio'],
                            data['pb_ratio'],
                            datetime.now().isoformat()
                        ))
                        action = "插入"
                    
                    updated_count += 1
                    print(f"  ✅ {stock_code}: {action}成功 - 价格={data['current_price']:.2f}, 换手率={data['turnover_rate']:.2f}%")
                    
                except Exception as e:
                    print(f"  ❌ {stock_code}: 更新失败 - {e}")
            
            conn.commit()
        
        print(f"\n📈 更新结果:")
        print(f"  成功更新: {updated_count}/{len(market_data)} 只股票")
        
        # 3. 验证更新结果
        print(f"\n🔍 验证更新结果...")
        
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            for stock_code in test_stocks:
                cursor.execute('''
                    SELECT close_price, total_market_cap, circulating_market_cap, 
                           turnover_rate, pe_ratio, pb_ratio
                    FROM daily_stock_changes 
                    WHERE stock_code = ? AND trade_date = ?
                ''', (stock_code, trade_date))
                
                result = cursor.fetchone()
                if result:
                    print(f"  {stock_code}: 价格={result[0]:.2f}, 市值={result[1]/10000:.2f}亿, 换手率={result[3]:.2f}%, PE={result[4]:.1f}")
                else:
                    print(f"  {stock_code}: 数据库中仍无数据")
    
    print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 测试股票数据更新完成!")

if __name__ == '__main__':
    asyncio.run(update_test_stocks())