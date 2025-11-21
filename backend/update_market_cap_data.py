#!/usr/bin/env python3
"""
更新特定股票的市值数据
"""
import asyncio
import sys
import sqlite3

# 添加项目根目录到路径
sys.path.append('/Users/quxiaomeng/工作/code/Claude made stock bot/backend')

from services.tencent_data_service import TencentDataService
from database import DatabaseManager

async def update_market_cap_data():
    """更新特定股票的市值数据"""
    print("🔧 更新股票市值数据")
    print("=" * 50)
    
    # 需要更新的股票
    target_stocks = ['301150', '300300', '301662', '301228']
    
    db_manager = DatabaseManager()
    
    try:
        async with TencentDataService() as service:
            # 获取最新数据
            data = await service.get_stock_data(target_stocks)
            
            # 更新数据库
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock_code in target_stocks:
                    if stock_code in data and data[stock_code]:
                        stock_info = data[stock_code]
                        
                        total_cap = stock_info.get('total_market_cap', 0)
                        circulating_cap = stock_info.get('circulating_market_cap', 0)
                        
                        print(f"📊 更新 {stock_code} ({stock_info.get('stock_name', 'N/A')})")
                        print(f"   总市值: {total_cap:.2f}万元 = {total_cap/10000:.1f}亿元")
                        print(f"   流通市值: {circulating_cap:.2f}万元 = {circulating_cap/10000:.1f}亿元")
                        
                        # 更新今天的数据
                        cursor.execute('''
                            UPDATE daily_stock_changes 
                            SET total_market_cap = ?, circulating_market_cap = ?
                            WHERE stock_code = ? AND trade_date = '2025-11-17'
                        ''', (total_cap, circulating_cap, stock_code))
                        
                        affected = cursor.rowcount
                        print(f"   ✅ 已更新 {affected} 条记录")
                        print()
                    else:
                        print(f"❌ 未能获取 {stock_code} 的数据")
                
                conn.commit()
                print("🎉 数据更新完成")
                
    except Exception as e:
        print(f"❌ 更新失败: {e}")

if __name__ == "__main__":
    asyncio.run(update_market_cap_data())