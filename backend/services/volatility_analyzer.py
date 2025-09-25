"""
波动性分析模块
实现股票历史波动性分析、横盘整理期识别和突破信号检测
"""
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

@dataclass
class VolatilityAnalysisResult:
    """波动性分析结果"""
    stock_code: str
    stock_name: str
    analysis_period_days: int                   # 分析周期天数
    
    # 波动性指标
    historical_volatility: float               # 历史波动率
    price_volatility_percent: float            # 价格波动百分比
    sideways_period_days: int                  # 横盘整理天数
    
    # 横盘整理分析
    is_sideways_consolidation: bool            # 是否存在横盘整理
    consolidation_start_date: str              # 整理开始日期
    consolidation_end_date: str                # 整理结束日期
    consolidation_price_range: Tuple[float, float]  # 整理区间价格范围
    
    # 突破分析
    has_breakout: bool                         # 是否存在突破
    breakout_date: Optional[str]               # 突破日期
    breakout_price: Optional[float]            # 突破价格
    breakout_direction: Optional[str]          # 突破方向(upward/downward)
    
    # 综合评分
    volatility_score: float                    # 波动性评分(1-10)
    pattern_quality: str                       # 形态质量(excellent/good/fair/poor)
    
    # 元数据
    analysis_date: str                         # 分析日期
    created_at: str                           # 创建时间

@dataclass
class PriceData:
    """价格数据结构"""
    trade_date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    change_percent: float

class VolatilityAnalyzer:
    """波动性分析器"""
    
    def __init__(self):
        self.analysis_period = 90  # 默认90天分析周期
        self.sideways_threshold = 0.20  # 横盘整理阈值(20%)
        self.min_sideways_days = 15     # 最少横盘天数
        
    async def analyze_stock_volatility(self, 
                                     stock_code: str, 
                                     stock_name: str,
                                     price_data: List[PriceData]) -> VolatilityAnalysisResult:
        """
        分析股票波动性
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price_data: 价格数据列表(按日期升序)
            
        Returns:
            波动性分析结果
        """
        try:
            logger.info(f"🔍 开始分析股票 {stock_code} 的波动性")
            
            if len(price_data) < 30:
                logger.warning(f"股票 {stock_code} 数据不足，无法进行波动性分析")
                return self._create_empty_result(stock_code, stock_name)
            
            # 1. 计算历史波动率
            historical_volatility = self._calculate_historical_volatility(price_data)
            
            # 2. 分析价格波动范围
            price_volatility = self._calculate_price_volatility(price_data)
            
            # 3. 识别横盘整理期
            sideways_result = self._identify_sideways_consolidation(price_data)
            
            # 4. 检测突破信号
            breakout_result = self._detect_breakout_signals(price_data, sideways_result)
            
            # 5. 计算综合评分
            volatility_score, pattern_quality = self._calculate_volatility_score(
                historical_volatility, price_volatility, sideways_result, breakout_result
            )
            
            # 构建分析结果
            result = VolatilityAnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                analysis_period_days=len(price_data),
                historical_volatility=historical_volatility,
                price_volatility_percent=price_volatility,
                sideways_period_days=sideways_result.get('duration_days', 0),
                is_sideways_consolidation=sideways_result.get('is_sideways', False),
                consolidation_start_date=sideways_result.get('start_date', ''),
                consolidation_end_date=sideways_result.get('end_date', ''),
                consolidation_price_range=sideways_result.get('price_range', (0, 0)),
                has_breakout=breakout_result.get('has_breakout', False),
                breakout_date=breakout_result.get('breakout_date'),
                breakout_price=breakout_result.get('breakout_price'),
                breakout_direction=breakout_result.get('direction'),
                volatility_score=volatility_score,
                pattern_quality=pattern_quality,
                analysis_date=datetime.now().strftime('%Y-%m-%d'),
                created_at=datetime.now().isoformat()
            )
            
            logger.info(f"✅ 股票 {stock_code} 波动性分析完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ 股票 {stock_code} 波动性分析失败: {e}")
            return self._create_empty_result(stock_code, stock_name)
    
    def _calculate_historical_volatility(self, price_data: List[PriceData]) -> float:
        """计算历史波动率"""
        try:
            # 计算日收益率
            daily_returns = []
            for i in range(1, len(price_data)):
                prev_close = price_data[i-1].close_price
                curr_close = price_data[i].close_price
                if prev_close > 0:
                    daily_return = (curr_close - prev_close) / prev_close
                    daily_returns.append(daily_return)
            
            if len(daily_returns) < 10:
                return 0.0
            
            # 计算收益率标准差
            std_dev = statistics.stdev(daily_returns)
            
            # 年化波动率
            annualized_volatility = std_dev * math.sqrt(252)  # 252个交易日
            
            return round(annualized_volatility * 100, 2)  # 转换为百分比
            
        except Exception as e:
            logger.debug(f"计算历史波动率失败: {e}")
            return 0.0
    
    def _calculate_price_volatility(self, price_data: List[PriceData]) -> float:
        """计算价格波动百分比"""
        try:
            if len(price_data) < 2:
                return 0.0
            
            prices = [data.close_price for data in price_data]
            min_price = min(prices)
            max_price = max(prices)
            
            if min_price <= 0:
                return 0.0
            
            volatility_percent = ((max_price - min_price) / min_price) * 100
            return round(volatility_percent, 2)
            
        except Exception as e:
            logger.debug(f"计算价格波动失败: {e}")
            return 0.0
    
    def _identify_sideways_consolidation(self, price_data: List[PriceData]) -> Dict:
        """识别横盘整理期"""
        try:
            if len(price_data) < self.min_sideways_days:
                return {'is_sideways': False}
            
            # 寻找最长的横盘整理期
            best_sideways = {'is_sideways': False, 'duration_days': 0}
            
            # 滑动窗口检测横盘整理
            for start_idx in range(len(price_data) - self.min_sideways_days):
                for end_idx in range(start_idx + self.min_sideways_days, len(price_data)):
                    window_data = price_data[start_idx:end_idx + 1]
                    
                    # 计算该窗口期间的价格波动
                    prices = [data.close_price for data in window_data]
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    if min_price <= 0:
                        continue
                    
                    volatility = (max_price - min_price) / min_price
                    
                    # 如果波动在阈值内，认为是横盘整理
                    if volatility <= self.sideways_threshold:
                        duration = end_idx - start_idx + 1
                        if duration > best_sideways['duration_days']:
                            best_sideways = {
                                'is_sideways': True,
                                'duration_days': duration,
                                'start_date': window_data[0].trade_date,
                                'end_date': window_data[-1].trade_date,
                                'price_range': (min_price, max_price),
                                'start_idx': start_idx,
                                'end_idx': end_idx,
                                'volatility_percent': round(volatility * 100, 2)
                            }
            
            return best_sideways
            
        except Exception as e:
            logger.debug(f"识别横盘整理失败: {e}")
            return {'is_sideways': False}
    
    def _detect_breakout_signals(self, price_data: List[PriceData], sideways_result: Dict) -> Dict:
        """检测突破信号"""
        try:
            if not sideways_result.get('is_sideways', False):
                return {'has_breakout': False}
            
            consolidation_end_idx = sideways_result.get('end_idx', -1)
            price_range = sideways_result.get('price_range', (0, 0))
            
            if consolidation_end_idx == -1 or consolidation_end_idx >= len(price_data) - 1:
                return {'has_breakout': False}
            
            # 检查整理后的价格行为
            post_consolidation_data = price_data[consolidation_end_idx + 1:]
            
            if len(post_consolidation_data) < 3:  # 至少需要3天确认突破
                return {'has_breakout': False}
            
            resistance_level = price_range[1]  # 阻力位
            support_level = price_range[0]     # 支撑位
            
            # 寻找突破点
            for i, data in enumerate(post_consolidation_data):
                close_price = data.close_price
                
                # 向上突破
                if close_price > resistance_level * 1.02:  # 突破阻力位2%以上
                    # 确认突破（连续2天收盘价在阻力位之上）
                    if self._confirm_breakout(post_consolidation_data[i:], resistance_level, 'upward'):
                        return {
                            'has_breakout': True,
                            'breakout_date': data.trade_date,
                            'breakout_price': close_price,
                            'direction': 'upward',
                            'breakout_strength': round((close_price - resistance_level) / resistance_level * 100, 2)
                        }
                
                # 向下突破
                elif close_price < support_level * 0.98:  # 跌破支撑位2%以上
                    if self._confirm_breakout(post_consolidation_data[i:], support_level, 'downward'):
                        return {
                            'has_breakout': True,
                            'breakout_date': data.trade_date,
                            'breakout_price': close_price,
                            'direction': 'downward',
                            'breakout_strength': round((support_level - close_price) / support_level * 100, 2)
                        }
            
            return {'has_breakout': False}
            
        except Exception as e:
            logger.debug(f"检测突破信号失败: {e}")
            return {'has_breakout': False}
    
    def _confirm_breakout(self, data_after_breakout: List[PriceData], level: float, direction: str) -> bool:
        """确认突破有效性"""
        try:
            if len(data_after_breakout) < 2:
                return False
            
            confirmation_count = 0
            for data in data_after_breakout[:3]:  # 检查后续3天
                if direction == 'upward' and data.close_price > level:
                    confirmation_count += 1
                elif direction == 'downward' and data.close_price < level:
                    confirmation_count += 1
            
            return confirmation_count >= 2  # 至少2天确认
            
        except Exception as e:
            logger.debug(f"确认突破失败: {e}")
            return False
    
    def _calculate_volatility_score(self, 
                                  historical_volatility: float,
                                  price_volatility: float,
                                  sideways_result: Dict,
                                  breakout_result: Dict) -> Tuple[float, str]:
        """计算波动性综合评分"""
        try:
            score = 0.0
            
            # 1. 横盘整理评分 (40%)
            if sideways_result.get('is_sideways', False):
                duration_days = sideways_result.get('duration_days', 0)
                volatility_percent = sideways_result.get('volatility_percent', 100)
                
                # 横盘时间越长、波动越小，评分越高
                duration_score = min(duration_days / 60, 1.0) * 4  # 最高4分
                volatility_score = max(0, (20 - volatility_percent) / 20) * 4  # 最高4分
                score += (duration_score + volatility_score) / 2
            
            # 2. 突破信号评分 (30%)
            if breakout_result.get('has_breakout', False):
                direction = breakout_result.get('direction', '')
                strength = breakout_result.get('breakout_strength', 0)
                
                if direction == 'upward':
                    # 向上突破加分更多
                    score += min(strength / 10, 1.0) * 3
                else:
                    # 向下突破减分
                    score -= min(strength / 10, 1.0) * 2
            
            # 3. 历史波动率评分 (20%)
            if 10 <= historical_volatility <= 30:  # 适中的波动率
                score += 2
            elif historical_volatility < 10:  # 波动率过低
                score += 1
            
            # 4. 整体价格波动评分 (10%)
            if price_volatility <= 25:  # 相对稳定
                score += 1
            
            # 限制评分范围
            score = max(0, min(score, 10))
            
            # 确定形态质量
            if score >= 8:
                pattern_quality = 'excellent'
            elif score >= 6:
                pattern_quality = 'good'
            elif score >= 4:
                pattern_quality = 'fair'
            else:
                pattern_quality = 'poor'
            
            return round(score, 2), pattern_quality
            
        except Exception as e:
            logger.debug(f"计算波动性评分失败: {e}")
            return 0.0, 'poor'
    
    def _create_empty_result(self, stock_code: str, stock_name: str) -> VolatilityAnalysisResult:
        """创建空的分析结果"""
        return VolatilityAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_period_days=0,
            historical_volatility=0.0,
            price_volatility_percent=0.0,
            sideways_period_days=0,
            is_sideways_consolidation=False,
            consolidation_start_date='',
            consolidation_end_date='',
            consolidation_price_range=(0, 0),
            has_breakout=False,
            breakout_date=None,
            breakout_price=None,
            breakout_direction=None,
            volatility_score=0.0,
            pattern_quality='poor',
            analysis_date=datetime.now().strftime('%Y-%m-%d'),
            created_at=datetime.now().isoformat()
        )
    
    def is_high_quality_pattern(self, result: VolatilityAnalysisResult) -> bool:
        """判断是否为高质量形态（值得关注）"""
        return (
            result.is_sideways_consolidation and
            result.sideways_period_days >= 20 and
            result.has_breakout and
            result.breakout_direction == 'upward' and
            result.volatility_score >= 6.0
        )