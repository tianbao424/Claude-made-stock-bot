#!/usr/bin/env python3
"""
修复 stock_pool.db 中的技术指标表结构
添加缺失的 is_bearish_aligned 列
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_stock_pool_technical_indicators():
    """修复 stock_pool.db 的技术指标表结构"""
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        logger.info("检查 stock_technical_indicators 表结构...")
        cursor.execute("PRAGMA table_info(stock_technical_indicators)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"当前列: {column_names}")
        
        # 添加缺失的列
        missing_columns = []
        
        # 检查 is_bearish_aligned
        if 'is_bearish_aligned' not in column_names:
            missing_columns.append(('is_bearish_aligned', 'BOOLEAN DEFAULT 0'))
        
        # 检查其他可能缺失的列
        expected_columns = {
            'ma30': 'REAL',
            'ma120': 'REAL',
            'ma250': 'REAL',
            'macd_histogram': 'REAL',
            'boll_upper': 'REAL',
            'boll_middle': 'REAL',
            'boll_lower': 'REAL',
            'is_golden_cross': 'BOOLEAN DEFAULT 0',
            'is_death_cross': 'BOOLEAN DEFAULT 0',
            'is_volume_breakout': 'BOOLEAN DEFAULT 0',
            'is_price_breakout': 'BOOLEAN DEFAULT 0',
            'volume_ma5': 'REAL',
            'volume_ma10': 'REAL',
            'volume_ma20': 'REAL'
        }
        
        for col_name, col_type in expected_columns.items():
            if col_name not in column_names:
                missing_columns.append((col_name, col_type))
        
        # 添加所有缺失的列
        for col_name, col_type in missing_columns:
            logger.info(f"添加列 {col_name} ({col_type})...")
            try:
                cursor.execute(f'ALTER TABLE stock_technical_indicators ADD COLUMN {col_name} {col_type}')
                logger.info(f"✅ 成功添加列 {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.info(f"列 {col_name} 已存在")
                else:
                    logger.error(f"❌ 添加列 {col_name} 失败: {e}")
        
        # 重命名可能存在差异的列
        # stock_code vs symbol
        if 'stock_code' in column_names and 'symbol' not in column_names:
            logger.info("stock_code 列已存在，无需重命名")
        elif 'symbol' in column_names and 'stock_code' not in column_names:
            logger.info("注意：表使用 symbol 而非 stock_code")
            # 不做修改，让代码适配这个差异
        
        conn.commit()
        
        # 再次检查表结构
        cursor.execute("PRAGMA table_info(stock_technical_indicators)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"更新后的列: {column_names}")
        
        logger.info("✅ stock_pool.db 修复完成！")
        
    except Exception as e:
        logger.error(f"❌ 修复失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_stock_pool_technical_indicators()