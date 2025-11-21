"""
历史数据补充服务
用于获取和补充股票的历史K线数据，确保技术指标计算有足够的数据支撑
"""
import asyncio
import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import akshare as ak

logger = logging.getLogger(__name__)

class HistoricalDataService:
    """历史数据补充服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    async def supplement_historical_data(self, 
                                       stock_codes: List[str] = None,
                                       days: int = 3,
                                       force_update: bool = False) -> Dict:
        """
        补充历史数据
        
        Args:
            stock_codes: 股票代码列表，None表示所有股票
            days: 补充的天数
            force_update: 是否强制更新已存在的数据
            
        Returns:
            补充结果统计
        """
        start_time = datetime.now()
        
        # 获取需要补充的股票列表
        if stock_codes is None:
            stock_codes = await self._get_active_stock_codes()
            
        logger.info(f"📊 开始补充 {len(stock_codes)} 只股票的历史数据，回溯 {days} 天")
        
        stats = {
            'total_stocks': len(stock_codes),
            'success_count': 0,
            'failed_count': 0,
            'updated_records': 0,
            'skipped_count': 0,
            'invalid_count': 0,  # 新增：无效股票代码计数
            'failed_stocks': [],
            'invalid_stocks': []  # 新增：无效股票代码列表
        }
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        # 方案2：优化批量大小以提高采集效率
        batch_size = 8  # 增加批次大小，提高效率
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            
            # 串行处理而非并发，避免API频率限制
            batch_results = []
            for stock_code in batch:
                result = await self._supplement_single_stock(
                    stock_code, start_date, end_date, force_update
                )
                batch_results.append(result)
                
                # 减少每个请求之间的延迟
                await asyncio.sleep(1.0)  # 减少单个请求间隔
            
            # 统计结果
            for j, result in enumerate(batch_results):
                stock_code = batch[j]
                if isinstance(result, Exception):
                    stats['failed_count'] += 1
                    stats['failed_stocks'].append(stock_code)
                    logger.error(f"❌ {stock_code} 补充失败: {result}")
                elif result is None:
                    # 区分无效股票代码和数据获取失败
                    from services.reliable_data_fetcher import reliable_data_fetcher
                    if not reliable_data_fetcher._is_valid_stock_code(stock_code):
                        stats['invalid_count'] += 1
                        stats['invalid_stocks'].append(stock_code)
                        logger.debug(f"⚠️ {stock_code} 无效股票代码")
                    else:
                        stats['failed_count'] += 1
                        stats['failed_stocks'].append(stock_code)
                        logger.warning(f"❌ {stock_code} 数据获取失败")
                elif result:
                    if result['updated']:
                        stats['success_count'] += 1
                        stats['updated_records'] += result['records']
                    else:
                        stats['skipped_count'] += 1
                
            # 进度报告
            processed = min(i + batch_size, len(stock_codes))
            logger.info(f"📈 进度: {processed}/{len(stock_codes)} "
                       f"({processed/len(stock_codes)*100:.1f}%)")
            
            # 批次间减少休息时间以提高效率
            await asyncio.sleep(3)  # 减少批次间隔时间
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ 历史数据补充完成")
        logger.info(f"   总股票数: {stats['total_stocks']}")
        logger.info(f"   成功: {stats['success_count']}")
        logger.info(f"   跳过: {stats['skipped_count']}")
        logger.info(f"   失败: {stats['failed_count']}")
        logger.info(f"   无效代码: {stats['invalid_count']}")
        logger.info(f"   更新记录: {stats['updated_records']}")
        logger.info(f"   用时: {elapsed:.1f}秒")
        
        # 显示无效股票代码示例（前5个）
        if stats['invalid_stocks']:
            sample_invalid = stats['invalid_stocks'][:5]
            logger.info(f"   无效代码示例: {', '.join(sample_invalid)}")
        
        return stats
    
    async def _supplement_single_stock(self, 
                                     stock_code: str,
                                     start_date: str,
                                     end_date: str,
                                     force_update: bool) -> Optional[Dict]:
        """补充单只股票的历史数据"""
        try:
            # 检查是否需要更新
            if not force_update:
                existing_count = self._count_existing_data(stock_code, start_date, end_date)
                # 如果已有数据覆盖率超过80%，跳过
                expected_days = self._calculate_trading_days(start_date, end_date)
                if existing_count / expected_days > 0.8:
                    return {'updated': False, 'records': 0}
            
            # 获取历史数据
            df = await self._fetch_stock_history(stock_code, start_date, end_date)
            
            if df is None or df.empty:
                return None
                
            # 保存到数据库
            records_saved = await self._save_historical_data(stock_code, df, force_update)
            
            return {'updated': True, 'records': records_saved}
            
        except Exception as e:
            logger.debug(f"补充 {stock_code} 历史数据失败: {e}")
            return None
    
    async def _fetch_stock_history(self, 
                                 stock_code: str,
                                 start_date: str,
                                 end_date: str) -> Optional[pd.DataFrame]:
        """获取股票历史数据，使用可靠数据源"""
        
        try:
            # 使用可靠数据获取器
            from services.reliable_data_fetcher import reliable_data_fetcher
            
            # 计算需要的天数
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            days_needed = (end_dt - start_dt).days + 1
            
            # 使用可靠数据源获取数据
            df = await reliable_data_fetcher.fetch_stock_history(stock_code, days_needed)
            
            if df is not None and not df.empty:
                logger.debug(f"📊 获取 {stock_code} 历史数据: {len(df)}条记录")
                return df
            else:
                logger.warning(f"🚫 获取 {stock_code} 历史数据失败")
                return None
                
        except Exception as e:
            logger.warning(f"❌ 获取 {stock_code} 历史数据异常: {e}")
            return None
    
    
    async def _save_historical_data(self, 
                                  stock_code: str,
                                  df: pd.DataFrame,
                                  force_update: bool) -> int:
        """保存历史数据到数据库"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                saved_count = 0
                
                for _, row in df.iterrows():
                    # 检查是否已存在
                    if not force_update:
                        cursor.execute('''
                            SELECT COUNT(*) FROM daily_stock_changes 
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (stock_code, row['date']))
                        
                        if cursor.fetchone()[0] > 0:
                            continue
                    
                    # 插入或更新到 daily_stock_changes 表
                    cursor.execute('''
                        INSERT OR REPLACE INTO daily_stock_changes
                        (stock_code, trade_date, open_price, close_price, high_price, low_price,
                         volume, turnover, change_percent, market, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_code,
                        row['date'],
                        row['open'],
                        row['close'],
                        row['high'],
                        row['low'],
                        row['volume'],
                        row['amount'],
                        row['change_percent'],
                        'SH' if stock_code.startswith('6') else 'SZ',
                        datetime.now().isoformat()
                    ))
                    
                    saved_count += 1
                
                conn.commit()
                return saved_count
                
        except Exception as e:
            logger.error(f"保存 {stock_code} 历史数据失败: {e}")
            return 0
    
    def _count_existing_data(self, stock_code: str, start_date: str, end_date: str) -> int:
        """统计已有数据数量"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM daily_stock_changes 
                    WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
                ''', (stock_code, start_date, end_date))
                
                return cursor.fetchone()[0]
        except:
            return 0
    
    def _calculate_trading_days(self, start_date: str, end_date: str) -> int:
        """计算预期交易日数量（简化版）"""
        try:
            start = datetime.strptime(start_date, '%Y%m%d')
            end = datetime.strptime(end_date, '%Y%m%d')
            total_days = (end - start).days
            # 简化计算：去掉周末，大约70%是交易日
            return int(total_days * 0.7)
        except:
            return 60  # 默认值
    
    async def _get_latest_price(self, stock_code: str) -> float:
        """获取股票最新价格"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT close_price FROM daily_stock_changes 
                    WHERE stock_code = ? 
                    ORDER BY trade_date DESC 
                    LIMIT 1
                ''', (stock_code,))
                
                result = cursor.fetchone()
                return result[0] if result else 10.0
        except:
            return 10.0  # 默认价格
    
    async def _get_active_stock_codes(self) -> List[str]:
        """获取活跃A股代码列表（排除港股和B股）"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 仅获取A股代码（6位数字，特定前缀）
                cursor.execute('''
                    SELECT DISTINCT stock_code FROM daily_stock_changes 
                    WHERE trade_date >= date('now', '-30 days')
                    AND LENGTH(stock_code) = 6 
                    AND stock_code GLOB '[0-9][0-9][0-9][0-9][0-9][0-9]'
                    AND (
                        SUBSTR(stock_code, 1, 2) IN ('60', '68', '00', '30')
                    )
                    ORDER BY stock_code
                ''')
                
                stock_codes = [row[0] for row in cursor.fetchall()]
                
                # 如果A股数量太少，获取A股主要股票
                if len(stock_codes) < 100:
                    stock_codes.extend(self._get_major_stock_codes())
                
                logger.info(f"📊 获取到 {len(stock_codes)} 只A股代码")
                return list(set(stock_codes))  # 去重
                
        except Exception as e:
            logger.error(f"获取A股代码列表失败: {e}")
            return self._get_major_stock_codes()
    
    def _get_major_stock_codes(self) -> List[str]:
        """获取主要股票代码（备用）"""
        return [
            '000001', '000002', '000858', '000725', '000776',
            '600000', '600036', '600519', '600887', '600276',
            '002415', '002714', '002352', '002230', '002304'
        ]
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """转换股票代码为akshare格式"""
        if stock_code.startswith('6'):
            return stock_code + '.SH'
        else:
            return stock_code + '.SZ'

# 便捷函数
def get_historical_data_service(db_manager):
    """获取历史数据服务实例"""
    return HistoricalDataService(db_manager)