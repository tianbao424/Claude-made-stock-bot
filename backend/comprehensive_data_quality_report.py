#!/usr/bin/env python3
"""
全面数据质量评估报告
"""
import sqlite3
import sys
from datetime import datetime, timedelta
import json

sys.path.append('/Users/quxiaomeng/工作/code/Claude made stock bot/backend')

from database import DatabaseManager

def generate_comprehensive_data_quality_report():
    """生成全面的数据质量评估报告"""
    print("📊 AI股票聊天助手 - 数据质量评估报告")
    print("=" * 80)
    print(f"🕐 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    db_manager = DatabaseManager()
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 1. 数据库整体概览
        print("🗃️  1. 数据库整体概览")
        print("-" * 50)
        
        # 统计各表的记录数
        tables = ['stock_info', 'daily_stock_changes', 'stock_technical_indicators']
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"  📋 {table}: {count:,} 条记录")
            except Exception as e:
                print(f"  ❌ {table}: 表不存在或查询失败")
        
        # 数据库文件大小
        import os
        db_size = os.path.getsize(db_manager.db_path) / (1024 * 1024)
        print(f"  💾 数据库大小: {db_size:.2f} MB")
        print()
        
        # 2. 股票池完整性分析
        print("🎯 2. 股票池完整性分析")
        print("-" * 50)
        
        # 总体股票统计
        cursor.execute('''
            SELECT 
                COUNT(*) as 总数,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as 活跃数,
                COUNT(CASE WHEN LENGTH(symbol) = 6 THEN 1 END) as A股数量,
                COUNT(CASE WHEN LENGTH(symbol) = 5 THEN 1 END) as 港股数量,
                COUNT(CASE WHEN market = 'SH' THEN 1 END) as 上海股票,
                COUNT(CASE WHEN market = 'SZ' THEN 1 END) as 深圳股票,
                COUNT(CASE WHEN market = 'HK' THEN 1 END) as 港股统计,
                COUNT(CASE WHEN market = '' OR market IS NULL THEN 1 END) as 未分类
            FROM stock_info 
            WHERE LENGTH(symbol) IN (5, 6)
        ''')
        
        stats = cursor.fetchone()
        total, active, a_stocks, hk_stocks, sh_stocks, sz_stocks, hk_market, unknown = stats
        
        print(f"  📊 股票池总览:")
        print(f"     • 总股票数: {total:,} 只")
        print(f"     • 活跃股票: {active:,} 只 ({active/total*100:.1f}%)")
        print(f"     • A股合计: {a_stocks:,} 只")
        print(f"     • 港股合计: {hk_stocks:,} 只")
        print()
        
        print(f"  🏢 市场分布:")
        print(f"     • 上海证券交易所: {sh_stocks:,} 只")
        print(f"     • 深圳证券交易所: {sz_stocks:,} 只") 
        print(f"     • 香港证券交易所: {hk_market:,} 只")
        print(f"     • 未分类股票: {unknown:,} 只")
        print()
        
        # 3. 交易数据时效性分析
        print("📅 3. 交易数据时效性分析") 
        print("-" * 50)
        
        # 最新交易日期
        cursor.execute('SELECT MAX(trade_date) FROM daily_stock_changes')
        latest_date = cursor.fetchone()[0]
        
        # 各市场最新数据分布
        cursor.execute('''
            SELECT 
                s.market,
                MAX(d.trade_date) as 最新日期,
                COUNT(DISTINCT CASE WHEN d.trade_date >= '2025-11-18' THEN d.stock_code END) as 近期数据,
                COUNT(DISTINCT d.stock_code) as 有数据股票
            FROM stock_info s
            LEFT JOIN daily_stock_changes d ON s.symbol = d.stock_code
            WHERE s.is_active = 1 AND LENGTH(s.symbol) IN (5, 6)
            GROUP BY s.market
            ORDER BY 有数据股票 DESC
        ''')
        
        market_data = cursor.fetchall()
        today = datetime.now().strftime('%Y-%m-%d')
        
        print(f"  📆 数据时效性:")
        print(f"     • 最新数据日期: {latest_date}")
        print(f"     • 当前日期: {today}")
        print()
        
        print(f"  🏢 各市场数据情况:")
        total_recent = 0
        total_stocks_with_data = 0
        
        for market, latest, recent, with_data in market_data:
            market_name = {
                'SH': '上海A股', 'SZ': '深圳A股', 'HK': '港股',
                '': '未分类', None: '未分类'
            }.get(market, market or '未分类')
            
            if latest:
                days_behind = (datetime.now() - datetime.strptime(latest, '%Y-%m-%d')).days
                freshness = "🟢 最新" if days_behind <= 1 else "🟡 较新" if days_behind <= 3 else "🔴 滞后"
            else:
                freshness = "❌ 无数据"
                days_behind = -1
            
            print(f"     • {market_name}: {with_data:,}只有数据, 近期{recent:,}只, {freshness}")
            
            total_recent += recent
            total_stocks_with_data += with_data
        
        print(f"     • 总计: {total_stocks_with_data:,}只有交易数据, 其中{total_recent:,}只为近期数据")
        print()
        
        # 4. 数据完整性评估
        print("🔍 4. 数据完整性评估")
        print("-" * 50)
        
        # 检查关键字段完整性
        cursor.execute('''
            SELECT 
                COUNT(*) as 总记录,
                COUNT(CASE WHEN close_price > 0 THEN 1 END) as 有效价格,
                COUNT(CASE WHEN volume > 0 THEN 1 END) as 有效成交量,
                COUNT(CASE WHEN turnover > 0 THEN 1 END) as 有效成交额,
                COUNT(CASE WHEN total_market_cap > 0 THEN 1 END) as 有效市值,
                COUNT(CASE WHEN turnover_rate > 0 THEN 1 END) as 有效换手率
            FROM daily_stock_changes 
            WHERE trade_date >= '2025-11-15'
        ''')
        
        completeness = cursor.fetchone()
        total_records, valid_price, valid_volume, valid_turnover, valid_market_cap, valid_turnover_rate = completeness
        
        print(f"  📋 关键字段完整性 (近期数据):")
        if total_records > 0:
            print(f"     • 总记录数: {total_records:,} 条")
            print(f"     • 有效价格: {valid_price:,} ({valid_price/total_records*100:.1f}%)")
            print(f"     • 有效成交量: {valid_volume:,} ({valid_volume/total_records*100:.1f}%)")
            print(f"     • 有效成交额: {valid_turnover:,} ({valid_turnover/total_records*100:.1f}%)")
            print(f"     • 有效市值: {valid_market_cap:,} ({valid_market_cap/total_records*100:.1f}%)")
            print(f"     • 有效换手率: {valid_turnover_rate:,} ({valid_turnover_rate/total_records*100:.1f}%)")
        else:
            print(f"     ❌ 没有近期数据记录")
        print()
        
        # 5. 数据质量异常检测
        print("⚠️  5. 数据质量异常检测")
        print("-" * 50)
        
        # 异常价格检测
        cursor.execute('''
            SELECT COUNT(*) 
            FROM daily_stock_changes 
            WHERE trade_date >= '2025-11-15' 
              AND (close_price <= 0 OR close_price > 10000)
        ''')
        abnormal_prices = cursor.fetchone()[0]
        
        # 异常成交量检测
        cursor.execute('''
            SELECT COUNT(*) 
            FROM daily_stock_changes 
            WHERE trade_date >= '2025-11-15' 
              AND volume < 0
        ''')
        abnormal_volumes = cursor.fetchone()[0]
        
        # 缺失数据检测
        cursor.execute('''
            SELECT COUNT(*) 
            FROM stock_info s 
            WHERE s.is_active = 1 
              AND LENGTH(s.symbol) IN (5, 6)
              AND NOT EXISTS (
                  SELECT 1 FROM daily_stock_changes d 
                  WHERE d.stock_code = s.symbol 
                    AND d.trade_date >= '2025-11-15'
              )
        ''')
        missing_recent_data = cursor.fetchone()[0]
        
        print(f"  🔍 数据异常统计:")
        print(f"     • 异常价格记录: {abnormal_prices:,} 条")
        print(f"     • 异常成交量记录: {abnormal_volumes:,} 条") 
        print(f"     • 缺失近期数据的活跃股票: {missing_recent_data:,} 只")
        print()
        
        # 6. 性能指标分析
        print("⚡ 6. 系统性能指标")
        print("-" * 50)
        
        # 查询性能测试
        import time
        
        # 测试基础查询性能
        start_time = time.time()
        cursor.execute('''
            SELECT COUNT(*) FROM daily_stock_changes 
            WHERE trade_date >= '2025-11-15'
        ''')
        basic_query_time = time.time() - start_time
        
        # 测试复杂查询性能
        start_time = time.time()
        cursor.execute('''
            SELECT s.market, AVG(d.close_price), COUNT(*)
            FROM stock_info s
            JOIN daily_stock_changes d ON s.symbol = d.stock_code
            WHERE d.trade_date >= '2025-11-15' AND s.is_active = 1
            GROUP BY s.market
        ''')
        complex_query_time = time.time() - start_time
        
        print(f"  🚀 查询性能测试:")
        print(f"     • 基础查询耗时: {basic_query_time:.3f} 秒")
        print(f"     • 复杂查询耗时: {complex_query_time:.3f} 秒")
        print()
        
        # 7. 数据质量评分
        print("📊 7. 综合数据质量评分")
        print("-" * 50)
        
        # 计算各维度评分
        completeness_score = (valid_price / total_records * 100) if total_records > 0 else 0
        freshness_score = (total_recent / total_stocks_with_data * 100) if total_stocks_with_data > 0 else 0
        coverage_score = (total_stocks_with_data / active * 100) if active > 0 else 0
        accuracy_score = max(0, 100 - (abnormal_prices + abnormal_volumes) / total_records * 100) if total_records > 0 else 0
        
        # 综合评分
        overall_score = (completeness_score + freshness_score + coverage_score + accuracy_score) / 4
        
        print(f"  📈 质量评分明细:")
        print(f"     • 数据完整性: {completeness_score:.1f}/100")
        print(f"     • 数据时效性: {freshness_score:.1f}/100")  
        print(f"     • 数据覆盖率: {coverage_score:.1f}/100")
        print(f"     • 数据准确性: {accuracy_score:.1f}/100")
        print()
        
        # 等级判定
        if overall_score >= 90:
            grade = "🟢 优秀 (A级)"
        elif overall_score >= 80:
            grade = "🟡 良好 (B级)"
        elif overall_score >= 70:
            grade = "🟠 一般 (C级)"
        else:
            grade = "🔴 较差 (D级)"
        
        print(f"  🏆 综合质量评分: {overall_score:.1f}/100 - {grade}")
        print()
        
        # 8. 改进建议
        print("💡 8. 数据质量改进建议")
        print("-" * 50)
        
        suggestions = []
        
        if freshness_score < 80:
            suggestions.append("🔄 建议增加数据更新频率，特别是港股数据")
        
        if completeness_score < 90:
            suggestions.append("🔍 建议检查数据采集流程，提高关键字段完整性")
        
        if abnormal_prices > 0:
            suggestions.append("🛠️ 建议添加数据验证规则，过滤异常价格数据")
        
        if missing_recent_data > active * 0.1:
            suggestions.append("📊 建议检查数据采集覆盖范围，减少缺失数据")
        
        if coverage_score < 95:
            suggestions.append("🎯 建议扩大数据采集范围，提高股票覆盖率")
        
        if not suggestions:
            suggestions.append("✅ 数据质量良好，建议保持当前数据采集和维护策略")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        print()
        print("=" * 80)
        print(f"📋 报告生成完成 | 分析对象: {active:,}只活跃股票 | 综合评分: {overall_score:.1f}/100")

if __name__ == "__main__":
    generate_comprehensive_data_quality_report()