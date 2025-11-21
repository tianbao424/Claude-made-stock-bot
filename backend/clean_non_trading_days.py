#!/usr/bin/env python3
"""
清理数据库中的非交易日错误数据
删除周末和节假日的股票数据
"""

import sqlite3
import os
from datetime import datetime
from utils.market_hours import isWeekday, isHoliday, ALL_HOLIDAYS

def clean_non_trading_day_data():
    """清理非交易日数据"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    print("🧹 开始清理非交易日错误数据...")
    print("=" * 50)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 统计清理前的数据
            cursor.execute('SELECT COUNT(*) FROM daily_stock_changes')
            total_before = cursor.fetchone()[0]
            
            print(f"📊 清理前总记录数: {total_before:,}")
            
            # 2. 识别周末数据
            cursor.execute("""
                SELECT COUNT(*) FROM daily_stock_changes 
                WHERE strftime('%w', trade_date) IN ('0', '6')
            """)
            weekend_count = cursor.fetchone()[0]
            
            print(f"🗓️ 周末数据: {weekend_count:,} 条")
            
            # 3. 识别节假日数据
            holiday_placeholders = ','.join(['?' for _ in ALL_HOLIDAYS])
            cursor.execute(f"""
                SELECT COUNT(*) FROM daily_stock_changes 
                WHERE trade_date IN ({holiday_placeholders})
            """, ALL_HOLIDAYS)
            holiday_count = cursor.fetchone()[0]
            
            print(f"🎋 节假日数据: {holiday_count:,} 条")
            
            # 4. 显示即将删除的数据样例
            cursor.execute("""
                SELECT trade_date, COUNT(*) as count
                FROM daily_stock_changes 
                WHERE strftime('%w', trade_date) IN ('0', '6')
                GROUP BY trade_date
                ORDER BY trade_date DESC
                LIMIT 10
            """)
            
            weekend_samples = cursor.fetchall()
            if weekend_samples:
                print(f"\n📅 周末数据示例:")
                for date, count in weekend_samples:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                    weekday = weekday_names[date_obj.weekday()]
                    print(f"   {date} ({weekday}): {count} 条记录")
            
            # 5. 确认删除
            total_to_delete = weekend_count + holiday_count
            if total_to_delete == 0:
                print("✅ 没有发现需要清理的非交易日数据")
                return
            
            print(f"\n⚠️ 即将删除 {total_to_delete:,} 条非交易日数据")
            
            # 6. 执行清理 - 删除周末数据
            print("🗑️ 删除周末数据...")
            cursor.execute("""
                DELETE FROM daily_stock_changes 
                WHERE strftime('%w', trade_date) IN ('0', '6')
            """)
            weekend_deleted = cursor.rowcount
            print(f"   删除周末数据: {weekend_deleted:,} 条")
            
            # 7. 执行清理 - 删除节假日数据
            print("🗑️ 删除节假日数据...")
            cursor.execute(f"""
                DELETE FROM daily_stock_changes 
                WHERE trade_date IN ({holiday_placeholders})
            """, ALL_HOLIDAYS)
            holiday_deleted = cursor.rowcount
            print(f"   删除节假日数据: {holiday_deleted:,} 条")
            
            # 8. 提交更改
            conn.commit()
            
            # 9. 统计清理后的数据
            cursor.execute('SELECT COUNT(*) FROM daily_stock_changes')
            total_after = cursor.fetchone()[0]
            
            print(f"\n📊 清理结果:")
            print(f"   清理前: {total_before:,} 条记录")
            print(f"   清理后: {total_after:,} 条记录")
            print(f"   已删除: {total_before - total_after:,} 条记录")
            print(f"   删除率: {(total_before - total_after) / total_before * 100:.1f}%")
            
            # 10. 验证剩余数据
            cursor.execute("""
                SELECT trade_date, COUNT(*) as count
                FROM daily_stock_changes 
                GROUP BY trade_date
                ORDER BY trade_date DESC
                LIMIT 10
            """)
            
            remaining_samples = cursor.fetchall()
            print(f"\n✅ 清理后数据验证 (最近10个交易日):")
            for date, count in remaining_samples:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                is_trading_day = isWeekday(date_obj) and not isHoliday(date_obj)
                status = "✅ 交易日" if is_trading_day else "❌ 非交易日"
                print(f"   {date}: {count:,} 条记录 - {status}")
            
            return {
                'total_before': total_before,
                'total_after': total_after,
                'deleted_count': total_before - total_after,
                'weekend_deleted': weekend_deleted,
                'holiday_deleted': holiday_deleted
            }
            
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return None

def verify_trading_days():
    """验证清理后的数据是否都是交易日"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    print(f"\n🔍 验证数据完整性...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否还有周末数据
            cursor.execute("""
                SELECT COUNT(*) FROM daily_stock_changes 
                WHERE strftime('%w', trade_date) IN ('0', '6')
            """)
            remaining_weekends = cursor.fetchone()[0]
            
            # 检查是否还有节假日数据
            holiday_placeholders = ','.join(['?' for _ in ALL_HOLIDAYS])
            cursor.execute(f"""
                SELECT COUNT(*) FROM daily_stock_changes 
                WHERE trade_date IN ({holiday_placeholders})
            """, ALL_HOLIDAYS)
            remaining_holidays = cursor.fetchone()[0]
            
            print(f"   剩余周末数据: {remaining_weekends} 条")
            print(f"   剩余节假日数据: {remaining_holidays} 条")
            
            if remaining_weekends == 0 and remaining_holidays == 0:
                print("✅ 数据清理验证通过，所有非交易日数据已清理")
                return True
            else:
                print("⚠️ 仍有非交易日数据残留，可能需要进一步清理")
                return False
                
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    print("🧹 非交易日数据清理工具")
    print("=" * 60)
    
    # 执行清理
    result = clean_non_trading_day_data()
    
    if result:
        # 验证清理结果
        verify_trading_days()
        
        print("\n" + "=" * 60)
        print("💡 清理完成，建议:")
        print("1. 重新运行股票筛选测试")
        print("2. 检查筛选结果是否正确")
        print("3. 验证连续性判断是否准确")
    else:
        print("❌ 清理失败，请检查错误信息")