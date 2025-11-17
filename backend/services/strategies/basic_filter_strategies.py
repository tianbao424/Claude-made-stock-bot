"""
基础过滤策略实现
包含5个基础的股票过滤策略
"""
from ..strategy_base import DailyStrategy, StrategyResult, SignalType, SignalStrength, RiskLevel
import logging

logger = logging.getLogger(__name__)

class LowPriceFilter(DailyStrategy):
    """
    低价股过滤策略
    条件：股价 < 6元 → 剔除
    逻辑：低价股往往质地较差，风险较高
    """
    
    def __init__(self, price_threshold: float = 6.0):
        super().__init__(
            name="low_price_filter",
            description="过滤低于指定价格的股票，避免垃圾股风险",
            weight=1.0
        )
        self.price_threshold = price_threshold
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        stock_code = stock_data.get('stock_code', '')
        
        # 特殊处理银行股（银行股股价普遍较低）
        if stock_code.startswith('601') or stock_code.startswith('000001'):
            bank_threshold = 3.0  # 银行股使用更低的阈值
            if close_price < bank_threshold:
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.STRONG,
                    score=0,
                    confidence=0.95,
                    reason=f"银行股股价{close_price:.2f}元过低，可能存在问题",
                    risk_level=RiskLevel.HIGH
                )
        
        # 一般股票判断
        if close_price < self.price_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.STRONG,
                score=0,
                confidence=0.9,
                reason=f"股价{close_price:.2f}元低于{self.price_threshold}元，为垃圾股特征",
                risk_level=RiskLevel.HIGH,
                details={'price': close_price, 'threshold': self.price_threshold}
            )
        
        # 价格合理区间给予不同评分
        if close_price >= 50:
            score = 60  # 高价股
        elif close_price >= 20:
            score = 80  # 中价股，最优
        elif close_price >= 10:
            score = 70  # 低价绩优股
        else:
            score = 50  # 接近阈值
        
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.BUY if score >= 70 else SignalType.HOLD,
            strength=SignalStrength.MEDIUM,
            score=score,
            confidence=0.8,
            reason=f"股价{close_price:.2f}元处于合理区间",
            risk_level=RiskLevel.LOW,
            details={'price': close_price, 'price_range': self._get_price_range(close_price)}
        )
    
    def _get_price_range(self, price: float) -> str:
        """获取价格区间描述"""
        if price >= 50:
            return "高价股"
        elif price >= 20:
            return "中价股"
        elif price >= 10:
            return "低价绩优"
        else:
            return "低价股"


class HighPositionNewsFilter(DailyStrategy):
    """
    高位利好回避策略
    条件：累计涨幅 > 80% 且 出现利好新闻 → 剔除
    逻辑：高位放利好往往是出货信号
    """
    
    def __init__(self, gain_threshold: float = 0.8, days: int = 60):
        super().__init__(
            name="high_position_news_filter",
            description="识别高位利好出货，避免接盘",
            weight=1.5  # 重要策略，权重较高
        )
        self.gain_threshold = gain_threshold
        self.days = days
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        # 计算累计涨幅（使用MA60作为参考）
        close_price = stock_data.get('close_price', 0)
        ma60 = technical_data.get('ma60')
        
        if not ma60 or ma60 <= 0:
            # 没有足够历史数据，使用备选方案
            change_percent = stock_data.get('change_percent', 0)
            if change_percent > 50:  # 短期涨幅过大
                return StrategyResult(
                    pass_filter=False,
                    signal=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    score=20,
                    confidence=0.7,
                    reason=f"短期涨幅{change_percent:.1f}%过大，需要谨慎",
                    risk_level=RiskLevel.HIGH
                )
            
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=60,
                confidence=0.5,
                reason="历史数据不足，保持观望",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 计算相对60日均线的涨幅
        gain_ratio = (close_price - ma60) / ma60
        
        # 检查是否有新闻（这里简化处理，实际应该接入新闻接口）
        has_positive_news = self._check_news_sentiment(stock_data, technical_data)
        
        if gain_ratio > self.gain_threshold and has_positive_news:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.STRONG,
                score=10,
                confidence=0.9,
                reason=f"股价已累计上涨{gain_ratio*100:.1f}%，高位放利好疑似出货",
                risk_level=RiskLevel.HIGH,
                details={
                    'gain_ratio': gain_ratio,
                    'current_price': close_price,
                    'ma60': ma60,
                    'has_news': has_positive_news
                }
            )
        
        # 涨幅过大但没有利好
        if gain_ratio > self.gain_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.MEDIUM,
                score=30,
                confidence=0.8,
                reason=f"涨幅{gain_ratio*100:.1f}%已经很大，建议等待回调",
                risk_level=RiskLevel.HIGH,
                details={'gain_ratio': gain_ratio}
            )
        
        # 正常情况
        score = 80 - gain_ratio * 50  # 涨幅越大分数越低
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.BUY if gain_ratio < 0.3 else SignalType.HOLD,
            strength=SignalStrength.MEDIUM,
            score=max(50, min(90, score)),
            confidence=0.8,
            reason=f"涨幅{gain_ratio*100:.1f}%处于合理范围",
            risk_level=RiskLevel.LOW if gain_ratio < 0.3 else RiskLevel.MEDIUM,
            details={'gain_ratio': gain_ratio, 'ma60': ma60}
        )
    
    def _check_news_sentiment(self, stock_data: dict, technical_data: dict) -> bool:
        """检查新闻情绪（简化版本）"""
        # 使用一些技术指标作为代理判断
        # 实际应该接入新闻API
        
        # 如果连续涨停，可能有利好
        is_limit_up = technical_data.get('is_limit_up', False)
        
        # 成交量异常放大，可能有消息
        volume_ratio = technical_data.get('volume_ratio', 1.0)
        
        return is_limit_up or volume_ratio > 3.0


class MADeviationFilter(DailyStrategy):
    """
    均线偏离过远策略
    条件：close/MA20 > 1.2 → 等待回调
    逻辑：偏离均线过远容易回调
    """
    
    def __init__(self, deviation_threshold: float = 1.2):
        super().__init__(
            name="ma_deviation_filter",
            description="检测股价偏离均线程度，避免追高",
            weight=1.2
        )
        self.deviation_threshold = deviation_threshold
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        close_price = stock_data.get('close_price', 0)
        ma20 = technical_data.get('ma20')
        ma5 = technical_data.get('ma5')
        
        if not ma20 or ma20 <= 0:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="缺少20日均线数据，无法判断",
                risk_level=RiskLevel.MEDIUM
            )
        
        deviation = close_price / ma20
        
        # 严重偏离
        if deviation > self.deviation_threshold:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.STRONG,
                score=20,
                confidence=0.85,
                reason=f"股价偏离20日均线{(deviation-1)*100:.1f}%，严重超买",
                risk_level=RiskLevel.HIGH,
                details={
                    'deviation': deviation,
                    'ma20': ma20,
                    'close': close_price,
                    'distance': close_price - ma20
                }
            )
        
        # 均线下方（可能是买入机会）
        if deviation < 0.95:
            # 检查趋势
            trend = self._check_trend(ma5, ma20)
            if trend == "up":
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    score=90,
                    confidence=0.9,
                    reason=f"股价低于20日均线{(1-deviation)*100:.1f}%，上升趋势中的回调买点",
                    risk_level=RiskLevel.LOW,
                    details={'deviation': deviation, 'trend': trend}
                )
            else:
                return StrategyResult(
                    pass_filter=True,
                    signal=SignalType.WAIT,
                    strength=SignalStrength.MEDIUM,
                    score=40,
                    confidence=0.7,
                    reason=f"股价低于均线但趋势不明朗",
                    risk_level=RiskLevel.MEDIUM
                )
        
        # 正常偏离范围
        score = 100 - abs(deviation - 1) * 100  # 越接近均线分数越高
        
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.BUY if 0.98 <= deviation <= 1.05 else SignalType.HOLD,
            strength=SignalStrength.MEDIUM,
            score=max(60, min(85, score)),
            confidence=0.8,
            reason=f"股价相对均线偏离{(deviation-1)*100:.1f}%，处于合理范围",
            risk_level=RiskLevel.LOW,
            details={'deviation': deviation, 'ma20': ma20}
        )
    
    def _check_trend(self, ma5: float, ma20: float) -> str:
        """检查趋势方向"""
        if ma5 and ma20:
            if ma5 > ma20 * 1.02:
                return "up"
            elif ma5 < ma20 * 0.98:
                return "down"
        return "neutral"


class GapUpFilter(DailyStrategy):
    """
    跳空高开回避策略
    条件：连续3日跳空缺口未回补 → 剔除
    逻辑：连续跳空上涨后容易回调补缺口
    """
    
    def __init__(self, max_gap_days: int = 3):
        super().__init__(
            name="gap_up_filter",
            description="识别连续跳空上涨，避免追高",
            weight=1.0
        )
        self.max_gap_days = max_gap_days
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        # 检查是否有跳空
        has_gap_up = technical_data.get('has_gap_up', False)
        gap_ratio = technical_data.get('gap_ratio', 0)
        
        # 这里需要获取历史跳空数据（简化处理）
        consecutive_gap_days = await self._count_consecutive_gaps(stock_data, technical_data)
        
        # 连续跳空超过阈值
        if consecutive_gap_days >= self.max_gap_days:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.STRONG,
                score=10,
                confidence=0.9,
                reason=f"连续{consecutive_gap_days}天跳空上涨未回补，短期风险极大",
                risk_level=RiskLevel.HIGH,
                details={
                    'gap_days': consecutive_gap_days,
                    'latest_gap': gap_ratio
                }
            )
        
        # 有跳空但未达到危险程度
        if has_gap_up and consecutive_gap_days > 0:
            score = 60 - consecutive_gap_days * 15
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.WAIT,
                strength=SignalStrength.MEDIUM,
                score=max(30, score),
                confidence=0.7,
                reason=f"存在{consecutive_gap_days}个未回补缺口，需要谨慎",
                risk_level=RiskLevel.MEDIUM,
                details={'gap_days': consecutive_gap_days, 'gap_ratio': gap_ratio}
            )
        
        # 无跳空或已回补
        return StrategyResult(
            pass_filter=True,
            signal=SignalType.BUY,
            strength=SignalStrength.WEAK,
            score=75,
            confidence=0.8,
            reason="无连续跳空风险",
            risk_level=RiskLevel.LOW,
            details={'has_gap': has_gap_up}
        )
    
    async def _count_consecutive_gaps(self, stock_data: dict, technical_data: dict) -> int:
        """计算连续跳空天数（简化版）"""
        # 实际应该查询历史数据
        # 这里使用技术指标简单判断
        if technical_data.get('has_gap_up', False):
            # 根据涨幅估算可能的连续天数
            change_percent = stock_data.get('change_percent', 0)
            if change_percent > 15:  # 累计涨幅很大
                return 3
            elif change_percent > 10:
                return 2
            else:
                return 1
        return 0


class TurnoverFilter(DailyStrategy):
    """
    换手率过高策略
    条件：turnover_rate > 40% 且 非新股 → 剔除
    逻辑：换手率过高说明分歧大，风险高
    """
    
    def __init__(self, max_turnover: float = 40.0, new_stock_days: int = 30):
        super().__init__(
            name="turnover_filter",
            description="过滤换手率异常的股票",
            weight=0.8
        )
        self.max_turnover = max_turnover
        self.new_stock_days = new_stock_days
    
    async def analyze(self, stock_data: dict, technical_data: dict) -> StrategyResult:
        turnover_rate = technical_data.get('turnover_rate', 0)
        
        # 检查是否为新股（简化判断）
        is_new_stock = await self._is_new_stock(stock_data)
        
        # 换手率数据异常
        if turnover_rate <= 0 or turnover_rate > 100:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.WAIT,
                strength=SignalStrength.WEAK,
                score=0,
                confidence=0.3,
                reason="换手率数据异常",
                risk_level=RiskLevel.MEDIUM
            )
        
        # 非新股但换手率过高
        if not is_new_stock and turnover_rate > self.max_turnover:
            return StrategyResult(
                pass_filter=False,
                signal=SignalType.SELL,
                strength=SignalStrength.STRONG,
                score=10,
                confidence=0.85,
                reason=f"换手率{turnover_rate:.1f}%异常高，可能有资金出逃",
                risk_level=RiskLevel.HIGH,
                details={
                    'turnover_rate': turnover_rate,
                    'is_new_stock': is_new_stock
                }
            )
        
        # 新股高换手率是正常的
        if is_new_stock and turnover_rate > self.max_turnover:
            return StrategyResult(
                pass_filter=True,
                signal=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                score=60,
                confidence=0.7,
                reason=f"新股换手率{turnover_rate:.1f}%偏高但属正常",
                risk_level=RiskLevel.MEDIUM,
                details={'turnover_rate': turnover_rate, 'is_new_stock': True}
            )
        
        # 换手率合理范围评分
        if turnover_rate < 2:
            score = 60  # 过低，流动性差
            signal = SignalType.HOLD
        elif turnover_rate < 5:
            score = 80  # 正常，健康
            signal = SignalType.BUY
        elif turnover_rate < 10:
            score = 85  # 活跃，良好
            signal = SignalType.BUY
        elif turnover_rate < 20:
            score = 70  # 偏高，谨慎
            signal = SignalType.HOLD
        else:
            score = 50  # 较高，观望
            signal = SignalType.WAIT
        
        return StrategyResult(
            pass_filter=True,
            signal=signal,
            strength=SignalStrength.MEDIUM,
            score=score,
            confidence=0.8,
            reason=f"换手率{turnover_rate:.1f}%，{self._get_turnover_desc(turnover_rate)}",
            risk_level=RiskLevel.LOW if turnover_rate < 10 else RiskLevel.MEDIUM,
            details={'turnover_rate': turnover_rate}
        )
    
    def _get_turnover_desc(self, turnover: float) -> str:
        """获取换手率描述"""
        if turnover < 2:
            return "流动性偏低"
        elif turnover < 5:
            return "流动性正常"
        elif turnover < 10:
            return "交投活跃"
        elif turnover < 20:
            return "交投偏热"
        else:
            return "交投过热"
    
    async def _is_new_stock(self, stock_data: dict) -> bool:
        """判断是否为新股（简化版）"""
        # 实际应该查询上市日期
        # 这里用一些特征简单判断
        stock_code = stock_data.get('stock_code', '')
        
        # 科创板和创业板新股
        if stock_code.startswith('688') or stock_code.startswith('30'):
            return True
        
        # 其他简化判断...
        return False


