"""
策略API服务
提供策略列表、配置和测试功能
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from ..database import DatabaseManager
from .strategy_base import get_all_strategies, get_strategy

logger = logging.getLogger(__name__)

class StrategyApiService:
    """策略API服务"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    async def get_available_strategies(self) -> Dict[str, Any]:
        """
        获取所有可用策略的详细信息
        
        Returns:
            包含策略信息的字典
        """
        try:
            all_strategies = get_all_strategies()
            
            # 构建策略信息
            strategy_info = {
                "basic_filter": [],
                "volume_price": [],
                "trend_following": [],
                "pattern_recognition": [],
                "comprehensive": []
            }
            
            # 策略类别映射
            category_map = {
                "low_price_filter": "basic_filter",
                "high_position_news_filter": "basic_filter",
                "ma_deviation_filter": "basic_filter",
                "gap_up_filter": "basic_filter",
                "turnover_filter": "basic_filter",
                "volume_ratio_strategy": "volume_price",
                "volume_price_relation": "volume_price",
                "volume_trend_analysis": "volume_price",
                "low_volume_low_price": "volume_price",
                "ma_golden_cross": "trend_following",
                "trend_momentum": "trend_following",
                "trend_reversal": "trend_following",
                "support_resistance": "pattern_recognition",
                "breakout_strategy": "pattern_recognition",
                "volume_pattern": "pattern_recognition",
                "comprehensive_analysis": "comprehensive"
            }
            
            for name, strategy in all_strategies.items():
                category = category_map.get(name, "other")
                
                # 获取策略参数信息
                params = self._get_strategy_parameters(strategy)
                
                strategy_detail = {
                    "name": name,
                    "display_name": strategy.description,
                    "description": strategy.description,
                    "weight": strategy.weight,
                    "parameters": params,
                    "enabled_by_default": True
                }
                
                if category in strategy_info:
                    strategy_info[category].append(strategy_detail)
            
            return {
                "success": True,
                "strategies": strategy_info,
                "total_count": len(all_strategies),
                "categories": {
                    "basic_filter": "基础过滤策略",
                    "volume_price": "量价关系策略", 
                    "trend_following": "趋势跟随策略",
                    "pattern_recognition": "技术形态策略",
                    "comprehensive": "综合分析策略"
                }
            }
            
        except Exception as e:
            logger.error(f"获取可用策略失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _get_strategy_parameters(self, strategy) -> List[Dict[str, Any]]:
        """获取策略参数定义"""
        params = []
        
        # 根据策略类型定义参数
        if hasattr(strategy, 'price_threshold'):
            params.append({
                "name": "price_threshold",
                "display_name": "价格阈值(元)",
                "type": "float",
                "default": getattr(strategy, 'price_threshold', 6.0),
                "min": 0.1,
                "max": 100.0,
                "unit": "元",
                "description": "低于此价格的股票将被过滤"
            })
        
        if hasattr(strategy, 'gain_threshold'):
            params.append({
                "name": "gain_threshold",
                "display_name": "涨幅阈值",
                "type": "float",
                "default": getattr(strategy, 'gain_threshold', 0.8),
                "min": 0.1,
                "max": 5.0,
                "unit": "倍",
                "description": "累计涨幅超过此比例视为高位(0.8表示80%)"
            })
            
        if hasattr(strategy, 'deviation_threshold'):
            params.append({
                "name": "deviation_threshold", 
                "display_name": "偏离阈值",
                "type": "float",
                "default": getattr(strategy, 'deviation_threshold', 1.2),
                "min": 1.0,
                "max": 2.0,
                "unit": "倍",
                "description": "股价相对均线偏离超过此比例视为过高(1.2表示120%)"
            })
            
        if hasattr(strategy, 'max_gap_days'):
            params.append({
                "name": "max_gap_days",
                "display_name": "最大跳空天数",
                "type": "int",
                "default": getattr(strategy, 'max_gap_days', 3),
                "min": 1,
                "max": 10,
                "description": "连续跳空超过此天数将被过滤"
            })
            
        if hasattr(strategy, 'max_turnover'):
            params.append({
                "name": "max_turnover",
                "display_name": "最大换手率(%)",
                "type": "float",
                "default": getattr(strategy, 'max_turnover', 40.0),
                "min": 10.0,
                "max": 100.0,
                "unit": "%",
                "description": "换手率超过此百分比将被过滤(非新股)"
            })
            
        if hasattr(strategy, 'volume_threshold'):
            params.append({
                "name": "volume_threshold",
                "display_name": "量比阈值",
                "type": "float",
                "default": getattr(strategy, 'volume_threshold', 2.0),
                "min": 0.5,
                "max": 10.0,
                "description": "量比超过此值视为放量"
            })
            
        if hasattr(strategy, 'ma_period'):
            params.append({
                "name": "ma_period",
                "display_name": "均线周期",
                "type": "int",
                "default": getattr(strategy, 'ma_period', 20),
                "min": 5,
                "max": 120,
                "description": "计算均线使用的周期"
            })
            
        
        return params
    
    async def test_strategy_config(self, strategy_name: str, config: Dict[str, Any], 
                                 sample_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        测试策略配置
        
        Args:
            strategy_name: 策略名称
            config: 策略配置参数
            sample_data: 用于测试的样本数据
            
        Returns:
            测试结果
        """
        try:
            # 获取策略
            strategy = get_strategy(strategy_name)
            if not strategy:
                return {
                    "status": "error",
                    "message": f"策略 {strategy_name} 不存在"
                }
            
            # 应用配置参数
            for param, value in config.items():
                if hasattr(strategy, param):
                    setattr(strategy, param, value)
            
            # 准备测试数据
            if not sample_data:
                sample_data = {
                    'stock_code': '000001',
                    'stock_name': '测试股票',
                    'close_price': 10.0,
                    'change_percent': 2.0
                }
            
            # 构建技术数据（根据配置模拟）
            technical_data = self._build_technical_data(sample_data, config)
            
            # 执行策略分析
            result = await strategy.analyze(sample_data, technical_data)
            
            return {
                "status": "success",
                "strategy_name": strategy_name,
                "config": config,
                "result": {
                    "pass_filter": result.pass_filter,
                    "signal": result.signal.value,
                    "strength": result.strength.value,
                    "score": result.score,
                    "confidence": result.confidence,
                    "reason": result.reason,
                    "risk_level": result.risk_level.value,
                    "details": result.details
                }
            }
            
        except Exception as e:
            logger.error(f"测试策略配置失败: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _build_technical_data(self, stock_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """根据测试配置构建技术指标数据"""
        close_price = stock_data.get('close_price', 10.0)
        
        # 基础技术数据
        technical_data = {
            'ma5': close_price * 0.98,
            'ma10': close_price * 0.96,
            'ma20': close_price * 0.95,
            'ma60': close_price * 0.90,
            'volume_ratio': 1.5,
            'turnover_rate': config.get('test_turnover', 5.0),
            'rsi': 50,
            'macd': 0.1,
            'kdj_k': 50,
            'kdj_d': 50
        }
        
        # 根据配置调整数据
        if 'test_price' in config:
            # 调整均线以测试偏离
            technical_data['ma20'] = config['test_price'] / 1.1
            
        if 'test_turnover' in config:
            technical_data['turnover_rate'] = config['test_turnover']
            
        if 'test_volume_ratio' in config:
            technical_data['volume_ratio'] = config['test_volume_ratio']
            
        if config.get('test_gap', False):
            technical_data['has_gap_up'] = True
            technical_data['gap_ratio'] = 0.03
            
        if config.get('test_limit_up', False):
            technical_data['is_limit_up'] = True
            
        # 特殊处理跳空策略的测试数据
        change_percent = stock_data.get('change_percent', 0)
        if change_percent > 0:
            technical_data['has_gap_up'] = True
            technical_data['gap_ratio'] = min(change_percent / 100, 0.1)  # 将涨幅转换为跳空比例
            
        return technical_data