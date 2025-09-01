import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import os

@dataclass
class StockPool:
    stock_code: str
    stock_name: str
    pool_type: str  # "holding" | "potential"
    shares: int = 0
    avg_cost: float = 0.0
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    id: Optional[int] = None

class DatabaseManager:
    def __init__(self, db_path: str = "stock_pool.db"):
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
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(stock_code, pool_type)
                )
            ''')
            
            conn.commit()
            print("✅ Database initialized successfully")
    
    def add_stock(self, stock: StockPool) -> Optional[int]:
        """添加股票到池中"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                stock.created_at = now
                stock.updated_at = now
                
                cursor.execute('''
                    INSERT INTO stock_pool 
                    (stock_code, stock_name, pool_type, shares, avg_cost, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock.stock_code, stock.stock_name, stock.pool_type,
                    stock.shares, stock.avg_cost, stock.notes,
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
                               notes, created_at, updated_at
                        FROM stock_pool 
                        WHERE pool_type = ?
                        ORDER BY updated_at DESC
                    ''', (pool_type,))
                else:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, pool_type, shares, avg_cost,
                               notes, created_at, updated_at
                        FROM stock_pool 
                        ORDER BY pool_type, updated_at DESC
                    ''')
                
                rows = cursor.fetchall()
                
                stocks = []
                for row in rows:
                    stock = StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        notes=row[6],
                        created_at=row[7],
                        updated_at=row[8]
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
                
                allowed_fields = ['stock_name', 'shares', 'avg_cost', 'notes', 'pool_type']
                for field, value in updates.items():
                    if field in allowed_fields:
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
                           notes, created_at, updated_at
                    FROM stock_pool 
                    WHERE id = ?
                ''', (stock_id,))
                
                row = cursor.fetchone()
                if row:
                    return StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        notes=row[6],
                        created_at=row[7],
                        updated_at=row[8]
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

# 全局数据库实例
db_manager = DatabaseManager()