"""
技术形态识别策略实现
包含3个基于技术形态的选股策略
"""
from ..strategy_base import DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel
import logging

logger = logging.getLogger(__name__)

class SupportResistanceStrategy(DailyStrategy):
    """
    支撑阻力策略
    - 在关键支撑位获得支撑 → 买入信号
    - 突破关键阻力位 → 追涨信号  
    - 假突破后快速回落 → 卖出信号
    """
    
    def __init__(self):
        super().__init__(
            name="support_resistance",
            description="基于支撑阻力位的买卖信号",
            weight=1.3
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        high_price = stock_data.get('high_price', close_price)
        low_price = stock_data.get('low_price', close_price)
        change_percent = stock_data.get('change_percent', 0)
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        
        if not ma20 or not ma60:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少均线数据用于确定支撑阻力",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 使用均线作为关键支撑阻力位
        support_levels = [ma20, ma60]
        resistance_levels = [ma20 * 1.05, ma60 * 1.1]
        
        # 计算价格相对位置
        price_vs_ma20 = close_price / ma20
        price_vs_ma60 = close_price / ma60
        
        # 检查是否在支撑位获得支撑
        for i, support in enumerate(support_levels):
            support_tolerance = support * 0.02  # 2%容忍度
            
            # 价格接近支撑位且获得支撑
            if abs(close_price - support) <= support_tolerance and low_price <= support and close_price > support:
                support_name = "MA20" if i == 0 else "MA60"
                
                # 检查成交量确认
                volume_confirmed = volume_ratio > 0.8
                
                # 计算支撑强度
                support_strength = "强" if close_price > support * 1.01 else "中"
                
                score = 85 if volume_confirmed else 75
                confidence = 0.85 if volume_confirmed else 0.75
                
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG if volume_confirmed else SignalStrength.MEDIUM,
                    score=score,
                    confidence=confidence,
                    reason=f"在{support_name}支撑位({support:.2f})获得{support_strength}支撑",
                    risk_level=RiskLevel.LOW,
                    target_price=close_price * 1.08,
                    stop_loss_price=support * 0.97,
                    details={
                        'pattern': 'support_hold',
                        'support_level': support,
                        'support_name': support_name,
                        'distance_to_support': (close_price - support) / support,
                        'volume_confirmation': volume_confirmed
                    }
                )
        
        # 检查阻力位突破
        for i, resistance in enumerate(resistance_levels):
            resistance_name = "MA20+5%" if i == 0 else "MA60+10%"
            
            # 突破阻力位
            if close_price > resistance and high_price > resistance * 1.01:
                # 检查是否有效突破（成交量配合）
                if volume_ratio > 1.5 and change_percent > 3:
                    return StrategyResult(
                        pass_filter=True,
                        signal=SignalType.BUY,
                        strength=SignalStrength.STRONG,
                        score=88,
                        confidence=0.9,
                        reason=f"有效突破{resistance_name}阻力位({resistance:.2f})",
                        risk_level=RiskLevel.LOW,
                        target_price=close_price * 1.1,
                        stop_loss_price=resistance * 0.98,
                        details={
                            'pattern': 'resistance_breakout',
                            'resistance_level': resistance,
                            'resistance_name': resistance_name,
                            'breakout_strength': 'strong',
                            'volume_confirmation': True
                        }
                    )
                else:
                    # 可能是假突破
                    return StrategyResult(
                        pass_filter=False,
                        signal=SignalType.WAIT,
                        strength=SignalStrength.MEDIUM,
                        score=45,
                        confidence=0.7,
                        reason=f"突破{resistance_name}但量能不足，疑似假突破",
                        risk_level=RiskLevel.MEDIUM,
                        details={
                            'pattern': 'weak_breakout',
                            'resistance_level': resistance,
                            'volume_ratio': volume_ratio
                        }
                    )
        
        # 检查是否跌破支撑
        for i, support in enumerate(support_levels):
            support_name = "MA20" if i == 0 else "MA60"
            
            if close_price < support * 0.98 and low_price < support * 0.97:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    score=20,
                    confidence=0.85,
                    reason=f"跌破{support_name}关键支撑位({support:.2f})",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'pattern': 'support_break',
                        'support_level': support,
                        'support_name': support_name
                    }
                )
        
        # 在支撑阻力区间内
        if ma20 <= close_price <= ma20 * 1.05:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=65,
                confidence=0.7,
                reason="在支撑阻力区间内震荡",
                risk_level=RiskLevel.MEDIUM,
                details={
                    'pattern': 'range_bound',
                    'support': ma20,
                    'resistance': ma20 * 1.05
                }
            )
        
        # 其他情况
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            score=60,
            confidence=0.6,
            reason="无明显支撑阻力信号",
            risk_level=RiskLevel.MEDIUM,
            details={'price_vs_ma20': price_vs_ma20, 'price_vs_ma60': price_vs_ma60}
        )


class BreakoutStrategy(DailyStrategy):
    """
    突破策略
    - 箱体突破 → 追涨信号
    - 平台整理后突破 → 强势信号
    - 缩量盘整后放量突破 → 最佳买点
    """
    
    def __init__(self):
        super().__init__(
            name="breakout_strategy",
            description="识别各种突破形态的买入机会",
            weight=1.4
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        high_price = stock_data.get('high_price', close_price)
        change_percent = stock_data.get('change_percent', 0)
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        is_new_high = technical_data.get('is_new_high', False)
        
        if not ma5 or not ma20:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 判断是否处于整理状态（MA5和MA20相近）
        ma_convergence = abs(ma5 - ma20) / ma20
        is_consolidating = ma_convergence < 0.03  # 3%以内算整理
        
        # 策略1：放量创新高突破
        if is_new_high and volume_ratio > 1.8 and change_percent > 5:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG,
                score=92,
                confidence=0.95,
                reason=f"放量创新高突破(涨{change_percent:.1f}%，量比{volume_ratio:.1f})",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.15,
                stop_loss_price=close_price * 0.92,
                details={
                    'pattern': 'volume_new_high_breakout',
                    'volume_ratio': volume_ratio,
                    'change_percent': change_percent,
                    'is_new_high': is_new_high
                }
            )
        
        # 策略2：平台整理后突破
        if is_consolidating and change_percent > 4 and volume_ratio > 1.3:
            # 判断突破方向
            price_above_mas = close_price > max(ma5, ma20)
            
            if price_above_mas:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=88,
                    confidence=0.9,
                    reason=f"平台整理后向上突破(涨{change_percent:.1f}%)",
                    risk_level=RiskLevel.LOW,
                    target_price=close_price * 1.12,
                    stop_loss_price=max(ma5, ma20) * 0.98,
                    details={
                        'pattern': 'platform_breakout_up',
                        'consolidation_level': max(ma5, ma20),
                        'ma_convergence': ma_convergence
                    }
                )
            else:
                # 向下突破
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    score=15,
                    confidence=0.85,
                    reason=f"平台整理后向下突破(跌{abs(change_percent):.1f}%)",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'pattern': 'platform_breakout_down',
                        'consolidation_level': min(ma5, ma20)
                    }
                )
        
        # 策略3：箱体突破判断
        box_top = ma20 * 1.05  # 以MA20+5%作为箱体上沿
        box_bottom = ma20 * 0.95  # 以MA20-5%作为箱体下沿
        
        # 突破箱体上沿
        if close_price > box_top and high_price > box_top:
            if volume_ratio > 1.2:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    score=82,
                    confidence=0.8,
                    reason=f"突破箱体上沿{box_top:.2f}",
                    risk_level=RiskLevel.LOW,
                    target_price=close_price * 1.08,
                    stop_loss_price=box_top * 0.98,
                    details={
                        'pattern': 'box_breakout_up',
                        'box_top': box_top,
                        'box_bottom': box_bottom
                    }
                )
            else:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=50,
                    confidence=0.6,
                    reason="突破箱体但成交量不足",
                    risk_level=RiskLevel.MEDIUM,
                    details={'pattern': 'weak_box_breakout'}
                )
        
        # 跌破箱体下沿
        elif close_price < box_bottom:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                score=30,
                confidence=0.75,
                reason=f"跌破箱体下沿{box_bottom:.2f}",
                risk_level=RiskLevel.HIGH,
                details={
                    'pattern': 'box_breakdown',
                    'box_bottom': box_bottom
                }
            )
        
        # 在箱体内震荡
        elif box_bottom <= close_price <= box_top:
            # 判断在箱体内的位置
            box_position = (close_price - box_bottom) / (box_top - box_bottom)
            
            if box_position > 0.8:  # 接近箱体上沿
                signal = SignalType.WAIT
                score = 65
                reason = "接近箱体上沿，等待突破"
            elif box_position < 0.2:  # 接近箱体下沿
                signal = SignalType.BUY
                score = 75
                reason = "接近箱体下沿，反弹机会"
            else:  # 箱体中部
                signal = SignalType.HOLD
                score = 60
                reason = "箱体内震荡"
            
            return StrategyResult(
                pass_filter=True,
                signal=signal,
                strength=SignalStrength.WEAK,
                score=score,
                confidence=0.7,
                reason=reason,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'pattern': 'box_range',
                    'box_position': box_position,
                    'box_top': box_top,
                    'box_bottom': box_bottom
                }
            )
        
        # 其他情况
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            score=55,
            confidence=0.6,
            reason="无明显突破信号",
            risk_level=RiskLevel.MEDIUM,
            details={'ma_convergence': ma_convergence}
        )


class VolumePatternStrategy(DailyStrategy):
    """
    量价配合形态策略
    - 堆量上涨 → 持续看多
    - 缩量回调 → 健康调整  
    - 放量滞涨 → 谨慎观望
    """
    
    def __init__(self):
        super().__init__(
            name="volume_pattern",
            description="基于量价配合形态的趋势判断",
            weight=1.2
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        change_percent = stock_data.get('change_percent', 0)
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        avg_volume_5d = technical_data.get('avg_volume_5d', 0)
        avg_volume_20d = technical_data.get('avg_volume_20d', 0)
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        
        if not avg_volume_5d or not avg_volume_20d or not ma5 or not ma20:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少成交量或均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 计算量能趋势
        volume_trend = avg_volume_5d / avg_volume_20d
        price_trend = ma5 / ma20
        
        # 判断价格趋势方向
        is_uptrend = price_trend > 1.02
        is_downtrend = price_trend < 0.98
        is_sideways = 0.98 <= price_trend <= 1.02
        
        # 策略1：堆量上涨形态
        if is_uptrend and volume_trend > 1.2 and volume_ratio > 1.0:
            # 持续放量上涨，健康的上升趋势
            pattern_strength = "强" if volume_ratio > 1.5 else "中"
            
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG if volume_ratio > 1.5 else SignalStrength.MEDIUM,
                score=90 if volume_ratio > 1.5 else 80,
                confidence=0.9,
                reason=f"堆量上涨形态({pattern_strength}势)，量价配合良好",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.12,
                details={
                    'pattern': 'volume_accumulation_up',
                    'volume_trend': volume_trend,
                    'price_trend': price_trend,
                    'pattern_strength': pattern_strength
                }
            )
        
        # 策略2：缩量回调形态
        elif is_uptrend and change_percent < 0 and volume_ratio < 0.8:
            # 上升趋势中的缩量回调，健康调整
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                score=78,
                confidence=0.8,
                reason=f"上升趋势中缩量回调(量比{volume_ratio:.2f})，健康调整",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.08,
                stop_loss_price=ma20 * 0.98,
                details={
                    'pattern': 'healthy_pullback',
                    'volume_ratio': volume_ratio,
                    'in_uptrend': True
                }
            )
        
        # 策略3：放量滞涨形态
        elif abs(change_percent) < 2 and volume_ratio > 2.0:
            # 成交量放大但价格涨幅有限
            if close_price > ma20:
                # 高位放量滞涨，可能是头部
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    score=25,
                    confidence=0.85,
                    reason=f"放量滞涨(量比{volume_ratio:.1f})，疑似头部信号",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'pattern': 'volume_stagnation_top',
                        'volume_ratio': volume_ratio,
                        'change_percent': change_percent
                    }
                )
            else:
                # 低位放量滞涨，可能是底部
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=55,
                    confidence=0.7,
                    reason=f"低位放量滞涨，可能酝酿变盘",
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        'pattern': 'volume_stagnation_bottom',
                        'volume_ratio': volume_ratio
                    }
                )
        
        # 策略4：放量下跌形态
        elif change_percent < -3 and volume_ratio > 1.5:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.STRONG,
                score=20,
                confidence=0.9,
                reason=f"放量下跌(跌{abs(change_percent):.1f}%)，趋势转弱",
                risk_level=RiskLevel.HIGH,
                details={
                    'pattern': 'volume_decline',
                    'volume_ratio': volume_ratio,
                    'change_percent': change_percent
                }
            )
        
        # 策略5：缩量盘整形态
        elif is_sideways and volume_ratio < 0.8:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=65,
                confidence=0.7,
                reason=f"缩量盘整，等待方向选择",
                risk_level=RiskLevel.MEDIUM,
                details={
                    'pattern': 'volume_consolidation',
                    'volume_ratio': volume_ratio,
                    'price_trend': 'sideways'
                }
            )
        
        # 其他正常量价关系
        else:
            # 根据量价配合度评分
            if is_uptrend and volume_ratio > 0.8:
                score = 70
                signal = SignalType.HOLD
                reason = "量价配合正常，趋势延续"
            elif is_downtrend and volume_ratio < 1.2:
                score = 40
                signal = SignalType.WAIT
                reason = "下跌但量能不大，观望"
            else:
                score = 60
                signal = SignalType.HOLD
                reason = "量价关系一般"
            
            return StrategyResult(
                pass_filter=score >= 50,
                signal=signal,
                strength=SignalStrength.WEAK,
                score=score,
                confidence=0.6,
                reason=reason,
                risk_level=RiskLevel.MEDIUM,
                details={
                    'volume_ratio': volume_ratio,
                    'volume_trend': volume_trend,
                    'price_trend': price_trend
                }
            )