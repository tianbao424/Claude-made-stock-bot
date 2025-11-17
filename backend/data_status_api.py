"""
数据状态API - 为重构的数据采集中心提供接口
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from database import DatabaseManager
from services.data_sync_scheduler import get_data_sync_scheduler

logger = logging.getLogger(__name__)

class DataStatusAPI:
    """数据状态API处理类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def get_data_update_status(self) -> Dict[str, Any]:
        """获取数据更新状态"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取最新数据日期
                cursor.execute('''
                    SELECT DISTINCT trade_date 
                    FROM daily_stock_changes 
                    ORDER BY trade_date DESC 
                    LIMIT 1
                ''')
                latest_date_row = cursor.fetchone()
                latest_date = latest_date_row[0] if latest_date_row else None
                
                # 获取当前日期
                today_date = datetime.now().strftime('%Y-%m-%d')
                
                # 计算落后天数
                if latest_date:
                    latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
                    today_dt = datetime.strptime(today_date, '%Y-%m-%d')
                    days_behind = (today_dt - latest_dt).days
                else:
                    days_behind = 999  # 无数据
                
                # 获取总股票数量（从daily_stock_changes表中获取更准确的数量）
                cursor.execute('SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes')
                total_stocks = cursor.fetchone()[0]
                
                # 获取最新记录数量
                latest_records_count = 0
                if latest_date:
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM daily_stock_changes 
                        WHERE trade_date = ?
                    ''', (latest_date,))
                    latest_records_count = cursor.fetchone()[0]
                
                # 计算数据新鲜度评分
                if days_behind == 0:
                    data_freshness_score = 100.0
                elif days_behind == 1:
                    data_freshness_score = 90.0
                elif days_behind <= 3:
                    data_freshness_score = 70.0
                elif days_behind <= 7:
                    data_freshness_score = 50.0
                else:
                    data_freshness_score = 20.0
                
                # 判断是否需要更新
                is_up_to_date = days_behind <= 1
                needs_update = days_behind > 1 or latest_records_count < total_stocks * 0.8
                
                return {
                    "latest_date": latest_date or "无数据",
                    "today_date": today_date,
                    "days_behind": days_behind,
                    "total_stocks": total_stocks,
                    "latest_records_count": latest_records_count,
                    "is_up_to_date": is_up_to_date,
                    "needs_update": needs_update,
                    "data_freshness_score": data_freshness_score
                }
                
        except Exception as e:
            logger.error(f"获取数据更新状态失败: {e}")
            return {
                "latest_date": "错误",
                "today_date": datetime.now().strftime('%Y-%m-%d'),
                "days_behind": 999,
                "total_stocks": 0,
                "latest_records_count": 0,
                "is_up_to_date": False,
                "needs_update": True,
                "data_freshness_score": 0.0
            }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        try:
            scheduler = get_data_sync_scheduler(self.db_manager)
            status = scheduler.get_scheduler_status()
            
            # 获取今日任务状态
            today_collection_status = self._get_task_status_today('daily_data_collection')
            today_screening_status = self._get_task_status_today('strong_rise_screening')
            
            # 计算下次执行时间
            now = datetime.now()
            collection_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
            screening_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
            
            # 如果已过今日执行时间，则设为明日
            if now > collection_time:
                collection_time += timedelta(days=1)
            if now > screening_time:
                screening_time += timedelta(days=1)
            
            next_scheduled_time = min(collection_time, screening_time)
            
            return {
                "is_running": status['running'],
                "last_run_time": None,  # 可以从调度器状态中获取
                "next_scheduled_time": next_scheduled_time.isoformat(),
                "today_collection_status": today_collection_status,
                "today_screening_status": today_screening_status,
                "collection_time": "17:00",
                "screening_time": "18:00",
                "tasks": status.get('tasks', {}),
                "stats": status.get('stats', {})
            }
            
        except Exception as e:
            logger.error(f"获取调度器状态失败: {e}")
            return {
                "is_running": False,
                "last_run_time": None,
                "next_scheduled_time": None,
                "today_collection_status": "failed",
                "today_screening_status": "failed",
                "collection_time": "17:00",
                "screening_time": "18:00",
                "tasks": {},
                "stats": {}
            }
    
    def get_market_cap_status(self) -> Dict[str, Any]:
        """获取市值数据状态"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取总股票数量（从daily_stock_changes表中获取更准确的数量）
                cursor.execute('SELECT COUNT(DISTINCT stock_code) FROM daily_stock_changes')
                total_stocks_count = cursor.fetchone()[0]
                
                # 获取有市值数据的股票数量
                cursor.execute('''
                    SELECT COUNT(DISTINCT stock_code) 
                    FROM daily_stock_changes 
                    WHERE total_market_cap > 0 OR circulating_market_cap > 0
                ''')
                updated_stocks_count = cursor.fetchone()[0]
                
                # 计算完整率
                completion_rate = (updated_stocks_count / total_stocks_count * 100) if total_stocks_count > 0 else 0
                
                # 获取最后更新时间（最新记录的创建时间）
                cursor.execute('''
                    SELECT MAX(created_at) 
                    FROM daily_stock_changes 
                    WHERE total_market_cap > 0
                ''')
                last_update_row = cursor.fetchone()
                last_update_time = last_update_row[0] if last_update_row and last_update_row[0] else None
                
                return {
                    "last_update_time": last_update_time,
                    "updated_stocks_count": updated_stocks_count,
                    "total_stocks_count": total_stocks_count,
                    "completion_rate": completion_rate,
                    "data_source": "腾讯财经API",
                    "next_update_time": None  # 根据调度器设置
                }
                
        except Exception as e:
            logger.error(f"获取市值数据状态失败: {e}")
            return {
                "last_update_time": None,
                "updated_stocks_count": 0,
                "total_stocks_count": 0,
                "completion_rate": 0.0,
                "data_source": "腾讯财经API",
                "next_update_time": None
            }
    
    def _get_task_status_today(self, task_name: str) -> str:
        """获取今日任务执行状态"""
        try:
            scheduler = get_data_sync_scheduler(self.db_manager)
            status = scheduler.get_scheduler_status()
            
            task_info = status.get('tasks', {}).get(task_name, {})
            if not task_info:
                return 'not_started'
            
            last_run = task_info.get('last_run')
            last_success = task_info.get('last_success')
            
            if not last_run:
                return 'not_started'
            
            # 检查是否为今日执行
            try:
                last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                today = datetime.now().date()
                
                if last_run_dt.date() == today:
                    if last_success and datetime.fromisoformat(last_success.replace('Z', '+00:00')).date() == today:
                        return 'completed'
                    else:
                        return 'failed'
                else:
                    return 'not_started'
            except:
                return 'not_started'
                
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return 'failed'
    
    async def trigger_manual_data_collection(self) -> Dict[str, Any]:
        """触发手动数据收集"""
        try:
            start_time = datetime.now()
            scheduler = get_data_sync_scheduler(self.db_manager)
            result = await scheduler.manual_sync('daily_data_collection')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": result.success,
                "message": result.message,
                "records_processed": result.records_updated,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"手动数据收集失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "records_processed": 0,
                "duration_seconds": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_manual_screening(self) -> Dict[str, Any]:
        """触发手动股票筛选"""
        try:
            start_time = datetime.now()
            scheduler = get_data_sync_scheduler(self.db_manager)
            result = await scheduler.manual_sync('strong_rise_screening')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": result.success,
                "message": result.message,
                "records_processed": result.records_updated,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"手动股票筛选失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "records_processed": 0,
                "duration_seconds": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_market_cap_update(self) -> Dict[str, Any]:
        """触发市值数据更新"""
        try:
            start_time = datetime.now()
            
            # 导入腾讯数据服务
            from services.tencent_data_service import supplement_with_tencent_api
            
            # 获取昨天的日期作为目标日期
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            result = await supplement_with_tencent_api(
                self.db_manager, 
                trade_date=yesterday,
                limit=1000
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": result.get('success', False),
                "message": result.get('message', '执行完成'),
                "records_processed": result.get('updated_count', 0),
                "duration_seconds": duration,
                "timestamp": start_time.isoformat(),
                "updated_count": result.get('updated_count', 0)
            }
            
        except Exception as e:
            logger.error(f"市值数据更新失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "records_processed": 0,
                "duration_seconds": 0,
                "timestamp": datetime.now().isoformat(),
                "updated_count": 0
            }