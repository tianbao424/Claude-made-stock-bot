import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import AsyncExitStack

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv
import logging

from database import DatabaseManager, StockPool, StockInfo
from services.stock_data import stock_data_service
from services.akshare_service import akshare_service
from services.improved_akshare_service import improved_akshare_service
from services.optimized_data_service import get_optimized_data_service

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI股票聊天助手", version="1.0.0")

# 挂载静态文件服务
frontend_static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static")
if os.path.exists(frontend_static_path):
    app.mount("/static", StaticFiles(directory=frontend_static_path), name="static")

class WebStockAnalysisBot:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        self.client = OpenAI(
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
        )
        
        self.stock_name_map = {
            "茅台": "600519", "贵州茅台": "600519",
            "平安": "000001", "中国平安": "000001",
            "腾讯": "00700", "阿里": "09988", "阿里巴巴": "09988",
            "比亚迪": "002594", "宁德时代": "300750",
            "美团": "03690", "小米": "01810"
        }
        
        # 使用统一的数据库路径
        self.db_manager = DatabaseManager(os.path.join(os.path.dirname(__file__), "stock_pool.db"))

    async def connect_to_server(self) -> bool:
        try:
            python_path = os.getenv("MCP_PYTHON_PATH", "python3")
            server_params = StdioServerParameters(
                command=python_path,
                args=["-m", "akshare_one_mcp"],
                env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()
            response = await self.session.list_tools()
            logger.info("🔗 已连接到akshare MCP服务器")
            logger.info(f"📊 可用工具: {', '.join([tool.name for tool in response.tools])}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 连接MCP服务器失败: {e}")
            return False

    def normalize_stock_input(self, user_input: str) -> str:
        for name, code in self.stock_name_map.items():
            if name in user_input:
                user_input = user_input.replace(name, f"{name}({code})")
        return user_input

    async def process_query(self, query: str) -> str:
        if not self.session:
            return "❌ 未连接到MCP服务器"

        processed_query = self.normalize_stock_input(query)
        
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的股票分析助手。你可以调用以下股票数据工具来获取信息：

1. 使用get_hist_data获取历史数据进行技术分析
2. 使用get_realtime_data获取实时行情数据  
3. 使用get_news_data获取相关新闻资讯
4. 使用get_balance_sheet获取资产负债表
5. 使用get_income_statement获取利润表
6. 使用get_cash_flow获取现金流量表

请根据用户问题智能选择合适的工具，并提供专业的股票分析。
对于中国股票，请使用6位数字代码（如600519代表贵州茅台）。
始终用中文回复用户。"""
            },
            {
                "role": "user", 
                "content": processed_query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in response.tools
        ]

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=messages,
                tools=available_tools,
                temperature=0.1
            )

            final_responses = []
            
            for choice in response.choices:
                message = choice.message
                
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                        except Exception as tool_error:
                            error_msg = str(tool_error)
                            
                            if "KeyError" in error_msg and "current_liabilities" in error_msg:
                                tool_result_msg = "❌ 该股票的财务数据暂时无法获取，可能是数据源问题或股票代码不正确"
                            elif "symbol" in error_msg.lower() or "股票代码" in error_msg:
                                tool_result_msg = "❌ 股票代码格式错误，请检查输入的股票代码是否正确"
                            elif "timeout" in error_msg.lower() or "超时" in error_msg:
                                tool_result_msg = "❌ 网络连接超时，请稍后重试"
                            else:
                                tool_result_msg = f"❌ 数据获取失败: {tool_name}工具调用异常"
                            
                            messages.append({
                                "role": "assistant", 
                                "content": f"正在调用{tool_name}工具..."
                            })
                            messages.append({
                                "role": "user",
                                "content": f"工具调用结果: {tool_result_msg}"
                            })
                            continue
                        
                        messages.append({
                            "role": "assistant", 
                            "content": message.content or f"正在调用{tool_name}工具..."
                        })
                        
                        if result.content:
                            tool_result = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                            messages.append({
                                "role": "user",
                                "content": f"工具调用结果: {tool_result}"
                            })

                    final_response = self.client.chat.completions.create(
                        model=os.getenv("MODEL"),
                        messages=messages,
                        temperature=0.1
                    )
                    final_responses.append(final_response.choices[0].message.content)
                    
                else:
                    final_responses.append(message.content)

            return "\n\n".join(final_responses) if final_responses else "抱歉，无法处理您的查询。"
            
        except Exception as e:
            return f"❌ 处理查询时发生错误: {e}"

    async def cleanup(self):
        await self.exit_stack.aclose()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

class StockPoolCreateRequest(BaseModel):
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    pool_type: str = Field(..., description="池类型", pattern="^(holding|potential)$")
    tags: Optional[List[str]] = Field(None, description="标签")
    notes: Optional[str] = Field(None, description="备注")

class StockPoolUpdateRequest(BaseModel):
    stock_code: Optional[str] = Field(None, description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    pool_type: Optional[str] = Field(None, description="池类型", pattern="^(holding|potential)$")
    tags: Optional[List[str]] = Field(None, description="标签")
    notes: Optional[str] = Field(None, description="备注")

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None

class StockInfoResponse(BaseModel):
    symbol: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    short_name: str = Field(description="股票简称")
    market: str = Field(description="所属市场")
    industry: str = Field(description="所属行业")
    sector: str = Field(default="", description="板块分类")
    market_cap: float = Field(default=0.0, description="市值")
    pe_ratio: float = Field(default=0.0, description="市盈率")
    pb_ratio: float = Field(default=0.0, description="市净率")
    dividend_yield: float = Field(default=0.0, description="股息率")
    listing_date: str = Field(default="", description="上市日期")
    is_active: bool = Field(default=True, description="是否活跃")

class StockSearchRequest(BaseModel):
    query: str = Field(description="搜索关键词")
    limit: Optional[int] = Field(20, description="返回结果数量限制")

class AddToPoolRequest(BaseModel):
    pool_type: str = Field(..., description="池类型", pattern="^(holding|potential)$")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    notes: Optional[str] = Field("", description="备注信息")
    shares: Optional[int] = Field(0, description="股数，持仓股票必填")
    avg_cost: Optional[float] = Field(0.0, description="平均成本，持仓股票必填")

def stock_pool_to_dict(stock: 'StockPool') -> Dict:
    """将StockPool对象转换为字典"""
    return {
        "id": stock.id,
        "stock_code": stock.stock_code,
        "stock_name": stock.stock_name,
        "pool_type": stock.pool_type,
        "shares": stock.shares,
        "avg_cost": stock.avg_cost,
        "current_price": stock.current_price,
        "market_value": stock.market_value,
        "tags": stock.tags,
        "notes": stock.notes,
        "created_at": stock.created_at,
        "updated_at": stock.updated_at
    }

def stock_info_to_dict(stock: 'StockInfo') -> Dict:
    """将StockInfo对象转换为字典"""
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "short_name": stock.short_name,
        "market": stock.market,
        "industry": stock.industry,
        "sector": stock.sector,
        "market_cap": stock.market_cap,
        "pe_ratio": stock.pe_ratio,
        "pb_ratio": stock.pb_ratio,
        "dividend_yield": stock.dividend_yield,
        "listing_date": stock.listing_date,
        "is_active": stock.is_active
    }

bot = WebStockAnalysisBot()
manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 启动AI股票聊天助手...")
    success = await bot.connect_to_server()
    if success:
        logger.info("✅ Stock bot initialized successfully")
    else:
        logger.error("❌ Failed to connect to MCP server")

@app.on_event("shutdown")
async def shutdown_event():
    await bot.cleanup()

@app.get("/", response_class=HTMLResponse)
async def get():
    try:
        frontend_html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
        with open(frontend_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <body>
            <h1>❌ 前端文件未找到</h1>
            <p>请确保frontend/index.html文件存在</p>
        </body>
        </html>
        """, status_code=404)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "query":
                query = message_data["content"]
                
                await manager.send_personal_message(
                    json.dumps({"type": "typing", "content": ""}), websocket
                )
                
                response = await bot.process_query(query)
                
                await manager.send_personal_message(
                    json.dumps({"type": "response", "content": response}), websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 股票池管理API
@app.get("/api/stock-pools")
async def get_stock_pools(pool_type: Optional[str] = None):
    """获取股票池列表"""
    try:
        stocks = bot.db_manager.get_stocks(pool_type)
        stock_dicts = [stock_pool_to_dict(stock) for stock in stocks]
        
        return ApiResponse(success=True, data=stock_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock-pools/{stock_id}")
async def get_stock_pool_by_id(stock_id: int):
    """根据ID获取股票池"""
    try:
        stock = bot.db_manager.get_stock_by_id(stock_id)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        stock_dict = {
            "id": stock.id,
            "stock_code": stock.stock_code,
            "stock_name": stock.stock_name,
            "pool_type": stock.pool_type,
            "tags": stock.tags,
            "notes": stock.notes,
            "created_at": stock.created_at,
            "updated_at": stock.updated_at
        }
        
        return ApiResponse(success=True, data=stock_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/search")
async def search_stocks(query: str, market: str = 'all', limit: int = 20):
    """高性能智能搜索股票"""
    try:
        if not query.strip():
            return ApiResponse(success=False, message="搜索关键词不能为空")
        
        # 使用优化的数据服务
        optimized_service = get_optimized_data_service()
        results, total = await optimized_service.search_stocks(query.strip(), market, limit)
        
        return ApiResponse(
            success=True, 
            data=results,
            message=f"找到 {len(results)} 条结果 (共{total}条匹配)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/info/{symbol}")
async def get_stock_info(symbol: str):
    """根据代码获取股票详细信息"""
    try:
        stock = bot.db_manager.get_stock_info_by_symbol(symbol)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        stock_dict = {
            "symbol": stock.symbol,
            "name": stock.name,
            "short_name": stock.short_name,
            "market": stock.market,
            "industry": stock.industry,
            "sector": stock.sector,
            "market_cap": stock.market_cap,
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "dividend_yield": stock.dividend_yield,
            "listing_date": stock.listing_date,
            "is_active": stock.is_active,
            "created_at": stock.created_at,
            "updated_at": stock.updated_at
        }
        
        return ApiResponse(success=True, data=stock_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/stats")
async def get_stock_stats():
    """获取股票数据统计信息（优化版本）"""
    try:
        # 使用优化的数据服务获取详细统计
        optimized_service = get_optimized_data_service()
        stats = await optimized_service.get_stats()
        
        return ApiResponse(
            success=True, 
            data=stats, 
            message=f"数据库中共有 {stats['total_stocks']} 只股票"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/realtime/{symbol}")
async def get_stock_realtime(symbol: str):
    """获取股票实时行情数据"""
    try:
        # 从优化数据服务获取股票基本信息
        optimized_service = get_optimized_data_service()
        search_results, _ = await optimized_service.search_stocks(symbol, limit=1)
        
        if not search_results:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        stock_info = search_results[0]
        
        # 根据市场类型获取实时数据（使用改进的多源服务）
        market = "HK" if stock_info['market'] == "HK" else "A"
        realtime_data = await improved_akshare_service.get_stock_realtime_data_enhanced(symbol, market)
        
        if not realtime_data:
            raise HTTPException(status_code=500, detail="获取实时数据失败")
        
        # 转换为字典格式并添加数据源信息
        response_data = {
            'symbol': realtime_data.symbol,
            'name': realtime_data.name,
            'current_price': realtime_data.current_price,
            'change_amount': realtime_data.change_amount,
            'change_percent': realtime_data.change_percent,
            'volume': realtime_data.volume,
            'turnover': realtime_data.turnover,
            'open_price': realtime_data.open_price,
            'high_price': realtime_data.high_price,
            'low_price': realtime_data.low_price,
            'prev_close': realtime_data.prev_close,
            'market_cap': realtime_data.market_cap,
            'pe_ratio': realtime_data.pe_ratio,
            'pb_ratio': realtime_data.pb_ratio,
            'timestamp': realtime_data.timestamp,
            'data_source': realtime_data.data_source.value,
            'is_simulated': realtime_data.is_simulated
        }
        
        return ApiResponse(
            success=True, 
            data=response_data,
            message="实时数据获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data-sources/status")
async def get_data_sources_status():
    """获取数据源状态"""
    try:
        # 检查所有数据源状态
        await improved_akshare_service.check_all_data_sources()
        status_summary = improved_akshare_service.get_data_source_summary()
        
        return ApiResponse(
            success=True,
            data=status_summary,
            message="数据源状态获取成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance/cache-stats")
async def get_cache_stats():
    """获取缓存性能统计"""
    try:
        optimized_service = get_optimized_data_service()
        cache_stats = optimized_service.get_cache_stats()
        
        return ApiResponse(
            success=True,
            data=cache_stats,
            message="缓存统计获取成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stock-pools")
async def create_stock_pool(stock_data: StockPoolCreateRequest):
    """创建股票池"""
    try:
        stock = StockPool(
            stock_code=stock_data.stock_code,
            stock_name=stock_data.stock_name,
            pool_type=stock_data.pool_type,
            tags=stock_data.tags,
            notes=stock_data.notes or ""
        )
        stock_id = bot.db_manager.add_stock(stock)
        
        # 返回创建的股票信息
        created_stock = bot.db_manager.get_stock_by_id(stock_id)
        stock_dict = {
            "id": created_stock.id,
            "stock_code": created_stock.stock_code,
            "stock_name": created_stock.stock_name,
            "pool_type": created_stock.pool_type,
            "tags": created_stock.tags,
            "notes": created_stock.notes,
            "created_at": created_stock.created_at,
            "updated_at": created_stock.updated_at
        }
        
        return ApiResponse(success=True, data=stock_dict, message="股票添加成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/stock-pools/{stock_id}")
async def update_stock_pool(stock_id: int, stock_data: StockPoolUpdateRequest):
    """更新股票池"""
    try:
        # 检查股票是否存在
        existing_stock = bot.db_manager.get_stock_by_id(stock_id)
        if not existing_stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 准备更新数据
        updates = {}
        if stock_data.stock_code is not None:
            updates["stock_code"] = stock_data.stock_code
        if stock_data.stock_name is not None:
            updates["stock_name"] = stock_data.stock_name
        if stock_data.pool_type is not None:
            updates["pool_type"] = stock_data.pool_type
        if stock_data.tags is not None:
            updates["tags"] = stock_data.tags
        if stock_data.notes is not None:
            updates["notes"] = stock_data.notes
        
        # 更新股票
        success = bot.db_manager.update_stock(stock_id, updates)
        if not success:
            raise HTTPException(status_code=400, detail="更新失败")
        
        # 返回更新后的股票信息
        updated_stock = bot.db_manager.get_stock_by_id(stock_id)
        stock_dict = {
            "id": updated_stock.id,
            "stock_code": updated_stock.stock_code,
            "stock_name": updated_stock.stock_name,
            "pool_type": updated_stock.pool_type,
            "tags": updated_stock.tags,
            "notes": updated_stock.notes,
            "created_at": updated_stock.created_at,
            "updated_at": updated_stock.updated_at
        }
        
        return ApiResponse(success=True, data=stock_dict, message="股票更新成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/stock-pools/{stock_id}")
async def delete_stock_pool(stock_id: int):
    """删除股票池"""
    try:
        # 检查股票是否存在
        existing_stock = bot.db_manager.get_stock_by_id(stock_id)
        if not existing_stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 删除股票
        success = bot.db_manager.delete_stock(stock_id)
        if not success:
            raise HTTPException(status_code=400, detail="删除失败")
        
        return ApiResponse(success=True, message="股票删除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock-pools/type/{pool_type}")
async def get_stock_pools_by_type(pool_type: str):
    """根据类型获取股票池"""
    if pool_type not in ["holding", "potential"]:
        raise HTTPException(status_code=400, detail="无效的股票池类型")
    
    try:
        stocks = bot.db_manager.get_stocks(pool_type)
        stock_dicts = []
        for stock in stocks:
            stock_dict = {
                "id": stock.id,
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "pool_type": stock.pool_type,
                "tags": stock.tags,
                "notes": stock.notes,
                "created_at": stock.created_at,
                "updated_at": stock.updated_at
            }
            stock_dicts.append(stock_dict)
        
        return ApiResponse(success=True, data=stock_dicts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_stock_current_price(symbol: str) -> float:
    """获取股票当前价格"""
    try:
        # 使用MCP AkShare服务获取实时价格
        if bot.session:
            result = await bot.session.call_tool(
                "get_realtime_data", 
                {"symbol": symbol}
            )
            if result.content and len(result.content) > 0:
                data = json.loads(result.content[0].text)
                if data.get("data") and len(data["data"]) > 0:
                    # 获取当前价格字段
                    price_data = data["data"][0]
                    return float(price_data.get("current", 0.0) or price_data.get("close", 0.0))
    except Exception as e:
        logger.warning(f"获取股票 {symbol} 实时价格失败: {e}")
    
    return 0.0

@app.get("/api/stocks/{symbol}/price")
async def get_stock_price(symbol: str):
    """获取股票实时价格"""
    try:
        price = await get_stock_current_price(symbol)
        return ApiResponse(
            success=True,
            data={"symbol": symbol, "current_price": price},
            message="获取股价成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股价失败: {str(e)}")

@app.post("/api/stocks/{symbol}/add-to-pool")
async def add_stock_to_pool(symbol: str, request: AddToPoolRequest):
    """从股票信息库添加股票到股票池"""
    try:
        # 1. 检查股票是否存在于信息库中
        optimized_service = get_optimized_data_service()
        search_results, _ = await optimized_service.search_stocks(symbol, limit=1)
        
        if not search_results:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        stock_info = search_results[0]
        
        # 2. 检查股票是否已经存在于股票池中
        existing_stock = bot.db_manager.check_stock_exists(symbol)
        
        if existing_stock:
            # 股票已存在，检查是否要转换类型
            if existing_stock.pool_type == request.pool_type:
                return ApiResponse(
                    success=False, 
                    message=f"股票 {symbol} 已存在于{('持仓' if request.pool_type == 'holding' else '关注')}股票池中"
                )
            else:
                # 转换股票池类型
                current_price = await get_stock_current_price(symbol) if request.pool_type == 'holding' else 0.0
                market_value = (request.shares or 0) * current_price if request.pool_type == 'holding' else 0.0
                
                # 验证持仓股票必填字段
                if request.pool_type == 'holding' and (not request.shares or request.shares <= 0):
                    return ApiResponse(
                        success=False,
                        message="持仓股票必须填写股数"
                    )
                
                # 更新现有股票
                updates = {
                    'pool_type': request.pool_type,
                    'shares': request.shares or 0,
                    'avg_cost': request.avg_cost or 0.0,
                    'current_price': current_price,
                    'market_value': market_value,
                    'tags': request.tags,
                    'notes': request.notes
                }
                
                bot.db_manager.update_stock(existing_stock.id, updates)
                updated_stock = bot.db_manager.get_stock_by_id(existing_stock.id)
                
                pool_type_name = "持仓股票池" if request.pool_type == "holding" else "关注股票池"
                
                return ApiResponse(
                    success=True,
                    data=stock_pool_to_dict(updated_stock),
                    message=f"成功将 {stock_info['name']} ({symbol}) 转换到{pool_type_name}"
                )
        
        # 3. 创建新股票
        # 验证持仓股票必填字段
        if request.pool_type == 'holding' and (not request.shares or request.shares <= 0):
            return ApiResponse(
                success=False,
                message="持仓股票必须填写股数"
            )
        
        # 获取当前价格并计算市值
        current_price = await get_stock_current_price(symbol) if request.pool_type == 'holding' else 0.0
        market_value = (request.shares or 0) * current_price if request.pool_type == 'holding' else 0.0
        
        stock_pool = StockPool(
            stock_code=symbol,
            stock_name=stock_info['name'],
            pool_type=request.pool_type,
            shares=request.shares or 0,
            avg_cost=request.avg_cost or 0.0,
            current_price=current_price,
            market_value=market_value,
            tags=request.tags,
            notes=request.notes
        )
        
        stock_id = bot.db_manager.add_stock(stock_pool)
        
        # 4. 返回创建的股票信息
        created_stock = bot.db_manager.get_stock_by_id(stock_id)
        stock_dict = stock_pool_to_dict(created_stock)
        
        pool_type_name = "持仓股票池" if request.pool_type == "holding" else "关注股票池"
        
        return ApiResponse(
            success=True, 
            data=stock_dict, 
            message=f"成功将 {stock_info['name']} ({symbol}) 添加到{pool_type_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mcp_connected": bot.session is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)