#!/usr/bin/env python3
"""
测试备用的实时数据API接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime

def test_alternative_realtime_apis():
    """测试其他实时数据API"""
    print("🔄 测试备用实时数据API...")
    
    # 测试不同的实时数据源
    alternative_apis = [
        # A股替代API
        ("stock_zh_a_spot", "A股实时行情-新浪源"),
        ("stock_zh_a_spot_em", "A股实时行情-东方财富源"), # 这个我们知道失败了
        ("stock_individual_info_em", "个股信息-东方财富"),
        
        # 港股替代API
        ("stock_hk_spot", "港股实时行情-新浪源"),
        ("stock_hk_spot_em", "港股实时行情-东方财富源"), # 这个我们知道失败了
    ]
    
    for api_name, description in alternative_apis:
        try:
            print(f"\n  📡 测试 {description}...")
            
            if not hasattr(ak, api_name):
                print(f"  ❌ {description} - API方法不存在")
                continue
                
            api_func = getattr(ak, api_name)
            
            # 不同API可能需要不同参数
            if api_name == "stock_individual_info_em":
                # 这个API需要股票代码参数
                data = api_func(symbol="000001")
            else:
                data = api_func()
            
            if data is not None and len(data) > 0:
                print(f"  ✅ {description} - 获取到 {len(data)} 条数据")
                
                # 显示数据结构
                if isinstance(data, pd.DataFrame):
                    print(f"  📋 数据列: {list(data.columns)[:8]}")  # 显示前8列
                    if len(data) > 0:
                        # 显示第一条记录的关键字段
                        first_row = data.iloc[0]
                        key_fields = []
                        for col in data.columns[:6]:  # 前6个字段
                            key_fields.append(f"{col}: {first_row[col]}")
                        print(f"  📊 样本数据: {', '.join(key_fields)}")
                else:
                    print(f"  📊 数据类型: {type(data)}")
            else:
                print(f"  ⚠️ {description} - 返回数据为空")
                
        except Exception as e:
            error_msg = str(e)[:150]
            if "RemoteDisconnected" in error_msg:
                print(f"  ❌ {description} - 连接被远程服务器断开")
            elif "timeout" in error_msg.lower():
                print(f"  ❌ {description} - 请求超时")
            else:
                print(f"  ❌ {description} - 调用失败: {error_msg}")

def test_specific_stock_alternatives():
    """测试获取特定股票的备用方法"""
    print("\n🔄 测试特定股票的备用获取方法...")
    
    test_stocks = [
        ("000001", "平安银行"),
        ("600519", "贵州茅台"),
    ]
    
    for symbol, name in test_stocks:
        print(f"\n  📊 测试 {name} ({symbol})...")
        
        # 方法1: 尝试个股信息API
        try:
            data = ak.stock_individual_info_em(symbol=symbol)
            if data is not None and len(data) > 0:
                print(f"  ✅ 个股信息API - 获取到 {len(data)} 条信息")
                if isinstance(data, pd.DataFrame):
                    print(f"  📋 信息类型: {list(data.columns) if hasattr(data, 'columns') else '非DataFrame'}")
                else:
                    print(f"  📊 数据内容: {str(data)[:100]}")
            else:
                print(f"  ⚠️ 个股信息API - 无数据")
        except Exception as e:
            print(f"  ❌ 个股信息API - 失败: {str(e)[:100]}")
        
        # 方法2: 尝试历史数据API（最新一天）
        try:
            today = datetime.now().strftime("%Y%m%d")
            yesterday = (datetime.now().replace(day=datetime.now().day-1)).strftime("%Y%m%d")
            
            data = ak.stock_zh_a_daily(symbol=symbol, start_date=yesterday, end_date=today, adjust="")
            if data is not None and len(data) > 0:
                latest = data.iloc[-1]  # 最新一天的数据
                print(f"  ✅ 历史数据API - 最新价格: {latest.get('close', '未知')}")
                print(f"  📊 日期: {latest.get('date', '未知')}, 开盘: {latest.get('open', '未知')}, 最高: {latest.get('high', '未知')}")
            else:
                print(f"  ⚠️ 历史数据API - 无数据")
        except Exception as e:
            print(f"  ❌ 历史数据API - 失败: {str(e)[:100]}")

def test_yahoo_finance_alternative():
    """测试Yahoo Finance作为备用数据源"""
    print("\n🔄 测试Yahoo Finance备用数据源...")
    
    try:
        import yfinance as yf
        print("  ✅ yfinance模块可用")
        
        # 测试几只股票
        test_symbols = [
            ("000001.SZ", "平安银行"),
            ("600519.SS", "贵州茅台"), 
            ("0700.HK", "腾讯控股"),
        ]
        
        for symbol, name in test_symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info:
                    price = info.get('currentPrice') or info.get('regularMarketPrice', '未知')
                    change = info.get('regularMarketChangePercent', '未知')
                    print(f"  ✅ {name} - 价格: {price}, 变化: {change}")
                else:
                    print(f"  ⚠️ {name} - 无信息")
            except Exception as e:
                print(f"  ❌ {name} - Yahoo Finance失败: {str(e)[:50]}")
                
    except ImportError:
        print("  ⚠️ yfinance模块未安装，可运行: pip install yfinance")
        print("  💡 这可以作为备用数据源")

def main():
    print("🧪 备用API数据源测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 测试备用实时API
    test_alternative_realtime_apis()
    
    # 测试特定股票的备用方法
    test_specific_stock_alternatives()
    
    # 测试Yahoo Finance
    test_yahoo_finance_alternative()
    
    print("\n" + "=" * 50)
    print("🎯 备用API测试完成")

if __name__ == "__main__":
    main()