import React, { useState, useEffect } from 'react';
import { Play, Filter, TrendingUp, Calendar, BarChart3, RefreshCw, AlertCircle, Target, Info } from 'lucide-react';
import Pagination from './Pagination';
import { deepAnalysisAPI, autoPoolAPI } from '../services/api';

interface ScreeningResult {
  id?: number;
  stock_code: string;
  stock_name: string;
  market: string;
  consecutive_days: number;
  avg_rise_percent: number;
  total_volume: number;
  avg_volume: number;
  screening_date?: string;
  daily_changes?: any[];
}

interface ScreeningCriteria {
  screening_type: string;
  min_consecutive_days: number;
  min_rise_percent: number;
  min_volume: number;
  market_filter: string[];
  screening_date?: string;
}

interface LatestResultsData {
  screening_date: string | null;
  screening_type: string;
  results: ScreeningResult[];
}

const StockScreeningDashboard: React.FC = () => {
  const [latestResults, setLatestResults] = useState<LatestResultsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [manualTriggerLoading, setManualTriggerLoading] = useState(false);
  const [initDataLoading, setInitDataLoading] = useState(false);
  const [criteria, setCriteria] = useState<ScreeningCriteria>({
    screening_type: 'strong_rise_3d',
    min_consecutive_days: 3,
    min_rise_percent: 7.0,
    min_volume: 0,
    market_filter: ['SH', 'SZ']
  });
  const [message, setMessage] = useState<string>('');
  
  // 深度分析相关状态
  const [deepAnalysisLoading, setDeepAnalysisLoading] = useState<string[]>([]);
  const [autoPoolProcessing, setAutoPoolProcessing] = useState(false);
  const [showAnalysisInfo, setShowAnalysisInfo] = useState(false);
  
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // 计算分页数据
  const totalItems = latestResults?.results?.length || 0;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentPageData = latestResults?.results?.slice(startIndex, endIndex) || [];

  // 重置分页
  const resetPagination = () => {
    setCurrentPage(1);
  };

  // 获取最新筛选结果
  const fetchLatestResults = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/screening/latest-results?screening_type=strong_rise_3d&limit=200');
      const data = await response.json();
      
      if (data.success) {
        setLatestResults(data.data);
        setMessage(data.message);
        resetPagination();
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

  // 手动触发筛选（使用当前界面条件）
  const handleManualTrigger = async () => {
    setManualTriggerLoading(true);
    try {
      const response = await fetch('/api/screening/manual-trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(criteria)  // 发送当前界面的筛选条件
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

  // 初始化历史数据
  const handleInitHistoricalData = async () => {
    setInitDataLoading(true);
    try {
      const response = await fetch('/api/screening/init-historical-data?days=7', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      const data = await response.json();
      
      if (data.success) {
        setMessage(`历史数据初始化完成，共收集 ${data.data.total_records} 条记录`);
      } else {
        setMessage('历史数据初始化失败');
      }
    } catch (error) {
      console.error('历史数据初始化失败:', error);
      setMessage('历史数据初始化失败');
    } finally {
      setInitDataLoading(false);
    }
  };

  // 执行自定义筛选
  const handleCustomScreening = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/screening/screen-stocks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(criteria)
      });
      const data = await response.json();
      
      if (data.success) {
        // 将自定义筛选结果转换为最新结果格式
        setLatestResults({
          screening_date: new Date().toISOString().split('T')[0],
          screening_type: criteria.screening_type,
          results: data.data
        });
        setMessage(data.message);
        resetPagination();
      } else {
        setMessage('自定义筛选失败');
      }
    } catch (error) {
      console.error('自定义筛选失败:', error);
      setMessage('自定义筛选失败');
    } finally {
      setLoading(false);
    }
  };

  // 监听预设应用事件
  useEffect(() => {
    const handleApplyPreset = (event: any) => {
      const presetCriteria = event.detail;
      setCriteria({
        screening_type: presetCriteria.screening_type || 'strong_rise_3d',
        min_consecutive_days: presetCriteria.min_consecutive_days,
        min_rise_percent: presetCriteria.min_rise_percent,
        min_volume: presetCriteria.min_volume,
        market_filter: presetCriteria.market_filter
      });
    };

    window.addEventListener('applyScreeningPreset', handleApplyPreset);
    return () => {
      window.removeEventListener('applyScreeningPreset', handleApplyPreset);
    };
  }, []);

  // 深度分析单只股票
  const handleSingleDeepAnalysis = async (stockCode: string) => {
    setDeepAnalysisLoading(prev => [...prev, stockCode]);
    try {
      await deepAnalysisAPI.analyze({
        stock_codes: [stockCode],
        save_results: true
      });
      setMessage(`股票 ${stockCode} 深度分析完成`);
    } catch (error) {
      console.error('深度分析失败:', error);
      setMessage(`股票 ${stockCode} 深度分析失败`);
    } finally {
      setDeepAnalysisLoading(prev => prev.filter(code => code !== stockCode));
    }
  };

  // 批量深度分析
  const handleBatchDeepAnalysis = async () => {
    if (!latestResults?.results || latestResults.results.length === 0) {
      setMessage('没有筛选结果可以分析');
      return;
    }

    setDeepAnalysisLoading(prev => [...prev, 'batch']);
    try {
      const stockCodes = latestResults.results.map(result => result.stock_code);
      await deepAnalysisAPI.analyze({
        stock_codes: stockCodes,
        save_results: true
      });
      setMessage(`批量深度分析完成，共分析 ${stockCodes.length} 只股票`);
    } catch (error) {
      console.error('批量深度分析失败:', error);
      setMessage('批量深度分析失败');
    } finally {
      setDeepAnalysisLoading(prev => prev.filter(code => code !== 'batch'));
    }
  };

  // 自动处理筛选结果（深度分析+自动添加）
  const handleAutoProcessScreening = async () => {
    setAutoPoolProcessing(true);
    try {
      const result = await autoPoolAPI.processScreening();
      setMessage(`自动处理完成！分析了 ${result.total_analyzed} 只股票，添加了 ${result.added_to_pool} 只到关注池`);
    } catch (error) {
      console.error('自动处理失败:', error);
      setMessage('自动处理筛选结果失败');
    } finally {
      setAutoPoolProcessing(false);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchLatestResults();
  }, []);

  return (
    <>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #94a3b8;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #64748b;
        }
        .custom-scrollbar::-webkit-scrollbar-corner {
          background: #f1f5f9;
        }
      `}</style>
      <div className="h-screen flex flex-col p-3 lg:p-4 max-w-7xl mx-auto">
      {/* 头部 */}
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Filter className="w-7 h-7 text-blue-600" />
              股票甄选
            </h1>
            <p className="text-gray-600 mt-1">智能筛选强势上涨股票 + 深度技术分析</p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={fetchLatestResults}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新结果
            </button>
            
            <button
              onClick={handleAutoProcessScreening}
              disabled={autoPoolProcessing}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Target className={`w-4 h-4 ${autoPoolProcessing ? 'animate-spin' : ''}`} />
              {autoPoolProcessing ? '智能处理中...' : '智能分析'}
            </button>
            
            <button
              onClick={handleBatchDeepAnalysis}
              disabled={deepAnalysisLoading.includes('batch') || !latestResults?.results?.length}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <TrendingUp className={`w-4 h-4 ${deepAnalysisLoading.includes('batch') ? 'animate-spin' : ''}`} />
              {deepAnalysisLoading.includes('batch') ? '深度分析中...' : '批量分析'}
            </button>
            
            <button
              onClick={handleInitHistoricalData}
              disabled={initDataLoading}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${initDataLoading ? 'animate-spin' : ''}`} />
              {initDataLoading ? '初始化中...' : '初始化数据'}
            </button>
            
            <button
              onClick={handleManualTrigger}
              disabled={manualTriggerLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className={`w-4 h-4 ${manualTriggerLoading ? 'animate-spin' : ''}`} />
              {manualTriggerLoading ? '执行中...' : '手动筛选'}
            </button>
          </div>
        </div>
      </div>

      {/* 筛选条件设置 */}
      <div className="flex-shrink-0 bg-white rounded-lg shadow-sm border p-3 mb-4">
        <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-green-600" />
          筛选条件
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              连续天数
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={criteria.min_consecutive_days}
              onChange={(e) => setCriteria({
                ...criteria,
                min_consecutive_days: parseInt(e.target.value) || 3
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              最小涨幅 (%)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              step="0.1"
              value={criteria.min_rise_percent}
              onChange={(e) => setCriteria({
                ...criteria,
                min_rise_percent: parseFloat(e.target.value) || 7.0
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              市场选择
            </label>
            <select
              value={criteria.market_filter.join(',')}
              onChange={(e) => setCriteria({
                ...criteria,
                market_filter: e.target.value.split(',').filter(m => m)
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="SH,SZ">A股 (沪深)</option>
              <option value="SH">上海A股</option>
              <option value="SZ">深圳A股</option>
              <option value="HK">港股</option>
              <option value="SH,SZ,HK">全市场</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleCustomScreening}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Filter className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              自定义筛选
            </button>
          </div>
        </div>
      </div>

      {/* 消息提示 */}
      {message && (
        <div className="flex-shrink-0 mb-2">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span className="text-blue-800 text-sm">{message}</span>
          </div>
        </div>
      )}

      {/* 深度分析功能说明 - 可折叠 */}
      <div className="flex-shrink-0 mb-2">
        <div className="bg-purple-50 border border-purple-200 rounded-lg">
          <button
            onClick={() => setShowAnalysisInfo(!showAnalysisInfo)}
            className="w-full p-2 flex items-center justify-between hover:bg-purple-100 transition-colors rounded-lg"
          >
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-800">深度分析功能</span>
            </div>
            <Info className={`w-4 h-4 text-purple-600 transform transition-transform ${showAnalysisInfo ? 'rotate-180' : ''}`} />
          </button>
          {showAnalysisInfo && (
            <div className="px-2 pb-2">
              <div className="text-xs text-purple-700 space-y-1">
                <div>• <span className="font-medium">智能分析</span>：自动识别低波动突破模式并添加到关注池</div>
                <div>• <span className="font-medium">批量分析</span>：对所有筛选结果进行深度技术分析</div>
                <div>• <span className="font-medium">单股分析</span>：点击表格中的"深度分析"按钮分析单只股票</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 筛选结果 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden flex flex-col">
        <div className="p-3 border-b bg-gray-50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-red-600" />
              筛选结果
            </h2>
            {latestResults?.screening_date && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Calendar className="w-4 h-4" />
                {latestResults.screening_date}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-x-auto overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
                <p className="text-gray-600">正在加载筛选结果...</p>
              </div>
            </div>
          ) : latestResults?.results && latestResults.results.length > 0 ? (
            <div className="custom-scrollbar">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      股票代码
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      股票名称
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      市场
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      连续天数
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      平均涨幅
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      平均成交量
                    </th>
                    <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      深度分析
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentPageData.map((result, index) => (
                    <tr key={result.stock_code || index} className="hover:bg-gray-50">
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm font-medium text-blue-600">
                          {result.stock_code}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {result.stock_name}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {result.market}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {result.consecutive_days} 天
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm font-medium text-red-600">
                          +{result.avg_rise_percent.toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {(result.avg_volume / 10000).toFixed(2)}万
                        </span>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-center">
                        <button
                          onClick={() => handleSingleDeepAnalysis(result.stock_code)}
                          disabled={deepAnalysisLoading.includes(result.stock_code)}
                          className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-purple-600 bg-purple-100 rounded-full hover:bg-purple-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          <Target className={`w-3 h-3 ${deepAnalysisLoading.includes(result.stock_code) ? 'animate-spin' : ''}`} />
                          {deepAnalysisLoading.includes(result.stock_code) ? '分析中' : '深度分析'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Filter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">暂无筛选结果</h3>
                <p className="text-gray-600 mb-4">
                  尝试调整筛选条件或点击"手动筛选"来获取最新数据
                </p>
                <button
                  onClick={handleManualTrigger}
                  disabled={manualTriggerLoading}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Play className={`w-4 h-4 ${manualTriggerLoading ? 'animate-spin' : ''}`} />
                  {manualTriggerLoading ? '执行中...' : '开始筛选'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 底部统计信息 */}
        {latestResults?.results && latestResults.results.length > 0 && (
          <div className="flex-shrink-0 p-3 bg-gray-50 border-t text-sm text-gray-600">
            <div className="flex items-center justify-between">
              <span>
                共找到 <span className="font-medium text-gray-900">{latestResults.results.length}</span> 只符合条件的股票
              </span>
              <span>
                筛选条件：连续 {criteria.min_consecutive_days} 天涨幅超过 {criteria.min_rise_percent}%
              </span>
            </div>
          </div>
        )}
      </div>
      
      {/* 分页控件 - 独立显示 */}
      {latestResults?.results && latestResults.results.length > 0 && (
        <div className="flex-shrink-0 mt-2 bg-white rounded-lg shadow-sm border p-3">
          <div className="flex items-center justify-between flex-wrap gap-4">
            {/* 左侧：每页条数和统计信息 */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700">每页显示</label>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <span className="text-sm text-gray-700">条</span>
              </div>
              
              <div className="text-sm text-gray-600">
                显示第 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, totalItems)} 条，共 {totalItems} 条
              </div>
            </div>

            {/* 右侧：分页按钮 */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded-l bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map(pageNum => (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-3 py-1 text-sm border-t border-b border-r border-gray-300 ${
                    pageNum === currentPage
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white hover:bg-gray-50'
                  }`}
                >
                  {pageNum}
                </button>
              ))}
              
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage >= totalPages}
                className="px-3 py-1 text-sm border border-gray-300 rounded-r bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      )}

      </div>
    </>
  );
};

export default StockScreeningDashboard;