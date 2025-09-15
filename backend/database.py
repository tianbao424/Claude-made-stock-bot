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
    current_price: float = 0.0
    market_value: float = 0.0
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

@dataclass  
class StrategyAnalysisData:
    """策略分析输入数据"""
    # 股票基本信息
    stock_code: str
    stock_name: str
    industry: str = ""
    
    # 持仓信息
    shares: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss_pct: float = 0.0
    profit_loss_amount: float = 0.0
    
    # 技术分析数据
    price_trend_30d: List[float] = None
    rsi: float = 50.0
    macd_signal: str = ""
    support_level: float = 0.0
    resistance_level: float = 0.0
    volume_status: str = ""
    
    # 基本面数据
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    roe: float = 0.0
    financial_health: str = ""
    recent_performance: str = ""
    industry_position: str = ""
    
    # 市场环境
    market_trend: str = ""
    sector_performance: str = ""
    market_sentiment: str = ""

@dataclass
class GeneratedStrategy:
    """AI生成的投资策略"""
    comprehensive_score: float
    risk_level: str  # low/medium/high
    action_recommendation: str  # buy/hold/reduce/sell
    target_price_min: float
    target_price_max: float
    timeframe: str  # short/medium/long
    position_suggestion: float  # 0-1
    analysis_summary: str
    key_metrics: List[str]
    risk_warnings: List[str]
    action_plan: List[str]
    confidence_level: float
    
    # 额外分析内容
    technical_analysis: str = ""
    fundamental_analysis: str = ""
    market_context: str = ""

@dataclass
class StrategyAnalysis:
    """策略分析记录"""
    id: Optional[int] = None
    stock_pool_id: int = 0
    stock_code: str = ""
    
    # 分析时的持仓数据
    shares_at_analysis: int = 0
    cost_at_analysis: float = 0.0
    price_at_analysis: float = 0.0
    market_value_at_analysis: float = 0.0
    profit_loss_pct: float = 0.0
    
    # AI策略结果
    comprehensive_score: float = 0.0
    risk_level: str = ""
    action_recommendation: str = ""
    target_price_min: float = 0.0
    target_price_max: float = 0.0
    timeframe: str = ""
    position_suggestion: float = 0.0
    
    # 分析内容
    analysis_summary: str = ""
    key_metrics: Optional[List[str]] = None
    risk_warnings: Optional[List[str]] = None
    action_plan: Optional[List[str]] = None
    technical_analysis: str = ""
    fundamental_analysis: str = ""
    market_context: str = ""
    
    # 元数据
    analysis_date: str = ""
    model_version: str = "qwen-coder-plus"
    confidence_level: float = 0.0
    created_at: str = ""

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
                    stock_code TEXT NOT NULL UNIQUE,
                    stock_name TEXT NOT NULL,
                    pool_type TEXT NOT NULL CHECK(pool_type IN ('holding', 'potential')),
                    shares INTEGER DEFAULT 0,
                    avg_cost REAL DEFAULT 0.0,
                    current_price REAL DEFAULT 0.0,
                    market_value REAL DEFAULT 0.0,
                    notes TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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
            
            # 创建策略分析表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_pool_id INTEGER NOT NULL,
                    stock_code TEXT NOT NULL,
                    
                    -- 分析时的持仓数据
                    shares_at_analysis INTEGER,
                    cost_at_analysis REAL,
                    price_at_analysis REAL,
                    market_value_at_analysis REAL,
                    profit_loss_pct REAL,
                    
                    -- AI策略结果
                    comprehensive_score REAL,
                    risk_level TEXT,
                    action_recommendation TEXT,
                    target_price_min REAL,
                    target_price_max REAL,
                    timeframe TEXT,
                    position_suggestion REAL,
                    
                    -- 分析内容 (JSON格式存储)
                    analysis_summary TEXT,
                    key_metrics TEXT,
                    risk_warnings TEXT,  
                    action_plan TEXT,
                    technical_analysis TEXT,
                    fundamental_analysis TEXT,
                    market_context TEXT,
                    
                    -- 元数据
                    analysis_date TEXT NOT NULL,
                    model_version TEXT DEFAULT 'qwen-coder-plus',
                    confidence_level REAL,
                    
                    created_at TEXT NOT NULL,
                    
                    FOREIGN KEY (stock_pool_id) REFERENCES stock_pool(id)
                )
            ''')
            
            # 创建搜索索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_info(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_pinyin ON stock_info(pinyin)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_market ON stock_info(market)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_info(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_stock_code ON strategy_analysis(stock_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_date ON strategy_analysis(analysis_date)')
            
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
                    (stock_code, stock_name, pool_type, shares, avg_cost, current_price, market_value, notes, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock.stock_code, stock.stock_name, stock.pool_type,
                    stock.shares, stock.avg_cost, stock.current_price, stock.market_value, 
                    stock.notes, tags_json, stock.created_at, stock.updated_at
                ))
                
                stock_id = cursor.lastrowid
                conn.commit()
                return stock_id
                
        except sqlite3.IntegrityError:
            raise ValueError(f"股票 {stock.stock_code} 已存在于股票池中")
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
                               current_price, market_value, notes, tags, created_at, updated_at
                        FROM stock_pool 
                        WHERE pool_type = ?
                        ORDER BY updated_at DESC
                    ''', (pool_type,))
                else:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, pool_type, shares, avg_cost,
                               current_price, market_value, notes, tags, created_at, updated_at
                        FROM stock_pool 
                        ORDER BY pool_type, updated_at DESC
                    ''')
                
                rows = cursor.fetchall()
                
                stocks = []
                for row in rows:
                    # 反序列化标签
                    tags = json.loads(row[9]) if row[9] else None
                    
                    stock = StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        current_price=row[6],
                        market_value=row[7],
                        notes=row[8],
                        tags=tags,
                        created_at=row[10],
                        updated_at=row[11]
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
                
                allowed_fields = ['stock_name', 'shares', 'avg_cost', 'current_price', 'market_value', 'notes', 'pool_type', 'tags']
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
                           current_price, market_value, notes, tags, created_at, updated_at
                    FROM stock_pool 
                    WHERE id = ?
                ''', (stock_id,))
                
                row = cursor.fetchone()
                if row:
                    # 反序列化标签
                    tags = json.loads(row[9]) if row[9] else None
                    
                    return StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        current_price=row[6],
                        market_value=row[7],
                        notes=row[8],
                        tags=tags,
                        created_at=row[10],
                        updated_at=row[11]
                    )
                return None
                
        except Exception as e:
            raise Exception(f"获取股票信息失败: {str(e)}")
    
    def check_stock_exists(self, stock_code: str) -> Optional[StockPool]:
        """检查股票是否已存在，返回现有股票信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, stock_code, stock_name, pool_type, shares, avg_cost,
                           current_price, market_value, notes, tags, created_at, updated_at
                    FROM stock_pool 
                    WHERE stock_code = ?
                ''', (stock_code,))
                
                row = cursor.fetchone()
                if row:
                    # 反序列化标签
                    tags = json.loads(row[9]) if row[9] else None
                    
                    return StockPool(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        pool_type=row[3],
                        shares=row[4],
                        avg_cost=row[5],
                        current_price=row[6],
                        market_value=row[7],
                        notes=row[8],
                        tags=tags,
                        created_at=row[10],
                        updated_at=row[11]
                    )
                return None
                
        except Exception as e:
            return None
    
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
    
    def get_all_stock_info(self) -> List[StockInfo]:
        """获取所有股票信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, symbol, name, short_name, market, industry, pinyin, sector,
                           market_cap, pe_ratio, pb_ratio, dividend_yield, listing_date,
                           is_active, created_at, updated_at
                    FROM stock_info 
                    WHERE is_active = 1
                    ORDER BY symbol
                ''')
                
                stocks = []
                for row in cursor.fetchall():
                    stocks.append(StockInfo(
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
                    ))
                
                return stocks
                
        except Exception as e:
            return []
    
    # ===== 策略分析管理方法 =====
    
    def save_strategy_analysis(self, strategy: GeneratedStrategy, pool_id: int, analysis_data: StrategyAnalysisData) -> Optional[int]:
        """保存策略分析结果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO strategy_analysis 
                    (stock_pool_id, stock_code, shares_at_analysis, cost_at_analysis, 
                     price_at_analysis, market_value_at_analysis, profit_loss_pct,
                     comprehensive_score, risk_level, action_recommendation,
                     target_price_min, target_price_max, timeframe, position_suggestion,
                     analysis_summary, key_metrics, risk_warnings, action_plan,
                     technical_analysis, fundamental_analysis, market_context,
                     analysis_date, model_version, confidence_level, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pool_id, analysis_data.stock_code, analysis_data.shares,
                    analysis_data.avg_cost, analysis_data.current_price, 
                    analysis_data.market_value, analysis_data.profit_loss_pct,
                    strategy.comprehensive_score, strategy.risk_level,
                    strategy.action_recommendation, strategy.target_price_min,
                    strategy.target_price_max, strategy.timeframe, strategy.position_suggestion,
                    strategy.analysis_summary, 
                    json.dumps(strategy.key_metrics),
                    json.dumps(strategy.risk_warnings),
                    json.dumps(strategy.action_plan),
                    strategy.technical_analysis, strategy.fundamental_analysis,
                    strategy.market_context, now, strategy.model_version,
                    strategy.confidence_level, now
                ))
                
                strategy_id = cursor.lastrowid
                conn.commit()
                return strategy_id
                
        except Exception as e:
            raise Exception(f"保存策略分析失败: {str(e)}")
    
    def get_strategy_analysis(self, strategy_id: int) -> Optional[StrategyAnalysis]:
        """获取策略分析记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM strategy_analysis WHERE id = ?
                ''', (strategy_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_strategy_analysis(row)
                return None
                
        except Exception as e:
            logger.error(f"获取策略分析失败: {e}")
            return None
    
    def get_strategies_by_pool(self, pool_id: int, limit: int = 10) -> List[StrategyAnalysis]:
        """获取股票池的策略分析历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM strategy_analysis 
                    WHERE stock_pool_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (pool_id, limit))
                
                rows = cursor.fetchall()
                return [self._row_to_strategy_analysis(row) for row in rows]
                
        except Exception as e:
            logger.error(f"获取策略历史失败: {e}")
            return []
    
    def _row_to_strategy_analysis(self, row) -> StrategyAnalysis:
        """将数据库行转换为StrategyAnalysis对象"""
        return StrategyAnalysis(
            id=row[0],
            stock_pool_id=row[1], 
            stock_code=row[2],
            shares_at_analysis=row[3],
            cost_at_analysis=row[4],
            price_at_analysis=row[5],
            market_value_at_analysis=row[6],
            profit_loss_pct=row[7],
            comprehensive_score=row[8],
            risk_level=row[9],
            action_recommendation=row[10],
            target_price_min=row[11],
            target_price_max=row[12],
            timeframe=row[13],
            position_suggestion=row[14],
            analysis_summary=row[15],
            key_metrics=json.loads(row[16]) if row[16] else [],
            risk_warnings=json.loads(row[17]) if row[17] else [],
            action_plan=json.loads(row[18]) if row[18] else [],
            technical_analysis=row[19] or "",
            fundamental_analysis=row[20] or "",
            market_context=row[21] or "",
            analysis_date=row[22],
            model_version=row[23],
            confidence_level=row[24],
            created_at=row[25]
        )

# 全局数据库实例
db_manager = DatabaseManager()