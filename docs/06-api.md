# 📡 API接口文档

## 🎯 API概述

本文档详细描述了AI股票聊天助手的所有API接口，包括请求格式、响应结构、错误处理等。

### 基本信息
- **Base URL**: `http://localhost:8001/api`
- **协议**: HTTP/1.1
- **数据格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 📋 API端点总览

#### 🎯 核心业务API
```python
# 股票筛选相关
POST   /api/screening/screen-stocks          # 基础股票筛选
GET    /api/screening/latest-results         # 获取最新筛选结果
POST   /api/advanced-screening/basic         # 高级基础筛选
POST   /api/advanced-screening/strategy      # 策略筛选

# 数据管理相关
GET    /api/stock-info/status               # 股票信息状态
POST   /api/stock-info/full-update          # 股票信息更新
GET    /api/unified-collection/status       # 数据采集状态
POST   /api/unified-collection/force-collect # 强制数据采集

# AI分析相关
POST   /api/chat                            # AI聊天对话
GET    /api/strategies/available            # 可用策略列表
POST   /api/strategies/test                 # 策略测试

# 系统监控相关
GET    /api/system/health-check             # 系统健康检查
GET    /api/system/info                     # 系统信息
GET    /api/quota-status                    # 配额状态
```

#### 🔄 数据同步API
```python
# 数据采集API
POST   /api/data-sync/manual/collection     # 手动数据采集
POST   /api/data-sync/manual/screening      # 手动筛选触发
GET    /api/data-status/update-status       # 数据更新状态

# WebSocket端点
WS     /ws                                  # 实时通信
```

### 📊 API响应格式标准
```python
# 标准响应格式
class ApiResponse(BaseModel):
    success: bool                    # 操作成功标志
    message: str = ""               # 响应消息
    data: Optional[Any] = None      # 响应数据
    error_code: Optional[str] = None # 错误代码
    timestamp: str                   # 时间戳

# 示例响应
{
    "success": true,
    "message": "筛选完成",
    "data": {
        "results": [...],
        "total_count": 100
    },
    "timestamp": "2025-11-20T14:30:00Z"
}
```

## 🗂️ 股票池管理API

### 获取股票池列表
```http
GET /api/stock-pools
```

**参数**:
- `pool_type` (optional): 池类型 (`holding` | `potential`)
- `limit` (optional): 返回数量限制，默认100

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "stock_code": "000001",
      "stock_name": "平安银行",
      "pool_type": "holding",
      "shares": 1000,
      "avg_cost": 12.50,
      "current_price": 13.20,
      "market_value": 13200.00,
      "tags": ["银行股", "价值投资"],
      "notes": "长期持有",
      "created_at": "2025-09-25T10:00:00",
      "updated_at": "2025-09-25T15:30:00"
    }
  ],
  "message": "获取成功"
}
```

### 创建股票池条目
```http
POST /api/stock-pools
```

**请求体**:
```json
{
  "stock_code": "000001",
  "stock_name": "平安银行",
  "pool_type": "holding",
  "shares": 1000,
  "avg_cost": 12.50,
  "tags": ["银行股"],
  "notes": "新买入"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "stock_code": "000001",
    "stock_name": "平安银行",
    "pool_type": "holding",
    "shares": 1000,
    "avg_cost": 12.50,
    "current_price": 0.0,
    "market_value": 0.0,
    "created_at": "2025-09-25T10:00:00"
  },
  "message": "添加成功"
}
```

### 更新股票池条目
```http
PUT /api/stock-pools/{id}
```

### 删除股票池条目
```http
DELETE /api/stock-pools/{id}
```

### 批量更新股价
```http
POST /api/stock-pools/batch-update-prices
```

## 🤖 AI策略分析API

### 生成投资策略
```http
POST /api/strategy/generate/{stock_pool_id}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "stock_pool_id": 1,
    "stock_code": "000001",
    "comprehensive_score": 7.8,
    "risk_level": "medium",
    "action_recommendation": "hold",
    "target_price_min": 12.80,
    "target_price_max": 14.50,
    "analysis_summary": "基于当前技术指标和基本面分析...",
    "technical_analysis": "从技术角度看，该股票呈现...",
    "fundamental_analysis": "基本面分析显示...",
    "key_metrics": [
      {"metric": "PE", "value": "6.8", "comment": "估值较低"},
      {"metric": "PB", "value": "0.85", "comment": "破净资产"}
    ],
    "risk_warnings": [
      "银行业监管政策变化风险",
      "利率波动对净息差的影响"
    ],
    "action_plan": [
      "维持当前仓位，等待业绩改善",
      "关注三季度财报情况"
    ],
    "analysis_date": "2025-09-25T15:30:00"
  },
  "message": "策略分析完成"
}
```

### 获取策略历史
```http
GET /api/strategy/history/{stock_pool_id}
```

## 🔍 股票筛选API

### 手动触发筛选
```http
POST /api/screening/manual-trigger
```

**请求体**:
```json
{
  "screening_type": "strong_rise_3d",
  "min_consecutive_days": 3,
  "min_rise_percent": 7.0,
  "min_volume": 0,
  "market_filter": ["SH", "SZ"]
}
```

### 获取最新筛选结果
```http
GET /api/screening/latest-results?screening_type=strong_rise_3d&limit=50
```

**响应**:
```json
{
  "success": true,
  "data": {
    "screening_date": "2025-09-25",
    "screening_type": "strong_rise_3d",
    "results": [
      {
        "id": 1,
        "stock_code": "002594",
        "stock_name": "比亚迪",
        "market": "SZ",
        "consecutive_days": 3,
        "avg_rise_percent": 8.5,
        "total_volume": 15000000,
        "avg_volume": 5000000
      }
    ]
  },
  "message": "获取成功"
}
```

### 初始化历史数据
```http
POST /api/screening/init-historical-data?days_back=7
```

### 获取筛选历史
```http
GET /api/screening/history?screening_type=strong_rise_3d&limit=100
```

## 📊 深度分析API

### 执行深度分析
```http
POST /api/deep-analysis/analyze
```

**请求体**:
```json
{
  "stock_codes": ["000001", "002594"],
  "save_results": true
}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "stock_code": "000001",
      "overall_score": 7.2,
      "investment_grade": "B",
      "volatility_score": 6.8,
      "volume_score": 7.8,
      "is_low_volatility_breakout": false,
      "is_volume_price_coordinated": true,
      "is_worthy_of_attention": true,
      "risk_level": "medium",
      "recommendation": "适合中长期持有",
      "analysis_date": "2025-09-25T15:30:00"
    }
  ],
  "message": "深度分析完成"
}
```

### 获取分析结果
```http
GET /api/deep-analysis/results?stock_code=000001&limit=10
```

### 获取值得关注的股票
```http
GET /api/deep-analysis/worthy-stocks?limit=20
```

## 🔄 自动池管理API

### 处理筛选结果
```http
POST /api/auto-pool/process-screening
```

**响应**:
```json
{
  "success": true,
  "data": {
    "total_analyzed": 50,
    "qualified_stocks": 8,
    "added_to_pool": 5,
    "skipped_existing": 3,
    "processing_time": 15.8,
    "details": [
      {
        "stock_code": "002594",
        "action": "added",
        "reason": "符合自动添加条件"
      }
    ]
  },
  "message": "自动处理完成"
}
```

### 获取配置
```http
GET /api/auto-pool/config
```

### 更新配置
```http
PUT /api/auto-pool/config
```

## 📈 股票信息API

### 搜索股票
```http
GET /api/stocks/search?query=平安&limit=10
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "symbol": "000001",
      "name": "平安银行",
      "short_name": "平安银行",
      "market": "SZ",
      "industry": "银行",
      "sector": "金融业"
    }
  ],
  "message": "搜索成功"
}
```

### 获取股票详情
```http
GET /api/stocks/info/{symbol}
```

### 获取实时行情
```http
GET /api/stocks/realtime/{symbol}
```

## 🔧 数据同步API

### 获取数据源状态
```http
GET /api/data-sources/status
```

### 手动同步数据
```http
POST /api/data-sources/sync?task_name=daily_data_collection
```

## 📊 性能监控API

### 获取性能指标
```http
GET /api/performance/stats
```

**响应**:
```json
{
  "success": true,
  "data": {
    "api_response_times": {
      "avg": 150,
      "p95": 300,
      "p99": 500
    },
    "database_metrics": {
      "total_records": 50000,
      "query_performance": 25,
      "database_size": "125.5 MB"
    },
    "system_health": {
      "memory_usage": 65,
      "cpu_usage": 25,
      "disk_usage": 45,
      "status": "healthy"
    }
  },
  "message": "性能指标获取成功"
}
```

### 性能优化测试
```http
POST /api/performance/optimization-test
```

## 🌐 WebSocket API

### 连接地址
```
ws://localhost:8001/ws
```

### 消息格式

**发送消息**:
```json
{
  "type": "query",
  "content": "帮我分析一下000001这只股票",
  "timestamp": "2025-09-25T15:30:00Z"
}
```

**接收消息**:
```json
{
  "type": "response",
  "content": "基于最新数据分析，000001（平安银行）...",
  "timestamp": "2025-09-25T15:30:05Z"
}
```

## ❌ 错误处理

### HTTP状态码
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "股票代码不能为空",
    "details": {
      "field": "stock_code",
      "value": ""
    }
  }
}
```

### 常见错误码
- `VALIDATION_ERROR`: 参数验证失败
- `NOT_FOUND`: 资源未找到
- `DATABASE_ERROR`: 数据库操作失败
- `EXTERNAL_API_ERROR`: 外部API调用失败
- `RATE_LIMIT_EXCEEDED`: 请求频率超限

## 🔐 安全与认证

### API密钥（未来功能）
```http
Authorization: Bearer your-api-key
```

### 请求限制
- 每分钟最多100次请求
- 批量操作最多50条记录
- WebSocket连接最多5个

---

**注意**: API接口可能会根据功能更新而变化，建议定期查看最新文档。