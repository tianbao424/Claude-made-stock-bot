"""
量价关系策略实现
包含4个基于量价关系的选股策略
"""
from ..strategy_base import DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel
import logging

logger = logging.getLogger(__name__)

class VolumeRatioStrategy(DailyStrategy):
    """
    量比选股策略
    - 量比<0.5 且 创新高 → 买入信号（缩量新高）
    - 涨停且量比<1 → 次日高概率涨停
    - 突破20日均线后缩量回调 → 买入机会
    """
    
    def __init__(self):
        super().__init__(
            name="volume_ratio_strategy",
            description="基于量比的多维度选股策略",
            weight=1.5  # 重要策略
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        volume_ratio = technical_data.get('volume_ratio')
        is_new_high = technical_data.get('is_new_high', False)
        is_limit_up = technical_data.get('is_limit_up', False)
        close_price = stock_data.get('close_price', 0)
        ma20 = technical_data.get('ma20', 0)
        ma5 = technical_data.get('ma5', 0)
        
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
        
        # 策略1：缩量新高 - 最强信号
        if volume_ratio < 0.5 and is_new_high:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG,
                score=95,
                confidence=0.95,
                reason=f"缩量新高(量比{volume_ratio:.2f})，主力高度控盘，后市看涨",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.1,  # 目标涨幅10%
                details={
                    'volume_ratio': volume_ratio,
                    'is_new_high': is_new_high,
                    'pattern': 'shrink_volume_new_high'
                }
            )
        
        # 策略2：缩量涨停
        if is_limit_up and volume_ratio < 1.0:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.STRONG,
                score=90,
                confidence=0.85,
                reason=f"缩量涨停(量比{volume_ratio:.2f})，惜售明显，次日大概率继续涨停",
                risk_level=RiskLevel.MEDIUM,
                details={
                    'volume_ratio': volume_ratio,
                    'is_limit_up': is_limit_up,
                    'pattern': 'shrink_volume_limit_up'
                }
            )
        
        # 策略3：突破均线后缩量回调
        if ma20 > 0 and close_price > ma20:
            # 检查是否刚突破后回调
            price_above_ma20_ratio = (close_price - ma20) / ma20
            if 0 < price_above_ma20_ratio < 0.03 and volume_ratio < 0.8:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    score=85,
                    confidence=0.8,
                    reason=f"突破20日均线后缩量回调(量比{volume_ratio:.2f})，买入良机",
                    risk_level=RiskLevel.LOW,
                    stop_loss_price=ma20 * 0.98,  # 止损设在均线下方2%
                    details={
                        'volume_ratio': volume_ratio,
                        'above_ma20': price_above_ma20_ratio,
                        'pattern': 'ma_breakout_pullback'
                    }
                )
        
        # 量比异常判断
        if volume_ratio > 5.0:
            # 巨量，可能是出货
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.STRONG,
                score=15,
                confidence=0.8,
                reason=f"量比{volume_ratio:.2f}异常放大，疑似主力出货",
                risk_level=RiskLevel.HIGH,
                details={'volume_ratio': volume_ratio, 'pattern': 'huge_volume'}
            )
        elif volume_ratio > 3.0:
            # 放量，需要具体分析
            if stock_data.get('change_percent', 0) > 5:
                # 放量上涨
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.HOLD,
                    strength=SignalStrength.MEDIUM,
                    score=65,
                    confidence=0.7,
                    reason=f"放量上涨(量比{volume_ratio:.2f})，关注后续走势",
                    risk_level=RiskLevel.MEDIUM,
                    details={'volume_ratio': volume_ratio, 'pattern': 'volume_rise'}
                )
            else:
                # 放量不涨，不好
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=30,
                    confidence=0.7,
                    reason=f"放量滞涨(量比{volume_ratio:.2f})，上方压力大",
                    risk_level=RiskLevel.HIGH,
                    details={'volume_ratio': volume_ratio, 'pattern': 'volume_stagnation'}
                )
        
        # 正常量比
        score = 70 + (1 - abs(volume_ratio - 1)) * 20  # 量比越接近1分数越高
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            score=max(50, min(80, score)),
            confidence=0.6,
            reason=f"量比{volume_ratio:.2f}正常，无明显信号",
            risk_level=RiskLevel.MEDIUM,
            details={'volume_ratio': volume_ratio, 'pattern': 'normal'}
        )


class VolumePriceRelation(DailyStrategy):
    """
    量价关系策略
    - 缩量上涨 → 强势
    - 缩量下跌 → 仍弱
    - 放量滞涨 → 头部信号
    """
    
    def __init__(self):
        super().__init__(
            name="volume_price_relation",
            description="分析量价配合关系，判断趋势强弱",
            weight=1.3
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        change_percent = stock_data.get('change_percent', 0)
        close_price = stock_data.get('close_price', 0)
        ma5 = technical_data.get('ma5', 0)
        ma20 = technical_data.get('ma20', 0)
        
        # 判断价格变化
        is_rising = change_percent > 0.5
        is_falling = change_percent < -0.5
        is_flat = abs(change_percent) <= 0.5
        
        # 判断成交量变化
        is_shrink_volume = volume_ratio < 0.8
        is_normal_volume = 0.8 <= volume_ratio <= 1.5
        is_heavy_volume = volume_ratio > 1.5
        
        # 缩量上涨 - 最强势
        if is_rising and is_shrink_volume:
            # 进一步判断趋势
            if ma5 > ma20 and close_price > ma5:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=92,
                    confidence=0.9,
                    reason=f"缩量上涨(涨{change_percent:.1f}%,量比{volume_ratio:.2f})，上升趋势强势",
                    risk_level=RiskLevel.LOW,
                    details={
                        'pattern': 'shrink_volume_rise',
                        'trend': 'strong_uptrend'
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.HOLD,
                    strength=SignalStrength.MEDIUM,
                    score=75,
                    confidence=0.8,
                    reason=f"缩量上涨但趋势不明确，持有观察",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'shrink_volume_rise'}
                )
        
        # 放量滞涨 - 头部信号
        if is_flat and is_heavy_volume:
            # 检查位置
            if technical_data.get('is_new_high', False):
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    score=20,
                    confidence=0.85,
                    reason=f"高位放量滞涨(量比{volume_ratio:.2f})，疑似头部",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'pattern': 'volume_stagnation_top',
                        'volume_ratio': volume_ratio
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=40,
                    confidence=0.7,
                    reason=f"放量滞涨，上方压力较大",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'volume_stagnation'}
                )
        
        # 缩量下跌 - 杀跌动能不足
        if is_falling and is_shrink_volume:
            # 检查支撑位
            if close_price > ma20 * 0.98:  # 接近20日均线
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    score=70,
                    confidence=0.75,
                    reason=f"缩量下跌接近支撑，可能企稳",
                    risk_level=RiskLevel.MEDIUM,
                    stop_loss_price=ma20 * 0.95,
                    details={
                        'pattern': 'shrink_volume_fall_support',
                        'support': ma20
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=30,
                    confidence=0.7,
                    reason=f"缩量下跌但仍然偏弱",
                    risk_level=RiskLevel.HIGH,
                    details={'pattern': 'shrink_volume_fall'}
                )
        
        # 放量上涨 - 正常突破
        if is_rising and is_heavy_volume:
            if change_percent > 5:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    score=80,
                    confidence=0.8,
                    reason=f"放量大涨{change_percent:.1f}%，突破有效",
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        'pattern': 'volume_breakout',
                        'change': change_percent
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.HOLD,
                    strength=SignalStrength.WEAK,
                    score=65,
                    confidence=0.7,
                    reason=f"温和放量上涨，持续观察",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'normal_volume_rise'}
                )
        
        # 其他情况
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            score=60,
            confidence=0.6,
            reason=f"量价关系正常，无特殊信号",
            risk_level=RiskLevel.MEDIUM,
            details={
                'volume_ratio': volume_ratio,
                'change_percent': change_percent
            }
        )


class VolumeTrendAnalysis(DailyStrategy):
    """
    量能趋势分析策略
    分析成交量的变化趋势，判断资金动向
    """
    
    def __init__(self):
        super().__init__(
            name="volume_trend_analysis",
            description="通过量能趋势判断资金流向",
            weight=1.1
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        volume = stock_data.get('volume', 0)
        avg_volume_5d = technical_data.get('avg_volume_5d', 0)
        avg_volume_20d = technical_data.get('avg_volume_20d', 0)
        change_percent = stock_data.get('change_percent', 0)
        
        if not avg_volume_5d or not avg_volume_20d:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少历史成交量数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 计算量能趋势
        volume_trend_short = avg_volume_5d / avg_volume_20d
        current_vs_avg5 = volume / avg_volume_5d if avg_volume_5d > 0 else 0
        
        # 量能持续放大 - 资金持续流入
        if volume_trend_short > 1.5 and current_vs_avg5 > 1.2:
            if change_percent > 0:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=88,
                    confidence=0.85,
                    reason="量能持续放大，资金积极流入，趋势向好",
                    risk_level=RiskLevel.LOW,
                    details={
                        'volume_trend': volume_trend_short,
                        'current_ratio': current_vs_avg5,
                        'pattern': 'continuous_volume_increase'
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=35,
                    confidence=0.7,
                    reason="量能放大但股价不涨，可能有分歧",
                    risk_level=RiskLevel.HIGH,
                    details={'pattern': 'volume_price_divergence'}
                )
        
        # 量能持续萎缩 - 观望情绪浓
        elif volume_trend_short < 0.7 and current_vs_avg5 < 0.8:
            if change_percent < -3:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    score=25,
                    confidence=0.75,
                    reason="量能持续萎缩且下跌，趋势转弱",
                    risk_level=RiskLevel.HIGH,
                    details={'pattern': 'volume_shrink_decline'}
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.WEAK,
                    score=55,
                    confidence=0.6,
                    reason="量能萎缩，市场观望",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'volume_shrink_sideways'}
                )
        
        # 量能平稳
        else:
            score = 70 + (volume_trend_short - 1) * 20
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=max(60, min(80, score)),
                confidence=0.7,
                reason="量能相对平稳，趋势延续",
                risk_level=RiskLevel.MEDIUM,
                details={
                    'volume_trend': volume_trend_short,
                    'pattern': 'stable_volume'
                }
            )


class LowVolumeLowPrice(DailyStrategy):
    """
    地量地价策略
    在下跌末期寻找地量地价的企稳信号
    """
    
    def __init__(self):
        super().__init__(
            name="low_volume_low_price",
            description="识别地量地价的反转机会",
            weight=1.2
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        close_price = stock_data.get('close_price', 0)
        ma60 = technical_data.get('ma60', 0)
        change_percent = stock_data.get('change_percent', 0)
        
        # 判断是否处于相对低位（使用MA60作为参考）
        if not ma60 or ma60 <= 0:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少长期均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        price_position = close_price / ma60
        
        # 地量判断（成交量极度萎缩）
        is_extreme_low_volume = volume_ratio < 0.3
        is_low_volume = volume_ratio < 0.5
        
        # 地价判断（价格处于低位）
        is_low_price = price_position < 0.8  # 低于60日均线20%
        
        # 地量地价 + 止跌信号
        if is_extreme_low_volume and is_low_price:
            if change_percent >= 0:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=85,
                    confidence=0.8,
                    reason=f"地量地价止跌(量比{volume_ratio:.2f}，价位{price_position:.2f})，底部信号",
                    risk_level=RiskLevel.LOW,
                    target_price=close_price * 1.15,
                    details={
                        'volume_ratio': volume_ratio,
                        'price_position': price_position,
                        'pattern': 'bottom_signal'
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=65,
                    confidence=0.7,
                    reason="地量地价但仍在下跌，继续观察",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'potential_bottom'}
                )
        
        # 低量但不是低价
        elif is_low_volume and not is_low_price:
            if price_position > 1.2:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    score=30,
                    confidence=0.75,
                    reason="高位缩量，动能不足",
                    risk_level=RiskLevel.HIGH,
                    details={'pattern': 'high_position_shrink'}
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.HOLD,
                    strength=SignalStrength.WEAK,
                    score=60,
                    confidence=0.6,
                    reason="缩量横盘整理",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'consolidation'}
                )
        
        # 正常情况
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            score=65,
            confidence=0.6,
            reason="量价关系正常",
            risk_level=RiskLevel.MEDIUM,
            details={
                'volume_ratio': volume_ratio,
                'price_position': price_position
            }
        )