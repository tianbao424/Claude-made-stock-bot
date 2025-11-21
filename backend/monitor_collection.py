#!/usr/bin/env python3
"""
监控方案2全量采集进度
实时显示采集状态和性能指标
"""

import sqlite3
import os
import time
import sys
from datetime import datetime, timedelta

def monitor_collection_progress():
    """监控采集进度"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    print("📊 方案2全量采集进度监控")
    print("=" * 60)
    print("按 Ctrl+C 退出监控\n")
    
    start_monitor_time = datetime.now()
    last_count = 0
    
    try:
        while True:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 检查今天的采集数量
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT COUNT(DISTINCT stock_code) 
                    FROM daily_stock_changes 
                    WHERE DATE(created_at) = ?
                ''', (today,))
                
                today_count = cursor.fetchone()[0]
                
                # 总A股数量
                cursor.execute('''
                    SELECT COUNT(DISTINCT stock_code) 
                    FROM daily_stock_changes 
                    WHERE LENGTH(stock_code) = 6 
                    AND SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                ''')
                
                total_a_stocks = cursor.fetchone()[0]
                
                # 计算进度
                progress = today_count / total_a_stocks * 100 if total_a_stocks > 0 else 0
                
                # 计算速度 (每分钟采集数量)
                new_stocks = today_count - last_count
                monitor_duration = (datetime.now() - start_monitor_time).total_seconds() / 60
                speed_per_minute = new_stocks / monitor_duration if monitor_duration > 0 else 0
                
                # 预估剩余时间
                remaining_stocks = total_a_stocks - today_count
                if speed_per_minute > 0:
                    remaining_minutes = remaining_stocks / speed_per_minute
                    remaining_hours = remaining_minutes / 60
                    eta = datetime.now() + timedelta(minutes=remaining_minutes)
                    eta_str = eta.strftime("%H:%M:%S")
                else:
                    remaining_hours = 0
                    eta_str = "计算中..."
                
                # 清屏并显示进度
                os.system('clear' if os.name == 'posix' else 'cls')
                
                print("📊 方案2全量A股采集进度监控")
                print("=" * 60)
                print(f"🕐 监控时间: {datetime.now().strftime('%H:%M:%S')}")
                print()
                
                print(f"📈 采集进度:")
                print(f"   已完成: {today_count:,}/{total_a_stocks:,} 只股票")
                print(f"   进度: {progress:.1f}%")
                
                # 进度条
                bar_width = 40
                filled = int(bar_width * progress / 100)
                bar = "█" * filled + "▒" * (bar_width - filled)
                print(f"   [{bar}] {progress:.1f}%")
                
                print(f"\n⚡ 性能指标:")
                print(f"   采集速度: {speed_per_minute:.1f} 股/分钟")
                print(f"   预估剩余: {remaining_hours:.1f} 小时")
                print(f"   预计完成: {eta_str}")
                
                # 检查最近的采集记录
                cursor.execute('''
                    SELECT stock_code, created_at 
                    FROM daily_stock_changes 
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at DESC 
                    LIMIT 5
                ''', (today,))
                
                recent_records = cursor.fetchall()
                if recent_records:
                    print(f"\n📋 最近采集:")
                    for stock_code, created_at in recent_records:
                        print(f"   {stock_code} - {created_at}")
                
                # 检查是否有采集进程在运行
                import subprocess
                try:
                    result = subprocess.run(['pgrep', '-f', 'start_background_collection.py'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"\n✅ 采集进程运行中 (PID: {result.stdout.strip()})")
                    else:
                        print(f"\n⚠️ 采集进程可能已停止")
                except:
                    print(f"\n❓ 无法检查进程状态")
                
                print(f"\n💡 按 Ctrl+C 退出监控")
                print("=" * 60)
                
                last_count = today_count
                
                # 如果完成度达到100%，停止监控
                if progress >= 100:
                    print("\n🎉 采集已完成！")
                    break
                    
            time.sleep(30)  # 每30秒刷新一次
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 监控已停止")
    except Exception as e:
        print(f"❌ 监控错误: {e}")

def show_collection_summary():
    """显示采集总结"""
    
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 今日采集统计
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT stock_code) as stocks,
                    COUNT(*) as records,
                    MIN(created_at) as start_time,
                    MAX(created_at) as end_time
                FROM daily_stock_changes 
                WHERE DATE(created_at) = ?
            ''', (today,))
            
            summary = cursor.fetchone()
            
            if summary and summary[0] > 0:
                stocks, records, start_time, end_time = summary
                
                # 计算持续时间
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration = (end_dt - start_dt).total_seconds() / 3600
                
                print(f"\n📊 今日采集总结:")
                print(f"   采集股票: {stocks:,} 只")
                print(f"   数据记录: {records:,} 条")
                print(f"   开始时间: {start_dt.strftime('%H:%M:%S')}")
                print(f"   结束时间: {end_dt.strftime('%H:%M:%S')}")
                print(f"   总用时: {duration:.1f} 小时")
                
                if duration > 0:
                    avg_time = duration * 3600 / stocks
                    print(f"   平均每股: {avg_time:.2f} 秒")
                    
                    # 与预估对比
                    estimated_per_stock = 1.79  # 方案2测试结果
                    if avg_time <= estimated_per_stock:
                        improvement = ((estimated_per_stock - avg_time) / estimated_per_stock * 100)
                        print(f"   优于预估: {improvement:+.1f}%")
                    else:
                        print(f"   慢于预估: {(avg_time - estimated_per_stock):.2f}秒")
                        
            else:
                print("📊 今日暂无采集数据")
                
    except Exception as e:
        print(f"❌ 无法获取总结: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        show_collection_summary()
    else:
        monitor_collection_progress()