"""
高性能股票数据管理服务
实现分层架构和智能缓存策略
"""
import asyncio
import time
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import logging

logger = logging.getLogger(__name__)

@dataclass
class StockIndexItem:
    """股票索引项"""
    symbol: str
    name: str
    name_pinyin: str
    short_name: str
    market: str
    industry: str
    popularity_score: int = 0
    is_active: bool = True
    listing_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass 
class CacheItem:
    """缓存项"""
    data: Dict
    cached_at: float
    ttl: int
    source: str

class InMemoryCache:
    """内存缓存实现"""
    
    def __init__(self):
        self._cache: Dict[str, CacheItem] = {}
        self._stats = defaultdict(int)
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存项"""
        if key not in self._cache:
            self._stats['miss'] += 1
            return None
        
        item = self._cache[key]
        if time.time() - item.cached_at > item.ttl:
            del self._cache[key]
            self._stats['expired'] += 1
            return None
        
        self._stats['hit'] += 1
        return item.data
    
    def set(self, key: str, data: Dict, ttl: int, source: str = "unknown"):
        """设置缓存项"""
        self._cache[key] = CacheItem(
            data=data,
            cached_at=time.time(),
            ttl=ttl,
            source=source
        )
        self._stats['set'] += 1
    
    def delete(self, key: str):
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
            self._stats['delete'] += 1
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._stats.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_requests = self._stats['hit'] + self._stats['miss']
        hit_rate = (self._stats['hit'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_items': len(self._cache),
            'hit_rate': round(hit_rate, 2),
            'stats': dict(self._stats)
        }

class OptimizedDataService:
    """优化的数据服务"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.cache = InMemoryCache()
        self.hot_stocks_cache = InMemoryCache()  # 热门股票专用缓存
        self.search_cache = InMemoryCache()     # 搜索结果缓存
        
        # 热门股票列表 (基于市值、活跃度等)
        self.hot_stock_symbols = set([
            # 沪深300权重股
            '000001', '000002', '000858', '000876', '600000', '600036', 
            '600519', '600036', '600887', '601318', '601398', '601857',
            # 科技股
            '000063', '002415', '300059', '300750', 
            # 港股
            '00700', '09988', '03690', '01810', '09618'
        ])
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        
        # 创建优化的股票索引表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_index_optimized (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                name_pinyin TEXT,
                short_name TEXT,
                market TEXT NOT NULL,
                industry TEXT,
                popularity_score INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                listing_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建高性能索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_name_search ON stock_index_optimized(name, name_pinyin)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol_market ON stock_index_optimized(symbol, market)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_popularity ON stock_index_optimized(popularity_score DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_market_active ON stock_index_optimized(market, is_active)')
        
        conn.close()
        logger.info("✅ 优化数据库初始化完成")
    
    def generate_pinyin(self, text: str) -> str:
        """生成简化拼音 (实际项目中可使用pypinyin)"""
        # 简化映射，实际可以用pypinyin库
        pinyin_map = {
            '茅台': 'maotai', '平安': 'pingan', '银行': 'yinhang',
            '腾讯': 'tengxun', '阿里': 'ali', '招商': 'zhaoshang',
            '贵州': 'guizhou', '中国': 'zhongguo', '浦发': 'pufa'
        }
        
        result = text.lower()
        for chinese, pinyin in pinyin_map.items():
            result = result.replace(chinese, pinyin)
        
        return result
    
    async def bulk_import_stocks(self, stocks_data: List[Dict]) -> int:
        """批量导入股票数据"""
        if not stocks_data:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        imported_count = 0
        
        try:
            for stock_data in stocks_data:
                try:
                    # 生成拼音索引
                    pinyin = self.generate_pinyin(stock_data['name'])
                    
                    # 计算初始热度评分
                    popularity = 100 if stock_data['symbol'] in self.hot_stock_symbols else 0
                    
                    stock_item = StockIndexItem(
                        symbol=stock_data['symbol'],
                        name=stock_data['name'],
                        name_pinyin=pinyin,
                        short_name=stock_data.get('short_name', stock_data['name']),
                        market=stock_data['market'],
                        industry=stock_data.get('industry', '其他'),
                        popularity_score=popularity,
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    
                    # 使用REPLACE INTO避免重复插入
                    conn.execute('''
                        REPLACE INTO stock_index_optimized 
                        (symbol, name, name_pinyin, short_name, market, industry, 
                         popularity_score, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_item.symbol, stock_item.name, stock_item.name_pinyin,
                        stock_item.short_name, stock_item.market, stock_item.industry,
                        stock_item.popularity_score, stock_item.is_active,
                        stock_item.created_at, stock_item.updated_at
                    ))
                    
                    imported_count += 1
                    
                    # 每1000条提交一次
                    if imported_count % 1000 == 0:
                        conn.commit()
                        logger.info(f"📈 已导入 {imported_count} 只股票...")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 跳过股票 {stock_data.get('symbol', 'unknown')}: {e}")
            
            conn.commit()
            logger.info(f"🎉 批量导入完成! 成功导入 {imported_count} 只股票")
            
        finally:
            conn.close()
        
        # 导入完成后预热热门股票缓存
        await self._preheat_hot_stocks()
        
        return imported_count
    
    async def search_stocks(self, query: str, market: str = 'all', limit: int = 20) -> Tuple[List[Dict], int]:
        """高性能股票搜索"""
        if not query.strip():
            return [], 0
        
        # 生成缓存键
        cache_key = self._generate_search_cache_key(query, market, limit)
        
        # 检查搜索缓存
        cached_result = self.search_cache.get(cache_key)
        if cached_result:
            return cached_result['results'], cached_result['total']
        
        # 执行数据库查询
        start_time = time.time()
        results, total = await self._execute_search_query(query, market, limit)
        query_time = (time.time() - start_time) * 1000
        
        logger.info(f"🔍 搜索耗时: {query_time:.1f}ms, 结果数: {len(results)}")
        
        # 缓存搜索结果 (1分钟TTL)
        cache_data = {'results': results, 'total': total}
        self.search_cache.set(cache_key, cache_data, ttl=60, source="search")
        
        # 更新热度评分
        asyncio.create_task(self._update_search_popularity(query, results))
        
        return results, total
    
    def _generate_search_cache_key(self, query: str, market: str, limit: int) -> str:
        """生成搜索缓存键"""
        content = f"{query}:{market}:{limit}"
        return f"search:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _execute_search_query(self, query: str, market: str, limit: int) -> Tuple[List[Dict], int]:
        """执行搜索查询"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # 构建WHERE条件
            where_conditions = ["is_active = 1"]
            params = []
            
            # 市场筛选
            if market != 'all':
                where_conditions.append("market = ?")
                params.append(market.upper())
            
            # 搜索条件 (支持股票代码和名称)
            search_condition = "(symbol LIKE ? OR name LIKE ? OR name_pinyin LIKE ?)"
            where_conditions.append(search_condition)
            search_param = f"%{query}%"
            params.extend([search_param, search_param, search_param])
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM stock_index_optimized WHERE {where_clause}"
            cursor = conn.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 分页查询结果 (按热度排序)
            query_sql = f'''
                SELECT symbol, name, market, industry, popularity_score
                FROM stock_index_optimized 
                WHERE {where_clause}
                ORDER BY popularity_score DESC, symbol ASC
                LIMIT ?
            '''
            params.append(limit)
            
            cursor = conn.execute(query_sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            return results, total
            
        finally:
            conn.close()
    
    async def _update_search_popularity(self, query: str, results: List[Dict]):
        """更新搜索热度评分"""
        if not results:
            return
        
        conn = sqlite3.connect(self.db_path)
        try:
            # 为搜索到的股票增加热度
            symbols = [result['symbol'] for result in results[:5]]  # 只更新前5个结果
            placeholders = ','.join(['?' for _ in symbols])
            
            conn.execute(f'''
                UPDATE stock_index_optimized 
                SET popularity_score = popularity_score + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE symbol IN ({placeholders})
            ''', symbols)
            
            conn.commit()
            
        except Exception as e:
            logger.warning(f"更新热度评分失败: {e}")
        finally:
            conn.close()
    
    async def _preheat_hot_stocks(self):
        """预热热门股票缓存"""
        logger.info("🔥 开始预热热门股票缓存...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # 获取热门股票信息
            cursor = conn.execute('''
                SELECT symbol, name, market, industry, popularity_score
                FROM stock_index_optimized
                WHERE symbol IN ({}) AND is_active = 1
            '''.format(','.join(['?' for _ in self.hot_stock_symbols])), 
            list(self.hot_stock_symbols))
            
            hot_stocks = [dict(row) for row in cursor.fetchall()]
            
            # 缓存到内存 (30分钟TTL)
            for stock in hot_stocks:
                cache_key = f"hot_stock:{stock['symbol']}"
                self.hot_stocks_cache.set(cache_key, stock, ttl=1800, source="preheat")
            
            logger.info(f"✅ 预热完成，缓存了 {len(hot_stocks)} 只热门股票")
            
        finally:
            conn.close()
    
    def get_hot_stock(self, symbol: str) -> Optional[Dict]:
        """获取热门股票信息（从缓存）"""
        cache_key = f"hot_stock:{symbol}"
        return self.hot_stocks_cache.get(cache_key)
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'search_cache': self.search_cache.get_stats(),
            'hot_stocks_cache': self.hot_stocks_cache.get_stats(),
            'general_cache': self.cache.get_stats()
        }
    
    async def get_stats(self) -> Dict:
        """获取数据统计信息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # 总体统计
            cursor = conn.execute('SELECT COUNT(*) as total FROM stock_index_optimized WHERE is_active = 1')
            total_stocks = cursor.fetchone()['total']
            
            # 按市场统计
            cursor = conn.execute('''
                SELECT market, COUNT(*) as count 
                FROM stock_index_optimized 
                WHERE is_active = 1 
                GROUP BY market 
                ORDER BY count DESC
            ''')
            market_stats = [dict(row) for row in cursor.fetchall()]
            
            # 热门股票统计
            cursor = conn.execute('''
                SELECT COUNT(*) as hot_count
                FROM stock_index_optimized 
                WHERE popularity_score > 50 AND is_active = 1
            ''')
            hot_count = cursor.fetchone()['hot_count']
            
            return {
                'total_stocks': total_stocks,
                'hot_stocks_count': hot_count,
                'market_distribution': market_stats,
                'cache_stats': self.get_cache_stats(),
                'last_updated': datetime.now().isoformat()
            }
            
        finally:
            conn.close()

# 全局实例
optimized_data_service = None

def get_optimized_data_service(db_path: str = None) -> OptimizedDataService:
    """获取优化数据服务实例"""
    global optimized_data_service
    
    if optimized_data_service is None:
        if db_path is None:
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
        optimized_data_service = OptimizedDataService(db_path)
    
    return optimized_data_service

# 测试函数
async def test_performance():
    """性能测试"""
    print("🧪 优化数据服务性能测试")
    print("=" * 40)
    
    service = get_optimized_data_service()
    
    # 测试搜索性能
    test_queries = ["平安", "茅台", "银行", "腾讯", "000001"]
    
    for query in test_queries:
        start_time = time.time()
        results, total = await service.search_stocks(query, limit=10)
        end_time = time.time()
        
        print(f"🔍 搜索 '{query}': {len(results)}条结果, 用时{(end_time-start_time)*1000:.1f}ms")
        
        # 显示前3个结果
        for result in results[:3]:
            print(f"  • {result['symbol']} - {result['name']} ({result['market']})")
    
    # 显示缓存统计
    stats = service.get_cache_stats()
    print(f"\\n📊 缓存统计: {stats}")

if __name__ == "__main__":
    asyncio.run(test_performance())