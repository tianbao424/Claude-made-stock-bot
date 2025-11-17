#!/usr/bin/env python3
"""
增强的网络处理器
解决AkShare API连接问题，提供智能重试和降级策略
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import random
import pandas as pd

logger = logging.getLogger(__name__)

class NetworkRetryHandler:
    """网络重试处理器"""
    
    def __init__(self):
        self.failure_count = 0
        self.last_success_time = time.time()
        self.backoff_time = 0.1  # 初始退避时间
        self.max_backoff = 30.0  # 最大退避时间
        self.consecutive_failures = 0
        
    async def execute_with_retry(self, func, *args, max_retries=3, **kwargs) -> Optional[Any]:
        """带重试的函数执行"""
        
        for attempt in range(max_retries + 1):
            try:
                # 动态退避
                if attempt > 0:
                    wait_time = min(self.backoff_time * (2 ** (attempt - 1)), self.max_backoff)
                    # 添加随机抖动，避免请求冲突
                    jitter = random.uniform(0, wait_time * 0.1)
                    total_wait = wait_time + jitter
                    
                    logger.debug(f"⏳ 第 {attempt + 1} 次重试，等待 {total_wait:.2f} 秒...")
                    await asyncio.sleep(total_wait)
                
                # 执行函数 - 修复异步调用问题
                if asyncio.iscoroutinefunction(func):
                    # 如果是协程函数，直接await
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=30.0)
                else:
                    # 如果是普通函数，在线程中执行
                    result = await asyncio.wait_for(
                        asyncio.to_thread(func, *args, **kwargs),
                        timeout=30.0
                    )
                
                # 成功时重置计数器
                self.consecutive_failures = 0
                self.last_success_time = time.time()
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ 请求超时 (尝试 {attempt + 1}/{max_retries + 1})")
                self.consecutive_failures += 1
                
            except Exception as e:
                error_msg = str(e)
                self.consecutive_failures += 1
                
                # 分析错误类型
                if "Connection aborted" in error_msg or "RemoteDisconnected" in error_msg:
                    logger.warning(f"🔌 连接中断 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                elif "HTTPError" in error_msg and "429" in error_msg:
                    logger.warning(f"🚦 频率限制 (尝试 {attempt + 1}/{max_retries + 1})")
                    # 频率限制时需要更长的等待时间
                    if attempt < max_retries:
                        await asyncio.sleep(60 + random.uniform(0, 30))
                else:
                    logger.warning(f"❌ 请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                
                # 最后一次重试失败时记录详细错误
                if attempt == max_retries:
                    logger.error(f"🚫 所有重试失败: {error_msg}")
        
        return None
    
    def should_pause(self) -> bool:
        """判断是否需要暂停请求"""
        return self.consecutive_failures >= 10
    
    async def adaptive_delay(self):
        """自适应延迟"""
        if self.consecutive_failures > 5:
            delay = min(self.consecutive_failures * 2, 60)
            logger.info(f"🛡️ 连续失败 {self.consecutive_failures} 次，暂停 {delay} 秒")
            await asyncio.sleep(delay)

class EnhancedHistoryUpdater:
    """增强的历史数据更新器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.retry_handler = NetworkRetryHandler()
        
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
        except ImportError:
            logger.error("❌ AkShare模块未安装")
            self.ak = None
            self.available = False
    
    async def update_single_stock_with_fallback(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """单个股票的历史数据更新（带回退策略）"""
        
        if not self.available:
            return None
        
        # 策略1: 尝试AkShare历史数据接口
        result = await self._try_akshare_history(symbol, days)
        if result is not None:
            return result
        
        # 策略2: 尝试使用东财接口
        result = await self._try_eastmoney_history(symbol, days)
        if result is not None:
            return result
        
        # 策略3: 尝试简化的日线数据
        result = await self._try_simple_daily(symbol, days)
        if result is not None:
            return result
        
        logger.warning(f"⚠️ {symbol} 所有数据源都失败")
        return None
    
    async def _try_akshare_history(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """尝试AkShare历史数据接口"""
        
        async def fetch_data():
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            return self.ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
        
        try:
            data = await self.retry_handler.execute_with_retry(fetch_data, max_retries=2)
            
            if data is not None and not data.empty:
                logger.debug(f"✅ AkShare接口获取 {symbol} 成功: {len(data)} 条记录")
                return data
        except Exception as e:
            logger.debug(f"🔄 AkShare接口失败 {symbol}: {e}")
        
        return None
    
    async def _try_eastmoney_history(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """尝试东财接口"""
        
        async def fetch_data():
            return self.ak.stock_zh_a_hist_em(
                symbol=symbol,
                period="daily",
                adjust=""
            )
        
        try:
            data = await self.retry_handler.execute_with_retry(fetch_data, max_retries=2)
            
            if data is not None and not data.empty:
                # 限制到指定天数
                if len(data) > days:
                    data = data.tail(days)
                logger.debug(f"✅ 东财接口获取 {symbol} 成功: {len(data)} 条记录")
                return data
        except Exception as e:
            logger.debug(f"🔄 东财接口失败 {symbol}: {e}")
        
        return None
    
    async def _try_simple_daily(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """尝试简化的日线数据"""
        
        async def fetch_data():
            return self.ak.stock_zh_a_daily(symbol=symbol, adjust="")
        
        try:
            data = await self.retry_handler.execute_with_retry(fetch_data, max_retries=1)
            
            if data is not None and not data.empty:
                # 限制到指定天数
                if len(data) > days:
                    data = data.tail(days)
                logger.debug(f"✅ 简化接口获取 {symbol} 成功: {len(data)} 条记录")
                return data
        except Exception as e:
            logger.debug(f"🔄 简化接口失败 {symbol}: {e}")
        
        return None
    
    async def batch_update_with_smart_retry(self, symbols: List[str], days: int = 30, 
                                          batch_size: int = 10) -> Dict[str, int]:
        """智能批量更新"""
        
        results = {
            'total': len(symbols),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        logger.info(f"🚀 开始智能批量更新 {len(symbols)} 只股票")
        
        # 分批处理
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            logger.info(f"📦 批次 {batch_num}/{total_batches}: 处理 {len(batch)} 只股票")
            
            # 检查是否需要暂停
            if self.retry_handler.should_pause():
                logger.warning("🛑 连续失败过多，暂停5分钟...")
                await asyncio.sleep(300)
                self.retry_handler.consecutive_failures = 0
            
            # 自适应延迟
            await self.retry_handler.adaptive_delay()
            
            # 处理当前批次
            batch_results = await self._process_batch(batch, days)
            
            results['success'] += batch_results['success']
            results['failed'] += batch_results['failed']
            results['errors'].extend(batch_results['errors'])
            
            # 批次间延迟
            if i + batch_size < len(symbols):  # 不是最后一批
                delay = min(self.retry_handler.consecutive_failures * 0.5 + 1, 10)
                logger.info(f"⏳ 批次间等待 {delay:.1f} 秒...")
                await asyncio.sleep(delay)
        
        success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
        logger.info(f"🎯 智能批量更新完成，成功率: {success_rate:.1f}% ({results['success']}/{results['total']})")
        
        return results
    
    async def _process_batch(self, symbols: List[str], days: int) -> Dict[str, int]:
        """处理单个批次"""
        
        batch_results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.debug(f"[{i}/{len(symbols)}] 处理 {symbol}...")
                
                data = await self.update_single_stock_with_fallback(symbol, days)
                
                if data is not None and not data.empty:
                    # 这里可以添加保存到数据库的逻辑
                    batch_results['success'] += 1
                    logger.debug(f"✅ {symbol} 更新成功，{len(data)} 条记录")
                else:
                    batch_results['failed'] += 1
                    batch_results['errors'].append(f"{symbol}: 无法获取数据")
                
                # 单个股票间的小延迟
                await asyncio.sleep(0.2)
                
            except Exception as e:
                batch_results['failed'] += 1
                error_msg = f"{symbol}: {str(e)}"
                batch_results['errors'].append(error_msg)
                logger.debug(f"❌ {symbol} 处理失败: {e}")
        
        return batch_results

# 测试函数
async def test_enhanced_handler():
    """测试增强的网络处理器"""
    
    print("🧪 测试增强的网络处理器")
    print("=" * 50)
    
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_pool.db")
    
    updater = EnhancedHistoryUpdater(db_path)
    
    # 测试股票列表（包含一些可能有问题的股票）
    test_symbols = [
        "000001", "000002", "600519", "600036",  # 正常股票
        "300001", "300002", "300003",             # 创业板
        "688001", "688002",                       # 科创板
        "999999", "888888"                        # 可能不存在的股票
    ]
    
    print(f"📊 测试股票: {test_symbols}")
    print()
    
    # 执行批量更新测试
    results = await updater.batch_update_with_smart_retry(
        test_symbols, 
        days=10, 
        batch_size=3
    )
    
    print("\n📈 测试结果:")
    print(f"  总计: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  成功率: {(results['success']/results['total']*100):.1f}%")
    
    if results['errors']:
        print(f"\n❌ 错误详情 (显示前5个):")
        for error in results['errors'][:5]:
            print(f"    {error}")
        if len(results['errors']) > 5:
            print(f"    ... 还有 {len(results['errors']) - 5} 个错误")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_enhanced_handler())