# 🔧 开发指南

## 🚀 环境搭建

### 系统要求
- **操作系统**: macOS、Windows、Linux
- **Node.js**: 18.0+ (推荐使用 LTS 版本)
- **Python**: 3.9+
- **Git**: 最新版本
- **内存**: 最少 8GB (推荐 16GB)

### 开发工具推荐
- **IDE**: VS Code / PyCharm / WebStorm
- **终端**: iTerm2 (macOS) / Windows Terminal
- **API测试**: Postman / Insomnia
- **数据库工具**: DB Browser for SQLite

### 快速启动

#### 1. 克隆项目
```bash
git clone <repository-url>
cd "Claude made stock bot"
```

#### 2. 安装依赖
```bash
# 安装前端依赖
cd frontend
npm install

# 返回根目录并安装Python依赖
cd ..
pip install -r requirements.txt

# 或者使用虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. 环境配置
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

#### 4. 数据库初始化
系统启动时会自动创建SQLite数据库，但建议手动初始化历史数据：
```bash
# 启动后端服务
cd backend
python main.py

# 访问前端界面 http://localhost:3000
# 点击股票甄选页面的"初始化数据"按钮
# 等待系统收集近7天的历史数据（约5-10分钟）
```

#### 4. 启动开发环境
```bash
# 方式一：一键启动 (推荐)
npm run dev

# 方式二：分别启动
npm run backend  # 启动后端
npm run frontend # 启动前端
```

### 环境验证
启动成功后验证以下URL：
- **前端**: http://localhost:3000
- **后端API文档**: http://localhost:8001/docs
- **WebSocket**: ws://localhost:8001/ws

## 📁 项目结构详解

### 根目录文件
```
Claude made stock bot/
├── package.json              # 项目元数据和脚本
├── requirements.txt          # Python依赖声明
├── .env.example             # 环境变量模板
├── .gitignore               # Git忽略规则
├── CLAUDE.md                # 开发者文档索引
└── README.md                # 用户使用手册
```

### 前端目录结构
```
frontend/
├── src/
│   ├── components/          # 可复用组件
│   │   ├── StockPoolManager.tsx         # 股票池管理
│   │   ├── StockScreeningDashboard.tsx  # 筛选面板
│   │   ├── ChatInterface.tsx            # 聊天界面
│   │   ├── DeepAnalysisDashboard.tsx    # 深度分析
│   │   └── common/                      # 通用组件
│   ├── hooks/               # 自定义Hooks
│   │   ├── useStockPool.ts              # 股票池状态
│   │   ├── useWebSocket.ts              # WebSocket通信
│   │   └── useStockScreening.ts         # 筛选状态
│   ├── services/            # API服务层
│   │   └── api.ts                       # HTTP客户端
│   ├── types/               # TypeScript类型
│   │   └── index.ts                     # 共享类型定义
│   ├── utils/               # 工具函数
│   ├── App.tsx              # 主应用组件
│   ├── App.css              # 全局样式
│   └── main.tsx             # 应用入口点
├── public/                  # 静态资源
├── index.html               # HTML入口文件
├── vite.config.ts           # Vite配置
├── tsconfig.json            # TypeScript配置
└── package.json             # 前端依赖管理
```

### 后端目录结构
```
backend/
├── main.py                  # FastAPI应用入口
├── database.py              # 数据访问层
├── services/                # 业务服务层
│   ├── strategy_service.py              # AI策略分析
│   ├── stock_screening_service.py       # 股票筛选
│   ├── stock_deep_analysis_service.py   # 深度分析
│   ├── volatility_analyzer.py           # 波动性分析
│   ├── volume_analyzer.py               # 成交量分析
│   ├── auto_pool_manager.py             # 自动池管理
│   ├── akshare_service.py               # 数据源服务
│   └── data_sync_scheduler.py           # 数据同步调度
├── utils/                   # 工具模块
│   └── market_hours.py                  # 交易时间工具
├── config/                  # 配置管理
└── stock_pool.db            # SQLite数据库文件
```

## 🛠️ 开发工作流

### Git工作流
我们采用 Feature Branch 工作流：

```bash
# 1. 创建功能分支
git checkout -b feature/股票筛选优化

# 2. 开发过程中定期提交
git add .
git commit -m "feat: 新增全市场数据收集功能"

# 3. 推送到远程仓库
git push origin feature/股票筛选优化

# 4. 创建Pull Request
# 5. Code Review后合并到主分支
```

### 分支命名规范
- `feature/功能名称` - 新功能开发
- `fix/问题描述` - Bug修复
- `docs/文档更新` - 文档更新
- `refactor/重构说明` - 代码重构
- `test/测试说明` - 测试相关

### 提交信息规范
```bash
type(scope): description

# Types:
feat     # 新功能
fix      # 修复bug
docs     # 文档更新
style    # 代码格式调整
refactor # 重构
test     # 测试
chore    # 构建/工具/依赖更新

# Examples:
feat(stock-pool): 添加批量导入功能
fix(api): 修复股票搜索接口超时问题
docs: 更新API文档
refactor(database): 优化数据库查询性能
```

## 📝 编码规范

### Python代码规范
遵循 PEP 8 标准，使用 Black 格式化工具：

```python
# 导入顺序
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database import DatabaseManager
from services.akshare_service import akshare_service

# 类定义
class StockAnalysisService:
    """股票分析服务
    
    提供完整的股票分析功能，包括技术分析、基本面分析等。
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._cache = {}
    
    async def analyze_stock(self, stock_code: str) -> Dict[str, Any]:
        """分析单只股票
        
        Args:
            stock_code: 股票代码
            
        Returns:
            分析结果字典
            
        Raises:
            ValueError: 股票代码无效时抛出
        """
        if not stock_code:
            raise ValueError("股票代码不能为空")
        
        # 获取股票数据
        stock_data = await self._get_stock_data(stock_code)
        
        return {
            "stock_code": stock_code,
            "analysis_result": stock_data,
            "timestamp": datetime.now().isoformat()
        }
```

### TypeScript代码规范
使用严格的TypeScript配置：

```typescript
// 接口定义
interface StockPool {
  id: number;
  stock_code: string;
  stock_name: string;
  pool_type: 'holding' | 'potential';
  shares: number;
  avg_cost: number;
  current_price: number;
  created_at: string;
}

// 组件定义
const StockPoolManager: React.FC = () => {
  // 状态管理
  const { stockPools, loading, error, createStockPool } = useStockPool();
  
  // 事件处理
  const handleCreateStock = useCallback(async (data: StockPoolCreate) => {
    try {
      await createStockPool(data);
    } catch (error) {
      console.error('创建失败:', error);
    }
  }, [createStockPool]);
  
  // 条件渲染
  if (loading) {
    return <LoadingSpinner />;
  }
  
  if (error) {
    return <ErrorMessage message={error} />;
  }
  
  return (
    <div className="space-y-4">
      {/* 组件内容 */}
    </div>
  );
};

export default React.memo(StockPoolManager);
```

### CSS/样式规范
使用 Tailwind CSS 实用优先的方法：

```tsx
// 组件样式示例
const StockCard: React.FC<StockCardProps> = ({ stock }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900">
          {stock.stock_name}
        </h3>
        <span className="text-sm text-gray-500">
          {stock.stock_code}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600">当前价格:</span>
          <span className="font-medium ml-1">¥{stock.current_price}</span>
        </div>
        <div>
          <span className="text-gray-600">持股数量:</span>
          <span className="font-medium ml-1">{stock.shares}股</span>
        </div>
      </div>
    </div>
  );
};
```

## 🧪 测试策略

### 前端测试
使用 Vitest + React Testing Library：

```typescript
// StockPoolManager.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import StockPoolManager from '../StockPoolManager';

// Mock API calls
vi.mock('../services/api', () => ({
  stockPoolAPI: {
    getAll: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue({ id: 1 }),
    update: vi.fn().mockResolvedValue({ id: 1 }),
    delete: vi.fn().mockResolvedValue(undefined)
  }
}));

describe('StockPoolManager', () => {
  test('renders stock pool manager', () => {
    render(<StockPoolManager />);
    expect(screen.getByText('股票池管理')).toBeInTheDocument();
  });
  
  test('creates new stock pool', async () => {
    render(<StockPoolManager />);
    
    // 点击添加按钮
    fireEvent.click(screen.getByText('添加股票'));
    
    // 填写表单
    fireEvent.change(screen.getByLabelText('股票代码'), {
      target: { value: '000001' }
    });
    
    // 提交表单
    fireEvent.click(screen.getByText('确认添加'));
    
    // 验证API调用
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        stock_code: '000001',
        stock_name: '平安银行'
      });
    });
  });
});
```

### 后端测试
使用 pytest + FastAPI TestClient：

```python
# test_stock_pool.py
import pytest
from fastapi.testclient import TestClient
from main import app
from database import DatabaseManager

client = TestClient(app)

@pytest.fixture
def db_manager():
    """测试数据库管理器"""
    return DatabaseManager(":memory:")

def test_create_stock_pool():
    """测试创建股票池"""
    response = client.post("/api/stock-pools", json={
        "stock_code": "000001",
        "stock_name": "平安银行",
        "pool_type": "holding",
        "shares": 1000,
        "avg_cost": 12.50
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["stock_code"] == "000001"

def test_get_stock_pools():
    """测试获取股票池列表"""
    response = client.get("/api/stock-pools")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
```

### 集成测试
```bash
# 运行所有测试
npm run test

# 运行前端测试
npm run test:frontend

# 运行后端测试
npm run test:backend

# 生成测试覆盖率报告
npm run test:coverage
```

## 🔧 调试指南

### 前端调试
1. **浏览器DevTools**：使用Chrome DevTools调试
2. **React DevTools**：安装React开发者扩展
3. **网络面板**：监控API请求和响应
4. **Console日志**：使用console.log进行调试

### 后端调试
1. **FastAPI文档**：访问 http://localhost:8001/docs
2. **Python调试器**：使用pdb或IDE调试器
3. **日志输出**：配置logging模块
4. **API测试**：使用Postman测试API端点

### 常见问题排查

#### 端口冲突
```bash
# 查看端口占用
lsof -ti:8001 | xargs kill -9  # 杀死8001端口进程
lsof -ti:3000 | xargs kill -9  # 杀死3000端口进程

# 或者使用项目脚本
npm run stop
```

#### 依赖问题
```bash
# 清理依赖
rm -rf node_modules package-lock.json
npm install

# Python依赖问题
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### 数据库问题
```bash
# 重建数据库
rm backend/stock_pool.db
python backend/database.py
```

## 📊 性能优化

### 前端优化
1. **代码分割**：使用React.lazy进行路由级分割
2. **组件优化**：使用React.memo避免不必要的重渲染
3. **状态管理**：避免过度渲染和状态提升
4. **资源优化**：图片压缩、懒加载

### 后端优化
1. **数据库优化**：合理使用索引、优化查询
2. **缓存策略**：对频繁查询的数据使用缓存
3. **并发处理**：使用asyncio处理并发请求
4. **API限流**：防止API滥用

### 监控和诊断
```python
# 性能监控中间件
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 🚀 部署流程

### 开发环境
```bash
# 启动开发服务器
npm run dev
```

### 生产环境构建
```bash
# 构建前端
cd frontend
npm run build

# 创建生产环境配置
cp .env.example .env.prod
# 编辑生产环境变量

# 启动生产服务器
npm run start:prod
```

### Docker部署
```dockerfile
# 多阶段构建
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ .
RUN npm run build

FROM python:3.9-slim AS backend
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/
EXPOSE 8001
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

**下一步**: 查看 [算法详解](05-algorithms.md) 了解系统核心算法的实现原理。