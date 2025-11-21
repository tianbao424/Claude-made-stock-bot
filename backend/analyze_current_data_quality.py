#!/usr/bin/env python3
"""
分析当前数据质量和问题
检查数据库中的股票代码分布和采集情况
"""

import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_current_data():
    """分析当前数据质量"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    print("📊 分析当前数据质量...")
    print("=" * 60)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 总体数据统计
            print("1️⃣ 总体数据统计:")
            cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes")
            total_stocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM daily_stock_changes")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_stock_changes")
            date_range = cursor.fetchone()
            
            print(f"   - 总股票数: {total_stocks:,}")
            print(f"   - 总记录数: {total_records:,}")
            print(f"   - 日期范围: {date_range[0]} ~ {date_range[1]}")
            
            # 2. 股票代码类型分析
            print("\n2️⃣ 股票代码类型分析:")
            cursor.execute("SELECT DISTINCT stock_code FROM daily_stock_changes ORDER BY stock_code")
            all_codes = [row[0] for row in cursor.fetchall()]
            
            code_analysis = analyze_stock_codes(all_codes)
            for category, codes in code_analysis.items():
                print(f"   - {category}: {len(codes)}个")
                if codes:
                    sample = codes[:5]
                    print(f"     示例: {', '.join(sample)}{'...' if len(codes) > 5 else ''}")
            
            # 3. 最近数据情况
            print("\n3️⃣ 最近数据情况:")
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            for date_label, date_val in [('今天', today), ('昨天', yesterday), ('一周前', last_week)]:
                cursor.execute('''
                    SELECT COUNT(DISTINCT stock_code) 
                    FROM daily_stock_changes 
                    WHERE trade_date = ?
                ''', (date_val,))
                count = cursor.fetchone()[0]
                print(f"   - {date_label} ({date_val}): {count:,}只股票")
            
            # 4. 数据质量检查
            print("\n4️⃣ 数据质量检查:")
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN volume > 0 THEN 1 END) as with_volume,
                    COUNT(CASE WHEN close_price > 0 THEN 1 END) as with_price,
                    COUNT(CASE WHEN change_percent != 0 THEN 1 END) as with_change
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
            ''')
            
            quality = cursor.fetchone()
            if quality:
                total, with_vol, with_price, with_change = quality
                print(f"   - 最近7天记录: {total:,}条")
                print(f"   - 有成交量: {with_vol:,} ({with_vol/total*100:.1f}%)")
                print(f"   - 有价格: {with_price:,} ({with_price/total*100:.1f}%)")
                print(f"   - 有涨跌幅: {with_change:,} ({with_change/total*100:.1f}%)")
            
            # 5. 采集成功率分析
            print("\n5️⃣ 最近采集情况:")
            cursor.execute('''
                SELECT trade_date, COUNT(DISTINCT stock_code) as stock_count
                FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
                GROUP BY trade_date
                ORDER BY trade_date DESC
            ''')
            
            recent_data = cursor.fetchall()
            if recent_data:
                print("   最近7天每日采集数:")
                for date, count in recent_data:
                    print(f"     {date}: {count:,}只股票")
            else:
                print("   ❌ 最近7天无数据")
            
            return {
                'total_stocks': total_stocks,
                'total_records': total_records,
                'code_analysis': code_analysis,
                'recent_data': recent_data
            }
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return None

def analyze_stock_codes(codes):
    """分析股票代码类型分布"""
    
    analysis = {
        'A股主板(60/68)': [],
        'A股深市(00/30)': [],
        'A股其他': [],
        'B股': [],
        '港股(5位)': [],
        '其他格式': []
    }
    
    for code in codes:
        if not code:
            continue
            
        clean_code = code.strip()
        if clean_code.startswith('SH') or clean_code.startswith('SZ'):
            clean_code = clean_code[2:]
        
        if len(clean_code) == 5:
            analysis['港股(5位)'].append(code)
        elif len(clean_code) == 6 and clean_code.isdigit():
            prefix = clean_code[:2]
            if prefix in ['60', '68']:
                analysis['A股主板(60/68)'].append(code)
            elif prefix in ['00', '30']:
                analysis['A股深市(00/30)'].append(code)
            elif prefix in ['90', '20']:
                analysis['B股'].append(code)
            else:
                analysis['A股其他'].append(code)
        else:
            analysis['其他格式'].append(code)
    
    return analysis

def quick_sample_test():
    """快速采样测试成功率"""
    
    print("\n🧪 快速采样测试...")
    print("=" * 60)
    
    # 从数据库中随机选择20只A股进行测试
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 获取A股代码样本
            cursor.execute('''
                SELECT DISTINCT stock_code 
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                ORDER BY RANDOM() 
                LIMIT 20
            ''')
            
            sample_codes = [row[0] for row in cursor.fetchall()]
            
            if not sample_codes:
                print("❌ 没有找到A股代码样本")
                return
            
            print(f"📊 测试样本: {len(sample_codes)}只A股")
            print(f"代码: {', '.join(sample_codes[:10])}...")
            
            # 使用可靠数据源测试
            import asyncio
            from services.reliable_data_fetcher import reliable_data_fetcher
            
            async def test_samples():
                success = 0
                failed = 0
                
                for code in sample_codes:
                    try:
                        df = await reliable_data_fetcher.fetch_stock_history(code, 1)
                        if df is not None and not df.empty:
                            success += 1
                            print(f"✅ {code}: 成功")
                        else:
                            failed += 1
                            print(f"❌ {code}: 失败")
                    except Exception as e:
                        failed += 1
                        print(f"❌ {code}: 异常 - {e}")
                    
                    # 避免请求过频
                    await asyncio.sleep(0.5)
                
                success_rate = success / len(sample_codes) * 100 if sample_codes else 0
                print(f"\n📊 快速测试结果:")
                print(f"   成功: {success}/{len(sample_codes)} ({success_rate:.1f}%)")
                
                return success_rate
            
            return asyncio.run(test_samples())
            
    except Exception as e:
        print(f"❌ 快速测试失败: {e}")
        return 0

def recommend_collection_strategy(analysis_result, success_rate):
    """基于分析结果推荐采集策略"""
    
    print("\n💡 采集策略建议:")
    print("=" * 60)
    
    if not analysis_result:
        print("❌ 无法分析，建议手动检查数据库")
        return
    
    total_stocks = analysis_result['total_stocks']
    code_analysis = analysis_result['code_analysis']
    
    # 计算有效A股数量
    a_stock_count = (len(code_analysis.get('A股主板(60/68)', [])) + 
                    len(code_analysis.get('A股深市(00/30)', [])))
    
    # 计算无效股票比例
    invalid_count = (len(code_analysis.get('港股(5位)', [])) + 
                    len(code_analysis.get('B股', [])) + 
                    len(code_analysis.get('其他格式', [])))
    
    invalid_rate = invalid_count / total_stocks * 100 if total_stocks > 0 else 0
    
    print(f"📊 股票构成分析:")
    print(f"   - 有效A股: {a_stock_count:,}只")
    print(f"   - 无效股票: {invalid_count:,}只 ({invalid_rate:.1f}%)")
    
    # 基于成功率给出建议
    if success_rate >= 80:
        print("✅ 数据源质量: 优秀")
        print("🔧 建议策略: 可以进行全量采集")
        print("📅 建议频率: 每天采集1天数据，或每周采集7天数据")
    elif success_rate >= 60:
        print("⚠️ 数据源质量: 良好")
        print("🔧 建议策略: 分批采集，避免大量失败")
        print("📅 建议频率: 每天采集1天数据")
    elif success_rate >= 40:
        print("❌ 数据源质量: 一般")
        print("🔧 建议策略: 小批量采集，重点采集主要股票")
        print("📅 建议频率: 重要股票每天采集")
    else:
        print("❌ 数据源质量: 较差")
        print("🔧 建议策略: 需要优化数据源或降级到模拟数据")
    
    # 数据库清理建议
    if invalid_rate > 30:
        print("\n🧹 数据库清理建议:")
        print(f"   - 发现{invalid_rate:.1f}%的无效股票代码")
        print("   - 建议清理港股和B股数据，专注A股")
        print("   - 可以提高采集效率和数据质量")

if __name__ == "__main__":
    print("🔍 开始分析当前数据质量...")
    
    # 1. 分析数据库数据
    analysis_result = analyze_current_data()
    
    # 2. 快速采样测试
    success_rate = quick_sample_test()
    
    # 3. 给出建议
    recommend_collection_strategy(analysis_result, success_rate)
    
    print("\n" + "=" * 60)
    print("📝 总结: 基于以上分析制定数据采集策略")