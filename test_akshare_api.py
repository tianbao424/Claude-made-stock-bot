#!/usr/bin/env python3
"""
AkShare API连接测试脚本
用于诊断当前API接口的可用性
"""

import asyncio
import sys
import traceback
from datetime import datetime

def test_akshare_import():
    """测试akshare导入"""
    try:
        import akshare as ak
        print("✅ akshare模块导入成功")
        print(f"📦 akshare版本: {ak.__version__ if hasattr(ak, '__version__') else 'unknown'}")
        return ak
    except ImportError as e:
        print(f"❌ akshare模块导入失败: {e}")
        print("💡 请运行: pip install akshare")
        return None

def test_network_connection():
    """测试网络连接"""
    try:
        import requests
        # 测试基础网络连接
        response = requests.get("https://www.baidu.com", timeout=10)
        if response.status_code == 200:
            print("✅ 网络连接正常")
            return True
        else:
            print(f"⚠️ 网络连接异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 网络连接失败: {e}")
        return False

def test_a_stock_api(ak):
    """测试A股API"""
    print("\n🔄 测试A股实时数据API...")
    
    # 测试多个不同的API接口
    test_apis = [
        ("stock_zh_a_spot_em", "东方财富A股实时行情"),
        ("stock_info_sh_name_code", "上海交易所股票信息"),
        ("stock_info_sz_name_code", "深圳交易所股票信息"),
    ]
    
    for api_name, description in test_apis:
        try:
            print(f"  📡 测试 {description}...")
            if hasattr(ak, api_name):
                api_func = getattr(ak, api_name)
                data = api_func()
                if data is not None and len(data) > 0:
                    print(f"  ✅ {description} - 获取到 {len(data)} 条数据")
                else:
                    print(f"  ⚠️ {description} - 返回数据为空")
            else:
                print(f"  ❌ {description} - API方法不存在")
        except Exception as e:
            print(f"  ❌ {description} - 调用失败: {str(e)[:100]}")
    
def test_hk_stock_api(ak):
    """测试港股API"""
    print("\n🔄 测试港股实时数据API...")
    
    # 测试港股API
    test_apis = [
        ("stock_hk_spot_em", "东方财富港股实时行情"),
    ]
    
    for api_name, description in test_apis:
        try:
            print(f"  📡 测试 {description}...")
            if hasattr(ak, api_name):
                api_func = getattr(ak, api_name)
                data = api_func()
                if data is not None and len(data) > 0:
                    print(f"  ✅ {description} - 获取到 {len(data)} 条数据")
                    # 显示前几条数据的列名
                    if hasattr(data, 'columns'):
                        print(f"  📋 数据列: {list(data.columns)[:10]}")  # 显示前10列
                else:
                    print(f"  ⚠️ {description} - 返回数据为空")
            else:
                print(f"  ❌ {description} - API方法不存在")
        except Exception as e:
            print(f"  ❌ {description} - 调用失败: {str(e)[:100]}")

def test_specific_stock(ak):
    """测试获取特定股票数据"""
    print("\n🔄 测试获取特定股票数据...")
    
    # 测试几只知名股票
    test_stocks = [
        ("000001", "A", "平安银行"),  # A股
        ("600519", "A", "贵州茅台"),  # A股
        ("00700", "HK", "腾讯控股"),  # 港股
    ]
    
    for symbol, market, name in test_stocks:
        try:
            print(f"  📊 测试 {name} ({symbol}) - {market}股...")
            
            if market == "A":
                # 测试A股数据
                data = ak.stock_zh_a_spot_em()
                stock_data = data[data['代码'] == symbol]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    price = row.get('最新价', 0)
                    change = row.get('涨跌幅', 0)
                    print(f"  ✅ {name} - 价格: {price}, 涨跌幅: {change}%")
                else:
                    print(f"  ⚠️ {name} - 未找到数据")
                    
            elif market == "HK":
                # 测试港股数据
                data = ak.stock_hk_spot_em()
                # 港股代码可能需要处理前导零
                search_code = symbol.lstrip('0')
                stock_data = data[data['代码'].astype(str).str.contains(search_code, na=False)]
                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    price = row.get('最新价', 0)
                    change = row.get('涨跌幅', 0)
                    print(f"  ✅ {name} - 价格: {price}, 涨跌幅: {change}%")
                else:
                    print(f"  ⚠️ {name} - 未找到数据")
                    
        except Exception as e:
            print(f"  ❌ {name} - 获取失败: {str(e)[:100]}")

def main():
    """主测试函数"""
    print("🧪 AkShare API连接诊断测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 1. 测试模块导入
    ak = test_akshare_import()
    if not ak:
        return False
    
    # 2. 测试网络连接
    if not test_network_connection():
        print("⚠️ 网络连接有问题，可能影响API调用")
    
    # 3. 测试A股API
    test_a_stock_api(ak)
    
    # 4. 测试港股API  
    test_hk_stock_api(ak)
    
    # 5. 测试特定股票数据
    test_specific_stock(ak)
    
    print("\n" + "=" * 50)
    print("🎯 测试完成")
    print("\n💡 建议:")
    print("- 如果网络连接失败，请检查网络设置")
    print("- 如果API调用失败，可能是服务器限流或维护")
    print("- 建议在交易时间内测试以获得更准确的结果")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出现意外错误: {e}")
        traceback.print_exc()