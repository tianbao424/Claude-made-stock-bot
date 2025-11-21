#!/usr/bin/env python3
"""
调试MACD计算问题
"""
import asyncio
import sys
import os
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.technical_indicator_service import TechnicalIndicatorService
from backend.database import DatabaseManager

def test_macd_calculation_directly():
    """直接测试MACD计算逻辑"""
    print("🧪 直接测试MACD计算逻辑...")
    
    # 创建测试数据
    test_prices = [10.0, 10.1, 10.2, 10.15, 10.3, 10.25, 10.4, 10.35, 10.5, 10.45,
                   10.6, 10.55, 10.7, 10.65, 10.8, 10.75, 10.9, 10.85, 11.0, 10.95,
                   11.1, 11.05, 11.2, 11.15, 11.3, 11.25, 11.4, 11.35, 11.5, 11.45]
    
    close_series = pd.Series(test_prices)
    print(f"测试数据长度: {len(close_series)}")
    print(f"数据范围: {close_series.min():.2f} - {close_series.max():.2f}")
    
    # 创建技术指标服务实例
    db_manager = DatabaseManager()
    tech_service = TechnicalIndicatorService(db_manager)
    
    # 测试MACD计算
    result = tech_service._calculate_macd(close_series)
    print(f"MACD计算结果: {result}")
    
    # 手动计算MACD验证
    print("\n📊 手动验证MACD计算...")
    ema_fast = close_series.ewm(span=12).mean()
    ema_slow = close_series.ewm(span=26).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=9).mean()
    hist = (dif - dea) * 2
    
    print(f"EMA12 最后值: {ema_fast.iloc[-1]:.6f}")
    print(f"EMA26 最后值: {ema_slow.iloc[-1]:.6f}")
    print(f"DIF 最后值: {dif.iloc[-1]:.6f}")
    print(f"DEA 最后值: {dea.iloc[-1]:.6f}")
    print(f"HIST 最后值: {hist.iloc[-1]:.6f}")
    
    return result

async def test_macd_with_real_data():
    """使用真实数据测试MACD计算"""
    print("🔍 使用真实数据测试MACD计算...")
    
    db_manager = DatabaseManager('stock_pool.db')
    tech_service = TechnicalIndicatorService(db_manager)
    
    # 获取一些真实股票数据
    with sqlite3.connect(db_manager.db_path) as conn:
        query = '''
            SELECT trade_date, close_price, open_price, high_price, low_price, volume
            FROM daily_stock_changes
            WHERE stock_code = '000001'
            AND close_price > 0 AND volume > 0
            ORDER BY trade_date ASC
        '''
        df = pd.read_sql_query(query, conn)
    
    print(f"找到 {len(df)} 条有效数据")
    if len(df) < 26:
        print("❌ 数据不足，无法计算MACD")
        return None
    
    print("前5条数据:")
    print(df.head())
    print("最后5条数据:")
    print(df.tail())
    
    # 测试MACD计算
    close_series = df['close_price']
    result = tech_service._calculate_macd(close_series)
    print(f"\n✅ MACD计算结果: {result}")
    
    # 检查数据质量
    print(f"\n📈 数据质量检查:")
    print(f"- 价格范围: {close_series.min():.2f} - {close_series.max():.2f}")
    print(f"- 是否有NaN: {close_series.isna().any()}")
    print(f"- 是否有零值: {(close_series == 0).any()}")
    print(f"- 数据类型: {close_series.dtype}")
    
    return result

async def test_complete_indicators():
    """测试完整的技术指标计算流程"""
    print("🔄 测试完整的技术指标计算流程...")
    
    db_manager = DatabaseManager('stock_pool.db')
    tech_service = TechnicalIndicatorService(db_manager)
    
    # 测试完整指标计算
    indicators = await tech_service.calculate_all_indicators('000001', days=60)
    
    print(f"计算的指标数量: {len(indicators)}")
    if indicators:
        print("MACD相关指标:")
        macd_indicators = {k: v for k, v in indicators.items() if 'macd' in k.lower()}
        for key, value in macd_indicators.items():
            print(f"  {key}: {value}")
        
        print("\n所有指标:")
        for key, value in indicators.items():
            print(f"  {key}: {value}")
    else:
        print("❌ 没有计算出任何指标")
    
    return indicators

async def debug_data_retrieval():
    """调试数据获取过程"""
    print("🔎 调试数据获取过程...")
    
    db_manager = DatabaseManager('stock_pool.db')
    tech_service = TechnicalIndicatorService(db_manager)
    
    # 测试数据获取
    df = await tech_service._get_stock_history('000001', 60)
    
    if df is not None:
        print(f"获取到数据: {len(df)} 条")
        print(f"列名: {list(df.columns)}")
        print(f"数据类型:")
        print(df.dtypes)
        print(f"\n前5行:")
        print(df.head())
        print(f"\n最后5行:")
        print(df.tail())
        
        # 检查关键列的数据质量
        for col in ['close_price', 'open_price', 'high_price', 'low_price']:
            if col in df.columns:
                series = df[col]
                print(f"\n{col} 数据质量:")
                print(f"  - 数量: {len(series)}")
                print(f"  - 非空: {series.notna().sum()}")
                print(f"  - 范围: {series.min():.2f} - {series.max():.2f}")
                print(f"  - 数据类型: {series.dtype}")
        
        return df
    else:
        print("❌ 未获取到数据")
        return None

async def main():
    """主函数"""
    print("🧪 开始MACD计算调试...")
    
    try:
        # 1. 直接测试MACD计算逻辑
        print("\n" + "="*50)
        test_macd_calculation_directly()
        
        # 2. 调试数据获取
        print("\n" + "="*50)
        df = await debug_data_retrieval()
        
        # 3. 使用真实数据测试
        print("\n" + "="*50)
        await test_macd_with_real_data()
        
        # 4. 测试完整指标计算
        print("\n" + "="*50)
        await test_complete_indicators()
        
        print("\n🎉 调试完成！")
        
    except Exception as e:
        print(f"\n💥 调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())