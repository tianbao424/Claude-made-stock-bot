#!/usr/bin/env python3
"""
API扩展 - 为新的前端功能提供后端API支持
"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from database import DatabaseManager
from services.stock_info_updater import get_stock_info_updater
from services.unified_tencent_collector import get_unified_collector
from services.data_sync_scheduler import get_data_sync_scheduler

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter()

# 全局数据库管理器
db_manager = DatabaseManager()

@router.get("/api/stock-info/status")
async def get_stock_info_status():
    """获取股票信息状态"""
    try:
        updater = get_stock_info_updater(db_manager)
        summary = await updater.get_update_summary()
        
        # 计算距离上次更新的天数
        days_since_update = 0
        needs_update = True
        
        if summary.get('last_updated'):
            try:
                last_updated = datetime.fromisoformat(summary['last_updated'].replace('Z', '+00:00'))
                days_since_update = (datetime.now() - last_updated).days
                needs_update = days_since_update > 7  # 7天以上需要更新
            except:
                days_since_update = 999
                needs_update = True
        
        return {
            "total_stocks_count": summary.get('total_stocks', 0),
            "active_stocks_count": summary.get('active_stocks', 0),
            "inactive_stocks_count": summary.get('inactive_stocks', 0),
            "market_distribution": summary.get('market_distribution', {}),
            "last_update_time": summary.get('last_updated'),
            "days_since_last_update": days_since_update,
            "needs_update": needs_update,
            "last_scan_count": 8994  # 固定扫描范围
        }
        
    except Exception as e:
        logger.error(f"获取股票信息状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/unified-collection/status")
async def get_unified_collection_status():
    """获取统一采集状态"""
    try:
        collector = get_unified_collector(db_manager)
        collection_status = await collector.get_collection_status()
        
        return {
            "is_enabled": True,
            "data_source": "腾讯财经API",
            "collection_method": "统一批量采集",
            "auto_stock_discovery": True,
            "last_discovery_time": collection_status.get('latest_date'),
            "new_stocks_found": 0,  # 这需要从实际执行结果中获取
            "updated_stocks": 0     # 这需要从实际执行结果中获取
        }
        
    except Exception as e:
        logger.error(f"获取统一采集状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/stock-info/full-update")
async def manual_stock_info_full_update():
    """手动执行股票信息全量更新"""
    try:
        logger.info("🚀 开始手动股票信息全量更新")
        start_time = datetime.now()
        
        updater = get_stock_info_updater(db_manager)
        result = await updater.full_update_stock_info()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.get('success'):
            return {
                "success": True,
                "message": f"股票信息更新完成: 新增{result.get('new_stocks', 0)}只, 更新{result.get('updated_stocks', 0)}只, 移除{result.get('removed_stocks', 0)}只",
                "records_processed": result.get('new_stocks', 0) + result.get('updated_stocks', 0),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "total_scanned": result.get('total_scanned', 0),
                    "valid_stocks": result.get('valid_stocks', 0),
                    "new_stocks": result.get('new_stocks', 0),
                    "updated_stocks": result.get('updated_stocks', 0),
                    "removed_stocks": result.get('removed_stocks', 0)
                }
            }
        else:
            return {
                "success": False,
                "message": f"股票信息更新失败: {result.get('error', '未知错误')}",
                "records_processed": 0,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"手动股票信息更新失败: {e}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "records_processed": 0,
            "duration_seconds": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.post("/api/unified-collection/force-collect")
async def force_unified_collection():
    """强制统一数据采集（包含股票发现）"""
    try:
        logger.info("⚡ 开始强制统一数据采集")
        start_time = datetime.now()
        
        collector = get_unified_collector(db_manager)
        # 强制执行，包含股票发现
        result = await collector.collect_daily_stock_data(force_discovery=True)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.success:
            return {
                "success": True,
                "message": f"强制统一采集完成: {result.successful_records}/{result.total_collected} 只股票",
                "records_processed": result.successful_records,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "total_collected": result.total_collected,
                    "successful_records": result.successful_records,
                    "failed_records": result.failed_records,
                    "collection_date": result.collection_date
                }
            }
        else:
            return {
                "success": False,
                "message": f"强制统一采集失败: {result.error_message}",
                "records_processed": 0,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"强制统一数据采集失败: {e}")
        return {
            "success": False,
            "message": f"执行异常: {str(e)}",
            "records_processed": 0,
            "duration_seconds": 0,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/api/system/health-check")
async def system_health_check():
    """系统健康检查"""
    try:
        # 检查数据库连接
        try:
            import sqlite3
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM stock_info LIMIT 1')
                db_status = "healthy"
        except Exception as e:
            db_status = f"error: {e}"
        
        # 检查腾讯API
        try:
            from services.tencent_data_service import TencentDataService
            tencent_service = TencentDataService()
            async with tencent_service as service:
                test_data = await service.get_stock_data(['000001'])
                api_status = "healthy" if test_data and '000001' in test_data else "unhealthy"
        except Exception as e:
            api_status = f"error: {e}"
        
        # 检查调度器
        try:
            scheduler = get_data_sync_scheduler(db_manager)
            scheduler_info = scheduler.get_scheduler_status()
            scheduler_status = "healthy" if scheduler_info['running'] else "stopped"
        except Exception as e:
            scheduler_status = f"error: {e}"
        
        overall_health = "healthy" if all(
            status in ["healthy", "stopped"] for status in [db_status, api_status, scheduler_status]
        ) else "unhealthy"
        
        return {
            "overall_health": overall_health,
            "components": {
                "database": db_status,
                "tencent_api": api_status,
                "scheduler": scheduler_status
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/system/info")
async def get_system_info():
    """获取系统信息"""
    try:
        # 获取各种统计信息
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 股票信息统计
            cursor.execute('SELECT COUNT(*), SUM(is_active) FROM stock_info WHERE LENGTH(symbol) = 6')
            total_stocks, active_stocks = cursor.fetchone()
            
            # 数据记录统计
            cursor.execute('SELECT COUNT(DISTINCT trade_date) FROM daily_stock_changes')
            trading_days = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM daily_stock_changes')
            total_records = cursor.fetchone()[0]
            
            # 最新数据
            cursor.execute('SELECT MAX(trade_date) FROM daily_stock_changes')
            latest_date = cursor.fetchone()[0]
            
        return {
            "system_version": "2.3.0",
            "data_source": "腾讯财经API",
            "collection_method": "统一批量采集",
            "statistics": {
                "total_stocks": total_stocks or 0,
                "active_stocks": int(active_stocks or 0),
                "trading_days_covered": trading_days or 0,
                "total_data_records": total_records or 0,
                "latest_data_date": latest_date
            },
            "features": [
                "统一腾讯API数据采集",
                "自动新股发现和更新", 
                "实时市值和换手率数据",
                "智能调度和监控",
                "多维度股票筛选"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))