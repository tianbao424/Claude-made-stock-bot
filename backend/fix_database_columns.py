#!/usr/bin/env python3
"""
修复数据库缺失的列
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_missing_columns():
    """添加缺失的数据库列"""
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(stock_technical_indicators)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            logger.info(f"当前列: {column_names}")
            
            # 检查并添加缺失的列
            columns_to_add = [
                ("is_bullish_aligned", "BOOLEAN DEFAULT 0"),
                ("trend_strength", "REAL DEFAULT 0"),
                ("trend_direction", "TEXT DEFAULT 'neutral'")
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in column_names:
                    try:
                        sql = f"ALTER TABLE stock_technical_indicators ADD COLUMN {col_name} {col_type}"
                        cursor.execute(sql)
                        logger.info(f"✅ 成功添加列: {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column" in str(e).lower():
                            logger.info(f"ℹ️ 列已存在: {col_name}")
                        else:
                            logger.error(f"❌ 添加列失败 {col_name}: {e}")
                else:
                    logger.info(f"ℹ️ 列已存在: {col_name}")
            
            # 提交更改
            conn.commit()
            
            # 验证更改
            cursor.execute("PRAGMA table_info(stock_technical_indicators)")
            new_columns = cursor.fetchall()
            new_column_names = [col[1] for col in new_columns]
            
            logger.info(f"更新后的列: {new_column_names}")
            
            return True
            
    except Exception as e:
        logger.error(f"修复数据库失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔧 开始修复数据库缺失的列...")
    
    if fix_missing_columns():
        logger.info("✅ 数据库修复完成！")
    else:
        logger.error("❌ 数据库修复失败！")