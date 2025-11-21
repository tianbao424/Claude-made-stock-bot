#!/usr/bin/env python3
"""
市值数据批量更新脚本
支持不同策略的大批量市值数据补充更新
"""
import asyncio
import logging
import argparse
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.market_cap_updater import MarketCapUpdater, UpdateStrategy
from backend.database import DatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_batch_update(strategy: str, limit: int, exchange: str = None):
    """运行批量更新"""
    print(f"🚀 开始市值数据批量更新")
    print(f"策略: {strategy}, 限制: {limit}只, 交易所: {exchange or '全部'}")
    print("="*60)
    
    # 初始化
    db_manager = DatabaseManager('stock_pool.db')
    updater = MarketCapUpdater(db_manager)
    
    # 转换策略
    strategy_map = {
        'active': UpdateStrategy.ACTIVE_STOCKS,
        'all': UpdateStrategy.ALL_MISSING,
        'exchange': UpdateStrategy.BY_EXCHANGE,
        'priority': UpdateStrategy.PRIORITY_LIST
    }
    
    update_strategy = strategy_map.get(strategy, UpdateStrategy.ACTIVE_STOCKS)
    
    # 显示更新前统计
    print("📊 更新前统计:")
    stats = updater.get_update_statistics()
    print(f"  总股票: {stats['total_stocks']:,}")
    print(f"  有市值: {stats['has_market_cap']:,}")
    print(f"  缺失: {stats['missing_market_cap']:,}")
    print(f"  覆盖率: {stats['coverage_rate']:.1f}%")
    
    for ex_stat in stats['exchange_breakdown']:
        print(f"    {ex_stat['exchange']}: {ex_stat['has_cap']:,}/{ex_stat['total']:,} ({ex_stat['coverage_rate']:.1f}%)")
    
    print(f"\n🎯 获取待更新股票列表...")
    targets = updater.get_missing_market_cap_stocks(update_strategy, limit, exchange)
    
    if not targets:
        print("⚠️ 没有找到需要更新的股票")
        return
    
    print(f"找到 {len(targets)} 只待更新股票")
    print("前10只股票:")
    for symbol, name, industry in targets[:10]:
        print(f"  {symbol} {name} ({industry})")
    
    # 确认是否继续
    if limit > 50:
        confirm = input(f"\n❓ 确定要更新 {len(targets)} 只股票吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 用户取消操作")
            return
    
    # 执行批量更新
    print(f"\n🔄 开始批量更新...")
    start_time = datetime.now()
    
    result = await updater.batch_update_market_cap(update_strategy, limit, exchange)
    
    # 显示结果
    print(f"\n✅ 批量更新完成!")
    print(f"执行时间: {result.execution_time:.1f}秒")
    print(f"目标股票: {result.total_targets}")
    print(f"成功更新: {result.successful_updates}")
    print(f"更新失败: {result.failed_updates}")
    print(f"成功率: {(result.successful_updates/result.total_targets*100):.1f}%")
    
    if result.updated_stocks:
        print(f"\n📈 成功更新的股票 (前20只):")
        for symbol in result.updated_stocks[:20]:
            print(f"  {symbol}")
    
    if result.errors:
        print(f"\n❌ 部分错误 (前10个):")
        for error in result.errors[:10]:
            print(f"  {error}")
    
    # 显示更新后统计
    print(f"\n📊 更新后统计:")
    final_stats = updater.get_update_statistics()
    print(f"  有市值: {final_stats['has_market_cap']:,} (+{final_stats['has_market_cap'] - stats['has_market_cap']})")
    print(f"  缺失: {final_stats['missing_market_cap']:,}")
    print(f"  覆盖率: {final_stats['coverage_rate']:.1f}% (+{final_stats['coverage_rate'] - stats['coverage_rate']:.1f}%)")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='市值数据批量更新工具')
    parser.add_argument('--strategy', 
                       choices=['active', 'all', 'exchange', 'priority'],
                       default='active',
                       help='更新策略 (default: active)')
    parser.add_argument('--limit', 
                       type=int, 
                       default=100,
                       help='更新数量限制 (default: 100)')
    parser.add_argument('--exchange',
                       choices=['SH', 'SZ', 'BJ'],
                       help='指定交易所 (仅在strategy=exchange时有效)')
    
    args = parser.parse_args()
    
    print(f"🤖 市值数据批量更新工具")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        asyncio.run(run_batch_update(args.strategy, args.limit, args.exchange))
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 更新过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()