"""
增强的数据采集服务
从外部数据源采集市值、换手率等财务数据
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sqlite3
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from services.improved_akshare_service import improved_akshare_service

logger = logging.getLogger(__name__)

class EnhancedDataCollector:
    """增强的数据采集器，专门用于采集财务指标数据"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.akshare_service = improved_akshare_service
        
    async def collect_stock_financial_data(self, stock_code: str, max_retries: int = 3) -> Optional[Dict]:
        """
        采集单只股票的财务数据（带重试机制和连接优化）
        
        Args:
            stock_code: 股票代码
            max_retries: 最大重试次数
            
        Returns:
            Dict包含: market_cap, circulating_cap, total_shares, circulating_shares, turnover_rate
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.debug(f"🔄 {stock_code} 第 {attempt + 1} 次尝试...")
                    # 重试前等待更长时间，避免连接冲突
                    wait_time = min(3 ** attempt, 15)  # 3秒、9秒、15秒递增
                    await asyncio.sleep(wait_time)
                
                # 在每次请求前稍作延迟，避免过快请求
                await asyncio.sleep(0.5)
                
                # 使用akshare获取个股信息
                import akshare as ak
                
                # 设置请求超时和重试机制
                try:
                    data = ak.stock_individual_info_em(symbol=stock_code)
                except Exception as ak_error:
                    # 如果是连接错误，立即重试
                    if "Connection" in str(ak_error) or "Remote" in str(ak_error):
                        logger.debug(f"🔌 {stock_code} 连接错误，等待重试: {ak_error}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                    raise ak_error
                
                if data is None or len(data) == 0:
                    logger.warning(f"⚠️ {stock_code} 未获取到个股信息")
                    return None
                
                # 解析数据
                info_dict = {}
                for _, row in data.iterrows():
                    info_dict[row['item']] = row['value']
                
                # 验证关键数据
                total_market_cap = float(info_dict.get('总市值', 0))
                circulating_shares = float(info_dict.get('流通股', 0))
                
                if total_market_cap <= 0 and circulating_shares <= 0:
                    logger.warning(f"⚠️ {stock_code} 财务数据无效")
                    return None
                
                # 提取财务数据
                financial_data = {
                    'stock_code': stock_code,
                    'total_market_cap': total_market_cap,                        # 总市值 
                    'circulating_market_cap': float(info_dict.get('流通市值', 0)), # 流通市值
                    'total_shares': float(info_dict.get('总股本', 0)),            # 总股本
                    'circulating_shares': circulating_shares,                    # 流通股
                    'current_price': float(info_dict.get('最新', 0)),             # 当前价格
                    'industry': info_dict.get('行业', ''),                       # 行业
                    'listing_date': info_dict.get('上市时间', ''),                # 上市时间
                    'collection_date': datetime.now().strftime('%Y-%m-%d'),
                    'collection_time': datetime.now().isoformat()
                }
                
                logger.debug(f"✅ {stock_code} 财务数据采集成功")
                return financial_data
                
            except Exception as e:
                error_msg = str(e)
                if attempt == max_retries - 1:
                    logger.error(f"❌ 采集 {stock_code} 财务数据失败（已重试 {max_retries} 次）: {error_msg}")
                    return None
                else:
                    # 根据错误类型决定是否继续重试
                    if "Connection" in error_msg or "Remote" in error_msg or "timeout" in error_msg.lower():
                        logger.debug(f"🔌 {stock_code} 第 {attempt + 1} 次网络错误: {error_msg[:50]}...")
                        continue
                    else:
                        # 非网络错误，直接返回
                        logger.warning(f"⚠️ {stock_code} 数据错误（不重试）: {error_msg[:50]}...")
                        return None
        
        return None
    
    async def calculate_accurate_turnover_rate(self, stock_code: str, trade_date: str) -> Optional[float]:
        """
        计算准确的换手率
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            换手率百分比
        """
        try:
            # 1. 获取财务数据（流通股）
            financial_data = await self.collect_stock_financial_data(stock_code)
            if not financial_data or financial_data['circulating_shares'] <= 0:
                logger.warning(f"⚠️ {stock_code} 流通股数据不可用")
                return None
            
            # 2. 获取交易数据（成交量）
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT volume FROM daily_stock_changes 
                    WHERE stock_code = ? AND trade_date = ?
                ''', (stock_code, trade_date))
                
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"⚠️ {stock_code} {trade_date} 交易数据不存在")
                    return None
                
                volume = result[0]
            
            # 3. 计算换手率
            # 换手率 = (成交量 / 流通股) × 100%
            turnover_rate = (volume / financial_data['circulating_shares']) * 100
            
            logger.debug(f"📊 {stock_code} {trade_date} 换手率计算:")
            logger.debug(f"  - 成交量: {volume:,} 股")
            logger.debug(f"  - 流通股: {financial_data['circulating_shares']:,} 股")
            logger.debug(f"  - 换手率: {turnover_rate:.4f}%")
            
            return turnover_rate
            
        except Exception as e:
            logger.error(f"❌ 计算 {stock_code} {trade_date} 换手率失败: {e}")
            return None
    
    async def update_stock_financial_info(self, stock_codes: List[str], batch_size: int = 10) -> Dict[str, any]:
        """
        批量更新股票财务信息到数据库（分批处理）
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 每批处理的股票数量
            
        Returns:
            更新统计信息
        """
        logger.info(f"🔄 开始批量更新财务信息，股票数量: {len(stock_codes)}")
        logger.info(f"📦 分批处理，每批 {batch_size} 只股票")
        
        success_count = 0
        error_count = 0
        network_error_count = 0
        data_invalid_count = 0
        updated_stocks = []
        
        # 分批处理
        for batch_start in range(0, len(stock_codes), batch_size):
            batch_end = min(batch_start + batch_size, len(stock_codes))
            batch_codes = stock_codes[batch_start:batch_end]
            
            logger.info(f"📊 处理第 {batch_start//batch_size + 1} 批 ({batch_start + 1}-{batch_end}/{len(stock_codes)})")
            
            batch_success = 0
            batch_errors = 0
            
            for stock_code in batch_codes:
                try:
                    # 采集财务数据（带重试）
                    financial_data = await self.collect_stock_financial_data(stock_code, max_retries=2)
                    if not financial_data:
                        error_count += 1
                        data_invalid_count += 1
                        continue
                    
                    # 更新stock_info表
                    with sqlite3.connect(self.db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # 更新市值等信息
                        cursor.execute('''
                            UPDATE stock_info 
                            SET market_cap = ?, 
                                industry = ?,
                                updated_at = ?
                            WHERE symbol = ?
                        ''', (
                            financial_data['total_market_cap'],
                            financial_data['industry'],
                            financial_data['collection_time'],
                            stock_code
                        ))
                        
                        # 如果没有更新到记录，插入新记录
                        if cursor.rowcount == 0:
                            cursor.execute('''
                                INSERT OR REPLACE INTO stock_info 
                                (symbol, name, market_cap, industry, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                stock_code,
                                f'股票{stock_code}',  # 临时名称
                                financial_data['total_market_cap'],
                                financial_data['industry'],
                                financial_data['collection_time'],
                                financial_data['collection_time']
                            ))
                        
                        conn.commit()
                        
                    success_count += 1
                    batch_success += 1
                    updated_stocks.append(stock_code)
                    
                    # 控制请求频率，避免API过载
                    await asyncio.sleep(1.0)  # 每个请求间隔1秒，更保守
                    
                except Exception as e:
                    error_count += 1
                    batch_errors += 1
                    if "Connection" in str(e) or "Remote" in str(e):
                        network_error_count += 1
                    logger.debug(f"❌ 更新 {stock_code} 财务信息失败: {e}")
            
            logger.info(f"  批次完成: 成功 {batch_success}, 失败 {batch_errors}")
            
            # 批次间停顿，避免过载
            if batch_end < len(stock_codes):
                logger.info("⏱️ 批次间休息 5 秒...")
                await asyncio.sleep(5)  # 增加批次间休息时间
        
        result = {
            'total_requested': len(stock_codes),
            'success_count': success_count,
            'error_count': error_count,
            'network_error_count': network_error_count,
            'data_invalid_count': data_invalid_count,
            'updated_stocks': updated_stocks,
            'update_time': datetime.now().isoformat()
        }
        
        logger.info(f"📊 财务信息更新完成:")
        logger.info(f"  - 请求总数: {result['total_requested']}")
        logger.info(f"  - 成功: {result['success_count']}")
        logger.info(f"  - 失败: {result['error_count']}")
        logger.info(f"    - 网络错误: {network_error_count}")
        logger.info(f"    - 数据无效: {data_invalid_count}")
        logger.info(f"  - 成功率: {(success_count/len(stock_codes)*100):.1f}%")
        
        return result
    
    async def enhance_daily_stock_data_with_turnover_rate(self, trade_date: str) -> Dict[str, any]:
        """
        为指定日期的股票数据添加准确的换手率
        
        Args:
            trade_date: 交易日期
            
        Returns:
            处理统计信息
        """
        logger.info(f"🔄 开始计算 {trade_date} 的准确换手率...")
        
        # 1. 获取该日期的所有股票交易数据
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT stock_code FROM daily_stock_changes 
                WHERE trade_date = ? AND volume > 0
            ''', (trade_date,))
            
            stock_codes = [row[0] for row in cursor.fetchall()]
        
        if not stock_codes:
            logger.warning(f"⚠️ {trade_date} 没有找到交易数据")
            return {'error': '没有找到交易数据'}
        
        logger.info(f"📊 找到 {len(stock_codes)} 只有交易数据的股票")
        
        # 2. 为每只股票计算换手率
        success_count = 0
        error_count = 0
        
        for stock_code in stock_codes:
            try:
                turnover_rate = await self.calculate_accurate_turnover_rate(stock_code, trade_date)
                
                if turnover_rate is not None:
                    # 更新数据库中的换手率
                    with sqlite3.connect(self.db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # 检查是否有对应的技术指标记录
                        cursor.execute('''
                            SELECT id FROM stock_technical_indicators 
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (stock_code, trade_date))
                        
                        if cursor.fetchone():
                            # 更新现有记录
                            cursor.execute('''
                                UPDATE stock_technical_indicators 
                                SET turnover_rate = ?, updated_at = ?
                                WHERE stock_code = ? AND trade_date = ?
                            ''', (turnover_rate, datetime.now().isoformat(), stock_code, trade_date))
                        else:
                            # 插入新记录
                            cursor.execute('''
                                INSERT INTO stock_technical_indicators 
                                (stock_code, trade_date, turnover_rate, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                stock_code, trade_date, turnover_rate,
                                datetime.now().isoformat(),
                                datetime.now().isoformat()
                            ))
                        
                        conn.commit()
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        logger.info(f"📊 已处理 {success_count}/{len(stock_codes)} 只股票...")
                
                else:
                    error_count += 1
                    
                # 避免请求过于频繁
                await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"❌ 处理 {stock_code} 换手率失败: {e}")
                error_count += 1
        
        result = {
            'trade_date': trade_date,
            'total_stocks': len(stock_codes),
            'success_count': success_count,
            'error_count': error_count,
            'process_time': datetime.now().isoformat()
        }
        
        logger.info(f"✅ {trade_date} 换手率计算完成:")
        logger.info(f"  - 总股票数: {result['total_stocks']}")
        logger.info(f"  - 成功: {result['success_count']}")
        logger.info(f"  - 失败: {result['error_count']}")
        logger.info(f"  - 成功率: {(success_count/len(stock_codes)*100):.1f}%")
        
        return result

# 创建全局实例
def get_enhanced_data_collector(db_manager: DatabaseManager) -> EnhancedDataCollector:
    """获取增强数据采集器实例"""
    return EnhancedDataCollector(db_manager)