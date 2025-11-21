"""
演示策略实现
用于测试策略框架的基本功能
"""
from .strategy_base import (
    DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel,
    register_strategy
)

class LowPriceFilterStrategy(DailyStrategy):
    """低价股过滤策略 - 仅针对普通股票"""
    
    def __init__(self, price_threshold: float = 6.0):
        super().__init__(
            name="low_price_filter",
            description="过滤低于指定价格的普通股票，避免垃圾股风险",
            weight=1.0
        )
        self.price_threshold = price_threshold
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        """分析股票是否符合价格要求"""
        close_price = stock_data.get('close_price', 0)
        industry = stock_data.get('industry', '')
        stock_name = stock_data.get('name', '')
        
        # 判断是否为银行股，银行股交给银行低价股策略处理
        is_bank = ('银行' in industry or '银行' in stock_name or 
                  any(keyword in stock_name for keyword in ['银行', '农商', '村镇银行', '信用社']))
        
        if is_bank:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.9,
                reason="银行股请使用专门的银行低价股策略",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 普通股价格检查
        if close_price < self.price_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.9,
                reason=f"股价{close_price:.2f}元低于{self.price_threshold}元阈值",
                risk_level=RiskLevel.HIGH
            )
        else:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                score=75,
                confidence=0.8,
                reason=f"股价{close_price:.2f}元符合要求",
                risk_level=RiskLevel.LOW
            )

class BankLowPriceFilterStrategy(DailyStrategy):
    """银行低价股过滤策略 - 专门针对银行股"""
    
    def __init__(self, price_threshold: float = 3.5):
        super().__init__(
            name="bank_low_price_filter",
            description="专门针对银行股的低价过滤策略",
            weight=1.2
        )
        self.price_threshold = price_threshold
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        """分析银行股是否符合价格要求"""
        close_price = stock_data.get('close_price', 0)
        industry = stock_data.get('industry', '')
        stock_name = stock_data.get('name', '')
        
        # 检查是否为银行股
        is_bank = ('银行' in industry or '银行' in stock_name or 
                  any(keyword in stock_name for keyword in ['银行', '农商', '村镇银行', '信用社']))
        
        if not is_bank:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.9,
                reason="非银行股，请使用普通低价股策略",
                risk_level=RiskLevel.MEDIUM
            )
        
        if close_price < self.price_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.8,
                reason=f"银行股价{close_price:.2f}元低于{self.price_threshold}元阈值",
                risk_level=RiskLevel.HIGH
            )
        else:
            # 银行股估值相对较低，给予更高评分
            score = 80 if close_price < 5.0 else 75
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                score=score,
                confidence=0.8,
                reason=f"银行股价{close_price:.2f}元符合要求，估值相对较低",
                risk_level=RiskLevel.LOW
            )

class MADeviationStrategy(DailyStrategy):
    """均线偏离策略 - 演示策略"""
    
    def __init__(self, deviation_threshold: float = 1.2):
        super().__init__(
            name="ma_deviation",
            description="检测股价相对20日均线的偏离度",
            weight=1.5
        )
        self.deviation_threshold = deviation_threshold
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        """分析股价相对均线的偏离"""
        close_price = stock_data.get('close_price', 0)
        ma20 = technical_data.get('ma20', 0)
        
        if not ma20 or ma20 <= 0:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.5,
                reason="缺少20日均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        deviation = close_price / ma20
        
        if deviation > self.deviation_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.MEDIUM,
                score=30,
                confidence=0.7,
                reason=f"股价偏离20日均线{(deviation-1)*100:.1f}%，建议等待回调",
                risk_level=RiskLevel.HIGH,
                details={'deviation': deviation, 'ma20': ma20}
            )
        else:
            score = 85 - (deviation - 1) * 50  # 偏离越小分数越高
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG if deviation < 1.1 else SignalStrength.MEDIUM,
                score=max(60, score),
                confidence=0.8,
                reason=f"股价相对20日均线偏离{(deviation-1)*100:.1f}%，适合买入",
                risk_level=RiskLevel.LOW,
                details={'deviation': deviation, 'ma20': ma20}
            )

class VolumeRatioStrategy(DailyStrategy):
    """量比策略 - 演示策略"""
    
    def __init__(self):
        super().__init__(
            name="volume_ratio",
            description="基于量比的选股策略",
            weight=1.2
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        """分析量比信号"""
        volume_ratio = technical_data.get('volume_ratio')
        is_new_high = technical_data.get('is_new_high', False)
        is_limit_up = technical_data.get('is_limit_up', False)
        
        if volume_ratio is None:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少量比数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 缩量新高
        if volume_ratio < 0.5 and is_new_high:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG,
                score=90,
                confidence=0.9,
                reason=f"缩量新高(量比{volume_ratio:.2f})，主力控盘良好",
                risk_level=RiskLevel.LOW,
                details={'volume_ratio': volume_ratio, 'is_new_high': is_new_high}
            )
        
        # 缩量涨停
        elif is_limit_up and volume_ratio < 1.0:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.STRONG,
                score=85,
                confidence=0.8,
                reason=f"缩量涨停(量比{volume_ratio:.2f})，次日大概率继续涨停",
                risk_level=RiskLevel.MEDIUM,
                details={'volume_ratio': volume_ratio, 'is_limit_up': is_limit_up}
            )
        
        # 量比过高
        elif volume_ratio > 5.0:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                score=20,
                confidence=0.7,
                reason=f"量比过高({volume_ratio:.2f})，可能存在出货",
                risk_level=RiskLevel.HIGH,
                details={'volume_ratio': volume_ratio}
            )
        
        # 正常量比
        else:
            score = 60 + (2 - volume_ratio) * 10  # 量比越接近1-2分数越高
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=max(40, min(80, score)),
                confidence=0.6,
                reason=f"量比{volume_ratio:.2f}，正常范围",
                risk_level=RiskLevel.MEDIUM,
                details={'volume_ratio': volume_ratio}
            )

def register_demo_strategies():
    """注册演示策略"""
    # 创建策略实例
    low_price_filter = LowPriceFilterStrategy(price_threshold=6.0)
    bank_low_price_filter = BankLowPriceFilterStrategy(price_threshold=3.5)
    ma_deviation = MADeviationStrategy(deviation_threshold=1.2)
    volume_ratio = VolumeRatioStrategy()
    
    # 注册策略
    register_strategy(low_price_filter)
    register_strategy(bank_low_price_filter)
    register_strategy(ma_deviation)
    register_strategy(volume_ratio)
    
    return {
        'low_price_filter': low_price_filter,
        'bank_low_price_filter': bank_low_price_filter,
        'ma_deviation': ma_deviation,
        'volume_ratio': volume_ratio
    }