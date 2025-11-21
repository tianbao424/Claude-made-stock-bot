"""
技术指标计算服务
支持MA、KDJ、RSI、MACD、OBV等常用指标
不依赖TA-Lib，使用纯Python+Pandas实现
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
import sqlite3

logger = logging.getLogger(__name__)

class TechnicalIndicatorService:
    """技术指标计算服务"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    async def calculate_all_indicators(self, stock_code: str, days: int = 60) -> Dict:
        """
        计算股票的所有技术指标
        
        Args:
            stock_code: 股票代码
            days: 计算天数
            
        Returns:
            包含所有指标的字典
        """
        try:
            # 获取历史数据
            df = await self._get_stock_history(stock_code, days)
            if df is None or len(df) < 5:  # 降低最小数据要求
                logger.warning(f"股票 {stock_code} 历史数据不足 (少于5条)")
                return {}
            
            indicators = {}
            
            # 移动平均线
            indicators.update(self._calculate_moving_averages(df))
            
            # 量价指标
            indicators.update(self._calculate_volume_indicators(df))
            
            # 技术指标
            indicators.update(self._calculate_technical_indicators(df))
            
            # 形态指标
            indicators.update(self._calculate_pattern_indicators(df))
            
            return indicators
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {stock_code}, {e}")
            return {}
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> Dict:
        """计算移动平均线 - 优化版"""
        close = df['close_price']
        result = {}
        
        # 动态调整计算周期，确保有足够数据
        # 针对30天数据优化的均线周期
        periods = {
            'ma5': (5, 3),    # (期望周期, 最小周期)
            'ma10': (10, 5),
            'ma20': (20, 10),
            'ma30': (30, 15)   # 用ma30替代ma60，更适合30天数据
        }
        
        for ma_name, (target_period, min_period) in periods.items():
            if len(close) >= min_period:
                # 使用可用的最大周期，但不超过目标周期
                actual_period = min(target_period, len(close))
                
                # 数据不足时使用EMA，数据充足时使用SMA
                if len(close) < target_period:
                    # 指数加权移动平均，参数适应目标周期
                    alpha = 2 / (target_period + 1)
                    ma_value = close.ewm(alpha=alpha, min_periods=min_period).mean().iloc[-1]
                else:
                    # 标准简单移动平均
                    ma_value = close.rolling(window=actual_period, min_periods=min_period).mean().iloc[-1]
                
                result[ma_name] = float(ma_value) if not pd.isna(ma_value) else None
            else:
                result[ma_name] = None
        
        # 添加均线趋势分析
        result.update(self._calculate_ma_trends(result))
        
        return result
    
    def _calculate_ma_trends(self, ma_dict: Dict) -> Dict:
        """计算均线趋势关系"""
        trends = {}
        
        # 收集有效的均线值
        mas = [ma_dict.get(f'ma{period}') for period in [5, 10, 20, 30]]
        valid_mas = [ma for ma in mas if ma is not None]
        
        if len(valid_mas) >= 2:
            # 检查多头排列（短期MA > 长期MA）
            trends['is_bullish_aligned'] = all(
                valid_mas[i] >= valid_mas[i+1] for i in range(len(valid_mas)-1)
            )
            
            # 检查空头排列（短期MA < 长期MA）
            trends['is_bearish_aligned'] = all(
                valid_mas[i] <= valid_mas[i+1] for i in range(len(valid_mas)-1)
            )
        
        # 金叉死叉信号
        if ma_dict.get('ma5') and ma_dict.get('ma10'):
            ma5_ma10_ratio = ma_dict['ma5'] / ma_dict['ma10']
            trends['ma5_ma10_ratio'] = ma5_ma10_ratio
            trends['golden_cross_signal'] = ma5_ma10_ratio > 1.01  # 金叉信号
            trends['death_cross_signal'] = ma5_ma10_ratio < 0.99   # 死叉信号
        
        # 价格与均线关系
        if ma_dict.get('ma20'):
            trends['price_above_ma20'] = True  # 这里需要当前价格，暂时设为True
            trends['ma20_slope'] = self._calculate_ma_slope(ma_dict.get('ma20'))
        if ma_dict.get('ma30'):
            trends['price_above_ma30'] = True
            trends['ma30_slope'] = self._calculate_ma_slope(ma_dict.get('ma30'))
        
        return trends
    
    def _calculate_ma_slope(self, ma_value: float) -> str:
        """简化的均线斜率计算"""
        # 这里需要历史均线数据才能准确计算斜率
        # 暂时返回中性
        return "neutral"
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict:
        """计算量价指标 - 优化版"""
        volume = df['volume']
        close = df['close_price']
        amount = df.get('amount', pd.Series([0] * len(df)))
        
        current_volume = volume.iloc[-1] if len(volume) > 0 else 0
        current_close = close.iloc[-1] if len(close) > 0 else 0
        current_amount = amount.iloc[-1] if len(amount) > 0 else 0
        
        indicators = {}
        
        # 量比计算 - 改进版
        indicators.update(self._calculate_volume_ratio(volume, current_volume))
        
        # 换手率计算 - 修复版
        indicators.update(self._calculate_turnover_rate(df, current_volume, current_amount))
        
        # 成交量统计
        indicators['avg_volume_5d'] = volume.rolling(window=5).mean().iloc[-1] if len(volume) >= 5 else None
        indicators['avg_volume_20d'] = volume.rolling(window=20).mean().iloc[-1] if len(volume) >= 20 else None
        
        # 量价配合度
        indicators.update(self._calculate_volume_price_relationship(df))
        
        return indicators
    
    def _calculate_volume_ratio(self, volume: pd.Series, current_volume: float) -> Dict:
        """计算量比 - 精确版"""
        result = {}
        
        # 标准量比：当日成交量 / 近N日平均成交量
        for period in [5, 10, 20]:
            if len(volume) >= period:
                avg_volume = volume.rolling(window=period).mean().iloc[-1]
                if avg_volume and avg_volume > 0:
                    ratio = current_volume / avg_volume
                    result[f'volume_ratio_{period}d'] = round(ratio, 2)
        
        # 主要量比指标（使用5日平均）
        if result.get('volume_ratio_5d'):
            result['volume_ratio'] = result['volume_ratio_5d']
            
            # 量比分类
            ratio = result['volume_ratio']
            if ratio >= 5.0:
                result['volume_level'] = 'extreme_high'  # 极度放量
            elif ratio >= 3.0:
                result['volume_level'] = 'very_high'     # 严重放量
            elif ratio >= 2.0:
                result['volume_level'] = 'high'          # 放量
            elif ratio >= 1.5:
                result['volume_level'] = 'moderate_high' # 温和放量
            elif ratio >= 0.8:
                result['volume_level'] = 'normal'        # 正常
            elif ratio >= 0.5:
                result['volume_level'] = 'low'           # 缩量
            else:
                result['volume_level'] = 'very_low'      # 地量
        
        return result
    
    def _calculate_turnover_rate(self, df: pd.DataFrame, current_volume: float, current_amount: float) -> Dict:
        """计算换手率 - 修复版"""
        result = {}
        
        # 方法1: 如果数据中已有换手率，直接使用
        if 'turnover_rate' in df.columns:
            turnover_rate = df['turnover_rate'].iloc[-1]
            if pd.notna(turnover_rate) and turnover_rate > 0:
                result['turnover_rate'] = round(float(turnover_rate), 2)
                result['turnover_method'] = 'direct'
                return result
        
        # 方法2: 根据成交量和流通股本估算
        if current_volume > 0:
            # 根据股票代码估算流通股本（简化方法）
            stock_code = df.get('stock_code', '').iloc[0] if 'stock_code' in df.columns else None
            estimated_shares = self._estimate_shares_outstanding(stock_code, current_amount, current_volume)
            
            if estimated_shares > 0:
                # 换手率 = 成交量 / 流通股本 * 100%
                turnover_rate = (current_volume / estimated_shares) * 100
                result['turnover_rate'] = round(min(turnover_rate, 100), 2)  # 限制最大100%
                result['turnover_method'] = 'estimated'
            else:
                # 方法3: 根据成交额反推（极简版）
                if current_amount > 0:
                    avg_price = current_amount / current_volume if current_volume > 0 else 0
                    if avg_price > 0:
                        # 假设流通市值 = 成交额 * 某个倍数（根据换手率反推）
                        estimated_turnover = min((current_amount / 10000000) * 0.1, 20)  # 简化估算
                        result['turnover_rate'] = round(estimated_turnover, 2)
                        result['turnover_method'] = 'amount_based'
        
        # 换手率分类
        if 'turnover_rate' in result:
            rate = result['turnover_rate']
            if rate >= 20:
                result['turnover_level'] = 'extreme_high'    # 极度活跃
            elif rate >= 10:
                result['turnover_level'] = 'very_high'       # 非常活跃
            elif rate >= 5:
                result['turnover_level'] = 'high'            # 活跃
            elif rate >= 2:
                result['turnover_level'] = 'moderate'        # 适中
            elif rate >= 1:
                result['turnover_level'] = 'low'             # 清淡
            else:
                result['turnover_level'] = 'very_low'        # 冷清
        
        return result
    
    def _estimate_shares_outstanding(self, stock_code: str, amount: float, volume: float) -> float:
        """估算流通股本（简化方法）"""
        if not stock_code or amount <= 0 or volume <= 0:
            return 0
        
        # 根据股票类型和市值估算流通股本
        avg_price = amount / volume
        
        # 根据股票代码前缀判断板块
        if stock_code.startswith('60'):  # 沪市主板
            if avg_price > 50:
                return 50000  # 高价股，流通盘较小（万股）
            elif avg_price > 20:
                return 100000  # 中价股
            else:
                return 200000  # 低价股，流通盘较大
        elif stock_code.startswith('688'):  # 科创板
            return 40000  # 科创板股票流通盘相对较小
        elif stock_code.startswith('30'):  # 创业板
            return 80000
        else:  # 深市主板、中小板
            return 120000
    
    def _calculate_volume_price_relationship(self, df: pd.DataFrame) -> Dict:
        """计算量价关系"""
        if len(df) < 2:
            return {}
        
        # 获取最近两天的数据
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        price_change = current['close_price'] - previous['close_price']
        volume_change = current['volume'] - previous['volume']
        
        result = {}
        
        # 量价关系分类
        if price_change > 0 and volume_change > 0:
            result['volume_price_pattern'] = 'rise_with_volume'      # 价涨量增
        elif price_change > 0 and volume_change < 0:
            result['volume_price_pattern'] = 'rise_without_volume'   # 价涨量缩
        elif price_change < 0 and volume_change > 0:
            result['volume_price_pattern'] = 'fall_with_volume'      # 价跌量增
        elif price_change < 0 and volume_change < 0:
            result['volume_price_pattern'] = 'fall_without_volume'   # 价跌量缩
        else:
            result['volume_price_pattern'] = 'neutral'               # 中性
        
        # 量价配合度评分（1-10分）
        abs_price_change_pct = abs(price_change / previous['close_price']) if previous['close_price'] > 0 else 0
        abs_volume_change_pct = abs(volume_change / previous['volume']) if previous['volume'] > 0 else 0
        
        if abs_price_change_pct > 0.03 and abs_volume_change_pct > 0.5:  # 价量齐变
            result['volume_price_score'] = 9
        elif abs_price_change_pct > 0.02 and abs_volume_change_pct > 0.3:
            result['volume_price_score'] = 7
        elif abs_price_change_pct > 0.01 or abs_volume_change_pct > 0.2:
            result['volume_price_score'] = 5
        else:
            result['volume_price_score'] = 3
        
        return result
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """计算技术指标"""
        high = df['high_price']
        low = df['low_price']
        close = df['close_price']
        volume = df['volume']
        
        indicators = {}
        
        # KDJ指标
        if len(close) >= 9:
            kdj = self._calculate_kdj(high, low, close)
            indicators.update(kdj)
        
        # RSI指标
        for period in [6, 12, 24]:
            if len(close) >= period:
                rsi = self._calculate_rsi(close, period)
                indicators[f'rsi_{period}'] = rsi
        
        # MACD指标
        if len(close) >= 26:
            macd = self._calculate_macd(close)
            indicators.update(macd)
        
        # OBV指标
        if len(volume) > 1:
            obv = self._calculate_obv(close, volume)
            indicators['obv'] = obv
        
        return indicators
    
    def _calculate_kdj(self, high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9) -> Dict:
        """计算KDJ指标"""
        try:
            # 计算RSV
            low_min = low.rolling(window=n).min()
            high_max = high.rolling(window=n).max()
            rsv = (close - low_min) / (high_max - low_min) * 100
            
            # 计算K值
            k = rsv.ewm(alpha=1/3).mean()
            
            # 计算D值
            d = k.ewm(alpha=1/3).mean()
            
            # 计算J值
            j = 3 * k - 2 * d
            
            return {
                'kdj_k': k.iloc[-1] if not pd.isna(k.iloc[-1]) else None,
                'kdj_d': d.iloc[-1] if not pd.isna(d.iloc[-1]) else None,
                'kdj_j': j.iloc[-1] if not pd.isna(j.iloc[-1]) else None
            }
        except Exception as e:
            logger.debug(f"KDJ计算失败: {e}")
            return {'kdj_k': None, 'kdj_d': None, 'kdj_j': None}
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> Optional[float]:
        """计算RSI指标"""
        try:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
        except Exception as e:
            logger.debug(f"RSI计算失败: {e}")
            return None
    
    def _calculate_macd(self, close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """计算MACD指标"""
        try:
            # 计算快慢EMA
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            
            # DIF线
            dif = ema_fast - ema_slow
            
            # DEA线
            dea = dif.ewm(span=signal).mean()
            
            # MACD柱
            hist = (dif - dea) * 2
            
            return {
                'macd_dif': dif.iloc[-1] if not pd.isna(dif.iloc[-1]) else None,
                'macd_dea': dea.iloc[-1] if not pd.isna(dea.iloc[-1]) else None,
                'macd_hist': hist.iloc[-1] if not pd.isna(hist.iloc[-1]) else None
            }
        except Exception as e:
            logger.debug(f"MACD计算失败: {e}")
            return {'macd_dif': None, 'macd_dea': None, 'macd_hist': None}
    
    def _calculate_obv(self, close: pd.Series, volume: pd.Series) -> Optional[float]:
        """计算OBV指标"""
        try:
            obv = [0]
            for i in range(1, len(close)):
                if close.iloc[i] > close.iloc[i-1]:
                    obv.append(obv[-1] + volume.iloc[i])
                elif close.iloc[i] < close.iloc[i-1]:
                    obv.append(obv[-1] - volume.iloc[i])
                else:
                    obv.append(obv[-1])
            
            return obv[-1] if obv else None
        except Exception as e:
            logger.debug(f"OBV计算失败: {e}")
            return None
    
    def _calculate_pattern_indicators(self, df: pd.DataFrame) -> Dict:
        """计算形态指标"""
        if len(df) < 5:
            return {}
        
        try:
            close = df['close_price']
            high = df['high_price']
            low = df['low_price']
            change_percent = df.get('change_percent', pd.Series([0] * len(df)))
            
            # 是否创新高（根据可用数据动态调整窗口）
            window_size = min(20, len(df) - 1) if len(df) > 1 else 1
            is_new_high = close.iloc[-1] >= high.rolling(window=window_size).max().iloc[-1]
            
            # 是否涨停（简化判断）
            current_change = change_percent.iloc[-1] if len(change_percent) > 0 else 0
            is_limit_up = current_change >= 9.8  # 接近涨停
            
            # 向上跳空检测
            has_gap_up = False
            gap_ratio = 0
            if len(df) >= 2:
                yesterday_high = high.iloc[-2]
                today_low = low.iloc[-1]
                if today_low > yesterday_high:
                    has_gap_up = True
                    gap_ratio = (today_low - yesterday_high) / yesterday_high
            
            return {
                'is_new_high': bool(is_new_high),
                'is_limit_up': bool(is_limit_up),
                'has_gap_up': bool(has_gap_up),
                'gap_ratio': float(gap_ratio)
            }
        except Exception as e:
            logger.debug(f"形态指标计算失败: {e}")
            return {
                'is_new_high': False,
                'is_limit_up': False,
                'has_gap_up': False,
                'gap_ratio': 0.0
            }
    
    async def _get_stock_history(self, stock_code: str, days: int) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')  # 扩大范围
            
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = '''
                    SELECT trade_date, open_price, high_price, low_price, 
                           close_price, volume, turnover, change_percent
                    FROM daily_stock_changes
                    WHERE stock_code = ? AND trade_date >= ?
                    ORDER BY trade_date DESC
                    LIMIT ?
                '''
                
                df = pd.read_sql_query(query, conn, params=(stock_code, start_date, days))
                
                if not df.empty:
                    # 按日期排序（从旧到新）
                    df = df.sort_values('trade_date').reset_index(drop=True)
                    
                    # 确保数据类型正确
                    numeric_columns = ['open_price', 'high_price', 'low_price', 'close_price', 
                                     'volume', 'turnover', 'change_percent']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    logger.debug(f"获取到 {stock_code} 的 {len(df)} 条历史数据")
                    return df
                else:
                    logger.debug(f"未找到 {stock_code} 的历史数据")
                    return None
                
        except Exception as e:
            logger.error(f"获取历史数据失败: {stock_code}, {e}")
            return None
    
    async def save_indicators_to_db(self, stock_code: str, trade_date: str, indicators: Dict):
        """保存技术指标到数据库"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 准备数据
                data = {
                    'stock_code': stock_code,
                    'trade_date': trade_date,
                    'updated_at': datetime.now().isoformat()
                }
                
                # 添加指标数据
                for key, value in indicators.items():
                    # 确保布尔值转换为整数
                    if isinstance(value, bool):
                        data[key] = int(value)
                    elif value is not None:
                        data[key] = value
                
                # 动态构建SQL
                columns = list(data.keys())
                placeholders = ['?' for _ in columns]
                values = list(data.values())
                
                sql = f'''
                    INSERT OR REPLACE INTO stock_technical_indicators 
                    ({', '.join(columns)}) VALUES ({', '.join(placeholders)})
                '''
                
                cursor.execute(sql, values)
                conn.commit()
                
                logger.debug(f"✅ 保存技术指标成功: {stock_code} {trade_date}")
                
        except Exception as e:
            logger.error(f"❌ 保存技术指标失败: {stock_code}, {e}")
    
    async def batch_calculate_indicators(self, stock_codes: List[str], trade_date: str = None) -> int:
        """批量计算技术指标"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        success_count = 0
        total_count = len(stock_codes)
        
        logger.info(f"开始批量计算技术指标: {total_count} 只股票")
        
        # 分批处理，避免内存过大
        batch_size = 50
        for i in range(0, total_count, batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            
            # 并发处理批次内的股票
            tasks = []
            for stock_code in batch_codes:
                task = self._calculate_single_stock_indicators(stock_code, trade_date)
                tasks.append(task)
            
            # 执行并发任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.debug(f"计算失败: {batch_codes[j]}, {result}")
                elif result:
                    success_count += 1
            
            # 进度报告
            current_progress = min(i + batch_size, total_count)
            logger.info(f"技术指标计算进度: {current_progress}/{total_count} (成功: {success_count})")
        
        logger.info(f"✅ 批量计算完成: {success_count}/{total_count}")
        return success_count
    
    async def _calculate_single_stock_indicators(self, stock_code: str, trade_date: str) -> bool:
        """计算单只股票的技术指标"""
        try:
            indicators = await self.calculate_all_indicators(stock_code)
            if indicators:
                await self.save_indicators_to_db(stock_code, trade_date, indicators)
                return True
            return False
        except Exception as e:
            logger.debug(f"计算单股指标失败: {stock_code}, {e}")
            return False
    
    async def get_indicators_from_db(self, stock_code: str, trade_date: str = None) -> Optional[Dict]:
        """从数据库获取技术指标"""
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
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
            logger.error(f"获取技术指标失败: {stock_code}, {e}")
            return None

# 全局实例
_technical_indicator_service = None

def get_technical_indicator_service(db_manager):
    """获取技术指标服务实例"""
    global _technical_indicator_service
    if _technical_indicator_service is None:
        _technical_indicator_service = TechnicalIndicatorService(db_manager)
    return _technical_indicator_service