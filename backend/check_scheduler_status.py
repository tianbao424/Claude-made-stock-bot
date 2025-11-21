#!/usr/bin/env python3
"""
检查当前定时采集任务的配置和状态
"""
import sys
import os
from datetime import datetime, time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.data_sync_scheduler import get_data_sync_scheduler

def check_scheduler_status():
    """检查定时任务配置和状态"""
    print("📅 定时数据采集任务配置检查")
    print("="*50)
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db_manager = DatabaseManager('stock_pool.db')
    scheduler = get_data_sync_scheduler(db_manager)
    
    # 获取调度器状态
    status = scheduler.get_scheduler_status()
    
    print(f"\n🔧 调度器状态:")
    print(f"运行状态: {'✅ 运行中' if status['running'] else '❌ 未运行'}")
    
    print(f"\n📊 统计信息:")
    stats = status['stats']
    print(f"  总同步次数: {stats['total_syncs']}")
    print(f"  成功次数: {stats['successful_syncs']}")
    print(f"  失败次数: {stats['failed_syncs']}")
    if stats['last_full_sync']:
        print(f"  最后全量同步: {stats['last_full_sync']}")
    
    print(f"\n⚙️  配置的定时任务:")
    print("="*70)
    
    # 按类别组织任务
    task_categories = {
        '数据同步任务': ['stock_info_daily', 'stock_info_weekly'],
        '数据采集任务': ['daily_data_collection', 'strong_rise_screening'],
        '系统维护任务': ['data_source_health', 'cache_cleanup']
    }
    
    for category, task_names in task_categories.items():
        print(f"\n📋 {category}:")
        for task_name in task_names:
            if task_name in status['tasks']:
                task = status['tasks'][task_name]
                status_icon = "✅" if task['enabled'] else "❌"
                health_icon = "🟢" if task['health_status'] == 'healthy' else "🔴"
                
                print(f"  {status_icon} {task['description']}")
                print(f"     频率: {task['frequency']}")
                print(f"     健康状态: {health_icon} {task['health_status']} (错误次数: {task['error_count']})")
                
                if task['last_run']:
                    print(f"     最后运行: {task['last_run']}")
                if task['last_success']:
                    print(f"     最后成功: {task['last_success']}")
                else:
                    print(f"     最后成功: 尚未成功执行")
    
    # 显示具体的定时时间配置
    print(f"\n🕐 详细定时配置:")
    print("="*50)
    
    schedule_config = [
        ("每日凌晨2点", "02:00", "股票基础信息同步", "stock_info_daily"),
        ("每周日凌晨1点", "01:00", "股票信息全量同步", "stock_info_weekly"),
        ("每日凌晨3点", "03:00", "缓存清理", "cache_cleanup"),
        ("每日8:30", "08:30", "开盘前健康检查", "data_source_health"),
        ("每日15:10", "15:10", "A股收盘后检查", "data_source_health"),
        ("每日16:10", "16:10", "港股收盘后检查", "data_source_health"),
        ("每日17:00", "17:00", "收集股票涨跌数据", "daily_data_collection"),
        ("每日18:00", "18:00", "执行股票筛选", "strong_rise_screening")
    ]
    
    current_time = datetime.now().time()
    
    for description, schedule_time, task_desc, task_name in schedule_config:
        enabled = status['tasks'].get(task_name, {}).get('enabled', False)
        status_icon = "✅" if enabled else "❌"
        
        # 计算下次执行时间
        schedule_time_obj = time.fromisoformat(schedule_time)
        if schedule_time_obj > current_time:
            next_run = f"今天 {schedule_time}"
        else:
            next_run = f"明天 {schedule_time}"
        
        print(f"  {status_icon} {description:<15} | {task_desc:<20} | 下次执行: {next_run}")
    
    # 显示市场时间相关的逻辑
    print(f"\n🏦 市场时间逻辑:")
    print("="*30)
    print("• 股票数据采集和筛选只在交易日执行")
    print("• 健康检查在交易日的关键时间点执行")
    print("• 基础信息同步每日执行（不受交易日限制）")
    print("• 全量同步每周执行一次")
    
    # 当前是否为交易时间的检查
    print(f"\n⏰ 当前时间分析:")
    print("="*30)
    
    try:
        # 尝试获取市场状态
        from utils.market_hours import getMarketStatusSummary
        market_status = getMarketStatusSummary()
        
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"工作日: {'是' if market_status.get('isWeekday', False) else '否'}")
        print(f"假期: {'是' if market_status.get('isHoliday', False) else '否'}")
        print(f"交易日: {'是' if market_status.get('isWeekday', False) and not market_status.get('isHoliday', False) else '否'}")
        
    except ImportError:
        print("市场时间工具模块未找到，无法获取详细的市场状态")
    
    # 给出启动建议
    print(f"\n💡 操作建议:")
    print("="*20)
    
    if not status['running']:
        print("🔧 调度器未运行，建议启动:")
        print("   1. 在主程序中调用 scheduler.start_scheduler()")
        print("   2. 或者重启后端服务自动启动调度器")
    else:
        print("✅ 调度器正常运行中")
    
    # 检查是否有失败的任务
    failed_tasks = [name for name, task in status['tasks'].items() 
                   if task['health_status'] == 'error']
    
    if failed_tasks:
        print(f"\n⚠️  注意: 发现异常任务:")
        for task_name in failed_tasks:
            task = status['tasks'][task_name]
            print(f"   • {task['description']}: {task['error_count']} 次错误")
    
    # 下次重要任务预告
    print(f"\n📅 下次重要任务预告:")
    print("="*30)
    
    tomorrow = datetime.now().replace(hour=17, minute=0, second=0, microsecond=0)
    if datetime.now().hour >= 17:
        tomorrow = tomorrow + datetime.timedelta(days=1)
    
    print(f"下次数据采集: {tomorrow.strftime('%Y-%m-%d 17:00')} (每日股票数据)")
    print(f"下次股票筛选: {tomorrow.replace(hour=18).strftime('%Y-%m-%d 18:00')} (强势股筛选)")
    
    # 手动执行建议
    print(f"\n🔧 手动执行命令:")
    print("="*25)
    print("如需立即执行数据采集:")
    print("  POST /api/data-sync/manual/daily_data_collection")
    print("如需立即执行股票筛选:")
    print("  POST /api/data-sync/manual/strong_rise_screening")
    print("如需检查数据源健康:")
    print("  POST /api/data-sync/manual/data_source_health")

if __name__ == '__main__':
    # 导入必要的模块
    from datetime import timedelta
    check_scheduler_status()