#!/usr/bin/env python3
"""
开始方案2优化后的全量A股数据采集
基于58.5%效率提升的优化配置
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.historical_data_service import HistoricalDataService
from datetime import datetime

async def start_full_collection():
    print('🚀 开始方案2优化后的全量A股数据采集...')
    print('=' * 60)
    
    # 初始化服务
    db_manager = DatabaseManager()
    service = HistoricalDataService(db_manager)
    
    # 获取A股代码总数
    stock_codes = await service._get_active_stock_codes()
    print(f'📊 将采集 {len(stock_codes):,} 只A股的1天历史数据')
    
    # 显示优化配置
    print('⚙️  优化配置:')
    print('   - 批量大小: 8 只/批次')
    print('   - 单个间隔: 1.0秒')
    print('   - 批次间隔: 3秒')
    print('   - 预估时间: 2.3小时')
    
    start_time = datetime.now()
    print(f'🕐 开始时间: {start_time.strftime("%H:%M:%S")}')
    
    # 开始全量采集
    result = await service.supplement_historical_data(
        stock_codes=None,  # 所有A股
        days=1,
        force_update=True
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    duration_hours = duration / 3600
    
    print(f'\n🏁 采集完成!')
    print(f'📊 最终统计:')
    print(f'   - 总股票数: {result["total_stocks"]:,}')
    print(f'   - 成功采集: {result["success_count"]:,}')
    print(f'   - 采集失败: {result["failed_count"]:,}')
    print(f'   - 无效代码: {result["invalid_count"]:,}')
    print(f'   - 跳过重复: {result["skipped_count"]:,}')
    print(f'   - 更新记录: {result["updated_records"]:,}')
    print(f'   - 实际用时: {duration_hours:.1f}小时')
    
    success_rate = result["success_count"] / result["total_stocks"] * 100 if result["total_stocks"] > 0 else 0
    print(f'   - 成功率: {success_rate:.1f}%')
    
    # 与预估对比
    estimated_hours = 2.3
    if duration_hours <= estimated_hours:
        print(f'✅ 实际用时优于预估 ({estimated_hours:.1f}小时)')
    else:
        print(f'⚠️ 实际用时超出预估 ({estimated_hours:.1f}小时)')
    
    # 效率分析
    avg_time_per_stock = duration / result["total_stocks"] if result["total_stocks"] > 0 else 0
    print(f'📈 效率指标:')
    print(f'   - 平均每股用时: {avg_time_per_stock:.2f}秒')
    
    original_estimated_per_stock = 4.32
    if avg_time_per_stock < original_estimated_per_stock:
        improvement = ((original_estimated_per_stock - avg_time_per_stock) / original_estimated_per_stock * 100)
        print(f'   - 相比原方案改进: {improvement:+.1f}%')
    
    return result

if __name__ == "__main__":
    print("🎯 方案2全量A股数据采集")
    print("基于58.5%效率提升的优化配置")
    print("=" * 60)
    
    result = asyncio.run(start_full_collection())
    
    print("\n" + "=" * 60)
    
    if result["success_count"] > 0:
        print("✅ 全量采集执行完成")
        print(f"📊 成功采集了 {result['success_count']:,} 只A股的数据")
        print(f"📈 数据库新增 {result['updated_records']:,} 条记录")
    else:
        print("❌ 采集过程中遇到问题，需要检查配置")
    
    print("💡 下一步: 验证数据质量和完整性")