"""
高级筛选服务
整合所有策略，提供统一的筛选接口
"""
import asyncio
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np

from .strategy_base import (
    strategy_registry, StrategyResult, SignalType, 
    SignalStrength, RiskLevel
)
from .technical_indicator_service import get_technical_indicator_service
from .quota_manager import get_quota_manager

logger = logging.getLogger(__name__)

def convert_numpy_types(obj):
    """转换 numpy 类型和其他不可序列化类型为 Python 原生类型"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj

class AdvancedScreeningService:
    """高级筛选服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.tech_service = get_technical_indicator_service(db_manager)
        self.quota_manager = get_quota_manager()
        
    async def screen_stocks_advanced(self, 
                                   stock_codes: List[str],
                                   strategy_config: Dict,
                                   screening_date: str = None) -> List[Dict]:
        """
        执行高级股票筛选
        
        Args:
            stock_codes: 股票代码列表
            strategy_config: 策略配置
            screening_date: 筛选日期
            
        Returns:
            筛选结果列表
        """
        # 检查配额
        if not self.quota_manager.check_quota("strategy_screening"):
            logger.warning("⚠️ 策略筛选配额已用尽，返回空结果")
            return []
        
        if screening_date is None:
            screening_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"🚀 开始高级筛选，股票数量: {len(stock_codes)}")
        
        # 记录一次请求
        self.quota_manager.record_request("strategy_screening")
        
        results = []
        
        # 确保技术指标已计算
        logger.info("📊 确保技术指标数据...")
        await self._ensure_technical_indicators(stock_codes, screening_date)
        
        # 并行处理股票
        logger.info("🔄 并行分析股票...")
        tasks = []
        batch_size = 20  # 每批处理20只股票
        
        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            for stock_code in batch_codes:
                task = self._analyze_single_stock(stock_code, strategy_config, screening_date)
                tasks.append(task)
        
        # 执行分析
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        success_count = 0
        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                logger.debug(f"分析股票失败: {stock_codes[i % len(stock_codes)]}, {result}")
                continue
            
            if result and result.get('pass_filter'):
                results.append(result)
                success_count += 1
        
        # 按评分排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 保存结果
        await self._save_screening_results(results, strategy_config, screening_date)
        
        logger.info(f"✅ 高级筛选完成，找到 {len(results)} 只符合条件的股票 (成功分析: {success_count})")
        return results
    
    async def _ensure_technical_indicators(self, stock_codes: List[str], screening_date: str):
        """确保技术指标已计算"""
        # 检查哪些股票缺少技术指标
        missing_codes = []
        
        import sqlite3
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            for code in stock_codes[:10]:  # 限制检查数量
                cursor.execute('''
                    SELECT COUNT(*) FROM stock_technical_indicators
                    WHERE stock_code = ? AND trade_date = ?
                ''', (code, screening_date))
                
                if cursor.fetchone()[0] == 0:
                    missing_codes.append(code)
        
        if missing_codes:
            logger.info(f"计算缺失的技术指标: {len(missing_codes)} 只股票")
            await self.tech_service.batch_calculate_indicators(missing_codes, screening_date)
    
    async def _analyze_single_stock(self, 
                                  stock_code: str, 
                                  strategy_config: Dict,
                                  screening_date: str) -> Optional[Dict]:
        """分析单只股票"""
        try:
            # 获取股票基础数据
            stock_data = await self._get_stock_data(stock_code, screening_date)
            if not stock_data:
                return None
            
            # 获取技术指标数据
            technical_data = await self._get_technical_data(stock_code, screening_date)
            if not technical_data:
                # 如果没有技术指标，尝试计算
                indicators = await self.tech_service.calculate_all_indicators(stock_code)
                if indicators:
                    await self.tech_service.save_indicators_to_db(stock_code, screening_date, indicators)
                    technical_data = indicators
                else:
                    technical_data = {}
            
            # 执行策略分析
            strategy_results = []
            total_score = 0
            total_weight = 0
            
            # 获取启用的策略 - 修复策略配置解析
            strategy_groups = strategy_config.get('strategy_groups', {})
            advanced_filter = strategy_groups.get('advanced_filter', {})
            configured_strategies = advanced_filter.get('strategies', {})
            
            logger.info(f"📋 配置的策略: {list(configured_strategies.keys())}")
            
            # 执行配置的策略
            for strategy_name, strategy_cfg in configured_strategies.items():
                if not strategy_cfg.get('enabled', True):
                    logger.debug(f"跳过未启用的策略: {strategy_name}")
                    continue
                    
                strategy = strategy_registry.get_strategy(strategy_name)
                if not strategy:
                    logger.warning(f"策略不存在: {strategy_name}")
                    continue
                
                # 设置策略参数
                strategy_params = strategy_cfg.get('params', {})
                if strategy_params:
                    logger.info(f"🔧 为策略 {strategy_name} 设置参数: {strategy_params}")
                    # 更新策略参数
                    if hasattr(strategy, 'update_parameters'):
                        strategy.update_parameters(strategy_params)
                
                try:
                    result = await strategy.analyze(stock_data, technical_data)
                    strategy_results.append({
                        'strategy': strategy_name,
                        'result': result.to_dict() if hasattr(result, 'to_dict') else result.__dict__
                    })
                    
                    if result.pass_filter:
                        weight = strategy_cfg.get('weight', 1.0)
                        total_score += result.score * weight
                        total_weight += weight
                        logger.debug(f"策略 {strategy_name} 通过筛选，评分: {result.score}, 权重: {weight}")
                    else:
                        logger.debug(f"策略 {strategy_name} 未通过筛选，评分: {result.score}")
                        
                except Exception as e:
                    logger.warning(f"策略 {strategy_name} 执行失败: {e}")
                    continue
            
            # 计算综合评分
            final_score = total_score / total_weight if total_weight > 0 else 0
            
            # 判断是否通过筛选
            min_score = strategy_config.get('min_score', 60)
            pass_filter = final_score >= min_score
            
            if not pass_filter:
                return None
            
            # 生成最终信号
            final_signal = self._generate_final_signal(strategy_results)
            
            return {
                'stock_code': stock_code,
                'stock_name': stock_data.get('stock_name', stock_code),
                'screening_date': screening_date,
                'pass_filter': True,
                'score': final_score,
                'signal': final_signal['signal'],
                'strength': final_signal['strength'],
                'risk_level': final_signal['risk_level'],
                'current_price': stock_data.get('close_price'),
                'change_percent': stock_data.get('change_percent', 0),
                'volume': stock_data.get('volume', 0),
                'strategy_results': strategy_results,
                'technical_data': technical_data
            }
            
        except Exception as e:
            logger.debug(f"分析股票失败: {stock_code}, {e}")
            return None
    
    def _generate_final_signal(self, strategy_results: List[Dict]) -> Dict:
        """生成最终信号"""
        buy_count = 0
        sell_count = 0
        hold_count = 0
        total_score = 0
        
        for sr in strategy_results:
            result = sr['result']
            signal = result.get('signal')
            score = result.get('score', 0)
            
            total_score += score
            
            if signal == SignalType.BUY.value:
                buy_count += 1
            elif signal == SignalType.SELL.value:
                sell_count += 1
            elif signal == SignalType.HOLD.value:
                hold_count += 1
        
        # 简单的信号合成逻辑
        total_signals = buy_count + sell_count + hold_count
        avg_score = total_score / max(len(strategy_results), 1)
        
        if buy_count > sell_count and buy_count > 0:
            strength = SignalStrength.STRONG if buy_count >= 3 else SignalStrength.MEDIUM
            risk_level = RiskLevel.MEDIUM if avg_score > 70 else RiskLevel.HIGH
            return {
                'signal': SignalType.BUY.value,
                'strength': strength.value,
                'risk_level': risk_level.value
            }
        elif sell_count > 0:
            return {
                'signal': SignalType.SELL.value,
                'strength': SignalStrength.MEDIUM.value,
                'risk_level': RiskLevel.HIGH.value
            }
        else:
            return {
                'signal': SignalType.HOLD.value,
                'strength': SignalStrength.WEAK.value,
                'risk_level': RiskLevel.LOW.value
            }
    
    async def _get_stock_data(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取股票基础数据"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取最近的交易数据
                cursor.execute('''
                    SELECT * FROM daily_stock_changes
                    WHERE stock_code = ? AND trade_date <= ?
                    ORDER BY trade_date DESC
                    LIMIT 1
                ''', (stock_code, trade_date))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    stock_data = dict(zip(columns, row))
                    
                    # 获取股票名称
                    cursor.execute('SELECT name FROM stock_info WHERE symbol = ?', (stock_code,))
                    name_row = cursor.fetchone()
                    if name_row:
                        stock_data['stock_name'] = name_row[0]
                    
                    return stock_data
                return None
                
        except Exception as e:
            logger.debug(f"获取股票数据失败: {stock_code}, {e}")
            return None
    
    async def _get_technical_data(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取技术指标数据"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM stock_technical_indicators
                    WHERE stock_code = ? AND trade_date = ?
                ''', (stock_code, trade_date))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.debug(f"获取技术数据失败: {stock_code}, {e}")
            return None
    
    async def _save_screening_results(self, 
                                    results: List[Dict],
                                    strategy_config: Dict,
                                    screening_date: str):
        """保存筛选结果"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 清理当天的旧结果
                cursor.execute('''
                    DELETE FROM advanced_screening_results
                    WHERE screening_date = ? AND strategy_type = ?
                ''', (screening_date, 'advanced_daily'))
                
                # 保存新结果
                for result in results:
                    strategies_passed = [sr['strategy'] for sr in result.get('strategy_results', [])]
                    
                    cursor.execute('''
                        INSERT INTO advanced_screening_results
                        (stock_code, stock_name, screening_date, strategy_type,
                         signal_type, signal_strength, score, confidence, reason,
                         risk_level, current_price, technical_data, strategies_passed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result['stock_code'],
                        result['stock_name'],
                        screening_date,
                        'advanced_daily',
                        result['signal'],
                        result['strength'],
                        convert_numpy_types(result['score']),
                        0.8,  # 默认置信度
                        f"通过{len(result['strategy_results'])}个策略",
                        result['risk_level'],
                        convert_numpy_types(result['current_price']),
                        json.dumps(convert_numpy_types(result.get('technical_data', {}))),
                        json.dumps(strategies_passed)
                    ))
                
                conn.commit()
                logger.info(f"💾 保存筛选结果成功: {len(results)} 条")
                
        except Exception as e:
            logger.error(f"❌ 保存筛选结果失败: {e}")
    
    async def get_screening_results(self, 
                                   screening_date: str = None,
                                   strategy_type: str = 'advanced_daily',
                                   limit: int = 100) -> List[Dict]:
        """获取筛选结果"""
        if screening_date is None:
            screening_date = datetime.now().strftime('%Y-%m-%d')
        
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM advanced_screening_results
                    WHERE screening_date = ? AND strategy_type = ?
                    ORDER BY score DESC
                    LIMIT ?
                ''', (screening_date, strategy_type, limit))
                
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                results = []
                for row in rows:
                    result = dict(zip(columns, row))
                    
                    # 解析JSON字段
                    if result.get('technical_data'):
                        try:
                            result['technical_data'] = json.loads(result['technical_data'])
                        except:
                            result['technical_data'] = {}
                    
                    if result.get('strategies_passed'):
                        try:
                            result['strategies_passed'] = json.loads(result['strategies_passed'])
                        except:
                            result['strategies_passed'] = []
                    
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"获取筛选结果失败: {e}")
            return []

# 全局实例
_advanced_screening_service = None

def get_advanced_screening_service(db_manager):
    """获取高级筛选服务实例"""
    global _advanced_screening_service
    if _advanced_screening_service is None:
        _advanced_screening_service = AdvancedScreeningService(db_manager)
    return _advanced_screening_service