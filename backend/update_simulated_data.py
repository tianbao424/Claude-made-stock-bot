#!/usr/bin/env python3
"""
更新模拟数据为真实数据
识别并替换数据库中的模拟数据
"""

import asyncio
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from services.historical_data_service import HistoricalDataService
from database import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def identify_simulated_data():
    """识别需要更新的模拟数据"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    print("🔍 识别需要更新的模拟数据:")
    print("=" * 50)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. 查找价格为10.0的模拟数据
            cursor.execute('''
                SELECT 
                    stock_code, 
                    trade_date,
                    open_price, close_price, volume
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                AND (close_price = 10.0 OR volume = 0)
                ORDER BY trade_date DESC, stock_code
                LIMIT 20
            ''')
            
            fake_data = cursor.fetchall()
            
            print(f"📊 发现的模拟数据样本:")
            print(f"股票代码 | 交易日期   | 开盘  | 收盘  | 成交量")
            print("-" * 50)
            for stock, date, open_p, close_p, volume in fake_data:
                print(f"{stock}  | {date} | {open_p:5.2f} | {close_p:5.2f} | {volume:8.0f}")
            
            # 2. 统计各日期的模拟数据数量
            cursor.execute('''
                SELECT 
                    trade_date,
                    COUNT(CASE WHEN close_price = 10.0 THEN 1 END) as price_10_count,
                    COUNT(CASE WHEN volume = 0 THEN 1 END) as zero_volume_count,
                    COUNT(*) as total_records
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                GROUP BY trade_date
                HAVING price_10_count > 0 OR zero_volume_count > 0
                ORDER BY trade_date DESC
            ''')
            
            date_stats = cursor.fetchall()
            
            print(f"\n📅 各日期模拟数据统计:")
            print(f"交易日期   | 价格10.0 | 零成交量 | 总记录")
            print("-" * 45)
            for date, price_10, zero_vol, total in date_stats:
                print(f"{date} |   {price_10:5} |   {zero_vol:5} |  {total:5}")
            
            # 3. 查找可以更新的日期范围
            cursor.execute('''
                SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date
                FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                AND (close_price = 10.0 OR volume = 0)
            ''')
            
            date_range = cursor.fetchone()
            
            if date_range and date_range[0]:
                print(f"\n🎯 需要更新的日期范围:")
                print(f"   最早模拟数据: {date_range[0]}")
                print(f"   最新模拟数据: {date_range[1]}")
                
                # 计算天数
                start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
                end_date = datetime.strptime(date_range[1], '%Y-%m-%d')
                days_span = (end_date - start_date).days + 1
                print(f"   跨度天数: {days_span}天")
                
                return date_range, date_stats
            
            return None, date_stats
            
    except Exception as e:
        logger.error(f"识别模拟数据失败: {e}")
        return None, []

async def update_simulated_to_real(target_dates=None, max_days_back=30):
    """更新模拟数据为真实数据"""
    
    logger.info("🔄 开始更新模拟数据为真实数据...")
    
    # 初始化服务
    db_manager = DatabaseManager()
    service = HistoricalDataService(db_manager)
    
    try:
        # 获取需要更新的股票和日期
        if target_dates is None:
            # 如果没有指定日期，获取所有有模拟数据的日期
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT trade_date
                    FROM daily_stock_changes 
                    WHERE LENGTH(stock_code) = 6 
                    AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                    AND (close_price = 10.0 OR volume = 0)
                    ORDER BY trade_date DESC
                    LIMIT ?
                ''', (max_days_back,))
                
                target_dates = [row[0] for row in cursor.fetchall()]
        
        if not target_dates:
            logger.info("✅ 没有发现需要更新的模拟数据")
            return
        
        logger.info(f"📊 发现 {len(target_dates)} 个日期需要更新: {target_dates[:5]}...")
        
        # 计算需要补充的天数（从最早的模拟数据到今天）
        earliest_date = min(target_dates)
        earliest_dt = datetime.strptime(earliest_date, '%Y-%m-%d')
        days_needed = (datetime.now() - earliest_dt).days + 1
        
        logger.info(f"🕐 将补充 {days_needed} 天的历史数据")
        
        # 使用历史数据服务更新数据
        result = await service.supplement_historical_data(
            stock_codes=None,  # 所有A股
            days=days_needed,
            force_update=True  # 强制更新，覆盖模拟数据
        )
        
        logger.info("✅ 模拟数据更新完成!")
        logger.info(f"   成功更新: {result['success_count']}只股票")
        logger.info(f"   更新记录: {result['updated_records']}条")
        logger.info(f"   失败数量: {result['failed_count']}只股票")
        
        return result
        
    except Exception as e:
        logger.error(f"更新模拟数据失败: {e}")
        return None

def clean_obvious_fake_data():
    """清理明显的假数据"""
    
    logger.info("🧹 清理明显的假数据...")
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 删除明显的假数据（价格10.0且成交量为0）
            cursor.execute('''
                DELETE FROM daily_stock_changes 
                WHERE LENGTH(stock_code) = 6 
                AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                AND close_price = 10.0 
                AND volume = 0
                AND open_price = 10.0
                AND high_price = 10.0
                AND low_price = 10.0
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"✅ 清理了 {deleted_count} 条明显的假数据")
            
            return deleted_count
            
    except Exception as e:
        logger.error(f"清理假数据失败: {e}")
        return 0

async def comprehensive_data_update():
    """综合数据更新策略"""
    
    print("🚀 开始综合数据更新...")
    print("=" * 60)
    
    # 1. 识别问题数据
    print("1️⃣ 识别模拟数据...")
    date_range, date_stats = identify_simulated_data()
    
    if not date_stats:
        print("✅ 没有发现模拟数据，无需更新")
        return
    
    # 2. 清理明显假数据
    print("\n2️⃣ 清理明显假数据...")
    cleaned_count = clean_obvious_fake_data()
    
    # 3. 更新剩余模拟数据
    print("\n3️⃣ 更新剩余模拟数据为真实数据...")
    
    # 计算更新天数
    if date_range and date_range[0]:
        start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
        days_to_update = (datetime.now() - start_date).days + 1
        
        print(f"📊 更新参数:")
        print(f"   开始日期: {date_range[0]}")
        print(f"   更新天数: {days_to_update}")
        print(f"   预计用时: {days_to_update * 1.2 / 60:.1f}分钟")
        
        # 执行更新
        result = await update_simulated_to_real(max_days_back=days_to_update)
        
        if result:
            print(f"\n✅ 数据更新完成:")
            print(f"   清理假数据: {cleaned_count}条")
            print(f"   更新股票: {result['success_count']}只")
            print(f"   新增记录: {result['updated_records']}条")
            print(f"   失败股票: {result['failed_count']}只")
        else:
            print(f"\n❌ 数据更新失败")
    
    # 4. 验证更新效果
    print(f"\n4️⃣ 验证更新效果...")
    print("正在重新检查数据质量...")
    
    # 重新检查
    _, remaining_fake = identify_simulated_data()
    
    if not remaining_fake:
        print("✅ 所有模拟数据已成功更新为真实数据!")
    else:
        print(f"⚠️ 仍有 {len(remaining_fake)} 个日期存在模拟数据")

if __name__ == "__main__":
    print("🔄 模拟数据更新工具")
    print("=" * 60)
    
    # 执行综合更新
    asyncio.run(comprehensive_data_update())
    
    print("\n" + "=" * 60)
    print("💡 建议: 定期运行此脚本确保数据真实性")