# 第1周实施详细指南

## 概览
- **目标**：搭建高级选股策略的基础架构
- **时间**：第1周（Day 1-5）
- **关键交付物**：数据库升级、技术指标服务、策略框架

---

## Day 1-2: 数据库升级与迁移

### 任务清单

#### ✅ 步骤1：备份现有数据库
```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# 备份SQLite数据库
cp backend/stock_pool.db backups/$(date +%Y%m%d)/stock_pool_backup.db

# 验证备份完整性
sqlite3 backups/$(date +%Y%m%d)/stock_pool_backup.db ".tables"
```

#### ✅ 步骤2：创建新数据表
```sql
-- backend/database_upgrade.sql
-- 技术指标表
CREATE TABLE IF NOT EXISTS stock_technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    
    -- 移动平均线
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma60 REAL,
    
    -- 量价指标
    volume_ratio REAL,        -- 量比
    turnover_rate REAL,       -- 换手率
    avg_volume_5d REAL,       -- 5日平均成交量
    avg_volume_20d REAL,      -- 20日平均成交量
    
    -- 技术指标
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
    
    -- 形态指标
    is_new_high BOOLEAN DEFAULT 0,    -- 是否创新高
    is_limit_up BOOLEAN DEFAULT 0,    -- 是否涨停
    has_gap_up BOOLEAN DEFAULT 0,     -- 是否向上跳空
    gap_ratio REAL,                   -- 跳空幅度
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 创建索引
CREATE INDEX idx_tech_stock_date ON stock_technical_indicators(stock_code, trade_date);
CREATE INDEX idx_tech_trade_date ON stock_technical_indicators(trade_date);

-- 高级筛选结果表
CREATE TABLE IF NOT EXISTS advanced_screening_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    screening_date TEXT NOT NULL,
    
    -- 策略信息
    strategy_type TEXT NOT NULL,      -- 策略类型：daily/intraday/risk
    signal_type TEXT NOT NULL,        -- 信号类型：buy/sell/hold/wait
    signal_strength TEXT NOT NULL,    -- 信号强度：strong/medium/weak
    
    -- 分析结果
    score REAL NOT NULL,              -- 综合评分 0-100
    confidence REAL,                  -- 置信度 0-1
    reason TEXT,                      -- 触发原因
    risk_level TEXT,                  -- 风险等级：low/medium/high
    
    -- 技术数据
    current_price REAL,
    target_price REAL,
    stop_loss_price REAL,
    technical_data TEXT,              -- JSON格式的详细技术数据
    
    -- 策略详情
    strategies_passed TEXT,           -- JSON数组：通过的策略列表
    strategies_failed TEXT,           -- JSON数组：未通过的策略列表
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, screening_date, strategy_type)
);

-- 创建索引
CREATE INDEX idx_adv_screening_date ON advanced_screening_results(screening_date);
CREATE INDEX idx_adv_stock_code ON advanced_screening_results(stock_code);
CREATE INDEX idx_adv_signal_type ON advanced_screening_results(signal_type);

-- 实时信号表
CREATE TABLE IF NOT EXISTS realtime_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    signal_time TEXT NOT NULL,
    
    -- 信号信息
    signal_type TEXT NOT NULL,        -- buy/sell/hold/alert
    price REAL NOT NULL,
    volume REAL,
    strategy_name TEXT NOT NULL,      -- 触发的策略名称
    
    -- 紧急程度
    urgency TEXT NOT NULL,            -- high/medium/low
    
    -- 详细信息
    details TEXT,                     -- JSON格式的详细信息
    message TEXT,                     -- 用户友好的消息
    
    -- 状态管理
    is_processed BOOLEAN DEFAULT 0,   -- 是否已处理
    is_notified BOOLEAN DEFAULT 0,    -- 是否已通知
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_rt_signal_time ON realtime_signals(signal_time);
CREATE INDEX idx_rt_stock_code ON realtime_signals(stock_code);
CREATE INDEX idx_rt_urgency ON realtime_signals(urgency);
CREATE INDEX idx_rt_processed ON realtime_signals(is_processed);

-- 策略配置表
CREATE TABLE IF NOT EXISTS strategy_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,                     -- 用户ID（未来多用户支持）
    config_name TEXT NOT NULL,
    config_type TEXT NOT NULL,       -- daily/intraday/risk
    
    -- 配置数据
    config_data TEXT NOT NULL,       -- JSON格式的配置
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### ✅ 步骤3：编写迁移脚本
```python
# backend/migrations/001_add_technical_indicators.py
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def migrate_database(db_path: str):
    """执行数据库迁移"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 读取SQL文件
            with open('database_upgrade.sql', 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # 执行迁移
            cursor.executescript(sql_script)
            
            # 记录迁移历史
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT NOT NULL,
                    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute(
                'INSERT INTO migration_history (migration_name) VALUES (?)',
                ('001_add_technical_indicators',)
            )
            
            conn.commit()
            logger.info("✅ 数据库迁移成功完成")
            return True
            
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        return False

if __name__ == "__main__":
    migrate_database('backend/stock_pool.db')
```

### 验收标准
- [ ] 备份文件创建成功
- [ ] 新表结构创建无误
- [ ] 索引创建成功
- [ ] 迁移脚本运行无错误
- [ ] 现有数据完整性验证通过

---

## Day 3-4: 技术指标计算服务

### 任务清单

#### ✅ 步骤1：创建技术指标服务
```python
# backend/services/technical_indicator_service.py
"""
技术指标计算服务
支持MA、KDJ、RSI、MACD、OBV等常用指标
"""
import numpy as np
import pandas as pd
import talib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicatorService:
    """技术指标计算服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    async def calculate_all_indicators(self, stock_code: str, days: int = 60) -> Dict:
        """
        计算股票的所有技术指标
        
        Args:
            stock_code: 股票代码
            days: 计算天数
            
        Returns:
            包含所有指标的字典
        """
        try:
            # 获取历史数据
            df = await self._get_stock_history(stock_code, days)
            if df is None or len(df) < 20:
                logger.warning(f"股票 {stock_code} 历史数据不足")
                return {}
            
            indicators = {}
            
            # 移动平均线
            indicators.update(self._calculate_moving_averages(df))
            
            # 量价指标
            indicators.update(self._calculate_volume_indicators(df))
            
            # 技术指标
            indicators.update(self._calculate_technical_indicators(df))
            
            # 形态指标
            indicators.update(self._calculate_pattern_indicators(df))
            
            return indicators
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {stock_code}, {e}")
            return {}
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> Dict:
        """计算移动平均线"""
        close = df['close_price'].values
        
        return {
            'ma5': talib.SMA(close, timeperiod=5)[-1] if len(close) >= 5 else None,
            'ma10': talib.SMA(close, timeperiod=10)[-1] if len(close) >= 10 else None,
            'ma20': talib.SMA(close, timeperiod=20)[-1] if len(close) >= 20 else None,
            'ma60': talib.SMA(close, timeperiod=60)[-1] if len(close) >= 60 else None,
        }
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict:
        """计算量价指标"""
        volume = df['volume'].values
        close = df['close_price'].values
        
        # 量比计算
        avg_volume_5d = np.mean(volume[-5:]) if len(volume) >= 5 else None
        avg_volume_20d = np.mean(volume[-20:]) if len(volume) >= 20 else None
        current_volume = volume[-1] if len(volume) > 0 else 0
        
        volume_ratio = (current_volume / avg_volume_5d) if avg_volume_5d and avg_volume_5d > 0 else None
        
        # 换手率（需要流通股本数据，这里简化处理）
        turnover_rate = df['turnover'].iloc[-1] / df['close_price'].iloc[-1] / 100 if len(df) > 0 else None
        
        return {
            'volume_ratio': volume_ratio,
            'turnover_rate': turnover_rate,
            'avg_volume_5d': avg_volume_5d,
            'avg_volume_20d': avg_volume_20d
        }
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """计算技术指标"""
        high = df['high_price'].values
        low = df['low_price'].values
        close = df['close_price'].values
        volume = df['volume'].values
        
        indicators = {}
        
        # KDJ指标
        if len(close) >= 9:
            k, d = talib.STOCH(high, low, close, 
                             fastk_period=9, slowk_period=3, slowd_period=3)
            indicators['kdj_k'] = k[-1] if not np.isnan(k[-1]) else None
            indicators['kdj_d'] = d[-1] if not np.isnan(d[-1]) else None
            indicators['kdj_j'] = 3 * k[-1] - 2 * d[-1] if not np.isnan(k[-1]) and not np.isnan(d[-1]) else None
        
        # RSI指标
        if len(close) >= 6:
            rsi_6 = talib.RSI(close, timeperiod=6)
            indicators['rsi_6'] = rsi_6[-1] if not np.isnan(rsi_6[-1]) else None
        
        if len(close) >= 12:
            rsi_12 = talib.RSI(close, timeperiod=12)
            indicators['rsi_12'] = rsi_12[-1] if not np.isnan(rsi_12[-1]) else None
        
        # MACD指标
        if len(close) >= 26:
            dif, dea, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            indicators['macd_dif'] = dif[-1] if not np.isnan(dif[-1]) else None
            indicators['macd_dea'] = dea[-1] if not np.isnan(dea[-1]) else None
            indicators['macd_hist'] = hist[-1] if not np.isnan(hist[-1]) else None
        
        # OBV指标
        if len(volume) > 1:
            obv = talib.OBV(close, volume)
            indicators['obv'] = obv[-1] if not np.isnan(obv[-1]) else None
        
        return indicators
    
    def _calculate_pattern_indicators(self, df: pd.DataFrame) -> Dict:
        """计算形态指标"""
        if len(df) < 20:
            return {}
        
        close = df['close_price'].values
        high = df['high_price'].values
        
        # 是否创新高（20日）
        is_new_high = close[-1] >= np.max(high[-20:])
        
        # 是否涨停（简化判断）
        change_percent = df['change_percent'].iloc[-1] if len(df) > 0 else 0
        is_limit_up = change_percent >= 9.8  # 接近涨停
        
        # 向上跳空检测
        has_gap_up = False
        gap_ratio = 0
        if len(df) >= 2:
            yesterday_high = df['high_price'].iloc[-2]
            today_low = df['low_price'].iloc[-1]
            if today_low > yesterday_high:
                has_gap_up = True
                gap_ratio = (today_low - yesterday_high) / yesterday_high
        
        return {
            'is_new_high': is_new_high,
            'is_limit_up': is_limit_up,
            'has_gap_up': has_gap_up,
            'gap_ratio': gap_ratio
        }
    
    async def _get_stock_history(self, stock_code: str, days: int) -> pd.DataFrame:
        """获取股票历史数据"""
        import sqlite3
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = '''
                    SELECT trade_date, open_price, high_price, low_price, 
                           close_price, volume, turnover, change_percent
                    FROM daily_stock_changes
                    WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
                    ORDER BY trade_date
                '''
                
                df = pd.read_sql_query(query, conn, params=(stock_code, start_date, end_date))
                return df if not df.empty else None
                
        except Exception as e:
            logger.error(f"获取历史数据失败: {stock_code}, {e}")
            return None
    
    async def save_indicators_to_db(self, stock_code: str, trade_date: str, indicators: Dict):
        """保存技术指标到数据库"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 准备数据
                data = {
                    'stock_code': stock_code,
                    'trade_date': trade_date,
                    **indicators,
                    'updated_at': datetime.now().isoformat()
                }
                
                # 动态构建SQL
                columns = list(data.keys())
                placeholders = ['?' * len(columns)]
                values = list(data.values())
                
                sql = f'''
                    INSERT OR REPLACE INTO stock_technical_indicators 
                    ({', '.join(columns)}) VALUES ({', '.join(placeholders)})
                '''
                
                cursor.execute(sql, values)
                conn.commit()
                
                logger.info(f"✅ 保存技术指标成功: {stock_code} {trade_date}")
                
        except Exception as e:
            logger.error(f"❌ 保存技术指标失败: {stock_code}, {e}")
    
    async def batch_calculate_indicators(self, stock_codes: List[str], trade_date: str = None):
        """批量计算技术指标"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        success_count = 0
        total_count = len(stock_codes)
        
        for i, stock_code in enumerate(stock_codes):
            try:
                indicators = await self.calculate_all_indicators(stock_code)
                if indicators:
                    await self.save_indicators_to_db(stock_code, trade_date, indicators)
                    success_count += 1
                
                # 进度报告
                if (i + 1) % 100 == 0:
                    logger.info(f"技术指标计算进度: {i + 1}/{total_count}")
                    
            except Exception as e:
                logger.error(f"批量计算指标失败: {stock_code}, {e}")
                continue
        
        logger.info(f"✅ 批量计算完成: {success_count}/{total_count}")
        return success_count

# 全局实例
_technical_indicator_service = None

def get_technical_indicator_service(db_manager):
    """获取技术指标服务实例"""
    global _technical_indicator_service
    if _technical_indicator_service is None:
        _technical_indicator_service = TechnicalIndicatorService(db_manager)
    return _technical_indicator_service
```

#### ✅ 步骤2：安装依赖
```bash
# 添加到 backend/requirements.txt
echo "TA-Lib==0.4.25" >> backend/requirements.txt
echo "numpy>=1.21.0" >> backend/requirements.txt
echo "pandas>=1.3.0" >> backend/requirements.txt

# 安装依赖
pip install -r backend/requirements.txt
```

#### ✅ 步骤3：创建单元测试
```python
# tests/backend/test_technical_indicators.py
import pytest
import pandas as pd
import numpy as np
from backend.services.technical_indicator_service import TechnicalIndicatorService

class TestTechnicalIndicatorService:
    
    def setup_method(self):
        """测试前准备"""
        # 创建模拟数据
        dates = pd.date_range('2024-01-01', periods=60)
        self.mock_data = pd.DataFrame({
            'trade_date': dates.strftime('%Y-%m-%d'),
            'open_price': np.random.uniform(10, 15, 60),
            'high_price': np.random.uniform(15, 20, 60),
            'low_price': np.random.uniform(8, 12, 60),
            'close_price': np.random.uniform(10, 15, 60),
            'volume': np.random.randint(1000, 10000, 60),
            'turnover': np.random.uniform(1000000, 10000000, 60),
            'change_percent': np.random.uniform(-5, 5, 60)
        })
    
    def test_calculate_moving_averages(self):
        """测试移动平均线计算"""
        service = TechnicalIndicatorService(None)
        result = service._calculate_moving_averages(self.mock_data)
        
        assert 'ma5' in result
        assert 'ma20' in result
        assert result['ma5'] is not None
        assert result['ma20'] is not None
    
    def test_calculate_volume_indicators(self):
        """测试量价指标计算"""
        service = TechnicalIndicatorService(None)
        result = service._calculate_volume_indicators(self.mock_data)
        
        assert 'volume_ratio' in result
        assert 'avg_volume_5d' in result
    
    def test_calculate_technical_indicators(self):
        """测试技术指标计算"""
        service = TechnicalIndicatorService(None)
        result = service._calculate_technical_indicators(self.mock_data)
        
        assert 'kdj_k' in result
        assert 'rsi_6' in result
        assert 'macd_dif' in result
        
    def test_calculate_pattern_indicators(self):
        """测试形态指标计算"""
        service = TechnicalIndicatorService(None)
        result = service._calculate_pattern_indicators(self.mock_data)
        
        assert 'is_new_high' in result
        assert 'is_limit_up' in result
        assert isinstance(result['is_new_high'], bool)
```

### 验收标准
- [ ] 技术指标服务创建成功
- [ ] 所有指标计算函数正常工作
- [ ] 单元测试通过率 100%
- [ ] 批量计算功能正常
- [ ] 数据保存到数据库成功

---

## Day 5: 基础框架集成

### 任务清单

#### ✅ 步骤1：创建策略基类
```python
# backend/services/strategy_base.py
"""
策略基础类和接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WAIT = "wait"
    ALERT = "alert"

class SignalStrength(Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class StrategyResult:
    """策略执行结果"""
    pass_filter: bool                    # 是否通过筛选
    signal: Optional[SignalType] = None  # 信号类型
    strength: Optional[SignalStrength] = None  # 信号强度
    score: float = 0.0                  # 评分 0-100
    confidence: float = 0.0             # 置信度 0-1
    reason: str = ""                    # 原因说明
    risk_level: RiskLevel = RiskLevel.MEDIUM
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    details: Dict = None                # 详细信息

class BaseStrategy(ABC):
    """策略基础类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.enabled = True
        self.weight = 1.0  # 策略权重
    
    @abstractmethod
    async def analyze(self, stock_data: Dict, technical_data: Dict) -> StrategyResult:
        """
        分析股票数据，返回策略结果
        
        Args:
            stock_data: 股票基础数据
            technical_data: 技术指标数据
            
        Returns:
            StrategyResult: 策略分析结果
        """
        pass
    
    def is_enabled(self) -> bool:
        """检查策略是否启用"""
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """设置策略启用状态"""
        self.enabled = enabled
    
    def get_config_schema(self) -> Dict:
        """返回策略配置schema"""
        return {}

class DailyStrategy(BaseStrategy):
    """日线级策略基类"""
    pass

class IntradayStrategy(BaseStrategy):
    """分时级策略基类"""
    pass

class RiskStrategy(BaseStrategy):
    """风控策略基类"""
    pass

# 策略注册器
class StrategyRegistry:
    """策略注册管理器"""
    
    def __init__(self):
        self._strategies = {}
        self._daily_strategies = {}
        self._intraday_strategies = {}
        self._risk_strategies = {}
    
    def register(self, strategy: BaseStrategy):
        """注册策略"""
        self._strategies[strategy.name] = strategy
        
        if isinstance(strategy, DailyStrategy):
            self._daily_strategies[strategy.name] = strategy
        elif isinstance(strategy, IntradayStrategy):
            self._intraday_strategies[strategy.name] = strategy
        elif isinstance(strategy, RiskStrategy):
            self._risk_strategies[strategy.name] = strategy
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """获取策略实例"""
        return self._strategies.get(name)
    
    def get_daily_strategies(self) -> Dict[str, DailyStrategy]:
        """获取所有日线策略"""
        return self._daily_strategies
    
    def get_intraday_strategies(self) -> Dict[str, IntradayStrategy]:
        """获取所有分时策略"""
        return self._intraday_strategies
    
    def get_risk_strategies(self) -> Dict[str, RiskStrategy]:
        """获取所有风控策略"""
        return self._risk_strategies
    
    def list_all_strategies(self) -> List[str]:
        """列出所有策略名称"""
        return list(self._strategies.keys())

# 全局注册器实例
strategy_registry = StrategyRegistry()
```

#### ✅ 步骤2：集成到现有服务
```python
# backend/services/advanced_screening_service.py
"""
高级筛选服务
整合所有策略，提供统一的筛选接口
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

from .strategy_base import (
    strategy_registry, StrategyResult, SignalType, 
    SignalStrength, RiskLevel
)
from .technical_indicator_service import get_technical_indicator_service

logger = logging.getLogger(__name__)

class AdvancedScreeningService:
    """高级筛选服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.tech_service = get_technical_indicator_service(db_manager)
        
    async def screen_stocks_advanced(self, 
                                   stock_codes: List[str],
                                   strategy_config: Dict,
                                   screening_date: str = None) -> List[Dict]:
        """
        执行高级股票筛选
        
        Args:
            stock_codes: 股票代码列表
            strategy_config: 策略配置
            screening_date: 筛选日期
            
        Returns:
            筛选结果列表
        """
        if screening_date is None:
            screening_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始高级筛选，股票数量: {len(stock_codes)}")
        
        results = []
        
        # 批量获取技术指标
        logger.info("正在批量计算技术指标...")
        await self.tech_service.batch_calculate_indicators(stock_codes, screening_date)
        
        # 并行处理股票
        tasks = []
        for stock_code in stock_codes:
            task = self._analyze_single_stock(stock_code, strategy_config, screening_date)
            tasks.append(task)
        
        # 执行分析
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                logger.error(f"分析股票失败: {stock_codes[i]}, {result}")
                continue
            
            if result and result['pass_filter']:
                results.append(result)
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 保存结果
        await self._save_screening_results(results, strategy_config, screening_date)
        
        logger.info(f"高级筛选完成，找到 {len(results)} 只符合条件的股票")
        return results
    
    async def _analyze_single_stock(self, 
                                  stock_code: str, 
                                  strategy_config: Dict,
                                  screening_date: str) -> Optional[Dict]:
        """分析单只股票"""
        try:
            # 获取股票基础数据
            stock_data = await self._get_stock_data(stock_code, screening_date)
            if not stock_data:
                return None
            
            # 获取技术指标数据
            technical_data = await self._get_technical_data(stock_code, screening_date)
            if not technical_data:
                return None
            
            # 执行策略分析
            strategy_results = []
            total_score = 0
            total_weight = 0
            
            # 日线策略
            daily_strategies = strategy_registry.get_daily_strategies()
            for name, strategy in daily_strategies.items():
                if not strategy.is_enabled():
                    continue
                
                if name in strategy_config.get('enabled_strategies', []):
                    result = await strategy.analyze(stock_data, technical_data)
                    strategy_results.append({
                        'strategy': name,
                        'result': result
                    })
                    
                    if result.pass_filter:
                        total_score += result.score * strategy.weight
                        total_weight += strategy.weight
            
            # 计算综合评分
            final_score = total_score / total_weight if total_weight > 0 else 0
            
            # 判断是否通过筛选
            min_score = strategy_config.get('min_score', 60)
            pass_filter = final_score >= min_score
            
            if not pass_filter:
                return None
            
            # 生成最终信号
            final_signal = self._generate_final_signal(strategy_results)
            
            return {
                'stock_code': stock_code,
                'stock_name': stock_data.get('stock_name', stock_code),
                'screening_date': screening_date,
                'pass_filter': True,
                'score': final_score,
                'signal': final_signal['signal'],
                'strength': final_signal['strength'],
                'risk_level': final_signal['risk_level'],
                'current_price': stock_data.get('close_price'),
                'strategy_results': strategy_results,
                'technical_data': technical_data
            }
            
        except Exception as e:
            logger.error(f"分析股票失败: {stock_code}, {e}")
            return None
    
    def _generate_final_signal(self, strategy_results: List[Dict]) -> Dict:
        """生成最终信号"""
        buy_signals = []
        sell_signals = []
        hold_signals = []
        
        for sr in strategy_results:
            result = sr['result']
            if result.signal == SignalType.BUY:
                buy_signals.append(result)
            elif result.signal == SignalType.SELL:
                sell_signals.append(result)
            elif result.signal == SignalType.HOLD:
                hold_signals.append(result)
        
        # 简单的信号合成逻辑
        if len(buy_signals) > len(sell_signals):
            strength = SignalStrength.STRONG if len(buy_signals) >= 3 else SignalStrength.MEDIUM
            return {
                'signal': SignalType.BUY.value,
                'strength': strength.value,
                'risk_level': RiskLevel.MEDIUM.value
            }
        elif len(sell_signals) > 0:
            return {
                'signal': SignalType.SELL.value,
                'strength': SignalStrength.MEDIUM.value,
                'risk_level': RiskLevel.HIGH.value
            }
        else:
            return {
                'signal': SignalType.HOLD.value,
                'strength': SignalStrength.WEAK.value,
                'risk_level': RiskLevel.LOW.value
            }
    
    async def _get_stock_data(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取股票基础数据"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM daily_stock_changes
                    WHERE stock_code = ? AND trade_date = ?
                ''', (stock_code, trade_date))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取股票数据失败: {stock_code}, {e}")
            return None
    
    async def _get_technical_data(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取技术指标数据"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM stock_technical_indicators
                    WHERE stock_code = ? AND trade_date = ?
                ''', (stock_code, trade_date))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取技术数据失败: {stock_code}, {e}")
            return None
    
    async def _save_screening_results(self, 
                                    results: List[Dict],
                                    strategy_config: Dict,
                                    screening_date: str):
        """保存筛选结果"""
        import sqlite3
        import json
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for result in results:
                    cursor.execute('''
                        INSERT OR REPLACE INTO advanced_screening_results
                        (stock_code, stock_name, screening_date, strategy_type,
                         signal_type, signal_strength, score, confidence, reason,
                         risk_level, current_price, technical_data, strategies_passed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result['stock_code'],
                        result['stock_name'],
                        screening_date,
                        'advanced_daily',
                        result['signal'],
                        result['strength'],
                        result['score'],
                        0.8,  # 默认置信度
                        f"通过{len(result['strategy_results'])}个策略",
                        result['risk_level'],
                        result['current_price'],
                        json.dumps(result['technical_data']),
                        json.dumps([sr['strategy'] for sr in result['strategy_results']])
                    ))
                
                conn.commit()
                logger.info(f"保存筛选结果成功: {len(results)} 条")
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")

# 全局实例
_advanced_screening_service = None

def get_advanced_screening_service(db_manager):
    """获取高级筛选服务实例"""
    global _advanced_screening_service
    if _advanced_screening_service is None:
        _advanced_screening_service = AdvancedScreeningService(db_manager)
    return _advanced_screening_service
```

### 验收标准
- [ ] 策略基类创建成功
- [ ] 策略注册器工作正常
- [ ] 高级筛选服务集成完成
- [ ] 与现有服务无冲突
- [ ] 基础测试通过

---

## 第1周总结

### 完成情况检查
- [ ] 数据库升级完成
- [ ] 技术指标服务可用
- [ ] 策略框架搭建完成
- [ ] 所有测试通过
- [ ] 文档更新完整

### 下周准备
- 准备实现具体的日线策略
- 策略参数配置准备
- 前端界面升级准备

---

## 注意事项

1. **数据备份**：每次数据库操作前必须备份
2. **测试先行**：每个功能必须有对应测试
3. **文档同步**：代码和文档同步更新
4. **性能监控**：关注计算性能，及时优化
5. **错误处理**：完善错误捕获和日志记录