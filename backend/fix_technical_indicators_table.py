#!/usr/bin/env python3
"""
修复技术指标表结构
添加缺失的 is_bearish_aligned 列
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_technical_indicators_table():
    """修复技术指标表结构"""
    db_path = os.path.join(os.path.dirname(__file__), "ai_stock_assistant.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 首先创建技术指标表（如果不存在）
        logger.info("创建技术指标表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                
                -- 价格相关指标
                ma5 REAL,
                ma10 REAL,
                ma20 REAL,
                ma30 REAL,
                ma60 REAL,
                ma120 REAL,
                ma250 REAL,
                
                -- MACD指标
                macd_dif REAL,
                macd_dea REAL,
                macd_histogram REAL,
                
                -- RSI指标
                rsi6 REAL,
                rsi12 REAL,
                rsi24 REAL,
                
                -- BOLL指标
                boll_upper REAL,
                boll_middle REAL,
                boll_lower REAL,
                
                -- 成交量指标
                volume_ma5 REAL,
                volume_ma10 REAL,
                volume_ma20 REAL,
                volume_ratio REAL,
                
                -- 技术形态标记
                is_golden_cross BOOLEAN DEFAULT 0,
                is_death_cross BOOLEAN DEFAULT 0,
                is_volume_breakout BOOLEAN DEFAULT 0,
                is_price_breakout BOOLEAN DEFAULT 0,
                is_bullish_aligned BOOLEAN DEFAULT 0,
                is_bearish_aligned BOOLEAN DEFAULT 0,  -- 新增的列
                
                -- 元数据
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                UNIQUE(symbol, trade_date)
            )
        ''')
        logger.info("✅ 技术指标表创建成功")
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(stock_technical_indicators)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"当前列: {column_names}")
        
        # 如果列不存在，添加它
        if 'is_bearish_aligned' not in column_names:
            logger.info("添加 is_bearish_aligned 列...")
            cursor.execute('''
                ALTER TABLE stock_technical_indicators 
                ADD COLUMN is_bearish_aligned BOOLEAN DEFAULT 0
            ''')
            logger.info("✅ is_bearish_aligned 列添加成功")
        else:
            logger.info("✅ is_bearish_aligned 列已存在")
        
        # 创建索引
        logger.info("创建索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tech_symbol ON stock_technical_indicators(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tech_date ON stock_technical_indicators(trade_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tech_symbol_date ON stock_technical_indicators(symbol, trade_date)')
        
        conn.commit()
        logger.info("✅ 所有修复完成！")
        
    except Exception as e:
        logger.error(f"❌ 修复失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_technical_indicators_table()