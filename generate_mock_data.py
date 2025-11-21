#!/usr/bin/env python3
"""
生成模拟历史数据用于测试数据优化脚本
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_mock_historical_data():
    """生成模拟历史K线数据"""
    print("🎯 生成模拟历史数据...")
    
    # 连接数据库
    db_path = "backend/stock_pool.db"
    
    # 测试股票代码
    test_stocks = ['000001', '000002', '600000', '600036', '600519']
    
    # 生成120天的历史数据
    end_date = datetime.now()
    dates = []
    for i in range(120, 0, -1):
        date = end_date - timedelta(days=i)
        # 只保留工作日
        if date.weekday() < 5:  # 0-6，0是周一，6是周日
            dates.append(date.strftime('%Y-%m-%d'))
    
    print(f"📅 生成日期范围: {dates[0]} 到 {dates[-1]} ({len(dates)} 个交易日)")
    
    total_records = 0
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        for stock_code in test_stocks:
            print(f"📊 生成 {stock_code} 的历史数据...")
            
            # 初始价格
            if stock_code == '600519':  # 茅台
                base_price = 1400
            elif stock_code.startswith('60'):  # 沪市
                base_price = 15
            else:  # 深市
                base_price = 12
            
            current_price = base_price
            
            for date in dates:
                # 生成随机价格变动 (-3% 到 +3%)
                change_pct = random.uniform(-0.03, 0.03)
                
                # 计算OHLC
                open_price = current_price
                close_price = open_price * (1 + change_pct)
                high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
                low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
                
                # 生成成交量和成交额
                volume = random.randint(50000, 2000000)  # 5万到200万股
                amount = volume * (high_price + low_price) / 2  # 简化计算
                
                # 插入数据
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_stock_changes
                    (stock_code, change_date, open_price, close_price, high_price, low_price,
                     volume, turnover, change_percent, change_amount, market)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock_code,
                    date,
                    round(open_price, 2),
                    round(close_price, 2),
                    round(high_price, 2),
                    round(low_price, 2),
                    volume,
                    round(amount, 2),
                    round(change_pct * 100, 2),
                    round(close_price - open_price, 2),
                    'SH' if stock_code.startswith('6') else 'SZ'
                ))
                
                current_price = close_price
                total_records += 1
        
        conn.commit()
    
    print(f"✅ 成功生成 {total_records} 条模拟历史数据")
    return total_records

def verify_generated_data():
    """验证生成的数据"""
    print("\n🔍 验证生成的数据...")
    
    db_path = "backend/stock_pool.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 统计总记录数
        cursor.execute('SELECT COUNT(*) FROM daily_stock_changes')
        total_records = cursor.fetchone()[0]
        
        # 统计股票数
        cursor.execute('SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes')
        total_stocks = cursor.fetchone()[0]
        
        # 获取日期范围
        cursor.execute('''
            SELECT MIN(change_date), MAX(change_date) 
            FROM daily_stock_changes
        ''')
        date_range = cursor.fetchone()
        
        # 展示样例数据
        cursor.execute('''
            SELECT stock_code, change_date, open_price, close_price, volume
            FROM daily_stock_changes
            WHERE stock_code = '000001'
            ORDER BY change_date DESC
            LIMIT 3
        ''')
        sample_data = cursor.fetchall()
        
        print(f"📊 数据统计:")
        print(f"   - 总记录数: {total_records:,}")
        print(f"   - 股票数量: {total_stocks}")
        print(f"   - 日期范围: {date_range[0]} 到 {date_range[1]}")
        
        print(f"\n📋 样例数据 (000001):")
        for row in sample_data:
            print(f"   {row[1]}: 开盘{row[2]} 收盘{row[3]} 成交量{row[4]:,}")

if __name__ == "__main__":
    try:
        records = generate_mock_historical_data()
        verify_generated_data()
        print(f"\n🎉 模拟数据生成完成! 现在可以测试数据优化脚本了。")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()