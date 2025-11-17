import React, { useState, useEffect } from 'react';
import { Play, Filter, TrendingUp, Calendar, BarChart3, RefreshCw, AlertCircle, Target, Info } from 'lucide-react';
import Pagination from './Pagination';
import DataInitializationPanel from './DataInitializationPanel';
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
  close_price?: number;        // 添加收盘价
  turnover_rate?: number;      // 添加换手率  
  market_cap?: number;         // 添加市值
  pe_ratio?: number;           // 添加市盈率
  screening_date?: string;
  daily_changes?: any[];
  strategy_score?: number;
  signal_type?: string;
  signal_strength?: string;
  risk_level?: string;
  strategies_passed?: any[];
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
  
  // 策略配置状态
  const [appliedStrategies, setAppliedStrategies] = useState<any[]>([]);
  
  // 结果类型切换状态
  const [resultType, setResultType] = useState<'basic' | 'strategy'>('basic');
  
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

  // 获取最新筛选结果（基础筛选）
  const fetchLatestResults = async () => {
    setLoading(true);
    try {
      // 获取传统的筛选结果
      const response = await fetch('/api/screening/latest-results?screening_type=strong_rise_3d&limit=200');
      const data = await response.json();
      
      if (data.success) {
        setLatestResults(data.data);
        if (data.data.screening_date) {
          setMessage(`${data.message} - 数据日期: ${data.data.screening_date}`);
        } else {
          setMessage(data.message);
        }
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


  // 获取策略筛选结果
  const fetchStrategyResults = async () => {
    setLoading(true);
    console.log('🔄 开始获取策略筛选结果...');
    
    try {
      // 首先尝试从后端API获取最新的策略筛选结果
      console.log('📡 调用API: /api/advanced-screening/results');
      const response = await fetch('/api/advanced-screening/results?limit=200');
      
      if (response.ok) {
        const apiResult = await response.json();
        console.log('🔍 API返回结果:', apiResult);
        
        if (apiResult.success && apiResult.data && apiResult.data.length > 0) {
          console.log(`✅ API返回了 ${apiResult.data.length} 条策略筛选结果`);
          // 使用API返回的策略结果
          const convertedResults = apiResult.data.map((item: any) => ({
            stock_code: item.stock_code,
            stock_name: item.stock_name,
            market: item.market || (item.stock_code.startsWith('6') ? 'SH' : 'SZ'),
            consecutive_days: 1,
            avg_rise_percent: item.avg_rise_percent || 0,
            total_volume: item.total_volume || 100000,
            avg_volume: item.avg_volume || 100000,
            screening_date: item.screening_date,
            strategy_score: item.score || item.final_score || 0,
            signal_type: item.signal_type || 'buy',
            signal_strength: item.signal_strength || 'strong',
            risk_level: item.risk_level || 'medium',
            strategies_passed: item.strategy_results || []
          }));

          setLatestResults({
            screening_date: convertedResults[0]?.screening_date || new Date().toISOString().split('T')[0],
            screening_type: 'strategy_advanced',
            results: convertedResults
          });
          setMessage(`✨ 策略筛选结果 - 共 ${convertedResults.length} 只股票`);
          resetPagination();
          setLoading(false);
          return;
        }
      }
      
      // 如果API没有数据，再检查sessionStorage中是否有最新的策略结果
      console.log('📡 API无数据，检查sessionStorage...');
      const strategyResult = sessionStorage.getItem('latest_screening_result');
      console.log('🔍 sessionStorage数据:', strategyResult ? '有数据' : '无数据');
      
      if (strategyResult) {
        const result = JSON.parse(strategyResult);
        console.log('📋 解析sessionStorage数据:', result);
        
        if (result.success && result.data && result.data.results) {
          console.log(`✅ sessionStorage中有 ${result.data.results.length} 条策略筛选结果`);
          // 使用sessionStorage中的策略结果
          const convertedResults = result.data.results.map((item: any) => ({
            stock_code: item.stock_code,
            stock_name: item.stock_name,
            market: item.market || (item.stock_code.startsWith('6') ? 'SH' : 'SZ'),
            consecutive_days: 1,
            avg_rise_percent: item.avg_rise_percent || 0,
            total_volume: item.total_volume || 100000,
            avg_volume: item.avg_volume || 100000,
            screening_date: item.screening_date,
            strategy_score: item.weighted_score || 0,
            signal_type: 'buy',
            signal_strength: 'strong',
            risk_level: 'medium',
            strategies_passed: item.strategy_scores || []
          }));

          setLatestResults({
            screening_date: result.data.screening_date || new Date().toISOString().split('T')[0],
            screening_type: 'strategy_advanced',
            results: convertedResults
          });
          setMessage(`✨ 策略筛选结果 - 共 ${convertedResults.length} 只股票 (来自缓存)`);
          resetPagination();
          setLoading(false);
          return;
        }
      }
      
      // 如果都没有数据，提示用户先在策略中心应用策略
      setMessage('暂无策略筛选结果。请前往"策略中心"选择策略并点击"应用策略"。');
      setLatestResults({
        screening_date: new Date().toISOString().split('T')[0],
        screening_type: 'strategy_advanced',  
        results: []
      });
      resetPagination();
    } catch (error) {
      console.error('获取策略筛选结果失败:', error);
      setMessage('获取策略筛选结果失败，已切换回基础筛选');
      setResultType('basic');
      fetchLatestResults();
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
        // 立即刷新一次，然后等待3秒后再次刷新确保数据同步
        fetchLatestResults();
        setTimeout(() => {
          fetchLatestResults();
        }, 3000);
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
        // 使用API返回的实际数据日期
        setLatestResults({
          screening_date: data.data.screening_date,
          screening_type: criteria.screening_type,
          results: data.data.results
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

  // 处理结果类型切换
  const handleResultTypeChange = (type: 'basic' | 'strategy') => {
    setResultType(type);
    if (type === 'basic') {
      fetchLatestResults();
    } else {
      fetchStrategyResults();
    }
  };

  // 初始加载
  useEffect(() => {
    // 检查是否有来自策略中心的结果
    const strategyResult = sessionStorage.getItem('latest_screening_result');
    if (strategyResult) {
      setResultType('strategy');
      // 不在这里删除sessionStorage，让fetchStrategyResults处理
    } else {
      setResultType('basic');
    }
    
    // 根据默认类型加载数据
    if (strategyResult) {
      fetchStrategyResults();
    } else {
      fetchLatestResults();
    }
    
    // 加载应用的策略配置
    const savedConfigs = localStorage.getItem('applied_strategy_configs');
    console.log('🔍 检查本地存储的策略配置:', savedConfigs);
    
    if (savedConfigs) {
      try {
        const configs = JSON.parse(savedConfigs);
        console.log('📋 解析的策略配置:', configs);
        setAppliedStrategies(configs);
      } catch (error) {
        console.error('加载策略配置失败:', error);
      }
    } else {
      console.log('⚠️ 本地存储中没有找到策略配置');
    }
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
      {/* 头部 - 压缩高度 */}
      <div className="flex-shrink-0 mb-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Filter className="w-6 h-6 text-blue-600" />
              股票甄选
            </h1>
            <p className="text-gray-600 text-sm">智能筛选强势上涨股票 + 深度技术分析</p>
          </div>
          
          <div className="flex gap-3">
            {/* 结果类型切换按钮 */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => handleResultTypeChange('basic')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  resultType === 'basic'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                基础筛选
              </button>
              <button
                onClick={() => handleResultTypeChange('strategy')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  resultType === 'strategy'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                策略筛选
              </button>
            </div>
            
            <button
              onClick={resultType === 'basic' ? fetchLatestResults : fetchStrategyResults}
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
              onClick={handleManualTrigger}
              disabled={manualTriggerLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className={`w-4 h-4 ${manualTriggerLoading ? 'animate-spin' : ''}`} />
              {manualTriggerLoading ? '执行中...' : '手动筛选'}
            </button>
          </div>
        </div>
        
        {/* 当前应用策略显示 */}
        {appliedStrategies.length > 0 && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-sm font-medium text-blue-900 mb-2 flex items-center gap-2">
              <Target className="w-4 h-4" />
              当前应用的策略 ({appliedStrategies.length}个)
            </h3>
            <div className="flex flex-wrap gap-2">
              {appliedStrategies.map((strategy, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full border border-blue-300"
                >
                  {strategy.strategy_id.replace(/_/g, ' ')} 
                  {strategy.weight !== 1.0 && ` (权重: ${strategy.weight})`}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {/* 数据初始化面板 - 压缩间距 */}
        <div className="mt-2">
          <DataInitializationPanel />
        </div>
      </div>

      {/* 筛选条件设置 - 根据结果类型动态显示 */}
      {resultType === 'strategy' ? (
        /* 策略筛选结果 - 显示应用的策略和筛选条件 */
        <div className="flex-shrink-0 bg-white rounded-lg shadow-sm border p-3 mb-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="w-6 h-6 text-blue-600" />
            策略筛选配置
          </h2>
          
          {/* 应用的策略 */}
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">当前应用的策略</h3>
            <div className="flex flex-wrap gap-2">
              {appliedStrategies.map((strategy, index) => (
                <div key={index} className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                  <span className="font-medium text-blue-900">{strategy.strategy_id.replace(/_/g, ' ')}</span>
                  {strategy.weight !== 1.0 && (
                    <span className="text-blue-600 text-sm">权重: {strategy.weight}</span>
                  )}
                </div>
              ))}
              {appliedStrategies.length === 0 && (
                <div className="text-gray-500 italic">未检测到应用的策略，请在策略中心重新应用</div>
              )}
            </div>
          </div>
          
          {/* 筛选统计 */}
          {latestResults && latestResults.results.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-3 bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{latestResults.results.length}</div>
                <div className="text-sm text-gray-600">符合条件股票</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {latestResults.results.filter(r => (r.strategy_score || 0) > 70).length}
                </div>
                <div className="text-sm text-gray-600">高分推荐</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {new Set(latestResults.results.map(r => r.market)).size}
                </div>
                <div className="text-sm text-gray-600">覆盖市场</div>
              </div>
            </div>
          )}
          
          <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
            <Info className="w-4 h-4" />
            <span>这些结果来自策略中心的智能筛选。如需重新筛选，请返回"策略中心"重新配置并应用策略。</span>
          </div>
        </div>
      ) : (
        /* 传统筛选结果 - 显示筛选条件 */
        <div className="flex-shrink-0 bg-white rounded-lg shadow-sm border p-3 mb-2">
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
      )}

      {/* 状态信息栏 - 压缩显示 */}
      <div className="flex-shrink-0 mb-2 space-y-1">
        {/* 数据新鲜度和消息提示合并到一行 */}
        <div className="flex gap-2 text-xs">
          {latestResults?.screening_date && (
            <div className="bg-green-50 border border-green-200 rounded px-2 py-1 flex items-center gap-1">
              <Calendar className="w-3 h-3 text-green-600" />
              <span className="text-green-800 font-medium">
                数据日期: {latestResults.screening_date}
              </span>
            </div>
          )}
          
          {message && (
            <div className="bg-blue-50 border border-blue-200 rounded px-2 py-1 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 text-blue-600" />
              <span className="text-blue-800">{message}</span>
            </div>
          )}
        </div>

        {/* 获取筛选结果提示 */}
        <div className="bg-blue-50 border border-blue-200 rounded px-2 py-1 flex items-center gap-1">
          <Info className="w-3 h-3 text-blue-600" />
          <span className="text-blue-800 text-xs">
            获取到 {latestResults?.screening_date || '2025-10-29'} 的 {totalItems} 条最新筛选结果 - 数据日期: {latestResults?.screening_date || '2025-10-29'}
          </span>
        </div>

        {/* 筛选条件显示 */}
        <div className="bg-gray-50 border border-gray-200 rounded px-2 py-1 flex items-center gap-2 text-xs">
          <span className="text-gray-600">筛选条件: 连续 3 天涨幅超过 7%</span>
        </div>
      </div>

      {/* 筛选结果 - 增加最小高度确保表格显示 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden flex flex-col min-h-[400px]">
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

        <div className="flex-1 overflow-x-auto overflow-y-auto" style={{ maxHeight: 'calc(100vh - 350px)' }}>
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div className="text-center">
                <RefreshCw className="w-6 h-6 text-blue-600 animate-spin mx-auto mb-2" />
                <p className="text-gray-600 text-sm">正在加载筛选结果...</p>
              </div>
            </div>
          ) : latestResults?.results && latestResults.results.length > 0 ? (
            <div className="custom-scrollbar">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      股票代码
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      股票名称
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      市场
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {resultType === 'strategy' ? '策略评分' : '连续天数'}
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {resultType === 'strategy' ? '信号强度' : '平均涨幅'}
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {resultType === 'strategy' ? '风险等级' : '平均成交量'}
                    </th>
                    <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      深度分析
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentPageData.map((result, index) => (
                    <tr key={result.stock_code || index} className="hover:bg-gray-50">
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className="text-sm font-medium text-blue-600">
                          {result.stock_code}
                        </span>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {result.stock_name}
                        </span>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {result.market}
                        </span>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {resultType === 'strategy' ? (
                          <span className="text-sm font-medium text-blue-600">
                            {result.strategy_score?.toFixed(1) || 'N/A'}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-900">
                            {result.consecutive_days} 天
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {resultType === 'strategy' ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            result.signal_strength === 'strong' ? 'bg-green-100 text-green-800' :
                            result.signal_strength === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {result.signal_type === 'buy' ? '买入' : 
                             result.signal_type === 'sell' ? '卖出' : '持有'} 
                            ({result.signal_strength === 'strong' ? '强' :
                              result.signal_strength === 'medium' ? '中' : '弱'})
                          </span>
                        ) : (
                          <span className="text-sm font-medium text-red-600">
                            +{result.avg_rise_percent.toFixed(2)}%
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {resultType === 'strategy' ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            result.risk_level === 'low' ? 'bg-green-100 text-green-800' :
                            result.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {result.risk_level === 'low' ? '低风险' :
                             result.risk_level === 'medium' ? '中风险' : '高风险'}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-900">
                            {(result.avg_volume / 10000).toFixed(2)}万
                          </span>
                        )}
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
              {resultType === 'strategy' ? (
                <span>
                  来源：策略中心智能筛选 | 数据日期：{latestResults.screening_date}
                </span>
              ) : (
                <span>
                  筛选条件：连续 {criteria.min_consecutive_days} 天涨幅超过 {criteria.min_rise_percent}%
                </span>
              )}
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