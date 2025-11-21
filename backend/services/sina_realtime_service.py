"""
新浪财经实时数据服务
直接调用新浪API获取股票实时行情数据
"""
import asyncio
import logging
import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SinaStockData:
    """新浪股票数据结构"""
    code: str
    name: str
    current_price: float
    open_price: float
    yesterday_close: float
    high_price: float
    low_price: float
    volume: int
    turnover: float
    change_amount: float
    change_percent: float
    market: str

class SinaRealtimeService:
    """新浪财经实时数据服务"""
    
    def __init__(self):
        self.base_url = "http://hq.sinajs.cn/list="
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def _convert_to_sina_code(self, stock_code: str, market: str) -> str:
        """转换股票代码为新浪格式"""
        if market.upper() == 'SH':
            return f'sh{stock_code}'
        elif market.upper() == 'SZ':
            return f'sz{stock_code}'
        else:
            # 自动判断
            if stock_code.startswith('6'):
                return f'sh{stock_code}'
            else:
                return f'sz{stock_code}'
    
    def _parse_sina_data(self, sina_code: str, data_str: str) -> Optional[SinaStockData]:
        """解析新浪数据格式"""
        try:
            if f'var hq_str_{sina_code}=' not in data_str:
                return None
                
            # 提取数据部分
            line = [l for l in data_str.split('\n') if f'hq_str_{sina_code}=' in l][0]
            data_part = line.split('="')[1].split('";')[0]
            fields = data_part.split(',')
            
            if len(fields) < 32:
                logger.warning(f"数据字段不完整: {sina_code}, 字段数: {len(fields)}")
                return None
            
            # 解析字段
            name = fields[0]
            open_price = float(fields[1]) if fields[1] else 0.0
            yesterday_close = float(fields[2]) if fields[2] else 0.0
            current_price = float(fields[3]) if fields[3] else 0.0
            high_price = float(fields[4]) if fields[4] else 0.0
            low_price = float(fields[5]) if fields[5] else 0.0
            volume = int(fields[8]) if fields[8] else 0
            turnover = float(fields[9]) if fields[9] else 0.0
            
            # 计算涨跌
            change_amount = current_price - yesterday_close if yesterday_close > 0 else 0.0
            change_percent = (change_amount / yesterday_close * 100) if yesterday_close > 0 else 0.0
            
            # 提取原始代码和市场
            original_code = sina_code[2:]  # 去掉sh/sz前缀
            market = sina_code[:2].upper()  # SH/SZ
            
            return SinaStockData(
                code=original_code,
                name=name,
                current_price=current_price,
                open_price=open_price,
                yesterday_close=yesterday_close,
                high_price=high_price,
                low_price=low_price,
                volume=volume,
                turnover=turnover,
                change_amount=change_amount,
                change_percent=change_percent,
                market=market
            )
            
        except Exception as e:
            logger.debug(f"解析新浪数据失败 {sina_code}: {e}")
            return None
    
    async def get_batch_data(self, stock_codes: List[Dict[str, str]], batch_size: int = 50) -> List[SinaStockData]:
        """批量获取股票数据"""
        all_data = []
        
        # 转换为新浪代码格式
        sina_codes = []
        for stock in stock_codes:
            sina_code = self._convert_to_sina_code(stock['code'], stock['market'])
            sina_codes.append(sina_code)
        
        # 分批处理
        for i in range(0, len(sina_codes), batch_size):
            batch_codes = sina_codes[i:i + batch_size]
            
            try:
                # 构建请求URL
                codes_str = ','.join(batch_codes)
                url = f"{self.base_url}{codes_str}"
                
                # 发送请求
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._make_request, url)
                    response = await loop.run_in_executor(None, lambda: future.result())
                
                if response and response.status_code == 200:
                    # 解析响应数据
                    for sina_code in batch_codes:
                        stock_data = self._parse_sina_data(sina_code, response.text)
                        if stock_data:
                            all_data.append(stock_data)
                else:
                    logger.warning(f"批次请求失败: {response.status_code if response else 'No response'}")
                    
            except Exception as e:
                logger.error(f"批量获取数据失败: {e}")
                continue
            
            # 批次间延迟
            if i + batch_size < len(sina_codes):
                await asyncio.sleep(0.1)
        
        logger.info(f"📊 新浪API获取数据: {len(all_data)}/{len(stock_codes)} 只股票")
        return all_data
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """发送HTTP请求"""
        try:
            response = self.session.get(url, timeout=10)
            return response
        except Exception as e:
            logger.debug(f"请求失败: {e}")
            return None
    
    async def test_connectivity(self) -> bool:
        """测试连接性"""
        try:
            test_codes = ['sz000001', 'sh600036']
            url = f"{self.base_url}{','.join(test_codes)}"
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._make_request, url)
                response = await loop.run_in_executor(None, lambda: future.result())
            
            if response and response.status_code == 200:
                # 检查是否有有效数据
                valid_count = sum(1 for code in test_codes if f'var hq_str_{code}=' in response.text)
                return valid_count > 0
            
            return False
            
        except Exception as e:
            logger.debug(f"连接测试失败: {e}")
            return False
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()

# 全局实例
sina_realtime_service = SinaRealtimeService()