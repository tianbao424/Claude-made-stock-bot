#!/usr/bin/env python3
"""
市值数据增量更新服务
专门用于补充缺失的股票市值数据，支持批量更新和增量同步
"""
import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from services.akshare_service import akshare_service

logger = logging.getLogger(__name__)

class UpdateStrategy(Enum):
    """更新策略"""
    ALL_MISSING = "all_missing"          # 所有缺失的
    ACTIVE_STOCKS = "active_stocks"      # 有交易数据的
    BY_EXCHANGE = "by_exchange"          # 按交易所
    BY_INDUSTRY = "by_industry"          # 按行业
    PRIORITY_LIST = "priority_list"      # 优先列表

@dataclass
class UpdateProgress:
    """更新进度"""
    total_targets: int
    completed: int
    failed: int
    skipped: int
    start_time: datetime
    current_symbol: str = ""
    error_count: int = 0
    
    @property
    def progress_percent(self) -> float:
        if self.total_targets == 0:
            return 0.0
        return (self.completed / self.total_targets) * 100
    
    @property
    def success_rate(self) -> float:
        processed = self.completed + self.failed
        if processed == 0:
            return 0.0
        return (self.completed / processed) * 100

@dataclass 
class UpdateResult:
    """更新结果"""
    success: bool
    total_targets: int
    successful_updates: int
    failed_updates: int
    skipped_updates: int
    execution_time: float
    errors: List[str]
    updated_stocks: List[str]

class MarketCapUpdater:
    """市值数据更新器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.progress: Optional[UpdateProgress] = None
        
        # 重试配置
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]  # 秒
        self.request_interval = 1.0  # 请求间隔，避免频率限制
        
    def get_missing_market_cap_stocks(self, 
                                    strategy: UpdateStrategy = UpdateStrategy.ACTIVE_STOCKS,
                                    limit: int = 100,
                                    exchange_filter: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """获取缺失市值数据的股票列表"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            base_query = '''
                SELECT si.symbol, si.name, si.industry
                FROM stock_info si
                WHERE (si.market_cap IS NULL OR si.market_cap = 0)
                  AND si.is_active = 1
            '''
            
            if strategy == UpdateStrategy.ACTIVE_STOCKS:
                # 优先有交易数据的股票
                query = base_query + '''
                    AND EXISTS (
                        SELECT 1 FROM daily_stock_changes dsc 
                        WHERE dsc.stock_code = si.symbol 
                          AND dsc.trade_date >= date('now', '-30 days')
                          AND dsc.volume > 0
                    )
                '''
                
            elif strategy == UpdateStrategy.BY_EXCHANGE:
                if exchange_filter == 'SZ':
                    query = base_query + " AND (si.symbol LIKE '0%' OR si.symbol LIKE '3%')"
                elif exchange_filter == 'SH':
                    query = base_query + " AND si.symbol LIKE '6%'"
                elif exchange_filter == 'BJ':
                    query = base_query + " AND (si.symbol LIKE '8%' OR si.symbol LIKE '4%')"
                else:
                    query = base_query
                    
            elif strategy == UpdateStrategy.PRIORITY_LIST:
                # 优先重要行业
                query = base_query + '''
                    AND si.industry IN ('银行', '保险', '证券', '房地产', '石油石化', 
                                       '钢铁', '汽车', '电子', '医药', '食品饮料', 
                                       '家用电器', '建筑材料', '化工')
                '''
            else:
                query = base_query
            
            query += f" ORDER BY si.symbol LIMIT {limit}"
            
            cursor.execute(query)
            return cursor.fetchall()
    
    async def update_single_stock_market_cap(self, symbol: str, retries: int = 0) -> Optional[Dict[str, Any]]:
        """更新单只股票的市值数据"""
        try:
            logger.debug(f"🔄 更新股票 {symbol} 的市值数据...")
            
            # 判断市场类型
            if symbol.startswith('6'):
                market = 'SH'
            elif symbol.startswith(('0', '3')):
                market = 'SZ'
            elif symbol.startswith(('8', '4')):
                market = 'BJ'
            else:
                market = 'A'
            
            # 获取实时数据
            realtime_data = await akshare_service.get_stock_realtime_data(symbol, market)
            
            if realtime_data and realtime_data.get('market_cap', 0) > 0 and not realtime_data.get('is_simulated', False):
                # 更新到数据库
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE stock_info 
                        SET market_cap = ?, 
                            pe_ratio = ?,
                            pb_ratio = ?,
                            updated_at = ?
                        WHERE symbol = ?
                    ''', (
                        realtime_data['market_cap'],
                        realtime_data.get('pe_ratio', 0),
                        realtime_data.get('pb_ratio', 0),
                        datetime.now().isoformat(),
                        symbol
                    ))
                    conn.commit()
                
                logger.debug(f"✅ {symbol} 市值更新成功: {realtime_data['market_cap']:,.0f}")
                return {
                    'symbol': symbol,
                    'market_cap': realtime_data['market_cap'],
                    'pe_ratio': realtime_data.get('pe_ratio', 0),
                    'pb_ratio': realtime_data.get('pb_ratio', 0),
                    'success': True
                }
            else:
                logger.warning(f"⚠️ {symbol} 未获取到有效市值数据")
                return None
                
        except Exception as e:
            if retries < self.max_retries:
                delay = self.retry_delays[min(retries, len(self.retry_delays) - 1)]
                logger.warning(f"⚠️ {symbol} 更新失败，{delay}秒后重试 ({retries+1}/{self.max_retries}): {e}")
                await asyncio.sleep(delay)
                return await self.update_single_stock_market_cap(symbol, retries + 1)
            else:
                logger.error(f"❌ {symbol} 更新失败，已达最大重试次数: {e}")
                return None
    
    async def batch_update_market_cap(self, 
                                    strategy: UpdateStrategy = UpdateStrategy.ACTIVE_STOCKS,
                                    limit: int = 100,
                                    exchange_filter: Optional[str] = None) -> UpdateResult:
        """批量更新市值数据"""
        start_time = datetime.now()
        
        # 获取目标股票列表
        targets = self.get_missing_market_cap_stocks(strategy, limit, exchange_filter)
        
        if not targets:
            logger.warning("⚠️ 没有找到需要更新的股票")
            return UpdateResult(
                success=False,
                total_targets=0,
                successful_updates=0,
                failed_updates=0,
                skipped_updates=0,
                execution_time=0,
                errors=["没有找到需要更新的股票"],
                updated_stocks=[]
            )
        
        logger.info(f"🎯 开始批量更新市值数据，目标股票: {len(targets)}只")
        
        # 初始化进度
        self.progress = UpdateProgress(
            total_targets=len(targets),
            completed=0,
            failed=0,
            skipped=0,
            start_time=start_time
        )
        
        successful_updates = 0
        failed_updates = 0
        updated_stocks = []
        errors = []
        
        for i, (symbol, name, industry) in enumerate(targets):
            self.progress.current_symbol = f"{symbol} {name}"
            
            try:
                # 更新单只股票
                result = await self.update_single_stock_market_cap(symbol)
                
                if result and result.get('success'):
                    successful_updates += 1
                    updated_stocks.append(symbol)
                    self.progress.completed += 1
                    
                    if successful_updates % 10 == 0:
                        logger.info(f"📊 已成功更新 {successful_updates}/{len(targets)} 只股票...")
                else:
                    failed_updates += 1
                    self.progress.failed += 1
                    errors.append(f"{symbol}: 获取数据失败")
                
                # 控制请求频率
                if i < len(targets) - 1:  # 不是最后一个
                    await asyncio.sleep(self.request_interval)
                
            except Exception as e:
                failed_updates += 1
                self.progress.failed += 1
                error_msg = f"{symbol}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ 处理 {symbol} 时发生错误: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        result = UpdateResult(
            success=successful_updates > 0,
            total_targets=len(targets),
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            skipped_updates=0,
            execution_time=execution_time,
            errors=errors[:10],  # 只保留前10个错误
            updated_stocks=updated_stocks
        )
        
        logger.info(f"✅ 批量更新完成:")
        logger.info(f"  - 目标股票: {result.total_targets}")
        logger.info(f"  - 成功更新: {result.successful_updates}")
        logger.info(f"  - 更新失败: {result.failed_updates}")
        logger.info(f"  - 成功率: {self.progress.success_rate:.1f}%")
        logger.info(f"  - 执行时间: {result.execution_time:.1f}秒")
        
        return result
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """获取更新统计信息"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 总体统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_stocks,
                    COUNT(CASE WHEN market_cap > 0 THEN 1 END) as has_market_cap,
                    COUNT(CASE WHEN market_cap IS NULL OR market_cap = 0 THEN 1 END) as missing_market_cap
                FROM stock_info 
                WHERE is_active = 1
            ''')
            total, has_cap, missing = cursor.fetchone()
            
            # 按交易所统计
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN symbol LIKE '6%' THEN 'SH'
                        WHEN symbol LIKE '0%' OR symbol LIKE '3%' THEN 'SZ'
                        WHEN symbol LIKE '8%' OR symbol LIKE '4%' THEN 'BJ'
                        ELSE 'OTHER'
                    END as exchange,
                    COUNT(*) as total,
                    COUNT(CASE WHEN market_cap > 0 THEN 1 END) as has_cap
                FROM stock_info 
                WHERE is_active = 1
                GROUP BY exchange
                ORDER BY total DESC
            ''')
            exchange_stats = cursor.fetchall()
            
            # 最近更新情况
            cursor.execute('''
                SELECT COUNT(*) 
                FROM stock_info 
                WHERE market_cap > 0 
                  AND DATE(updated_at) >= DATE('now', '-7 days')
            ''')
            recent_updates = cursor.fetchone()[0]
            
            return {
                'total_stocks': total,
                'has_market_cap': has_cap,
                'missing_market_cap': missing,
                'coverage_rate': (has_cap / total) * 100 if total > 0 else 0,
                'exchange_breakdown': [
                    {
                        'exchange': ex,
                        'total': tot,
                        'has_cap': cap,
                        'coverage_rate': (cap / tot) * 100 if tot > 0 else 0
                    }
                    for ex, tot, cap in exchange_stats
                ],
                'recent_updates_7days': recent_updates
            }

# 创建全局实例
def get_market_cap_updater(db_manager: DatabaseManager) -> MarketCapUpdater:
    """获取市值更新器实例"""
    return MarketCapUpdater(db_manager)

# 测试和演示函数
async def test_market_cap_updater():
    """测试市值更新器"""
    print("🧪 测试市值数据更新器")
    
    # 初始化
    db_path = "stock_pool.db"
    db_manager = DatabaseManager(db_path)
    updater = get_market_cap_updater(db_manager)
    
    # 获取当前统计
    print("\n📊 当前市值数据统计:")
    stats = updater.get_update_statistics()
    print(f"  总股票数: {stats['total_stocks']:,}")
    print(f"  有市值数据: {stats['has_market_cap']:,}")
    print(f"  缺失市值数据: {stats['missing_market_cap']:,}")
    print(f"  覆盖率: {stats['coverage_rate']:.1f}%")
    
    # 获取待更新股票
    print("\n🎯 待更新股票样本:")
    targets = updater.get_missing_market_cap_stocks(UpdateStrategy.ACTIVE_STOCKS, 10)
    for symbol, name, industry in targets[:5]:
        print(f"  {symbol} {name} ({industry})")
    
    # 测试小批量更新
    print("\n🔄 测试小批量更新（5只股票）...")
    result = await updater.batch_update_market_cap(UpdateStrategy.ACTIVE_STOCKS, 5)
    
    print(f"✅ 测试完成:")
    print(f"  成功更新: {result.successful_updates}")
    print(f"  更新失败: {result.failed_updates}")
    print(f"  执行时间: {result.execution_time:.1f}秒")
    
    if result.updated_stocks:
        print(f"  更新的股票: {', '.join(result.updated_stocks[:3])}...")

if __name__ == "__main__":
    asyncio.run(test_market_cap_updater())