#!/usr/bin/env python3
"""
运行数据源优化 - 补充历史数据和优化技术指标
"""
import asyncio
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append('.')

from backend.database import DatabaseManager
from backend.services.historical_data_service import HistoricalDataService
from backend.services.technical_indicator_service import TechnicalIndicatorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    print("="*80)
    print("数据源优化 - 历史数据补充和技术指标优化")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 初始化服务
    db_manager = DatabaseManager()
    historical_service = HistoricalDataService(db_manager)
    tech_service = TechnicalIndicatorService(db_manager)
    
    try:
        # 步骤1: 补充历史数据
        print("\n📊 步骤1: 补充历史数据")
        print("-" * 50)
        
        # 获取主要股票的30天历史数据
        stats = await historical_service.supplement_historical_data(
            stock_codes=None,  # 所有活跃股票
            days=30,           # 30天数据，适合大量股票处理
            force_update=False # 不强制更新已有数据
        )
        
        print(f"✅ 历史数据补充完成:")
        print(f"   - 总股票数: {stats['total_stocks']}")
        print(f"   - 成功更新: {stats['success_count']}")
        print(f"   - 跳过数量: {stats['skipped_count']}")
        print(f"   - 失败数量: {stats['failed_count']}")
        print(f"   - 新增记录: {stats['updated_records']}")
        
        if stats['failed_stocks']:
            print(f"   - 失败股票: {stats['failed_stocks'][:5]}...")  # 只显示前5个
        
        # 步骤2: 批量计算技术指标
        print(f"\n📈 步骤2: 计算技术指标")
        print("-" * 50)
        
        # 只有在有成功更新时才计算指标，或者总是计算现有数据的指标
        if stats['success_count'] > 0 or True:  # 总是计算指标
            # 获取有数据的股票代码
            stock_codes = await get_stocks_with_data(db_manager)
            
            indicator_stats = {
                'total': len(stock_codes),
                'success': 0,
                'failed': 0
            }
            
            print(f"开始为 {len(stock_codes)} 只股票计算技术指标...")
            
            # 批量计算技术指标
            batch_size = 5
            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]
                
                tasks = []
                for stock_code in batch:
                    task = calculate_indicators_for_stock(tech_service, stock_code)
                    tasks.append(task)
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        indicator_stats['failed'] += 1
                    elif result:
                        indicator_stats['success'] += 1
                        
                        # 显示示例结果
                        if indicator_stats['success'] <= 3:
                            stock_code = batch[j]
                            print(f"  示例 - {stock_code}: {format_indicators(result)}")
                    else:
                        indicator_stats['failed'] += 1
                
                # 进度报告
                processed = min(i + batch_size, len(stock_codes))
                print(f"  进度: {processed}/{len(stock_codes)} ({processed/len(stock_codes)*100:.1f}%)")
                
                await asyncio.sleep(0.5)  # 避免过于频繁
            
            print(f"✅ 技术指标计算完成:")
            print(f"   - 成功: {indicator_stats['success']}")
            print(f"   - 失败: {indicator_stats['failed']}")
        
        # 步骤3: 验证改进效果
        print(f"\n🔍 步骤3: 验证改进效果")
        print("-" * 50)
        
        await verify_improvements(db_manager, tech_service)
        
    except Exception as e:
        logger.error(f"执行过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("数据源优化完成!")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

async def get_stocks_with_data(db_manager):
    """获取有历史数据的股票代码"""
    import sqlite3
    
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 先尝试从 daily_stock_changes 表获取
            cursor.execute('''
                SELECT DISTINCT stock_code FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
                ORDER BY stock_code
                LIMIT 20
            ''')
            
            result = cursor.fetchall()
            if result:
                return [row[0] for row in result]
            
            # 如果没有数据，尝试从其他表获取
            cursor.execute('''
                SELECT DISTINCT stock_code FROM stock_pool 
                ORDER BY stock_code
                LIMIT 20
            ''')
            
            result = cursor.fetchall()
            if result:
                return [row[0] for row in result]
                
    except Exception as e:
        logger.error(f"获取股票代码失败: {e}")
    
    # 返回默认股票代码
    return ['000001', '000002', '600000', '600036', '600519']

async def calculate_indicators_for_stock(tech_service, stock_code):
    """为单只股票计算技术指标"""
    try:
        indicators = await tech_service.calculate_all_indicators(stock_code, days=30)
        return indicators if indicators else None
    except Exception as e:
        logger.debug(f"计算 {stock_code} 技术指标失败: {e}")
        return None

def format_indicators(indicators):
    """格式化指标显示"""
    key_indicators = ['ma5', 'ma10', 'ma20', 'ma60', 'volume_ratio', 'turnover_rate']
    result = []
    
    for key in key_indicators:
        if key in indicators and indicators[key] is not None:
            value = indicators[key]
            if isinstance(value, float):
                result.append(f"{key}={value:.2f}")
            else:
                result.append(f"{key}={value}")
    
    return ", ".join(result[:4])  # 只显示前4个

async def verify_improvements(db_manager, tech_service):
    """验证改进效果"""
    import sqlite3
    
    try:
        # 统计历史数据量
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 统计总记录数
            cursor.execute('SELECT COUNT(*) FROM daily_stock_changes')
            total_records = cursor.fetchone()[0]
            
            # 统计有数据的股票数
            cursor.execute('SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes')
            total_stocks = cursor.fetchone()[0]
            
            # 统计最近7天的数据
            cursor.execute('''
                SELECT COUNT(*) FROM daily_stock_changes 
                WHERE trade_date >= date('now', '-7 days')
            ''')
            recent_records = cursor.fetchone()[0]
            
            # 统计技术指标数据
            cursor.execute('SELECT COUNT(*) FROM stock_technical_indicators')
            indicator_records = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        print(f"📊 数据统计:")
        print(f"   - 历史K线数据: {total_records:,} 条")
        print(f"   - 覆盖股票数: {total_stocks} 只")
        print(f"   - 近7天数据: {recent_records} 条")
        print(f"   - 技术指标数据: {indicator_records} 条")
        
        # 测试技术指标计算
        test_stock = '000001'
        indicators = await tech_service.calculate_all_indicators(test_stock, days=30)
        
        if indicators:
            print(f"\n📈 技术指标测试 ({test_stock}):")
            
            # MA指标
            ma_indicators = [k for k in indicators.keys() if k.startswith('ma') and isinstance(indicators[k], (int, float))]
            if ma_indicators:
                print(f"   - 均线指标: {len(ma_indicators)} 个")
                for ma in ['ma5', 'ma10', 'ma20', 'ma60']:
                    if ma in indicators and indicators[ma]:
                        print(f"     {ma.upper()}: {indicators[ma]:.2f}")
            
            # 量价指标
            volume_indicators = ['volume_ratio', 'turnover_rate', 'volume_level', 'turnover_level']
            available_volume = [k for k in volume_indicators if k in indicators and indicators[k] is not None]
            if available_volume:
                print(f"   - 量价指标: {len(available_volume)} 个")
                for key in available_volume:
                    print(f"     {key}: {indicators[key]}")
            
            # 趋势指标
            trend_indicators = ['is_bullish_aligned', 'golden_cross_signal', 'volume_price_pattern']
            available_trend = [k for k in trend_indicators if k in indicators and indicators[k] is not None]
            if available_trend:
                print(f"   - 趋势指标: {len(available_trend)} 个")
        else:
            print(f"⚠️ 无法获取 {test_stock} 的技术指标")
            
    except Exception as e:
        logger.error(f"验证改进效果失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())