import json
import os
import asyncio
import sys
from typing import Optional, Dict, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class StockAnalysisBot:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        # 初始化Qwen-Coder客户端
        self.client = OpenAI(
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
        )
        
        # 股票名称到代码的映射
        self.stock_name_map = {
            "茅台": "600519",
            "贵州茅台": "600519",
            "平安": "000001",
            "中国平安": "000001",
            "腾讯": "00700",
            "阿里": "09988",
            "阿里巴巴": "09988",
            "比亚迪": "002594",
            "宁德时代": "300750",
            "美团": "03690",
            "小米": "01810"
        }
        
    async def connect_to_server(self, server_script_path: str):
        """连接到akshare MCP服务器"""
        try:
            # 使用Claude Desktop的akshare配置
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

            # 获取可用工具
            response = await self.session.list_tools()
            tools = response.tools
            print(f"🔗 已连接到akshare MCP服务器")
            print(f"📊 可用工具: {', '.join([tool.name for tool in tools])}")
            return True
            
        except Exception as e:
            print(f"❌ 连接MCP服务器失败: {e}")
            return False

    def normalize_stock_input(self, user_input: str) -> str:
        """将股票名称转换为代码，增强用户输入处理"""
        for name, code in self.stock_name_map.items():
            if name in user_input:
                user_input = user_input.replace(name, f"{name}({code})")
        return user_input

    async def process_query(self, query: str) -> str:
        """处理股票相关查询"""
        if not self.session:
            return "❌ 未连接到MCP服务器"

        # 预处理用户输入，添加股票代码信息
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

        # 获取可用工具列表
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
            # 调用LLM获取响应
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=messages,
                tools=available_tools,
                temperature=0.1
            )

            # 处理工具调用
            final_responses = []
            
            for choice in response.choices:
                message = choice.message
                
                if message.tool_calls:
                    # 有工具调用
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        print(f"🔍 正在调用工具: {tool_name}")
                        print(f"📝 参数: {tool_args}")
                        
                        # 执行工具调用
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                        except Exception as tool_error:
                            # 处理工具调用特定错误
                            error_msg = str(tool_error)
                            
                            # 针对不同类型的错误提供友好提示
                            if "KeyError" in error_msg and "current_liabilities" in error_msg:
                                tool_result_msg = "❌ 该股票的财务数据暂时无法获取，可能是数据源问题或股票代码不正确"
                            elif "symbol" in error_msg.lower() or "股票代码" in error_msg:
                                tool_result_msg = "❌ 股票代码格式错误，请检查输入的股票代码是否正确"
                            elif "timeout" in error_msg.lower() or "超时" in error_msg:
                                tool_result_msg = "❌ 网络连接超时，请稍后重试"
                            elif "connection" in error_msg.lower() or "连接" in error_msg:
                                tool_result_msg = "❌ 无法连接到数据源，请检查网络连接"
                            else:
                                tool_result_msg = f"❌ 数据获取失败: {tool_name}工具调用异常"
                            
                            # 创建错误结果对象
                            messages.append({
                                "role": "assistant", 
                                "content": f"正在调用{tool_name}工具..."
                            })
                            messages.append({
                                "role": "user",
                                "content": f"工具调用结果: {tool_result_msg}"
                            })
                            continue
                        
                        # 将工具结果添加到对话历史
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

                    # 基于工具调用结果生成最终分析
                    final_response = self.client.chat.completions.create(
                        model=os.getenv("MODEL"),
                        messages=messages,
                        temperature=0.1
                    )
                    final_responses.append(final_response.choices[0].message.content)
                    
                else:
                    # 直接回复，无需工具调用
                    final_responses.append(message.content)

            return "\n\n".join(final_responses) if final_responses else "抱歉，无法处理您的查询。"
            
        except Exception as e:
            return f"❌ 处理查询时发生错误: {e}"

    async def chat_loop(self):
        """股票分析聊天循环"""
        print("\n" + "="*60)
        print("🚀 股票看盘助手已启动！")
        print("💡 您可以询问:")
        print("   • 股票实时行情: '茅台现在多少钱'")  
        print("   • 技术分析: '分析一下比亚迪最近的走势'")
        print("   • 基本面分析: '茅台的财务状况怎么样'")
        print("   • 新闻资讯: '茅台最近有什么新闻'")
        print("💭 输入 'quit' 或 '退出' 结束对话")
        print("="*60)

        while True:
            try:
                query = input("\n📈 请输入您的股票问题: ").strip()
                
                if query.lower() in ['quit', '退出', 'exit', 'q']:
                    print("👋 感谢使用股票看盘助手，再见！")
                    break
                    
                if not query:
                    print("❓ 请输入有效的问题")
                    continue

                print("\n🤖 正在分析...")
                response = await self.process_query(query)
                print(f"\n📊 分析结果:\n{response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序已终止，再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()


async def main():
    # 获取MCP服务器路径
    server_path = os.getenv("AKSHARE_MCP_PATH")
    if not server_path:
        print("❌ 请在.env文件中设置AKSHARE_MCP_PATH")
        return
        
    if not os.path.exists(server_path):
        print(f"❌ MCP服务器文件不存在: {server_path}")
        return

    # 检查必要的环境变量
    required_vars = ["BASE_URL", "API_KEY", "MODEL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
        return

    bot = StockAnalysisBot()
    try:
        # 连接到MCP服务器
        if await bot.connect_to_server(server_path):
            # 启动聊天循环
            await bot.chat_loop()
    finally:
        # 清理资源
        await bot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())