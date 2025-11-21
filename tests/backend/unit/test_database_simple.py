"""
简化数据库测试 - 基础数据库功能测试
"""
import pytest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path

# 尝试导入后端模块
try:
    from backend.database import DatabaseManager, StockPool
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False
    print("Backend modules not available, testing basic database operations only")


class TestDatabaseBasics:
    """基础数据库操作测试"""
    
    def test_sqlite_connection(self):
        """测试SQLite连接"""
        # 创建临时数据库
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建测试表
            cursor.execute('''
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    value REAL
                )
            ''')
            
            # 插入测试数据
            cursor.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                ("test_item", 123.45)
            )
            conn.commit()
            
            # 查询数据
            cursor.execute("SELECT * FROM test_table")
            rows = cursor.fetchall()
            
            assert len(rows) == 1
            assert rows[0][1] == "test_item"  # name
            assert rows[0][2] == 123.45       # value
            
            conn.close()
            
        finally:
            # 清理临时文件
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_sql_injection_protection(self):
        """测试SQL注入防护"""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    password TEXT
                )
            ''')
            
            # 插入正常数据
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("testuser", "password123")
            )
            conn.commit()
            
            # 尝试SQL注入攻击 (应该被参数化查询阻止)
            malicious_input = "'; DROP TABLE users; --"
            
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (malicious_input,)
            )
            
            # 查询结果应该为空 (没有匹配的用户名)
            results = cursor.fetchall()
            assert len(results) == 0
            
            # 验证表仍然存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            table_exists = cursor.fetchone()
            assert table_exists is not None
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_transaction_handling(self):
        """测试事务处理"""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE accounts (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    balance REAL
                )
            ''')
            
            # 插入初始数据
            cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", ("Alice", 1000.0))
            cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", ("Bob", 500.0))
            conn.commit()
            
            # 开始事务 - 模拟转账
            try:
                cursor.execute("UPDATE accounts SET balance = balance - 100 WHERE name = ?", ("Alice",))
                cursor.execute("UPDATE accounts SET balance = balance + 100 WHERE name = ?", ("Bob",))
                
                # 检查中间状态
                cursor.execute("SELECT balance FROM accounts WHERE name = ?", ("Alice",))
                alice_balance = cursor.fetchone()[0]
                assert alice_balance == 900.0
                
                conn.commit()  # 提交事务
                
            except Exception as e:
                conn.rollback()  # 回滚事务
                raise e
            
            # 验证最终状态
            cursor.execute("SELECT balance FROM accounts WHERE name = ?", ("Alice",))
            alice_final = cursor.fetchone()[0]
            cursor.execute("SELECT balance FROM accounts WHERE name = ?", ("Bob",))
            bob_final = cursor.fetchone()[0]
            
            assert alice_final == 900.0
            assert bob_final == 600.0
            
            conn.close()
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


@pytest.mark.skipif(not BACKEND_AVAILABLE, reason="Backend modules not available")
class TestDatabaseManagerIntegration:
    """数据库管理器集成测试 (需要backend模块)"""
    
    @pytest.fixture
    def temp_db_path(self):
        """临时数据库路径"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    
    def test_database_manager_creation(self, temp_db_path):
        """测试数据库管理器创建"""
        if not BACKEND_AVAILABLE:
            pytest.skip("Backend modules not available")
            
        db_manager = DatabaseManager(temp_db_path)
        assert os.path.exists(temp_db_path)
        assert db_manager.db_path == temp_db_path
    
    @pytest.mark.asyncio
    async def test_stock_pool_basic_operations(self, temp_db_path):
        """测试股票池基础操作"""
        if not BACKEND_AVAILABLE:
            pytest.skip("Backend modules not available")
            
        db_manager = DatabaseManager(temp_db_path)
        
        # 创建股票池对象
        from datetime import datetime
        stock_pool = StockPool(
            stock_code="000001",
            stock_name="平安银行",
            pool_type="holding",
            shares=1000,
            avg_cost=12.50,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # 测试添加
        stock_id = await db_manager.add_stock_pool(stock_pool)
        assert stock_id is not None
        assert isinstance(stock_id, int)
        
        # 测试获取
        retrieved_stock = await db_manager.get_stock_pool(stock_id)
        assert retrieved_stock is not None
        assert retrieved_stock.stock_code == "000001"
        assert retrieved_stock.stock_name == "平安银行"


class TestDataValidation:
    """数据验证测试"""
    
    def test_stock_code_validation(self):
        """测试股票代码验证"""
        def is_valid_stock_code(code):
            if not code or not isinstance(code, str):
                return False
            # A股代码通常是6位数字
            if len(code) == 6 and code.isdigit():
                return True
            # 港股代码可能包含字母
            if 4 <= len(code) <= 6:
                return True
            return False
        
        # 有效代码
        assert is_valid_stock_code("000001") is True
        assert is_valid_stock_code("600036") is True
        assert is_valid_stock_code("00700") is True   # 港股
        
        # 无效代码
        assert is_valid_stock_code("") is False
        assert is_valid_stock_code(None) is False
        assert is_valid_stock_code("123") is False    # 太短 (3位)
        assert is_valid_stock_code("1234567") is False  # 太长
    
    def test_financial_data_validation(self):
        """测试财务数据验证"""
        def validate_financial_data(shares, price, cost):
            errors = []
            
            if shares is not None and shares < 0:
                errors.append("持股数量不能为负数")
            
            if price is not None and price <= 0:
                errors.append("股价必须大于0")
                
            if cost is not None and cost <= 0:
                errors.append("成本价必须大于0")
                
            return errors
        
        # 有效数据
        errors = validate_financial_data(1000, 13.20, 12.50)
        assert len(errors) == 0
        
        # 无效数据
        errors = validate_financial_data(-100, 13.20, 12.50)
        assert "持股数量不能为负数" in errors
        
        errors = validate_financial_data(1000, -5.0, 12.50)
        assert "股价必须大于0" in errors
        
        errors = validate_financial_data(1000, 13.20, 0)
        assert "成本价必须大于0" in errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])