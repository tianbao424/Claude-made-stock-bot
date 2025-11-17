"""
股票甄选服务
实现强势股识别、连续涨幅筛选等功能
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, StockScreening, DailyStockChange
from services.unified_tencent_collector import get_unified_collector

logger = logging.getLogger(__name__)

@dataclass
class ScreeningCriteria:
    """筛选条件"""
    screening_type: str
    min_consecutive_days: int = 3
    min_rise_percent: float = 7.0
    min_volume: int = 0
    market_filter: List[str] = None  # ['SH', 'SZ', 'HK']
    
    def to_dict(self) -> Dict:
        return {
            'screening_type': self.screening_type,
            'min_consecutive_days': self.min_consecutive_days,
            'min_rise_percent': self.min_rise_percent,
            'min_volume': self.min_volume,
            'market_filter': self.market_filter or ['SH', 'SZ', 'HK']
        }

@dataclass
class ScreeningResult:
    """筛选结果"""
    stock_code: str
    stock_name: str
    market: str
    consecutive_days: int
    avg_rise_percent: float
    total_volume: int
    avg_volume: int
    close_price: float
    turnover_rate: float = None
    market_cap: float = 0.0  # 市值(亿元)
    pe_ratio: float = 0.0    # 市盈率
    daily_changes: List[Dict] = None  # 每日涨跌详情

@dataclass
class ScreeningResponse:
    """筛选响应，包含结果和元数据"""
    results: List[ScreeningResult]
    screening_date: str  # 实际使用的数据日期
    total_count: int

class StockScreeningService:
    """股票甄选服务"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def collect_daily_data(self, trade_date: str = None) -> int:
        """
        收集指定日期的股票数据（使用统一腾讯采集器）
        
        Args:
            trade_date: 交易日期，格式YYYY-MM-DD，默认为智能判断的目标日期
            
        Returns:
            收集到的股票数量
        """
        logger.info(f"🔄 开始使用统一腾讯采集器收集股票数据...")
        
        try:
            # 使用统一腾讯采集器
            unified_collector = get_unified_collector(self.db_manager)
            result = await unified_collector.collect_daily_stock_data(trade_date)
            
            if result.success:
                logger.info(f"✅ 统一数据收集成功: {result.successful_records}/{result.total_collected} "
                           f"({result.successful_records/result.total_collected*100:.1f}%) "
                           f"用时 {result.duration_seconds:.1f}s")
                return result.successful_records
            else:
                logger.error(f"❌ 统一数据收集失败: {result.error_message}")
                return 0
            
        except Exception as e:
            logger.error(f"❌ 统一数据收集异常: {e}")
            return 0
    
    async def _collect_a_stock_data(self, trade_date: str) -> List[DailyStockChange]:
        """收集A股涨跌数据"""
        stocks_data = []
        
        try:
            # 检查日期是否是今天，如果是今天则使用实时数据
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 优先尝试使用实时数据接口，因为它能提供完整的市场快照
            # 即使是历史数据，实时接口也比逐个获取历史数据更可靠
            try:
                logger.info(f"尝试使用实时数据接口获取 {trade_date} 的数据...")
                df = akshare_service.ak.stock_zh_a_spot_em()
                
                if df is not None and not df.empty and len(df) > 4000:
                    logger.info(f"✅ 实时接口获取到 {len(df)} 只股票数据")
                    
                    for _, row in df.iterrows():
                        try:
                            stock_data = DailyStockChange(
                                stock_code=str(row.get('代码', '')),
                                trade_date=trade_date,
                                change_percent=float(row.get('涨跌幅', 0)),
                                close_price=float(row.get('最新价', 0)),
                                open_price=float(row.get('今开', 0)),
                                high_price=float(row.get('最高', 0)),
                                low_price=float(row.get('最低', 0)),
                                volume=int(row.get('成交量', 0)),
                                turnover=float(row.get('成交额', 0)),
                                market=self._get_market_from_code(str(row.get('代码', ''))),
                                # 新增市值和指标数据
                                total_market_cap=float(row.get('总市值', 0)) / 10000,  # 转换为万元
                                circulating_market_cap=float(row.get('流通市值', 0)) / 10000,  # 转换为万元
                                turnover_rate=float(row.get('换手率', 0)),
                                pe_ratio=float(row.get('市盈率-动态', 0)),
                                pb_ratio=float(row.get('市净率', 0)),
                                created_at=datetime.now().isoformat()
                            )
                            stocks_data.append(stock_data)
                            
                        except Exception as e:
                            logger.debug(f"处理股票数据失败: {row.get('代码', 'unknown')}, {e}")
                            continue
                    
                    logger.info(f"✅ 实时接口成功处理了 {len(stocks_data)} 条数据")
                    return stocks_data
                else:
                    logger.warning(f"实时接口数据不足或获取失败，数据量: {len(df) if df is not None else 0}")
            except Exception as e:
                logger.warning(f"实时数据接口调用失败: {e}")
            
            # 如果实时接口失败，才使用历史数据接口
            if trade_date == today:
                logger.info("实时接口失败，但这是今天的数据，不再尝试历史接口")
            else:
                logger.info("实时接口失败，尝试历史数据接口...")
                # 历史数据：使用全市场历史数据接口
                stocks_data = await self._collect_all_market_historical_data(trade_date)
                    
        except Exception as e:
            logger.error(f"获取A股数据失败: {e}")
            
        return stocks_data
    
    async def _collect_all_market_historical_data(self, trade_date: str) -> List[DailyStockChange]:
        """收集全市场历史数据（优化版）"""
        stocks_data = []
        
        try:
            # 首先检查是否为交易日
            if not self._is_trading_day_akshare(trade_date):
                logger.info(f"⏸️ {trade_date} 非交易日，跳过数据收集")
                return stocks_data
                
            logger.info(f"📊 开始收集 {trade_date} 的全市场历史数据...")
            
            # 方案1: 尝试使用历史行情接口（如果AkShare支持）
            try:
                # 将日期格式从 YYYY-MM-DD 转换为 YYYYMMDD
                date_str = trade_date.replace('-', '')
                
                # 使用东财历史数据接口获取所有A股历史数据  
                # 注意：这个接口可能不存在，直接跳到备选方案
                raise AttributeError("stock_zh_a_hist_df接口不存在，使用备选方案")
                
                if df is not None and not df.empty:
                    logger.info(f"✅ 通过历史数据接口获取到 {len(df)} 只股票的数据")
                    
                    for _, row in df.iterrows():
                        try:
                            stock_data = DailyStockChange(
                                stock_code=str(row.get('代码', '')),
                                trade_date=trade_date,
                                change_percent=float(row.get('涨跌幅', 0)),
                                close_price=float(row.get('收盘', 0)),
                                open_price=float(row.get('开盘', 0)),
                                high_price=float(row.get('最高', 0)),
                                low_price=float(row.get('最低', 0)),
                                volume=int(row.get('成交量', 0)),
                                turnover=float(row.get('成交额', 0)),
                                market=self._get_market_from_code(str(row.get('代码', ''))),
                                created_at=datetime.now().isoformat()
                            )
                            stocks_data.append(stock_data)
                        except Exception as e:
                            logger.debug(f"处理股票数据失败: {e}")
                            continue
                    
                    return stocks_data
                    
            except AttributeError:
                logger.info("历史数据接口不可用，尝试使用备选方案...")
            except Exception as e:
                logger.warning(f"历史数据接口调用失败: {e}，尝试使用备选方案...")
            
            # 方案2: 使用股票列表批量获取
            logger.info("使用批量获取方案收集历史数据...")
            
            # 先获取所有A股股票列表
            try:
                # 获取股票基础信息
                stock_list_df = akshare_service.ak.stock_info_a_code_name()
                
                if stock_list_df is None or stock_list_df.empty:
                    logger.warning("无法获取股票列表")
                    return stocks_data
                
                stock_codes = stock_list_df['code'].tolist()
                logger.info(f"获取到 {len(stock_codes)} 只股票代码")
                
            except Exception as e:
                logger.error(f"获取股票列表失败: {e}")
                # 尝试使用备用方法获取股票列表
                try:
                    # 使用沪深A股实时行情接口获取所有股票代码
                    spot_df = akshare_service.ak.stock_zh_a_spot_em()
                    if spot_df is not None and not spot_df.empty:
                        stock_codes = spot_df['代码'].tolist()
                        logger.info(f"通过备用方法获取到 {len(stock_codes)} 只股票代码")
                    else:
                        # 最后的备选：使用默认股票列表
                        stock_codes = self._get_default_stock_codes()
                        logger.warning(f"使用默认股票列表，仅 {len(stock_codes)} 只股票")
                except Exception as backup_error:
                    logger.error(f"备用方法也失败: {backup_error}")
                    stock_codes = self._get_default_stock_codes()
            
            # 批量并发获取历史数据
            batch_size = 50  # 每批处理50只股票
            success_count = 0
            fail_count = 0
            
            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i + batch_size]
                batch_tasks = []
                
                for code in batch_codes:
                    task = self._get_single_stock_history(code, trade_date)
                    batch_tasks.append(task)
                
                # 并发执行批量任务
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 收集结果
                for idx, result in enumerate(batch_results):
                    if isinstance(result, DailyStockChange):
                        stocks_data.append(result)
                        success_count += 1
                    elif isinstance(result, Exception):
                        fail_count += 1
                        logger.debug(f"股票 {batch_codes[idx]} 获取失败: {result}")
                    else:
                        fail_count += 1
                
                # 避免请求过快，加入延迟
                await asyncio.sleep(0.1)
                
                # 进度日志
                if (i + batch_size) % 500 == 0 or i + batch_size >= len(stock_codes):
                    logger.info(f"已处理 {min(i + batch_size, len(stock_codes))}/{len(stock_codes)} 只股票 (成功: {success_count}, 失败: {fail_count})")
            
            logger.info(f"✅ 完成历史数据收集，共获取 {len(stocks_data)} 条数据")
            
        except Exception as e:
            logger.error(f"收集历史数据失败: {e}")
        
        return stocks_data
    
    async def _get_single_stock_history(self, stock_code: str, trade_date: str) -> Optional[DailyStockChange]:
        """获取单只股票的历史数据"""
        try:
            # 将日期格式转换
            start_date = trade_date.replace('-', '')
            end_date = trade_date.replace('-', '')
            
            # 添加超时控制
            import asyncio
            import functools
            
            # 将同步调用转为异步并设置超时
            loop = asyncio.get_event_loop()
            hist_df = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(
                        akshare_service.ak.stock_zh_a_hist,
                        symbol=stock_code,
                        period="daily", 
                        start_date=start_date,
                        end_date=end_date,
                        adjust=""
                    )
                ),
                timeout=5.0  # 5秒超时
            )
            
            if hist_df is not None and not hist_df.empty:
                row = hist_df.iloc[-1]  # 获取最后一行（目标日期）
                
                # 计算涨跌幅
                change_percent = 0
                if '涨跌幅' in row:
                    change_percent = float(row['涨跌幅'])
                
                return DailyStockChange(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    change_percent=change_percent,
                    close_price=float(row.get('收盘', 0)),
                    open_price=float(row.get('开盘', 0)),
                    high_price=float(row.get('最高', 0)),
                    low_price=float(row.get('最低', 0)),
                    volume=int(row.get('成交量', 0)),
                    turnover=float(row.get('成交额', 0)),
                    market=self._get_market_from_code(stock_code),
                    created_at=datetime.now().isoformat()
                )
        except asyncio.TimeoutError:
            logger.debug(f"获取 {stock_code} 历史数据超时（5s）")
        except Exception as e:
            error_msg = str(e)
            if "网络" in error_msg or "timeout" in error_msg.lower():
                logger.debug(f"获取 {stock_code} 网络错误: {e}")
            elif "权限" in error_msg or "limit" in error_msg.lower():
                logger.warning(f"获取 {stock_code} 权限/限制错误: {e}")
            else:
                logger.debug(f"获取 {stock_code} 其他错误: {e}")
        
        return None
    
    def _is_trading_day_akshare(self, trade_date: str) -> bool:
        """使用AkShare判断是否为交易日"""
        try:
            # 获取交易日历
            calendar_df = akshare_service.ak.tool_trade_date_hist_sina()
            if calendar_df is not None and not calendar_df.empty:
                # 检查日期是否在交易日历中
                trade_dates = calendar_df['trade_date'].astype(str).tolist()
                return trade_date in trade_dates
        except Exception as e:
            logger.warning(f"获取交易日历失败: {e}，使用简单判断")
        
        # 降级方案：简单判断周末
        from datetime import datetime
        date_obj = datetime.strptime(trade_date, '%Y-%m-%d')
        weekday = date_obj.weekday()
        return weekday < 5  # 0-4 是周一到周五
    
    def _get_default_stock_codes(self) -> List[str]:
        """获取默认股票代码列表"""
        # 返回一些主要的股票代码
        return [
            # 上证主要股票
            '600000', '600036', '600519', '601318', '601166',
            '601288', '601398', '601939', '601857', '600276',
            # 深证主要股票
            '000001', '000002', '000858', '002594', '300750',
            '000333', '000651', '002415', '002475', '300059',
            # 科创板
            '688111', '688981', '688599', '688036', '688561'
        ]
    
    async def initialize_historical_data(self, days_back: int = 7) -> Dict[str, int]:
        """
        初始化历史数据（批量收集多天数据）
        
        Args:
            days_back: 向前回溯的天数，默认7天
            
        Returns:
            收集结果统计
        """
        logger.info(f"🚀 开始初始化历史数据，回溯 {days_back} 天...")
        
        from datetime import datetime, timedelta
        
        results = {
            'total_days': 0,
            'total_records': 0,
            'success_days': 0,
            'failed_days': 0,
            'details': []
        }
        
        # 计算需要收集的日期列表
        today = datetime.now()
        dates_to_collect = []
        
        for i in range(1, days_back + 1):
            check_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # 检查是否已有数据
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT COUNT(*) FROM daily_stock_changes WHERE trade_date = ?',
                    (check_date,)
                )
                existing_count = cursor.fetchone()[0]
            
            # 如果数据不足，加入收集列表
            if existing_count < 1000:  # 假设正常情况下应该有至少1000条数据
                dates_to_collect.append(check_date)
                logger.info(f"📅 {check_date} 需要收集数据（现有 {existing_count} 条）")
            else:
                logger.info(f"✅ {check_date} 已有充足数据（{existing_count} 条），跳过")
        
        results['total_days'] = len(dates_to_collect)
        
        # 批量收集历史数据
        for date_str in dates_to_collect:
            try:
                logger.info(f"📊 收集 {date_str} 的数据...")
                collected_count = await self.collect_daily_data(date_str)
                
                if collected_count > 0:
                    results['success_days'] += 1
                    results['total_records'] += collected_count
                    results['details'].append({
                        'date': date_str,
                        'status': 'success',
                        'records': collected_count
                    })
                    logger.info(f"✅ {date_str}: 成功收集 {collected_count} 条数据")
                else:
                    results['failed_days'] += 1
                    results['details'].append({
                        'date': date_str,
                        'status': 'failed',
                        'records': 0
                    })
                    logger.warning(f"⚠️ {date_str}: 未收集到数据")
                
                # 避免请求过快
                await asyncio.sleep(1)
                
            except Exception as e:
                results['failed_days'] += 1
                results['details'].append({
                    'date': date_str,
                    'status': 'error',
                    'records': 0,
                    'error': str(e)
                })
                logger.error(f"❌ {date_str}: 收集失败 - {e}")
        
        # 汇总报告
        logger.info(f"""
📈 历史数据初始化完成：
- 总天数: {results['total_days']}
- 成功天数: {results['success_days']}
- 失败天数: {results['failed_days']}
- 总记录数: {results['total_records']}
        """)
        
        return results
    
    def _get_market_from_code(self, stock_code: str) -> str:
        """根据股票代码判断市场"""
        if stock_code.startswith('6'):
            return 'SH'  # 上海
        elif stock_code.startswith(('0', '2', '3')):
            return 'SZ'  # 深圳
        elif len(stock_code) == 5:
            return 'HK'  # 港股
        else:
            return 'OTHER'
    
    async def _save_daily_changes(self, stocks_data: List[DailyStockChange], trade_date: str) -> int:
        """保存每日涨跌数据到数据库"""
        if not stocks_data:
            return 0
            
        import sqlite3
        
        saved_count = 0
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock_data in stocks_data:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO daily_stock_changes 
                            (stock_code, trade_date, change_percent, close_price, open_price,
                             high_price, low_price, volume, turnover, market, 
                             total_market_cap, circulating_market_cap, turnover_rate,
                             pe_ratio, pb_ratio, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_data.stock_code,
                            stock_data.trade_date,
                            stock_data.change_percent,
                            stock_data.close_price,
                            stock_data.open_price,
                            stock_data.high_price,
                            stock_data.low_price,
                            stock_data.volume,
                            stock_data.turnover,
                            stock_data.market,
                            stock_data.total_market_cap,
                            stock_data.circulating_market_cap,
                            stock_data.turnover_rate,
                            stock_data.pe_ratio,
                            stock_data.pb_ratio,
                            stock_data.created_at
                        ))
                        saved_count += 1
                        
                    except Exception as e:
                        logger.debug(f"保存股票数据失败: {stock_data.stock_code}, {e}")
                        continue
                
                conn.commit()
                logger.info(f"💾 成功保存 {saved_count} 条每日涨跌数据")
                
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            
        return saved_count
    
    async def screen_strong_rise_stocks(self, criteria: ScreeningCriteria, screening_date: str = None) -> ScreeningResponse:
        """
        筛选连续强势上涨股票
        
        Args:
            criteria: 筛选条件
            screening_date: 筛选日期，默认为数据库中最新的交易日期
            
        Returns:
            符合条件的股票列表
        """
        if screening_date is None:
            # 使用数据库中最新的交易日期而不是当前日期
            screening_date = await self._get_latest_trading_date()
        
        logger.info(f"📊 [数据库筛选条件]")
        logger.info(f"  - 筛选类型: {criteria.screening_type}")
        logger.info(f"  - 分析日期: {screening_date}")
        logger.info(f"  - 连续天数: ≥{criteria.min_consecutive_days}天")
        logger.info(f"  - 最小涨幅: ≥{criteria.min_rise_percent}%")
        logger.info(f"  - 最小成交量: ≥{criteria.min_volume}手")
        logger.info(f"  - 市场筛选: {criteria.market_filter}")
        
        results = []
        actual_screening_date = screening_date  # 保存实际使用的筛选日期
        
        try:
            # 查询符合条件的股票
            logger.info("🔍 [数据库查询] 开始查询符合条件的股票...")
            stocks_with_consecutive_rises = await self._find_consecutive_rise_stocks(criteria, screening_date)
            logger.info(f"📋 [数据库查询结果] 找到 {len(stocks_with_consecutive_rises)} 只候选股票")
            
            for stock_data in stocks_with_consecutive_rises:
                # 获取股票名称
                stock_name = await self._get_stock_name(stock_data['stock_code'])
                
                result = ScreeningResult(
                    stock_code=stock_data['stock_code'],
                    stock_name=stock_name,
                    market=stock_data['market'],
                    consecutive_days=stock_data['consecutive_days'],
                    avg_rise_percent=stock_data['avg_rise_percent'],
                    total_volume=stock_data['total_volume'],
                    avg_volume=stock_data['avg_volume'],
                    close_price=stock_data['close_price'],
                    turnover_rate=stock_data.get('turnover_rate'),
                    market_cap=stock_data.get('market_cap', 0.0),  # 新增市值字段
                    pe_ratio=stock_data.get('pe_ratio', 0.0),      # 新增市盈率字段
                    daily_changes=stock_data['daily_changes']
                )
                results.append(result)
                
                # 详细记录每只股票的信息
                logger.debug(f"  ✅ {stock_data['stock_code']} {stock_name} - "
                           f"连续{stock_data['consecutive_days']}天, "
                           f"平均涨幅{stock_data['avg_rise_percent']:.2f}%, "
                           f"平均成交量{stock_data['avg_volume']}手")
            
            # 显示前5只股票的详细信息
            if results:
                logger.info("📋 [数据库筛选结果] 前5只股票详情:")
                for i, result in enumerate(results[:5]):
                    logger.info(f"  {i+1}. {result.stock_code} {result.stock_name} "
                              f"({result.market}) - 连续{result.consecutive_days}天, "
                              f"平均涨幅{result.avg_rise_percent:.2f}%, "
                              f"平均成交量{result.avg_volume}手")
            
            logger.info(f"✅ [数据库筛选完成] 找到 {len(results)} 只符合条件的强势股票")
            
            # 保存筛选结果
            await self._save_screening_results(results, criteria, actual_screening_date)
            
        except Exception as e:
            logger.error(f"❌ 股票筛选失败: {e}")
            
        return ScreeningResponse(
            results=results,
            screening_date=actual_screening_date,
            total_count=len(results)
        )
    
    async def _find_consecutive_rise_stocks(self, criteria: ScreeningCriteria, screening_date: str) -> List[Dict]:
        """查找连续上涨的股票"""
        import sqlite3
        
        result_stocks = []
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算查询的日期范围（向前推N个交易日）
                end_date = datetime.strptime(screening_date, '%Y-%m-%d')
                start_date = end_date - timedelta(days=criteria.min_consecutive_days * 2)  # 多取一些数据
                
                # 查询最近N天的数据
                market_filter = "','".join(criteria.market_filter or ['SH', 'SZ', 'HK'])
                
                cursor.execute(f'''
                    SELECT stock_code, market, trade_date, change_percent, volume, close_price, turnover
                    FROM daily_stock_changes 
                    WHERE trade_date BETWEEN ? AND ?
                    AND market IN ('{market_filter}')
                    AND change_percent >= ?
                    ORDER BY stock_code, trade_date DESC
                ''', (start_date.strftime('%Y-%m-%d'), screening_date, criteria.min_rise_percent))
                
                rows = cursor.fetchall()
                
                # 按股票代码分组
                stocks_data = {}
                for row in rows:
                    stock_code = row[0]
                    if stock_code not in stocks_data:
                        stocks_data[stock_code] = []
                    
                    stocks_data[stock_code].append({
                        'trade_date': row[2],
                        'change_percent': row[3],
                        'volume': row[4],
                        'close_price': row[5],
                        'turnover': row[6],
                        'market': row[1]
                    })
                
                # 检查每只股票是否满足连续上涨条件
                for stock_code, daily_data in stocks_data.items():
                    # 按日期排序（最新的在前）
                    daily_data.sort(key=lambda x: x['trade_date'], reverse=True)
                    
                    # 过滤出只包含交易日的数据
                    from utils.market_hours import isWeekday, isHoliday
                    trading_day_data = []
                    for data in daily_data:
                        trade_date_obj = datetime.strptime(data['trade_date'], '%Y-%m-%d')
                        # 只保留工作日且非节假日的数据
                        if isWeekday(trade_date_obj) and not isHoliday(trade_date_obj):
                            trading_day_data.append(data)
                    
                    # 检查连续涨幅（基于实际交易日）
                    consecutive_count = 0
                    total_rise = 0
                    total_volume = 0
                    
                    for data in trading_day_data:
                        if data['change_percent'] >= criteria.min_rise_percent:
                            consecutive_count += 1
                            total_rise += data['change_percent']
                            total_volume += data['volume']
                            
                            if consecutive_count >= criteria.min_consecutive_days:
                                # 满足条件
                                avg_rise_percent = total_rise / consecutive_count
                                avg_volume = total_volume // consecutive_count
                                
                                # 获取最新交易日的收盘价
                                latest_close_price = trading_day_data[0]['close_price']
                                latest_turnover = trading_day_data[0]['turnover']
                                
                                # 获取准确的换手率数据 (优先使用daily_stock_changes表)
                                turnover_rate = None
                                try:
                                    # 优先从daily_stock_changes表获取换手率 (我们刚补充的数据)
                                    with sqlite3.connect(self.db_manager.db_path) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            SELECT turnover_rate FROM daily_stock_changes 
                                            WHERE stock_code = ? AND trade_date = ?
                                        ''', (stock_code, screening_date))
                                        
                                        result = cursor.fetchone()
                                        if result and result[0] is not None and result[0] > 0:
                                            turnover_rate = result[0]
                                        else:
                                            # 备用：从技术指标表获取
                                            cursor.execute('''
                                                SELECT turnover_rate FROM stock_technical_indicators 
                                                WHERE stock_code = ? AND trade_date = ?
                                                ORDER BY updated_at DESC LIMIT 1
                                            ''', (stock_code, screening_date))
                                            
                                            result = cursor.fetchone()
                                            if result and result[0] is not None and result[0] > 0:
                                                turnover_rate = result[0]
                                            else:
                                                # 最后备用：简化估算
                                                if latest_turnover and latest_close_price and latest_turnover > 0 and latest_close_price > 0:
                                                    estimated_circulating_shares = latest_turnover / latest_close_price
                                                    if estimated_circulating_shares > 0:
                                                        turnover_rate = (trading_day_data[0]['volume'] / estimated_circulating_shares) * 100
                                                        turnover_rate = min(turnover_rate, 50)  # 限制极端值
                                except Exception as e:
                                    logger.debug(f"获取换手率数据失败: {e}")
                                    turnover_rate = None
                                
                                # 获取市值数据
                                market_cap = 0
                                pe_ratio = 0
                                try:
                                    with sqlite3.connect(self.db_manager.db_path) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            SELECT total_market_cap, pe_ratio
                                            FROM daily_stock_changes 
                                            WHERE stock_code = ? AND trade_date = ?
                                        ''', (stock_code, screening_date))
                                        
                                        result = cursor.fetchone()
                                        if result:
                                            market_cap = result[0] / 10000 if result[0] else 0  # 转换为亿元
                                            pe_ratio = result[1] if result[1] else 0
                                except Exception as e:
                                    logger.debug(f"获取市值数据失败: {e}")
                                
                                result_stocks.append({
                                    'stock_code': stock_code,
                                    'market': trading_day_data[0]['market'],
                                    'consecutive_days': consecutive_count,
                                    'avg_rise_percent': avg_rise_percent,
                                    'total_volume': total_volume,
                                    'avg_volume': avg_volume,
                                    'close_price': latest_close_price,
                                    'turnover_rate': turnover_rate,
                                    'market_cap': market_cap,  # 新增市值字段
                                    'pe_ratio': pe_ratio,      # 新增市盈率字段
                                    'daily_changes': trading_day_data[:consecutive_count]
                                })
                                break
                        else:
                            break  # 连续性中断
                
        except Exception as e:
            logger.error(f"查询连续上涨股票失败: {e}")
            
        return result_stocks
    
    async def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM stock_info WHERE symbol = ?', (stock_code,))
                result = cursor.fetchone()
                return result[0] if result else stock_code
        except:
            return stock_code
    
    async def _save_screening_results(self, results: List[ScreeningResult], criteria: ScreeningCriteria, screening_date: str):
        """保存筛选结果"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 先删除当天同类型的旧结果
                cursor.execute('''
                    DELETE FROM stock_screening 
                    WHERE screening_date = ? AND screening_type = ?
                ''', (screening_date, criteria.screening_type))
                
                logger.info(f"🗑️ 清理了 {cursor.rowcount} 条当天旧的筛选结果")
                
                # 插入新的筛选结果
                for result in results:
                    cursor.execute('''
                        INSERT INTO stock_screening
                        (stock_code, stock_name, market, screening_date, screening_type,
                         criteria_met, consecutive_days, avg_rise_percent, total_volume, 
                         avg_volume, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.stock_code,
                        result.stock_name,
                        result.market,
                        screening_date,
                        criteria.screening_type,
                        json.dumps(criteria.to_dict()),
                        result.consecutive_days,
                        result.avg_rise_percent,
                        result.total_volume,
                        result.avg_volume,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"💾 保存了 {len(results)} 条筛选结果")
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")
    
    async def _get_latest_trading_date(self) -> str:
        """获取数据库中最新的交易日期"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询最新的交易日期
                cursor.execute('''
                    SELECT MAX(trade_date) 
                    FROM daily_stock_changes
                ''')
                
                result = cursor.fetchone()
                if result and result[0]:
                    latest_date = result[0]
                    logger.info(f"📅 使用数据库中最新的交易日期: {latest_date}")
                    return latest_date
                else:
                    # 如果没有数据，使用当前日期
                    fallback_date = datetime.now().strftime('%Y-%m-%d')
                    logger.warning(f"⚠️ 数据库中没有交易数据，使用当前日期: {fallback_date}")
                    return fallback_date
                    
        except Exception as e:
            # 如果查询失败，使用当前日期作为备选
            fallback_date = datetime.now().strftime('%Y-%m-%d')
            logger.error(f"❌ 获取最新交易日期失败: {e}，使用当前日期: {fallback_date}")
            return fallback_date
    
    async def get_screening_history(self, screening_type: str = None, limit: int = 100) -> List[StockScreening]:
        """获取筛选历史记录"""
        import sqlite3
        
        results = []
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                if screening_type:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, market, screening_date, screening_type,
                               criteria_met, consecutive_days, avg_rise_percent, total_volume,
                               avg_volume, created_at
                        FROM stock_screening 
                        WHERE screening_type = ?
                        ORDER BY screening_date DESC, avg_rise_percent DESC 
                        LIMIT ?
                    ''', (screening_type, limit))
                else:
                    cursor.execute('''
                        SELECT id, stock_code, stock_name, market, screening_date, screening_type,
                               criteria_met, consecutive_days, avg_rise_percent, total_volume,
                               avg_volume, created_at
                        FROM stock_screening 
                        ORDER BY screening_date DESC, avg_rise_percent DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    screening = StockScreening(
                        id=row[0],
                        stock_code=row[1],
                        stock_name=row[2],
                        market=row[3],
                        screening_date=row[4],
                        screening_type=row[5],
                        criteria_met=row[6],
                        consecutive_days=row[7],
                        avg_rise_percent=row[8],
                        total_volume=row[9],
                        avg_volume=row[10],
                        created_at=row[11]
                    )
                    results.append(screening)
                    
        except Exception as e:
            logger.error(f"获取筛选历史失败: {e}")
            
        return results

# 全局实例
_stock_screening_service = None

def get_stock_screening_service(db_manager: DatabaseManager) -> StockScreeningService:
    """获取股票筛选服务实例"""
    global _stock_screening_service
    if _stock_screening_service is None:
        _stock_screening_service = StockScreeningService(db_manager)
    return _stock_screening_service