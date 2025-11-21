#!/usr/bin/env python3
"""
调试港股过滤为什么没有生效
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.reliable_data_fetcher import reliable_data_fetcher

def debug_stock_filtering():
    """调试股票过滤逻辑"""
    
    print("🔍 调试股票代码过滤...")
    
    # 从日志中看到的失败代码
    failing_codes = ['00687', '00938', '600010', '00540', '07200', '300385']
    
    print(f"测试代码: {', '.join(failing_codes)}")
    print("-" * 60)
    
    for code in failing_codes:
        print(f"📊 测试代码: {code}")
        
        # 检查代码验证
        is_valid = reliable_data_fetcher._is_valid_stock_code(code)
        print(f"   验证结果: {'✅ 通过' if is_valid else '❌ 过滤'}")
        
        # 分析代码特征
        clean_code = code.strip()
        if clean_code.startswith('SH') or clean_code.startswith('SZ'):
            clean_code = clean_code[2:]
            
        print(f"   清理后代码: {clean_code}")
        print(f"   代码长度: {len(clean_code)}")
        print(f"   是否数字: {clean_code.isdigit()}")
        
        if len(clean_code) >= 2:
            print(f"   前两位: {clean_code[:2]}")
        
        # 分析为什么没被过滤
        if len(clean_code) == 5:
            print(f"   🏠 这是港股代码（5位）")
        elif len(clean_code) == 6:
            first_two = clean_code[:2]
            if first_two in ['60', '68', '00', '30']:
                print(f"   📈 这是A股代码")
            else:
                print(f"   ❓ 未知A股前缀: {first_two}")
        
        print("-" * 40)

def test_stock_validation_logic():
    """详细测试股票验证逻辑"""
    
    print("\n🧪 详细测试验证逻辑...")
    
    test_codes = ['07200', '00687', '600010', '300385']
    
    for code in test_codes:
        print(f"\n📊 详细分析: {code}")
        
        # 模拟验证过程
        print("   验证步骤:")
        
        # 步骤1：基本检查
        if not code or len(code) < 6:
            print("   ❌ 步骤1失败：代码为空或长度不足6位")
            continue
        else:
            print("   ✅ 步骤1通过：基本格式检查")
        
        # 步骤2：移除前缀
        clean_code = code.strip()
        if clean_code.startswith('SH') or clean_code.startswith('SZ'):
            clean_code = clean_code[2:]
        print(f"   ✅ 步骤2完成：清理后代码 = {clean_code}")
        
        # 步骤3：检查6位数字
        if len(clean_code) != 6 or not clean_code.isdigit():
            print(f"   ❌ 步骤3失败：不是6位数字（长度={len(clean_code)}, 数字={clean_code.isdigit()}）")
            continue
        else:
            print("   ✅ 步骤3通过：6位数字格式")
        
        # 步骤4：检查前缀
        first_two = clean_code[:2]
        valid_prefixes = ['60', '68', '00', '30']
        
        if first_two in valid_prefixes:
            print(f"   ✅ 步骤4通过：有效A股前缀 {first_two}")
        else:
            print(f"   ❌ 步骤4失败：无效前缀 {first_two}")
        
        # 最终结果
        is_valid = reliable_data_fetcher._is_valid_stock_code(code)
        print(f"   🎯 最终结果: {'✅ 有效' if is_valid else '❌ 无效'}")

if __name__ == "__main__":
    print("🔍 开始调试股票代码过滤...")
    print("=" * 70)
    
    debug_stock_filtering()
    
    print("\n" + "=" * 70)
    
    test_stock_validation_logic()