#!/usr/bin/env python3
"""
创建高级筛选结果表
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_advanced_screening_table():
    """创建高级筛选结果表"""
    db_path = os.path.join(os.path.dirname(__file__), "ai_stock_assistant.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建高级筛选结果表
        logger.info("创建高级筛选结果表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advanced_screening_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                screening_date TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                signal_strength TEXT NOT NULL,
                score REAL NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT,
                risk_level TEXT NOT NULL,
                current_price REAL,
                technical_data TEXT,  -- JSON格式
                strategies_passed TEXT,  -- JSON格式
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(stock_code, screening_date, strategy_type)
            )
        ''')
        
        # 创建索引
        logger.info("创建索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_adv_screening_date ON advanced_screening_results(screening_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_adv_screening_type ON advanced_screening_results(strategy_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_adv_screening_score ON advanced_screening_results(score DESC)')
        
        conn.commit()
        logger.info("✅ 高级筛选结果表创建成功！")
        
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_advanced_screening_table()