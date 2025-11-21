"""
技术指标服务单元测试
"""
import pytest
import pandas as pd
import numpy as np
import asyncio
import tempfile
import sqlite3
import os
import sys

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.services.technical_indicator_service import TechnicalIndicatorService

class MockDatabaseManager:
    """模拟数据库管理器"""
    def __init__(self, db_path):
        self.db_path = db_path

class TestTechnicalIndicatorService:
    
    @pytest.fixture
    def setup_test_data(self):
        """创建测试数据"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 创建测试数据表
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # 创建测试表
            cursor.execute('''
                CREATE TABLE daily_stock_changes (
                    stock_code TEXT,
                    trade_date TEXT,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume INTEGER,
                    turnover REAL,
                    change_percent REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE stock_technical_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT,
                    trade_date TEXT,
                    ma5 REAL,
                    ma10 REAL,
                    ma20 REAL,
                    ma60 REAL,
                    volume_ratio REAL,
                    turnover_rate REAL,
                    avg_volume_5d REAL,
                    avg_volume_20d REAL,
                    kdj_k REAL,
                    kdj_d REAL,
                    kdj_j REAL,
                    rsi_6 REAL,
                    rsi_12 REAL,
                    rsi_24 REAL,
                    macd_dif REAL,
                    macd_dea REAL,
                    macd_hist REAL,
                    obv REAL,
                    is_new_high BOOLEAN,
                    is_limit_up BOOLEAN,
                    has_gap_up BOOLEAN,
                    gap_ratio REAL,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # 插入测试数据（60天的模拟数据）
            dates = pd.date_range('2024-01-01', periods=60)
            base_price = 10.0
            
            for i, date in enumerate(dates):
                # 模拟价格波动
                price_change = np.sin(i * 0.1) * 0.5 + np.random.normal(0, 0.2)
                price = base_price + price_change
                
                cursor.execute('''
                    INSERT INTO daily_stock_changes 
                    (stock_code, trade_date, open_price, high_price, low_price, 
                     close_price, volume, turnover, change_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'TEST001',
                    date.strftime('%Y-%m-%d'),
                    price * 0.99,  # open
                    price * 1.02,  # high
                    price * 0.98,  # low
                    price,         # close
                    np.random.randint(1000, 10000),  # volume
                    np.random.uniform(1000000, 10000000),  # turnover
                    np.random.uniform(-5, 5)  # change_percent
                ))
            
            conn.commit()
        
        # 创建服务实例
        self.db_manager = MockDatabaseManager(self.temp_db.name)
        self.service = TechnicalIndicatorService(self.db_manager)
        
        yield
        
        # 清理
        os.unlink(self.temp_db.name)
    
    def test_calculate_moving_averages(self, setup_test_data):
        """测试移动平均线计算"""
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=30)
        df = pd.DataFrame({
            'trade_date': dates.strftime('%Y-%m-%d'),
            'close_price': range(10, 40)  # 递增价格
        })
        
        result = self.service._calculate_moving_averages(df)
        
        # 验证结果
        assert 'ma5' in result
        assert 'ma10' in result
        assert 'ma20' in result
        assert 'ma60' in result
        
        # MA5应该不为空（有30个数据点）
        assert result['ma5'] is not None
        assert result['ma10'] is not None
        assert result['ma20'] is not None
        
        # MA60应该为空（只有30个数据点）
        assert result['ma60'] is None
        
        # MA5应该小于MA10（因为价格递增）
        assert result['ma5'] > result['ma10']
    
    def test_calculate_volume_indicators(self, setup_test_data):
        """测试量价指标计算"""
        df = pd.DataFrame({
            'volume': [1000, 1500, 2000, 1200, 1800, 2200],
            'close_price': [10, 11, 12, 11.5, 12.5, 13],
            'turnover': [10000, 15000, 20000, 12000, 18000, 22000]
        })
        
        result = self.service._calculate_volume_indicators(df)
        
        assert 'volume_ratio' in result
        assert 'turnover_rate' in result
        assert 'avg_volume_5d' in result
        assert 'avg_volume_20d' in result
        
        # 验证量比计算
        assert result['volume_ratio'] is not None
        assert result['avg_volume_5d'] is not None
    
    def test_calculate_kdj(self, setup_test_data):
        """测试KDJ指标计算"""
        # 创建测试数据
        df = pd.DataFrame({
            'high_price': [15, 16, 17, 16, 18, 19, 18, 20, 21, 20, 22, 23],
            'low_price': [10, 11, 12, 11, 13, 14, 13, 15, 16, 15, 17, 18],
            'close_price': [12, 13, 14, 13, 15, 16, 15, 17, 18, 17, 19, 20]
        })
        
        result = self.service._calculate_kdj(
            df['high_price'], 
            df['low_price'], 
            df['close_price']
        )
        
        assert 'kdj_k' in result
        assert 'kdj_d' in result
        assert 'kdj_j' in result
        
        # KDJ值应该在合理范围内
        if result['kdj_k'] is not None:
            assert 0 <= result['kdj_k'] <= 100
        if result['kdj_d'] is not None:
            assert 0 <= result['kdj_d'] <= 100
    
    def test_calculate_rsi(self, setup_test_data):
        """测试RSI指标计算"""
        # 创建测试数据（交替上涨下跌）
        prices = [10, 11, 10.5, 12, 11, 13, 12.5, 14, 13, 15, 14.5, 16, 15, 17, 16.5]
        close_series = pd.Series(prices)
        
        rsi = self.service._calculate_rsi(close_series, 6)
        
        if rsi is not None:
            assert 0 <= rsi <= 100
    
    def test_calculate_macd(self, setup_test_data):
        """测试MACD指标计算"""
        # 创建上升趋势的价格数据
        prices = list(range(10, 50))  # 40个数据点
        close_series = pd.Series(prices)
        
        result = self.service._calculate_macd(close_series)
        
        assert 'macd_dif' in result
        assert 'macd_dea' in result
        assert 'macd_hist' in result
        
        # MACD值应该存在（有足够的数据）
        assert result['macd_dif'] is not None
        assert result['macd_dea'] is not None
        assert result['macd_hist'] is not None
    
    def test_calculate_pattern_indicators(self, setup_test_data):
        """测试形态指标计算"""
        # 创建30个数据点（足够计算20日新高）
        prices = list(range(10, 40))  # 30个递增价格
        df = pd.DataFrame({
            'close_price': prices,
            'high_price': [x + 1 for x in prices],
            'low_price': [x - 1 for x in prices],
            'change_percent': [2.0] * 29 + [10.0]  # 最后一天涨停
        })
        
        result = self.service._calculate_pattern_indicators(df)
        
        assert 'is_new_high' in result
        assert 'is_limit_up' in result
        assert 'has_gap_up' in result
        assert 'gap_ratio' in result
        
        # 应该创新高（递增价格，当前价格是最高的）
        assert result['is_new_high'] is True
        
        # 应该涨停（最后一天10%涨幅）
        assert result['is_limit_up'] is True
        
        # 检查数据类型
        assert isinstance(result['is_new_high'], bool)
        assert isinstance(result['is_limit_up'], bool)
        assert isinstance(result['has_gap_up'], bool)
        assert isinstance(result['gap_ratio'], float)
    
    @pytest.mark.asyncio
    async def test_calculate_all_indicators(self, setup_test_data):
        """测试完整的指标计算"""
        result = await self.service.calculate_all_indicators('TEST001')
        
        # 验证返回了所有类型的指标
        assert isinstance(result, dict)
        
        # 移动平均线
        assert 'ma5' in result
        assert 'ma20' in result
        
        # 量价指标
        assert 'volume_ratio' in result
        
        # 技术指标
        assert 'kdj_k' in result
        assert 'rsi_6' in result
        assert 'macd_dif' in result
        
        # 形态指标
        assert 'is_new_high' in result
    
    @pytest.mark.asyncio
    async def test_save_and_get_indicators(self, setup_test_data):
        """测试指标保存和读取"""
        test_indicators = {
            'ma5': 10.5,
            'ma20': 10.0,
            'volume_ratio': 1.2,
            'kdj_k': 50.0,
            'rsi_6': 60.0,
            'is_new_high': True,
            'is_limit_up': False
        }
        
        # 保存指标
        await self.service.save_indicators_to_db(
            'TEST001', 
            '2024-03-01', 
            test_indicators
        )
        
        # 读取指标
        result = await self.service.get_indicators_from_db('TEST001', '2024-03-01')
        
        assert result is not None
        assert result['ma5'] == 10.5
        assert result['ma20'] == 10.0
        assert result['volume_ratio'] == 1.2
        assert result['is_new_high'] == 1  # 布尔值存储为整数
        assert result['is_limit_up'] == 0
    
    @pytest.mark.asyncio
    async def test_batch_calculate_indicators(self, setup_test_data):
        """测试批量计算指标"""
        stock_codes = ['TEST001']  # 只有一只测试股票
        
        success_count = await self.service.batch_calculate_indicators(
            stock_codes, 
            '2024-03-01'
        )
        
        assert success_count == 1
        
        # 验证数据已保存
        result = await self.service.get_indicators_from_db('TEST001', '2024-03-01')
        assert result is not None

def run_tests():
    """运行测试"""
    import subprocess
    import sys
    
    try:
        # 运行pytest
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            __file__, 
            '-v', 
            '--tb=short'
        ], capture_output=True, text=True)
        
        print("测试输出:")
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试失败: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
        sys.exit(1)