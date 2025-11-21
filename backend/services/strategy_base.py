"""
策略基础类和接口定义
为高级选股策略提供统一的框架和接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WAIT = "wait"
    ALERT = "alert"

class SignalStrength(Enum):
    """信号强度枚举"""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"

class RiskLevel(Enum):
    """风险等级枚举"""
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
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'pass_filter': self.pass_filter,
            'signal': self.signal.value if self.signal else None,
            'strength': self.strength.value if self.strength else None,
            'score': self.score,
            'confidence': self.confidence,
            'reason': self.reason,
            'risk_level': self.risk_level.value,
            'target_price': self.target_price,
            'stop_loss_price': self.stop_loss_price,
            'details': self.details or {}
        }

class BaseStrategy(ABC):
    """策略基础类"""
    
    def __init__(self, name: str, description: str = "", weight: float = 1.0):
        self.name = name
        self.description = description
        self.enabled = True
        self.weight = weight  # 策略权重
    
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
    
    def set_weight(self, weight: float):
        """设置策略权重"""
        self.weight = max(0.0, min(5.0, weight))  # 限制在0-5范围内
    
    def get_config_schema(self) -> Dict:
        """返回策略配置schema"""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'weight': self.weight,
            'parameters': {}
        }
    
    def get_info(self) -> Dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'weight': self.weight,
            'type': self.__class__.__name__
        }
    
    def update_parameters(self, params: Dict):
        """
        更新策略参数
        
        Args:
            params: 新的参数字典
        """
        logger.info(f"🔧 更新策略 {self.name} 参数: {params}")
        # 默认实现：将参数设置为实例属性
        for key, value in params.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                setattr(self, key, value)
                logger.debug(f"  {key}: {old_value} → {value}")
            else:
                logger.warning(f"策略 {self.name} 不支持参数 {key}")
        return True

class DailyStrategy(BaseStrategy):
    """日线级策略基类"""
    
    def __init__(self, name: str, description: str = "", weight: float = 1.0):
        super().__init__(name, description, weight)
        self.strategy_type = "daily"

class IntradayStrategy(BaseStrategy):
    """分时级策略基类"""
    
    def __init__(self, name: str, description: str = "", weight: float = 1.0):
        super().__init__(name, description, weight)
        self.strategy_type = "intraday"

class RiskStrategy(BaseStrategy):
    """风控策略基类"""
    
    def __init__(self, name: str, description: str = "", weight: float = 1.0):
        super().__init__(name, description, weight)
        self.strategy_type = "risk"

class StrategyRegistry:
    """策略注册管理器"""
    
    def __init__(self):
        self._strategies = {}
        self._daily_strategies = {}
        self._intraday_strategies = {}
        self._risk_strategies = {}
    
    def register(self, strategy: BaseStrategy):
        """注册策略"""
        if not isinstance(strategy, BaseStrategy):
            raise ValueError(f"策略必须继承自BaseStrategy: {type(strategy)}")
        
        self._strategies[strategy.name] = strategy
        
        if isinstance(strategy, DailyStrategy):
            self._daily_strategies[strategy.name] = strategy
            logger.info(f"✅ 注册日线策略: {strategy.name}")
        elif isinstance(strategy, IntradayStrategy):
            self._intraday_strategies[strategy.name] = strategy
            logger.info(f"✅ 注册分时策略: {strategy.name}")
        elif isinstance(strategy, RiskStrategy):
            self._risk_strategies[strategy.name] = strategy
            logger.info(f"✅ 注册风控策略: {strategy.name}")
        else:
            logger.warning(f"⚠️ 未知策略类型: {strategy.name}")
    
    def unregister(self, strategy_name: str):
        """注销策略"""
        if strategy_name in self._strategies:
            strategy = self._strategies.pop(strategy_name)
            
            # 从分类中删除
            if strategy_name in self._daily_strategies:
                self._daily_strategies.pop(strategy_name)
            elif strategy_name in self._intraday_strategies:
                self._intraday_strategies.pop(strategy_name)
            elif strategy_name in self._risk_strategies:
                self._risk_strategies.pop(strategy_name)
            
            logger.info(f"✅ 注销策略: {strategy_name}")
            return True
        return False
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """获取策略实例"""
        return self._strategies.get(name)
    
    def get_daily_strategies(self) -> Dict[str, DailyStrategy]:
        """获取所有日线策略"""
        return self._daily_strategies.copy()
    
    def get_intraday_strategies(self) -> Dict[str, IntradayStrategy]:
        """获取所有分时策略"""
        return self._intraday_strategies.copy()
    
    def get_risk_strategies(self) -> Dict[str, RiskStrategy]:
        """获取所有风控策略"""
        return self._risk_strategies.copy()
    
    def get_enabled_strategies(self, strategy_type: str = None) -> Dict[str, BaseStrategy]:
        """获取启用的策略"""
        if strategy_type == "daily":
            strategies = self._daily_strategies
        elif strategy_type == "intraday":
            strategies = self._intraday_strategies
        elif strategy_type == "risk":
            strategies = self._risk_strategies
        else:
            strategies = self._strategies
        
        return {name: strategy for name, strategy in strategies.items() if strategy.is_enabled()}
    
    def list_all_strategies(self) -> List[str]:
        """列出所有策略名称"""
        return list(self._strategies.keys())
    
    def get_strategy_info(self) -> Dict:
        """获取所有策略信息"""
        return {
            'total': len(self._strategies),
            'daily': len(self._daily_strategies),
            'intraday': len(self._intraday_strategies),
            'risk': len(self._risk_strategies),
            'enabled': len([s for s in self._strategies.values() if s.is_enabled()]),
            'strategies': {name: strategy.get_info() for name, strategy in self._strategies.items()}
        }
    
    def set_strategy_enabled(self, name: str, enabled: bool) -> bool:
        """设置策略启用状态"""
        strategy = self.get_strategy(name)
        if strategy:
            strategy.set_enabled(enabled)
            logger.info(f"✅ 策略 {name} {'启用' if enabled else '禁用'}")
            return True
        return False
    
    def set_strategy_weight(self, name: str, weight: float) -> bool:
        """设置策略权重"""
        strategy = self.get_strategy(name)
        if strategy:
            strategy.set_weight(weight)
            logger.info(f"✅ 策略 {name} 权重设置为 {weight}")
            return True
        return False

# 全局注册器实例
strategy_registry = StrategyRegistry()

def register_strategy(strategy: BaseStrategy):
    """注册策略的便捷函数"""
    strategy_registry.register(strategy)

def get_strategy_registry() -> StrategyRegistry:
    """获取策略注册器"""
    return strategy_registry

# 策略装饰器
def daily_strategy(name: str, description: str = "", weight: float = 1.0):
    """日线策略装饰器"""
    def decorator(cls):
        if not issubclass(cls, DailyStrategy):
            # 动态创建继承自DailyStrategy的类
            class WrappedStrategy(cls, DailyStrategy):
                def __init__(self):
                    DailyStrategy.__init__(self, name, description, weight)
                    if hasattr(cls, '__init__'):
                        cls.__init__(self)
            
            WrappedStrategy.__name__ = cls.__name__
            WrappedStrategy.__qualname__ = cls.__qualname__
            return WrappedStrategy
        return cls
    return decorator

def intraday_strategy(name: str, description: str = "", weight: float = 1.0):
    """分时策略装饰器"""
    def decorator(cls):
        if not issubclass(cls, IntradayStrategy):
            class WrappedStrategy(cls, IntradayStrategy):
                def __init__(self):
                    IntradayStrategy.__init__(self, name, description, weight)
                    if hasattr(cls, '__init__'):
                        cls.__init__(self)
            
            WrappedStrategy.__name__ = cls.__name__
            WrappedStrategy.__qualname__ = cls.__qualname__
            return WrappedStrategy
        return cls
    return decorator

def risk_strategy(name: str, description: str = "", weight: float = 1.0):
    """风控策略装饰器"""
    def decorator(cls):
        if not issubclass(cls, RiskStrategy):
            class WrappedStrategy(cls, RiskStrategy):
                def __init__(self):
                    RiskStrategy.__init__(self, name, description, weight)
                    if hasattr(cls, '__init__'):
                        cls.__init__(self)
            
            WrappedStrategy.__name__ = cls.__name__
            WrappedStrategy.__qualname__ = cls.__qualname__
            return WrappedStrategy
        return cls
    return decorator

# 便捷函数
def get_all_strategies() -> Dict[str, BaseStrategy]:
    """获取所有注册的策略"""
    return strategy_registry._strategies.copy()

def get_strategy(name: str) -> Optional[BaseStrategy]:
    """根据名称获取策略"""
    return strategy_registry.get_strategy(name)
