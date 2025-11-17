"""
策略模块初始化
注册所有可用的策略
"""
from ..strategy_base import register_strategy
from .basic_filter_strategies import (
    LowPriceFilter,
    HighPositionNewsFilter,
    MADeviationFilter,
    GapUpFilter,
    TurnoverFilter
)
from .volume_price_strategies import (
    VolumeRatioStrategy,
    VolumePriceRelation,
    VolumeTrendAnalysis,
    LowVolumeLowPrice
)
from .trend_following_strategies import (
    MAGoldenCross,
    TrendMomentum,
    TrendReversal
)
from .pattern_recognition_strategies import (
    SupportResistanceStrategy,
    BreakoutStrategy,
    VolumePatternStrategy
)
from .comprehensive_strategy import ComprehensiveAnalysis

def register_basic_filter_strategies():
    """注册基础过滤策略"""
    strategies = [
        LowPriceFilter(),
        HighPositionNewsFilter(),
        MADeviationFilter(), 
        GapUpFilter(),
        TurnoverFilter()
    ]
    
    for strategy in strategies:
        register_strategy(strategy)
    
    return strategies

def register_volume_price_strategies():
    """注册量价关系策略"""
    strategies = [
        VolumeRatioStrategy(),
        VolumePriceRelation(),
        VolumeTrendAnalysis(),
        LowVolumeLowPrice()
    ]
    
    for strategy in strategies:
        register_strategy(strategy)
    
    return strategies

def register_trend_following_strategies():
    """注册趋势跟随策略"""
    strategies = [
        MAGoldenCross(),
        TrendMomentum(),
        TrendReversal()
    ]
    
    for strategy in strategies:
        register_strategy(strategy)
    
    return strategies

def register_pattern_recognition_strategies():
    """注册技术形态识别策略"""
    strategies = [
        SupportResistanceStrategy(),
        BreakoutStrategy(),
        VolumePatternStrategy()
    ]
    
    for strategy in strategies:
        register_strategy(strategy)
    
    return strategies

def register_comprehensive_strategy():
    """注册综合判断策略"""
    strategy = ComprehensiveAnalysis()
    register_strategy(strategy)
    return [strategy]

def register_all_daily_strategies():
    """注册所有日线策略"""
    basic_strategies = register_basic_filter_strategies()
    volume_strategies = register_volume_price_strategies()
    trend_strategies = register_trend_following_strategies()
    pattern_strategies = register_pattern_recognition_strategies()
    comprehensive_strategies = register_comprehensive_strategy()
    
    all_strategies = basic_strategies + volume_strategies + trend_strategies + pattern_strategies + comprehensive_strategies
    
    print(f"✅ 注册了 {len(all_strategies)} 个日线策略:")
    for strategy in all_strategies:
        print(f"  - {strategy.name}: {strategy.description}")
    
    return all_strategies

# 自动注册所有策略
def auto_register():
    """自动注册所有策略"""
    return register_all_daily_strategies()

# 策略列表
AVAILABLE_STRATEGIES = {
    'basic_filter': [
        'low_price_filter',
        'high_position_news_filter', 
        'ma_deviation_filter',
        'gap_up_filter',
        'turnover_filter'
    ],
    'volume_price': [
        'volume_ratio_strategy',
        'volume_price_relation',
        'volume_trend_analysis',
        'low_volume_low_price'
    ],
    'trend_following': [
        'ma_golden_cross',
        'trend_momentum',
        'trend_reversal'
    ],
    'pattern_recognition': [
        'support_resistance',
        'breakout_strategy',
        'volume_pattern'
    ],
    'comprehensive': [
        'comprehensive_analysis'
    ]
}