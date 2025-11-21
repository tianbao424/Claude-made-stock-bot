#!/usr/bin/env python3
"""
使用akshare补充A股市值和换手率数据
"""
import asyncio
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.akshare_service import akshare_service

async def supplement_with_akshare():
    """使用akshare补充市值数据"""
    print("🚀 开始使用AkShare补充A股市值和换手率数据...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_manager = DatabaseManager('stock_pool.db')
    
    # 1. 查找需要补充的股票
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT stock_code 
            FROM daily_stock_changes 
            WHERE trade_date = "2025-11-14" 
              AND (total_market_cap = 0 OR total_market_cap IS NULL)
              AND volume > 0
            ORDER BY volume DESC
        ''')
        
        stock_codes = [row[0] for row in cursor.fetchall()]
    
    print(f"找到需要补充的股票: {len(stock_codes)} 只")
    if stock_codes:
        print(f"股票列表: {stock_codes[:10]}...")  # 显示前10只
    
    if not stock_codes:
        print("没有需要补充的股票")
        return
    
    success_count = 0
    failed_count = 0
    
    # 2. 使用akshare获取实时数据
    try:
        print("📊 获取A股实时数据...")
        stock_data = await akshare_service.get_all_a_stock_realtime_data()
        
        if not stock_data:
            print("❌ 获取A股数据失败")
            return
            
        print(f"📈 获取到 {len(stock_data)} 只股票的实时数据")
        
        # 3. 构建股票代码到数据的映射
        stock_map = {}
        for stock in stock_data:
            code = stock.get('symbol', '')
            if code:
                stock_map[code] = stock
        
        # 4. 更新需要补充的股票
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            for stock_code in stock_codes:
                try:
                    if stock_code in stock_map:
                        stock_info = stock_map[stock_code]
                        
                        # 提取市值数据 (万元) - 根据akshare service的字段名
                        total_market_cap = float(stock_info.get('total_market_cap', 0))
                        circulating_market_cap = float(stock_info.get('circulating_market_cap', 0))
                        turnover_rate = float(stock_info.get('turnover_rate', 0))
                        pe_ratio = float(stock_info.get('pe_ratio', 0)) if stock_info.get('pe_ratio', 0) not in [None, '', '-'] else 0
                        pb_ratio = float(stock_info.get('pb_ratio', 0)) if stock_info.get('pb_ratio', 0) not in [None, '', '-'] else 0
                        
                        # 更新数据库
                        cursor.execute('''
                            UPDATE daily_stock_changes 
                            SET total_market_cap = ?, 
                                circulating_market_cap = ?, 
                                turnover_rate = ?,
                                pe_ratio = ?,
                                pb_ratio = ?
                            WHERE stock_code = ? AND trade_date = "2025-11-14"
                        ''', (total_market_cap, circulating_market_cap, turnover_rate, 
                              pe_ratio, pb_ratio, stock_code))
                        
                        if cursor.rowcount > 0:
                            success_count += 1
                            print(f"✅ {stock_code}: 市值={total_market_cap:.2f}万元, 换手率={turnover_rate:.2f}%")
                        
                    else:
                        print(f"⚠️  {stock_code}: 未找到数据")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"❌ {stock_code}: 处理失败 - {e}")
                    failed_count += 1
                    continue
            
            conn.commit()
            
    except Exception as e:
        print(f"❌ 数据获取失败: {e}")
        return
    
    print(f"\n📊 数据补充结果:")
    print(f"✅ 成功处理: {success_count} 只股票")
    print(f"❌ 失败处理: {failed_count} 只股票")
    print(f"📈 总体处理: {success_count + failed_count} 只股票")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 数据补充完成!")

if __name__ == '__main__':
    asyncio.run(supplement_with_akshare())