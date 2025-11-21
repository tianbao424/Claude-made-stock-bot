#!/usr/bin/env python3
"""
港股数据问题专项分析
"""
import sqlite3
import sys
import asyncio

sys.path.append('/Users/quxiaomeng/工作/code/Claude made stock bot/backend')

from database import DatabaseManager
from services.tencent_data_service import TencentDataService

async def analyze_hk_data_issue():
    """分析港股数据缺失问题"""
    print("🇭🇰 港股数据问题专项分析")
    print("=" * 60)
    
    db_manager = DatabaseManager()
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 1. 港股基本情况
        print("📊 1. 港股数据基本情况")
        print("-" * 40)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as 总数,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as 活跃数
            FROM stock_info 
            WHERE market = 'HK' OR LENGTH(symbol) = 5
        ''')
        
        hk_total, hk_active = cursor.fetchone()
        print(f"  港股总数: {hk_total:,} 只")
        print(f"  活跃港股: {hk_active:,} 只")
        print()
        
        # 2. 港股交易数据分布
        print("📅 2. 港股交易数据时间分布")
        print("-" * 40)
        
        cursor.execute('''
            SELECT 
                d.trade_date,
                COUNT(*) as 记录数
            FROM daily_stock_changes d
            JOIN stock_info s ON d.stock_code = s.symbol
            WHERE (s.market = 'HK' OR LENGTH(s.symbol) = 5)
            GROUP BY d.trade_date
            ORDER BY d.trade_date DESC
            LIMIT 10
        ''')
        
        hk_data_by_date = cursor.fetchall()
        print(f"  最近港股数据分布:")
        for date, count in hk_data_by_date:
            print(f"    {date}: {count:,} 条记录")
        print()
        
        # 3. 选取样本港股测试腾讯API
        print("🔌 3. 腾讯API港股支持测试")
        print("-" * 40)
        
        cursor.execute('''
            SELECT symbol, name 
            FROM stock_info 
            WHERE market = 'HK' AND is_active = 1
            LIMIT 10
        ''')
        
        hk_samples = cursor.fetchall()
        print(f"  测试样本港股 (前10只):")
        for symbol, name in hk_samples:
            print(f"    {symbol} - {name}")
        print()
        
        # 测试腾讯API对港股的支持
        print(f"  🧪 腾讯API测试结果:")
        
        try:
            async with TencentDataService() as service:
                test_codes = [sample[0] for sample in hk_samples[:5]]  # 测试前5只
                
                for code in test_codes:
                    try:
                        # 尝试获取单只股票数据
                        data = await service.get_stock_data([code])
                        
                        if code in data and data[code]:
                            price = data[code].get('current_price', 0)
                            print(f"    ✅ {code}: 价格 {price}")
                        else:
                            print(f"    ❌ {code}: 无数据返回")
                    except Exception as e:
                        print(f"    ❌ {code}: API调用失败 - {str(e)[:50]}")
                
        except Exception as e:
            print(f"    ❌ 腾讯API服务初始化失败: {e}")
        
        print()
        
        # 4. 港股代码格式分析
        print("🔍 4. 港股代码格式分析")
        print("-" * 40)
        
        cursor.execute('''
            SELECT 
                LENGTH(symbol) as 代码长度,
                COUNT(*) as 数量,
                GROUP_CONCAT(symbol, ', ') as 示例代码
            FROM stock_info 
            WHERE market = 'HK' 
            GROUP BY LENGTH(symbol)
            ORDER BY 数量 DESC
        ''')
        
        hk_code_formats = cursor.fetchall()
        print(f"  港股代码格式分析:")
        for length, count, examples in hk_code_formats:
            example_codes = examples.split(', ')[:3] if examples else []
            print(f"    {length}位代码: {count:,} 只 (例: {', '.join(example_codes)})")
        print()
        
        # 5. 建议解决方案
        print("💡 5. 问题分析与解决建议")
        print("-" * 40)
        
        print(f"  📋 问题总结:")
        print(f"    • 港股数据最新日期: {hk_data_by_date[0][0] if hk_data_by_date else '无数据'}")
        print(f"    • 数据滞后天数: {'8+天' if hk_data_by_date and hk_data_by_date[0][0] < '2025-11-15' else '未知'}")
        print(f"    • 腾讯API港股支持: 有限/不支持")
        print()
        
        print(f"  🔧 解决方案建议:")
        print(f"    1. 🌐 考虑集成港股专用数据源 (如雅虎财经、富途API)")
        print(f"    2. 🔄 设置港股数据更新策略 (港股交易时间UTC+8)")
        print(f"    3. 🏷️  优化港股代码格式处理 (5位数字代码)")
        print(f"    4. ⚠️  在前端标明港股数据的限制和更新频率")
        print(f"    5. 📊 考虑港股数据的手动更新或第三方数据购买")

if __name__ == "__main__":
    asyncio.run(analyze_hk_data_issue())