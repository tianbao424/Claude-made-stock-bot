#!/usr/bin/env python3
"""
腾讯财经数据服务
直接获取股票实时数据，包括换手率
"""
import asyncio
import aiohttp
import logging
import re
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DatabaseManager

logger = logging.getLogger(__name__)

class TencentDataService:
    """腾讯财经数据服务"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager
        self.base_url = 'http://qt.gtimg.cn'
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=20,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://stockapp.finance.qq.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """转换股票代码为腾讯格式"""
        if stock_code.startswith('6'):
            return f'sh{stock_code}'  # 沪市
        else:
            return f'sz{stock_code}'  # 深市
    
    def _parse_tencent_data(self, content: str, stock_code: str) -> Optional[Dict]:
        """解析腾讯财经返回的数据"""
        try:
            # 腾讯数据格式: v_股票代码="数据1~数据2~数据3~..."
            match = re.search(r'"([^"]*)"', content)
            if not match:
                return None
            
            data_parts = match.group(1).split('~')
            if len(data_parts) < 40:
                logger.warning(f"股票 {stock_code} 数据字段不足: {len(data_parts)}")
                return None
            
            # 解析关键数据字段
            try:
                result = {
                    'stock_code': stock_code,
                    'stock_name': data_parts[1],
                    'current_price': float(data_parts[3]) if data_parts[3] else 0,
                    'open_price': float(data_parts[5]) if data_parts[5] else 0,
                    'close_yesterday': float(data_parts[4]) if data_parts[4] else 0,
                    'high_price': float(data_parts[33]) if len(data_parts) > 33 and data_parts[33] else 0,
                    'low_price': float(data_parts[34]) if len(data_parts) > 34 and data_parts[34] else 0,
                    'volume': int(data_parts[6]) if data_parts[6] else 0,  # 成交量(手)
                    'turnover_amount': float(data_parts[37]) if len(data_parts) > 37 and data_parts[37] else 0,  # 成交额(万元)
                    'turnover_rate': float(data_parts[38].replace('%', '')) if len(data_parts) > 38 and data_parts[38] else 0,  # 换手率
                    'change_amount': float(data_parts[31]) if len(data_parts) > 31 and data_parts[31] else 0,  # 涨跌额
                    'change_percent': float(data_parts[32]) if len(data_parts) > 32 and data_parts[32] else 0,  # 涨跌幅
                    'pe_ratio': float(data_parts[39]) if len(data_parts) > 39 and data_parts[39] else 0,  # 市盈率
                    'pb_ratio': float(data_parts[46]) if len(data_parts) > 46 and data_parts[46] else 0,  # 市净率
                    # 修正: 字段72/73直接是万元为单位的市值数据
                    'total_market_cap': float(data_parts[73]) / 100 if len(data_parts) > 73 and data_parts[73] else 0,  # 总市值(万元)
                    'circulating_market_cap': float(data_parts[72]) / 100 if len(data_parts) > 72 and data_parts[72] else 0,  # 流通市值(万元)
                    'data_timestamp': data_parts[30] if len(data_parts) > 30 else '',  # 数据时间戳
                    'data_source': 'tencent'
                }
                
                # 处理成交量单位转换（手 -> 股）
                result['volume'] = result['volume'] * 100
                
                # 验证数据合理性
                if result['current_price'] <= 0:
                    logger.warning(f"股票 {stock_code} 价格数据异常: {result['current_price']}")
                    return None
                
                return result
                
            except (ValueError, IndexError) as e:
                logger.error(f"解析股票 {stock_code} 数据时出错: {e}")
                logger.debug(f"原始数据: {data_parts[:50]}")  # 显示前50个字段用于调试
                return None
                
        except Exception as e:
            logger.error(f"解析腾讯数据失败 {stock_code}: {e}")
            return None
    
    async def get_stock_data(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """获取股票数据"""
        results = {}
        
        # 分批处理，每批50只股票
        batch_size = 50
        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            
            try:
                # 构建腾讯财经API请求
                tencent_codes = [self._convert_stock_code(code) for code in batch_codes]
                codes_str = ','.join(tencent_codes)
                url = f'{self.base_url}/q={codes_str}'
                
                logger.info(f"获取第 {i//batch_size + 1} 批数据 ({len(batch_codes)} 只股票)")
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text(encoding='gbk')
                        
                        # 按行解析每只股票的数据
                        lines = content.strip().split('\n')
                        for j, line in enumerate(lines):
                            if j < len(batch_codes):
                                stock_code = batch_codes[j]
                                parsed_data = self._parse_tencent_data(line, stock_code)
                                if parsed_data:
                                    results[stock_code] = parsed_data
                                    logger.debug(f"成功解析 {stock_code}: 换手率={parsed_data['turnover_rate']:.2f}%")
                    else:
                        logger.warning(f"第 {i//batch_size + 1} 批请求失败: HTTP {response.status}")
                
                # 避免请求过于频繁
                if i + batch_size < len(stock_codes):
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"第 {i//batch_size + 1} 批数据获取失败: {e}")
                continue
        
        logger.info(f"腾讯财经获取完成: {len(results)}/{len(stock_codes)} 只股票")
        return results
    
    async def update_database_with_tencent_data(self, market_data: Dict[str, Dict], trade_date: str) -> int:
        """使用腾讯数据更新数据库"""
        if not self.db_manager:
            logger.error("数据库管理器未初始化")
            return 0
        
        updated_count = 0
        
        try:
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                for stock_code, data in market_data.items():
                    try:
                        cursor.execute('''
                            UPDATE daily_stock_changes 
                            SET total_market_cap = ?, 
                                circulating_market_cap = ?, 
                                turnover_rate = ?,
                                pe_ratio = ?,
                                pb_ratio = ?
                            WHERE stock_code = ? AND trade_date = ?
                        ''', (
                            data.get('total_market_cap', 0),
                            data.get('circulating_market_cap', 0),
                            data.get('turnover_rate', 0),
                            data.get('pe_ratio', 0),
                            data.get('pb_ratio', 0),
                            stock_code,
                            trade_date
                        ))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                            
                    except Exception as e:
                        logger.error(f"更新股票 {stock_code} 数据失败: {e}")
                        continue
                
                conn.commit()
                logger.info(f"数据库更新完成: {updated_count} 只股票")
                
        except Exception as e:
            logger.error(f"数据库更新失败: {e}")
        
        return updated_count

async def supplement_with_tencent_api(
    db_manager: DatabaseManager, 
    trade_date: str = None, 
    limit: int = 500
) -> Dict:
    """使用腾讯API补充A股市值和换手率数据"""
    
    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"🚀 开始使用腾讯财经API补充数据 (日期: {trade_date})")
    
    # 1. 查找需要补充的股票
    try:
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT stock_code 
                FROM daily_stock_changes 
                WHERE trade_date = ? 
                  AND (total_market_cap = 0 OR total_market_cap IS NULL 
                       OR turnover_rate = 0 OR turnover_rate IS NULL)
                  AND volume >= 0
                ORDER BY volume DESC
                LIMIT ?
            ''', (trade_date, limit))
            
            stock_codes = [row[0] for row in cursor.fetchall()]
    
    except Exception as e:
        logger.error(f"查询需要补充的股票失败: {e}")
        return {'success': False, 'error': str(e)}
    
    if not stock_codes:
        logger.info("✅ 没有找到需要补充数据的股票")
        return {'success': True, 'total_updated': 0, 'message': '无需补充'}
    
    logger.info(f"📊 找到 {len(stock_codes)} 只需要补充数据的股票")
    
    # 2. 使用腾讯API获取数据
    try:
        async with TencentDataService(db_manager) as service:
            market_data = await service.get_stock_data(stock_codes)
            updated_count = await service.update_database_with_tencent_data(market_data, trade_date)
        
        success_rate = (len(market_data) / len(stock_codes)) * 100 if stock_codes else 0
        
        result = {
            'success': True,
            'total_processed': len(stock_codes),
            'success_count': len(market_data),
            'updated_count': updated_count,
            'failed_count': len(stock_codes) - len(market_data),
            'success_rate': f"{success_rate:.1f}%",
            'data_source_stats': {'tencent': len(market_data)},
            'message': f"腾讯API补充完成: {len(market_data)}/{len(stock_codes)} 只股票"
        }
        
        logger.info(f"✅ {result['message']}")
        return result
        
    except Exception as e:
        logger.error(f"腾讯API数据补充失败: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    # 测试代码
    async def test_service():
        db_manager = DatabaseManager('stock_pool.db')
        result = await supplement_with_tencent_api(db_manager, "2025-11-14", limit=10)
        print(f"测试结果: {result}")
    
    asyncio.run(test_service())