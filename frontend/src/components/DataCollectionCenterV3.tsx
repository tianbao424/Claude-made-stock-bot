import React, { useState, useEffect, useRef } from 'react';
import {
  Database, RefreshCw, Download, Upload, Settings, TrendingUp,
  AlertCircle, CheckCircle, Clock, Activity, BarChart3, 
  Wifi, WifiOff, Play, Pause, RotateCcw, Trash2,
  Info, Eye, Search, Calendar, Filter, Timer, Zap, Plus,
  FileSearch, Layers, Target, Sparkles, Star
} from 'lucide-react';

// 数据更新状态
interface DataUpdateStatus {
  latest_date: string;
  today_date: string;
  days_behind: number;
  total_stocks: number;
  latest_records_count: number;
  is_up_to_date: boolean;
  needs_update: boolean;
  data_freshness_score: number;
}

// 定时调度器状态
interface SchedulerStatus {
  is_running: boolean;
  last_run_time: string | null;
  next_scheduled_time: string | null;
  today_collection_status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  today_screening_status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  collection_time: string; // "17:00"
  screening_time: string;  // "18:00"
}

// 手动操作结果
interface ManualOperationResult {
  success: boolean;
  message: string;
  records_processed: number;
  duration_seconds: number;
  timestamp: string;
}

// 市值更新状态
interface MarketCapUpdateStatus {
  last_update_time: string | null;
  updated_stocks_count: number;
  total_stocks_count: number;
  completion_rate: number;
  data_source: string;
  next_update_time: string | null;
}

// 股票信息更新状态 (新增)
interface StockInfoUpdateStatus {
  last_update_time: string | null;
  total_stocks_count: number;
  active_stocks_count: number;
  inactive_stocks_count: number;
  market_distribution: Record<string, number>;
  days_since_last_update: number;
  needs_update: boolean;
  last_scan_count: number;
}

// 统一数据采集状态 (新增)
interface UnifiedCollectionStatus {
  is_enabled: boolean;
  data_source: string;
  collection_method: string;
  auto_stock_discovery: boolean;
  last_discovery_time: string | null;
  new_stocks_found: number;
  updated_stocks: number;
}

const DataCollectionCenterV3: React.FC = () => {
  const [dataUpdateStatus, setDataUpdateStatus] = useState<DataUpdateStatus | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [marketCapStatus, setMarketCapStatus] = useState<MarketCapUpdateStatus | null>(null);
  const [stockInfoStatus, setStockInfoStatus] = useState<StockInfoUpdateStatus | null>(null);
  const [unifiedStatus, setUnifiedStatus] = useState<UnifiedCollectionStatus | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [operationLogs, setOperationLogs] = useState<string[]>([]);
  const [selectedOperation, setSelectedOperation] = useState<string>('');
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 刷新所有数据
  const refreshAllData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchDataUpdateStatus(),
        fetchSchedulerStatus(), 
        fetchMarketCapStatus(),
        fetchStockInfoStatus(),
        fetchUnifiedStatus()
      ]);
      addLog('📊 所有状态数据刷新完成');
    } catch (error) {
      addLog(`❌ 数据刷新失败: ${error}`);
    }
    setIsLoading(false);
  };

  // 获取数据更新状态
  const fetchDataUpdateStatus = async () => {
    try {
      const response = await fetch('/api/data-status/update-status');
      if (response.ok) {
        const data = await response.json();
        setDataUpdateStatus(data);
      }
    } catch (error) {
      console.error('获取数据更新状态失败:', error);
    }
  };

  // 获取调度器状态
  const fetchSchedulerStatus = async () => {
    try {
      const response = await fetch('/api/data-sync/scheduler-status');
      if (response.ok) {
        const data = await response.json();
        setSchedulerStatus(data);
      }
    } catch (error) {
      console.error('获取调度器状态失败:', error);
    }
  };

  // 获取市值数据状态
  const fetchMarketCapStatus = async () => {
    try {
      const response = await fetch('/api/market-data/status-v2');
      if (response.ok) {
        const data = await response.json();
        setMarketCapStatus(data);
      }
    } catch (error) {
      console.error('获取市值数据状态失败:', error);
    }
  };

  // 获取股票信息状态 (新增)
  const fetchStockInfoStatus = async () => {
    try {
      const response = await fetch('/api/stock-info/status');
      if (response.ok) {
        const data = await response.json();
        setStockInfoStatus(data);
      }
    } catch (error) {
      console.error('获取股票信息状态失败:', error);
    }
  };

  // 获取统一采集状态 (新增)
  const fetchUnifiedStatus = async () => {
    try {
      const response = await fetch('/api/unified-collection/status');
      if (response.ok) {
        const data = await response.json();
        setUnifiedStatus(data);
      }
    } catch (error) {
      console.error('获取统一采集状态失败:', error);
    }
  };

  // 手动数据收集
  const handleManualDataCollection = async () => {
    setSelectedOperation('数据收集');
    addLog('🚀 开始手动执行统一数据收集...');
    
    try {
      const response = await fetch('/api/data-sync/manual/collection', {
        method: 'POST'
      });
      
      const result: ManualOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 统一数据收集成功: ${result.records_processed} 条记录 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 统一数据收集失败: ${result.message}`);
      }
      
      // 刷新数据状态
      await refreshAllData();
    } catch (error) {
      addLog(`❌ 统一数据收集异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 手动股票筛选
  const handleManualScreening = async () => {
    setSelectedOperation('股票筛选');
    addLog('🔍 开始手动执行股票筛选...');
    
    try {
      const response = await fetch('/api/data-sync/manual/screening', {
        method: 'POST'
      });
      
      const result: ManualOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 股票筛选完成: 发现 ${result.records_processed} 只符合条件的股票`);
      } else {
        addLog(`❌ 股票筛选失败: ${result.message}`);
      }
      
      await refreshAllData();
    } catch (error) {
      addLog(`❌ 股票筛选异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 手动市值更新
  const handleManualMarketCapUpdate = async () => {
    setSelectedOperation('市值更新');
    addLog('💰 开始手动更新市值数据...');
    
    try {
      const response = await fetch('/api/market-data/manual-update', {
        method: 'POST'
      });
      
      const result: ManualOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 市值更新完成: ${result.records_processed} 只股票 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 市值更新失败: ${result.message}`);
      }
      
      await refreshAllData();
    } catch (error) {
      addLog(`❌ 市值更新异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 手动股票信息全量更新 (新增)
  const handleManualStockInfoUpdate = async () => {
    setSelectedOperation('股票信息更新');
    addLog('🔍 开始执行股票信息全量更新（预计10-15分钟）...');
    
    try {
      const response = await fetch('/api/stock-info/full-update', {
        method: 'POST'
      });
      
      const result: ManualOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 股票信息更新完成: 新增${result.records_processed}只股票 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 股票信息更新失败: ${result.message}`);
      }
      
      await refreshAllData();
    } catch (error) {
      addLog(`❌ 股票信息更新异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 强制统一数据采集 (新增)
  const handleForceUnifiedCollection = async () => {
    setSelectedOperation('强制采集');
    addLog('⚡ 开始强制统一数据采集（包含股票发现）...');
    
    try {
      const response = await fetch('/api/unified-collection/force-collect', {
        method: 'POST'
      });
      
      const result: ManualOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 强制采集完成: ${result.records_processed} 条记录 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 强制采集失败: ${result.message}`);
      }
      
      await refreshAllData();
    } catch (error) {
      addLog(`❌ 强制采集异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 添加日志
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit', 
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    const logMessage = `${timestamp} ${message}`;
    setOperationLogs(prev => [logMessage, ...prev.slice(0, 19)]);
  };

  // 清空日志
  const clearLogs = () => {
    setOperationLogs([]);
    addLog('🧹 操作日志已清空');
  };

  // 获取状态指示器
  const getStatusIndicator = (status: 'healthy' | 'warning' | 'error' | 'unknown') => {
    switch (status) {
      case 'healthy': return <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>;
      case 'warning': return <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>;
      case 'error': return <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>;
      default: return <div className="w-3 h-3 bg-gray-400 rounded-full"></div>;
    }
  };

  // 判断数据状态
  const getDataStatus = (): 'healthy' | 'warning' | 'error' | 'unknown' => {
    if (!dataUpdateStatus) return 'unknown';
    if (dataUpdateStatus.is_up_to_date) return 'healthy';
    if (dataUpdateStatus.days_behind <= 1) return 'warning';
    return 'error';
  };

  // 判断调度器状态
  const getSchedulerStatusLevel = (): 'healthy' | 'warning' | 'error' | 'unknown' => {
    if (!schedulerStatus) return 'unknown';
    if (schedulerStatus.is_running) return 'healthy';
    return 'error';
  };

  // 判断股票信息状态 (新增)
  const getStockInfoStatusLevel = (): 'healthy' | 'warning' | 'error' | 'unknown' => {
    if (!stockInfoStatus) return 'unknown';
    if (stockInfoStatus.needs_update) return 'warning';
    if (stockInfoStatus.days_since_last_update > 14) return 'error';
    return 'healthy';
  };

  // 自动刷新逻辑
  useEffect(() => {
    refreshAllData();
    
    if (autoRefresh) {
      intervalRef.current = setInterval(refreshAllData, 30000);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* 页面标题和控制栏 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">数据采集中心</h1>
                <p className="text-gray-600">管理票数据的采集、更新和质量监控（统一腾讯API）</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors ${
                  autoRefresh 
                    ? 'bg-green-100 text-green-700 border border-green-200' 
                    : 'bg-gray-100 text-gray-700 border border-gray-200'
                }`}
              >
                {autoRefresh ? <Eye className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                <span>{autoRefresh ? '自动刷新' : '手动刷新'}</span>
              </button>
              
              <button
                onClick={refreshAllData}
                disabled={isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                <span>刷新状态</span>
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* 左侧：状态监控区域 */}
          <div className="space-y-6">
            
            {/* 数据更新状态 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">数据更新状态</h2>
                {getStatusIndicator(getDataStatus())}
              </div>
              
              {dataUpdateStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">最新数据日期:</span>
                    <span className="font-mono text-lg font-semibold text-gray-900">
                      {dataUpdateStatus.latest_date}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">落后天数:</span>
                    <span className={`font-semibold ${dataUpdateStatus.days_behind === 0 ? 'text-green-600' : 'text-orange-600'}`}>
                      {dataUpdateStatus.days_behind}天
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">数据新鲜度:</span>
                    <span className={`font-semibold ${dataUpdateStatus.data_freshness_score >= 90 ? 'text-green-600' : 'text-orange-600'}`}>
                      {dataUpdateStatus.data_freshness_score.toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">
                        {dataUpdateStatus.total_stocks.toLocaleString()}
                      </div>
                      <div className="text-sm text-blue-600 font-medium">总股票数量</div>
                    </div>
                  </div>
                  
                  {dataUpdateStatus.needs_update && (
                    <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="flex items-center space-x-2 text-yellow-800">
                        <Info className="w-4 h-4" />
                        <span className="text-sm font-medium">建议更新数据</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              )}
            </div>

            {/* 股票信息状态 (新增) */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">股票信息状态</h2>
                {getStatusIndicator(getStockInfoStatusLevel())}
              </div>
              
              {stockInfoStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">活跃股票:</span>
                    <span className="font-semibold text-gray-900">
                      {stockInfoStatus.active_stocks_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">总股票数:</span>
                    <span className="font-semibold text-gray-900">
                      {stockInfoStatus.total_stocks_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">上次更新:</span>
                    <span className="text-sm text-gray-600">
                      {stockInfoStatus.last_update_time 
                        ? new Date(stockInfoStatus.last_update_time).toLocaleDateString() 
                        : '从未更新'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">距今天数:</span>
                    <span className={`font-semibold ${stockInfoStatus.days_since_last_update > 7 ? 'text-orange-600' : 'text-green-600'}`}>
                      {stockInfoStatus.days_since_last_update}天
                    </span>
                  </div>
                  
                  {/* 市场分布 */}
                  <div className="mt-4">
                    <div className="text-sm text-gray-600 mb-2">市场分布:</div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      {Object.entries(stockInfoStatus.market_distribution).map(([market, count]) => (
                        <div key={market} className="bg-gray-50 rounded px-2 py-1 text-center">
                          <div className="font-semibold">{market || '其他'}</div>
                          <div className="text-gray-600">{count}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {stockInfoStatus.needs_update && (
                    <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="flex items-center space-x-2 text-yellow-800">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">建议执行股票信息全量更新</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              )}
            </div>

            {/* 调度器状态 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">调度器状态</h2>
                {getStatusIndicator(getSchedulerStatusLevel())}
              </div>
              
              {schedulerStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">运行状态:</span>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      schedulerStatus.is_running ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {schedulerStatus.is_running ? '运行中' : '已停止'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">今日数据收集:</span>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      schedulerStatus.today_collection_status === 'completed' ? 'bg-green-100 text-green-800' :
                      schedulerStatus.today_collection_status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                      schedulerStatus.today_collection_status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {schedulerStatus.today_collection_status === 'completed' ? '已完成' :
                       schedulerStatus.today_collection_status === 'in_progress' ? '进行中' :
                       schedulerStatus.today_collection_status === 'failed' ? '失败' : '未开始'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">今日股票筛选:</span>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      schedulerStatus.today_screening_status === 'completed' ? 'bg-green-100 text-green-800' :
                      schedulerStatus.today_screening_status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                      schedulerStatus.today_screening_status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {schedulerStatus.today_screening_status === 'completed' ? '已完成' :
                       schedulerStatus.today_screening_status === 'in_progress' ? '进行中' :
                       schedulerStatus.today_screening_status === 'failed' ? '失败' : '未开始'}
                    </span>
                  </div>
                  
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                      <div className="text-sm text-blue-600 mb-1">执行时间</div>
                      <div className="font-semibold text-blue-800">
                        数据收集: {schedulerStatus.collection_time}
                      </div>
                      <div className="font-semibold text-blue-800">
                        股票筛选: {schedulerStatus.screening_time}
                      </div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3 border border-green-100">
                      <div className="text-sm text-green-600 mb-1">下次执行</div>
                      <div className="font-mono text-sm text-green-800">
                        {schedulerStatus.next_scheduled_time ? 
                          new Date(schedulerStatus.next_scheduled_time).toLocaleString('zh-CN', {
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          }) : '未安排'}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              )}
            </div>
          </div>

          {/* 右侧：操作和日志区域 */}
          <div className="space-y-6">
            
            {/* 统一数据采集状态 (新增) */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">统一采集状态</h2>
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  <span className="text-sm text-purple-600 font-medium">腾讯API</span>
                </div>
              </div>
              
              {unifiedStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">数据源:</span>
                    <span className="font-semibold text-purple-600">{unifiedStatus.data_source}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">采集方式:</span>
                    <span className="font-semibold text-gray-900">{unifiedStatus.collection_method}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">自动股票发现:</span>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${
                      unifiedStatus.auto_stock_discovery ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {unifiedStatus.auto_stock_discovery ? '已启用' : '已禁用'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">上次发现:</span>
                    <span className="text-sm text-gray-600">
                      {unifiedStatus.last_discovery_time 
                        ? new Date(unifiedStatus.last_discovery_time).toLocaleDateString() 
                        : '从未执行'}
                    </span>
                  </div>
                  
                  {(unifiedStatus.new_stocks_found > 0 || unifiedStatus.updated_stocks > 0) && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="text-sm text-green-800 space-y-1">
                        <div>🆕 新发现股票: {unifiedStatus.new_stocks_found} 只</div>
                        <div>🔄 更新股票: {unifiedStatus.updated_stocks} 只</div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              )}
            </div>

            {/* 快速操作 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">快速操作</h2>
              
              <div className="grid grid-cols-1 gap-3">
                
                {/* 统一数据收集 */}
                <button
                  onClick={handleManualDataCollection}
                  disabled={selectedOperation === '数据收集'}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white p-4 rounded-lg transition-colors flex items-center justify-center space-x-3"
                >
                  {selectedOperation === '数据收集' ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Download className="w-5 h-5" />
                  )}
                  <span className="font-medium">统一数据收集</span>
                  <span className="text-blue-200 text-sm">价格+市值+换手率</span>
                </button>

                {/* 股票信息全量更新 */}
                <button
                  onClick={handleManualStockInfoUpdate}
                  disabled={selectedOperation === '股票信息更新'}
                  className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white p-4 rounded-lg transition-colors flex items-center justify-center space-x-3"
                >
                  {selectedOperation === '股票信息更新' ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <FileSearch className="w-5 h-5" />
                  )}
                  <span className="font-medium">股票信息全量更新</span>
                  <span className="text-purple-200 text-sm">发现新股</span>
                </button>

                {/* 强制统一采集 */}
                <button
                  onClick={handleForceUnifiedCollection}
                  disabled={selectedOperation === '强制采集'}
                  className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white p-4 rounded-lg transition-colors flex items-center justify-center space-x-3"
                >
                  {selectedOperation === '强制采集' ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Zap className="w-5 h-5" />
                  )}
                  <span className="font-medium">强制统一采集</span>
                  <span className="text-orange-200 text-sm">含股票发现</span>
                </button>

                <div className="grid grid-cols-2 gap-3">
                  {/* 股票筛选 */}
                  <button
                    onClick={handleManualScreening}
                    disabled={selectedOperation === '股票筛选'}
                    className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white p-3 rounded-lg transition-colors flex items-center justify-center space-x-2"
                  >
                    {selectedOperation === '股票筛选' ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Target className="w-4 h-4" />
                    )}
                    <span className="font-medium">股票筛选</span>
                  </button>

                  {/* 市值更新 */}
                  <button
                    onClick={handleManualMarketCapUpdate}
                    disabled={selectedOperation === '市值更新'}
                    className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white p-3 rounded-lg transition-colors flex items-center justify-center space-x-2"
                  >
                    {selectedOperation === '市值更新' ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <TrendingUp className="w-4 h-4" />
                    )}
                    <span className="font-medium">市值更新</span>
                  </button>
                </div>
              </div>
            </div>

            {/* 操作日志 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">操作日志</h2>
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm text-gray-600">实时更新</span>
                  </div>
                  <button
                    onClick={clearLogs}
                    className="text-gray-400 hover:text-red-600 transition-colors"
                    title="清空日志"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto">
                {operationLogs.length > 0 ? (
                  <div className="space-y-1">
                    {operationLogs.map((log, index) => (
                      <div key={index} className="text-green-400 font-mono text-sm">
                        {log}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-center py-8 text-sm">
                    暂无操作记录
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataCollectionCenterV3;