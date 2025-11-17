#!/usr/bin/env python3
"""
股票信息全量更新器
基于腾讯API的全量股票信息更新服务
"""
import asyncio
import logging
import sqlite3
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Set

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from services.tencent_data_service import TencentDataService

logger = logging.getLogger(__name__)

class StockInfoUpdater:
    """股票信息全量更新器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.tencent_service = TencentDataService(db_manager)
        
    async def full_update_stock_info(self) -> Dict[str, Any]:
        """
        全量更新股票信息
        通过扫描所有可能的股票代码，发现和更新完整的股票列表
        
        Returns:
            Dict: 更新结果统计
        """
        logger.info("🚀 开始全量更新股票信息...")
        
        result = {
            'total_scanned': 0,
            'valid_stocks': 0,
            'new_stocks': 0,
            'updated_stocks': 0,
            'removed_stocks': 0,
            'execution_time': 0,
            'success': False
        }
        
        start_time = datetime.now()
        
        try:
            # 1. 获取现有股票信息
            existing_stocks = self._get_existing_stocks()
            logger.info(f"📊 现有股票数量: {len(existing_stocks)}")
            
            # 2. 扫描并获取所有有效股票
            valid_stocks = await self._scan_all_stocks()
            result['total_scanned'] = self._get_total_scan_count()
            result['valid_stocks'] = len(valid_stocks)
            
            logger.info(f"🔍 扫描发现有效股票: {len(valid_stocks)} 只")
            
            # 3. 分析差异
            analysis = self._analyze_differences(existing_stocks, valid_stocks)
            
            # 4. 执行更新操作
            new_count = await self._add_new_stocks(analysis['new_stocks'])
            updated_count = await self._update_existing_stocks(analysis['updated_stocks'])
            removed_count = await self._remove_inactive_stocks(analysis['removed_stocks'])
            
            result['new_stocks'] = new_count
            result['updated_stocks'] = updated_count
            result['removed_stocks'] = removed_count
            result['success'] = True
            
            # 5. 更新统计信息
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            
            logger.info(f"✅ 股票信息全量更新完成:")
            logger.info(f"   新增股票: {new_count} 只")
            logger.info(f"   更新股票: {updated_count} 只") 
            logger.info(f"   移除股票: {removed_count} 只")
            logger.info(f"   执行时间: {execution_time:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ 股票信息全量更新失败: {e}")
            result['error'] = str(e)
            result['execution_time'] = (datetime.now() - start_time).total_seconds()
            
        return result
    
    def _get_existing_stocks(self) -> Dict[str, Dict[str, Any]]:
        """获取现有股票信息"""
        stocks = {}
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, name, market, is_active
                    FROM stock_info
                    WHERE LENGTH(symbol) = 6
                ''')
                
                for row in cursor.fetchall():
                    symbol, name, market, is_active = row
                    stocks[symbol] = {
                        'name': name,
                        'market': market,
                        'is_active': bool(is_active)
                    }
                    
        except Exception as e:
            logger.error(f"❌ 获取现有股票失败: {e}")
            
        return stocks
    
    async def _scan_all_stocks(self) -> Dict[str, Dict[str, Any]]:
        """扫描所有可能的股票代码"""
        valid_stocks = {}
        
        # 定义A股代码范围
        scan_ranges = [
            # 深交所主板: 000001-000999
            ('000', 1, 999),
            # 深交所中小板: 002001-002999  
            ('002', 1, 999),
            # 深交所创业板: 300001-300999
            ('300', 1, 999),
            # 上交所主板: 600000-603999
            ('600', 0, 999),
            ('601', 0, 999), 
            ('603', 0, 999),
            # 上交所科创板: 688001-688999
            ('688', 1, 999),
            # 北交所: 430001-430999, 830001-830999
            ('430', 1, 999),
            ('830', 1, 999)
        ]
        
        total_codes = []
        for prefix, start, end in scan_ranges:
            for num in range(start, end + 1):
                code = f"{prefix}{num:03d}"
                total_codes.append(code)
        
        logger.info(f"📡 开始扫描 {len(total_codes)} 个可能的股票代码...")
        
        # 分批扫描，每批50个
        batch_size = 50
        total_batches = (len(total_codes) + batch_size - 1) // batch_size
        
        async with self.tencent_service as service:
            for i in range(0, len(total_codes), batch_size):
                batch_codes = total_codes[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                try:
                    batch_data = await service.get_stock_data(batch_codes)
                    
                    if batch_data:
                        for stock_code, data in batch_data.items():
                            # 验证股票数据有效性
                            if self._is_valid_stock_data(data):
                                valid_stocks[stock_code] = {
                                    'name': data.get('stock_name', ''),
                                    'market': self._determine_market(stock_code),
                                    'current_price': data.get('current_price', 0),
                                    'volume': data.get('volume', 0),
                                    'market_cap': data.get('total_market_cap', 0)
                                }
                    
                    # 进度报告
                    if batch_num % 20 == 0:
                        logger.info(f"   扫描进度: {batch_num}/{total_batches} "
                                   f"({batch_num/total_batches*100:.1f}%) "
                                   f"发现有效股票: {len(valid_stocks)} 只")
                    
                    # 添加延迟避免请求过快
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.debug(f"批次 {batch_num} 失败: {e}")
                    continue
        
        logger.info(f"✅ 扫描完成，发现有效股票: {len(valid_stocks)} 只")
        return valid_stocks
    
    def _is_valid_stock_data(self, data: Dict[str, Any]) -> bool:
        """验证股票数据是否有效"""
        if not data:
            return False
        
        # 检查基本要素
        price = data.get('current_price', 0)
        name = data.get('stock_name', '')
        
        # 有效条件：有价格且不为0，有股票名称
        return (price > 0 and 
                name and 
                name.strip() != '' and
                not name.startswith('股票'))  # 过滤掉默认名称
    
    def _determine_market(self, stock_code: str) -> str:
        """根据股票代码确定市场"""
        if stock_code.startswith(('60', '68')):
            return 'SH'  # 上海
        elif stock_code.startswith(('00', '30', '20')):
            return 'SZ'  # 深圳
        elif stock_code.startswith(('43', '83')):
            return 'BJ'  # 北京
        else:
            return 'OTHER'
    
    def _get_total_scan_count(self) -> int:
        """获取总扫描数量"""
        # 计算所有扫描范围的总数
        ranges = [
            999,   # 000xxx
            999,   # 002xxx
            999,   # 300xxx
            1000,  # 600xxx
            1000,  # 601xxx
            1000,  # 603xxx
            999,   # 688xxx
            999,   # 430xxx
            999    # 830xxx
        ]
        return sum(ranges)
    
    def _analyze_differences(self, existing: Dict[str, Dict], valid: Dict[str, Dict]) -> Dict[str, List]:
        """分析现有股票和有效股票的差异"""
        existing_codes = set(existing.keys())
        valid_codes = set(valid.keys())
        
        # 新股票：在有效股票中但不在现有股票中
        new_codes = valid_codes - existing_codes
        new_stocks = [
            {
                'symbol': code,
                'name': valid[code]['name'],
                'market': valid[code]['market']
            }
            for code in new_codes
        ]
        
        # 需要更新的股票：名称或状态发生变化
        updated_stocks = []
        for code in existing_codes & valid_codes:
            if existing[code]['name'] != valid[code]['name']:
                updated_stocks.append({
                    'symbol': code,
                    'old_name': existing[code]['name'],
                    'new_name': valid[code]['name'],
                    'market': valid[code]['market']
                })
        
        # 需要移除的股票：在现有股票中但不在有效股票中
        removed_codes = existing_codes - valid_codes
        removed_stocks = [
            {
                'symbol': code,
                'name': existing[code]['name'],
                'market': existing[code]['market']
            }
            for code in removed_codes if existing[code]['is_active']
        ]
        
        return {
            'new_stocks': new_stocks,
            'updated_stocks': updated_stocks,
            'removed_stocks': removed_stocks
        }
    
    async def _add_new_stocks(self, new_stocks: List[Dict[str, Any]]) -> int:
        """添加新股票"""
        if not new_stocks:
            return 0
        
        added_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock in new_stocks:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO stock_info 
                            (symbol, name, market, is_active, created_at, updated_at)
                            VALUES (?, ?, ?, 1, ?, ?)
                        ''', (
                            stock['symbol'],
                            stock['name'],
                            stock['market'],
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        
                        if cursor.rowcount > 0:
                            added_count += 1
                            logger.debug(f"   ✅ 新增: {stock['symbol']} {stock['name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 添加股票 {stock['symbol']} 失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量添加新股票失败: {e}")
        
        return added_count
    
    async def _update_existing_stocks(self, updated_stocks: List[Dict[str, Any]]) -> int:
        """更新现有股票"""
        if not updated_stocks:
            return 0
        
        updated_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock in updated_stocks:
                    try:
                        cursor.execute('''
                            UPDATE stock_info 
                            SET name = ?, updated_at = ?
                            WHERE symbol = ?
                        ''', (
                            stock['new_name'],
                            datetime.now().isoformat(),
                            stock['symbol']
                        ))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                            logger.info(f"   🔄 更新: {stock['symbol']} "
                                       f"{stock['old_name']} → {stock['new_name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 更新股票 {stock['symbol']} 失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量更新股票失败: {e}")
        
        return updated_count
    
    async def _remove_inactive_stocks(self, removed_stocks: List[Dict[str, Any]]) -> int:
        """标记不活跃股票"""
        if not removed_stocks:
            return 0
        
        removed_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock in removed_stocks:
                    try:
                        cursor.execute('''
                            UPDATE stock_info 
                            SET is_active = 0, updated_at = ?
                            WHERE symbol = ?
                        ''', (
                            datetime.now().isoformat(),
                            stock['symbol']
                        ))
                        
                        if cursor.rowcount > 0:
                            removed_count += 1
                            logger.info(f"   ❌ 标记不活跃: {stock['symbol']} {stock['name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 标记股票 {stock['symbol']} 不活跃失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量标记不活跃股票失败: {e}")
        
        return removed_count
    
    async def get_update_summary(self) -> Dict[str, Any]:
        """获取更新摘要"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 总股票数和活跃股票数 (包括A股6位和港股5位)
                cursor.execute('SELECT COUNT(*), SUM(is_active) FROM stock_info WHERE LENGTH(symbol) IN (5, 6)')
                total, active = cursor.fetchone()
                
                # 最近更新时间
                cursor.execute('SELECT MAX(updated_at) FROM stock_info WHERE LENGTH(symbol) IN (5, 6)')
                last_updated = cursor.fetchone()[0]
                
                # 市场分布
                cursor.execute('''
                    SELECT market, COUNT(*) 
                    FROM stock_info 
                    WHERE LENGTH(symbol) IN (5, 6) AND is_active = 1 
                    GROUP BY market
                ''')
                market_dist = dict(cursor.fetchall())
                
                return {
                    'total_stocks': total or 0,
                    'active_stocks': int(active or 0),
                    'inactive_stocks': (total or 0) - int(active or 0),
                    'last_updated': last_updated,
                    'market_distribution': market_dist
                }
                
        except Exception as e:
            logger.error(f"❌ 获取更新摘要失败: {e}")
            return {}

# 全局实例
stock_info_updater = None

def get_stock_info_updater(db_manager: DatabaseManager) -> StockInfoUpdater:
    """获取股票信息更新器实例"""
    global stock_info_updater
    
    # 暂时每次都创建新实例，确保SQL更改生效
    stock_info_updater = StockInfoUpdater(db_manager)
    
    return stock_info_updater