# 🤖 AI股票聊天助手 - 开发指南

本文档为Claude开发人员提供项目结构、技术细节和开发指导。

## 📁 项目结构详解

### 🏗️ 根目录结构
```
stock-bot/
├── 📄 package.json                   # 主项目配置，包含并发启动脚本
├── 📄 stock_bot.py                   # CLI版本(保留兼容性)
├── 📄 requirements.txt               # Python依赖包列表
├── 📁 backend/                       # 后端FastAPI服务
├── 📁 frontend/                      # React前端应用
├── 📁 config/                        # 配置管理模块
├── 📁 scripts/                       # 部署和工具脚本
├── 📁 tests/                         # 测试文件
└── 📄 *.md                          # 文档文件
```

### 🔧 后端架构 (backend/)
```python
backend/
├── main.py                 # FastAPI应用入口
│   ├── WebStockAnalysisBot # 主业务逻辑类
│   ├── ConnectionManager   # WebSocket连接管理
│   ├── API路由定义         # REST API端点
│   └── WebSocket处理       # 实时通信
├── database.py             # 数据层
│   ├── StockPool          # 股票池数据模型
│   ├── StrategyAnalysis   # 策略分析数据模型
│   ├── DatabaseManager    # 数据库操作类
│   └── SQLite管理         # 数据持久化
├── services/               # 业务服务层
│   ├── strategy_service.py # AI策略分析服务
│   ├── akshare_service.py  # AkShare数据服务
│   └── ...                # 其他服务
├── requirements.txt        # Python依赖
└── stock_pool.db          # SQLite数据库文件
```

### ⚛️ 前端架构 (frontend/)
```typescript
frontend/
├── src/
│   ├── components/                    # React组件
│   │   ├── StockPoolManager.tsx      # 股票池管理主界面
│   │   ├── StockPoolForm.tsx         # 股票添加/编辑表单
│   │   ├── StrategyAnalysisButton.tsx # AI策略分析按钮
│   │   ├── StrategyModal.tsx         # 策略分析结果展示
│   │   └── ChatInterface.tsx         # AI聊天界面
│   ├── hooks/                        # 自定义React Hooks
│   │   ├── useStockPool.ts           # 股票池数据管理
│   │   └── useWebSocket.ts           # WebSocket通信
│   ├── services/                     # 服务层
│   │   └── api.ts                    # HTTP API客户端
│   ├── types/                        # TypeScript类型定义
│   │   └── index.ts                  # 共享类型接口
│   ├── App.tsx                       # 主应用组件
│   ├── App.css                       # 全局样式
│   └── main.tsx                      # 应用入口点
├── package.json                      # 前端依赖配置
├── vite.config.ts                    # Vite构建配置
├── tsconfig.json                     # TypeScript配置
└── index.html                        # HTML入口文件
```

## 🛠️ 技术栈详解

### 🔙 后端技术栈

#### FastAPI框架
```python
# main.py - 核心应用结构
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AI股票聊天助手", version="1.1.0")

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
```

#### 数据库设计
```python
# database.py - 数据模型
@dataclass
class StockPool:
    stock_code: str              # 股票代码
    stock_name: str              # 股票名称  
    pool_type: str               # holding|potential
    tags: Optional[List[str]]    # 标签列表(JSON存储)
    notes: str                   # 备注信息
    created_at: str              # 创建时间
    updated_at: str              # 更新时间
    id: Optional[int] = None     # 主键ID
```

#### API端点设计
```python
# REST API路由
@app.get("/api/stock-pools")           # 获取股票池列表
@app.post("/api/stock-pools")          # 创建股票
@app.get("/api/stock-pools/{id}")      # 获取单个股票
@app.put("/api/stock-pools/{id}")      # 更新股票
@app.delete("/api/stock-pools/{id}")   # 删除股票

# AI策略分析API
@app.post("/api/strategy/generate/{stock_pool_id}")  # 生成策略分析
@app.get("/api/strategy/history/{stock_pool_id}")   # 获取策略历史
@app.get("/api/strategy/{strategy_id}")             # 获取单个策略

# WebSocket端点
@app.websocket("/ws")                  # 实时聊天通信
```

### 🎨 前端技术栈

#### React组件架构
```typescript
// App.tsx - 主应用结构
const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  
  return (
    <div className="h-screen bg-gray-50 flex">
      <Sidebar />                    {/* 导航侧边栏 */}
      <MainContent>
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'pool' && <StockPoolManager />}
      </MainContent>
    </div>
  );
};
```

#### 数据管理Hooks
```typescript
// useStockPool.ts - 股票池数据管理
export const useStockPool = () => {
  const [stockPools, setStockPools] = useState<StockPool[]>([]);
  const [loading, setLoading] = useState(false);
  
  const createStockPool = async (data: StockPoolCreate) => {
    const newPool = await stockPoolAPI.create(data);
    setStockPools(prev => [...prev, newPool]);
  };
  
  return { stockPools, createStockPool, ... };
};
```

#### WebSocket通信
```typescript
// useWebSocket.ts - 实时通信管理
export const useWebSocket = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  
  const sendMessage = (content: string) => {
    const wsMessage = { type: 'query', content };
    wsRef.current?.send(JSON.stringify(wsMessage));
  };
  
  return { messages, sendMessage, ... };
};
```

## 🔄 数据流设计

### 📊 股票池管理流程
```
前端操作 → API调用 → 后端处理 → 数据库更新 → 响应返回 → UI更新
    ↓
StockPoolManager.tsx
    ↓
useStockPool Hook
    ↓  
api.ts (HTTP Client)
    ↓
FastAPI Route Handler
    ↓
DatabaseManager
    ↓
SQLite Database
```

### 💬 AI聊天流程
```
用户输入 → WebSocket发送 → AI处理 → MCP调用 → 数据获取 → AI分析 → 响应返回
    ↓
ChatInterface.tsx
    ↓
useWebSocket Hook
    ↓
WebSocket Connection
    ↓
FastAPI WebSocket Handler
    ↓
WebStockAnalysisBot.process_query()
    ↓
MCP AkShare Server
    ↓
AI Model (Qwen-Coder)
```

### 🤖 AI策略分析流程
```
点击策略按钮 → 实时价格更新 → 数据收集 → AI策略生成 → 结果存储 → 策略展示
    ↓
StrategyAnalysisButton.tsx
    ↓
strategyAPI.generateAnalysis()
    ↓
POST /api/strategy/generate/{id}
    ↓
StrategyDataCollector.collect_comprehensive_data()
    ↓ (并发收集)
├── 技术指标 (RSI, MACD, BOLL)
├── 基本面数据 (PE, PB, ROE)
├── 市场环境数据
└── 价格历史数据
    ↓
AIStrategyGenerator.generate_strategy()
    ↓
OpenAI Compatible API (Qwen-Coder-Plus)
    ↓
StrategyModal.tsx (结果展示)
```

## 🤖 AI策略分析系统详解

### 💡 核心功能
AI策略分析系统是本项目的核心创新功能，为持仓股票提供智能化的投资策略建议。

#### ✨ 主要特性
- **🔄 实时数据更新**：策略生成前自动获取最新股价
- **📊 多维度分析**：技术面、基本面、市场环境综合分析
- **🧠 AI驱动生成**：基于Qwen-Coder-Plus模型的智能策略生成
- **📈 量化评分**：1-10分综合评分系统
- **⚠️ 风险评估**：低/中/高风险等级评估
- **📋 具体建议**：买入/持有/减仓/卖出操作建议
- **📅 历史记录**：完整的策略分析历史追踪

#### 🔧 技术实现

**数据收集层** (`StrategyDataCollector`)
```python
# 并发收集多维度数据
tasks = [
    get_technical_indicators(stock_code),    # RSI, MACD, BOLL指标
    get_fundamental_data(stock_code),        # PE, PB, ROE财务数据
    get_market_context(stock_code),          # 大盘走势, 市场情绪
    get_price_history(stock_code, days=30)   # 30天价格历史
]
```

**AI策略生成层** (`AIStrategyGenerator`)
```python
# 结构化提示工程
prompt = f"""
## 投资策略分析请求
### 股票基本信息: {stock_name}({stock_code})
### 持仓情况: {shares}股, 成本￥{avg_cost}, 现价￥{current_price}
### 技术面数据: RSI {rsi}, MACD {macd_signal}
### 基本面数据: PE {pe_ratio}, ROE {roe}%
### 市场环境: {market_trend}

请提供结构化的投资策略建议(JSON格式)...
"""
```

**前端展示层** (`StrategyModal`)
- 📱 响应式全屏模态框设计
- 🎨 可视化风险等级和操作建议
- 📊 清晰的目标价位区间展示
- 📋 详细的分析内容和行动计划
- 📈 策略历史记录对比

#### 🎯 使用场景
1. **持仓优化**：为现有持仓提供操作建议
2. **风险控制**：评估持仓风险等级
3. **投资决策**：基于AI分析制定投资策略
4. **策略追踪**：历史策略对比和复盘

## 🛠️ 开发工作流

### 🚀 开发环境搭建
```bash
# 1. 克隆项目
git clone <repository>
cd stock-bot

# 2. 安装依赖
npm install              # 安装根目录和前端依赖
pip install -r requirements.txt  # 安装后端依赖

# 3. 启动开发服务器
npm run dev             # 并发启动前后端
```

### 📝 代码规范

#### Python代码规范
```python
# 遵循PEP 8规范
# 使用类型注解
async def create_stock_pool(
    stock_data: StockPoolCreateRequest
) -> ApiResponse[StockPool]:
    """创建股票池条目
    
    Args:
        stock_data: 股票池创建请求数据
        
    Returns:
        包含创建结果的API响应
        
    Raises:
        HTTPException: 当创建失败时抛出
    """
    try:
        # 实现逻辑
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### TypeScript代码规范  
```typescript
// 使用严格类型检查
// 接口优先于类型别名
interface StockPoolCreateRequest {
  stock_code: string;
  stock_name: string;
  pool_type: 'holding' | 'potential';
  tags?: string[];
  notes?: string;
}

// 使用函数式组件和Hooks
const StockPoolManager: React.FC = () => {
  // Hook调用位于顶层
  const { stockPools, createStockPool } = useStockPool();
  
  // 事件处理函数
  const handleCreate = useCallback(async (data: StockPoolCreateRequest) => {
    try {
      await createStockPool(data);
    } catch (error) {
      console.error('创建失败:', error);
    }
  }, [createStockPool]);
  
  return <div>...</div>;
};
```

### 🧪 测试策略

#### 后端测试
```python
# tests/test_database.py
import pytest
from backend.database import DatabaseManager, StockPool

@pytest.fixture
def db_manager():
    return DatabaseManager(":memory:")  # 内存数据库测试

def test_create_stock_pool(db_manager):
    stock = StockPool(
        stock_code="000001",
        stock_name="平安银行", 
        pool_type="holding"
    )
    stock_id = db_manager.add_stock(stock)
    assert stock_id is not None
```

#### 前端测试
```typescript
// 使用React Testing Library
import { render, screen } from '@testing-library/react';
import StockPoolManager from './StockPoolManager';

test('renders stock pool manager', () => {
  render(<StockPoolManager />);
  expect(screen.getByText('股票池管理')).toBeInTheDocument();
});
```

## 🔧 配置管理

### 环境变量配置
```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AI服务配置
    API_KEY: str
    BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL: str = "qwen-coder-plus"
    
    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001
    
    # 数据库配置  
    DATABASE_PATH: str = "stock_pool.db"
    
    class Config:
        env_file = ".env"
```

### Vite配置
```typescript
// frontend/vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8001', 
        ws: true,
      },
    },
  },
});
```

## 🚀 部署指南

### 开发部署
```bash
# 使用npm并发启动
npm run dev
```

### 生产部署
```bash
# 构建前端
npm run build

# 启动后端(生产模式)
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### Docker部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY frontend/dist/ ./frontend/dist/

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 🐛 调试指南

### 后端调试
```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# FastAPI自动文档: http://localhost:8001/docs
# 查看API交互和测试端点
```

### 前端调试
```typescript
// 使用React Developer Tools
// Chrome控制台查看网络请求
// Vite热重载和错误提示

// WebSocket连接调试
const ws = new WebSocket('ws://localhost:8001/ws');
ws.onmessage = (event) => {
  console.log('WebSocket message:', JSON.parse(event.data));
};
```

## 📈 性能优化

### 后端优化
- 使用异步操作 (async/await)
- 数据库连接池管理
- Redis缓存热点数据
- API响应压缩

### 前端优化
- React.memo() 避免不必要重渲染
- useMemo() 缓存计算结果  
- useCallback() 稳定函数引用
- 虚拟滚动处理大量数据

## 🔐 安全考虑

- API密钥环境变量存储
- SQL注入防护 (Pydantic验证)
- CORS跨域配置
- WebSocket连接认证
- 输入数据验证和清理

## ✅ 当前状态

### 🎯 v2.0.0 完成功能
- ✅ React前端架构完整实现
- ✅ 表格式股票池管理界面
- ✅ 标签和备注系统
- ✅ WebSocket实时通信
- ✅ 响应式UI设计
- ✅ 一键启动系统 (`npm run dev`)
- ✅ TypeScript类型安全
- ✅ 自定义CSS样式系统
- ✅ **AI投资策略分析系统**
- ✅ **实时价格获取和更新**
- ✅ **完整的策略历史记录**
- ✅ **智能化投资建议生成**

### 🚀 启动方式
```bash
# 一键启动前后端
npm run dev

# 访问地址
# 前端: http://localhost:3000
# 后端: http://localhost:8001
```

### 📋 主要组件
- **StockPoolManager.tsx** - 股票池管理主界面 (表格视图)
- **StockPoolForm.tsx** - 股票添加/编辑表单
- **StrategyAnalysisButton.tsx** - AI策略分析触发按钮
- **StrategyModal.tsx** - 策略分析结果展示模态框
- **ChatInterface.tsx** - AI聊天界面
- **useStockPool.ts** - 股票池数据管理Hook
- **useWebSocket.ts** - WebSocket通信Hook

### 🔄 数据库结构
```sql
-- 股票池表
CREATE TABLE stock_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,           -- 股票代码
    stock_name TEXT NOT NULL,           -- 股票名称
    pool_type TEXT NOT NULL,            -- holding|potential
    shares INTEGER DEFAULT 0,           -- 持股数量
    avg_cost REAL DEFAULT 0.0,          -- 平均成本
    current_price REAL DEFAULT 0.0,     -- 当前价格
    market_value REAL DEFAULT 0.0,      -- 市值
    tags TEXT DEFAULT '',               -- JSON格式标签
    notes TEXT DEFAULT '',              -- 备注信息
    created_at TEXT NOT NULL,           -- 创建时间
    updated_at TEXT NOT NULL,           -- 更新时间
    UNIQUE(stock_code, pool_type)
);

-- 策略分析表
CREATE TABLE strategy_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_pool_id INTEGER NOT NULL,     -- 关联股票池ID
    stock_code TEXT NOT NULL,           -- 股票代码
    
    -- 分析时的持仓数据
    shares_at_analysis INTEGER,         -- 分析时持股数量
    cost_at_analysis REAL,              -- 分析时成本价
    price_at_analysis REAL,             -- 分析时股价
    market_value_at_analysis REAL,      -- 分析时市值
    profit_loss_pct REAL,               -- 盈亏百分比
    
    -- AI策略结果
    comprehensive_score REAL,           -- 综合评分(1-10)
    risk_level TEXT,                    -- 风险等级(low/medium/high)
    action_recommendation TEXT,         -- 操作建议(buy/hold/reduce/sell)
    target_price_min REAL,              -- 目标价位下限
    target_price_max REAL,              -- 目标价位上限
    timeframe TEXT,                     -- 投资时间框架(short/medium/long)
    position_suggestion REAL,           -- 建议仓位比例(0-1)
    
    -- 分析内容(JSON格式存储)
    analysis_summary TEXT,              -- 分析摘要
    key_metrics TEXT,                   -- 关键指标
    risk_warnings TEXT,                 -- 风险提示
    action_plan TEXT,                   -- 行动计划
    technical_analysis TEXT,            -- 技术分析
    fundamental_analysis TEXT,          -- 基本面分析
    market_context TEXT,                -- 市场环境
    
    -- 元数据
    analysis_date TEXT NOT NULL,        -- 分析日期
    model_version TEXT DEFAULT 'qwen-coder-plus',  -- AI模型版本
    confidence_level REAL,              -- 置信度(0-1)
    created_at TEXT NOT NULL,           -- 创建时间
    
    FOREIGN KEY (stock_pool_id) REFERENCES stock_pool(id)
);
```

---

**更新时间**: 2025-09-09  
**版本**: v2.0.0  
**维护者**: Claude AI Assistant