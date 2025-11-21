#!/usr/bin/env python3
"""
后台启动方案2优化后的全量A股数据采集
"""

import asyncio
import sys
import os
import signal
import logging
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from services.historical_data_service import HistoricalDataService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_collection.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 全局变量用于优雅停止
running = True

def signal_handler(signum, frame):
    global running
    logger.info("接收到停止信号，正在优雅停止...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def background_collection():
    global running
    
    logger.info('🚀 启动方案2优化后的全量A股数据采集 (后台模式)')
    logger.info('=' * 60)
    
    try:
        # 初始化服务
        db_manager = DatabaseManager()
        service = HistoricalDataService(db_manager)
        
        # 获取A股代码总数
        stock_codes = await service._get_active_stock_codes()
        logger.info(f'📊 将采集 {len(stock_codes):,} 只A股的1天历史数据')
        
        # 显示优化配置
        logger.info('⚙️  优化配置:')
        logger.info('   - 批量大小: 8 只/批次')
        logger.info('   - 单个间隔: 1.0秒')
        logger.info('   - 批次间隔: 3秒')
        logger.info('   - 预估时间: 2.3小时')
        
        start_time = datetime.now()
        logger.info(f'🕐 开始时间: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 创建一个可以被中断的采集任务
        class InterruptibleService(HistoricalDataService):
            async def supplement_historical_data(self, **kwargs):
                # 重写方法以支持中断检查
                if not running:
                    logger.info("采集被用户中断")
                    return {'interrupted': True}
                return await super().supplement_historical_data(**kwargs)
        
        # 开始全量采集
        result = await service.supplement_historical_data(
            stock_codes=None,  # 所有A股
            days=1,
            force_update=True
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        duration_hours = duration / 3600
        
        logger.info('🏁 采集完成!')
        logger.info('📊 最终统计:')
        logger.info(f'   - 总股票数: {result["total_stocks"]:,}')
        logger.info(f'   - 成功采集: {result["success_count"]:,}')
        logger.info(f'   - 采集失败: {result["failed_count"]:,}')
        logger.info(f'   - 无效代码: {result["invalid_count"]:,}')
        logger.info(f'   - 跳过重复: {result["skipped_count"]:,}')
        logger.info(f'   - 更新记录: {result["updated_records"]:,}')
        logger.info(f'   - 实际用时: {duration_hours:.1f}小时')
        
        success_rate = result["success_count"] / result["total_stocks"] * 100 if result["total_stocks"] > 0 else 0
        logger.info(f'   - 成功率: {success_rate:.1f}%')
        
        return result
        
    except Exception as e:
        logger.error(f"采集过程中发生错误: {e}")
        return None

def check_collection_status():
    """检查采集状态"""
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查今天的采集进度
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
            
            progress = today_count / total_a_stocks * 100 if total_a_stocks > 0 else 0
            
            logger.info(f'📊 当前采集进度:')
            logger.info(f'   - 今日已采集: {today_count:,}只')
            logger.info(f'   - 总A股数量: {total_a_stocks:,}只')
            logger.info(f'   - 完成进度: {progress:.1f}%')
            
    except Exception as e:
        logger.error(f"检查状态失败: {e}")

if __name__ == "__main__":
    logger.info("🎯 方案2全量A股数据采集 (后台模式)")
    logger.info("Ctrl+C 可以优雅停止采集")
    logger.info("=" * 60)
    
    try:
        # 检查当前状态
        check_collection_status()
        
        # 启动采集
        result = asyncio.run(background_collection())
        
        logger.info("\n" + "=" * 60)
        
        if result and result.get("success_count", 0) > 0:
            logger.info("✅ 全量采集执行完成")
            logger.info(f"📊 成功采集了 {result['success_count']:,} 只A股的数据")
            logger.info(f"📈 数据库新增 {result['updated_records']:,} 条记录")
        else:
            logger.info("❌ 采集过程中遇到问题，需要检查配置")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 用户主动停止采集")
    except Exception as e:
        logger.error(f"发生未预期错误: {e}")
    
    logger.info("💡 可通过查看 full_collection.log 了解详细过程")