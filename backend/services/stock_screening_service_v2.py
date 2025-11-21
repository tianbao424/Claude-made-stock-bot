"""
股票甄选服务 V2 - 使用统一腾讯采集器
实现强势股识别、连续涨幅筛选等功能
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, StockScreening, DailyStockChange
from services.unified_tencent_collector import get_unified_collector

logger = logging.getLogger(__name__)

@dataclass
class ScreeningCriteria:
    """筛选条件"""
    screening_type: str
    min_consecutive_days: int = 3
    min_rise_percent: float = 7.0
    min_volume: int = 0
    market_filter: List[str] = None  # ['SH', 'SZ', 'HK']
    
    def to_dict(self) -> Dict:
        return {
            'screening_type': self.screening_type,
            'min_consecutive_days': self.min_consecutive_days,
            'min_rise_percent': self.min_rise_percent,
            'min_volume': self.min_volume,
            'market_filter': self.market_filter or ['SH', 'SZ', 'HK']
        }

@dataclass
class ScreeningResult:
    """筛选结果"""
    stock_code: str
    stock_name: str
    market: str
    consecutive_days: int
    avg_rise_percent: float
    total_volume: int
    avg_volume: int
    close_price: float
    turnover_rate: float = None
    market_cap: float = 0.0  # 市值(亿元)
    pe_ratio: float = 0.0    # 市盈率
    daily_changes: List[Dict] = None  # 每日涨跌详情

@dataclass
class ScreeningResponse:
    """筛选响应，包含结果和元数据"""
    results: List[ScreeningResult]
    screening_date: str  # 实际使用的数据日期
    total_count: int

class StockScreeningService:
    """股票甄选服务 V2"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def collect_daily_data(self, trade_date: str = None) -> int:
        """
        收集指定日期的股票数据（使用统一腾讯采集器）
        
        Args:
            trade_date: 交易日期，格式YYYY-MM-DD，默认为智能判断的目标日期
            
        Returns:
            收集到的股票数量
        """
        logger.info(f"🔄 开始使用统一腾讯采集器收集股票数据...")
        
        try:
            # 使用统一腾讯采集器
            unified_collector = get_unified_collector(self.db_manager)
            result = await unified_collector.collect_daily_stock_data(trade_date)
            
            if result.success:
                logger.info(f"✅ 统一数据收集成功: {result.successful_records}/{result.total_collected} "
                           f"({result.successful_records/result.total_collected*100:.1f}%) "
                           f"用时 {result.duration_seconds:.1f}s")
                return result.successful_records
            else:
                logger.error(f"❌ 统一数据收集失败: {result.error_message}")
                return 0
            
        except Exception as e:
            logger.error(f"❌ 统一数据收集异常: {e}")
            return 0
    
    async def screen_strong_rise_stocks(self, criteria: ScreeningCriteria) -> ScreeningResponse:
        """
        筛选强势上涨股票
        
        Args:
            criteria: 筛选条件
            
        Returns:
            ScreeningResponse: 筛选结果
        """
        logger.info(f"🔍 开始执行股票筛选: {criteria.screening_type}")
        
        try:
            # 获取可用的数据日期范围
            available_dates = self._get_available_dates(days_back=criteria.min_consecutive_days + 5)
            if len(available_dates) < criteria.min_consecutive_days:
                logger.warning(f"数据不足，需要 {criteria.min_consecutive_days} 天，实际只有 {len(available_dates)} 天")
                return ScreeningResponse(
                    results=[],
                    screening_date=available_dates[0] if available_dates else "无数据",
                    total_count=0
                )
            
            # 使用最新的N天数据进行筛选
            screening_dates = available_dates[:criteria.min_consecutive_days]
            latest_date = screening_dates[0]
            
            logger.info(f"使用数据日期范围: {screening_dates}")
            
            # 执行筛选逻辑
            if criteria.screening_type == 'strong_rise_3d':
                results = await self._filter_consecutive_rise_stocks(
                    screening_dates, criteria
                )
            elif criteria.screening_type == 'volume_surge':
                results = await self._filter_volume_surge_stocks(
                    screening_dates, criteria  
                )
            elif criteria.screening_type == 'breakthrough':
                results = await self._filter_breakthrough_stocks(
                    screening_dates, criteria
                )
            else:
                logger.warning(f"未支持的筛选类型: {criteria.screening_type}")
                results = []
            
            # 保存筛选结果
            if results:
                await self._save_screening_results(results, criteria, latest_date)
            
            response = ScreeningResponse(
                results=results,
                screening_date=latest_date,
                total_count=len(results)
            )
            
            logger.info(f"✅ 筛选完成，找到 {len(results)} 只符合条件的股票")
            return response
            
        except Exception as e:
            logger.error(f"❌ 股票筛选失败: {e}")
            return ScreeningResponse(
                results=[],
                screening_date="筛选失败",
                total_count=0
            )
    
    def _get_available_dates(self, days_back: int = 10) -> List[str]:
        """获取可用的交易日期"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT trade_date 
                    FROM daily_stock_changes 
                    ORDER BY trade_date DESC 
                    LIMIT ?
                ''', (days_back,))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取可用日期失败: {e}")
            return []
    
    async def _filter_consecutive_rise_stocks(self, dates: List[str], criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """筛选连续上涨股票"""
        import sqlite3
        results = []
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建日期占位符
                date_placeholders = ','.join(['?' for _ in dates])
                market_filter = tuple(criteria.market_filter) if criteria.market_filter else ('SH', 'SZ')
                market_placeholders = ','.join(['?' for _ in market_filter])
                
                # 查询在指定日期范围内连续上涨的股票
                query = f'''
                    SELECT 
                        stock_code,
                        COUNT(*) as rise_days,
                        AVG(change_percent) as avg_change,
                        AVG(volume) as avg_volume,
                        SUM(volume) as total_volume,
                        MIN(close_price) as min_price,
                        MAX(close_price) as max_price,
                        (SELECT close_price FROM daily_stock_changes d2 
                         WHERE d2.stock_code = d1.stock_code AND d2.trade_date = ? 
                         ORDER BY trade_date DESC LIMIT 1) as latest_price,
                        (SELECT total_market_cap FROM daily_stock_changes d3
                         WHERE d3.stock_code = d1.stock_code AND d3.trade_date = ?
                         ORDER BY trade_date DESC LIMIT 1) as market_cap,
                        (SELECT turnover_rate FROM daily_stock_changes d4
                         WHERE d4.stock_code = d1.stock_code AND d4.trade_date = ?
                         ORDER BY trade_date DESC LIMIT 1) as turnover_rate,
                        (SELECT pe_ratio FROM daily_stock_changes d5
                         WHERE d5.stock_code = d1.stock_code AND d5.trade_date = ?
                         ORDER BY trade_date DESC LIMIT 1) as pe_ratio
                    FROM daily_stock_changes d1
                    WHERE d1.trade_date IN ({date_placeholders})
                        AND d1.change_percent >= ?
                        AND d1.market IN ({market_placeholders})
                        AND d1.volume >= ?
                    GROUP BY d1.stock_code
                    HAVING COUNT(*) >= ?
                        AND AVG(d1.change_percent) >= ?
                    ORDER BY AVG(d1.change_percent) DESC, SUM(d1.volume) DESC
                    LIMIT 100
                '''
                
                # 执行查询
                params = (
                    dates[0], dates[0], dates[0], dates[0],  # 最新日期用于获取最新数据
                    *dates,  # 日期范围
                    0.0,  # 最小涨幅（这里设为0，具体筛选在HAVING中）
                    *market_filter,  # 市场过滤
                    criteria.min_volume,  # 最小成交量
                    criteria.min_consecutive_days,  # 最少连续天数
                    criteria.min_rise_percent  # 平均涨幅要求
                )
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # 获取股票名称
                stock_names = self._get_stock_names([row[0] for row in rows])
                
                # 构建结果
                for row in rows:
                    stock_code = row[0]
                    result = ScreeningResult(
                        stock_code=stock_code,
                        stock_name=stock_names.get(stock_code, '未知'),
                        market=self._get_market_from_code(stock_code),
                        consecutive_days=int(row[1]),
                        avg_rise_percent=float(row[2]),
                        avg_volume=int(row[3]),
                        total_volume=int(row[4]),
                        close_price=float(row[7]) if row[7] else 0.0,
                        market_cap=float(row[8]) / 10000 if row[8] else 0.0,  # 转换为亿元
                        turnover_rate=float(row[9]) if row[9] else 0.0,
                        pe_ratio=float(row[10]) if row[10] else 0.0
                    )
                    results.append(result)
                
                logger.info(f"✅ 筛选到 {len(results)} 只连续上涨股票")
                
        except Exception as e:
            logger.error(f"❌ 连续上涨筛选失败: {e}")
            
        return results
    
    async def _filter_volume_surge_stocks(self, dates: List[str], criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """筛选成交量暴增股票"""
        # 这里可以实现成交量激增的筛选逻辑
        logger.info("成交量暴增筛选功能待实现")
        return []
    
    async def _filter_breakthrough_stocks(self, dates: List[str], criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """筛选突破股票"""
        # 这里可以实现技术突破的筛选逻辑
        logger.info("技术突破筛选功能待实现")
        return []
    
    def _get_stock_names(self, stock_codes: List[str]) -> Dict[str, str]:
        """批量获取股票名称"""
        import sqlite3
        names = {}
        
        try:
            if not stock_codes:
                return names
                
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                placeholders = ','.join(['?' for _ in stock_codes])
                cursor.execute(f'''
                    SELECT stock_code, stock_name 
                    FROM stock_pool 
                    WHERE stock_code IN ({placeholders})
                ''', stock_codes)
                
                for row in cursor.fetchall():
                    names[row[0]] = row[1]
                    
        except Exception as e:
            logger.error(f"获取股票名称失败: {e}")
            
        return names
    
    def _get_market_from_code(self, stock_code: str) -> str:
        """根据股票代码判断市场"""
        if stock_code.startswith('6'):
            return 'SH'
        elif stock_code.startswith(('0', '3')):
            return 'SZ'
        else:
            return 'OTHER'
    
    async def _save_screening_results(self, results: List[ScreeningResult], criteria: ScreeningCriteria, screening_date: str):
        """保存筛选结果到数据库"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for result in results:
                    screening = StockScreening(
                        stock_code=result.stock_code,
                        stock_name=result.stock_name,
                        market=result.market,
                        screening_type=criteria.screening_type,
                        consecutive_days=result.consecutive_days,
                        avg_rise_percent=result.avg_rise_percent,
                        total_volume=result.total_volume,
                        avg_volume=result.avg_volume,
                        close_price=result.close_price,
                        screening_date=screening_date,
                        criteria=json.dumps(criteria.to_dict()),
                        created_at=datetime.now().isoformat()
                    )
                    
                    # 保存到数据库
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_screening 
                        (stock_code, stock_name, market, screening_type, consecutive_days,
                         avg_rise_percent, total_volume, avg_volume, close_price,
                         screening_date, criteria, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        screening.stock_code, screening.stock_name, screening.market,
                        screening.screening_type, screening.consecutive_days,
                        screening.avg_rise_percent, screening.total_volume,
                        screening.avg_volume, screening.close_price,
                        screening.screening_date, screening.criteria,
                        screening.created_at
                    ))
                
                conn.commit()
                logger.info(f"💾 保存了 {len(results)} 条筛选结果")
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")

    async def initialize_historical_data(self, days_back: int = 7) -> Dict[str, Any]:
        """初始化历史数据"""
        logger.info(f"🚀 开始初始化历史数据，回溯 {days_back} 天...")
        
        success_days = 0
        failed_days = 0
        total_records = 0
        
        unified_collector = get_unified_collector(self.db_manager)
        
        # 计算需要收集的日期
        for i in range(days_back):
            target_date = (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')
            
            try:
                result = await unified_collector.collect_daily_stock_data(target_date)
                if result.success:
                    success_days += 1
                    total_records += result.successful_records
                    logger.info(f"✅ {target_date}: {result.successful_records} 条记录")
                else:
                    failed_days += 1
                    logger.warning(f"❌ {target_date}: {result.error_message}")
                    
                # 添加延迟避免请求过快
                await asyncio.sleep(1)
                
            except Exception as e:
                failed_days += 1
                logger.error(f"❌ {target_date}: {e}")
        
        return {
            'success_days': success_days,
            'failed_days': failed_days,
            'total_records': total_records
        }

# 全局服务实例
stock_screening_service: Optional[StockScreeningService] = None

def get_stock_screening_service(db_manager: DatabaseManager) -> StockScreeningService:
    """获取股票甄选服务实例"""
    global stock_screening_service
    
    if stock_screening_service is None:
        stock_screening_service = StockScreeningService(db_manager)
    
    return stock_screening_service