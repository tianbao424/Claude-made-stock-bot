#!/usr/bin/env python3
"""
数据库迁移脚本 001 - 添加高级策略支持
执行时间: 2025-01-06
版本: v2.0
"""

import sqlite3
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """备份数据库"""
    try:
        backup_dir = f"backups/{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = f"{backup_dir}/stock_pool_backup_{datetime.now().strftime('%H%M%S')}.db"
        
        # 使用SQLite的VACUUM INTO进行备份
        with sqlite3.connect(db_path) as conn:
            conn.execute(f"VACUUM INTO '{backup_path}'")
        
        logger.info(f"✅ 数据库备份成功: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"❌ 数据库备份失败: {e}")
        raise

def check_table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def get_table_info(cursor, table_name: str):
    """获取表结构信息"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def execute_migration(db_path: str) -> bool:
    """执行数据库迁移"""
    try:
        logger.info("🚀 开始执行数据库迁移...")
        
        # 1. 备份数据库
        backup_path = backup_database(db_path)
        
        # 2. 连接数据库
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 3. 检查迁移是否已执行
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='migration_history'
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    SELECT COUNT(*) FROM migration_history 
                    WHERE migration_name = '001_add_technical_indicators'
                """)
                if cursor.fetchone()[0] > 0:
                    logger.info("⚠️ 迁移已执行过，跳过")
                    return True
            
            # 4. 读取并执行SQL脚本
            sql_file = os.path.join(os.path.dirname(__file__), 'database_upgrade.sql')
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # 执行完整的SQL脚本
            try:
                cursor.executescript(sql_script)
                logger.info("✅ SQL脚本执行成功")
            except Exception as e:
                logger.error(f"❌ SQL脚本执行失败: {e}")
                # 尝试逐个执行
                logger.info("🔄 尝试逐个执行SQL语句...")
                
                # 分割SQL语句
                statements = []
                current_statement = ""
                for line in sql_script.split('\n'):
                    line = line.strip()
                    if line.startswith('--') or not line:
                        continue
                    
                    current_statement += line + " "
                    if line.endswith(';'):
                        statements.append(current_statement.strip())
                        current_statement = ""
                
                for i, statement in enumerate(statements):
                    try:
                        cursor.execute(statement)
                        logger.debug(f"执行SQL语句 {i+1}/{len(statements)}: {statement[:30]}...")
                    except Exception as stmt_error:
                        if "already exists" in str(stmt_error).lower():
                            logger.debug(f"对象已存在，跳过: {stmt_error}")
                        else:
                            logger.error(f"执行SQL失败: {statement[:50]}... 错误: {stmt_error}")
                            # 继续执行其他语句而不是抛出异常
            
            # 5. 验证表创建
            required_tables = [
                'stock_technical_indicators',
                'advanced_screening_results',
                'realtime_signals',
                'strategy_configs',
                'migration_history'
            ]
            
            for table in required_tables:
                if check_table_exists(cursor, table):
                    logger.info(f"✅ 表 {table} 创建成功")
                    # 显示表结构
                    info = get_table_info(cursor, table)
                    logger.debug(f"表 {table} 字段数: {len(info)}")
                else:
                    logger.error(f"❌ 表 {table} 创建失败")
                    raise Exception(f"表 {table} 创建失败")
            
            # 6. 提交事务
            conn.commit()
            logger.info("✅ 数据库迁移执行成功")
            
            # 7. 验证数据完整性
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result[0] == 'ok':
                logger.info("✅ 数据库完整性检查通过")
            else:
                logger.error(f"❌ 数据库完整性检查失败: {result[0]}")
                raise Exception("数据库完整性检查失败")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        logger.info(f"💡 可以从备份恢复: {backup_path}")
        return False

def verify_migration(db_path: str) -> bool:
    """验证迁移结果"""
    try:
        logger.info("🔍 验证迁移结果...")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 检查所有新表
            tables_to_check = [
                'stock_technical_indicators',
                'advanced_screening_results',
                'realtime_signals',
                'strategy_configs'
            ]
            
            for table in tables_to_check:
                # 检查表存在
                if not check_table_exists(cursor, table):
                    logger.error(f"❌ 表 {table} 不存在")
                    return False
                
                # 检查索引
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = cursor.fetchall()
                logger.info(f"✅ 表 {table}: {len(indexes)} 个索引")
            
            # 检查迁移记录
            cursor.execute("""
                SELECT migration_name, executed_at 
                FROM migration_history 
                WHERE migration_name = '001_add_technical_indicators'
            """)
            
            result = cursor.fetchone()
            if result:
                logger.info(f"✅ 迁移记录: {result[0]} - {result[1]}")
            else:
                logger.error("❌ 未找到迁移记录")
                return False
            
            logger.info("✅ 迁移验证通过")
            return True
            
    except Exception as e:
        logger.error(f"❌ 迁移验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("数据库迁移脚本 001 - 高级选股策略支持")
    logger.info("=" * 60)
    
    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), 'stock_pool.db')
    
    if not os.path.exists(db_path):
        logger.error(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"📁 数据库路径: {db_path}")
    
    # 执行迁移
    success = execute_migration(db_path)
    
    if success:
        # 验证迁移
        if verify_migration(db_path):
            logger.info("🎉 数据库迁移完成！")
            return True
        else:
            logger.error("❌ 迁移验证失败")
            return False
    else:
        logger.error("❌ 数据库迁移失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)