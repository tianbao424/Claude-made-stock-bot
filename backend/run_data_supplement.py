#!/usr/bin/env python3
"""
执行A股市值和换手率数据补充
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.external_market_data_fetcher import supplement_a_stock_market_data

async def main():
    """主执行函数"""
    print("🚀 开始执行A股市值和换手率数据补充...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_manager = DatabaseManager('stock_pool.db')
    
    # 获取最新的交易日期
    try:
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT trade_date 
                FROM daily_stock_changes 
                ORDER BY trade_date DESC 
                LIMIT 1
            ''')
            latest_date = cursor.fetchone()
            trade_date = latest_date[0] if latest_date else None
            
        print(f"📅 使用交易日期: {trade_date}")
        
        # 执行数据补充（分批处理，每批500只股票）
        result = await supplement_a_stock_market_data(
            db_manager, 
            trade_date=trade_date,
            limit=500  # 先处理500只，后续可以增加
        )
        
        print("\n📊 数据补充结果:")
        print(f"✅ 成功处理: {result.get('success_count', 0)} 只股票")
        print(f"❌ 失败处理: {result.get('failed_count', 0)} 只股票") 
        print(f"📈 总体处理: {result.get('total_processed', 0)} 只股票")
        print(f"⚡ 数据源分布: {result.get('data_source_stats', {})}")
        
        if result.get('errors'):
            print(f"\n⚠️  处理错误: {len(result['errors'])} 个")
            for error in result['errors'][:5]:  # 只显示前5个错误
                print(f"   - {error}")
                
        print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎉 数据补充完成!")
        
    except Exception as e:
        print(f"❌ 数据补充失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())