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

def stock_pool_to_dict(stock: 'StockPool') -> Dict:
    """将StockPool对象转换为字典"""
    return {
        "id": stock.id,
        "stock_code": stock.stock_code,
        "stock_name": stock.stock_name,
        "pool_type": stock.pool_type,
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
async def search_stocks(query: str, limit: int = 20):
    """智能搜索股票"""
    try:
        if not query.strip():
            return ApiResponse(success=False, message="搜索关键词不能为空")
        
        # 使用已有的数据库管理器
        results = bot.db_manager.search_stocks(query.strip(), limit)
        
        # 转换为响应格式
        stock_list = []
        for stock in results:
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
                "is_active": stock.is_active
            }
            stock_list.append(stock_dict)
        
        return ApiResponse(
            success=True, 
            data=stock_list, 
            message=f"找到 {len(stock_list)} 条结果"
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
    """获取股票数据统计信息"""
    try:
        count = bot.db_manager.get_stock_info_count()
        return ApiResponse(
            success=True, 
            data={"total_stocks": count}, 
            message=f"数据库中共有 {count} 只股票"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/realtime/{symbol}")
async def get_stock_realtime(symbol: str):
    """获取股票实时行情数据"""
    try:
        # 从数据库获取股票基本信息以确定市场
        stock_info = bot.db_manager.get_stock_info_by_symbol(symbol)
        
        if not stock_info:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        # 根据市场类型获取实时数据
        market = "HK" if stock_info.market == "HK" else "A"
        realtime_data = await akshare_service.get_stock_realtime_data(symbol, market)
        
        if not realtime_data:
            raise HTTPException(status_code=500, detail="获取实时数据失败")
        
        return ApiResponse(
            success=True, 
            data=realtime_data,
            message="实时数据获取成功"
        )
    except HTTPException:
        raise
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

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mcp_connected": bot.session is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)