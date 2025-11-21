#!/usr/bin/env python3
"""
检查当前数据库的数据质量
验证历史数据补充是否成功
"""

import sqlite3
import os
from datetime import datetime, timedelta

def check_data_quality():
    """检查数据质量"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    print("📊 检查数据库数据质量...")
    print(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 总体数据统计
            print("\n📈 总体数据统计:")
            cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes")
            total_stocks = cursor.fetchone()[0]
            print(f"   总股票数: {total_stocks}")
            
            cursor.execute("SELECT COUNT(*) FROM daily_stock_changes")
            total_records = cursor.fetchone()[0]
            print(f"   总记录数: {total_records:,}")
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_stock_changes")
            date_range = cursor.fetchone()
            print(f"   日期范围: {date_range[0]} - {date_range[1]}")
            
            # 2. 近期数据覆盖情况
            print("\n📅 近期数据覆盖情况:")
            
            # 最近30天有数据的股票
            cursor.execute('''
                SELECT COUNT(DISTINCT stock_code) 
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-30 days')
            ''')
            stocks_30d = cursor.fetchone()[0]
            coverage_30d = (stocks_30d / total_stocks * 100) if total_stocks > 0 else 0
            print(f"   最近30天有数据的股票: {stocks_30d} ({coverage_30d:.1f}%)")
            
            # 最近7天有数据的股票
            cursor.execute('''
                SELECT COUNT(DISTINCT stock_code) 
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
            ''')
            stocks_7d = cursor.fetchone()[0]
            coverage_7d = (stocks_7d / total_stocks * 100) if total_stocks > 0 else 0
            print(f"   最近7天有数据的股票: {stocks_7d} ({coverage_7d:.1f}%)")
            
            # 今天有数据的股票
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(DISTINCT stock_code) 
                FROM daily_stock_changes 
                WHERE trade_date = ?
            ''', (today,))
            stocks_today = cursor.fetchone()[0]
            print(f"   今天有数据的股票: {stocks_today}")
            
            # 3. 数据完整性分析
            print("\n🔍 数据完整性分析:")
            
            # 按股票统计数据天数
            cursor.execute('''
                SELECT stock_code, COUNT(*) as days_count,
                       MIN(trade_date) as first_date,
                       MAX(trade_date) as last_date
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-30 days')
                GROUP BY stock_code 
                ORDER BY days_count DESC 
                LIMIT 10
            ''')
            
            top_stocks = cursor.fetchall()
            if top_stocks:
                print("   数据最完整的10只股票:")
                for stock_code, days, first_date, last_date in top_stocks:
                    print(f"     {stock_code}: {days}天 ({first_date} - {last_date})")
            
            # 4. 最新数据示例
            print("\n📊 最新数据示例:")
            cursor.execute('''
                SELECT stock_code, trade_date, close_price, volume, change_percent
                FROM daily_stock_changes 
                ORDER BY trade_date DESC, stock_code 
                LIMIT 5
            ''')
            
            recent_data = cursor.fetchall()
            if recent_data:
                print("   最新5条记录:")
                for stock_code, date, close, volume, change in recent_data:
                    volume_str = f"{volume:,}" if volume else "0"
                    print(f"     {stock_code} {date}: 收盘={close}, 成交量={volume_str}, 涨幅={change}%")
            
            # 5. 数据源分析
            print("\n🔧 数据来源分析:")
            cursor.execute('''
                SELECT COUNT(*), 
                       COUNT(CASE WHEN volume > 0 THEN 1 END) as with_volume,
                       COUNT(CASE WHEN change_percent != 0 THEN 1 END) as with_change
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
            ''')
            
            source_stats = cursor.fetchone()
            if source_stats:
                total_recent, with_vol, with_change = source_stats
                vol_rate = (with_vol / total_recent * 100) if total_recent > 0 else 0
                change_rate = (with_change / total_recent * 100) if total_recent > 0 else 0
                print(f"   最近7天记录: {total_recent:,}条")
                print(f"   有成交量数据: {with_vol:,}条 ({vol_rate:.1f}%)")
                print(f"   有涨跌幅数据: {with_change:,}条 ({change_rate:.1f}%)")
            
            # 6. 质量评估
            print("\n✅ 数据质量评估:")
            
            if stocks_30d >= 100:
                print("   ✅ 历史数据覆盖率: 良好")
            elif stocks_30d >= 50:
                print("   ⚠️  历史数据覆盖率: 一般")
            else:
                print("   ❌ 历史数据覆盖率: 不足")
            
            if total_records >= 10000:
                print("   ✅ 数据规模: 充足")
            elif total_records >= 1000:
                print("   ⚠️  数据规模: 一般")
            else:
                print("   ❌ 数据规模: 不足")
            
            if vol_rate >= 80:
                print("   ✅ 数据完整性: 良好")
            elif vol_rate >= 60:
                print("   ⚠️  数据完整性: 一般")
            else:
                print("   ❌ 数据完整性: 不足")
            
    except Exception as e:
        print(f"❌ 检查数据质量失败: {e}")

if __name__ == "__main__":
    check_data_quality()