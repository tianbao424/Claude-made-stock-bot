# 🤖 AI股票聊天助手

基于**FastAPI + WebSocket**的现代化股票分析聊天机器人，集成**Qwen-Coder AI**和**AkShare数据源**，提供实时股票分析、技术指标计算和财务数据查询。支持**CLI命令行**和**Web浏览器**双重使用方式。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-Real%20Time-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 核心特性

🧠 **AI智能分析** - 集成Qwen-Coder大语言模型，提供专业股票分析  
📊 **实时数据** - 通过AkShare获取实时股票行情和财务数据  
⚡ **双重界面** - CLI命令行 + Web浏览器两种使用方式  
🌐 **现代化Web界面** - 响应式设计，支持桌面和移动端  
💾 **数据持久化** - SQLite股票池管理，支持持仓和关注列表  
🔧 **一键部署** - 单文件架构，简化部署流程  

## 🏗️ 项目架构

```
stock-bot/
├── 📄 stock_bot.py            # CLI版本主程序
├── 📁 backend/                # Web版本服务端
│   ├── 📄 main.py            # FastAPI应用(内嵌前端)
│   ├── 📄 database.py        # 数据库管理模块
│   ├── 📄 requirements.txt   # Web版本依赖
│   └── 📄 stock_pool.db      # SQLite数据库
├── 📁 config/                # 配置文件目录
│   └── 📄 .env.template      # 环境变量模板
├── 📁 scripts/               # 部署脚本
│   ├── 📄 install.sh         # 自动安装脚本
│   └── 📄 start.sh          # 服务启动脚本
├── 📄 requirements.txt       # CLI版本依赖
├── 📄 README.md             # 项目文档
├── 📄 CLAUDE.md             # 开发指南
└── 📄 test_browser.js       # Web界面测试脚本
```

## 🚀 快速开始

### 1. 环境要求

- **Python 3.8+**
- **AkShare MCP服务器** (需要单独安装)
- **API密钥** (阿里云DashScope或兼容的OpenAI API)

### 2. 一键安装

```bash
# 克隆项目
git clone <repository-url>
cd stock-bot

# 运行安装脚本
./scripts/install.sh
```

### 3. 配置环境

复制环境配置模板并填入您的信息：

```bash
# 复制配置模板
cp .env.template .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

**必需配置项：**

```env
# AI服务配置
API_KEY=your_dashscope_api_key_here        # 从阿里云控制台获取
MODEL=qwen-coder-plus                      # AI模型名称
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 数据源配置  
AKSHARE_MCP_PATH=/path/to/your/python3     # Python环境路径
```

**可选配置项：**

```env
# Web服务配置
SERVER_HOST=0.0.0.0                        # 服务器主机 (默认: 0.0.0.0)
SERVER_PORT=8001                           # 服务器端口 (默认: 8001)

# 应用配置
DEBUG=False                                # 调试模式 (默认: False)
LOG_LEVEL=INFO                            # 日志级别 (默认: INFO)
```

### 4. 启动服务

#### 🌐 Web版本启动（推荐）

```bash
# 使用启动脚本
./scripts/start.sh

# 或直接启动
python3 backend/main.py
```

**访问地址：http://localhost:8001**

#### 💻 CLI版本启动

```bash
# 命令行版本
python3 stock_bot.py
```

## 💬 使用示例

### 🌐 Web版本功能

#### 主要界面特性
- **实时聊天界面** - 类似微信的对话体验
- **状态指示器** - 显示连接状态和AI思考过程
- **股票池管理** - 分类管理持仓股票和关注列表
- **响应式设计** - 完美支持手机、平板和桌面访问

#### 支持的查询类型

| 查询类型 | 示例问题 | 功能说明 |
|---------|----------|----------|
| 🏷️ **实时行情** | "茅台现在多少钱" | 获取最新股价、涨跌幅等 |
| 📈 **技术分析** | "分析一下比亚迪最近的走势" | 技术指标计算和趋势分析 |
| 💰 **基本面分析** | "茅台的财务状况怎么样" | 资产负债表、利润表等 |
| 📰 **新闻资讯** | "宁德时代最近有什么新闻" | 相关新闻和公告信息 |
| 📊 **历史数据** | "平安银行过去一个月走势" | 历史价格和成交量分析 |

### 💻 CLI版本功能

CLI版本提供纯命令行交互体验，适合开发者和命令行爱好者：

```bash
📈 请输入您的股票问题: 茅台现在多少钱
🤖 正在分析...
📊 分析结果:
贵州茅台(600519) 当前价格: ¥1,847.50 (+2.34%)
```

## 🛠️ 技术栈详解

### 后端技术

#### Web版本
- **FastAPI** - 现代异步Web框架，高性能API服务
- **WebSocket** - 实时双向通信，流畅聊天体验
- **SQLite** - 轻量级数据库，股票池数据持久化
- **Uvicorn** - 高性能ASGI服务器

#### CLI版本  
- **AsyncIO** - 异步I/O处理，提升响应速度
- **MCP协议** - 模型控制协议，连接AkShare数据源

### AI & 数据层
- **Qwen-Coder** - 阿里云大语言模型，专业股票分析
- **AkShare** - 金融数据接口库，数据源丰富
- **OpenAI API兼容** - 支持多种AI服务提供商

### 前端技术
- **内嵌HTML5** - 现代化单页应用，无需额外前端服务
- **响应式CSS** - CSS Grid + Flexbox，完美适配各种设备
- **原生JavaScript** - WebSocket客户端，无框架依赖

## 📊 支持的股票市场

### 中国A股
- 上海证券交易所 (60XXXX)
- 深圳证券交易所 (00XXXX, 30XXXX)

### 香港股市
- 港交所 (00XXX)

### 智能股票识别

系统内置常用股票名称映射，支持中文名称自动转换：

```python
"茅台/贵州茅台" → 600519
"平安/中国平安" → 000001  
"比亚迪" → 002594
"宁德时代" → 300750
"腾讯" → 00700
"阿里巴巴" → 09988
"美团" → 03690
"小米" → 01810
```

## 🎯 版本对比

| 特性 | CLI版本 | Web版本 |
|------|---------|---------|
| **界面体验** | 命令行文本 | 现代化Web UI |
| **访问方式** | 本地运行 | 浏览器访问 |
| **数据存储** | 无持久化 | SQLite数据库 |
| **用户支持** | 单用户 | 多用户并发 |
| **移动端** | 不支持 | 完整支持 |
| **股票池管理** | 不支持 | 完整支持 |
| **实时通信** | 标准I/O | WebSocket |
| **部署复杂度** | 极简单 | 简单 |
| **适用场景** | 开发调试 | 生产使用 |

## 🔧 高级配置

### 环境配置验证

```bash
# 验证配置是否正确
python3 config/settings.py
```

### 自定义服务端口

```env
# 在 .env 文件中设置
SERVER_HOST=127.0.0.1
SERVER_PORT=8080
```

### 添加新的股票映射

```python
# 在 backend/main.py 中的 stock_name_map 字典添加
"您的股票名称": "股票代码"
```

### 数据库配置

```env
# 在 .env 文件中设置数据库路径
DATABASE_PATH=data/custom_stock_pool.db
```

### 调试模式

```env
# 在 .env 文件中启用调试模式
DEBUG=True
LOG_LEVEL=DEBUG
```

## 📋 API接口文档

### WebSocket接口

```javascript
// 连接WebSocket
ws://localhost:8001/ws

// 发送查询消息
{
  "type": "query",
  "content": "茅台现在多少钱",
  "timestamp": "2025-01-01T12:00:00Z"
}

// 接收响应消息
{
  "type": "response|typing|error",
  "content": "响应内容"
}
```

### REST API接口

```bash
# 获取股票池列表
GET /api/stocks?pool_type=holding|potential

# 添加股票到池
POST /api/stocks
{
  "stock_code": "600519",
  "stock_name": "贵州茅台", 
  "pool_type": "holding",
  "shares": 100,
  "avg_cost": 1800.0,
  "notes": "长期持有"
}

# 健康检查
GET /health
```

## 🐛 故障排除

### 常见问题

**Q: 提示"未连接到MCP服务器"**  
A: 检查 `.env` 文件中的 `AKSHARE_MCP_PATH` 是否正确设置

**Q: Web界面无法加载**  
A: 确认端口8001未被占用，或修改为其他端口

**Q: AI回复"处理查询时发生错误"**  
A: 检查API密钥是否有效，网络连接是否正常

**Q: 股票数据无法获取**  
A: 确认AkShare MCP服务器正常运行

**Q: WebSocket连接失败**  
A: 检查防火墙设置，确保WebSocket端口可访问

### 日志查看

#### Web版本日志

```bash
python3 backend/main.py

# 正常启动日志:
# 🚀 启动AI股票聊天助手...
# ✅ Database initialized successfully
# 🔗 已连接到akshare MCP服务器
# 📊 可用工具: get_hist_data, get_realtime_data...
# INFO: Uvicorn running on http://0.0.0.0:8001
```

#### CLI版本日志

```bash
python3 stock_bot.py

# 正常启动日志:
# 🚀 股票看盘助手已启动！
# 💡 您可以询问...
```

### 依赖问题解决

```bash
# 重新安装依赖
pip3 install -r requirements.txt
pip3 install -r backend/requirements.txt

# 检查Python版本
python3 --version  # 应该 >= 3.8

# 检查关键依赖
python3 -c "import fastapi, openai, mcp"
```

## 🚀 部署指南

### 开发环境部署

```bash
# 1. 安装和配置
./scripts/install.sh
vim .env  # 配置API密钥

# 2. 启动开发服务
python3 backend/main.py

# 3. 访问测试
curl http://localhost:8001/health
```

### 生产环境建议

```bash
# 使用进程管理器
pip3 install supervisor
# 或使用 Docker 容器化部署

# 反向代理配置 (Nginx)
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发流程

1. **Fork项目** - 创建您的功能分支
2. **本地开发** - 使用CLI版本快速测试逻辑
3. **Web集成** - 在Web版本中集成新功能  
4. **测试验证** - 运行`node test_browser.js`进行自动化测试
5. **提交代码** - 创建Pull Request

### 代码规范

- 遵循Python PEP 8编码规范
- 异步函数使用async/await
- 添加适当的错误处理
- 保持CLI和Web版本功能一致性

## 📄 开源协议

本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源协议。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代异步Web框架
- [AkShare](https://github.com/akfamily/akshare) - 金融数据接口
- [Qwen-Coder](https://tongyi.aliyun.com/) - 阿里云大语言模型
- [MCP Protocol](https://modelcontextprotocol.io/) - 模型控制协议

## 📈 项目状态

- ✅ **CLI版本**: 生产就绪，功能完整
- ✅ **Web版本**: 生产就绪，现代化界面
- ✅ **数据库**: SQLite持久化存储
- ✅ **API接口**: REST + WebSocket双重支持
- ✅ **移动端**: 响应式设计完整支持
- ✅ **部署**: 一键启动，简化运维

---

⭐ **如果这个项目对您有帮助，请给一个Star！**

🔗 **立即体验**: 运行 `./scripts/start.sh` 然后访问 http://localhost:8001