"""
股票深度分析服务
整合波动性分析和成交量分析，提供综合的股票深度分析
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from services.volatility_analyzer import VolatilityAnalyzer, VolatilityAnalysisResult, PriceData
from services.volume_analyzer import VolumeAnalyzer, VolumeAnalysisResult
from services.akshare_service import AkShareService

logger = logging.getLogger(__name__)

@dataclass
class DeepAnalysisResult:
    """深度分析综合结果"""
    stock_code: str
    stock_name: str
    analysis_date: str
    
    # 分析结果
    volatility_analysis: VolatilityAnalysisResult
    volume_analysis: VolumeAnalysisResult
    
    # 综合评估
    overall_score: float                    # 综合评分(1-10)
    investment_grade: str                   # 投资等级(A/B/C/D)
    recommendation: str                     # 投资建议(强烈推荐/推荐/观察/回避)
    
    # 关键特征
    is_low_volatility_breakout: bool        # 是否为低波动突破
    is_volume_price_coordinated: bool       # 是否量价配合
    is_worthy_of_attention: bool            # 是否值得关注
    
    # 风险评估
    risk_level: str                         # 风险等级(low/medium/high)
    risk_factors: List[str]                 # 风险因素
    
    # 投资建议
    entry_suggestions: List[str]            # 入场建议
    position_size_suggestion: str           # 仓位建议
    holding_period_suggestion: str          # 持有期建议
    
    # 元数据
    created_at: str

class StockDeepAnalysisService:
    """股票深度分析服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.volatility_analyzer = VolatilityAnalyzer()
        self.volume_analyzer = VolumeAnalyzer()
        self.akshare_service = AkShareService()
        
        # 分析参数配置
        self.analysis_period_days = 90      # 分析周期
        self.high_quality_threshold = 7.0   # 高质量阈值
        self.attention_threshold = 6.0      # 关注阈值
        
    async def analyze_screening_stocks(self, screening_results: List[Dict]) -> List[DeepAnalysisResult]:
        """
        对筛选出的股票进行深度分析
        
        Args:
            screening_results: 筛选结果列表
            
        Returns:
            深度分析结果列表
        """
        try:
            logger.info(f"🔍 开始对 {len(screening_results)} 只筛选股票进行深度分析")
            
            analysis_tasks = []
            
            # 并发分析多只股票
            for stock in screening_results:
                task = self._analyze_single_stock(
                    stock['stock_code'],
                    stock['stock_name']
                )
                analysis_tasks.append(task)
            
            # 执行并发分析
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # 过滤成功的结果
            valid_results = []
            for result in results:
                if isinstance(result, DeepAnalysisResult):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"股票分析失败: {result}")
            
            # 按综合评分排序
            valid_results.sort(key=lambda x: x.overall_score, reverse=True)
            
            logger.info(f"✅ 深度分析完成，有效结果 {len(valid_results)} 只")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"❌ 批量深度分析失败: {e}")
            return []
    
    async def _analyze_single_stock(self, stock_code: str, stock_name: str) -> Optional[DeepAnalysisResult]:
        """分析单只股票"""
        try:
            logger.debug(f"📈 开始分析股票 {stock_code}")
            
            # 1. 获取历史价格数据
            price_data = await self._get_stock_price_data(stock_code)
            
            if not price_data or len(price_data) < 30:
                logger.warning(f"股票 {stock_code} 历史数据不足")
                return None
            
            # 2. 并发执行波动性分析和成交量分析
            volatility_task = self.volatility_analyzer.analyze_stock_volatility(
                stock_code, stock_name, price_data
            )
            volume_task = self.volume_analyzer.analyze_volume_patterns(
                stock_code, stock_name, price_data
            )
            
            volatility_result, volume_result = await asyncio.gather(
                volatility_task, volume_task
            )
            
            # 3. 综合评估
            comprehensive_evaluation = self._evaluate_comprehensive_analysis(
                volatility_result, volume_result
            )
            
            # 4. 构建深度分析结果
            deep_analysis_result = DeepAnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                analysis_date=datetime.now().strftime('%Y-%m-%d'),
                volatility_analysis=volatility_result,
                volume_analysis=volume_result,
                overall_score=comprehensive_evaluation['overall_score'],
                investment_grade=comprehensive_evaluation['investment_grade'],
                recommendation=comprehensive_evaluation['recommendation'],
                is_low_volatility_breakout=comprehensive_evaluation['is_low_volatility_breakout'],
                is_volume_price_coordinated=comprehensive_evaluation['is_volume_price_coordinated'],
                is_worthy_of_attention=comprehensive_evaluation['is_worthy_of_attention'],
                risk_level=comprehensive_evaluation['risk_level'],
                risk_factors=comprehensive_evaluation['risk_factors'],
                entry_suggestions=comprehensive_evaluation['entry_suggestions'],
                position_size_suggestion=comprehensive_evaluation['position_size_suggestion'],
                holding_period_suggestion=comprehensive_evaluation['holding_period_suggestion'],
                created_at=datetime.now().isoformat()
            )
            
            logger.debug(f"✅ 股票 {stock_code} 分析完成，综合评分: {comprehensive_evaluation['overall_score']}")
            
            return deep_analysis_result
            
        except Exception as e:
            logger.error(f"❌ 股票 {stock_code} 深度分析失败: {e}")
            return None
    
    async def _get_stock_price_data(self, stock_code: str) -> List[PriceData]:
        """获取股票价格数据"""
        try:
            # 计算开始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.analysis_period_days + 30)  # 多获取一些数据以防节假日
            
            # 从AkShare获取历史数据
            hist_data = await self.akshare_service.get_stock_history_data(
                symbol=stock_code,
                market="A",
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if hist_data is None or hist_data.empty:
                logger.warning(f"无法获取股票 {stock_code} 的历史数据")
                return []
            
            logger.info(f"获取到 {len(hist_data)} 条历史数据，列名: {list(hist_data.columns)}")
            
            # 转换为PriceData格式
            price_data_list = []
            for _, row in hist_data.iterrows():
                try:
                    # 尝试不同的列名格式（中文和英文）
                    date_col = None
                    for col in ['日期', 'date', 'Date', 'DATE']:
                        if col in row.index:
                            date_col = col
                            break
                    
                    open_col = None
                    for col in ['开盘', 'open', 'Open', 'OPEN']:
                        if col in row.index:
                            open_col = col
                            break
                    
                    high_col = None
                    for col in ['最高', 'high', 'High', 'HIGH']:
                        if col in row.index:
                            high_col = col
                            break
                    
                    low_col = None
                    for col in ['最低', 'low', 'Low', 'LOW']:
                        if col in row.index:
                            low_col = col
                            break
                    
                    close_col = None
                    for col in ['收盘', 'close', 'Close', 'CLOSE']:
                        if col in row.index:
                            close_col = col
                            break
                    
                    volume_col = None
                    for col in ['成交量', 'volume', 'Volume', 'VOLUME', 'vol']:
                        if col in row.index:
                            volume_col = col
                            break
                    
                    change_col = None
                    for col in ['涨跌幅', 'change', 'Change', 'pct_chg', 'pct_change']:
                        if col in row.index:
                            change_col = col
                            break
                    
                    # 提取数据
                    trade_date = str(row[date_col]) if date_col else ''
                    open_price = float(row[open_col]) if open_col and row[open_col] is not None else 0.0
                    high_price = float(row[high_col]) if high_col and row[high_col] is not None else 0.0
                    low_price = float(row[low_col]) if low_col and row[low_col] is not None else 0.0
                    close_price = float(row[close_col]) if close_col and row[close_col] is not None else 0.0
                    volume = int(row[volume_col]) if volume_col and row[volume_col] is not None else 0
                    change_percent = float(row[change_col]) if change_col and row[change_col] is not None else 0.0
                    
                    # 跳过无效数据
                    if not trade_date or close_price <= 0:
                        continue
                    
                    price_data = PriceData(
                        trade_date=trade_date,
                        open_price=open_price,
                        high_price=high_price,
                        low_price=low_price,
                        close_price=close_price,
                        volume=volume,
                        change_percent=change_percent
                    )
                    price_data_list.append(price_data)
                    
                except Exception as e:
                    logger.debug(f"转换价格数据失败: {e}")
                    continue
            
            # 按日期排序
            price_data_list.sort(key=lambda x: x.trade_date)
            
            # 只保留最近的分析周期数据
            if len(price_data_list) > self.analysis_period_days:
                price_data_list = price_data_list[-self.analysis_period_days:]
            
            return price_data_list
            
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 价格数据失败: {e}")
            return []
    
    def _evaluate_comprehensive_analysis(self, 
                                       volatility_result: VolatilityAnalysisResult,
                                       volume_result: VolumeAnalysisResult) -> Dict:
        """综合评估分析结果"""
        try:
            # 1. 计算综合评分
            volatility_weight = 0.6  # 波动性分析权重
            volume_weight = 0.4      # 成交量分析权重
            
            overall_score = (
                volatility_result.volatility_score * volatility_weight +
                volume_result.volume_score * volume_weight
            )
            overall_score = round(overall_score, 2)
            
            # 2. 确定投资等级
            if overall_score >= 8.5:
                investment_grade = 'A'
                recommendation = '强烈推荐'
            elif overall_score >= 7.0:
                investment_grade = 'B'
                recommendation = '推荐'
            elif overall_score >= 5.5:
                investment_grade = 'C'
                recommendation = '观察'
            else:
                investment_grade = 'D'
                recommendation = '回避'
            
            # 3. 判断关键特征
            is_low_volatility_breakout = (
                volatility_result.is_sideways_consolidation and
                volatility_result.has_breakout and
                volatility_result.breakout_direction == 'upward' and
                volatility_result.sideways_period_days >= 20
            )
            
            is_volume_price_coordinated = (
                volume_result.has_volume_breakout and
                volume_result.price_volume_trend == 'bullish' and
                volume_result.money_flow_direction == 'inflow'
            )
            
            is_worthy_of_attention = (
                overall_score >= self.attention_threshold or
                is_low_volatility_breakout or
                is_volume_price_coordinated
            )
            
            # 4. 风险评估
            risk_level, risk_factors = self._assess_risk_level(volatility_result, volume_result)
            
            # 5. 生成投资建议
            entry_suggestions = self._generate_entry_suggestions(
                volatility_result, volume_result, is_low_volatility_breakout
            )
            
            position_size_suggestion = self._suggest_position_size(overall_score, risk_level)
            holding_period_suggestion = self._suggest_holding_period(volatility_result, volume_result)
            
            return {
                'overall_score': overall_score,
                'investment_grade': investment_grade,
                'recommendation': recommendation,
                'is_low_volatility_breakout': is_low_volatility_breakout,
                'is_volume_price_coordinated': is_volume_price_coordinated,
                'is_worthy_of_attention': is_worthy_of_attention,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'entry_suggestions': entry_suggestions,
                'position_size_suggestion': position_size_suggestion,
                'holding_period_suggestion': holding_period_suggestion
            }
            
        except Exception as e:
            logger.error(f"综合评估失败: {e}")
            return self._get_default_evaluation()
    
    def _assess_risk_level(self, volatility_result: VolatilityAnalysisResult, 
                          volume_result: VolumeAnalysisResult) -> tuple:
        """评估风险等级"""
        try:
            risk_factors = []
            risk_score = 0
            
            # 波动性风险因素
            if volatility_result.historical_volatility > 40:
                risk_factors.append("历史波动率过高")
                risk_score += 2
            
            if not volatility_result.has_breakout:
                risk_factors.append("缺乏明确的突破信号")
                risk_score += 1
            
            if volatility_result.pattern_quality == 'poor':
                risk_factors.append("技术形态质量较差")
                risk_score += 2
            
            # 成交量风险因素
            if volume_result.volume_price_divergence:
                risk_factors.append("存在量价背离")
                risk_score += 2
            
            if volume_result.money_flow_direction == 'outflow':
                risk_factors.append("资金流出明显")
                risk_score += 2
            
            if not volume_result.has_volume_breakout:
                risk_factors.append("缺乏成交量支撑")
                risk_score += 1
            
            # 确定风险等级
            if risk_score <= 2:
                risk_level = 'low'
            elif risk_score <= 4:
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            return risk_level, risk_factors
            
        except Exception as e:
            logger.debug(f"评估风险等级失败: {e}")
            return 'medium', ['评估数据不足']
    
    def _generate_entry_suggestions(self, volatility_result: VolatilityAnalysisResult,
                                  volume_result: VolumeAnalysisResult,
                                  is_low_volatility_breakout: bool) -> List[str]:
        """生成入场建议"""
        suggestions = []
        
        try:
            if is_low_volatility_breakout:
                suggestions.append("建议在突破确认后逢回调入场")
                suggestions.append("可分批建仓，降低成本")
            
            if volume_result.has_volume_breakout:
                suggestions.append("成交量放大确认，可考虑追涨")
            
            if volatility_result.has_breakout and volume_result.money_flow_direction == 'inflow':
                suggestions.append("突破+资金流入，形态良好")
            
            if volatility_result.volatility_score >= 7 and volume_result.volume_score >= 6:
                suggestions.append("技术指标良好，可积极关注")
            
            if not suggestions:
                suggestions.append("建议观察，等待更明确的入场信号")
            
            return suggestions
            
        except Exception as e:
            logger.debug(f"生成入场建议失败: {e}")
            return ["建议谨慎观察"]
    
    def _suggest_position_size(self, overall_score: float, risk_level: str) -> str:
        """建议仓位大小"""
        try:
            if overall_score >= 8.5 and risk_level == 'low':
                return "可考虑中等仓位(20-30%)"
            elif overall_score >= 7.0 and risk_level in ['low', 'medium']:
                return "建议小仓位试探(10-20%)"
            elif overall_score >= 6.0:
                return "建议轻仓观察(5-10%)"
            else:
                return "建议观察，暂不建仓"
                
        except Exception as e:
            logger.debug(f"建议仓位失败: {e}")
            return "建议谨慎控制仓位"
    
    def _suggest_holding_period(self, volatility_result: VolatilityAnalysisResult,
                              volume_result: VolumeAnalysisResult) -> str:
        """建议持有期"""
        try:
            if volatility_result.is_sideways_consolidation and volatility_result.has_breakout:
                return "中长期持有(3-6个月)"
            elif volume_result.has_volume_breakout and volume_result.consecutive_high_volume_days >= 3:
                return "短中期持有(1-3个月)"
            else:
                return "短期观察(2-4周)"
                
        except Exception as e:
            logger.debug(f"建议持有期失败: {e}")
            return "根据市场情况灵活调整"
    
    def _get_default_evaluation(self) -> Dict:
        """获取默认评估结果"""
        return {
            'overall_score': 0.0,
            'investment_grade': 'D',
            'recommendation': '数据不足',
            'is_low_volatility_breakout': False,
            'is_volume_price_coordinated': False,
            'is_worthy_of_attention': False,
            'risk_level': 'high',
            'risk_factors': ['数据不足，无法准确评估'],
            'entry_suggestions': ['建议等待更多数据'],
            'position_size_suggestion': '暂不建议建仓',
            'holding_period_suggestion': '待评估'
        }
    
    def get_attention_worthy_stocks(self, analysis_results: List[DeepAnalysisResult]) -> List[DeepAnalysisResult]:
        """筛选值得关注的股票"""
        try:
            attention_stocks = []
            
            for result in analysis_results:
                if (result.is_worthy_of_attention and 
                    result.overall_score >= self.attention_threshold and
                    result.investment_grade in ['A', 'B']):
                    attention_stocks.append(result)
            
            # 按综合评分排序
            attention_stocks.sort(key=lambda x: x.overall_score, reverse=True)
            
            return attention_stocks
            
        except Exception as e:
            logger.error(f"筛选关注股票失败: {e}")
            return []