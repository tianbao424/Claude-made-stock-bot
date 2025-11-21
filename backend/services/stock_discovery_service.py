#!/usr/bin/env python3
"""
股票发现服务
负责发现新上市股票并更新stock_info表
"""
import asyncio
import logging
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from services.tencent_data_service import TencentDataService

logger = logging.getLogger(__name__)

class StockDiscoveryService:
    """股票发现服务"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.tencent_service = TencentDataService(db_manager)
        
    async def discover_and_update_stocks(self) -> Dict[str, Any]:
        """
        发现新上市股票并更新stock_info表
        
        Returns:
            Dict: 包含发现结果的字典
        """
        logger.info("🔍 开始股票发现和更新...")
        
        result = {
            'existing_count': 0,
            'discovered_count': 0,
            'new_stocks': [],
            'updated_stocks': [],
            'active_stocks': [],
            'inactive_stocks': []
        }
        
        try:
            # 1. 获取当前数据库中的股票
            existing_stocks = self._get_existing_stocks()
            result['existing_count'] = len(existing_stocks)
            logger.info(f"📊 数据库现有股票: {len(existing_stocks)} 只")
            
            # 2. 从腾讯API发现所有可交易股票
            discovered_stocks = await self._discover_stocks_from_tencent()
            result['discovered_count'] = len(discovered_stocks)
            logger.info(f"🔍 腾讯API发现股票: {len(discovered_stocks)} 只")
            
            # 3. 分析差异并更新
            analysis = self._analyze_stock_differences(existing_stocks, discovered_stocks)
            
            # 4. 添加新股票
            if analysis['new_stocks']:
                new_count = await self._add_new_stocks(analysis['new_stocks'])
                result['new_stocks'] = analysis['new_stocks'][:10]  # 只返回前10个用于显示
                logger.info(f"✅ 新增股票: {new_count} 只")
            
            # 5. 更新现有股票信息
            if analysis['updated_stocks']:
                updated_count = await self._update_existing_stocks(analysis['updated_stocks'])
                result['updated_stocks'] = analysis['updated_stocks'][:5]
                logger.info(f"🔄 更新股票: {updated_count} 只")
            
            # 6. 标记不活跃股票
            if analysis['inactive_stocks']:
                inactive_count = await self._mark_inactive_stocks(analysis['inactive_stocks'])
                result['inactive_stocks'] = analysis['inactive_stocks'][:5]
                logger.info(f"⏸️ 标记不活跃: {inactive_count} 只")
            
            # 7. 确认活跃股票
            if analysis['active_stocks']:
                active_count = await self._confirm_active_stocks(analysis['active_stocks'])
                result['active_stocks'] = len(analysis['active_stocks'])
                
            logger.info(f"✅ 股票发现完成: 新增{len(analysis['new_stocks'])}只, "
                       f"更新{len(analysis['updated_stocks'])}只, "
                       f"不活跃{len(analysis['inactive_stocks'])}只")
            
        except Exception as e:
            logger.error(f"❌ 股票发现失败: {e}")
            result['error'] = str(e)
            
        return result
    
    def _get_existing_stocks(self) -> Dict[str, Dict[str, Any]]:
        """获取数据库中现有的股票信息"""
        stocks = {}
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, name, market, is_active, updated_at
                    FROM stock_info
                    WHERE (symbol LIKE '6%' OR symbol LIKE '0%' OR symbol LIKE '3%') 
                        AND LENGTH(symbol) = 6
                ''')
                
                for row in cursor.fetchall():
                    symbol, name, market, is_active, updated_at = row
                    stocks[symbol] = {
                        'name': name,
                        'market': market,
                        'is_active': bool(is_active),
                        'updated_at': updated_at
                    }
                    
        except Exception as e:
            logger.error(f"❌ 获取现有股票失败: {e}")
            
        return stocks
    
    async def _discover_stocks_from_tencent(self) -> Dict[str, Dict[str, Any]]:
        """从腾讯API发现股票"""
        discovered_stocks = {}
        
        try:
            # 使用腾讯API获取所有A股的实时数据
            # 这里我们构建一个比较完整的A股代码范围进行测试
            test_ranges = []
            
            # 深交所: 000001-002999, 300001-300999
            for prefix in ['000', '002', '300']:
                for i in range(1, 1000 if prefix != '300' else 1000):
                    code = f"{prefix}{i:03d}"
                    test_ranges.append(code)
            
            # 上交所: 600000-603999, 605000-605999, 688001-688999
            for prefix in ['600', '601', '603', '605', '688']:
                start_num = 1 if prefix == '688' else 0
                end_num = 999 if prefix in ['605', '688'] else 1000
                for i in range(start_num, end_num):
                    code = f"{prefix}{i:03d}"
                    test_ranges.append(code)
            
            # 分批测试，每批100个
            batch_size = 100
            total_batches = (len(test_ranges) + batch_size - 1) // batch_size
            logger.info(f"📡 开始测试 {len(test_ranges)} 个股票代码，分 {total_batches} 批次")
            
            valid_count = 0
            async with self.tencent_service as service:
                for i in range(0, len(test_ranges), batch_size):
                    batch_codes = test_ranges[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    
                    try:
                        batch_data = await service.get_stock_data(batch_codes)
                        
                        if batch_data:
                            for stock_code, data in batch_data.items():
                                # 验证数据有效性
                                if (data.get('current_price', 0) > 0 and 
                                    data.get('stock_name') and 
                                    data.get('stock_name') != ''):
                                    
                                    discovered_stocks[stock_code] = {
                                        'name': data.get('stock_name', ''),
                                        'market': self._determine_market(stock_code),
                                        'current_price': data.get('current_price', 0),
                                        'volume': data.get('volume', 0),
                                        'market_cap': data.get('total_market_cap', 0)
                                    }
                                    valid_count += 1
                        
                        # 添加小延迟避免请求过快
                        if batch_num % 10 == 0:
                            logger.info(f"   完成第 {batch_num}/{total_batches} 批，发现有效股票 {valid_count} 只")
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.debug(f"批次 {batch_num} 失败: {e}")
                        continue
            
            logger.info(f"🎯 股票发现完成，共发现有效股票 {len(discovered_stocks)} 只")
            
        except Exception as e:
            logger.error(f"❌ 从腾讯API发现股票失败: {e}")
            
        return discovered_stocks
    
    def _determine_market(self, stock_code: str) -> str:
        """根据股票代码确定市场"""
        if stock_code.startswith('6'):
            return 'SH'  # 上海
        elif stock_code.startswith(('0', '2', '3')):
            return 'SZ'  # 深圳
        else:
            return 'OTHER'
    
    def _analyze_stock_differences(self, existing: Dict[str, Dict], discovered: Dict[str, Dict]) -> Dict[str, List]:
        """分析现有股票和发现股票的差异"""
        result = {
            'new_stocks': [],
            'updated_stocks': [],
            'active_stocks': [],
            'inactive_stocks': []
        }
        
        existing_codes = set(existing.keys())
        discovered_codes = set(discovered.keys())
        
        # 新股票：在发现中但不在现有中
        new_codes = discovered_codes - existing_codes
        for code in new_codes:
            result['new_stocks'].append({
                'symbol': code,
                'name': discovered[code]['name'],
                'market': discovered[code]['market'],
                'price': discovered[code]['current_price'],
                'market_cap': discovered[code]['market_cap']
            })
        
        # 需要更新的股票：名称发生变化
        for code in existing_codes & discovered_codes:
            existing_name = existing[code]['name']
            discovered_name = discovered[code]['name']
            
            if existing_name != discovered_name:
                result['updated_stocks'].append({
                    'symbol': code,
                    'old_name': existing_name,
                    'new_name': discovered_name,
                    'market': discovered[code]['market']
                })
            
            # 确认活跃股票
            if existing[code]['is_active']:
                result['active_stocks'].append(code)
        
        # 可能不活跃的股票：在现有中但不在发现中
        inactive_codes = existing_codes - discovered_codes
        for code in inactive_codes:
            if existing[code]['is_active']:  # 只标记原本活跃的
                result['inactive_stocks'].append({
                    'symbol': code,
                    'name': existing[code]['name'],
                    'market': existing[code]['market']
                })
        
        return result
    
    async def _add_new_stocks(self, new_stocks: List[Dict[str, Any]]) -> int:
        """添加新股票到数据库"""
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
                            logger.info(f"   ✅ 新增股票: {stock['symbol']} {stock['name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 添加股票 {stock['symbol']} 失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量添加新股票失败: {e}")
            
        return added_count
    
    async def _update_existing_stocks(self, updated_stocks: List[Dict[str, Any]]) -> int:
        """更新现有股票信息"""
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
                            logger.info(f"   🔄 更新股票: {stock['symbol']} "
                                       f"{stock['old_name']} → {stock['new_name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 更新股票 {stock['symbol']} 失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量更新股票失败: {e}")
            
        return updated_count
    
    async def _mark_inactive_stocks(self, inactive_stocks: List[Dict[str, Any]]) -> int:
        """标记不活跃股票"""
        if not inactive_stocks:
            return 0
            
        inactive_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock in inactive_stocks:
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
                            inactive_count += 1
                            logger.info(f"   ⏸️ 标记不活跃: {stock['symbol']} {stock['name']}")
                            
                    except Exception as e:
                        logger.error(f"❌ 标记股票 {stock['symbol']} 不活跃失败: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 批量标记不活跃股票失败: {e}")
            
        return inactive_count
    
    async def _confirm_active_stocks(self, active_stocks: List[str]) -> int:
        """确认活跃股票（确保is_active=1）"""
        if not active_stocks:
            return 0
            
        confirmed_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 批量更新活跃状态
                placeholders = ','.join(['?' for _ in active_stocks])
                cursor.execute(f'''
                    UPDATE stock_info 
                    SET is_active = 1, updated_at = ?
                    WHERE symbol IN ({placeholders}) AND is_active != 1
                ''', [datetime.now().isoformat()] + active_stocks)
                
                confirmed_count = cursor.rowcount
                conn.commit()
                
                if confirmed_count > 0:
                    logger.info(f"   ✅ 确认活跃股票: {confirmed_count} 只")
                    
        except Exception as e:
            logger.error(f"❌ 确认活跃股票失败: {e}")
            
        return confirmed_count
    
    async def get_stock_discovery_summary(self) -> Dict[str, Any]:
        """获取股票发现摘要"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 总股票数
                cursor.execute('SELECT COUNT(*) FROM stock_info WHERE LENGTH(symbol) = 6')
                total_stocks = cursor.fetchone()[0]
                
                # 活跃股票数
                cursor.execute('SELECT COUNT(*) FROM stock_info WHERE LENGTH(symbol) = 6 AND is_active = 1')
                active_stocks = cursor.fetchone()[0]
                
                # 最近更新时间
                cursor.execute('SELECT MAX(updated_at) FROM stock_info WHERE LENGTH(symbol) = 6')
                last_updated = cursor.fetchone()[0]
                
                # 市场分布
                cursor.execute('''
                    SELECT market, COUNT(*) 
                    FROM stock_info 
                    WHERE LENGTH(symbol) = 6 AND is_active = 1 
                    GROUP BY market
                ''')
                market_distribution = dict(cursor.fetchall())
                
                return {
                    'total_stocks': total_stocks,
                    'active_stocks': active_stocks,
                    'inactive_stocks': total_stocks - active_stocks,
                    'last_updated': last_updated,
                    'market_distribution': market_distribution
                }
                
        except Exception as e:
            logger.error(f"❌ 获取股票发现摘要失败: {e}")
            return {}

# 全局实例
stock_discovery_service: Optional[StockDiscoveryService] = None

def get_stock_discovery_service(db_manager: DatabaseManager) -> StockDiscoveryService:
    """获取股票发现服务实例"""
    global stock_discovery_service
    
    if stock_discovery_service is None:
        stock_discovery_service = StockDiscoveryService(db_manager)
    
    return stock_discovery_service