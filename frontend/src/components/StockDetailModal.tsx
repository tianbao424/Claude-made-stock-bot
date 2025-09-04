import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, RefreshCw, Building2, Globe, BarChart3 } from 'lucide-react';
import { StockInfo } from '../services/api';

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
  market_cap?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  timestamp: string;
}

interface StockDetailModalProps {
  stock: StockInfo | null;
  isOpen: boolean;
  onClose: () => void;
}

const StockDetailModal: React.FC<StockDetailModalProps> = ({ stock, isOpen, onClose }) => {
  const [realtimeData, setRealtimeData] = useState<RealtimeStockData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取实时数据
  const fetchRealtimeData = async () => {
    if (!stock) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/stocks/realtime/${stock.symbol}`);
      const result = await response.json();
      
      if (result.success && result.data) {
        setRealtimeData(result.data);
      } else {
        setError(result.message || '获取实时数据失败');
      }
    } catch (err) {
      setError('网络请求失败');
      console.error('获取实时数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  // 自动刷新机制
  useEffect(() => {
    if (!isOpen || !stock || !autoRefresh) return;

    fetchRealtimeData();
    
    const interval = setInterval(() => {
      fetchRealtimeData();
    }, 30000); // 每30秒刷新

    return () => clearInterval(interval);
  }, [isOpen, stock, autoRefresh]);

  // 格式化数字显示
  const formatNumber = (num: number, decimal: number = 2) => {
    if (isNaN(num)) return '--';
    return num.toLocaleString('zh-CN', { 
      minimumFractionDigits: decimal, 
      maximumFractionDigits: decimal 
    });
  };

  // 格式化大数字(成交量、成交额)
  const formatLargeNumber = (num: number) => {
    if (isNaN(num) || num === 0) return '--';
    if (num >= 100000000) return `${(num / 100000000).toFixed(2)}亿`;
    if (num >= 10000) return `${(num / 10000).toFixed(2)}万`;
    return num.toLocaleString();
  };

  // 获取涨跌颜色
  const getPriceColor = (change: number) => {
    if (change > 0) return 'text-red-600';
    if (change < 0) return 'text-green-600';
    return 'text-gray-600';
  };

  // 获取涨跌图标
  const getPriceIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="w-4 h-4" />;
    if (change < 0) return <TrendingDown className="w-4 h-4" />;
    return null;
  };

  if (!isOpen || !stock) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4 py-16">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[75vh] overflow-hidden border border-gray-200">
        {/* 模态头部 */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-2xl font-bold text-gray-900">
                {stock.name}
              </h2>
              <span className="px-3 py-1 bg-blue-50 text-blue-600 text-sm font-semibold rounded-lg">
                {stock.symbol}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="inline-flex items-center px-3 py-1 bg-gray-50 text-gray-700 rounded-lg">
                <Globe className="w-4 h-4 mr-2" />
                <span>{stock.market === 'SH' ? '上交所' : stock.market === 'SZ' ? '深交所' : stock.market === 'HK' ? '港交所' : stock.market}</span>
              </span>
              <span className="inline-flex items-center px-3 py-1 bg-gray-50 text-gray-700 rounded-lg">
                <Building2 className="w-4 h-4 mr-2" />
                <span>{stock.industry}</span>
              </span>
              {stock.sector && (
                <span className="inline-flex items-center px-3 py-1 bg-gray-50 text-gray-700 rounded-lg">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  <span>{stock.sector}</span>
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2 ml-4">
            <button
              onClick={fetchRealtimeData}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-50 text-sm"
              title="刷新数据"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-500' : 'text-gray-600'}`} />
              <span className="text-gray-700">刷新</span>
            </button>
            
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                autoRefresh 
                  ? 'bg-blue-50 text-blue-600 hover:bg-blue-100' 
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
              title="自动刷新"
            >
              <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-blue-600' : 'bg-gray-400'}`} />
              自动刷新
            </button>
            
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 主要内容 */}
        <div className="px-6 pt-2 pb-6 overflow-y-auto" style={{maxHeight: 'calc(75vh - 100px)'}}>
          {/* 错误提示 */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {/* 实时行情数据 */}
          {realtimeData ? (
            <div className="space-y-4">
              {/* 核心价格信息 */}
              <div className="bg-white border border-gray-200 rounded-lg px-4 pt-2 pb-4">
                {/* 价格展示区域 */}
                <div className="text-center mb-3">
                  <div className={`text-3xl font-bold mb-1.5 ${getPriceColor(realtimeData.change_amount)}`}>
                    ¥{formatNumber(realtimeData.current_price)}
                  </div>
                  <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-semibold ${
                    realtimeData.change_amount > 0 
                      ? 'bg-red-50 text-red-600' 
                      : realtimeData.change_amount < 0 
                        ? 'bg-green-50 text-green-600'
                        : 'bg-gray-50 text-gray-600'
                  }`}>
                    {getPriceIcon(realtimeData.change_amount)}
                    <span>
                      {realtimeData.change_amount > 0 ? '+' : ''}{formatNumber(realtimeData.change_amount)}
                    </span>
                    <span>
                      ({realtimeData.change_percent > 0 ? '+' : ''}{formatNumber(realtimeData.change_percent)}%)
                    </span>
                  </div>
                </div>
                
                {/* 基础数据紧凑布局 */}
                <div className="flex justify-center items-center gap-4 mb-3 text-sm bg-gray-50 rounded-lg py-2">
                  <div className="flex flex-col items-center px-2">
                    <span className="text-xs text-gray-500">昨收</span>
                    <span className="font-medium text-gray-900 text-sm">¥{formatNumber(realtimeData.prev_close)}</span>
                  </div>
                  <div className="w-px h-6 bg-gray-300"></div>
                  <div className="flex flex-col items-center px-2">
                    <span className="text-xs text-gray-500">今开</span>
                    <span className="font-medium text-gray-900 text-sm">¥{formatNumber(realtimeData.open_price)}</span>
                  </div>
                  <div className="w-px h-6 bg-gray-300"></div>
                  <div className="flex flex-col items-center px-2">
                    <span className="text-xs text-gray-500">最高</span>
                    <span className="font-medium text-red-600 text-sm">¥{formatNumber(realtimeData.high_price)}</span>
                  </div>
                  <div className="w-px h-6 bg-gray-300"></div>
                  <div className="flex flex-col items-center px-2">
                    <span className="text-xs text-gray-500">最低</span>
                    <span className="font-medium text-green-600 text-sm">¥{formatNumber(realtimeData.low_price)}</span>
                  </div>
                </div>
              </div>

              {/* 详细数据面板 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* 交易数据 */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2.5 flex items-center">
                    <BarChart3 className="w-4 h-4 mr-2 text-blue-600" />
                    交易数据
                  </h4>
                  <div className="space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">成交量</span>
                      <span className="text-xs font-medium text-gray-900">{formatLargeNumber(realtimeData.volume)}手</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">成交额</span>
                      <span className="text-xs font-medium text-gray-900">{formatLargeNumber(realtimeData.turnover)}元</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">振幅</span>
                      <span className="text-xs font-medium text-gray-900">
                        {formatNumber(((realtimeData.high_price - realtimeData.low_price) / realtimeData.prev_close * 100))}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">换手率</span>
                      <span className="text-xs font-medium text-gray-900">
                        {realtimeData.volume > 0 && realtimeData.market_cap && realtimeData.market_cap > 0 
                          ? formatNumber((realtimeData.turnover / realtimeData.market_cap * 100)) + '%'
                          : '--'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 估值指标 */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2.5 flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2 text-emerald-600" />
                    估值指标
                  </h4>
                  <div className="space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">市盈率(P/E)</span>
                      <span className="text-xs font-medium text-gray-900">
                        {realtimeData.pe_ratio && realtimeData.pe_ratio > 0 ? formatNumber(realtimeData.pe_ratio) : '--'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">市净率(P/B)</span>
                      <span className="text-xs font-medium text-gray-900">
                        {realtimeData.pb_ratio && realtimeData.pb_ratio > 0 ? formatNumber(realtimeData.pb_ratio) : '--'}
                      </span>
                    </div>
                    {realtimeData.market_cap && realtimeData.market_cap > 0 && (
                      <div className="flex justify-between">
                        <span className="text-xs text-gray-600">总市值</span>
                        <span className="text-xs font-medium text-gray-900">{formatLargeNumber(realtimeData.market_cap)}元</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">每股净资产</span>
                      <span className="text-xs font-medium text-gray-900">
                        {realtimeData.pb_ratio && realtimeData.pb_ratio > 0 
                          ? '¥' + formatNumber(realtimeData.current_price / realtimeData.pb_ratio) 
                          : '--'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 数据状态 */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 mt-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-gray-700">实时数据</span>
                    <span className="text-gray-500">
                      {new Date(realtimeData.timestamp).toLocaleString('zh-CN', {
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-gray-500">
                    <div className={`w-1 h-1 rounded-full ${autoRefresh ? 'bg-blue-500' : 'bg-gray-400'}`}></div>
                    <span>{autoRefresh ? '自动刷新' : '已暂停'}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
                <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-blue-300 rounded-full animate-spin" style={{animationDirection: 'reverse', animationDuration: '1.5s'}}></div>
              </div>
              <div className="mt-6 text-center">
                <p className="text-lg font-medium text-gray-700 mb-2">正在获取实时行情数据</p>
                <p className="text-sm text-gray-500">请稍候，正在从AkShare获取最新数据...</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center">
                <BarChart3 className="w-12 h-12 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">暂无实时数据</h3>
              <p className="text-gray-500 mb-6">点击下方按钮获取{stock.name}的最新行情</p>
              <button
                onClick={fetchRealtimeData}
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium rounded-lg hover:from-blue-600 hover:to-blue-700 transform hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                <RefreshCw className="w-5 h-5" />
                获取实时数据
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StockDetailModal;