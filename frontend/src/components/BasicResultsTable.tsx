import React, { useState, useMemo, useRef } from 'react';
import { ChevronLeft, ChevronRight, TrendingUp, Target, Filter } from 'lucide-react';

interface StockResult {
  stock_code: string;
  stock_name: string;
  market: string;
  industry: string;
  consecutive_days: number;
  avg_rise_percent: number;
  total_volume: number;
  avg_volume: number;
  market_cap: number;
  pe_ratio: number;
  close_price: number;
  turnover_rate?: number;
  screening_date: string;
  strategy_score?: number;
  signal_type?: string;
  signal_strength?: string;
  risk_level?: string;
}

interface BasicResultsTableProps {
  results: StockResult[];
  loading: boolean;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  showStrategyColumns: boolean;
}

const BasicResultsTable: React.FC<BasicResultsTableProps> = ({
  results,
  loading,
  currentPage,
  pageSize,
  onPageChange,
  onPageSizeChange,
  showStrategyColumns
}) => {
  const [sortField, setSortField] = useState<keyof StockResult>('avg_rise_percent');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const tableRef = useRef<HTMLDivElement>(null);

  // 排序处理
  const sortedResults = useMemo(() => {
    if (!results.length) return [];
    
    return [...results].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      
      if (aVal === bVal) return 0;
      if (aVal === undefined || aVal === null) return 1;
      if (bVal === undefined || bVal === null) return -1;
      
      const comparison = aVal > bVal ? 1 : -1;
      return sortDirection === 'desc' ? -comparison : comparison;
    });
  }, [results, sortField, sortDirection]);

  // 分页处理
  const totalPages = Math.ceil(results.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentPageData = sortedResults.slice(startIndex, endIndex);

  // 处理排序
  const handleSort = (field: keyof StockResult) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // 格式化数字
  const formatNumber = (num: number, decimals: number = 2): string => {
    return num.toLocaleString('zh-CN', { 
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals 
    });
  };

  // 格式化成交量
  const formatVolume = (volume: number): string => {
    if (volume >= 10000) {
      return `${(volume / 10000).toFixed(1)}万`;
    }
    return volume.toString();
  };

  // 格式化市值 (API返回的已经是亿元单位)
  const formatMarketCap = (cap: number): string => {
    if (cap >= 1000) {
      return `${(cap / 1000).toFixed(1)}千亿`;
    } else if (cap >= 100) {
      return `${cap.toFixed(0)}亿`;
    } else if (cap >= 1) {
      return `${cap.toFixed(1)}亿`;
    } else {
      return `${(cap * 10000).toFixed(0)}万`;
    }
  };

  // 获取信号强度的样式
  const getSignalStyle = (strength?: string) => {
    switch (strength) {
      case 'strong':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'weak':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  // 获取风险等级样式
  const getRiskStyle = (level?: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  // 排序指示器组件
  const SortIndicator: React.FC<{ field: keyof StockResult }> = ({ field }) => (
    <span className="ml-1">
      {sortField === field ? (
        sortDirection === 'desc' ? '↓' : '↑'
      ) : (
        '↕'
      )}
    </span>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-gray-600">正在加载筛选结果...</p>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Filter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">暂无筛选结果</h3>
          <p className="text-gray-600">
            调整筛选条件后重新执行筛选
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        .results-table-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .results-table-scrollbar::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 4px;
        }
        .results-table-scrollbar::-webkit-scrollbar-thumb {
          background: #94a3b8;
          border-radius: 4px;
        }
        .results-table-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #64748b;
        }
      `}</style>
    <div className="flex flex-col h-full">
      {/* 表格头部信息 */}
      <div className="flex-shrink-0 p-4 bg-gray-50 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              {showStrategyColumns ? (
                <>
                  <Target className="w-5 h-5 text-purple-600" />
                  策略筛选结果
                </>
              ) : (
                <>
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                  基础筛选结果
                </>
              )}
            </h3>
            <span className="text-sm text-gray-600">
              共 {results.length} 只股票
            </span>
          </div>
          
        </div>
      </div>

      {/* 表格内容 */}
      <div className="flex-1 overflow-x-auto overflow-y-auto" ref={tableRef}>
        <div className="results-table-scrollbar">
          <table className="w-full">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('stock_code')}
              >
                股票代码
                <SortIndicator field="stock_code" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('stock_name')}
              >
                股票名称
                <SortIndicator field="stock_name" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('market')}
              >
                市场
                <SortIndicator field="market" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('consecutive_days')}
              >
                连续天数
                <SortIndicator field="consecutive_days" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('avg_rise_percent')}
              >
                平均涨幅
                <SortIndicator field="avg_rise_percent" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('close_price')}
              >
                收盘价格
                <SortIndicator field="close_price" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('avg_volume')}
              >
                平均成交量
                <SortIndicator field="avg_volume" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('market_cap')}
              >
                市值
                <SortIndicator field="market_cap" />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('turnover_rate')}
              >
                换手率
                <SortIndicator field="turnover_rate" />
              </th>
              {showStrategyColumns && (
                <>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('strategy_score')}
                  >
                    策略评分
                    <SortIndicator field="strategy_score" />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    信号强度
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    风险等级
                  </th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {currentPageData.map((stock, index) => (
              <tr key={`${stock.stock_code}-${index}`} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm font-medium text-blue-600">
                    {stock.stock_code}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div>
                    <span className="text-sm font-medium text-gray-900">
                      {stock.stock_name}
                    </span>
                    {stock.industry && (
                      <div className="text-xs text-gray-500">{stock.industry}</div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    stock.market === 'SH' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {stock.market}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {stock.consecutive_days} 天
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm font-medium text-red-600">
                    +{formatNumber(stock.avg_rise_percent)}%
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm font-medium text-gray-900">
                    ¥{formatNumber(stock.close_price, 2)}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {formatVolume(stock.avg_volume)}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {formatMarketCap(stock.market_cap)}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {stock.turnover_rate ? `${formatNumber(stock.turnover_rate, 2)}%` : 'N/A'}
                  </span>
                </td>
                {showStrategyColumns && (
                  <>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm font-medium text-blue-600">
                        {stock.strategy_score?.toFixed(1) || 'N/A'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        getSignalStyle(stock.signal_strength)
                      }`}>
                        {stock.signal_type === 'buy' ? '买入' : 
                         stock.signal_type === 'sell' ? '卖出' : '持有'} 
                        ({stock.signal_strength === 'strong' ? '强' :
                          stock.signal_strength === 'medium' ? '中' : '弱'})
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        getRiskStyle(stock.risk_level)
                      }`}>
                        {stock.risk_level === 'low' ? '低风险' :
                         stock.risk_level === 'medium' ? '中风险' : '高风险'}
                      </span>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      </div>

    </div>
    </>
  );
};

export default BasicResultsTable;