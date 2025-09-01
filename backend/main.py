import os
import json
import asyncio
from typing import Dict, List, Optional
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

from database import DatabaseManager, StockPool

load_dotenv()

app = FastAPI(title="AI股票聊天助手", version="1.0.0")

# 挂载静态文件服务
import os
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
        
        self.db_manager = DatabaseManager()

    async def connect_to_server(self) -> bool:
        try:
            server_params = StdioServerParameters(
                command="/Users/quxiaomeng/.venvs/akmcp312/bin/python3",
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
            print(f"🔗 已连接到akshare MCP服务器")
            print(f"📊 可用工具: {', '.join([tool.name for tool in response.tools])}")
            return True
            
        except Exception as e:
            print(f"❌ 连接MCP服务器失败: {e}")
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

class StockPoolAPI(BaseModel):
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    pool_type: str = Field(..., description="池类型", pattern="^(holding|potential)$")
    shares: int = Field(0, description="持股数量")
    avg_cost: float = Field(0.0, description="平均成本")
    notes: str = Field("", description="备注")

bot = WebStockAnalysisBot()
manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    print("🚀 启动AI股票聊天助手...")
    success = await bot.connect_to_server()
    if success:
        print("✅ Stock bot initialized successfully")
    else:
        print("❌ Failed to connect to MCP server")

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

@app.get("/api/stocks")
async def get_stocks(pool_type: Optional[str] = None):
    try:
        stocks = bot.db_manager.get_stocks(pool_type)
        return {"stocks": [stock.__dict__ for stock in stocks]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stocks")
async def add_stock(stock_data: StockPoolAPI):
    try:
        stock = StockPool(
            stock_code=stock_data.stock_code,
            stock_name=stock_data.stock_name,
            pool_type=stock_data.pool_type,
            shares=stock_data.shares,
            avg_cost=stock_data.avg_cost,
            notes=stock_data.notes
        )
        stock_id = bot.db_manager.add_stock(stock)
        return {"message": "股票添加成功", "stock_id": stock_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mcp_connected": bot.session is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)