#!/usr/bin/env python3
"""
分析腾讯API正确的字段映射
"""

def analyze_tencent_api_fields():
    """分析腾讯API字段映射"""
    print("📊 腾讯财经API字段分析")
    print("="*50)
    
    # 基于调试结果的分析
    print("🔍 关键发现:")
    print("1. 成交量单位是'手'，需要乘以100转换为股")
    print("2. 换手率在字段38，值为26.92%，这是合理的")
    print("3. 市值字段的数据存在问题:")
    print("   - 字段51(流通市值): 22.51万元 (明显偏低)")
    print("   - 字段52(总市值): 241.21万元 (明显偏低)")
    print("   - 字段43(总股本): 5.27万股 (数据异常)")
    print("   - 字段44(流通股本): 42.14万股 (数据异常)")
    
    print(f"\n🧮 问题分析:")
    print("问题1: 股本数据单位错误")
    print("  - API返回的股本数据可能不是'万股'单位")
    print("  - 实际流通股本应该是4.2亿股左右")
    print("  - 需要查看其他字段或调整单位")
    
    print(f"\n问题2: 市值字段可能在其他位置")
    print("  - 字段72: 186964785 (可能是以元为单位的流通市值)")
    print("  - 字段73: 229743622 (可能是以元为单位的总市值)")
    print("  - 需要验证这些大数值字段")
    
    # 验证计算
    price = 22.54
    field_72 = 186964785  # 以元为单位
    field_73 = 229743622  # 以元为单位
    
    estimated_circulating_shares_72 = field_72 / price
    estimated_total_shares_73 = field_73 / price
    
    print(f"\n🔢 基于大数值字段的验证:")
    print(f"字段72 ÷ 股价 = {field_72:,} ÷ {price} = {estimated_circulating_shares_72:,.0f}股")
    print(f"字段73 ÷ 股价 = {field_73:,} ÷ {price} = {estimated_total_shares_73:,.0f}股")
    print(f"折算为万股: {estimated_circulating_shares_72/10000:.1f}万股, {estimated_total_shares_73/10000:.1f}万股")
    
    print(f"\n💡 正确字段映射推测:")
    correct_mapping = {
        1: "股票名称", 
        3: "当前价格",
        4: "昨日收盘价",
        5: "今日开盘价", 
        6: "成交量(手)",
        30: "数据时间戳",
        32: "涨跌幅(%)",
        33: "最高价",
        34: "最低价", 
        38: "换手率(%)",
        39: "市盈率",
        46: "市净率",
        72: "流通市值(元)",
        73: "总市值(元)"
    }
    
    for field_num, field_desc in correct_mapping.items():
        print(f"  字段{field_num:2d}: {field_desc}")
    
    print(f"\n🔧 修复建议:")
    print("1. 更新字段索引:")
    print("   - 流通市值: 字段72 (单位:元)")
    print("   - 总市值: 字段73 (单位:元)")
    print("   - 换手率: 字段38 (单位:%)")
    print("   - 成交量: 字段6 × 100 (手转股)")
    
    print(f"\n2. 单位转换:")
    print("   - 市值从元转万元: 除以10000") 
    print("   - 成交量从手转股: 乘以100")
    
    print(f"\n3. 验证数据合理性:")
    print("   - 市值范围检查")
    print("   - 换手率范围检查(0-100%)")
    print("   - 价格正数检查")

if __name__ == '__main__':
    analyze_tencent_api_fields()