import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import os

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class StockPool:
    stock_code: str
    stock_name: str
    pool_type: str  # "holding" | "potential"
    shares: int = 0
    avg_cost: float = 0.0
    notes: str = ""
    tags: Optional[List[str]] = None
    created_at: str = ""
    updated_at: str = ""
    id: Optional[int] = None

@dataclass
class StockInfo:
    symbol: str
    name: str
    short_name: str = ""
    market: str = ""  # SH/SZ/HK
    industry: str = ""
    pinyin: str = ""
    sector: str = ""
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    dividend_yield: float = 0.0
    listing_date: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    id: Optional[int] = None

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 统一使用backend目录下的数据库文件
            self.db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
        else:
            self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库和表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建股票池表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    pool_type TEXT NOT NULL CHECK(pool_type IN ('holding', 'potential')),
                    shares INTEGER DEFAULT 0,
                    avg_cost REAL DEFAULT 0.0,
                    notes TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(stock_code, pool_type)
                )
            ''')
            
            # 创建股票基础信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    short_name TEXT DEFAULT '',
                    market TEXT DEFAULT '',
                    industry TEXT DEFAULT '',
                    pinyin TEXT DEFAULT '',
                    sector TEXT DEFAULT '',
                    market_cap REAL DEFAULT 0.0,
                    pe_ratio REAL DEFAULT 0.0,
                    pb_ratio REAL DEFAULT 0.0,
                    dividend_yield REAL DEFAULT 0.0,
                    listing_date TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 创建搜索索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_info(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_pinyin ON stock_info(pinyin)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_market ON stock_info(market)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_info(symbol)')
            
            conn.commit()
            logger.info("✅ Database initialized successfully")
    
    def add_stock(self, stock: StockPool) -> Optional[int]:
        """添加股票到池中"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                stock.created_at = now
                stock.updated_at = now
                
                # 序列化标签为JSON字符串
                tags_json = json.dumps(stock.tags) if stock.tags else ""
                
                cursor.execute('''
                    INSERT INTO stock_pool 
                    (stock_code, stock_name, pool_type, shares, avg_cost, notes, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock.stock_code, stock.stock_name, stock.pool_type,
                    stock.shares, stock.avg_cost, stock.notes, tags_json,
                    stock.created_at, stock.updated_at
                ))
                
                stock_id = cursor.lastrowid
                conn.commit()
                return stock_id
                
        except sqlite3.IntegrityError:
            raise ValueError(f"股票 {stock.stock_code} 已存在于 {stock.pool_type} 池中")
        except Exception as e:
            raise Exception(f"添加股票失败: {str(e)}")
    
    def get_stocks(self, pool_type: Optional[str] = None) -> List[StockPool]:
        """获取股票池列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if pool_type:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, pool_type, shares, avg_cost, 
                               notes, tags, created_at, updated_at
                        FROM stock_pool 
                        WHERE pool_type = ?
                        ORDER BY updated_at DESC
                    ''', (pool_type,))
                else:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, pool_type, shares, avg_cost,
                               notes, tags, created_at, updated_at
                        FROM stock_pool 
                        ORDER BY pool_type, updated_at DESC
                    ''')
                
                rows = cursor.fetchall()
                
                stocks = []
                for row in rows:
                    # 反序列化标签
                    tags = json.loads(row[7]) if row[7] else None
                    
                    stock = StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        notes=row[6],
                        tags=tags,
                        created_at=row[8],
                        updated_at=row[9]
                    )
                    stocks.append(stock)
                
                return stocks
                
        except Exception as e:
            raise Exception(f"获取股票列表失败: {str(e)}")
    
    def update_stock(self, stock_id: int, updates: Dict) -> bool:
        """更新股票信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建更新SQL
                update_fields = []
                values = []
                
                allowed_fields = ['stock_name', 'shares', 'avg_cost', 'notes', 'pool_type', 'tags']
                for field, value in updates.items():
                    if field in allowed_fields:
                        if field == 'tags':
                            # 序列化标签
                            value = json.dumps(value) if value else ""
                        update_fields.append(f"{field} = ?")
                        values.append(value)
                
                if not update_fields:
                    return False
                
                # 添加更新时间
                update_fields.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(stock_id)
                
                sql = f"UPDATE stock_pool SET {', '.join(update_fields)} WHERE id = ?"
                
                cursor.execute(sql, values)
                affected_rows = cursor.rowcount
                conn.commit()
                
                return affected_rows > 0
                
        except Exception as e:
            raise Exception(f"更新股票信息失败: {str(e)}")
    
    def delete_stock(self, stock_id: int) -> bool:
        """删除股票"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM stock_pool WHERE id = ?", (stock_id,))
                affected_rows = cursor.rowcount
                conn.commit()
                
                return affected_rows > 0
                
        except Exception as e:
            raise Exception(f"删除股票失败: {str(e)}")
    
    def get_stock_by_id(self, stock_id: int) -> Optional[StockPool]:
        """根据ID获取股票"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, stock_code, stock_name, pool_type, shares, avg_cost,
                           notes, tags, created_at, updated_at
                    FROM stock_pool 
                    WHERE id = ?
                ''', (stock_id,))
                
                row = cursor.fetchone()
                if row:
                    # 反序列化标签
                    tags = json.loads(row[7]) if row[7] else None
                    
                    return StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        notes=row[6],
                        tags=tags,
                        created_at=row[8],
                        updated_at=row[9]
                    )
                return None
                
        except Exception as e:
            raise Exception(f"获取股票信息失败: {str(e)}")
    
    def check_stock_exists(self, stock_code: str, pool_type: str) -> bool:
        """检查股票是否已存在于指定池中"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM stock_pool 
                    WHERE stock_code = ? AND pool_type = ?
                ''', (stock_code, pool_type))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            return False
    
    def get_pool_summary(self) -> Dict:
        """获取股票池概览信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取各池的股票数量
                cursor.execute('''
                    SELECT pool_type, COUNT(*) 
                    FROM stock_pool 
                    GROUP BY pool_type
                ''')
                
                summary = {"holding": 0, "potential": 0}
                for pool_type, count in cursor.fetchall():
                    summary[pool_type] = count
                
                return summary
                
        except Exception as e:
            return {"holding": 0, "potential": 0}
    
    # ===== 股票信息管理方法 =====
    
    def add_stock_info(self, stock_info: StockInfo) -> Optional[int]:
        """添加股票基础信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                stock_info.created_at = now
                stock_info.updated_at = now
                
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_info 
                    (symbol, name, short_name, market, industry, pinyin, sector, 
                     market_cap, pe_ratio, pb_ratio, dividend_yield, listing_date, 
                     is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock_info.symbol, stock_info.name, stock_info.short_name,
                    stock_info.market, stock_info.industry, stock_info.pinyin,
                    stock_info.sector, stock_info.market_cap, stock_info.pe_ratio,
                    stock_info.pb_ratio, stock_info.dividend_yield, stock_info.listing_date,
                    1 if stock_info.is_active else 0, stock_info.created_at, stock_info.updated_at
                ))
                
                stock_id = cursor.lastrowid
                conn.commit()
                return stock_id
                
        except Exception as e:
            raise Exception(f"添加股票信息失败: {str(e)}")
    
    def search_stocks(self, query: str, limit: int = 20) -> List[StockInfo]:
        """智能搜索股票"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建搜索条件
                search_term = f"%{query}%"
                
                cursor.execute('''
                    SELECT id, symbol, name, short_name, market, industry, pinyin, sector,
                           market_cap, pe_ratio, pb_ratio, dividend_yield, listing_date,
                           is_active, created_at, updated_at
                    FROM stock_info 
                    WHERE (symbol LIKE ? 
                       OR name LIKE ? 
                       OR short_name LIKE ?
                       OR pinyin LIKE ?)
                       AND is_active = 1
                    ORDER BY 
                        CASE 
                            WHEN symbol = ? THEN 1
                            WHEN symbol LIKE ? THEN 2
                            WHEN name LIKE ? THEN 3
                            ELSE 4
                        END,
                        LENGTH(name)
                    LIMIT ?
                ''', (search_term, search_term, search_term, search_term, 
                      query, f"{query}%", f"{query}%", limit))
                
                rows = cursor.fetchall()
                
                stocks = []
                for row in rows:
                    stock_info = StockInfo(
                        id=row[0],
                        symbol=row[1],
                        name=row[2],
                        short_name=row[3],
                        market=row[4],
                        industry=row[5],
                        pinyin=row[6],
                        sector=row[7],
                        market_cap=row[8],
                        pe_ratio=row[9],
                        pb_ratio=row[10],
                        dividend_yield=row[11],
                        listing_date=row[12],
                        is_active=bool(row[13]),
                        created_at=row[14],
                        updated_at=row[15]
                    )
                    stocks.append(stock_info)
                
                return stocks
                
        except Exception as e:
            raise Exception(f"搜索股票失败: {str(e)}")
    
    def get_stock_info_count(self) -> int:
        """获取股票信息总数"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM stock_info")
                return cursor.fetchone()[0]
        except Exception as e:
            return 0
    
    def get_stock_info_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """根据代码获取股票信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, symbol, name, short_name, market, industry, pinyin, sector,
                           market_cap, pe_ratio, pb_ratio, dividend_yield, listing_date,
                           is_active, created_at, updated_at
                    FROM stock_info 
                    WHERE symbol = ?
                ''', (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return StockInfo(
                        id=row[0],
                        symbol=row[1],
                        name=row[2],
                        short_name=row[3],
                        market=row[4],
                        industry=row[5],
                        pinyin=row[6],
                        sector=row[7],
                        market_cap=row[8],
                        pe_ratio=row[9],
                        pb_ratio=row[10],
                        dividend_yield=row[11],
                        listing_date=row[12],
                        is_active=bool(row[13]),
                        created_at=row[14],
                        updated_at=row[15]
                    )
                return None
                
        except Exception as e:
            return None

# 全局数据库实例
db_manager = DatabaseManager()