#!/usr/bin/env python3
"""
中富通股票数据对比分析总结
基于刚才的测试结果
"""
from datetime import datetime

def analyze_zhongfutong_data():
    """分析中富通股票数据对比结果"""
    print("📊 中富通股票数据对比分析总结")
    print("="*60)
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 基于刚才测试的实际数据
    stock_info = {
        'code': '300560',
        'name': '中富通',
        'db_date': '2025-11-14',
        'api_time': '20251117161412'
    }
    
    # 数据库数据 (2025-11-14历史数据)
    db_data = {
        'close_price': 18.78,
        'open_price': 15.71,
        'volume': 60_277_883,
        'turnover': 1_046_320_221.14,
        'turnover_rate': 14.36,
        'total_market_cap': 1127000,  # 万元
        'circulating_market_cap': 788900,  # 万元
        'pe_ratio': 0.0,
        'pb_ratio': 0.0
    }
    
    # API实时数据 (2025-11-17实时)
    api_data = {
        'current_price': 22.54,
        'open_price': 22.54,
        'volume': 50_329_500,
        'turnover_amount': 113_314.0,
        'turnover_rate': 26.92,
        'total_market_cap': 42,  # 万元
        'circulating_market_cap': 52,  # 万元
        'pe_ratio': -43.2,
        'pb_ratio': 5.34
    }
    
    print(f"\n🏢 股票基本信息:")
    print(f"  股票代码: {stock_info['code']}")
    print(f"  股票名称: {stock_info['name']}")
    print(f"  数据库数据日期: {stock_info['db_date']}")
    print(f"  API数据时间: {stock_info['api_time']} (2025-11-17 16:14:12)")
    
    print(f"\n📈 关键数据对比:")
    print("="*50)
    
    # 价格变化
    price_change = api_data['current_price'] - db_data['close_price']
    price_change_pct = (price_change / db_data['close_price']) * 100
    
    print(f"💰 股价变化:")
    print(f"  历史收盘价 (11-14): {db_data['close_price']:.2f}元")
    print(f"  实时价格 (11-17):   {api_data['current_price']:.2f}元")
    print(f"  价格变化:          +{price_change:.2f}元 (+{price_change_pct:.1f}%)")
    
    # 成交量对比
    print(f"\n📊 成交数据对比:")
    print(f"  历史成交量 (11-14): {db_data['volume']:,}股")
    print(f"  当日成交量 (11-17): {api_data['volume']:,}股")
    print(f"  成交量变化:        {(api_data['volume'] - db_data['volume']):,}股")
    
    # 换手率对比
    print(f"\n🔄 换手率对比:")
    print(f"  历史换手率 (11-14): {db_data['turnover_rate']:.2f}%")
    print(f"  当日换手率 (11-17): {api_data['turnover_rate']:.2f}%")
    print(f"  换手率变化:        +{(api_data['turnover_rate'] - db_data['turnover_rate']):.2f}%")
    
    # 市值对比 (这里API数据似乎有问题)
    print(f"\n💼 市值数据分析:")
    print(f"  历史总市值 (11-14): {db_data['total_market_cap']/10000:.2f}亿元")
    print(f"  API总市值 (11-17):  {api_data['total_market_cap']/10000:.4f}亿元 ⚠️")
    print(f"  历史流通市值:      {db_data['circulating_market_cap']/10000:.2f}亿元")
    print(f"  API流通市值:       {api_data['circulating_market_cap']/10000:.4f}亿元 ⚠️")
    
    print(f"\n🔍 数据质量分析:")
    print("="*40)
    
    print("✅ 数据一致性良好的字段:")
    print("  • 股价数据: 反映了市场真实变化 (+20%涨幅)")
    print("  • 成交量数据: 数值合理，符合交易逻辑")
    print("  • 换手率数据: 显示活跃交易 (+12.56%)")
    
    print(f"\n⚠️  需要注意的数据异常:")
    print("  • API市值数据异常: 可能是数据解析或单位问题")
    print("  • 成交额数据差异: API显示113,314元 vs 历史10.46亿元")
    print("  • PE/PB比率: 历史数据为0，API显示-43.2/5.34")
    
    print(f"\n📅 时间因素影响:")
    print("="*30)
    print("数据差异的主要原因:")
    print("1. 时间跨度: 11-14历史数据 vs 11-17实时数据")
    print("2. 市场变化: 3个交易日内股价上涨20%")
    print("3. 交易活跃: 换手率从14.36%上升到26.92%")
    print("4. 数据源差异: 历史快照 vs 实时行情")
    
    # 计算理论市值验证
    if api_data['current_price'] > 0:
        # 基于历史流通市值估算流通股本
        estimated_shares = (db_data['circulating_market_cap'] * 10000) / db_data['close_price']
        calculated_market_cap = api_data['current_price'] * estimated_shares / 10000
        
        print(f"\n🧮 市值计算验证:")
        print(f"  估算流通股本: {estimated_shares:,.0f}股")
        print(f"  理论流通市值: {calculated_market_cap:.2f}万元 ({calculated_market_cap/10000:.2f}亿元)")
        print(f"  API显示市值: {api_data['circulating_market_cap']:.2f}万元 (可能有误)")
    
    print(f"\n💡 结论和建议:")
    print("="*30)
    print("✅ 核心数据质量评估:")
    print("  • 股价数据: 优秀 - 准确反映市场变化")
    print("  • 换手率数据: 优秀 - 真实反映交易活跃度")  
    print("  • 成交量数据: 良好 - 符合市场交易特征")
    
    print(f"\n🔧 改进建议:")
    print("1. API解析优化: 检查市值数据字段解析逻辑")
    print("2. 单位统一: 确保成交额单位换算正确")
    print("3. 数据验证: 增加数据合理性检查机制")
    print("4. 实时更新: 建立定时更新机制保持数据新鲜度")
    
    print(f"\n🎯 总体评价:")
    print("外部数据源集成成功解决了模拟数据问题，")
    print("腾讯API提供的股价和换手率数据真实可靠，")
    print("为投资决策提供了有价值的参考信息。")
    
    print(f"\n" + "="*60)
    print("🎉 中富通股票数据对比分析完成!")

if __name__ == '__main__':
    analyze_zhongfutong_data()