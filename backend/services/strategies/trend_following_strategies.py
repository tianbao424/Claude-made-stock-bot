"""
趋势跟随策略实现
包含3个基于趋势跟随的选股策略
"""
from ..strategy_base import DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel
import logging

logger = logging.getLogger(__name__)

class MAGoldenCross(DailyStrategy):
    """
    均线金叉策略
    - MA5上穿MA20 → 买入信号
    - MA20上穿MA60 → 强势确认
    - 多头排列且股价回踩支撑 → 加仓机会
    """
    
    def __init__(self):
        super().__init__(
            name="ma_golden_cross",
            description="识别均线金叉买入信号",
            weight=1.4
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        
        if not all([ma5, ma20, ma60]) or any(x <= 0 for x in [ma5, ma20, ma60]):
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 计算均线相对位置
        ma5_vs_ma20 = ma5 / ma20
        ma20_vs_ma60 = ma20 / ma60
        price_vs_ma5 = close_price / ma5
        
        # 检查是否发生金叉
        is_golden_cross_520 = ma5_vs_ma20 > 1.005 and ma5_vs_ma20 < 1.02  # 刚刚金叉
        is_golden_cross_2060 = ma20_vs_ma60 > 1.002 and ma20_vs_ma60 < 1.015
        
        # 多头排列确认
        is_bullish_alignment = ma5 > ma20 > ma60
        
        # 策略1：双重金叉 - 最强信号
        if is_golden_cross_520 and is_golden_cross_2060 and volume_ratio > 1.2:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG,
                score=95,
                confidence=0.95,
                reason=f"双重金叉突破(MA5/MA20={ma5_vs_ma20:.3f}, MA20/MA60={ma20_vs_ma60:.3f})，强势启动",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.15,
                stop_loss_price=ma20 * 0.98,
                details={
                    'pattern': 'double_golden_cross',
                    'ma5_vs_ma20': ma5_vs_ma20,
                    'ma20_vs_ma60': ma20_vs_ma60,
                    'volume_confirmation': volume_ratio > 1.2
                }
            )
        
        # 策略2：MA5上穿MA20
        if is_golden_cross_520:
            confidence = 0.85 if volume_ratio > 1.0 else 0.7
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.STRONG,
                score=88,
                confidence=confidence,
                reason=f"MA5上穿MA20金叉信号(量比{volume_ratio:.2f})",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.08,
                stop_loss_price=ma20 * 0.98,
                details={
                    'pattern': 'ma5_golden_cross',
                    'volume_ratio': volume_ratio
                }
            )
        
        # 策略3：多头排列回踩支撑
        if is_bullish_alignment and 0.98 <= price_vs_ma5 <= 1.02:
            # 股价接近MA5，可能是回踩机会
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                score=82,
                confidence=0.8,
                reason=f"多头排列回踩MA5支撑，买入良机",
                risk_level=RiskLevel.LOW,
                target_price=close_price * 1.1,
                stop_loss_price=ma5 * 0.97,
                details={
                    'pattern': 'bullish_pullback',
                    'price_vs_ma5': price_vs_ma5,
                    'alignment': 'bullish'
                }
            )
        
        # 检查趋势方向
        if is_bullish_alignment:
            score = 75
            signal = SignalType.HOLD
            reason = "多头排列维持"
        elif ma5 > ma20:
            score = 65
            signal = SignalType.HOLD
            reason = "短期趋势向上"
        elif ma20 > ma60:
            score = 60
            signal = SignalType.HOLD
            reason = "中期趋势向上"
        else:
            # 空头排列
            score = 30
            signal = SignalType.SELL
            reason = "空头排列，趋势向下"
        
        return StrategyResult(
            pass_filter=score >= 50,
            signal=signal,
            strength=SignalStrength.WEAK,
            score=score,
            confidence=0.7,
            reason=reason,
            risk_level=RiskLevel.MEDIUM,
            details={
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60,
                'alignment': 'bullish' if is_bullish_alignment else 'bearish'
            }
        )


class TrendMomentum(DailyStrategy):
    """
    趋势动能策略
    - RSI从30以下回升至50以上 → 超跌反弹
    - KDJ低位金叉 → 底部确认
    - MACD零轴上方金叉 → 趋势加速
    """
    
    def __init__(self):
        super().__init__(
            name="trend_momentum",
            description="基于技术指标的趋势动能分析",
            weight=1.3
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        change_percent = stock_data.get('change_percent', 0)
        
        # 尝试获取技术指标，如果没有则使用通用指标
        rsi = technical_data.get('rsi') or technical_data.get('rsi_6') or technical_data.get('rsi_12')
        kdj_k = technical_data.get('kdj_k')
        kdj_d = technical_data.get('kdj_d')
        kdj_j = technical_data.get('kdj_j')
        macd = technical_data.get('macd') or technical_data.get('macd_dif')
        
        # 如果没有技术指标，使用价格动能分析
        if not any([rsi, kdj_k, macd]):
            # 基于价格变化和均线的简化动能分析
            ma5 = technical_data.get('ma5')
            ma20 = technical_data.get('ma20')
            volume_ratio = technical_data.get('volume_ratio', 1.0)
            
            if ma5 and ma20:
                price_momentum = (close_price - ma20) / ma20 * 100 if ma20 > 0 else 0
                trend_momentum = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
                
                # 动能强劲
                if price_momentum > 5 and trend_momentum > 2 and change_percent > 3:
                    return StrategyResult(
                        pass_filter=True,
                        signal=SignalType.BUY,
                        strength=SignalStrength.STRONG,
                        score=85,
                        confidence=0.8,
                        reason=f"价格动能强劲({price_momentum:.1f}%)，趋势加速",
                        risk_level=RiskLevel.MEDIUM,
                        details={'price_momentum': price_momentum, 'trend_momentum': trend_momentum}
                    )
                
                # 动能转弱
                elif price_momentum < -3 and change_percent < -2:
                    return StrategyResult(
                        pass_filter=False,
                        signal=SignalType.SELL,
                        strength=SignalStrength.MEDIUM,
                        score=25,
                        confidence=0.7,
                        reason=f"价格动能转弱({price_momentum:.1f}%)，趋势疲软",
                        risk_level=RiskLevel.HIGH,
                        details={'price_momentum': price_momentum}
                    )
                
                # 动能平稳
                else:
                    score = 60 + price_momentum if price_momentum < 20 else 60
                    return StrategyResult(
                        pass_filter=True,
                        signal=SignalType.HOLD,
                        strength=SignalStrength.WEAK,
                        score=max(50, min(80, score)),
                        confidence=0.6,
                        reason=f"价格动能正常({price_momentum:.1f}%)",
                        risk_level=RiskLevel.MEDIUM,
                        details={'price_momentum': price_momentum}
                    )
            else:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.WEAK,
                    score=0,
                    confidence=0.3,
                    reason="缺少必要的均线数据",
                    risk_level=RiskLevel.MEDIUM
                )
        
        # 如果有技术指标，使用技术指标分析
        signals = []
        total_score = 0
        
        # RSI分析
        if rsi is not None:
            if 30 <= rsi <= 70:
                # RSI正常范围
                signals.append(f"RSI={rsi:.1f}正常")
                total_score += 30
            elif rsi < 30:
                # 超跌反弹机会
                signals.append(f"RSI={rsi:.1f}超跌，反弹机会")
                total_score += 40
            else:
                # RSI超买
                signals.append(f"RSI={rsi:.1f}超买")
                total_score -= 10
        
        # KDJ分析
        if kdj_k is not None and kdj_d is not None:
            if kdj_k > kdj_d and kdj_k < 80:
                if kdj_k < 20:
                    signals.append(f"KDJ低位金叉(K={kdj_k:.1f})")
                    total_score += 35
                else:
                    signals.append(f"KDJ金叉信号")
                    total_score += 25
            elif kdj_k > 80:
                signals.append(f"KDJ高位钝化")
                total_score -= 15
        
        # MACD分析
        if macd is not None:
            if macd > 0:
                signals.append(f"MACD多头信号")
                total_score += 25
            else:
                signals.append(f"MACD空头信号")
                total_score -= 10
        
        # 计算最终结果
        if not signals:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=60,
                confidence=0.5,
                reason="技术指标无明显信号",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 根据总分判断
        final_score = max(0, min(100, 60 + total_score))
        signal_strength = SignalStrength.STRONG if abs(total_score) > 30 else SignalStrength.MEDIUM
        
        if total_score > 20:
            signal = SignalType.BUY
            risk = RiskLevel.LOW if total_score > 40 else RiskLevel.MEDIUM
        elif total_score < -20:
            signal = SignalType.SELL
            risk = RiskLevel.HIGH
        else:
            signal = SignalType.HOLD
            risk = RiskLevel.MEDIUM
        
        return StrategyResult(
            pass_filter=total_score > -30,
            signal=signal,
            strength=signal_strength,
            score=final_score,
            confidence=0.8 if len(signals) > 1 else 0.6,
            reason=f"技术指标综合信号: {', '.join(signals)}",
            risk_level=risk,
            details={'signals': signals, 'total_score': total_score}
        )
        
        # 综合评分
        final_score = 60 + total_score
        final_score = max(0, min(100, final_score))
        
        # 确定信号强度和类型
        strong_signals = [s for s in signals if s['strength'] == 'strong']
        if strong_signals and final_score >= 85:
            signal_type = SignalType.BUY
            signal_strength = SignalStrength.STRONG
            confidence = 0.9
        elif final_score >= 70:
            signal_type = SignalType.BUY
            signal_strength = SignalStrength.MEDIUM
            confidence = 0.8
        elif final_score >= 50:
            signal_type = SignalType.HOLD
            signal_strength = SignalStrength.WEAK
            confidence = 0.7
        else:
            signal_type = SignalType.SELL
            signal_strength = SignalStrength.MEDIUM
            confidence = 0.75
        
        # 生成原因描述
        main_signals = [s['description'] for s in signals[:2]]
        reason = "、".join(main_signals)
        
        return StrategyResult(
            pass_filter=final_score >= 50,
            signal=signal_type,
            strength=signal_strength,
            score=final_score,
            confidence=confidence,
            reason=reason,
            risk_level=RiskLevel.LOW if final_score >= 80 else RiskLevel.MEDIUM,
            target_price=close_price * 1.1 if final_score >= 80 else None,
            stop_loss_price=close_price * 0.95 if final_score >= 70 else None,
            details={
                'signals': signals,
                'indicators': {
                    'rsi_6': rsi_6,
                    'kdj_k': kdj_k,
                    'kdj_d': kdj_d,
                    'macd_dif': macd_dif,
                    'macd_dea': macd_dea
                }
            }
        )


class TrendReversal(DailyStrategy):
    """
    趋势反转策略
    - 连续下跌后出现反转信号 → 抄底机会
    - 高位连续上涨后出现顶部信号 → 减仓信号
    - 重要支撑/阻力位的突破确认
    """
    
    def __init__(self):
        super().__init__(
            name="trend_reversal",
            description="识别趋势反转的买卖信号",
            weight=1.2
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        change_percent = stock_data.get('change_percent', 0)
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        rsi_6 = technical_data.get('rsi_6')
        
        if not ma20 or not ma60:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 计算价格相对位置
        price_vs_ma20 = close_price / ma20
        price_vs_ma60 = close_price / ma60
        
        # 判断当前趋势状态
        if ma20 > ma60 * 1.02:
            trend_state = "uptrend"
        elif ma20 < ma60 * 0.98:
            trend_state = "downtrend"
        else:
            trend_state = "sideways"
        
        # 策略1：下跌趋势中的反转信号
        if trend_state == "downtrend" and price_vs_ma60 < 0.9:
            # 在下跌趋势中，寻找反转信号
            reversal_signals = []
            
            # 放量反弹
            if change_percent > 3 and volume_ratio > 1.5:
                reversal_signals.append("放量反弹")
            
            # RSI超跌反弹
            if rsi_6 and rsi_6 < 25 and change_percent > 0:
                reversal_signals.append("RSI超跌反弹")
            
            # 接近重要支撑
            if price_vs_ma60 < 0.85:
                reversal_signals.append("接近重要支撑")
            
            if reversal_signals:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG if len(reversal_signals) >= 2 else SignalStrength.MEDIUM,
                    score=80 + len(reversal_signals) * 5,
                    confidence=0.8,
                    reason=f"下跌趋势反转信号：{'+'.join(reversal_signals)}",
                    risk_level=RiskLevel.MEDIUM,
                    target_price=ma20,  # 目标回到20日均线
                    stop_loss_price=close_price * 0.93,
                    details={
                        'trend_state': trend_state,
                        'reversal_signals': reversal_signals,
                        'price_position': price_vs_ma60
                    }
                )
        
        # 策略2：上涨趋势中的顶部信号
        elif trend_state == "uptrend" and price_vs_ma20 > 1.1:
            # 在上涨趋势中，寻找顶部信号
            top_signals = []
            
            # 放量滞涨
            if volume_ratio > 2.0 and change_percent < 2:
                top_signals.append("放量滞涨")
            
            # RSI超买
            if rsi_6 and rsi_6 > 75:
                top_signals.append("RSI超买")
            
            # 偏离均线过远
            if price_vs_ma20 > 1.2:
                top_signals.append("偏离均线过远")
            
            if top_signals:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG if len(top_signals) >= 2 else SignalStrength.MEDIUM,
                    score=20 - len(top_signals) * 5,
                    confidence=0.8,
                    reason=f"上涨趋势顶部信号：{'+'.join(top_signals)}",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'trend_state': trend_state,
                        'top_signals': top_signals,
                        'price_position': price_vs_ma20
                    }
                )
        
        # 策略3：横盘震荡中的突破
        elif trend_state == "sideways":
            # 判断是向上还是向下突破
            if change_percent > 5 and volume_ratio > 1.8:
                # 向上突破
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=85,
                    confidence=0.85,
                    reason="横盘整理后向上突破",
                    risk_level=RiskLevel.LOW,
                    target_price=close_price * 1.12,
                    stop_loss_price=ma20 * 0.98,
                    details={
                        'pattern': 'upward_breakout',
                        'volume_confirmation': True
                    }
                )
            elif change_percent < -5 and volume_ratio > 1.8:
                # 向下突破
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    score=15,
                    confidence=0.85,
                    reason="横盘整理后向下突破",
                    risk_level=RiskLevel.HIGH,
                    details={
                        'pattern': 'downward_breakout',
                        'volume_confirmation': True
                    }
                )
        
        # 无明显反转信号
        if trend_state == "uptrend":
            score = 75
            signal = SignalType.HOLD
            reason = "上涨趋势延续"
        elif trend_state == "downtrend":
            score = 35
            signal = SignalType.WAIT
            reason = "下跌趋势延续"
        else:
            score = 60
            signal = SignalType.HOLD
            reason = "横盘整理中"
        
        return StrategyResult(
            pass_filter=score >= 50,
            signal=signal,
            strength=SignalStrength.WEAK,
            score=score,
            confidence=0.6,
            reason=reason,
            risk_level=RiskLevel.MEDIUM,
            details={
                'trend_state': trend_state,
                'price_vs_ma20': price_vs_ma20,
                'price_vs_ma60': price_vs_ma60
            }
        )