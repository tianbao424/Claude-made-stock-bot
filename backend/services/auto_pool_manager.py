"""
自动股票池管理器
根据深度分析结果自动管理股票池，将符合条件的股票添加到关注池
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from services.stock_deep_analysis_service import StockDeepAnalysisService, DeepAnalysisResult
from database import DatabaseManager, StockPool

logger = logging.getLogger(__name__)

@dataclass
class AutoPoolConfig:
    """自动股票池管理配置"""
    # 评分阈值
    min_overall_score: float = 6.0              # 最低综合评分
    min_volatility_score: float = 6.5           # 最低波动性评分
    min_volume_score: float = 5.5               # 最低成交量评分
    
    # 模式匹配要求
    require_low_volatility_breakout: bool = True  # 必须是低波动突破
    require_volume_coordination: bool = True      # 必须量价配合
    min_sideways_days: int = 20                   # 最少横盘天数
    
    # 投资等级要求
    allowed_investment_grades: List[str] = None   # 允许的投资等级
    max_risk_level: str = "medium"                # 最高风险等级
    
    # 自动添加设置
    auto_add_enabled: bool = True                 # 是否启用自动添加
    avoid_duplicates: bool = True                 # 避免重复添加
    max_auto_additions_per_day: int = 10          # 每天最大自动添加数量
    
    def __post_init__(self):
        if self.allowed_investment_grades is None:
            self.allowed_investment_grades = ['A', 'B']

class AutoPoolManager:
    """自动股票池管理器"""
    
    def __init__(self, db_manager: DatabaseManager, deep_analysis_service: StockDeepAnalysisService):
        self.db_manager = db_manager
        self.deep_analysis_service = deep_analysis_service
        self.config = AutoPoolConfig()
        
        # 统计信息
        self.daily_additions_count = 0
        self.last_reset_date = datetime.now().date()
        
    def set_config(self, config: AutoPoolConfig):
        """设置管理器配置"""
        self.config = config
        logger.info(f"📋 更新自动股票池管理配置")
    
    async def process_analysis_results(self, analysis_results: List[DeepAnalysisResult]) -> Dict:
        """
        处理分析结果并自动管理股票池
        
        Args:
            analysis_results: 深度分析结果列表
            
        Returns:
            处理结果统计
        """
        try:
            logger.info(f"🔄 开始处理 {len(analysis_results)} 个分析结果")
            
            # 重置每日计数器
            self._reset_daily_counter_if_needed()
            
            # 筛选符合条件的股票
            qualified_stocks = self._filter_qualified_stocks(analysis_results)
            logger.info(f"✅ 筛选出 {len(qualified_stocks)} 只符合条件的股票")
            
            # 获取现有股票池
            existing_stocks = self._get_existing_stock_codes()
            
            # 过滤已存在的股票
            new_qualified_stocks = []
            if self.config.avoid_duplicates:
                for stock in qualified_stocks:
                    if stock.stock_code not in existing_stocks:
                        new_qualified_stocks.append(stock)
                logger.info(f"🔍 去重后剩余 {len(new_qualified_stocks)} 只新股票")
            else:
                new_qualified_stocks = qualified_stocks
            
            # 限制每日添加数量
            if self.config.auto_add_enabled:
                remaining_quota = self.config.max_auto_additions_per_day - self.daily_additions_count
                if len(new_qualified_stocks) > remaining_quota:
                    logger.warning(f"⚠️  今日配额不足，限制添加数量从 {len(new_qualified_stocks)} 到 {remaining_quota}")
                    new_qualified_stocks = new_qualified_stocks[:remaining_quota]
            
            # 自动添加到股票池
            added_stocks = []
            if self.config.auto_add_enabled and new_qualified_stocks:
                added_stocks = await self._add_stocks_to_pool(new_qualified_stocks)
                self.daily_additions_count += len(added_stocks)
                logger.info(f"🎯 成功添加 {len(added_stocks)} 只股票到关注池")
            
            # 生成处理报告
            processing_report = {
                'total_analyzed': len(analysis_results),
                'qualified_stocks': len(qualified_stocks),
                'new_qualified_stocks': len(new_qualified_stocks),
                'added_to_pool': len(added_stocks),
                'daily_additions_used': self.daily_additions_count,
                'daily_quota_remaining': self.config.max_auto_additions_per_day - self.daily_additions_count,
                'qualified_stock_details': [
                    {
                        'stock_code': stock.stock_code,
                        'stock_name': stock.stock_name,
                        'overall_score': stock.overall_score,
                        'investment_grade': stock.investment_grade,
                        'is_low_volatility_breakout': stock.is_low_volatility_breakout,
                        'sideways_period_days': stock.volatility_analysis.sideways_period_days,
                        'breakout_direction': stock.volatility_analysis.breakout_direction,
                    } for stock in qualified_stocks
                ],
                'added_stock_details': [
                    {
                        'stock_code': stock.stock_code,
                        'stock_name': stock.stock_name,
                        'overall_score': stock.overall_score,
                        'reason': self._generate_addition_reason(stock)
                    } for stock in added_stocks
                ]
            }
            
            logger.info(f"📊 自动股票池管理完成: 分析{processing_report['total_analyzed']}只, 符合条件{processing_report['qualified_stocks']}只, 新增{processing_report['added_to_pool']}只")
            
            return processing_report
            
        except Exception as e:
            logger.error(f"❌ 自动股票池管理失败: {e}")
            return {
                'total_analyzed': len(analysis_results) if analysis_results else 0,
                'qualified_stocks': 0,
                'new_qualified_stocks': 0,
                'added_to_pool': 0,
                'error': str(e)
            }
    
    def _filter_qualified_stocks(self, analysis_results: List[DeepAnalysisResult]) -> List[DeepAnalysisResult]:
        """筛选符合条件的股票"""
        qualified_stocks = []
        
        for result in analysis_results:
            try:
                # 检查综合评分
                if result.overall_score < self.config.min_overall_score:
                    continue
                
                # 检查波动性评分
                if result.volatility_analysis.volatility_score < self.config.min_volatility_score:
                    continue
                
                # 检查成交量评分
                if result.volume_analysis.volume_score < self.config.min_volume_score:
                    continue
                
                # 检查投资等级
                if result.investment_grade not in self.config.allowed_investment_grades:
                    continue
                
                # 检查风险等级
                if not self._is_risk_level_acceptable(result.risk_level):
                    continue
                
                # 检查低波动突破要求
                if self.config.require_low_volatility_breakout:
                    if not result.is_low_volatility_breakout:
                        continue
                    
                    # 检查横盘天数
                    if result.volatility_analysis.sideways_period_days < self.config.min_sideways_days:
                        continue
                    
                    # 检查突破方向（只关注向上突破）
                    if result.volatility_analysis.breakout_direction != 'upward':
                        continue
                
                # 检查量价配合要求
                if self.config.require_volume_coordination:
                    if not result.is_volume_price_coordinated:
                        continue
                
                # 通过所有检查，添加到合格列表
                qualified_stocks.append(result)
                
            except Exception as e:
                logger.debug(f"筛选股票 {result.stock_code} 时出错: {e}")
                continue
        
        return qualified_stocks
    
    def _is_risk_level_acceptable(self, risk_level: str) -> bool:
        """检查风险等级是否可接受"""
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        max_risk_value = risk_order.get(self.config.max_risk_level, 1)
        current_risk_value = risk_order.get(risk_level, 2)
        return current_risk_value <= max_risk_value
    
    def _get_existing_stock_codes(self) -> Set[str]:
        """获取现有股票池中的股票代码"""
        try:
            existing_stocks = self.db_manager.get_all_stock_pools()
            return {stock.stock_code for stock in existing_stocks}
        except Exception as e:
            logger.warning(f"获取现有股票池失败: {e}")
            return set()
    
    async def _add_stocks_to_pool(self, qualified_stocks: List[DeepAnalysisResult]) -> List[DeepAnalysisResult]:
        """将符合条件的股票添加到股票池"""
        added_stocks = []
        
        for result in qualified_stocks:
            try:
                # 创建股票池条目
                stock_pool = StockPool(
                    stock_code=result.stock_code,
                    stock_name=result.stock_name,
                    pool_type='potential',  # 添加到潜在标的池
                    shares=0,  # 潜在标的不设置股数
                    avg_cost=0.0,  # 潜在标的不设置成本
                    current_price=0.0,  # 可以后续更新
                    market_value=0.0,
                    tags=[
                        '自动添加',
                        '低波动突破',
                        f'评分{result.overall_score}',
                        f'{result.investment_grade}级'
                    ],
                    notes=self._generate_addition_reason(result),
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                
                # 添加到数据库
                stock_id = self.db_manager.add_stock(stock_pool)
                if stock_id:
                    added_stocks.append(result)
                    logger.debug(f"✅ 成功添加股票 {result.stock_code} 到关注池")
                else:
                    logger.warning(f"⚠️  添加股票 {result.stock_code} 失败")
                    
            except Exception as e:
                logger.warning(f"❌ 添加股票 {result.stock_code} 到股票池失败: {e}")
                continue
        
        return added_stocks
    
    def _generate_addition_reason(self, result: DeepAnalysisResult) -> str:
        """生成添加原因说明"""
        reasons = []
        
        reasons.append(f"综合评分{result.overall_score}分({result.investment_grade}级)")
        
        if result.is_low_volatility_breakout:
            days = result.volatility_analysis.sideways_period_days
            direction = result.volatility_analysis.breakout_direction
            reasons.append(f"低波动突破(横盘{days}天后{direction}突破)")
        
        if result.is_volume_price_coordinated:
            reasons.append("量价配合良好")
        
        reasons.append(f"波动性评分{result.volatility_analysis.volatility_score}")
        reasons.append(f"成交量评分{result.volume_analysis.volume_score}")
        
        if result.risk_level == 'low':
            reasons.append("低风险")
        elif result.risk_level == 'medium':
            reasons.append("中等风险")
        
        return f"自动分析添加: {', '.join(reasons)}"
    
    def _reset_daily_counter_if_needed(self):
        """如果需要，重置每日计数器"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_additions_count = 0
            self.last_reset_date = today
            logger.info(f"🔄 重置每日自动添加计数器")
    
    def get_daily_statistics(self) -> Dict:
        """获取每日统计信息"""
        self._reset_daily_counter_if_needed()
        
        return {
            'date': self.last_reset_date.isoformat(),
            'daily_additions_used': self.daily_additions_count,
            'daily_quota_remaining': self.config.max_auto_additions_per_day - self.daily_additions_count,
            'auto_add_enabled': self.config.auto_add_enabled,
            'config': {
                'min_overall_score': self.config.min_overall_score,
                'min_volatility_score': self.config.min_volatility_score,
                'min_volume_score': self.config.min_volume_score,
                'require_low_volatility_breakout': self.config.require_low_volatility_breakout,
                'require_volume_coordination': self.config.require_volume_coordination,
                'min_sideways_days': self.config.min_sideways_days,
                'allowed_investment_grades': self.config.allowed_investment_grades,
                'max_risk_level': self.config.max_risk_level,
                'max_auto_additions_per_day': self.config.max_auto_additions_per_day
            }
        }
    
    def update_config_from_dict(self, config_dict: Dict):
        """从字典更新配置"""
        try:
            if 'min_overall_score' in config_dict:
                self.config.min_overall_score = float(config_dict['min_overall_score'])
            
            if 'min_volatility_score' in config_dict:
                self.config.min_volatility_score = float(config_dict['min_volatility_score'])
            
            if 'min_volume_score' in config_dict:
                self.config.min_volume_score = float(config_dict['min_volume_score'])
            
            if 'require_low_volatility_breakout' in config_dict:
                self.config.require_low_volatility_breakout = bool(config_dict['require_low_volatility_breakout'])
            
            if 'require_volume_coordination' in config_dict:
                self.config.require_volume_coordination = bool(config_dict['require_volume_coordination'])
            
            if 'min_sideways_days' in config_dict:
                self.config.min_sideways_days = int(config_dict['min_sideways_days'])
            
            if 'allowed_investment_grades' in config_dict:
                self.config.allowed_investment_grades = config_dict['allowed_investment_grades']
            
            if 'max_risk_level' in config_dict:
                self.config.max_risk_level = config_dict['max_risk_level']
            
            if 'auto_add_enabled' in config_dict:
                self.config.auto_add_enabled = bool(config_dict['auto_add_enabled'])
            
            if 'avoid_duplicates' in config_dict:
                self.config.avoid_duplicates = bool(config_dict['avoid_duplicates'])
            
            if 'max_auto_additions_per_day' in config_dict:
                self.config.max_auto_additions_per_day = int(config_dict['max_auto_additions_per_day'])
            
            logger.info(f"📋 配置更新成功")
            
        except Exception as e:
            logger.error(f"❌ 更新配置失败: {e}")
            raise ValueError(f"无效的配置参数: {e}")
    
    async def manual_screening_integration(self, screening_results: List[Dict]) -> Dict:
        """
        与现有股票筛选系统集成
        对筛选结果进行深度分析并自动管理股票池
        """
        try:
            logger.info(f"🔗 开始集成股票筛选结果进行深度分析")
            
            # 使用深度分析服务分析筛选结果
            analysis_results = await self.deep_analysis_service.analyze_screening_stocks(screening_results)
            
            # 处理分析结果
            processing_report = await self.process_analysis_results(analysis_results)
            
            # 添加集成特定信息
            processing_report.update({
                'integration_type': 'screening_results',
                'screening_results_count': len(screening_results),
                'analysis_success_rate': len(analysis_results) / len(screening_results) if screening_results else 0
            })
            
            logger.info(f"🎯 筛选集成完成: 筛选{len(screening_results)}只 -> 分析{len(analysis_results)}只 -> 添加{processing_report.get('added_to_pool', 0)}只")
            
            return processing_report
            
        except Exception as e:
            logger.error(f"❌ 筛选集成失败: {e}")
            return {
                'integration_type': 'screening_results',
                'screening_results_count': len(screening_results) if screening_results else 0,
                'error': str(e)
            }