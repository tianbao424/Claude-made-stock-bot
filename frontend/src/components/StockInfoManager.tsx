import React, { useState, useEffect } from 'react';
import { Search, Database, TrendingUp, Building2, Globe, RefreshCw, Eye } from 'lucide-react';
import { searchStocks, getStockStats, StockInfo } from '../services/api';
import StockDetailModal from './StockDetailModal';

const StockInfoManager: React.FC = () => {
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [filteredStocks, setFilteredStocks] = useState<StockInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMarket, setSelectedMarket] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ total_stocks: number } | null>(null);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  
  // 股票详情模态框状态
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // 加载统计信息
  const loadStats = async () => {
    try {
      const statsData = await getStockStats();
      setStats(statsData || null);
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  // 搜索股票
  const handleSearch = async (query: string) => {
    if (query.trim()) {
      setLoading(true);
      try {
        const results = await searchStocks(query.trim(), 100);
        setStocks(results);
        setFilteredStocks(results);
        setCurrentPage(1);
      } catch (error) {
        console.error('搜索失败:', error);
        setStocks([]);
        setFilteredStocks([]);
      } finally {
        setLoading(false);
      }
    } else {
      setStocks([]);
      setFilteredStocks([]);
    }
  };

  // 市场筛选
  const filterByMarket = (market: string) => {
    if (market === 'all') {
      setFilteredStocks(stocks);
    } else {
      setFilteredStocks(stocks.filter(stock => stock.market === market));
    }
    setCurrentPage(1);
  };

  // 处理搜索输入
  useEffect(() => {
    const searchTimer = setTimeout(() => {
      handleSearch(searchQuery);
    }, 300);

    return () => clearTimeout(searchTimer);
  }, [searchQuery]);

  // 处理市场筛选
  useEffect(() => {
    filterByMarket(selectedMarket);
  }, [selectedMarket, stocks]);

  // 初始化加载统计
  useEffect(() => {
    loadStats();
  }, []);

  // 获取市场列表
  const markets = ['all', ...Array.from(new Set(stocks.map(stock => stock.market)))];
  
  // 分页逻辑
  const totalPages = Math.ceil(filteredStocks.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentStocks = filteredStocks.slice(startIndex, endIndex);

  const getMarketColor = (market: string) => {
    switch (market) {
      case 'SH': return 'bg-red-100 text-red-800';
      case 'SZ': return 'bg-green-100 text-green-800';
      case 'HK': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getMarketName = (market: string) => {
    switch (market) {
      case 'SH': return '上交所';
      case 'SZ': return '深交所';
      case 'HK': return '港交所';
      default: return market;
    }
  };

  // 处理股票详情查看
  const handleViewStock = (stock: StockInfo) => {
    setSelectedStock(stock);
    setIsDetailModalOpen(true);
  };

  // 关闭详情模态框
  const handleCloseDetail = () => {
    setIsDetailModalOpen(false);
    setSelectedStock(null);
  };

  return (
    <div className="space-y-6">
      {/* 页面标题和统计 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold text-gray-900">股票信息库</h2>
        </div>
        
        {stats && (
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              <span>总计 {stats.total_stocks} 只股票</span>
            </div>
            <button
              onClick={loadStats}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
              title="刷新统计"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* 搜索和筛选栏 */}
      <div className="bg-white rounded-lg border shadow-sm p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* 搜索框 */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="搜索股票代码或名称..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {loading && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <div className="loading-spinner"></div>
              </div>
            )}
          </div>

          {/* 市场筛选 */}
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-gray-500" />
            <select
              value={selectedMarket}
              onChange={(e) => setSelectedMarket(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">所有市场</option>
              {markets.filter(m => m !== 'all').map(market => (
                <option key={market} value={market}>
                  {getMarketName(market)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 结果统计 */}
        {searchQuery && (
          <div className="mt-3 text-sm text-gray-600">
            找到 <span className="font-semibold">{filteredStocks.length}</span> 条结果
            {selectedMarket !== 'all' && (
              <span> (筛选: {getMarketName(selectedMarket)})</span>
            )}
          </div>
        )}
      </div>

      {/* 股票列表 */}
      {searchQuery ? (
        <div className="bg-white rounded-lg border shadow-sm">
          {currentStocks.length > 0 ? (
            <>
              {/* 表格 */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票代码
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        简称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        市场
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        行业
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {currentStocks.map((stock) => (
                      <tr key={`${stock.symbol}-${stock.market}`} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-mono font-semibold text-blue-600">
                            {stock.symbol}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-gray-900 font-medium">
                            {stock.name}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                          {stock.short_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getMarketColor(stock.market)}`}>
                            {getMarketName(stock.market)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                          <div className="flex items-center gap-1">
                            <Building2 className="w-3 h-3 text-gray-400" />
                            {stock.industry || '-'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => handleViewStock(stock)}
                            className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                            title="查看实时行情"
                          >
                            <Eye className="w-3 h-3" />
                            查看详情
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="px-6 py-3 border-t bg-gray-50 flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    显示 {startIndex + 1}-{Math.min(endIndex, filteredStocks.length)} 项，
                    共 {filteredStocks.length} 项
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                    >
                      上一页
                    </button>
                    <span className="text-sm text-gray-600">
                      {currentPage} / {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-8 text-center">
              <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">未找到股票</h3>
              <p className="text-gray-600">
                请尝试其他搜索关键词或调整筛选条件
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg border shadow-sm p-8 text-center">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">搜索股票信息</h3>
          <p className="text-gray-600 mb-4">
            输入股票代码或名称开始搜索
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{stats ? stats.total_stocks.toLocaleString() : '4620+'}</div>
              <div className="text-sm text-gray-600">支持股票</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">A+H</div>
              <div className="text-sm text-gray-600">双市场</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">智能</div>
              <div className="text-sm text-gray-600">搜索匹配</div>
            </div>
          </div>
        </div>
      )}

      {/* 股票详情模态框 */}
      <StockDetailModal
        stock={selectedStock}
        isOpen={isDetailModalOpen}
        onClose={handleCloseDetail}
      />
    </div>
  );
};

export default StockInfoManager;