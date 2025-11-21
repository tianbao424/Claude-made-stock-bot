#!/usr/bin/env python3
"""
财务数据更新脚本
用于定期更新股票的市值、换手率等财务数据
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.enhanced_data_collector import get_enhanced_data_collector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('financial_data_update.log')
    ]
)

logger = logging.getLogger(__name__)

async def update_all_stock_financial_data():
    """更新所有股票的财务数据"""
    logger.info("🚀 开始更新股票财务数据...")
    
    # 初始化数据库和采集器
    db_path = "stock_pool.db"
    db_manager = DatabaseManager(db_path)
    collector = get_enhanced_data_collector(db_manager)
    
    # 获取所有需要更新的股票代码
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT stock_code FROM daily_stock_changes 
            WHERE trade_date >= date('now', '-7 days')
            ORDER BY stock_code
        ''')
        
        stock_codes = [row[0] for row in cursor.fetchall()]
    
    if not stock_codes:
        logger.warning("⚠️ 没有找到需要更新的股票")
        return
    
    logger.info(f"📊 找到 {len(stock_codes)} 只股票需要更新财务数据")
    
    # 批量更新财务信息
    result = await collector.update_stock_financial_info(stock_codes)
    
    logger.info("✅ 财务数据更新完成")
    logger.info(f"📊 更新统计: {result}")
    
    return result

async def update_recent_turnover_rates():
    """更新最近几天的换手率数据"""
    logger.info("🚀 开始更新换手率数据...")
    
    # 初始化数据库和采集器
    db_path = "stock_pool.db"
    db_manager = DatabaseManager(db_path)
    collector = get_enhanced_data_collector(db_manager)
    
    # 获取最近的交易日期
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT trade_date FROM daily_stock_changes 
            WHERE trade_date >= date('now', '-5 days')
            ORDER BY trade_date DESC
            LIMIT 3
        ''')
        
        trade_dates = [row[0] for row in cursor.fetchall()]
    
    if not trade_dates:
        logger.warning("⚠️ 没有找到最近的交易数据")
        return
    
    logger.info(f"📅 将为以下日期计算换手率: {trade_dates}")
    
    results = []
    for trade_date in trade_dates:
        logger.info(f"🔄 处理 {trade_date}...")
        result = await collector.enhance_daily_stock_data_with_turnover_rate(trade_date)
        results.append(result)
        
        # 避免请求过于频繁
        await asyncio.sleep(1)
    
    logger.info("✅ 换手率数据更新完成")
    for result in results:
        logger.info(f"📊 {result['trade_date']}: 成功 {result.get('success_count', 0)}, 失败 {result.get('error_count', 0)}")
    
    return results

async def main():
    """主函数"""
    try:
        print("=" * 60)
        print("📊 股票财务数据更新工具")
        print("=" * 60)
        
        # 1. 更新财务数据（市值等）
        print("\n1️⃣ 更新股票财务数据...")
        financial_result = await update_all_stock_financial_data()
        
        print("\n" + "="*40)
        
        # 2. 更新换手率数据
        print("\n2️⃣ 更新换手率数据...")
        turnover_results = await update_recent_turnover_rates()
        
        print("\n" + "="*60)
        print("🎉 所有数据更新完成!")
        print(f"📅 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if financial_result:
            print(f"💼 财务数据: 成功 {financial_result['success_count']}, 失败 {financial_result['error_count']}")
        
        if turnover_results:
            total_success = sum(r.get('success_count', 0) for r in turnover_results)
            total_error = sum(r.get('error_count', 0) for r in turnover_results)
            print(f"📈 换手率数据: 成功 {total_success}, 失败 {total_error}")
        
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 更新过程中发生错误: {e}")
        raise

if __name__ == "__main__":
    # 运行更新
    asyncio.run(main())