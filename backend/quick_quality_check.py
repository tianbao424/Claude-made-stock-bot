#!/usr/bin/env python3
"""
快速检查数据质量和更新效果
"""

import sqlite3
import os
from datetime import datetime

def quick_quality_check():
    """快速检查数据质量"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    print("📊 快速数据质量检查:")
    print("=" * 50)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 总体数据统计
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT stock_code) as total_stocks,
                    COUNT(*) as total_records,
                    MAX(trade_date) as latest_date
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
            ''')
            
            total_stats = cursor.fetchone()
            print(f"📈 总体数据:")
            print(f"   A股数量: {total_stats[0]:,}只")
            print(f"   总记录数: {total_stats[1]:,}条")
            print(f"   最新日期: {total_stats[2]}")
            
            # 2. 模拟数据检查
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN close_price = 10.0 THEN 1 END) as price_10_count,
                    COUNT(CASE WHEN volume = 0 THEN 1 END) as zero_volume_count,
                    COUNT(*) as total
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
            ''')
            
            fake_stats = cursor.fetchone()
            price_10, zero_vol, total = fake_stats
            
            print(f"\n🔍 模拟数据检查:")
            print(f"   价格10.0: {price_10:,}条 ({price_10/total*100:.1f}%)")
            print(f"   零成交量: {zero_vol:,}条 ({zero_vol/total*100:.1f}%)")
            
            if price_10 < total * 0.01:  # 少于1%
                print(f"   ✅ 模拟数据已基本清理完成")
            elif price_10 < total * 0.05:  # 少于5%
                print(f"   ⚠️ 仍有少量模拟数据待处理")
            else:
                print(f"   ❌ 仍有较多模拟数据需要清理")
            
            # 3. 数据天数分布
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT trade_date) as days_count,
                    COUNT(*) as stocks_count
                FROM (
                    SELECT stock_code, COUNT(DISTINCT trade_date) as days_count
                    FROM daily_stock_changes 
                    WHERE LENGTH(stock_code) = 6 
                    AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                    GROUP BY stock_code
                ) AS stock_days
                GROUP BY days_count
                ORDER BY days_count DESC
                LIMIT 5
            ''')
            
            days_dist = cursor.fetchall()
            
            print(f"\n📊 数据天数分布 (Top 5):")
            for days, count in days_dist:
                percentage = count / total_stats[0] * 100
                print(f"   {days:2d}天: {count:4,}只股票 ({percentage:.1f}%)")
            
            # 4. 最新数据质量
            cursor.execute('''
                SELECT 
                    trade_date,
                    COUNT(*) as records,
                    AVG(CASE WHEN volume > 0 THEN 1.0 ELSE 0.0 END) * 100 as volume_rate,
                    AVG(CASE WHEN close_price != 10.0 THEN 1.0 ELSE 0.0 END) * 100 as price_quality
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                GROUP BY trade_date
                ORDER BY trade_date DESC
                LIMIT 5
            ''')
            
            recent_quality = cursor.fetchall()
            
            print(f"\n📅 最近5天数据质量:")
            print(f"日期       | 记录数 | 成交量率 | 价格质量")
            print("-" * 45)
            for date, records, vol_rate, price_qual in recent_quality:
                print(f"{date} | {records:4,} |  {vol_rate:6.1f}% |  {price_qual:6.1f}%")
            
            return {
                'total_stocks': total_stats[0],
                'fake_data_rate': price_10 / total * 100,
                'latest_date': total_stats[2]
            }
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return None

if __name__ == "__main__":
    result = quick_quality_check()
    
    print("\n" + "=" * 50)
    
    if result:
        print("💡 质量总结:")
        if result['fake_data_rate'] < 1:
            print("✅ 数据质量优秀，模拟数据已基本清理")
        elif result['fake_data_rate'] < 5:
            print("⚠️ 数据质量良好，还有少量模拟数据")
        else:
            print("❌ 数据质量需要改善，模拟数据较多")
        
        print(f"📊 关键指标:")
        print(f"   A股数量: {result['total_stocks']:,}只")
        print(f"   模拟数据率: {result['fake_data_rate']:.1f}%")
        print(f"   最新数据: {result['latest_date']}")
    else:
        print("❌ 无法获取数据质量信息")