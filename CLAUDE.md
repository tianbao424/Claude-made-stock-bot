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
│   ├── DatabaseManager    # 数据库操作类
│   └── SQLite管理         # 数据持久化
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

### 🎯 v1.1.0 完成功能
- ✅ React前端架构完整实现
- ✅ 表格式股票池管理界面
- ✅ 标签和备注系统
- ✅ WebSocket实时通信
- ✅ 响应式UI设计
- ✅ 一键启动系统 (`npm run dev`)
- ✅ TypeScript类型安全
- ✅ 自定义CSS样式系统

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
- **ChatInterface.tsx** - AI聊天界面
- **useStockPool.ts** - 股票池数据管理Hook
- **useWebSocket.ts** - WebSocket通信Hook

### 🔄 数据库结构
```sql
CREATE TABLE stock_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,           -- 股票代码
    stock_name TEXT NOT NULL,           -- 股票名称
    pool_type TEXT NOT NULL,            -- holding|potential
    tags TEXT DEFAULT '',               -- JSON格式标签
    notes TEXT DEFAULT '',              -- 备注信息
    created_at TEXT NOT NULL,           -- 创建时间
    updated_at TEXT NOT NULL,           -- 更新时间
    UNIQUE(stock_code, pool_type)
);
```

---

**更新时间**: 2025-09-01  
**版本**: v1.1.0  
**维护者**: Claude AI Assistant