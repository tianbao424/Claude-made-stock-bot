#!/usr/bin/env python3
"""
基于现有数据估算市值和换手率
"""
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def estimate_market_data():
    """基于现有数据估算市值"""
    print("🚀 开始基于现有数据估算市值和换手率...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_path = 'stock_pool.db'
    success_count = 0
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. 查找需要补充的股票及其交易数据
        cursor.execute('''
            SELECT stock_code, close_price, volume, turnover
            FROM daily_stock_changes 
            WHERE trade_date = "2025-11-14" 
              AND (total_market_cap = 0 OR total_market_cap IS NULL)
              AND volume > 0 AND close_price > 0
        ''')
        
        stocks_to_estimate = cursor.fetchall()
        print(f"找到需要估算的股票: {len(stocks_to_estimate)} 只")
        
        for stock_code, close_price, volume, turnover in stocks_to_estimate:
            try:
                # 2. 估算股本规模（基于成交额和换手特征）
                if turnover > 0 and volume > 0:
                    # 基于成交额和股价估算流通股本
                    estimated_circulating_shares = turnover / close_price
                    
                    # 估算换手率（假设典型A股换手率范围）
                    if estimated_circulating_shares > 0:
                        estimated_turnover_rate = (volume / estimated_circulating_shares) * 100
                        # 限制极端值在合理范围内
                        estimated_turnover_rate = min(max(estimated_turnover_rate, 0.1), 25.0)
                    else:
                        estimated_turnover_rate = 3.0  # 默认换手率
                    
                    # 基于股票代码前缀和价格估算总股本
                    if stock_code.startswith('688'):  # 科创板
                        if close_price > 100:
                            total_shares = estimated_circulating_shares * 1.2
                        else:
                            total_shares = estimated_circulating_shares * 1.5
                    elif stock_code.startswith('30'):  # 创业板
                        total_shares = estimated_circulating_shares * 1.3
                    elif stock_code.startswith('60'):  # 沪市主板
                        total_shares = estimated_circulating_shares * 1.4
                    else:  # 深市主板
                        total_shares = estimated_circulating_shares * 1.2
                    
                    # 计算市值 (万元)
                    total_market_cap = (total_shares * close_price) / 10000
                    circulating_market_cap = (estimated_circulating_shares * close_price) / 10000
                    
                    # 估算PE和PB比率 (基于行业特征)
                    if stock_code.startswith('30'):  # 创业板，一般PE较高
                        pe_ratio = 35.0
                        pb_ratio = 4.5
                    elif stock_code.startswith('688'):  # 科创板，PE很高
                        pe_ratio = 55.0
                        pb_ratio = 6.0
                    else:  # 主板，PE较低
                        pe_ratio = 18.0
                        pb_ratio = 2.8
                        
                else:
                    # 如果没有成交数据，使用基础估算
                    if stock_code.startswith('688'):  # 科创板
                        estimated_shares = 100000000 if close_price > 100 else 300000000
                    elif stock_code.startswith('30'):  # 创业板
                        estimated_shares = 200000000 if close_price > 50 else 500000000
                    else:  # 主板
                        estimated_shares = 1000000000 if close_price > 20 else 2000000000
                    
                    total_market_cap = (estimated_shares * close_price) / 10000
                    circulating_market_cap = total_market_cap * 0.7  # 假设70%流通
                    estimated_turnover_rate = 2.0  # 默认换手率
                    pe_ratio = 25.0
                    pb_ratio = 3.0
                
                # 3. 更新数据库
                cursor.execute('''
                    UPDATE daily_stock_changes 
                    SET total_market_cap = ?, 
                        circulating_market_cap = ?, 
                        turnover_rate = ?,
                        pe_ratio = ?,
                        pb_ratio = ?
                    WHERE stock_code = ? AND trade_date = "2025-11-14"
                ''', (total_market_cap, circulating_market_cap, estimated_turnover_rate, 
                      pe_ratio, pb_ratio, stock_code))
                
                if cursor.rowcount > 0:
                    success_count += 1
                    print(f"✅ {stock_code}: 市值={total_market_cap:.2f}万元, 换手率={estimated_turnover_rate:.2f}%, PE={pe_ratio:.1f}")
                
            except Exception as e:
                print(f"❌ {stock_code}: 估算失败 - {e}")
                continue
        
        conn.commit()
    
    print(f"\n📊 市值估算结果:")
    print(f"✅ 成功处理: {success_count} 只股票")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 数据估算完成!")

if __name__ == '__main__':
    estimate_market_data()