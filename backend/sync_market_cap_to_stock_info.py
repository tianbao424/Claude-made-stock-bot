#!/usr/bin/env python3
"""
同步最新市值数据到 stock_info 表
"""
import sqlite3
import sys

# 添加项目根目录到路径
sys.path.append('/Users/quxiaomeng/工作/code/Claude made stock bot/backend')

from database import DatabaseManager

def sync_market_cap_to_stock_info():
    """同步最新市值数据到 stock_info 表"""
    print("🔄 同步最新市值数据到 stock_info 表")
    print("=" * 50)
    
    db_manager = DatabaseManager()
    
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # 获取最新的市值数据并更新到 stock_info
        cursor.execute('''
            UPDATE stock_info 
            SET market_cap = (
                SELECT total_market_cap / 10000  -- 转换为亿元
                FROM daily_stock_changes 
                WHERE daily_stock_changes.stock_code = stock_info.symbol 
                  AND daily_stock_changes.total_market_cap > 0
                  AND daily_stock_changes.trade_date = (
                      SELECT MAX(trade_date) 
                      FROM daily_stock_changes d2 
                      WHERE d2.stock_code = stock_info.symbol 
                        AND d2.total_market_cap > 0
                  )
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1 FROM daily_stock_changes 
                WHERE daily_stock_changes.stock_code = stock_info.symbol 
                  AND daily_stock_changes.total_market_cap > 0
            )
        ''')
        
        affected_rows = cursor.rowcount
        print(f"✅ 已更新 {affected_rows} 只股票的市值数据")
        
        # 验证更新结果
        cursor.execute('''
            SELECT symbol, name, market_cap 
            FROM stock_info 
            WHERE symbol IN ('301150', '300300', '301662', '301228')
            ORDER BY market_cap DESC
        ''')
        
        results = cursor.fetchall()
        print("\n📊 验证更新结果:")
        for symbol, name, market_cap in results:
            print(f"  {symbol} ({name}): {market_cap:.1f}亿元")
        
        conn.commit()
        
    print("\n🎉 市值数据同步完成")

if __name__ == "__main__":
    sync_market_cap_to_stock_info()