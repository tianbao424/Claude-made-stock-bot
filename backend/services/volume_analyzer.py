"""
成交量分析模块
实现成交量突破分析、量价关系评估和资金流向分析
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import statistics

from .volatility_analyzer import PriceData

logger = logging.getLogger(__name__)

@dataclass
class VolumeAnalysisResult:
    """成交量分析结果"""
    stock_code: str
    stock_name: str
    analysis_period_days: int
    
    # 成交量基础指标
    avg_volume_30d: int                        # 30天平均成交量
    avg_volume_60d: int                        # 60天平均成交量
    current_volume: int                        # 当前成交量
    volume_ratio: float                        # 量比（当前/平均）
    
    # 成交量突破分析
    has_volume_breakout: bool                  # 是否存在成交量突破
    breakout_date: Optional[str]               # 成交量突破日期
    breakout_volume_ratio: Optional[float]     # 突破时量比
    consecutive_high_volume_days: int          # 连续放量天数
    
    # 量价关系分析
    volume_price_correlation: float            # 量价相关性(-1到1)
    volume_price_divergence: bool              # 是否存在量价背离
    price_volume_trend: str                    # 量价趋势(bullish/bearish/neutral)
    
    # 资金流向分析
    money_flow_direction: str                  # 资金流向(inflow/outflow/balanced)
    money_flow_intensity: float                # 资金流入强度(0-10)
    accumulation_distribution: float           # 累积分布指标
    
    # 成交量形态分析
    volume_pattern: str                        # 成交量形态(突破/缩量/放量/正常)
    volume_trend: str                          # 成交量趋势(increasing/decreasing/stable)
    
    # 综合评分
    volume_score: float                        # 成交量评分(1-10)
    volume_quality: str                        # 成交量质量(excellent/good/fair/poor)
    
    # 元数据
    analysis_date: str
    created_at: str

class VolumeAnalyzer:
    """成交量分析器"""
    
    def __init__(self):
        self.volume_breakout_threshold = 2.0    # 成交量突破阈值（2倍）
        self.high_volume_threshold = 1.5        # 高成交量阈值（1.5倍）
        self.correlation_threshold = 0.3        # 相关性阈值
        
    async def analyze_volume_patterns(self,
                                    stock_code: str,
                                    stock_name: str,
                                    price_data: List[PriceData]) -> VolumeAnalysisResult:
        """
        分析成交量形态
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price_data: 价格数据列表(按日期升序)
            
        Returns:
            成交量分析结果
        """
        try:
            logger.info(f"📊 开始分析股票 {stock_code} 的成交量形态")
            
            if len(price_data) < 30:
                logger.warning(f"股票 {stock_code} 数据不足，无法进行成交量分析")
                return self._create_empty_result(stock_code, stock_name)
            
            # 1. 计算基础成交量指标
            volume_metrics = self._calculate_volume_metrics(price_data)
            
            # 2. 分析成交量突破
            volume_breakout = self._analyze_volume_breakout(price_data, volume_metrics)
            
            # 3. 分析量价关系
            volume_price_analysis = self._analyze_volume_price_relationship(price_data)
            
            # 4. 分析资金流向
            money_flow_analysis = self._analyze_money_flow(price_data)
            
            # 5. 识别成交量形态
            volume_pattern_analysis = self._identify_volume_patterns(price_data, volume_metrics)
            
            # 6. 计算综合评分
            volume_score, volume_quality = self._calculate_volume_score(
                volume_metrics, volume_breakout, volume_price_analysis, 
                money_flow_analysis, volume_pattern_analysis
            )
            
            # 构建分析结果
            result = VolumeAnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                analysis_period_days=len(price_data),
                avg_volume_30d=volume_metrics['avg_volume_30d'],
                avg_volume_60d=volume_metrics['avg_volume_60d'],
                current_volume=volume_metrics['current_volume'],
                volume_ratio=volume_metrics['volume_ratio'],
                has_volume_breakout=volume_breakout['has_breakout'],
                breakout_date=volume_breakout.get('breakout_date'),
                breakout_volume_ratio=volume_breakout.get('breakout_ratio'),
                consecutive_high_volume_days=volume_breakout['consecutive_days'],
                volume_price_correlation=volume_price_analysis['correlation'],
                volume_price_divergence=volume_price_analysis['has_divergence'],
                price_volume_trend=volume_price_analysis['trend'],
                money_flow_direction=money_flow_analysis['direction'],
                money_flow_intensity=money_flow_analysis['intensity'],
                accumulation_distribution=money_flow_analysis['ad_value'],
                volume_pattern=volume_pattern_analysis['pattern'],
                volume_trend=volume_pattern_analysis['trend'],
                volume_score=volume_score,
                volume_quality=volume_quality,
                analysis_date=datetime.now().strftime('%Y-%m-%d'),
                created_at=datetime.now().isoformat()
            )
            
            logger.info(f"✅ 股票 {stock_code} 成交量分析完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ 股票 {stock_code} 成交量分析失败: {e}")
            return self._create_empty_result(stock_code, stock_name)
    
    def _calculate_volume_metrics(self, price_data: List[PriceData]) -> Dict:
        """计算基础成交量指标"""
        try:
            volumes = [data.volume for data in price_data if data.volume > 0]
            
            if not volumes:
                return {
                    'avg_volume_30d': 0,
                    'avg_volume_60d': 0,
                    'current_volume': 0,
                    'volume_ratio': 0.0
                }
            
            # 计算平均成交量
            avg_volume_30d = int(statistics.mean(volumes[-30:])) if len(volumes) >= 30 else int(statistics.mean(volumes))
            avg_volume_60d = int(statistics.mean(volumes[-60:])) if len(volumes) >= 60 else int(statistics.mean(volumes))
            current_volume = volumes[-1] if volumes else 0
            
            # 计算量比
            volume_ratio = current_volume / avg_volume_30d if avg_volume_30d > 0 else 0.0
            
            return {
                'avg_volume_30d': avg_volume_30d,
                'avg_volume_60d': avg_volume_60d,
                'current_volume': current_volume,
                'volume_ratio': round(volume_ratio, 2)
            }
            
        except Exception as e:
            logger.debug(f"计算成交量指标失败: {e}")
            return {'avg_volume_30d': 0, 'avg_volume_60d': 0, 'current_volume': 0, 'volume_ratio': 0.0}
    
    def _analyze_volume_breakout(self, price_data: List[PriceData], volume_metrics: Dict) -> Dict:
        """分析成交量突破"""
        try:
            avg_volume = volume_metrics['avg_volume_30d']
            if avg_volume <= 0:
                return {'has_breakout': False, 'consecutive_days': 0}
            
            # 寻找成交量突破点
            breakout_info = {'has_breakout': False, 'consecutive_days': 0}
            consecutive_days = 0
            
            # 从后往前检查最近的成交量突破
            for i in range(len(price_data) - 1, max(0, len(price_data) - 10), -1):
                data = price_data[i]
                volume_ratio = data.volume / avg_volume if avg_volume > 0 else 0
                
                if volume_ratio >= self.volume_breakout_threshold:
                    if not breakout_info['has_breakout']:
                        breakout_info.update({
                            'has_breakout': True,
                            'breakout_date': data.trade_date,
                            'breakout_ratio': round(volume_ratio, 2)
                        })
                    consecutive_days += 1
                else:
                    break
            
            # 计算连续高成交量天数
            high_volume_days = 0
            for i in range(len(price_data) - 1, -1, -1):
                data = price_data[i]
                volume_ratio = data.volume / avg_volume if avg_volume > 0 else 0
                
                if volume_ratio >= self.high_volume_threshold:
                    high_volume_days += 1
                else:
                    break
            
            breakout_info['consecutive_days'] = high_volume_days
            
            return breakout_info
            
        except Exception as e:
            logger.debug(f"分析成交量突破失败: {e}")
            return {'has_breakout': False, 'consecutive_days': 0}
    
    def _analyze_volume_price_relationship(self, price_data: List[PriceData]) -> Dict:
        """分析量价关系"""
        try:
            if len(price_data) < 10:
                return {'correlation': 0.0, 'has_divergence': False, 'trend': 'neutral'}
            
            # 计算价格变化和成交量的相关性
            price_changes = []
            volume_changes = []
            
            for i in range(1, len(price_data)):
                if price_data[i-1].close_price > 0 and price_data[i-1].volume > 0:
                    price_change = (price_data[i].close_price - price_data[i-1].close_price) / price_data[i-1].close_price
                    volume_change = (price_data[i].volume - price_data[i-1].volume) / price_data[i-1].volume
                    
                    price_changes.append(price_change)
                    volume_changes.append(volume_change)
            
            # 计算相关系数
            correlation = 0.0
            if len(price_changes) >= 10:
                try:
                    correlation = self._calculate_correlation(price_changes, volume_changes)
                except:
                    correlation = 0.0
            
            # 分析量价背离
            has_divergence = self._detect_volume_price_divergence(price_data[-10:])
            
            # 确定量价趋势
            trend = 'neutral'
            if correlation > self.correlation_threshold:
                trend = 'bullish'  # 量价齐升
            elif correlation < -self.correlation_threshold:
                trend = 'bearish'  # 价升量缩或价跌量增
            
            return {
                'correlation': round(correlation, 3),
                'has_divergence': has_divergence,
                'trend': trend
            }
            
        except Exception as e:
            logger.debug(f"分析量价关系失败: {e}")
            return {'correlation': 0.0, 'has_divergence': False, 'trend': 'neutral'}
    
    def _detect_volume_price_divergence(self, recent_data: List[PriceData]) -> bool:
        """检测量价背离"""
        try:
            if len(recent_data) < 5:
                return False
            
            # 检查最近5天的价格和成交量趋势
            price_trend = recent_data[-1].close_price > recent_data[0].close_price
            
            # 计算成交量趋势
            recent_volumes = [data.volume for data in recent_data[-3:]]
            earlier_volumes = [data.volume for data in recent_data[:3]]
            
            avg_recent_volume = statistics.mean(recent_volumes)
            avg_earlier_volume = statistics.mean(earlier_volumes)
            
            volume_trend = avg_recent_volume > avg_earlier_volume
            
            # 价格上涨但成交量下降，或价格下跌但成交量上升，都认为是背离
            divergence = (price_trend and not volume_trend) or (not price_trend and volume_trend)
            
            return divergence
            
        except Exception as e:
            logger.debug(f"检测量价背离失败: {e}")
            return False
    
    def _analyze_money_flow(self, price_data: List[PriceData]) -> Dict:
        """分析资金流向"""
        try:
            if len(price_data) < 10:
                return {'direction': 'balanced', 'intensity': 0.0, 'ad_value': 0.0}
            
            # 计算累积分布线(A/D Line)
            ad_values = []
            ad_line = 0.0
            
            for data in price_data:
                if data.high_price != data.low_price:
                    # 计算资金流量乘数
                    money_flow_multiplier = ((data.close_price - data.low_price) - 
                                           (data.high_price - data.close_price)) / (data.high_price - data.low_price)
                    
                    # 计算资金流量
                    money_flow_volume = money_flow_multiplier * data.volume
                    ad_line += money_flow_volume
                    ad_values.append(ad_line)
                else:
                    ad_values.append(ad_line)
            
            # 分析资金流向趋势
            recent_ad = ad_values[-5:] if len(ad_values) >= 5 else ad_values
            earlier_ad = ad_values[-10:-5] if len(ad_values) >= 10 else ad_values[:len(ad_values)//2]
            
            if recent_ad and earlier_ad:
                recent_avg = statistics.mean(recent_ad)
                earlier_avg = statistics.mean(earlier_ad)
                
                if recent_avg > earlier_avg * 1.05:
                    direction = 'inflow'
                    intensity = min((recent_avg - earlier_avg) / abs(earlier_avg) * 10, 10) if earlier_avg != 0 else 0
                elif recent_avg < earlier_avg * 0.95:
                    direction = 'outflow'
                    intensity = min((earlier_avg - recent_avg) / abs(earlier_avg) * 10, 10) if earlier_avg != 0 else 0
                else:
                    direction = 'balanced'
                    intensity = 0.0
            else:
                direction = 'balanced'
                intensity = 0.0
            
            return {
                'direction': direction,
                'intensity': round(intensity, 2),
                'ad_value': round(ad_line, 2)
            }
            
        except Exception as e:
            logger.debug(f"分析资金流向失败: {e}")
            return {'direction': 'balanced', 'intensity': 0.0, 'ad_value': 0.0}
    
    def _identify_volume_patterns(self, price_data: List[PriceData], volume_metrics: Dict) -> Dict:
        """识别成交量形态"""
        try:
            avg_volume = volume_metrics['avg_volume_30d']
            current_volume = volume_metrics['current_volume']
            volume_ratio = volume_metrics['volume_ratio']
            
            # 确定成交量形态
            if volume_ratio >= 2.0:
                pattern = '突破'
            elif volume_ratio <= 0.5:
                pattern = '缩量'
            elif volume_ratio >= 1.5:
                pattern = '放量'
            else:
                pattern = '正常'
            
            # 分析成交量趋势
            if len(price_data) >= 10:
                recent_volumes = [data.volume for data in price_data[-5:]]
                earlier_volumes = [data.volume for data in price_data[-10:-5]]
                
                recent_avg = statistics.mean(recent_volumes)
                earlier_avg = statistics.mean(earlier_volumes)
                
                if recent_avg > earlier_avg * 1.2:
                    trend = 'increasing'
                elif recent_avg < earlier_avg * 0.8:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            return {
                'pattern': pattern,
                'trend': trend
            }
            
        except Exception as e:
            logger.debug(f"识别成交量形态失败: {e}")
            return {'pattern': '正常', 'trend': 'stable'}
    
    def _calculate_volume_score(self, volume_metrics: Dict, volume_breakout: Dict,
                              volume_price_analysis: Dict, money_flow_analysis: Dict,
                              volume_pattern_analysis: Dict) -> Tuple[float, str]:
        """计算成交量综合评分"""
        try:
            score = 0.0
            
            # 1. 成交量突破评分 (30%)
            if volume_breakout['has_breakout']:
                breakout_ratio = volume_breakout.get('breakout_ratio', 0)
                consecutive_days = volume_breakout['consecutive_days']
                
                # 突破强度评分
                score += min(breakout_ratio / 3, 1.0) * 2  # 最高2分
                
                # 持续性评分
                score += min(consecutive_days / 5, 1.0) * 1  # 最高1分
            
            # 2. 量价关系评分 (25%)
            correlation = volume_price_analysis['correlation']
            trend = volume_price_analysis['trend']
            
            if trend == 'bullish':
                score += 2.5
            elif trend == 'neutral' and correlation > 0:
                score += 1.0
            elif volume_price_analysis['has_divergence']:
                score -= 1.0  # 量价背离扣分
            
            # 3. 资金流向评分 (25%)
            direction = money_flow_analysis['direction']
            intensity = money_flow_analysis['intensity']
            
            if direction == 'inflow':
                score += min(intensity / 5, 1.0) * 2.5
            elif direction == 'outflow':
                score -= min(intensity / 5, 1.0) * 1.5
            
            # 4. 成交量形态评分 (20%)
            pattern = volume_pattern_analysis['pattern']
            trend = volume_pattern_analysis['trend']
            
            if pattern == '突破':
                score += 1.5
            elif pattern == '放量':
                score += 1.0
            elif pattern == '缩量':
                score -= 0.5
            
            if trend == 'increasing':
                score += 0.5
            elif trend == 'decreasing':
                score -= 0.5
            
            # 限制评分范围
            score = max(0, min(score, 10))
            
            # 确定成交量质量
            if score >= 8:
                quality = 'excellent'
            elif score >= 6:
                quality = 'good'
            elif score >= 4:
                quality = 'fair'
            else:
                quality = 'poor'
            
            return round(score, 2), quality
            
        except Exception as e:
            logger.debug(f"计算成交量评分失败: {e}")
            return 0.0, 'poor'
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """计算相关系数"""
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0.0
            
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi * xi for xi in x)
            sum_y2 = sum(yi * yi for yi in y)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            if denominator == 0:
                return 0.0
            
            correlation = numerator / denominator
            return max(-1.0, min(1.0, correlation))  # 限制在[-1, 1]范围内
            
        except Exception as e:
            logger.debug(f"计算相关系数失败: {e}")
            return 0.0
    
    def _create_empty_result(self, stock_code: str, stock_name: str) -> VolumeAnalysisResult:
        """创建空的分析结果"""
        return VolumeAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_period_days=0,
            avg_volume_30d=0,
            avg_volume_60d=0,
            current_volume=0,
            volume_ratio=0.0,
            has_volume_breakout=False,
            breakout_date=None,
            breakout_volume_ratio=None,
            consecutive_high_volume_days=0,
            volume_price_correlation=0.0,
            volume_price_divergence=False,
            price_volume_trend='neutral',
            money_flow_direction='balanced',
            money_flow_intensity=0.0,
            accumulation_distribution=0.0,
            volume_pattern='正常',
            volume_trend='stable',
            volume_score=0.0,
            volume_quality='poor',
            analysis_date=datetime.now().strftime('%Y-%m-%d'),
            created_at=datetime.now().isoformat()
        )
    
    def is_high_quality_volume(self, result: VolumeAnalysisResult) -> bool:
        """判断是否为高质量成交量（值得关注）"""
        return (
            result.has_volume_breakout and
            result.consecutive_high_volume_days >= 2 and
            result.price_volume_trend == 'bullish' and
            result.money_flow_direction == 'inflow' and
            result.volume_score >= 6.0
        )