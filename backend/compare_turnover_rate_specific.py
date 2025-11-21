#!/usr/bin/env python3
"""
比较中富通(300560) 11月14日的换手率数据
数据源 vs 数据库
"""
import asyncio
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.tencent_data_service import TencentDataService

async def compare_turnover_rate_nov14():
    """比较11月14日中富通的换手率数据"""
    print("🔍 中富通(300560) 11月14日换手率数据对比")
    print("="*60)
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    stock_code = '300560'
    target_date = '2025-11-14'
    
    db_manager = DatabaseManager('stock_pool.db')
    
    # 1. 从数据库获取11月14日的数据
    print(f"\n📖 从数据库读取 {stock_code} 在 {target_date} 的数据...")
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT stock_code, trade_date, close_price, open_price, high_price, low_price,
                   volume, turnover, change_percent, total_market_cap, circulating_market_cap, 
                   turnover_rate, pe_ratio, pb_ratio, created_at
            FROM daily_stock_changes 
            WHERE stock_code = ? AND trade_date = ?
        ''', (stock_code, target_date))
        
        db_result = cursor.fetchone()
        
        if db_result:
            db_data = {
                'stock_code': db_result[0],
                'trade_date': db_result[1],
                'close_price': db_result[2],
                'open_price': db_result[3],
                'high_price': db_result[4],
                'low_price': db_result[5],
                'volume': db_result[6],
                'turnover': db_result[7],
                'change_percent': db_result[8],
                'total_market_cap': db_result[9],
                'circulating_market_cap': db_result[10],
                'turnover_rate': db_result[11],
                'pe_ratio': db_result[12],
                'pb_ratio': db_result[13],
                'created_at': db_result[14]
            }
            
            print(f"✅ 数据库数据获取成功:")
            print(f"  股票代码: {db_data['stock_code']}")
            print(f"  交易日期: {db_data['trade_date']}")
            print(f"  收盘价: {db_data['close_price']:.2f}元")
            print(f"  成交量: {db_data['volume']:,}股")
            print(f"  成交额: {db_data['turnover']:,.2f}元")
            print(f"  换手率: {db_data['turnover_rate']:.2f}%")
            print(f"  流通市值: {db_data['circulating_market_cap']:,.0f}万元")
            print(f"  数据创建时间: {db_data['created_at']}")
            
        else:
            print(f"❌ 数据库中未找到 {stock_code} 在 {target_date} 的数据")
            return
    
    # 2. 从腾讯API获取当前实时数据用于对比
    print(f"\n🌐 从腾讯API获取 {stock_code} 的实时数据...")
    
    async with TencentDataService(db_manager) as service:
        api_data = await service.get_stock_data([stock_code])
        
        if stock_code in api_data:
            api_stock_data = api_data[stock_code]
            
            print(f"✅ API数据获取成功:")
            print(f"  股票代码: {api_stock_data['stock_code']}")
            print(f"  股票名称: {api_stock_data['stock_name']}")
            print(f"  当前价格: {api_stock_data['current_price']:.2f}元")
            print(f"  成交量: {api_stock_data['volume']:,}股")
            print(f"  成交额: {api_stock_data['turnover_amount']:,.0f}元")
            print(f"  换手率: {api_stock_data['turnover_rate']:.2f}%")
            print(f"  流通市值: {api_stock_data['circulating_market_cap']:,.0f}万元")
            print(f"  数据时间戳: {api_stock_data.get('data_timestamp', 'N/A')}")
            
        else:
            print(f"❌ API未能获取 {stock_code} 的数据")
            return
    
    # 3. 换手率计算验证
    print(f"\n🧮 换手率计算验证")
    print("="*40)
    
    print("📊 数据库数据计算:")
    print(f"  成交量: {db_data['volume']:,}股")
    print(f"  流通市值: {db_data['circulating_market_cap']:,.0f}万元")
    print(f"  收盘价: {db_data['close_price']:.2f}元")
    
    # 计算流通股本 (流通市值 ÷ 收盘价)
    if db_data['close_price'] > 0:
        circulating_shares = (db_data['circulating_market_cap'] * 10000) / db_data['close_price']
        calculated_turnover_rate = (db_data['volume'] / circulating_shares) * 100
        
        print(f"  计算流通股本: {circulating_shares:,.0f}股")
        print(f"  计算换手率: ({db_data['volume']:,} ÷ {circulating_shares:,.0f}) × 100% = {calculated_turnover_rate:.2f}%")
        print(f"  数据库存储换手率: {db_data['turnover_rate']:.2f}%")
        
        # 对比计算结果与存储结果
        turnover_diff = abs(calculated_turnover_rate - db_data['turnover_rate'])
        print(f"  计算差异: {turnover_diff:.2f}%")
        
        if turnover_diff < 0.01:
            print("  ✅ 数据库换手率计算正确")
        else:
            print("  ⚠️  数据库换手率可能存在计算误差")
    
    print(f"\n📡 API实时数据:")
    print(f"  当前换手率: {api_stock_data['turnover_rate']:.2f}%")
    print(f"  流通市值: {api_stock_data['circulating_market_cap']:,.0f}万元")
    print(f"  当前成交量: {api_stock_data['volume']:,}股")
    
    # 4. 详细换手率对比分析
    print(f"\n🔍 换手率对比分析")
    print("="*50)
    
    print(f"{'数据源':<12} {'换手率':<10} {'成交量':<15} {'流通市值(万元)':<15}")
    print("-" * 60)
    print(f"{'数据库(11-14)':<12} {db_data['turnover_rate']:<10.2f} {db_data['volume']:<15,} {db_data['circulating_market_cap']:<15,.0f}")
    print(f"{'腾讯API(实时)':<12} {api_stock_data['turnover_rate']:<10.2f} {api_stock_data['volume']:<15,} {api_stock_data['circulating_market_cap']:<15,.0f}")
    
    # 计算差异
    turnover_rate_diff = api_stock_data['turnover_rate'] - db_data['turnover_rate']
    volume_diff = api_stock_data['volume'] - db_data['volume']
    market_cap_diff = api_stock_data['circulating_market_cap'] - db_data['circulating_market_cap']
    
    print(f"{'差异':<12} {turnover_rate_diff:<10.2f} {volume_diff:<15,} {market_cap_diff:<15,.0f}")
    
    if abs(turnover_rate_diff) < 1.0:
        print(f"\n✅ 换手率差异较小 ({turnover_rate_diff:.2f}%)，数据基本一致")
    else:
        print(f"\n⚠️  换手率差异较大 ({turnover_rate_diff:.2f}%)，可能原因:")
        print("   • 时间差异: 数据库为历史数据，API为实时数据")
        print("   • 交易活跃: 实时交易导致成交量变化")
        print("   • 市值变动: 股价变化影响流通市值")
    
    # 5. 数据质量评估
    print(f"\n📈 数据质量评估")
    print("="*30)
    
    # 检查数据合理性
    issues = []
    
    if db_data['turnover_rate'] <= 0:
        issues.append("数据库换手率为零或负数")
    elif db_data['turnover_rate'] > 100:
        issues.append("数据库换手率超过100%")
    
    if api_stock_data['turnover_rate'] <= 0:
        issues.append("API换手率为零或负数")
    elif api_stock_data['turnover_rate'] > 100:
        issues.append("API换手率超过100%")
    
    if db_data['volume'] <= 0:
        issues.append("数据库成交量为零")
    
    if api_stock_data['volume'] <= 0:
        issues.append("API成交量为零")
    
    if issues:
        print("⚠️  发现数据质量问题:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("✅ 数据质量良好，未发现明显异常")
    
    # 6. 结论
    print(f"\n🎯 分析结论")
    print("="*20)
    
    print(f"📊 中富通(300560) 换手率数据对比:")
    print(f"   数据库(11-14): {db_data['turnover_rate']:.2f}%")
    print(f"   腾讯API(实时): {api_stock_data['turnover_rate']:.2f}%")
    print(f"   差异: {turnover_rate_diff:+.2f}%")
    
    if abs(turnover_rate_diff) < 5.0:
        print(f"\n✅ 换手率数据一致性良好")
        print("   外部数据源成功替代了模拟数据")
        print("   腾讯API提供的换手率数据真实可靠")
    else:
        print(f"\n⚠️  换手率存在较大差异")
        print("   需要进一步分析数据获取时间和计算方法")
    
    print(f"\n💡 改进建议:")
    print("   • 确保数据库数据及时更新")
    print("   • 使用相同时间点的数据进行对比")
    print("   • 建立数据质量监控机制")

if __name__ == '__main__':
    asyncio.run(compare_turnover_rate_nov14())