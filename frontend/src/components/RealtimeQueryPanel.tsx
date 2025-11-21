import React, { useState, useEffect, useRef } from 'react';
import {
  Search, TrendingUp, TrendingDown, RefreshCw, 
  Eye, BarChart3, Clock, AlertCircle,
  CheckCircle, Wifi, WifiOff, Star, StarOff
} from 'lucide-react';

// 实时股价数据接口
interface RealtimeStockData {
  symbol: string;
  name: string;
  current_price: number;
  change_amount: number;
  change_percent: number;
  volume: number;
  turnover: number;
  open_price: number;
  high_price: number;
  low_price: number;
  prev_close: number;
  market_cap: number;
  pe_ratio: number;
  pb_ratio: number;
  timestamp: string;
}

// 查询结果接口
interface QueryResult {
  symbol: string;
  success: boolean;
  data?: RealtimeStockData;
  error?: string;
}

// 查询响应接口
interface QueryResponse {
  results: QueryResult[];
  summary: {
    total_symbols: number;
    successful_count: number;
    failed_count: number;
  };
}

// 自选股接口
interface WatchlistItem {
  symbol: string;
  name: string;
  market: string;
  addedAt: string;
}

const RealtimeQueryPanel: React.FC = () => {
  // 状态管理
  const [querySymbols, setQuerySymbols] = useState<string>('');
  const [selectedMarket, setSelectedMarket] = useState<'A' | 'HK'>('A');
  const [queryResults, setQueryResults] = useState<QueryResult[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(30); // 秒
  
  // 自选股管理
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [showWatchlistOnly, setShowWatchlistOnly] = useState(false);
  
  // UI状态
  const [sortBy, setSortBy] = useState<'symbol' | 'change_percent' | 'volume'>('symbol');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'failed'>('all');
  
  // 自动刷新定时器
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // 加载自选股
  useEffect(() => {
    const savedWatchlist = localStorage.getItem('stock_watchlist');
    if (savedWatchlist) {
      try {
        setWatchlist(JSON.parse(savedWatchlist));
      } catch (error) {
        console.error('加载自选股失败:', error);
      }
    }
  }, []);
  
  // 保存自选股
  useEffect(() => {
    localStorage.setItem('stock_watchlist', JSON.stringify(watchlist));
  }, [watchlist]);
  
  // 自动刷新控制
  useEffect(() => {
    if (autoRefresh && queryResults.length > 0) {
      intervalRef.current = setInterval(() => {
        handleRefreshAll();
      }, refreshInterval * 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, queryResults.length]);

  // 查询股票实时数据
  const queryRealtimeData = async (symbols: string[], market: string = 'A') => {
    try {
      setIsQuerying(true);
      
      const response = await fetch('/api/data-collection/realtime-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols, market })
      });
      
      if (response.ok) {
        const result: { data: QueryResponse } = await response.json();
        setQueryResults(result.data.results);
        setLastUpdateTime(new Date().toLocaleTimeString());
        
        // 自动添加到自选股（如果不存在）
        symbols.forEach(symbol => {
          const existingResult = result.data.results.find(r => r.symbol === symbol && r.success);
          if (existingResult && existingResult.data) {
            const existingWatch = watchlist.find(w => w.symbol === symbol);
            if (!existingWatch) {
              const newWatchItem: WatchlistItem = {
                symbol: symbol,
                name: existingResult.data.name,
                market: market,
                addedAt: new Date().toISOString()
              };
              setWatchlist(prev => [...prev, newWatchItem]);
            }
          }
        });
      } else {
        console.error('查询失败:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('查询异常:', error);
    } finally {
      setIsQuerying(false);
    }
  };

  // 处理查询按钮点击
  const handleQuery = () => {
    const symbols = querySymbols
      .split(/[,，\s\n]+/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
    
    if (symbols.length === 0) {
      alert('请输入股票代码');
      return;
    }
    
    queryRealtimeData(symbols, selectedMarket);
  };

  // 处理自选股查询
  const handleQueryWatchlist = () => {
    if (watchlist.length === 0) {
      alert('自选股列表为空');
      return;
    }
    
    // 按市场分组查询
    const aStocks = watchlist.filter(w => w.market === 'A').map(w => w.symbol);
    const hkStocks = watchlist.filter(w => w.market === 'HK').map(w => w.symbol);
    
    Promise.all([
      aStocks.length > 0 ? queryRealtimeData(aStocks, 'A') : Promise.resolve(),
      hkStocks.length > 0 ? queryRealtimeData(hkStocks, 'HK') : Promise.resolve()
    ]);
  };

  // 刷新所有数据
  const handleRefreshAll = () => {
    if (queryResults.length === 0) return;
    
    const successfulResults = queryResults.filter(r => r.success);
    if (successfulResults.length === 0) return;
    
    const symbols = successfulResults.map(r => r.symbol);
    queryRealtimeData(symbols, selectedMarket);
  };

  // 添加到自选股
  const addToWatchlist = (result: QueryResult) => {
    if (!result.success || !result.data) return;
    
    const existingWatch = watchlist.find(w => w.symbol === result.symbol);
    if (existingWatch) return;
    
    const newWatchItem: WatchlistItem = {
      symbol: result.symbol,
      name: result.data.name,
      market: selectedMarket,
      addedAt: new Date().toISOString()
    };
    
    setWatchlist(prev => [...prev, newWatchItem]);
  };

  // 从自选股移除
  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(prev => prev.filter(w => w.symbol !== symbol));
  };

  // 判断是否在自选股中
  const isInWatchlist = (symbol: string) => {
    return watchlist.some(w => w.symbol === symbol);
  };

  // 过滤和排序结果
  const getFilteredAndSortedResults = () => {
    let filtered = queryResults;
    
    // 状态过滤
    if (filterStatus === 'success') {
      filtered = filtered.filter(r => r.success);
    } else if (filterStatus === 'failed') {
      filtered = filtered.filter(r => !r.success);
    }
    
    // 自选股过滤
    if (showWatchlistOnly) {
      filtered = filtered.filter(r => isInWatchlist(r.symbol));
    }
    
    // 排序
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      if (sortBy === 'symbol') {
        aValue = a.symbol;
        bValue = b.symbol;
      } else if (sortBy === 'change_percent') {
        aValue = a.success && a.data ? a.data.change_percent : -999;
        bValue = b.success && b.data ? b.data.change_percent : -999;
      } else if (sortBy === 'volume') {
        aValue = a.success && a.data ? a.data.volume : 0;
        bValue = b.success && b.data ? b.data.volume : 0;
      }
      
      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    
    return filtered;
  };

  // 格式化数字
  const formatNumber = (num: number, decimals: number = 2) => {
    if (num >= 1e8) {
      return (num / 1e8).toFixed(decimals) + '亿';
    } else if (num >= 1e4) {
      return (num / 1e4).toFixed(decimals) + '万';
    }
    return num.toFixed(decimals);
  };

  // 渲染股票卡片
  const renderStockCard = (result: QueryResult) => {
    const isSuccess = result.success && result.data;
    const data = result.data;
    const inWatchlist = isInWatchlist(result.symbol);
    
    return (
      <div
        key={result.symbol}
        className={`bg-white border rounded-lg p-4 transition-all duration-200 ${
          isSuccess ? 'hover:shadow-md' : 'border-red-200 bg-red-50'
        }`}
      >
        {isSuccess && data ? (
          <>
            {/* 股票头部信息 */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-gray-900">{data.symbol}</h3>
                <span className="text-sm text-gray-600">{data.name}</span>
                <button
                  onClick={() => inWatchlist ? removeFromWatchlist(result.symbol) : addToWatchlist(result)}
                  className={`p-1 rounded transition-colors ${
                    inWatchlist 
                      ? 'text-yellow-500 hover:text-yellow-600' 
                      : 'text-gray-400 hover:text-yellow-500'
                  }`}
                >
                  {inWatchlist ? <Star className="w-4 h-4 fill-current" /> : <StarOff className="w-4 h-4" />}
                </button>
              </div>
              
              <div className="text-right">
                <div className="text-lg font-bold text-gray-900">
                  ¥{data.current_price.toFixed(2)}
                </div>
                <div className={`text-sm flex items-center gap-1 ${
                  data.change_percent >= 0 ? 'text-red-600' : 'text-green-600'
                }`}>
                  {data.change_percent >= 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  {data.change_percent >= 0 ? '+' : ''}{data.change_percent.toFixed(2)}%
                  <span className="ml-1">
                    ({data.change_amount >= 0 ? '+' : ''}{data.change_amount.toFixed(2)})
                  </span>
                </div>
              </div>
            </div>
            
            {/* 详细数据 */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">今开:</span>
                  <span>{data.open_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">最高:</span>
                  <span className="text-red-600">{data.high_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">最低:</span>
                  <span className="text-green-600">{data.low_price.toFixed(2)}</span>
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">成交量:</span>
                  <span>{formatNumber(data.volume, 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">成交额:</span>
                  <span>{formatNumber(data.turnover, 1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">市值:</span>
                  <span>{formatNumber(data.market_cap, 1)}</span>
                </div>
              </div>
            </div>
            
            {/* 估值指标 */}
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="flex justify-between text-sm">
                <div>
                  <span className="text-gray-500">PE: </span>
                  <span className={data.pe_ratio > 0 ? '' : 'text-gray-400'}>
                    {data.pe_ratio > 0 ? data.pe_ratio.toFixed(1) : '--'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">PB: </span>
                  <span className={data.pb_ratio > 0 ? '' : 'text-gray-400'}>
                    {data.pb_ratio > 0 ? data.pb_ratio.toFixed(1) : '--'}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(data.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          </>
        ) : (
          // 错误状态
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <div className="font-medium text-red-700">{result.symbol}</div>
              <div className="text-sm text-red-600">{result.error || '查询失败'}</div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 标题栏 */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-green-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">实时行情查询</h1>
              <p className="text-gray-600">查询股票实时价格和基本面数据</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {lastUpdateTime && (
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <Clock className="w-4 h-4" />
                <span>更新时间: {lastUpdateTime}</span>
              </div>
            )}
            
            <div className={`flex items-center gap-1 px-2 py-1 rounded text-sm ${
              autoRefresh ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {autoRefresh ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
              <span>{autoRefresh ? '自动刷新' : '手动刷新'}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* 查询控制面板 */}
      <div className="bg-white border-b px-6 py-4">
        <div className="space-y-4">
          {/* 查询输入 */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">股票代码（支持批量，用逗号分隔）</label>
              <textarea
                value={querySymbols}
                onChange={(e) => setQuerySymbols(e.target.value)}
                placeholder="请输入股票代码，如: 000001,600000,300750"
                className="w-full px-3 py-2 border rounded-lg resize-none"
                rows={2}
              />
            </div>
            
            <div className="w-32">
              <label className="block text-sm text-gray-600 mb-1">市场</label>
              <select
                value={selectedMarket}
                onChange={(e) => setSelectedMarket(e.target.value as 'A' | 'HK')}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="A">A股</option>
                <option value="HK">港股</option>
              </select>
            </div>
            
            <div className="flex flex-col justify-end gap-2">
              <button
                onClick={handleQuery}
                disabled={isQuerying}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Search className="w-4 h-4" />
                {isQuerying ? '查询中...' : '查询'}
              </button>
              
              <button
                onClick={handleQueryWatchlist}
                disabled={isQuerying || watchlist.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Star className="w-4 h-4" />
                自选股
              </button>
            </div>
          </div>
          
          {/* 控制选项 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* 自动刷新设置 */}
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">自动刷新</span>
              </label>
              
              {autoRefresh && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">间隔:</span>
                  <select
                    value={refreshInterval}
                    onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    <option value={10}>10秒</option>
                    <option value={30}>30秒</option>
                    <option value={60}>1分钟</option>
                    <option value={300}>5分钟</option>
                  </select>
                </div>
              )}
              
              {/* 显示过滤 */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">显示:</span>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value as any)}
                  className="px-2 py-1 border rounded text-sm"
                >
                  <option value="all">全部</option>
                  <option value="success">成功</option>
                  <option value="failed">失败</option>
                </select>
              </div>
              
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={showWatchlistOnly}
                  onChange={(e) => setShowWatchlistOnly(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">仅自选股</span>
              </label>
            </div>
            
            <div className="flex items-center gap-2">
              {/* 排序控制 */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">排序:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-2 py-1 border rounded text-sm"
                >
                  <option value="symbol">代码</option>
                  <option value="change_percent">涨跌幅</option>
                  <option value="volume">成交量</option>
                </select>
                
                <button
                  onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="px-2 py-1 border rounded text-sm hover:bg-gray-50"
                >
                  {sortOrder === 'asc' ? '↑' : '↓'}
                </button>
              </div>
              
              {/* 刷新按钮 */}
              <button
                onClick={handleRefreshAll}
                disabled={isQuerying || queryResults.length === 0}
                className="flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${isQuerying ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* 结果展示区 */}
      <div className="flex-1 overflow-y-auto p-6">
        {queryResults.length === 0 ? (
          <div className="text-center py-12">
            <BarChart3 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg mb-2">暂无查询结果</p>
            <p className="text-gray-400 text-sm">请输入股票代码进行查询</p>
          </div>
        ) : (
          <>
            {/* 统计信息 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium">查询结果</h2>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span>成功: {queryResults.filter(r => r.success).length}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <AlertCircle className="w-4 h-4 text-red-600" />
                    <span>失败: {queryResults.filter(r => !r.success).length}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="w-4 h-4 text-yellow-600" />
                    <span>自选: {watchlist.length}</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 股票卡片网格 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {getFilteredAndSortedResults().map(renderStockCard)}
            </div>
            
            {getFilteredAndSortedResults().length === 0 && (
              <div className="text-center py-8">
                <Eye className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">当前筛选条件下无结果</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default RealtimeQueryPanel;