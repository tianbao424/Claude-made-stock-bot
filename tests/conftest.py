"""
全局测试配置文件
为所有测试提供共享的 fixtures 和配置
"""
import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path.parent))  # 确保backend作为包可以导入

# 配置异步事件循环
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 后端测试 fixtures
@pytest.fixture(scope="session")
def temp_db_path() -> Generator[str, None, None]:
    """创建临时数据库文件"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

@pytest.fixture
def mock_akshare_data():
    """模拟 AkShare 数据"""
    return {
        'stock_info': {
            '000001': {
                'code': '000001',
                'name': '平安银行',
                'price': 13.20,
                'change': 0.50,
                'change_percent': 3.94
            },
            '000002': {
                'code': '000002', 
                'name': '万科A',
                'price': 22.50,
                'change': -0.30,
                'change_percent': -1.32
            }
        },
        'history_data': [
            {
                'date': '2023-01-01',
                'open': 13.00,
                'high': 13.50,
                'low': 12.80,
                'close': 13.20,
                'volume': 2000000,
                'change_percent': 1.54
            },
            {
                'date': '2023-01-02',
                'open': 13.20,
                'high': 13.80,
                'low': 13.10,
                'close': 13.60,
                'volume': 2500000,
                'change_percent': 3.03
            }
        ]
    }

# 前端测试 fixtures
@pytest.fixture(autouse=True)
def setup_dom_environment():
    """设置前端测试的DOM环境"""
    # 这里可以添加DOM相关的setup代码
    pass

@pytest.fixture
def mock_websocket():
    """模拟WebSocket连接"""
    class MockWebSocket:
        def __init__(self, url):
            self.url = url
            self.readyState = 1  # OPEN
            
        def send(self, data):
            pass
            
        def close(self):
            self.readyState = 3  # CLOSED
    
    return MockWebSocket

# 集成测试 fixtures
@pytest.fixture(scope="module") 
async def test_client():
    """测试用的FastAPI客户端"""
    from fastapi.testclient import TestClient
    from backend.main import app
    
    with TestClient(app) as client:
        yield client

@pytest.fixture
def sample_stock_data():
    """示例股票数据"""
    return [
        {
            'stock_code': '000001',
            'stock_name': '平安银行',
            'pool_type': 'holding',
            'shares': 1000,
            'avg_cost': 12.50,
            'current_price': 13.20,
            'market_value': 13200.0,
            'tags': ['银行', '金融'],
            'notes': '持仓股票'
        },
        {
            'stock_code': '000002',
            'stock_name': '万科A',
            'pool_type': 'potential',
            'shares': 0,
            'avg_cost': 0.0,
            'current_price': 22.50,
            'market_value': 0.0,
            'tags': ['房地产'],
            'notes': '潜在股票'
        }
    ]

# 性能测试相关
@pytest.fixture
def performance_timer():
    """性能计时器"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            if self.start_time is None:
                raise RuntimeError("Timer not started")
            return time.time() - self.start_time
    
    return Timer()

# 数据生成helpers
@pytest.fixture
def data_generator():
    """测试数据生成器"""
    import random
    import string
    from datetime import datetime, timedelta
    
    class DataGenerator:
        @staticmethod
        def random_string(length=10):
            return ''.join(random.choices(string.ascii_letters, k=length))
        
        @staticmethod
        def random_stock_code():
            return f"{random.randint(0, 999999):06d}"
        
        @staticmethod
        def random_price(min_price=1.0, max_price=1000.0):
            return round(random.uniform(min_price, max_price), 2)
        
        @staticmethod
        def random_date_range(days_back=30):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            return start_date, end_date
    
    return DataGenerator()

# 清理函数
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """测试后清理"""
    yield
    # 在这里添加清理逻辑，如清理临时文件、重置状态等
    pass