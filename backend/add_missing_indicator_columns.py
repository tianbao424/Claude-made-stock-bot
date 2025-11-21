#!/usr/bin/env python3
"""
添加技术指标服务中使用但数据库表中缺失的字段
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_indicator_columns():
    """添加缺失的技术指标字段到 stock_pool.db"""
    db_path = os.path.join(os.path.dirname(__file__), "stock_pool.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查当前表结构
        logger.info("检查当前 stock_technical_indicators 表结构...")
        cursor.execute("PRAGMA table_info(stock_technical_indicators)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"当前列数: {len(column_names)}")
        
        # 需要添加的字段列表（从技术指标服务代码中提取）
        missing_columns = {
            # 均线比率和信号
            'ma5_ma10_ratio': 'REAL',
            'golden_cross_signal': 'BOOLEAN DEFAULT 0',
            'death_cross_signal': 'BOOLEAN DEFAULT 0',
            
            # 价格与均线关系
            'price_above_ma20': 'BOOLEAN DEFAULT 0',
            'price_above_ma30': 'BOOLEAN DEFAULT 0',
            'ma20_slope': 'TEXT DEFAULT "neutral"',
            'ma30_slope': 'TEXT DEFAULT "neutral"',
            
            # 量比指标
            'volume_ratio_5d': 'REAL',
            'volume_ratio_10d': 'REAL',
            'volume_ratio_20d': 'REAL',
            'volume_level': 'TEXT DEFAULT "normal"',
            
            # 布林带指标
            'boll_position': 'REAL',
            'boll_width': 'REAL',
            
            # RSI 相关
            'rsi_signal': 'TEXT DEFAULT "neutral"',
            'rsi_oversold': 'BOOLEAN DEFAULT 0',
            'rsi_overbought': 'BOOLEAN DEFAULT 0',
            
            # MACD 信号
            'macd_signal': 'TEXT DEFAULT "neutral"',
            'macd_bullish': 'BOOLEAN DEFAULT 0',
            'macd_bearish': 'BOOLEAN DEFAULT 0',
            
            # 量价关系
            'volume_price_sync': 'BOOLEAN DEFAULT 0',
            'volume_divergence': 'BOOLEAN DEFAULT 0',
            'price_volume_trend': 'TEXT DEFAULT "neutral"'
        }
        
        # 添加缺失的列
        added_count = 0
        for col_name, col_type in missing_columns.items():
            if col_name not in column_names:
                try:
                    logger.info(f"添加列 {col_name} ({col_type})...")
                    cursor.execute(f'ALTER TABLE stock_technical_indicators ADD COLUMN {col_name} {col_type}')
                    added_count += 1
                    logger.info(f"✅ 成功添加列 {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        logger.info(f"列 {col_name} 已存在")
                    else:
                        logger.error(f"❌ 添加列 {col_name} 失败: {e}")
            else:
                logger.info(f"列 {col_name} 已存在")
        
        conn.commit()
        
        # 检查最终表结构
        cursor.execute("PRAGMA table_info(stock_technical_indicators)")
        columns = cursor.fetchall()
        final_column_names = [col[1] for col in columns]
        logger.info(f"最终列数: {len(final_column_names)}")
        logger.info(f"新增列数: {added_count}")
        
        # 显示所有列名（分组显示）
        logger.info("所有列名:")
        for i, col_name in enumerate(final_column_names):
            if i % 5 == 0:
                logger.info(f"  {', '.join(final_column_names[i:i+5])}")
        
        logger.info("✅ 所有缺失字段添加完成！")
        
    except Exception as e:
        logger.error(f"❌ 添加字段失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_missing_indicator_columns()