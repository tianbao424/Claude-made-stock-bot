"""
综合判断策略实现
整合多个策略信号，进行综合评分和决策
"""
from ..strategy_base import DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel
import logging

logger = logging.getLogger(__name__)

class ComprehensiveAnalysis(DailyStrategy):
    """
    综合判断策略
    - 汇总多个策略的信号
    - 加权计算综合得分
    - 根据市场环境动态调整权重
    - 提供综合买卖建议
    """
    
    def __init__(self):
        super().__init__(
            name="comprehensive_analysis",
            description="综合多维度分析的智能决策系统",
            weight=2.0  # 最高权重
        )
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        change_percent = stock_data.get('change_percent', 0)
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        
        if not all([ma5, ma20, ma60]):
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少必要的均线数据",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 判断市场环境
        market_env = self._analyze_market_environment(stock_data, technical_data)
        
        # 收集各维度信号
        signals = {
            'trend': self._analyze_trend_signals(stock_data, technical_data),
            'volume': self._analyze_volume_signals(stock_data, technical_data),
            'momentum': self._analyze_momentum_signals(stock_data, technical_data),
            'pattern': self._analyze_pattern_signals(stock_data, technical_data)
        }
        
        # 计算综合得分
        total_score = 0
        total_weight = 0
        signal_descriptions = []
        
        for signal_type, signal_data in signals.items():
            if signal_data:
                weight = signal_data['weight'] * market_env['weight_multiplier'].get(signal_type, 1.0)
                score = signal_data['score'] * weight
                total_score += score
                total_weight += weight
                
                if signal_data['signal'] != SignalType.HOLD:
                    signal_descriptions.append(f"{signal_data['description']}({signal_data['score']}分)")
        
        # 计算最终得分
        final_score = total_score / total_weight if total_weight > 0 else 60
        
        # 确定信号类型
        if final_score >= 80:
            signal = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = 0.9
            risk = RiskLevel.LOW
        elif final_score >= 70:
            signal = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = 0.8
            risk = RiskLevel.LOW
        elif final_score >= 60:
            signal = SignalType.HOLD
            strength = SignalStrength.MEDIUM
            confidence = 0.7
            risk = RiskLevel.MEDIUM
        elif final_score >= 40:
            signal = SignalType.WAIT
            strength = SignalStrength.WEAK
            confidence = 0.6
            risk = RiskLevel.MEDIUM
        else:
            signal = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = 0.8
            risk = RiskLevel.HIGH
        
        # 生成综合建议
        if signal_descriptions:
            reason = f"综合判断：{market_env['description']}，{'; '.join(signal_descriptions[:2])}"
        else:
            reason = f"综合判断：{market_env['description']}，无明显信号"
        
        return StrategyResult(
            pass_filter=final_score >= 40,
            signal=signal,
            strength=strength,
            score=final_score,
            confidence=confidence,
            reason=reason,
            risk_level=risk,
            target_price=close_price * 1.1 if signal == SignalType.BUY else None,
            stop_loss_price=close_price * 0.95 if signal == SignalType.BUY else None,
            details={
                'market_environment': market_env,
                'signals': signals,
                'signal_count': len(signal_descriptions),
                'final_score': final_score
            }
        )
    
    def _analyze_market_environment(self, stock_data: dict, technical_data: dict):
        """分析市场环境，动态调整各类信号权重"""
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        
        # 判断趋势强度
        if ma5 > ma20 > ma60:
            trend_state = 'strong_uptrend'
            description = '强势上涨趋势'
            weight_multiplier = {
                'trend': 1.5,      # 趋势信号权重增加
                'volume': 1.2,     # 量价信号适度增加
                'momentum': 1.3,   # 动能信号增加
                'pattern': 1.0     # 形态信号正常
            }
        elif ma5 < ma20 < ma60:
            trend_state = 'strong_downtrend'
            description = '弱势下跌趋势'
            weight_multiplier = {
                'trend': 1.3,      # 趋势信号权重增加
                'volume': 1.0,     # 量价信号正常
                'momentum': 1.2,   # 动能信号增加
                'pattern': 1.5     # 形态信号增加（寻找反转）
            }
        elif abs(ma20 - ma60) / ma60 < 0.03:
            trend_state = 'consolidation'
            description = '震荡整理阶段'
            weight_multiplier = {
                'trend': 0.8,      # 趋势信号权重降低
                'volume': 1.5,     # 量价信号增加（突破关键）
                'momentum': 1.0,   # 动能信号正常
                'pattern': 1.3     # 形态信号增加
            }
        else:
            trend_state = 'normal'
            description = '正常趋势状态'
            weight_multiplier = {
                'trend': 1.0,
                'volume': 1.0,
                'momentum': 1.0,
                'pattern': 1.0
            }
        
        # 根据成交量调整
        if volume_ratio > 2.0:
            description += '，放量明显'
            weight_multiplier['volume'] *= 1.2
        elif volume_ratio < 0.5:
            description += '，缩量明显'
            weight_multiplier['pattern'] *= 1.1
        
        return {
            'trend_state': trend_state,
            'description': description,
            'weight_multiplier': weight_multiplier
        }
    
    def _analyze_trend_signals(self, stock_data: dict, technical_data: dict):
        """分析趋势类信号"""
        ma5 = technical_data.get('ma5')
        ma20 = technical_data.get('ma20')
        ma60 = technical_data.get('ma60')
        close_price = stock_data.get('close_price', 0)
        
        score = 60  # 基础分
        signal = SignalType.HOLD
        description = "趋势信号"
        
        # 均线多头排列
        if ma5 > ma20 > ma60:
            score = 85
            signal = SignalType.BUY
            description = "均线多头排列"
        # 均线空头排列
        elif ma5 < ma20 < ma60:
            score = 25
            signal = SignalType.SELL
            description = "均线空头排列"
        # 价格在均线上方
        elif close_price > ma20 and close_price > ma60:
            score = 70
            signal = SignalType.HOLD
            description = "价格在均线上方"
        # 价格在均线下方
        elif close_price < ma20 and close_price < ma60:
            score = 40
            signal = SignalType.WAIT
            description = "价格在均线下方"
        
        return {
            'score': score,
            'signal': signal,
            'description': description,
            'weight': 1.0
        }
    
    def _analyze_volume_signals(self, stock_data: dict, technical_data: dict):
        """分析量价类信号"""
        change_percent = stock_data.get('change_percent', 0)
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        
        score = 60
        signal = SignalType.HOLD
        description = "量价信号"
        
        # 放量上涨
        if change_percent > 3 and volume_ratio > 1.5:
            score = 90
            signal = SignalType.BUY
            description = "放量上涨"
        # 缩量上涨
        elif change_percent > 3 and volume_ratio < 0.8:
            score = 65
            signal = SignalType.HOLD
            description = "缩量上涨"
        # 放量下跌
        elif change_percent < -3 and volume_ratio > 1.5:
            score = 20
            signal = SignalType.SELL
            description = "放量下跌"
        # 缩量下跌
        elif change_percent < -3 and volume_ratio < 0.8:
            score = 45
            signal = SignalType.WAIT
            description = "缩量下跌"
        
        return {
            'score': score,
            'signal': signal,
            'description': description,
            'weight': 0.8
        }
    
    def _analyze_momentum_signals(self, stock_data: dict, technical_data: dict):
        """分析动能类信号"""
        rsi = technical_data.get('rsi') or technical_data.get('rsi_6')
        kdj_k = technical_data.get('kdj_k')
        kdj_d = technical_data.get('kdj_d')
        
        if not any([rsi, kdj_k]):
            return None
        
        score = 60
        signal = SignalType.HOLD
        description = "动能信号"
        
        # RSI分析
        if rsi:
            if rsi < 30:
                score = 75
                signal = SignalType.BUY
                description = "RSI超跌"
            elif rsi > 70:
                score = 35
                signal = SignalType.SELL
                description = "RSI超买"
        
        # KDJ分析
        if kdj_k and kdj_d:
            if kdj_k < 20 and kdj_k > kdj_d:
                score = 80
                signal = SignalType.BUY
                description = "KDJ低位金叉"
            elif kdj_k > 80 and kdj_k < kdj_d:
                score = 30
                signal = SignalType.SELL
                description = "KDJ高位死叉"
        
        return {
            'score': score,
            'signal': signal,
            'description': description,
            'weight': 0.7
        }
    
    def _analyze_pattern_signals(self, stock_data: dict, technical_data: dict):
        """分析形态类信号"""
        close_price = stock_data.get('close_price', 0)
        high_price = stock_data.get('high_price', close_price)
        low_price = stock_data.get('low_price', close_price)
        ma20 = technical_data.get('ma20')
        is_new_high = technical_data.get('is_new_high', False)
        
        if not ma20:
            return None
        
        score = 60
        signal = SignalType.HOLD
        description = "形态信号"
        
        # 创新高
        if is_new_high:
            score = 88
            signal = SignalType.BUY
            description = "突破新高"
        # 箱体上沿
        elif close_price > ma20 * 1.05:
            score = 75
            signal = SignalType.BUY
            description = "突破箱体上沿"
        # 箱体下沿
        elif close_price < ma20 * 0.95:
            score = 35
            signal = SignalType.WAIT
            description = "跌破箱体下沿"
        
        return {
            'score': score,
            'signal': signal,
            'description': description,
            'weight': 0.6
        }