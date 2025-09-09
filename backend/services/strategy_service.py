"""
AI策略分析服务
提供股票投资策略的数据收集、AI分析和结果生成功能
"""

import json
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

from mcp import ClientSession
from openai import OpenAI

# 添加backend目录到Python路径
import sys
import os

# 获取backend目录的绝对路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import StrategyAnalysisData, GeneratedStrategy, StockPool

logger = logging.getLogger(__name__)


class StrategyDataCollector:
    """策略分析数据收集器"""
    
    def __init__(self, session: ClientSession):
        self.session = session
        self._cache = {}  # 简单缓存，避免短时间内重复调用
        
    async def collect_comprehensive_data(self, stock_code: str, pool: StockPool) -> StrategyAnalysisData:
        """收集策略分析所需的全部数据"""
        
        logger.info(f"开始收集股票 {stock_code} 的策略分析数据")
        
        # 计算持仓盈亏
        profit_loss_amount = (pool.current_price - pool.avg_cost) * pool.shares
        profit_loss_pct = (pool.current_price - pool.avg_cost) / pool.avg_cost * 100 if pool.avg_cost > 0 else 0
        
        # 并发收集各类数据，优化超时时间
        tasks = [
            asyncio.wait_for(self.get_technical_indicators(stock_code), timeout=15),
            asyncio.wait_for(self.get_fundamental_data(stock_code), timeout=15), 
            asyncio.wait_for(self.get_market_context(stock_code), timeout=10),
            asyncio.wait_for(self.get_price_history(stock_code, days=30), timeout=10)
        ]
        
        try:
            technical, fundamental, market, price_history = await asyncio.gather(*tasks)
        except Exception as e:
            logger.warning(f"部分数据收集失败，使用默认值: {e}")
            technical = self.get_default_technical_data()
            fundamental = self.get_default_fundamental_data()
            market = self.get_default_market_data()
            price_history = []
        
        # 避免参数重复的问题，先构建一个完整的参数字典
        data_dict = {
            "stock_code": stock_code,
            "stock_name": pool.stock_name,
            "industry": fundamental.get("industry", ""),
            "shares": pool.shares,
            "avg_cost": pool.avg_cost,
            "current_price": pool.current_price,
            "market_value": pool.market_value,
            "profit_loss_pct": profit_loss_pct,
            "profit_loss_amount": profit_loss_amount,
            "price_trend_30d": price_history,
        }
        
        # 合并其他数据，避免重复键
        for source_dict in [technical, fundamental, market]:
            for key, value in source_dict.items():
                if key not in data_dict:  # 只添加不重复的键
                    data_dict[key] = value
        
        return StrategyAnalysisData(**data_dict)
    
    async def get_technical_indicators(self, stock_code: str) -> Dict:
        """获取技术指标数据"""
        try:
            # 调用MCP获取技术指标
            result = await self.session.call_tool(
                "get_hist_data",
                {
                    "symbol": stock_code,
                    "recent_n": 60,
                    "indicators_list": ["RSI", "MACD", "BOLL"]
                }
            )
            
            if not result.content or len(result.content) == 0:
                return self.get_default_technical_data()
                
            # 调试：打印原始数据结构
            logger.info(f"MCP返回的原始数据类型: {type(result.content)}, 长度: {len(result.content) if result.content else 0}")
            
            data = json.loads(result.content[0].text)
            logger.info(f"解析后的数据类型: {type(data)}, 样本数据: {data if isinstance(data, (str, int, float)) else str(data)[:200]}")
            
            # 检查数据结构
            if isinstance(data, list):
                # 如果直接返回列表
                if len(data) == 0:
                    return self.get_default_technical_data()
                latest = data[-1]
                price_data = data[-20:] if len(data) >= 20 else data
            elif isinstance(data, dict) and "data" in data:
                # 如果是包装在data字段中
                if not data.get("data") or len(data["data"]) == 0:
                    return self.get_default_technical_data()
                latest = data["data"][-1]
                price_data = data["data"][-20:] if len(data["data"]) >= 20 else data["data"]
            else:
                logger.warning(f"未知的数据格式: {type(data)}")
                return self.get_default_technical_data()
            
            # 计算支撑阻力位 (简化版)
            prices = []
            for item in price_data:
                if isinstance(item, dict):
                    close_price = item.get("close") or item.get("Close") or item.get("收盘价", 0)
                    if close_price:
                        prices.append(float(close_price))
            
            if prices:
                support_level = min(prices) * 1.02  # 支撑位
                resistance_level = max(prices) * 0.98  # 阻力位
            else:
                # 从latest数据获取当前价格作为基准
                current_price = latest.get("close") or latest.get("Close") or latest.get("收盘价", 0)
                if current_price:
                    support_level = float(current_price) * 0.95
                    resistance_level = float(current_price) * 1.05
                else:
                    support_level = 0.0
                    resistance_level = 0.0
            
            return {
                "rsi": float(latest.get("RSI") or latest.get("rsi", 50.0)),
                "macd_signal": "多头" if float(latest.get("MACD") or latest.get("macd", 0)) > 0 else "空头",
                "support_level": support_level,
                "resistance_level": resistance_level,
                "volume_status": self.analyze_volume_trend(price_data[-10:] if len(price_data) >= 10 else price_data)
            }
            
        except Exception as e:
            logger.warning(f"获取技术指标失败: {e}")
            return self.get_default_technical_data()
    
    async def get_fundamental_data(self, stock_code: str) -> Dict:
        """获取基本面数据"""
        try:
            # 获取财务指标
            financial_result = await self.session.call_tool(
                "get_financial_metrics",
                {"symbol": stock_code, "recent_n": 1}
            )
            
            if not financial_result.content or len(financial_result.content) == 0:
                return self.get_default_fundamental_data()
                
            financial_data = json.loads(financial_result.content[0].text)
            logger.info(f"财务数据类型: {type(financial_data)}, 样本: {str(financial_data)[:200]}")
            
            # 处理不同的数据格式
            if isinstance(financial_data, list):
                latest_financial = financial_data[0] if len(financial_data) > 0 else {}
            elif isinstance(financial_data, dict) and "data" in financial_data:
                latest_financial = financial_data["data"][0] if financial_data.get("data") and len(financial_data["data"]) > 0 else {}
            else:
                latest_financial = financial_data if isinstance(financial_data, dict) else {}
            
            return {
                "pe_ratio": float(latest_financial.get("pe_ratio", 0)),
                "pb_ratio": float(latest_financial.get("pb_ratio", 0)),
                "roe": float(latest_financial.get("roe", 0)),
                "financial_health": self.assess_financial_health(latest_financial),
                "recent_performance": await self.get_recent_performance(stock_code),
                "industry_position": "市场参与者",  # 简化处理
                "industry": latest_financial.get("industry", "")
            }
            
        except Exception as e:
            logger.warning(f"获取基本面数据失败: {e}")
            return self.get_default_fundamental_data()
    
    async def get_market_context(self, stock_code: str) -> Dict:
        """获取市场环境数据"""
        try:
            # 获取大盘指数数据 (简化版)
            market_result = await self.session.call_tool(
                "get_hist_data",
                {"symbol": "000001", "recent_n": 5}  # 上证指数
            )
            
            if market_result.content and len(market_result.content) > 0:
                market_data = json.loads(market_result.content[0].text)
                
                # 处理不同数据格式
                prices_data = []
                if isinstance(market_data, list):
                    prices_data = market_data
                elif isinstance(market_data, dict) and "data" in market_data:
                    prices_data = market_data.get("data", [])
                
                if prices_data:
                    recent_prices = []
                    for item in prices_data:
                        if isinstance(item, dict):
                            close_price = item.get("close") or item.get("Close") or item.get("收盘价", 0)
                            if close_price:
                                recent_prices.append(float(close_price))
                    
                    if len(recent_prices) >= 2:
                        trend = "上涨" if recent_prices[-1] > recent_prices[0] else "下跌"
                    else:
                        trend = "震荡"
                else:
                    trend = "震荡"
            else:
                trend = "震荡"
                
            return {
                "market_trend": trend,
                "sector_performance": "跟随大盘",
                "market_sentiment": "中性"
            }
            
        except Exception as e:
            logger.warning(f"获取市场环境失败: {e}")
            return self.get_default_market_data()
    
    async def get_price_history(self, stock_code: str, days: int = 30) -> List[float]:
        """获取价格历史数据"""
        try:
            result = await self.session.call_tool(
                "get_hist_data",
                {"symbol": stock_code, "recent_n": days}
            )
            
            if not result.content or len(result.content) == 0:
                return []
                
            data = json.loads(result.content[0].text)
            
            # 处理不同数据格式
            prices_data = []
            if isinstance(data, list):
                prices_data = data
            elif isinstance(data, dict) and "data" in data:
                prices_data = data.get("data", [])
                
            prices = []
            for item in prices_data:
                if isinstance(item, dict):
                    close_price = item.get("close") or item.get("Close") or item.get("收盘价", 0)
                    if close_price:
                        prices.append(float(close_price))
            
            return prices
            
        except Exception as e:
            logger.warning(f"获取价格历史失败: {e}")
            return []
    
    async def get_recent_performance(self, stock_code: str) -> str:
        """获取近期业绩表现"""
        try:
            # 获取最新新闻
            news_result = await self.session.call_tool(
                "get_news_data",
                {"symbol": stock_code, "recent_n": 3}
            )
            
            if news_result.content and len(news_result.content) > 0:
                news_data = json.loads(news_result.content[0].text)
                
                # 处理不同数据格式
                news_items = []
                if isinstance(news_data, list):
                    news_items = news_data
                elif isinstance(news_data, dict) and "data" in news_data:
                    news_items = news_data.get("data", [])
                    
                if news_items and len(news_items) > 0:
                    # 简化处理：根据新闻判断业绩
                    return "业绩稳定"
            
            return "业绩平稳"
            
        except Exception as e:
            logger.warning(f"获取业绩表现失败: {e}")
            return "业绩平稳"
    
    def analyze_volume_trend(self, volume_data: List[Dict]) -> str:
        """分析成交量趋势"""
        try:
            if len(volume_data) < 5:
                return "成交量平稳"
                
            recent_volumes = []
            for item in volume_data:
                if isinstance(item, dict):
                    volume = item.get("volume") or item.get("Volume") or item.get("成交量", 0)
                    if volume:
                        recent_volumes.append(float(volume))
            
            if not recent_volumes:
                return "成交量平稳"
                
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            latest_volume = recent_volumes[-1]
            
            if latest_volume > avg_volume * 1.5:
                return "成交量放大"
            elif latest_volume < avg_volume * 0.5:
                return "成交量萎缩"
            else:
                return "成交量平稳"
                
        except Exception as e:
            return "成交量平稳"
    
    def assess_financial_health(self, financial_data: Dict) -> str:
        """评估财务健康度"""
        try:
            roe = float(financial_data.get("roe", 0))
            pe = float(financial_data.get("pe_ratio", 0))
            
            if roe > 15 and 0 < pe < 30:
                return "财务健康良好"
            elif roe > 10:
                return "财务状况稳健"
            elif roe > 5:
                return "财务状况一般"
            else:
                return "财务状况较弱"
                
        except Exception:
            return "财务状况一般"
    
    def get_default_technical_data(self) -> Dict:
        """默认技术分析数据"""
        return {
            "rsi": 50.0,
            "macd_signal": "震荡",
            "support_level": 0.0,
            "resistance_level": 0.0,
            "volume_status": "成交量平稳"
        }
    
    def get_default_fundamental_data(self) -> Dict:
        """默认基本面数据"""
        return {
            "pe_ratio": 0.0,
            "pb_ratio": 0.0,
            "roe": 0.0,
            "financial_health": "财务状况一般",
            "recent_performance": "业绩平稳",
            "industry_position": "市场参与者",
            "industry": ""
        }
    
    def get_default_market_data(self) -> Dict:
        """默认市场环境数据"""
        return {
            "market_trend": "震荡",
            "sector_performance": "跟随大盘", 
            "market_sentiment": "中性"
        }


class AIStrategyGenerator:
    """AI策略生成器"""
    
    def __init__(self, ai_client: OpenAI):
        self.ai_client = ai_client
        
    async def generate_strategy(self, data: StrategyAnalysisData) -> GeneratedStrategy:
        """生成投资策略"""
        
        logger.info(f"开始为股票 {data.stock_code} 生成AI策略")
        
        prompt = self.build_strategy_prompt(data)
        
        try:
            # 设置AI生成超时时间
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.ai_client.chat.completions.create,
                    model="qwen-coder-plus",
                    messages=[
                        {"role": "system", "content": self.get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # 较低的温度确保结果稳定
                    max_tokens=2000
                ),
                timeout=20  # AI生成20秒超时
            )
            
            strategy_text = response.choices[0].message.content
            return self.parse_strategy_response(strategy_text, data)
            
        except Exception as e:
            logger.error(f"AI策略生成失败: {e}")
            return self.get_fallback_strategy(data)
    
    def get_system_prompt(self) -> str:
        """系统提示词"""
        return """
        你是一位资深的A股投资顾问，具有15年的实战经验。你的分析风格：
        1. 数据驱动，结合技术面和基本面
        2. 风险控制优先，追求稳健收益  
        3. 给出具体可操作的建议
        4. 必须包含风险提示和免责声明
        
        请用专业但通俗易懂的语言回答，避免过于技术化的术语。
        所有建议都要基于提供的数据，不要做无根据的推测。
        """
    
    def build_strategy_prompt(self, data: StrategyAnalysisData) -> str:
        """构建策略分析提示词"""
        
        # 计算盈亏状态描述
        pnl_status = "盈利" if data.profit_loss_pct > 0 else "亏损"
        pnl_desc = f"当前{pnl_status}{abs(data.profit_loss_pct):.2f}%"
        
        # 技术面状态描述
        tech_status = "技术面偏强" if data.rsi > 50 else "技术面偏弱"
        
        prompt = f"""
## 投资策略分析请求

### 股票基本信息
- 股票：{data.stock_name}（{data.stock_code}）
- 行业：{data.industry}

### 持仓情况分析
- 持仓：{data.shares:,}股
- 成本价：￥{data.avg_cost:.2f}/股  
- 现价：￥{data.current_price:.2f}/股
- 持仓市值：￥{data.market_value:,.2f}
- 盈亏状态：{pnl_desc}（￥{data.profit_loss_amount:,.2f}）

### 技术面数据
- RSI指标：{data.rsi:.1f}（{tech_status}）
- MACD信号：{data.macd_signal}
- 关键价位：支撑￥{data.support_level:.2f}，阻力￥{data.resistance_level:.2f}
- 成交量：{data.volume_status}

### 基本面数据  
- 估值水平：PE {data.pe_ratio:.1f}，PB {data.pb_ratio:.2f}
- 盈利能力：ROE {data.roe:.1f}%
- 财务状况：{data.financial_health}
- 业绩表现：{data.recent_performance}

### 市场环境
- 大盘走势：{data.market_trend}
- 板块表现：{data.sector_performance}  
- 市场情绪：{data.market_sentiment}

请基于以上信息，提供结构化的投资策略建议。请严格按照以下JSON格式返回：

```json
{{
    "comprehensive_score": 7.2,
    "risk_level": "medium",
    "action_recommendation": "hold", 
    "target_price_min": {data.current_price * 0.9:.2f},
    "target_price_max": {data.current_price * 1.1:.2f},
    "timeframe": "medium",
    "position_suggestion": 0.75,
    "analysis_summary": "技术面突破重要阻力位，基本面业绩稳健，建议持有并逢低加仓",
    "key_metrics": [
        "关注RSI是否超买",
        "监控成交量变化", 
        "跟踪季度业绩"
    ],
    "risk_warnings": [
        "注意大盘系统性风险",
        "关注行业政策变化",
        "设置止损位￥{data.current_price * 0.85:.2f}"
    ],
    "action_plan": [
        "短期：持有观望，关注￥{data.resistance_level:.2f}突破情况",
        "中期：如跌破￥{data.support_level:.2f}考虑减仓20%", 
        "长期：基本面良好，适合长期持有"
    ],
    "confidence_level": 0.82
}}
```

注意：
1. comprehensive_score范围1-10分
2. risk_level: low/medium/high
3. action_recommendation: buy/hold/reduce/sell  
4. position_suggestion: 建议持仓比例0-1
5. 所有价格建议要合理，基于当前价格{data.current_price:.2f}
6. 必须包含具体的风险提示
"""
        return prompt
    
    def parse_strategy_response(self, response_text: str, data: StrategyAnalysisData) -> GeneratedStrategy:
        """解析AI返回的策略JSON"""
        try:
            # 提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("没有找到有效的JSON格式")
                
            json_str = response_text[json_start:json_end]
            strategy_data = json.loads(json_str)
            
            return GeneratedStrategy(
                comprehensive_score=float(strategy_data.get("comprehensive_score", 5.0)),
                risk_level=strategy_data.get("risk_level", "medium"),
                action_recommendation=strategy_data.get("action_recommendation", "hold"),
                target_price_min=float(strategy_data.get("target_price_min", data.current_price * 0.9)),
                target_price_max=float(strategy_data.get("target_price_max", data.current_price * 1.1)),
                timeframe=strategy_data.get("timeframe", "medium"),
                position_suggestion=float(strategy_data.get("position_suggestion", 0.5)),
                analysis_summary=strategy_data.get("analysis_summary", ""),
                key_metrics=strategy_data.get("key_metrics", []),
                risk_warnings=strategy_data.get("risk_warnings", []),
                action_plan=strategy_data.get("action_plan", []),
                confidence_level=float(strategy_data.get("confidence_level", 0.5))
            )
            
        except Exception as e:
            logger.error(f"解析AI策略响应失败: {e}")
            logger.debug(f"AI响应内容: {response_text}")
            return self.get_fallback_strategy(data)
    
    def get_fallback_strategy(self, data: StrategyAnalysisData) -> GeneratedStrategy:
        """获取备用策略（当AI生成失败时使用）"""
        return GeneratedStrategy(
            comprehensive_score=5.0,
            risk_level="medium",
            action_recommendation="hold",
            target_price_min=data.current_price * 0.9,
            target_price_max=data.current_price * 1.1,
            timeframe="medium",
            position_suggestion=0.5,
            analysis_summary="技术分析数据显示当前处于震荡区间，建议持有观望",
            key_metrics=["关注价格突破", "监控成交量", "跟踪基本面变化"],
            risk_warnings=["注意市场波动风险", "设置合理止损位", "分散投资降低风险"],
            action_plan=["短期观望", "中期根据趋势调整", "长期关注基本面"],
            confidence_level=0.6,
            technical_analysis="当前技术指标显示震荡格局",
            fundamental_analysis="基本面数据有限，建议谨慎",
            market_context="市场整体处于不确定状态"
        )