#!/usr/bin/env python3
"""
优化SQLite数据库性能，适配30天x5000股票的大数据量
"""
import sqlite3
import os

def optimize_sqlite_database():
    """优化SQLite数据库配置"""
    print("🔧 优化SQLite数据库性能...")
    
    db_path = "backend/stock_pool.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        print("📊 当前数据库配置:")
        
        # 查看当前配置
        current_settings = [
            "PRAGMA page_size",
            "PRAGMA cache_size", 
            "PRAGMA journal_mode",
            "PRAGMA synchronous",
            "PRAGMA temp_store"
        ]
        
        for setting in current_settings:
            cursor.execute(setting)
            result = cursor.fetchone()
            print(f"   {setting}: {result[0] if result else 'N/A'}")
        
        print("\n🚀 应用性能优化设置...")
        
        # 性能优化设置
        optimizations = [
            # 增加页面大小到4KB，提高大数据量处理效率
            "PRAGMA page_size = 4096",
            
            # 增加缓存大小到64MB，适合处理15万条记录
            "PRAGMA cache_size = -64000",  # 负数表示KB
            
            # WAL模式提高并发性能
            "PRAGMA journal_mode = WAL",
            
            # 异步写入，提高性能（数据安全性略降）
            "PRAGMA synchronous = NORMAL",
            
            # 内存临时存储
            "PRAGMA temp_store = MEMORY",
            
            # 启用内存映射，适合大文件
            "PRAGMA mmap_size = 268435456",  # 256MB
            
            # 优化查询规划器
            "PRAGMA optimize",
        ]
        
        for opt in optimizations:
            try:
                cursor.execute(opt)
                print(f"   ✅ {opt}")
            except Exception as e:
                print(f"   ❌ {opt} - {e}")
        
        # 检查关键索引
        print("\n🔍 检查数据库索引...")
        
        # daily_stock_changes表的索引
        indexes_to_check = [
            ("idx_daily_stock_code", "daily_stock_changes", "stock_code"),
            ("idx_daily_date", "daily_stock_changes", "change_date"),
            ("idx_daily_composite", "daily_stock_changes", "stock_code, change_date"),
        ]
        
        for idx_name, table_name, columns in indexes_to_check:
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='{idx_name}'
            """)
            
            if cursor.fetchone():
                print(f"   ✅ 索引存在: {idx_name}")
            else:
                print(f"   ⚠️ 创建索引: {idx_name}")
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON {table_name}({columns})
                    """)
                    print(f"      ✅ 索引创建成功")
                except Exception as e:
                    print(f"      ❌ 索引创建失败: {e}")
        
        # 分析表统计信息，优化查询计划
        cursor.execute("ANALYZE")
        
        conn.commit()
        
        print("\n📈 验证优化效果...")
        
        # 验证优化后的配置
        for setting in current_settings:
            cursor.execute(setting)
            result = cursor.fetchone()
            print(f"   {setting}: {result[0] if result else 'N/A'}")
        
        # 获取数据库大小信息
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        print(f"\n💾 数据库信息:")
        print(f"   文件大小: {db_size_mb:.2f} MB")
        print(f"   页面数量: {page_count:,}")
        print(f"   页面大小: {page_size:,} bytes")
        
        # 统计表记录数
        tables = ["daily_stock_changes", "stock_technical_indicators", "stock_pool"]
        print(f"\n📊 表记录统计:")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count:,} 条记录")
            except:
                print(f"   {table}: 表不存在")

def estimate_storage_requirements():
    """估算30天数据的存储需求"""
    print("\n📏 存储需求估算 (30天数据):")
    print("=" * 50)
    
    # 假设参数
    stocks_per_day = 5000
    trading_days = 22  # 30天约22个交易日
    total_records = stocks_per_day * trading_days
    
    # 每条记录估算大小
    record_size = 200  # bytes (包括索引开销)
    
    # 存储需求计算
    base_storage_mb = (total_records * record_size) / (1024 * 1024)
    index_overhead = base_storage_mb * 0.3  # 索引开销约30%
    total_storage_mb = base_storage_mb + index_overhead
    
    print(f"📊 数据规模:")
    print(f"   每日股票数: {stocks_per_day:,}")
    print(f"   交易日数: {trading_days}")
    print(f"   总记录数: {total_records:,}")
    
    print(f"\n💾 存储需求:")
    print(f"   基础数据: {base_storage_mb:.1f} MB")
    print(f"   索引开销: {index_overhead:.1f} MB")
    print(f"   总存储需求: {total_storage_mb:.1f} MB")
    
    # 性能预期
    print(f"\n⚡ 性能预期 (优化后):")
    print(f"   单股票查询: < 1ms")
    print(f"   技术指标计算: < 100ms/股票")
    print(f"   批量处理: ~50股票/秒")
    print(f"   全量计算时间: ~{total_records/50/60:.1f}分钟")

if __name__ == "__main__":
    optimize_sqlite_database()
    estimate_storage_requirements()
    print("\n🎉 SQLite数据库优化完成!")