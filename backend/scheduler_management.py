#!/usr/bin/env python3
"""
定时调度器管理工具
检查和管理定时数据采集任务
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta, time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def show_current_scheduler_config():
    """显示当前定时任务完整配置"""
    print("📅 定时数据采集任务完整配置")
    print("="*60)
    print(f"⏰ 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定时任务配置表
    print(f"\n🕐 详细定时任务配置:")
    print("="*60)
    
    tasks = [
        {
            "time": "01:00", 
            "frequency": "每周日", 
            "task": "股票信息全量同步",
            "description": "导入全部A股和港股基础信息",
            "condition": "无条件执行",
            "importance": "🟡 中等"
        },
        {
            "time": "02:00", 
            "frequency": "每日", 
            "task": "股票基础信息同步",
            "description": "增量同步新股票信息",
            "condition": "无条件执行",
            "importance": "🟢 低"
        },
        {
            "time": "03:00", 
            "frequency": "每日", 
            "task": "缓存清理",
            "description": "清理过期缓存数据",
            "condition": "无条件执行", 
            "importance": "🟢 低"
        },
        {
            "time": "08:30", 
            "frequency": "每日", 
            "task": "开盘前健康检查",
            "description": "检查数据源可用性",
            "condition": "仅交易日执行",
            "importance": "🟡 中等"
        },
        {
            "time": "15:10", 
            "frequency": "每日", 
            "task": "A股收盘后检查",
            "description": "检查A股数据源状态",
            "condition": "仅交易日执行",
            "importance": "🟡 中等"
        },
        {
            "time": "16:10", 
            "frequency": "每日", 
            "task": "港股收盘后检查",
            "description": "检查港股数据源状态",
            "condition": "仅交易日执行",
            "importance": "🟡 中等"
        },
        {
            "time": "17:00", 
            "frequency": "每日", 
            "task": "📊 股票涨跌数据收集",
            "description": "收集当日所有股票涨跌数据",
            "condition": "仅交易日执行",
            "importance": "🔴 高"
        },
        {
            "time": "18:00", 
            "frequency": "每日", 
            "task": "📈 强势股票筛选",
            "description": "执行股票筛选算法",
            "condition": "仅交易日执行",
            "importance": "🔴 高"
        }
    ]
    
    print(f"{'时间':<8} {'频率':<8} {'任务':<20} {'执行条件':<12} {'重要性'}")
    print("-" * 80)
    
    for task in tasks:
        print(f"{task['time']:<8} {task['frequency']:<8} {task['task']:<20} {task['condition']:<12} {task['importance']}")
    
    # 核心数据采集流程
    print(f"\n🎯 核心数据采集流程:")
    print("="*40)
    print("1. 17:00 - 股票涨跌数据收集")
    print("   • 从AkShare获取当日所有股票数据")
    print("   • 包括：价格、成交量、涨跌幅等")
    print("   • 使用腾讯API补充市值和换手率")
    print("   • 存储到 daily_stock_changes 表")
    
    print(f"\n2. 18:00 - 强势股票筛选")
    print("   • 基于收集的数据执行筛选算法")
    print("   • 默认条件：连续3天涨幅>7%")
    print("   • 生成筛选结果供前端使用")
    
    # 检查当前数据状态
    print(f"\n💾 当前数据状态检查:")
    print("="*40)
    
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager('stock_pool.db')
        
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查最新数据日期
            cursor.execute('''
                SELECT DISTINCT trade_date 
                FROM daily_stock_changes 
                ORDER BY trade_date DESC 
                LIMIT 1
            ''')
            latest_date = cursor.fetchone()
            latest_date = latest_date[0] if latest_date else "无数据"
            
            # 检查最新数据量
            cursor.execute('''
                SELECT COUNT(*) 
                FROM daily_stock_changes 
                WHERE trade_date = ?
            ''', (latest_date,))
            latest_count = cursor.fetchone()[0] if latest_date != "无数据" else 0
            
            print(f"最新数据日期: {latest_date}")
            print(f"最新数据量: {latest_count:,} 条记录")
            
            # 检查市值数据完整性
            if latest_date != "无数据":
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM daily_stock_changes 
                    WHERE trade_date = ? AND total_market_cap > 0
                ''', (latest_date,))
                market_cap_count = cursor.fetchone()[0]
                
                completion_rate = (market_cap_count / latest_count * 100) if latest_count > 0 else 0
                print(f"市值数据完整率: {completion_rate:.1f}% ({market_cap_count:,}/{latest_count:,})")
        
    except Exception as e:
        print(f"❌ 数据状态检查失败: {e}")
    
    # 时间分析
    print(f"\n⏰ 当前时间分析:")
    print("="*30)
    
    now = datetime.now()
    today = now.date()
    
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"今日是否工作日: {'是' if now.weekday() < 5 else '否'}")
    
    # 计算下次关键任务时间
    next_collection = datetime.combine(today, time(17, 0))
    if now > next_collection:
        next_collection += timedelta(days=1)
    
    next_screening = datetime.combine(today, time(18, 0))
    if now > next_screening:
        next_screening += timedelta(days=1)
    
    print(f"下次数据收集: {next_collection.strftime('%Y-%m-%d %H:%M')}")
    print(f"下次股票筛选: {next_screening.strftime('%Y-%m-%d %H:%M')}")
    
    # 检查是否错过今日任务
    collection_time = datetime.combine(today, time(17, 0))
    screening_time = datetime.combine(today, time(18, 0))
    
    if now.weekday() < 5:  # 工作日
        if now > collection_time and now < screening_time:
            print("⚠️  今日17:00数据收集可能已错过")
        elif now > screening_time:
            print("⚠️  今日18:00股票筛选可能已错过")
    
    # 启动建议
    print(f"\n🚀 启动建议:")
    print("="*20)
    print("1. 后端服务启动时自动启动调度器:")
    print("   • main.py 中的 startup_event 会自动启动")
    print("   • 检查日志确认启动成功")
    
    print(f"\n2. 手动启动调度器:")
    print("   • 重启后端服务: python3 main.py")
    print("   • 或调用API启动")
    
    print(f"\n3. 立即执行数据采集 (如果错过):")
    print("   curl -X POST http://localhost:8001/api/data-sync/manual/daily_data_collection")
    print("   curl -X POST http://localhost:8001/api/data-sync/manual/strong_rise_screening")
    
    # 配置文件位置
    print(f"\n📁 相关文件位置:")
    print("="*25)
    print("• 调度器配置: services/data_sync_scheduler.py")
    print("• 主程序入口: main.py")
    print("• 数据库文件: stock_pool.db")
    print("• 市值更新脚本: update_market_data.py")

def check_if_tasks_missed_today():
    """检查今日是否错过了关键任务"""
    print(f"\n🕐 今日任务执行状态检查:")
    print("="*40)
    
    now = datetime.now()
    today = now.date()
    
    # 关键任务时间点
    key_tasks = [
        (17, 0, "股票数据收集", "daily_data_collection"),
        (18, 0, "股票筛选", "strong_rise_screening")
    ]
    
    for hour, minute, task_name, task_id in key_tasks:
        task_time = datetime.combine(today, time(hour, minute))
        
        if now > task_time:
            # 检查是否有今日的执行记录（这里简化处理）
            status = "可能已错过" if now.weekday() < 5 else "今日非交易日"
            print(f"  {hour:02d}:{minute:02d} {task_name}: ⚠️  {status}")
        else:
            remaining = task_time - now
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"  {hour:02d}:{minute:02d} {task_name}: ⏳ {hours}小时{minutes}分钟后执行")

def show_manual_execution_guide():
    """显示手动执行指南"""
    print(f"\n🔧 手动执行指南:")
    print("="*30)
    
    print("如果错过了定时任务，可以手动执行:")
    
    commands = [
        ("立即收集股票数据", "POST /api/data-sync/manual/daily_data_collection"),
        ("立即执行股票筛选", "POST /api/data-sync/manual/strong_rise_screening"),
        ("检查数据源健康", "POST /api/data-sync/manual/data_source_health"),
        ("同步股票基础信息", "POST /api/data-sync/manual/stock_info_daily"),
        ("更新市值和换手率", "POST /api/market-data/update")
    ]
    
    for desc, api in commands:
        print(f"\n{desc}:")
        print(f"  curl -X POST 'http://localhost:8001{api}'")

if __name__ == '__main__':
    show_current_scheduler_config()
    check_if_tasks_missed_today() 
    show_manual_execution_guide()
    
    print(f"\n" + "="*60)
    print("🎉 定时调度器配置检查完成!")
    print("💡 建议定期检查调度器状态确保数据及时更新")