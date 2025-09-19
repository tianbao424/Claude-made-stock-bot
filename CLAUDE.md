# 🤖 AI股票聊天助手 - 技术开发文档

本文档为Claude开发人员提供项目完整技术架构、开发指南和最佳实践。

## 📁 项目架构全览

### 🏗️ 根目录结构
```
Claude made stock bot/
├── 📄 package.json                   # 主项目配置，包含并发启动脚本
├── 📄 requirements.txt               # Python依赖包列表
├── 📁 backend/                       # 后端FastAPI服务
├── 📁 frontend/                      # React前端应用
├── 📁 config/                        # 配置管理模块
├── 📁 scripts/                       # 部署和工具脚本
├── 📁 tests/                         # 测试文件
├── 📄 CLAUDE.md                      # 技术开发文档
├── 📄 README.md                      # 用户使用文档
└── 📄 stock_pool.db                  # SQLite数据库文件
```

### 🔧 后端架构 (backend/)
```python
backend/
├── main.py                           # FastAPI应用入口，50+API端点
│   ├── WebStockAnalysisBot           # 主业务逻辑类
│   ├── ConnectionManager             # WebSocket连接管理
│   ├── API路由定义                   # REST API端点
│   └── WebSocket处理                 # 实时通信
├── database.py                       # 数据访问层
│   ├── StockPool                     # 股票池数据模型
│   ├── StockInfo                     # 股票信息数据模型
│   ├── StrategyAnalysis              # 策略分析数据模型
│   ├── StockScreening                # 股票筛选数据模型
│   ├── DailyStockChange              # 每日股价变动数据模型
│   ├── DatabaseManager               # 数据库操作类
│   └── SQLite管理                    # 数据持久化
├── services/                         # 业务服务层
│   ├── strategy_service.py           # AI策略分析核心服务
│   ├── stock_screening_service.py    # 股票筛选算法服务
│   ├── akshare_service.py           # AkShare数据服务（原版）
│   ├── improved_akshare_service.py  # 优化AkShare数据服务
│   └── data_sync_scheduler.py       # 数据同步调度服务
├── requirements.txt                  # Python依赖
└── stock_pool.db                     # SQLite数据库文件
```

### ⚛️ 前端架构 (frontend/)
```typescript
frontend/
├── src/
│   ├── components/                           # React组件库
│   │   ├── StockPoolManager.tsx             # 股票池管理主界面
│   │   ├── StockPoolForm.tsx                # 股票添加/编辑表单
│   │   ├── StockScreeningDashboard.tsx      # 股票筛选控制面板
│   │   ├── ScreeningConfig.tsx              # 筛选条件配置组件
│   │   ├── ScreeningHistory.tsx             # 筛选历史记录组件
│   │   ├── StrategyAnalysisButton.tsx       # AI策略分析按钮
│   │   ├── StrategyModal.tsx                # 策略分析结果展示
│   │   ├── ChatInterface.tsx                # AI聊天界面
│   │   ├── PerformanceMonitor.tsx           # 性能监控组件
│   │   └── Pagination.tsx                   # 分页组件
│   ├── hooks/                               # 自定义React Hooks
│   │   ├── useStockPool.ts                  # 股票池数据管理
│   │   ├── useWebSocket.ts                  # WebSocket通信
│   │   └── useStockScreening.ts             # 股票筛选状态管理
│   ├── services/                            # 前端服务层
│   │   └── api.ts                           # HTTP API客户端
│   ├── types/                               # TypeScript类型定义
│   │   └── index.ts                         # 共享类型接口
│   ├── App.tsx                              # 主应用组件
│   ├── App.css                              # 全局样式
│   └── main.tsx                             # 应用入口点
├── package.json                             # 前端依赖配置
├── vite.config.ts                           # Vite构建配置
├── tsconfig.json                            # TypeScript配置
└── index.html                               # HTML入口文件
```

## 🛠️ 技术栈详解

### 🔙 后端技术栈

#### FastAPI框架核心
```python
# main.py - 核心应用结构
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="AI股票聊天助手",
    version="2.1.0",
    description="基于AI的智能股票投资分析平台"
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

#### 数据库设计完整架构
```python
# database.py - 完整数据模型
@dataclass
class StockPool:
    """股票池数据模型 - 支持持仓和潜在股票管理"""
    stock_code: str                      # 股票代码
    stock_name: str                      # 股票名称  
    pool_type: str                       # holding|potential
    shares: int = 0                      # 持股数量
    avg_cost: float = 0.0               # 平均成本
    current_price: float = 0.0          # 当前价格
    market_value: float = 0.0           # 市值
    tags: Optional[List[str]] = None    # 标签列表(JSON存储)
    notes: str = ""                     # 备注信息
    created_at: str = ""                # 创建时间
    updated_at: str = ""                # 更新时间
    id: Optional[int] = None            # 主键ID

@dataclass
class StrategyAnalysis:
    """AI策略分析数据模型"""
    stock_pool_id: int                  # 关联股票池ID
    stock_code: str                     # 股票代码
    comprehensive_score: float          # 综合评分(1-10)
    risk_level: str                     # 风险等级(low/medium/high)
    action_recommendation: str          # 操作建议(buy/hold/reduce/sell)
    target_price_min: float             # 目标价位下限
    target_price_max: float             # 目标价位上限
    analysis_summary: str               # 分析摘要
    technical_analysis: str             # 技术分析
    fundamental_analysis: str           # 基本面分析
    market_context: str                 # 市场环境
    key_metrics: str                    # 关键指标(JSON)
    risk_warnings: str                  # 风险提示(JSON)
    action_plan: str                    # 行动计划(JSON)
    analysis_date: str                  # 分析日期
    created_at: str                     # 创建时间
    id: Optional[int] = None            # 主键ID

@dataclass  
class StockScreening:
    """股票筛选结果数据模型"""
    stock_code: str                     # 股票代码
    stock_name: str                     # 股票名称
    market: str                         # 市场(SH/SZ/HK)
    screening_date: str                 # 筛选日期
    screening_type: str                 # 筛选类型
    criteria_met: str                   # 满足条件(JSON)
    consecutive_days: int               # 连续天数
    avg_rise_percent: float             # 平均涨幅
    total_volume: int                   # 总成交量
    avg_volume: int                     # 平均成交量
    created_at: str                     # 创建时间
    id: Optional[int] = None            # 主键ID
```

#### API端点设计架构
```python
# REST API路由 - 完整API设计
# 股票池管理API
@app.get("/api/stock-pools")                    # 获取股票池列表
@app.post("/api/stock-pools")                   # 创建股票
@app.get("/api/stock-pools/{id}")               # 获取单个股票
@app.put("/api/stock-pools/{id}")               # 更新股票
@app.delete("/api/stock-pools/{id}")            # 删除股票

# AI策略分析API
@app.post("/api/strategy/generate/{stock_pool_id}")    # 生成策略分析
@app.get("/api/strategy/history/{stock_pool_id}")     # 获取策略历史
@app.get("/api/strategy/{strategy_id}")               # 获取单个策略

# 股票筛选API
@app.post("/api/screening/manual-trigger")            # 手动触发筛选
@app.get("/api/screening/latest-results")             # 获取最新筛选结果
@app.post("/api/screening/init-historical-data")      # 初始化历史数据
@app.get("/api/screening/history")                    # 获取筛选历史

# 股票信息查询API
@app.get("/api/stocks/search")                        # 股票搜索
@app.get("/api/stocks/info/{symbol}")                 # 股票详情
@app.get("/api/stocks/realtime/{symbol}")             # 实时行情

# 数据源管理API
@app.get("/api/data-sources/status")                  # 数据源状态
@app.post("/api/data-sources/sync")                   # 手动同步

# 性能监控API
@app.get("/api/performance/stats")                    # 性能统计
@app.post("/api/performance/optimize")                # 性能优化

# WebSocket端点
@app.websocket("/ws")                                 # 实时聊天通信
```

### 🎨 前端技术栈

#### React组件架构设计
```typescript
// App.tsx - 主应用架构
const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  
  return (
    <div className="h-screen bg-gray-50 flex">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <MainContent>
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'pool' && <StockPoolManager />}
        {activeTab === 'screening' && <StockScreeningDashboard />}
        {activeTab === 'performance' && <PerformanceMonitor />}
      </MainContent>
    </div>
  );
};

// 组件通信架构
interface ComponentProps {
  onDataChange?: (data: any) => void;
  onError?: (error: string) => void;
  onSuccess?: (message: string) => void;
}
```

#### 状态管理架构
```typescript
// useStockPool.ts - 完整股票池状态管理
export const useStockPool = () => {
  const [stockPools, setStockPools] = useState<StockPool[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // CRUD操作
  const createStockPool = async (data: StockPoolCreate) => {
    setLoading(true);
    try {
      const newPool = await stockPoolAPI.create(data);
      setStockPools(prev => [...prev, newPool]);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const updateStockPool = async (id: number, data: StockPoolUpdate) => {
    setLoading(true);
    try {
      const updated = await stockPoolAPI.update(id, data);
      setStockPools(prev => prev.map(pool => 
        pool.id === id ? updated : pool
      ));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const deleteStockPool = async (id: number) => {
    setLoading(true);
    try {
      await stockPoolAPI.delete(id);
      setStockPools(prev => prev.filter(pool => pool.id !== id));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const refreshStockPools = async () => {
    setLoading(true);
    try {
      const pools = await stockPoolAPI.getAll();
      setStockPools(pools);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return { 
    stockPools, 
    loading, 
    error, 
    createStockPool, 
    updateStockPool, 
    deleteStockPool, 
    refreshStockPools 
  };
};
```

#### WebSocket通信架构
```typescript
// useWebSocket.ts - 实时通信管理
export const useWebSocket = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    setConnectionStatus('connecting');
    wsRef.current = new WebSocket(WS_URL);
    
    wsRef.current.onopen = () => {
      setConnectionStatus('connected');
    };
    
    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages(prev => [...prev, message]);
    };
    
    wsRef.current.onclose = () => {
      setConnectionStatus('disconnected');
      // 自动重连
      setTimeout(connect, 3000);
    };
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };
  }, []);
  
  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'query',
        content,
        timestamp: new Date().toISOString()
      };
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);
  
  return { messages, connectionStatus, sendMessage, connect };
};
```

## 🔄 核心业务流程

### 📊 股票池管理完整流程
```
用户操作 → 状态验证 → API调用 → 后端处理 → 数据库更新 → 响应返回 → UI更新 → 状态同步
    ↓
StockPoolManager.tsx (用户界面)
    ↓
useStockPool Hook (状态管理)
    ↓  
api.ts HTTP客户端 (网络层)
    ↓
FastAPI路由处理器 (业务逻辑)
    ↓
DatabaseManager (数据访问)
    ↓
SQLite数据库 (数据持久化)
    ↓
实时数据同步 (WebSocket通知)
```

### 💬 AI聊天完整流程
```
用户输入 → 消息验证 → WebSocket发送 → AI处理 → MCP调用 → 数据获取 → AI分析 → 流式响应
    ↓
ChatInterface.tsx (聊天界面)
    ↓
useWebSocket Hook (连接管理)
    ↓
WebSocket连接 (实时通信)
    ↓
FastAPI WebSocket处理器 (消息路由)
    ↓
WebStockAnalysisBot.process_query() (AI核心)
    ↓
MCP AkShare服务器 (数据获取)
    ↓
Qwen-Coder-Plus模型 (AI分析)
    ↓
流式响应返回 (实时展示)
```

### 🤖 AI策略分析完整流程
```
触发分析 → 数据收集 → 价格更新 → 指标计算 → AI策略生成 → 结果存储 → 策略展示 → 历史追踪
    ↓
StrategyAnalysisButton.tsx (触发按钮)
    ↓
strategyAPI.generateAnalysis() (API调用)
    ↓
POST /api/strategy/generate/{id} (后端接口)
    ↓
StrategyDataCollector.collect_comprehensive_data() (数据收集)
    ↓ (并发收集多维度数据)
├── 技术指标获取 (RSI, MACD, BOLL)
├── 基本面数据 (PE, PB, ROE)
├── 市场环境分析 (大盘走势, 板块表现)
├── 实时价格更新 (最新股价, 成交量)
└── 历史价格趋势 (30天历史数据)
    ↓
AIStrategyGenerator.generate_strategy() (AI策略引擎)
    ↓
OpenAI Compatible API调用 (Qwen-Coder-Plus)
    ↓
结构化策略结果解析 (JSON格式)
    ↓
数据库存储 (strategy_analysis表)
    ↓
StrategyModal.tsx 全屏展示 (策略结果)
    ↓
历史策略对比和追踪
```

### 🔍 股票筛选完整流程
```
条件设置 → 数据收集 → 筛选算法 → 结果过滤 → 数据存储 → 界面展示 → 历史管理
    ↓
ScreeningConfig.tsx (条件配置)
    ↓
StockScreeningDashboard.tsx (控制面板)
    ↓
POST /api/screening/manual-trigger (触发API)
    ↓
数据同步调度器 (获取最新数据)
    ↓
StockScreeningService.screen_strong_rise_stocks() (筛选算法)
    ↓ (多线程并发处理)
├── 每日涨跌数据分析
├── 连续涨幅计算
├── 成交量分析
├── 市场过滤器应用
└── 自定义条件匹配
    ↓
筛选结果排序和去重
    ↓
数据库存储 (stock_screening表)
    ↓
GET /api/screening/latest-results (结果获取)
    ↓
前端表格展示和分页
    ↓
ScreeningHistory.tsx (历史记录)
```

## 🤖 AI策略分析系统深度解析

### 💡 系统架构设计
AI策略分析是本项目的核心创新功能，采用模块化设计，实现了数据收集、AI分析、结果展示的完整闭环。

#### ✨ 技术特性
- **🔄 实时数据融合**：策略生成前自动获取最新股价和技术指标
- **📊 多维度分析引擎**：技术面、基本面、市场环境立体分析
- **🧠 AI驱动决策**：基于Qwen-Coder-Plus模型的智能策略生成
- **📈 量化评估体系**：1-10分综合评分，多级风险评估
- **⚠️ 风险控制**：动态风险等级评估和预警机制
- **📋 可执行建议**：具体的操作建议和行动计划
- **📅 历史策略追踪**：完整的策略分析历史记录和对比

#### 🔧 技术实现架构

**数据收集层** (`StrategyDataCollector`)
```python
class StrategyDataCollector:
    """策略数据收集器 - 多源数据并发收集"""
    
    async def collect_comprehensive_data(self, stock_code: str, stock_name: str) -> Dict:
        """并发收集多维度数据"""
        tasks = [
            self.get_technical_indicators(stock_code),    # 技术指标
            self.get_fundamental_data(stock_code),        # 基本面数据
            self.get_market_context(stock_code),          # 市场环境
            self.get_price_history(stock_code, days=30),  # 价格历史
            self.get_news_sentiment(stock_code),          # 新闻情感
            self.get_industry_comparison(stock_code)      # 行业对比
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'technical_indicators': results[0],
            'fundamental_data': results[1], 
            'market_context': results[2],
            'price_history': results[3],
            'news_sentiment': results[4],
            'industry_comparison': results[5],
            'collection_timestamp': datetime.now().isoformat()
        }
    
    async def get_technical_indicators(self, stock_code: str) -> Dict:
        """获取技术指标数据"""
        try:
            # 获取历史数据用于计算技术指标
            hist_data = await self.akshare_service.get_stock_history(
                stock_code, period=30
            )
            
            if hist_data is None or hist_data.empty:
                return self._get_simulated_technical_data()
            
            # 计算技术指标
            indicators = {
                'rsi': self._calculate_rsi(hist_data),
                'macd': self._calculate_macd(hist_data),
                'bollinger_bands': self._calculate_bollinger(hist_data),
                'moving_averages': self._calculate_ma(hist_data),
                'volume_analysis': self._analyze_volume(hist_data)
            }
            
            return indicators
            
        except Exception as e:
            logger.warning(f"技术指标获取失败，使用模拟数据: {e}")
            return self._get_simulated_technical_data()
```

**AI策略生成层** (`AIStrategyGenerator`)
```python
class AIStrategyGenerator:
    """AI策略生成引擎"""
    
    def __init__(self, openai_client):
        self.client = openai_client
        self.model = "qwen-coder-plus"
    
    async def generate_strategy(self, 
                               stock_data: Dict, 
                               holding_info: Dict) -> StrategyAnalysis:
        """生成投资策略"""
        
        # 构建结构化提示
        prompt = self._build_strategy_prompt(stock_data, holding_info)
        
        try:
            # 调用AI模型生成策略
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,  # 降低随机性，提高分析一致性
                response_format={"type": "json_object"}
            )
            
            # 解析AI响应
            strategy_json = json.loads(response.choices[0].message.content)
            
            # 构建策略分析对象
            strategy = StrategyAnalysis(
                stock_pool_id=holding_info['stock_pool_id'],
                stock_code=stock_data['stock_code'],
                comprehensive_score=strategy_json['comprehensive_score'],
                risk_level=strategy_json['risk_level'],
                action_recommendation=strategy_json['action_recommendation'],
                target_price_min=strategy_json['target_price_min'],
                target_price_max=strategy_json['target_price_max'],
                analysis_summary=strategy_json['analysis_summary'],
                technical_analysis=strategy_json['technical_analysis'],
                fundamental_analysis=strategy_json['fundamental_analysis'],
                market_context=strategy_json['market_context'],
                key_metrics=json.dumps(strategy_json['key_metrics']),
                risk_warnings=json.dumps(strategy_json['risk_warnings']),
                action_plan=json.dumps(strategy_json['action_plan']),
                analysis_date=datetime.now().isoformat()
            )
            
            return strategy
            
        except Exception as e:
            logger.error(f"AI策略生成失败: {e}")
            return self._generate_fallback_strategy(stock_data, holding_info)
    
    def _build_strategy_prompt(self, stock_data: Dict, holding_info: Dict) -> str:
        """构建策略分析提示词"""
        return f"""
# 投资策略分析请求

## 股票基本信息
- 股票代码: {stock_data['stock_code']}
- 股票名称: {stock_data['stock_name']}
- 当前价格: ¥{stock_data['current_price']}

## 持仓情况
- 持股数量: {holding_info['shares']}股
- 平均成本: ¥{holding_info['avg_cost']}
- 当前市值: ¥{holding_info['market_value']}
- 盈亏状况: {holding_info['profit_loss_percent']:.2f}%

## 技术分析数据
{self._format_technical_data(stock_data['technical_indicators'])}

## 基本面数据  
{self._format_fundamental_data(stock_data['fundamental_data'])}

## 市场环境
{self._format_market_context(stock_data['market_context'])}

请基于以上信息，生成一份详细的投资策略分析报告。

## 输出要求
请以JSON格式返回分析结果，包含以下字段：
{{
  "comprehensive_score": float,      // 综合评分(1-10)
  "risk_level": string,             // 风险等级("low"/"medium"/"high")
  "action_recommendation": string,   // 操作建议("buy"/"hold"/"reduce"/"sell")
  "target_price_min": float,        // 目标价位下限
  "target_price_max": float,        // 目标价位上限
  "analysis_summary": string,       // 分析摘要
  "technical_analysis": string,     // 技术分析
  "fundamental_analysis": string,   // 基本面分析
  "market_context": string,         // 市场环境分析
  "key_metrics": [                  // 关键指标
    {{"metric": "指标名", "value": "指标值", "comment": "说明"}}
  ],
  "risk_warnings": [               // 风险提示
    "风险点1", "风险点2"
  ],
  "action_plan": [                 // 行动计划
    "具体建议1", "具体建议2"
  ]
}}
"""
```

**前端展示层** (`StrategyModal`)
```typescript
// StrategyModal.tsx - 策略展示组件
interface StrategyModalProps {
  strategy: StrategyAnalysis;
  onClose: () => void;
  onViewHistory: () => void;
}

const StrategyModal: React.FC<StrategyModalProps> = ({ 
  strategy, 
  onClose, 
  onViewHistory 
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'technical' | 'fundamental' | 'plan'>('overview');
  
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };
  
  const getActionColor = (action: string) => {
    switch (action) {
      case 'buy': return 'text-green-600 bg-green-100';
      case 'hold': return 'text-blue-600 bg-blue-100';
      case 'reduce': return 'text-orange-600 bg-orange-100';
      case 'sell': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              AI投资策略分析 - {strategy.stock_code}
            </h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={onViewHistory}
                className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
              >
                查看历史策略
              </button>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
        
        {/* 核心指标卡片 */}
        <div className="px-6 py-4 bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {strategy.comprehensive_score}/10
              </div>
              <div className="text-sm text-gray-600">综合评分</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center">
              <div className={`inline-block px-2 py-1 rounded text-sm font-medium ${getRiskColor(strategy.risk_level)}`}>
                {strategy.risk_level === 'low' ? '低风险' : 
                 strategy.risk_level === 'medium' ? '中风险' : '高风险'}
              </div>
              <div className="text-sm text-gray-600 mt-1">风险等级</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center">
              <div className={`inline-block px-2 py-1 rounded text-sm font-medium ${getActionColor(strategy.action_recommendation)}`}>
                {strategy.action_recommendation === 'buy' ? '买入' :
                 strategy.action_recommendation === 'hold' ? '持有' :
                 strategy.action_recommendation === 'reduce' ? '减仓' : '卖出'}
              </div>
              <div className="text-sm text-gray-600 mt-1">操作建议</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center">
              <div className="text-lg font-semibold text-gray-900">
                ¥{strategy.target_price_min} - ¥{strategy.target_price_max}
              </div>
              <div className="text-sm text-gray-600">目标价位</div>
            </div>
          </div>
        </div>
        
        {/* 标签页导航 */}
        <div className="px-6 border-b border-gray-200">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', label: '分析概要' },
              { id: 'technical', label: '技术分析' },
              { id: 'fundamental', label: '基本面分析' },
              { id: 'plan', label: '行动计划' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        
        {/* 内容区域 */}
        <div className="px-6 py-4 max-h-96 overflow-y-auto">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div>
                <h3 className="font-medium text-gray-900 mb-2">策略摘要</h3>
                <p className="text-gray-700 whitespace-pre-line">
                  {strategy.analysis_summary}
                </p>
              </div>
              
              <div>
                <h3 className="font-medium text-gray-900 mb-2">关键指标</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {strategy.key_metrics && JSON.parse(strategy.key_metrics).map((metric: any, index: number) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-gray-900">
                          {metric.metric}
                        </span>
                        <span className="text-sm text-blue-600 font-medium">
                          {metric.value}
                        </span>
                      </div>
                      {metric.comment && (
                        <p className="text-xs text-gray-600 mt-1">
                          {metric.comment}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h3 className="font-medium text-gray-900 mb-2">风险提示</h3>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <ul className="text-sm text-red-700 space-y-1">
                    {strategy.risk_warnings && JSON.parse(strategy.risk_warnings).map((warning: string, index: number) => (
                      <li key={index} className="flex items-start">
                        <span className="text-red-500 mr-2">•</span>
                        {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'technical' && (
            <div>
              <h3 className="font-medium text-gray-900 mb-3">技术分析详情</h3>
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-line text-gray-700">
                  {strategy.technical_analysis}
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'fundamental' && (
            <div>
              <h3 className="font-medium text-gray-900 mb-3">基本面分析详情</h3>
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-line text-gray-700">
                  {strategy.fundamental_analysis}
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'plan' && (
            <div>
              <h3 className="font-medium text-gray-900 mb-3">具体行动计划</h3>
              <div className="space-y-3">
                {strategy.action_plan && JSON.parse(strategy.action_plan).map((action: string, index: number) => (
                  <div key={index} className="flex items-start p-3 bg-blue-50 rounded-lg">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">
                      {index + 1}
                    </div>
                    <div className="text-sm text-gray-700">
                      {action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* 底部信息 */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <div className="flex justify-between items-center text-sm text-gray-600">
            <span>分析时间: {new Date(strategy.analysis_date).toLocaleString()}</span>
            <span>AI模型: Qwen-Coder-Plus</span>
          </div>
        </div>
      </div>
    </div>
  );
};
```

#### 🎯 应用场景和价值
1. **投资决策支持**：为持仓股票提供AI驱动的专业投资建议
2. **风险管理**：动态评估投资风险，提供预警和控制建议  
3. **策略优化**：基于多维数据分析优化投资策略
4. **学习参考**：通过AI分析学习专业的投资分析方法
5. **历史复盘**：策略历史记录支持投资决策复盘和改进

## 🔍 股票筛选系统深度解析

### 💡 系统设计理念
股票筛选系统采用多维度量化分析，通过算法识别市场中的投资机会，支持自定义筛选条件和实时执行。

#### ✨ 核心特性
- **🔄 实时数据驱动**：基于最新市场数据进行筛选分析
- **📊 多维度筛选**：连续涨幅、成交量、市场分类等多重条件
- **🧠 算法优化**：高效的数据处理和筛选算法
- **📈 历史回测**：支持历史数据回填和策略验证
- **⚡ 并发处理**：多线程并发处理提升性能
- **📋 结果管理**：筛选结果的存储、查询和历史追踪

#### 🔧 技术实现深度

**筛选算法核心** (`StockScreeningService`)
```python
class StockScreeningService:
    """股票筛选服务 - 核心算法实现"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.akshare_service = AkShareService()
        
    async def screen_strong_rise_stocks(self, criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """筛选强势上涨股票"""
        logger.info(f"🔍 开始筛选强势股票 - 条件: {criteria.to_dict()}")
        
        # 获取股票基础列表
        stock_list = await self._get_stock_universe(criteria.market_filter)
        
        # 并发筛选处理
        screening_tasks = []
        batch_size = 50  # 批量处理大小
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            task = self._screen_stock_batch(batch, criteria)
            screening_tasks.append(task)
        
        # 执行并发筛选
        batch_results = await asyncio.gather(*screening_tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        for result in batch_results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"批量筛选失败: {result}")
        
        # 排序和去重
        filtered_results = self._filter_and_sort_results(all_results, criteria)
        
        # 保存筛选结果
        screening_date = datetime.now().strftime('%Y-%m-%d')
        await self._save_screening_results(filtered_results, criteria, screening_date)
        
        logger.info(f"✅ 筛选完成，找到 {len(filtered_results)} 只符合条件的强势股票")
        
        return filtered_results
    
    async def _screen_stock_batch(self, stock_batch: List[Dict], criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """批量筛选股票"""
        results = []
        
        for stock in stock_batch:
            try:
                # 获取股票历史数据
                hist_data = await self._get_stock_history_data(
                    stock['stock_code'], 
                    days=criteria.min_consecutive_days + 5
                )
                
                if hist_data is None or len(hist_data) < criteria.min_consecutive_days:
                    continue
                
                # 分析连续涨幅
                rise_analysis = self._analyze_consecutive_rises(hist_data, criteria)
                
                if rise_analysis['is_qualified']:
                    # 创建筛选结果
                    result = ScreeningResult(
                        stock_code=stock['stock_code'],
                        stock_name=stock['stock_name'],
                        market=stock['market'],
                        consecutive_days=rise_analysis['consecutive_days'],
                        avg_rise_percent=rise_analysis['avg_rise_percent'],
                        total_volume=rise_analysis['total_volume'],
                        avg_volume=rise_analysis['avg_volume'],
                        daily_changes=rise_analysis['daily_changes']
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"筛选股票 {stock['stock_code']} 失败: {e}")
                continue
        
        return results
    
    def _analyze_consecutive_rises(self, hist_data: List[Dict], criteria: ScreeningCriteria) -> Dict:
        """分析连续涨幅"""
        if len(hist_data) < criteria.min_consecutive_days:
            return {'is_qualified': False}
        
        # 按日期排序（最新的在前）
        sorted_data = sorted(hist_data, key=lambda x: x['trade_date'], reverse=True)
        
        consecutive_rises = []
        total_volume = 0
        
        # 分析最近N天的连续涨幅
        for i in range(criteria.min_consecutive_days):
            day_data = sorted_data[i]
            
            if day_data['change_percent'] <= 0:
                # 如果有任何一天不是上涨，则不符合条件
                return {'is_qualified': False}
            
            consecutive_rises.append({
                'date': day_data['trade_date'],
                'change_percent': day_data['change_percent'],
                'volume': day_data['volume'],
                'close_price': day_data['close_price']
            })
            
            total_volume += day_data['volume']
        
        # 计算平均涨幅
        avg_rise_percent = sum(day['change_percent'] for day in consecutive_rises) / len(consecutive_rises)
        avg_volume = total_volume // len(consecutive_rises)
        
        # 检查是否满足筛选条件
        is_qualified = (
            avg_rise_percent >= criteria.min_rise_percent and
            avg_volume >= criteria.min_volume
        )
        
        return {
            'is_qualified': is_qualified,
            'consecutive_days': len(consecutive_rises),
            'avg_rise_percent': round(avg_rise_percent, 2),
            'total_volume': total_volume,
            'avg_volume': avg_volume,
            'daily_changes': consecutive_rises
        }
    
    def _filter_and_sort_results(self, results: List[ScreeningResult], criteria: ScreeningCriteria) -> List[ScreeningResult]:
        """过滤和排序结果"""
        # 去重（基于股票代码）
        unique_results = {}
        for result in results:
            if result.stock_code not in unique_results:
                unique_results[result.stock_code] = result
            else:
                # 如果有重复，保留涨幅更高的
                if result.avg_rise_percent > unique_results[result.stock_code].avg_rise_percent:
                    unique_results[result.stock_code] = result
        
        # 转换为列表
        filtered_results = list(unique_results.values())
        
        # 按平均涨幅降序排序
        filtered_results.sort(key=lambda x: x.avg_rise_percent, reverse=True)
        
        return filtered_results
    
    async def _save_screening_results(self, results: List[ScreeningResult], criteria: ScreeningCriteria, screening_date: str):
        """保存筛选结果（改进版 - 替换当天旧结果）"""
        import sqlite3
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # 先删除当天同类型的旧结果
                cursor.execute('''
                    DELETE FROM stock_screening 
                    WHERE screening_date = ? AND screening_type = ?
                ''', (screening_date, criteria.screening_type))
                
                deleted_count = cursor.rowcount
                logger.info(f"🗑️ 清理了 {deleted_count} 条当天旧的筛选结果")
                
                # 插入新的筛选结果
                for result in results:
                    cursor.execute('''
                        INSERT INTO stock_screening
                        (stock_code, stock_name, market, screening_date, screening_type,
                         criteria_met, consecutive_days, avg_rise_percent, total_volume, 
                         avg_volume, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.stock_code,
                        result.stock_name,
                        result.market,
                        screening_date,
                        criteria.screening_type,
                        json.dumps(criteria.to_dict()),
                        result.consecutive_days,
                        result.avg_rise_percent,
                        result.total_volume,
                        result.avg_volume,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                logger.info(f"💾 保存了 {len(results)} 条筛选结果")
                
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")
```

**前端筛选控制面板** (`StockScreeningDashboard`)
```typescript
// StockScreeningDashboard.tsx - 筛选控制面板
const StockScreeningDashboard: React.FC = () => {
  const [criteria, setCriteria] = useState<ScreeningCriteria>({
    screening_type: 'strong_rise_3d',
    min_consecutive_days: 3,
    min_rise_percent: 9.0,
    min_volume: 0,
    market_filter: ['SH', 'SZ']
  });
  
  const [latestResults, setLatestResults] = useState<ScreeningResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [manualTriggerLoading, setManualTriggerLoading] = useState(false);
  const [message, setMessage] = useState<string>('');
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // 获取最新筛选结果
  const fetchLatestResults = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/screening/latest-results?screening_type=${criteria.screening_type}&limit=200`
      );
      const data = await response.json();
      
      if (data.success) {
        setLatestResults(data.data);
        setMessage(data.message);
      } else {
        setMessage('获取筛选结果失败');
      }
    } catch (error) {
      console.error('获取筛选结果失败:', error);
      setMessage('获取筛选结果失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 手动触发筛选
  const handleManualTrigger = async () => {
    setManualTriggerLoading(true);
    try {
      const response = await fetch('/api/screening/manual-trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(criteria)
      });
      const data = await response.json();
      
      if (data.success) {
        setMessage('筛选任务执行完成，正在刷新结果...');
        // 立即刷新一次，然后等待5秒后再次刷新确保数据同步
        fetchLatestResults();
        setTimeout(() => {
          fetchLatestResults();
        }, 5000);
      } else {
        setMessage('手动触发筛选失败');
      }
    } catch (error) {
      console.error('手动触发筛选失败:', error);
      setMessage('手动触发筛选失败');
    } finally {
      setManualTriggerLoading(false);
    }
  };
  
  // 分页数据
  const paginatedResults = useMemo(() => {
    if (!latestResults?.results) return [];
    const startIndex = (currentPage - 1) * pageSize;
    return latestResults.results.slice(startIndex, startIndex + pageSize);
  }, [latestResults, currentPage, pageSize]);
  
  const totalPages = useMemo(() => {
    if (!latestResults?.results) return 0;
    return Math.ceil(latestResults.results.length / pageSize);
  }, [latestResults, pageSize]);
  
  // 组件挂载时获取数据
  useEffect(() => {
    fetchLatestResults();
  }, []);
  
  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 头部 */}
      <div className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <TrendingUp className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-semibold text-gray-900">股票筛选</h1>
            <span className="text-sm text-gray-500">智能筛选强势上涨股票</span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={fetchLatestResults}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>刷新结果</span>
            </button>
            <button
              onClick={handleManualTrigger}
              disabled={manualTriggerLoading}
              className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <Play className={`w-4 h-4 ${manualTriggerLoading ? 'animate-pulse' : ''}`} />
              <span>{manualTriggerLoading ? '筛选中...' : '手动筛选'}</span>
            </button>
          </div>
        </div>
      </div>
      
      {/* 筛选条件 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <Filter className="w-5 h-5 mr-2" />
          筛选条件
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              连续天数
            </label>
            <select
              value={criteria.min_consecutive_days}
              onChange={(e) => setCriteria(prev => ({
                ...prev,
                min_consecutive_days: parseInt(e.target.value)
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={4}>4</option>
              <option value={5}>5</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              最小涨幅 (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={criteria.min_rise_percent}
              onChange={(e) => setCriteria(prev => ({
                ...prev,
                min_rise_percent: parseFloat(e.target.value)
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              市场选择
            </label>
            <select
              value={criteria.market_filter[0] || 'A股 (沪深)'}
              onChange={(e) => {
                const value = e.target.value;
                const marketFilter = value === 'A股 (沪深)' ? ['SH', 'SZ'] : 
                                   value === 'SH' ? ['SH'] : 
                                   value === 'SZ' ? ['SZ'] : ['SH', 'SZ'];
                setCriteria(prev => ({ ...prev, market_filter: marketFilter }));
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="A股 (沪深)">A股 (沪深)</option>
              <option value="SH">上海证券交易所</option>
              <option value="SZ">深圳证券交易所</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleManualTrigger}
              disabled={manualTriggerLoading}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              <Filter className="w-4 h-4" />
              <span>自定义筛选</span>
            </button>
          </div>
        </div>
      </div>
      
      {/* 消息提示 */}
      {message && (
        <div className="mx-6 mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center text-blue-800">
            <Info className="w-4 h-4 mr-2" />
            <span className="text-sm">{message}</span>
          </div>
        </div>
      )}
      
      {/* 筛选结果 */}
      <div className="flex-1 overflow-hidden">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900 flex items-center">
              <TrendingUp className="w-5 h-5 mr-2 text-red-500" />
              筛选结果
              {latestResults && (
                <span className="ml-2 text-sm text-gray-500">
                  {latestResults.screening_date}
                </span>
              )}
            </h2>
            
            {latestResults?.results && (
              <div className="text-sm text-gray-600">
                显示第 {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, latestResults.results.length)} 条，
                共 {latestResults.results.length} 条
              </div>
            )}
          </div>
          
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">加载中...</span>
            </div>
          ) : latestResults?.results && latestResults.results.length > 0 ? (
            <>
              {/* 结果表格 */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票代码
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        市场
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        连续天数
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        平均涨幅
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        平均成交量
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {paginatedResults.map((result, index) => (
                      <tr key={result.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-blue-600">
                            {result.stock_code}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {result.stock_name}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            result.market === 'SH' ? 'bg-red-100 text-red-800' : 
                            result.market === 'SZ' ? 'bg-green-100 text-green-800' : 
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {result.market}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {result.consecutive_days}天
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-red-600">
                            +{result.avg_rise_percent}%
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {(result.avg_volume / 10000).toFixed(2)}万
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* 分页组件 */}
              {totalPages > 1 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              )}
              
              {/* 统计信息 */}
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="text-sm text-blue-800">
                  <strong>共找到 {latestResults.results.length} 只符合条件的股票</strong>
                  <span className="ml-4">
                    筛选条件: 连续 {criteria.min_consecutive_days} 天涨幅超过 {criteria.min_rise_percent}%
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <TrendingUp className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">暂无筛选结果</h3>
              <p className="mt-1 text-sm text-gray-500">
                点击"手动筛选"按钮开始筛选股票
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

## ⏰ 数据同步调度系统

### 🔧 调度器架构设计
```python
# data_sync_scheduler.py - 数据同步调度核心
class DataSyncScheduler:
    """数据同步调度器 - 智能调度和错误恢复"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.stock_screening_service = None
        self.scheduler = None
        self.is_running = False
        
    async def start(self):
        """启动调度器"""
        if self.is_running:
            return
            
        logger.info("🚀 启动数据同步调度器...")
        
        self.scheduler = AsyncIOScheduler()
        
        # 每日数据收集 - 每天早上9点执行
        self.scheduler.add_job(
            self.daily_data_collection,
            CronTrigger(hour=9, minute=0),
            id='daily_data_collection',
            max_instances=1,
            coalesce=True
        )
        
        # 股票筛选 - 每天下午3点半执行
        self.scheduler.add_job(
            self.daily_stock_screening,
            CronTrigger(hour=15, minute=30),
            id='daily_stock_screening',
            max_instances=1,
            coalesce=True
        )
        
        # 数据源健康检查 - 每小时执行
        self.scheduler.add_job(
            self.health_check,
            CronTrigger(minute=0),
            id='health_check',
            max_instances=1
        )
        
        # 每周全量数据更新 - 每周日早上8点
        self.scheduler.add_job(
            self.weekly_full_sync,
            CronTrigger(day_of_week=6, hour=8, minute=0),
            id='weekly_full_sync',
            max_instances=1,
            coalesce=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info("📅 定时任务设置完成")
        logger.info("✅ 数据同步调度器启动成功")
    
    async def daily_data_collection(self):
        """每日数据收集任务"""
        logger.info("📊 开始每日数据收集...")
        
        try:
            # 检查是否为交易日
            if not self._is_trading_day():
                logger.info("⏸️ 今日非交易日，跳过数据收集")
                return SyncResult(True, "非交易日，跳过数据收集", 0)
            
            collected_count = 0
            
            # 获取股票列表
            stock_list = await self._get_active_stocks()
            
            # 批量收集数据
            batch_size = 100
            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i + batch_size]
                count = await self._collect_batch_data(batch)
                collected_count += count
                
                # 避免API限制，批次间暂停
                await asyncio.sleep(1)
            
            logger.info(f"✅ 每日数据收集完成，共收集 {collected_count} 条记录")
            
            return SyncResult(True, f"每日数据收集完成，共收集 {collected_count} 条记录", collected_count)
            
        except Exception as e:
            logger.error(f"❌ 每日数据收集失败: {e}")
            return SyncResult(False, f"数据收集失败: {str(e)}", 0)
    
    async def daily_stock_screening(self):
        """每日股票筛选任务"""
        logger.info("🔍 开始每日股票筛选...")
        
        try:
            if not self._is_trading_day():
                logger.info("⏸️ 今日非交易日，跳过股票筛选")
                return SyncResult(True, "非交易日，跳过股票筛选", 0)
            
            # 初始化筛选服务
            if not self.stock_screening_service:
                from services.stock_screening_service import StockScreeningService
                self.stock_screening_service = StockScreeningService(self.db_manager)
            
            # 使用默认筛选条件
            criteria = ScreeningCriteria(
                screening_type="strong_rise_3d",
                min_consecutive_days=3,
                min_rise_percent=7.0,
                min_volume=0,
                market_filter=['SH', 'SZ']
            )
            
            # 执行筛选
            results = await self.stock_screening_service.screen_strong_rise_stocks(criteria)
            
            logger.info(f"✅ 每日股票筛选完成，找到 {len(results)} 只符合条件的股票")
            
            return SyncResult(True, f"股票筛选完成，找到 {len(results)} 只股票", len(results))
            
        except Exception as e:
            logger.error(f"❌ 每日股票筛选失败: {e}")
            return SyncResult(False, f"股票筛选失败: {str(e)}", 0)
    
    def _is_trading_day(self) -> bool:
        """判断是否为交易日"""
        from datetime import datetime
        
        now = datetime.now()
        
        # 简单判断：周一到周五为交易日
        # 生产环境中应该考虑节假日
        weekday = now.weekday()
        return 0 <= weekday <= 4  # 0=周一, 4=周五
    
    async def manual_sync(self, sync_type: str) -> SyncResult:
        """手动触发同步任务"""
        logger.info(f"🔧 手动触发同步任务: {sync_type}")
        
        try:
            if sync_type == 'daily_data_collection':
                return await self.daily_data_collection()
            elif sync_type == 'strong_rise_screening':
                return await self.daily_stock_screening()
            elif sync_type == 'health_check':
                return await self.health_check()
            elif sync_type == 'weekly_full_sync':
                return await self.weekly_full_sync()
            else:
                return SyncResult(False, f"未知的同步类型: {sync_type}", 0)
                
        except Exception as e:
            logger.error(f"❌ 手动同步失败: {e}")
            return SyncResult(False, f"同步失败: {str(e)}", 0)
```

## 📊 性能监控系统

### 🔧 性能监控架构
```typescript
// PerformanceMonitor.tsx - 性能监控组件
const PerformanceMonitor: React.FC = () => {
  const [performanceData, setPerformanceData] = useState<PerformanceStats | null>(null);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  
  const fetchPerformanceStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/performance/stats');
      const data = await response.json();
      
      if (data.success) {
        setPerformanceData(data.data);
      }
    } catch (error) {
      console.error('获取性能数据失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const runOptimization = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/performance/optimize', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        setOptimizationResults(data.data);
        // 优化后重新获取性能数据
        await fetchPerformanceStats();
      }
    } catch (error) {
      console.error('性能优化失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">性能监控</h1>
        <div className="flex space-x-3">
          <button
            onClick={fetchPerformanceStats}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>刷新数据</span>
          </button>
          <button
            onClick={runOptimization}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            <Zap className="w-4 h-4" />
            <span>执行优化</span>
          </button>
        </div>
      </div>
      
      {performanceData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Clock className="w-8 h-8 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">平均响应时间</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {performanceData.avg_response_time}ms
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Database className="w-8 h-8 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">数据库查询</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {performanceData.db_query_count}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Activity className="w-8 h-8 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">CPU使用率</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {performanceData.cpu_usage}%
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <HardDrive className="w-8 h-8 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">内存使用</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {performanceData.memory_usage}MB
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* 更多性能监控内容... */}
    </div>
  );
};
```

## 🛠️ 开发工作流和最佳实践

### 🚀 开发环境搭建
```bash
# 1. 环境准备
git clone <repository>
cd "Claude made stock bot"

# 2. 后端依赖安装
pip install -r requirements.txt

# 3. 前端依赖安装  
npm install

# 4. 一键启动开发环境
npm run dev
```

### 📝 代码规范和最佳实践

#### Python后端规范
```python
# 遵循PEP 8规范，使用类型注解
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ApiResponse:
    """标准API响应格式"""
    success: bool
    data: Optional[Union[Dict, List]] = None
    message: str = ""
    
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
        # 数据验证
        if not stock_data.stock_code:
            raise ValueError("股票代码不能为空")
        
        # 业务逻辑处理
        result = await service.create_stock_pool(stock_data)
        
        return ApiResponse(
            success=True,
            data=result,
            message="股票池创建成功"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建股票池失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

#### TypeScript前端规范
```typescript
// 使用严格类型检查和函数式组件
interface StockPoolManagerProps {
  onStockPoolChange?: (pools: StockPool[]) => void;
  onError?: (error: string) => void;
}

const StockPoolManager: React.FC<StockPoolManagerProps> = ({ 
  onStockPoolChange, 
  onError 
}) => {
  // 状态管理
  const { stockPools, loading, error, createStockPool } = useStockPool();
  
  // 副作用处理
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);
  
  useEffect(() => {
    if (onStockPoolChange) {
      onStockPoolChange(stockPools);
    }
  }, [stockPools, onStockPoolChange]);
  
  // 事件处理函数
  const handleCreate = useCallback(async (data: StockPoolCreateRequest) => {
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
  
  return (
    <div className="space-y-4">
      {/* 组件内容 */}
    </div>
  );
};

export default React.memo(StockPoolManager);
```

### 🧪 测试策略

#### 后端单元测试
```python
# tests/test_stock_pool.py
import pytest
from backend.database import DatabaseManager, StockPool

@pytest.fixture
def db_manager():
    """测试数据库管理器"""
    return DatabaseManager(":memory:")

@pytest.fixture
def sample_stock_pool():
    """示例股票池数据"""
    return StockPool(
        stock_code="000001",
        stock_name="平安银行", 
        pool_type="holding",
        shares=1000,
        avg_cost=12.50,
        current_price=13.20
    )

async def test_create_stock_pool(db_manager, sample_stock_pool):
    """测试创建股票池"""
    stock_id = await db_manager.add_stock_pool(sample_stock_pool)
    assert stock_id is not None
    
    # 验证数据已保存
    saved_stock = await db_manager.get_stock_pool(stock_id)
    assert saved_stock.stock_code == "000001"
    assert saved_stock.stock_name == "平安银行"

async def test_update_stock_pool(db_manager, sample_stock_pool):
    """测试更新股票池"""
    stock_id = await db_manager.add_stock_pool(sample_stock_pool)
    
    # 更新数据
    sample_stock_pool.current_price = 14.00
    await db_manager.update_stock_pool(stock_id, sample_stock_pool)
    
    # 验证更新
    updated_stock = await db_manager.get_stock_pool(stock_id)
    assert updated_stock.current_price == 14.00
```

#### 前端组件测试
```typescript
// tests/StockPoolManager.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import StockPoolManager from '../components/StockPoolManager';

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
    fireEvent.change(screen.getByLabelText('股票名称'), {
      target: { value: '平安银行' }
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

### 📦 部署和运维

#### 生产环境部署
```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 生产环境启动后端
cd backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --access-logfile - \
  --error-logfile -

# 3. Nginx配置
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket代理
    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### Docker部署配置
```dockerfile
# 多阶段构建Dockerfile
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ .
RUN npm run build

FROM python:3.9-slim AS backend
WORKDIR /app

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建结果
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# 创建非root用户
RUN useradd -m -u 1000 stockbot
USER stockbot

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 🔧 性能优化建议

#### 后端优化
- **数据库连接池**：使用连接池管理数据库连接
- **异步处理**：充分利用FastAPI的异步特性
- **缓存策略**：对频繁查询的数据使用Redis缓存
- **API限流**：防止API滥用和过载

#### 前端优化
- **代码分割**：使用动态import进行路由级代码分割
- **虚拟滚动**：处理大量数据列表时使用虚拟滚动
- **防抖节流**：搜索和API调用使用防抖处理
- **缓存优化**：合理使用浏览器缓存和应用缓存

### 🔐 安全最佳实践

#### 数据安全
- **输入验证**：所有用户输入必须验证和清理
- **SQL注入防护**：使用参数化查询
- **XSS防护**：前端输出转义和CSP策略
- **CSRF防护**：使用CSRF token保护

#### API安全
- **身份认证**：JWT token认证机制
- **权限控制**：基于角色的访问控制
- **HTTPS加密**：生产环境强制HTTPS
- **API密钥管理**：安全存储和轮换API密钥

## ✅ 当前项目状态

### 🎯 v2.1.0 完成功能清单

#### ✅ 核心基础功能
- **React前端架构**：基于React 18的现代化前端应用
- **FastAPI后端服务**：高性能异步Web服务框架
- **SQLite数据库**：轻量级数据持久化解决方案
- **WebSocket实时通信**：AI聊天和实时数据更新
- **响应式UI设计**：完美适配桌面和移动设备

#### ✅ AI智能分析功能
- **AI投资策略生成系统**：基于Qwen-Coder-Plus的智能策略分析
- **实时数据融合**：策略分析前自动获取最新价格和指标
- **多维度评估体系**：综合评分、风险等级、操作建议
- **策略历史追踪**：完整的策略分析历史记录和对比
- **智能聊天助手**：支持自然语言股票查询和分析

#### ✅ 股票数据管理功能
- **股票筛选系统**：多维度股票筛选算法和可视化展示
- **股票池管理**：持仓和潜在股票的完整生命周期管理
- **实时行情更新**：集成AkShare数据源的实时价格更新
- **智能搜索引擎**：支持股票代码、名称、拼音多维搜索
- **标签分类系统**：灵活的股票分类和管理功能

#### ✅ 自动化运维功能
- **数据同步调度器**：智能定时任务和数据同步管理
- **性能监控系统**：系统性能监控和优化建议
- **健康检查机制**：数据源状态监控和故障恢复
- **批量数据处理**：高效的批量操作和数据处理

#### ✅ 开发运维功能
- **一键启动脚本**：`npm run dev` 自动启动前后端服务
- **自动端口管理**：智能端口冲突检测和清理
- **开发热重载**：前端Vite热重载和后端自动重启
- **完整日志系统**：结构化日志记录和错误追踪

### 🚀 技术架构特色

#### 🔧 后端技术亮点
- **MCP协议集成**：创新使用Model Context Protocol连接数据源
- **异步并发处理**：充分利用Python asyncio提升性能
- **智能缓存机制**：多级缓存优化数据访问性能
- **模块化服务设计**：清晰的服务边界和职责分离

#### ⚛️ 前端技术亮点
- **TypeScript端到端类型安全**：完整的类型系统保证代码质量
- **自定义Hooks架构**：可复用的状态管理和业务逻辑
- **组件化设计模式**：高内聚低耦合的组件架构
- **现代化UI体验**：基于Tailwind CSS的精美界面设计

### 📊 数据库架构优势
```sql
-- 完整的数据库表结构
-- 1. 股票池管理表
CREATE TABLE stock_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    pool_type TEXT NOT NULL CHECK(pool_type IN ('holding', 'potential')),
    shares INTEGER DEFAULT 0,
    avg_cost REAL DEFAULT 0.0,
    current_price REAL DEFAULT 0.0,
    market_value REAL DEFAULT 0.0,
    tags TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(stock_code, pool_type)
);

-- 2. AI策略分析表
CREATE TABLE strategy_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_pool_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    comprehensive_score REAL,
    risk_level TEXT,
    action_recommendation TEXT,
    target_price_min REAL,
    target_price_max REAL,
    analysis_summary TEXT,
    technical_analysis TEXT,
    fundamental_analysis TEXT,
    market_context TEXT,
    key_metrics TEXT,
    risk_warnings TEXT,
    action_plan TEXT,
    analysis_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (stock_pool_id) REFERENCES stock_pool(id)
);

-- 3. 股票筛选结果表
CREATE TABLE stock_screening (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    market TEXT NOT NULL,
    screening_date TEXT NOT NULL,
    screening_type TEXT NOT NULL,
    criteria_met TEXT,
    consecutive_days INTEGER,
    avg_rise_percent REAL,
    total_volume INTEGER,
    avg_volume INTEGER,
    created_at TEXT NOT NULL
);

-- 4. 股票基础信息表
CREATE TABLE stock_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    short_name TEXT,
    market TEXT NOT NULL,
    industry TEXT,
    sector TEXT,
    list_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 5. 每日股价变动表
CREATE TABLE daily_stock_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    change_percent REAL NOT NULL,
    close_price REAL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    volume INTEGER,
    turnover REAL,
    market TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(stock_code, trade_date)
);
```

### 🎯 项目核心价值

1. **🤖 AI驱动决策**：将人工智能引入投资决策流程，提供数据驱动的投资建议
2. **📊 实时数据分析**：基于最新市场数据的实时分析和决策支持
3. **🔄 自动化管理**：减少手动操作，提升投资管理效率
4. **💡 智能筛选**：自动发现投资机会，不错过市场热点
5. **📈 专业级工具**：为个人投资者提供机构级的分析工具

### 🌟 创新技术特色

- **MCP协议首创应用**：在股票分析领域首次应用Model Context Protocol
- **AI策略生成**：结合实时数据和AI模型的智能投资策略生成
- **全栈TypeScript**：端到端类型安全的现代化开发体验
- **微服务架构**：松耦合的服务设计便于扩展和维护
- **实时数据融合**：多数据源实时整合和智能分析

---

**文档更新时间**: 2025-09-19  
**项目版本**: v2.1.0  
**维护者**: AI股票助手开发团队  
**技术支持**: Claude AI Assistant

## 🔧 快速开发指令

### 常用开发命令
```bash
# 一键启动开发环境
npm run dev

# 停止所有服务
npm run stop

# 后端独立启动
npm run backend

# 前端独立启动
npm run frontend

# 安装所有依赖
npm run install

# 构建生产版本
npm run build
```

### 故障排除指南

#### 端口冲突问题
```bash
# 自动清理端口
npm run stop

# 手动清理特定端口
lsof -ti:8001 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

#### 数据库问题
```bash
# 重建数据库
rm backend/stock_pool.db
python backend/database.py
```

#### 依赖问题
```bash
# 清理并重新安装
rm -rf node_modules frontend/node_modules
rm package-lock.json frontend/package-lock.json
npm install
```

这份技术文档涵盖了项目的完整技术架构、核心功能实现、开发规范和最佳实践。为开发团队提供了详尽的技术指导和参考资料。