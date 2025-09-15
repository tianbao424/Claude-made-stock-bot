# 🚀 高性能股票数据架构设计方案

## 🎯 核心设计原则

1. **分层存储**: 热点数据 + 冷数据分离
2. **智能缓存**: 多级缓存策略  
3. **按需加载**: 延迟加载 + 预测预载
4. **异步更新**: 后台数据同步

## 🏗️ 四层数据架构

### 🔥 L1层: 热门股票池 (内存缓存)
**目标**: 毫秒级响应热门查询
```sql
-- 热门股票表 (500-1000只)
CREATE TABLE hot_stocks (
    symbol VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50),
    market VARCHAR(5), 
    industry VARCHAR(20),
    popularity_score INT,  -- 热度评分
    last_access TIMESTAMP, -- 最后访问时间
    cache_version INT      -- 缓存版本
);

-- 热门股票实时缓存 (Redis)
hot_stock:{symbol} = {
    "price": 13.77,
    "change": 0.15,
    "timestamp": "2024-09-04T17:30:00",
    "ttl": 300  // 5分钟TTL
}
```

**选股策略**:
- 沪深300 + 中证500成分股
- 用户搜索频次TOP股票
- 市值排名前500
- 成交量活跃股票

### 📊 L2层: 完整股票索引 (数据库)
**目标**: 秒级响应全量搜索
```sql
-- 完整股票索引表
CREATE TABLE stock_index (
    symbol VARCHAR(10) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    name_pinyin VARCHAR(100),   -- 拼音索引
    short_name VARCHAR(20),
    market VARCHAR(5),
    industry VARCHAR(20),
    listing_date DATE,
    is_active BOOLEAN DEFAULT true,
    popularity_score INT DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 高性能索引
CREATE INDEX idx_name_search ON stock_index(name, name_pinyin);
CREATE INDEX idx_symbol_market ON stock_index(symbol, market);  
CREATE INDEX idx_popularity ON stock_index(popularity_score DESC);
```

### ⚡ L3层: 智能缓存层 (Redis)
**目标**: 减少API调用，提升响应速度
```redis
# 实时价格缓存 (15分钟TTL)
realtime:{symbol} = {
    "data": {...},
    "source": "individual_em", 
    "cached_at": timestamp,
    "ttl": 900
}

# 搜索结果缓存 (1分钟TTL)  
search:{query_hash} = {
    "results": [...],
    "total": 1234,
    "cached_at": timestamp,
    "ttl": 60
}

# 热度统计缓存
popularity:{symbol} = {
    "search_count": 156,
    "view_count": 892,
    "last_7d_score": 234
}
```

### 🌐 L4层: 外部数据源 (API)
**目标**: 保证数据真实性和及时性
```python
# 智能API调用策略
class SmartDataProvider:
    def get_realtime_data(self, symbol: str):
        # 1. 检查L3缓存
        if cached := redis.get(f"realtime:{symbol}"):
            return cached
            
        # 2. 检查是否为热门股票
        if symbol in hot_stocks:
            # 高优先级API调用
            data = await fast_api_call(symbol)
        else:
            # 普通API调用 + 缓存
            data = await standard_api_call(symbol)
            
        # 3. 更新缓存和热度
        redis.setex(f"realtime:{symbol}", 900, data)
        update_popularity(symbol)
        
        return data
```

## 🎯 性能优化策略

### 1. 数据库查询优化
```sql
-- 分页查询优化 (使用游标)
SELECT * FROM stock_index 
WHERE id > :cursor_id 
ORDER BY id LIMIT 20;

-- 搜索查询优化 (全文索引)
SELECT *, MATCH(name, name_pinyin) AGAINST(:query) as relevance
FROM stock_index 
WHERE MATCH(name, name_pinyin) AGAINST(:query IN NATURAL LANGUAGE MODE)
ORDER BY relevance DESC, popularity_score DESC 
LIMIT 20;
```

### 2. 前端性能优化
```typescript
// 虚拟滚动大列表
const VirtualStockList = () => {
  const virtualizer = useVirtualizer({
    count: totalStocks,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60, // 每行高度
    overscan: 10 // 预渲染行数
  });
  
  return (
    <div style={{ height: virtualizer.getTotalSize() }}>
      {virtualizer.getVirtualItems().map(item => (
        <StockRow key={item.key} stock={stocks[item.index]} />
      ))}
    </div>
  );
};

// 搜索防抖优化
const useSearchDebounce = (query: string, delay: number = 300) => {
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [query, delay]);
  
  return debouncedQuery;
};
```

### 3. 缓存更新策略
```python
# 异步后台更新任务
@scheduler.scheduled_job('cron', hour=1)  # 每天凌晨1点
async def update_stock_index():
    """更新完整股票索引"""
    new_stocks = await akshare_service.get_all_stocks()
    await database.bulk_upsert_stocks(new_stocks)
    await update_popularity_scores()

@scheduler.scheduled_job('interval', minutes=10)  # 每10分钟
async def update_hot_stocks():
    """更新热门股票实时数据"""
    hot_symbols = await get_hot_stock_symbols()
    for symbol in hot_symbols:
        realtime_data = await get_realtime_data(symbol)
        await cache.setex(f"realtime:{symbol}", 600, realtime_data)

@scheduler.scheduled_job('interval', hours=1)  # 每小时
async def update_popularity_scores():
    """更新股票热度评分"""
    search_stats = await get_search_statistics()
    view_stats = await get_view_statistics()
    
    for symbol, stats in search_stats.items():
        score = calculate_popularity_score(stats)
        await database.update_popularity(symbol, score)
```

## 📊 预期性能指标

| 操作类型 | 当前性能 | 目标性能 | 优化策略 |
|---------|---------|---------|---------|
| **热门股票搜索** | 1-3秒 | <100ms | L1内存缓存 |
| **普通股票搜索** | 3-5秒 | <300ms | L2索引+L3缓存 |
| **股票列表加载** | 5-10秒 | <1秒 | 虚拟滚动+分页 |
| **实时数据获取** | 3-8秒 | <2秒 | 多源备份+缓存 |
| **数据库查询** | 500ms-2s | <100ms | 索引优化 |

## 🚀 实施步骤

### Phase 1: 数据基础优化 (1周)
1. 导入完整A股数据 (4564只)
2. 优化数据库索引和查询
3. 实现基础缓存层

### Phase 2: 缓存系统搭建 (1周)  
1. 集成Redis缓存
2. 实现多级缓存策略
3. 添加缓存命中率监控

### Phase 3: 前端性能优化 (3天)
1. 实现虚拟滚动
2. 添加搜索防抖
3. 优化组件渲染

### Phase 4: 智能预测系统 (1周)
1. 用户行为分析
2. 热点股票预测
3. 智能预加载

## 💡 关键技术细节

### 热度评分算法
```python
def calculate_popularity_score(stats):
    search_weight = stats.search_count * 10
    view_weight = stats.view_count * 5  
    recent_weight = stats.last_7d_activity * 20
    market_cap_weight = min(stats.market_cap / 1000000000, 100)
    
    return int(search_weight + view_weight + recent_weight + market_cap_weight)
```

### 缓存失效策略
```python
# 渐进式缓存失效，避免缓存雪崩
def get_cache_ttl(symbol: str, base_ttl: int = 300) -> int:
    hash_val = hash(symbol) % 100
    jitter = base_ttl * 0.1 * (hash_val / 100)  # ±10%随机化
    return int(base_ttl + jitter)
```

这个架构可以实现：
- **真实数据**: 100%真实股票数据
- **高性能**: 毫秒级热门查询，秒级普通查询  
- **可扩展**: 支持7000+股票规模
- **用户友好**: 流畅的搜索和浏览体验