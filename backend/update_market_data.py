#!/usr/bin/env python3
"""
市值和换手率数据更新脚本
使用腾讯财经API获取真实的换手率数据
"""
import asyncio
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.tencent_data_service import supplement_with_tencent_api

async def update_all_market_data():
    """更新所有股票的市值和换手率数据"""
    print("🚀 开始更新A股市值和换手率数据...")
    print("📊 数据源: 腾讯财经API (实时获取换手率)")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_manager = DatabaseManager('stock_pool.db')
    
    # 1. 获取最新的交易日期
    try:
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
        
        if not trade_date:
            print("❌ 未找到交易数据")
            return
        
        # 2. 统计当前数据状况
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM daily_stock_changes WHERE trade_date = ?', (trade_date,))
            total_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM daily_stock_changes 
                WHERE trade_date = ? 
                AND (total_market_cap = 0 OR total_market_cap IS NULL)
            ''', (trade_date,))
            missing_market_cap = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM daily_stock_changes 
                WHERE trade_date = ? 
                AND (turnover_rate = 0 OR turnover_rate IS NULL)
            ''', (trade_date,))
            missing_turnover = cursor.fetchone()[0]
            
        print(f"📊 当前数据状况:")
        print(f"  总股票数: {total_count}")
        print(f"  缺失市值: {missing_market_cap} 只")
        print(f"  缺失换手率: {missing_turnover} 只")
        print(f"  需要更新: {max(missing_market_cap, missing_turnover)} 只")
        
        if max(missing_market_cap, missing_turnover) == 0:
            print("✅ 数据已完整，无需更新")
            return
        
        # 3. 分批更新数据
        batch_size = 1000  # 每批处理1000只股票
        total_updated = 0
        total_success = 0
        
        while True:
            print(f"\n🔄 执行第 {(total_updated // batch_size) + 1} 批数据更新...")
            
            result = await supplement_with_tencent_api(
                db_manager, 
                trade_date=trade_date,
                limit=batch_size
            )
            
            if not result.get('success'):
                print(f"❌ 批次更新失败: {result.get('error', '未知错误')}")
                break
            
            batch_updated = result.get('updated_count', 0)
            batch_success = result.get('success_count', 0)
            
            total_updated += batch_updated
            total_success += batch_success
            
            print(f"📈 本批次结果: 获取 {batch_success} 只, 更新 {batch_updated} 只")
            
            # 如果本批次处理的股票数少于批次大小，说明已经处理完了
            if result.get('total_processed', 0) < batch_size:
                break
            
            # 添加延时避免过于频繁的请求
            await asyncio.sleep(2)
        
        # 4. 最终验证
        print(f"\n🎯 最终统计:")
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM daily_stock_changes 
                WHERE trade_date = ? 
                AND total_market_cap > 0 AND circulating_market_cap > 0
            ''', (trade_date,))
            completed_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM daily_stock_changes 
                WHERE trade_date = ? 
                AND (total_market_cap = 0 OR total_market_cap IS NULL)
            ''', (trade_date,))
            still_missing = cursor.fetchone()[0]
            
            # 数据质量统计
            cursor.execute('''
                SELECT 
                    AVG(turnover_rate) as avg_turnover,
                    AVG(total_market_cap) as avg_market_cap,
                    COUNT(CASE WHEN turnover_rate > 0 AND turnover_rate <= 50 THEN 1 END) as reasonable_turnover,
                    COUNT(*) as total
                FROM daily_stock_changes 
                WHERE trade_date = ?
            ''', (trade_date,))
            
            stats = cursor.fetchone()
            
        completion_rate = (completed_count / total_count) * 100 if total_count > 0 else 0
        
        print(f"✅ 数据补充完成:")
        print(f"  已补充: {completed_count}/{total_count} ({completion_rate:.1f}%)")
        print(f"  仍缺失: {still_missing}")
        print(f"  总更新: {total_updated} 只股票")
        print(f"  总获取: {total_success} 只股票")
        
        print(f"\n📊 数据质量:")
        if stats:
            print(f"  平均换手率: {stats[0]:.2f}%")
            print(f"  平均市值: {stats[1]/10000:.2f}亿元")
            print(f"  合理数据比例: {stats[2]}/{stats[3]} ({stats[2]/stats[3]*100:.1f}%)")
        
        print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎉 市值和换手率数据更新完成!")
        
    except Exception as e:
        print(f"❌ 数据更新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(update_all_market_data())