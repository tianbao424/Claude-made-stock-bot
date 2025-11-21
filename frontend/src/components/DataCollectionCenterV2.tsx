import React, { useState, useEffect, useRef } from 'react';
import {
  Database, RefreshCw, Download, Upload, Settings, TrendingUp,
  AlertCircle, CheckCircle, Clock, Activity, BarChart3, 
  Wifi, WifiOff, Play, Pause, RotateCcw, Trash2,
  Info, Eye, Search, Calendar, Filter, Timer, Zap
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

const DataCollectionCenterV2: React.FC = () => {
  // 核心状态
  const [dataUpdateStatus, setDataUpdateStatus] = useState<DataUpdateStatus | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [marketCapStatus, setMarketCapStatus] = useState<MarketCapUpdateStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState<string | null>(null);
  
  // 活动标签
  const [activeTab, setActiveTab] = useState<'overview' | 'scheduler' | 'manual' | 'history'>('overview');
  
  // 操作日志
  const [operationLogs, setOperationLogs] = useState<Array<{
    timestamp: string;
    type: 'info' | 'success' | 'warning' | 'error';
    operation: string;
    message: string;
    duration?: number;
  }>>([]);
  
  // 自动刷新
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // 添加日志
  const addLog = (type: 'info' | 'success' | 'warning' | 'error', operation: string, message: string, duration?: number) => {
    const newLog = {
      timestamp: new Date().toLocaleTimeString(),
      type,
      operation,
      message,
      duration
    };
    setOperationLogs(prev => [newLog, ...prev.slice(0, 49)]); // 保留最新50条
  };

  // API调用函数
  const fetchDataUpdateStatus = async () => {
    try {
      const response = await fetch('/api/data-status/update-status');
      if (response.ok) {
        const result = await response.json();
        setDataUpdateStatus(result.data);
        return result.data;
      }
    } catch (error) {
      console.error('获取数据更新状态失败:', error);
    }
  };

  const fetchSchedulerStatus = async () => {
    try {
      const response = await fetch('/api/data-sync/scheduler-status');
      if (response.ok) {
        const result = await response.json();
        setSchedulerStatus(result.data);
        return result.data;
      }
    } catch (error) {
      console.error('获取调度器状态失败:', error);
    }
  };

  const fetchMarketCapStatus = async () => {
    try {
      const response = await fetch('/api/market-data/status-v2');
      if (response.ok) {
        const result = await response.json();
        setMarketCapStatus(result.data);
        return result.data;
      }
    } catch (error) {
      console.error('获取市值更新状态失败:', error);
    }
  };

  // 手动操作函数
  const performManualDataCollection = async () => {
    setOperationInProgress('collection');
    addLog('info', '数据收集', '开始手动执行股票数据收集...');
    
    try {
      const startTime = Date.now();
      const response = await fetch('/api/data-sync/manual/collection', {
        method: 'POST'
      });
      
      const duration = (Date.now() - startTime) / 1000;
      
      if (response.ok) {
        const result = await response.json();
        addLog('success', '数据收集', `收集完成: ${result.records_processed || '未知'}条记录`, duration);
        // 刷新状态
        await Promise.all([fetchDataUpdateStatus(), fetchSchedulerStatus()]);
      } else {
        addLog('error', '数据收集', '收集失败: 服务器响应异常', duration);
      }
    } catch (error) {
      addLog('error', '数据收集', `收集异常: ${error}`, 0);
    } finally {
      setOperationInProgress(null);
    }
  };

  const performManualStockScreening = async () => {
    setOperationInProgress('screening');
    addLog('info', '股票筛选', '开始手动执行强势股票筛选...');
    
    try {
      const startTime = Date.now();
      const response = await fetch('/api/data-sync/manual/screening', {
        method: 'POST'
      });
      
      const duration = (Date.now() - startTime) / 1000;
      
      if (response.ok) {
        const result = await response.json();
        addLog('success', '股票筛选', `筛选完成: ${result.records_processed || '未知'}只股票符合条件`, duration);
        await fetchSchedulerStatus();
      } else {
        addLog('error', '股票筛选', '筛选失败: 服务器响应异常', duration);
      }
    } catch (error) {
      addLog('error', '股票筛选', `筛选异常: ${error}`, 0);
    } finally {
      setOperationInProgress(null);
    }
  };

  const performMarketCapUpdate = async () => {
    setOperationInProgress('market_cap');
    addLog('info', '市值更新', '开始使用腾讯API更新市值和换手率数据...');
    
    try {
      const startTime = Date.now();
      const response = await fetch('/api/market-data/manual-update', {
        method: 'POST'
      });
      
      const duration = (Date.now() - startTime) / 1000;
      
      if (response.ok) {
        const result = await response.json();
        addLog('success', '市值更新', `更新完成: ${result.updated_count || '未知'}只股票`, duration);
        await Promise.all([fetchMarketCapStatus(), fetchDataUpdateStatus()]);
      } else {
        addLog('error', '市值更新', '更新失败: 服务器响应异常', duration);
      }
    } catch (error) {
      addLog('error', '市值更新', `更新异常: ${error}`, 0);
    } finally {
      setOperationInProgress(null);
    }
  };

  // 初始化和自动刷新
  useEffect(() => {
    const refreshData = async () => {
      setIsLoading(true);
      try {
        await Promise.all([
          fetchDataUpdateStatus(),
          fetchSchedulerStatus(),
          fetchMarketCapStatus()
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    refreshData();

    if (autoRefresh) {
      intervalRef.current = setInterval(refreshData, 30000); // 每30秒刷新
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  // 渲染数据概览面板
  const renderOverviewPanel = () => (
    <div className="space-y-6">
      {/* 数据新鲜度状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 数据更新状态 */}
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">数据更新状态</h3>
            <div className={`w-3 h-3 rounded-full ${
              dataUpdateStatus?.is_up_to_date ? 'bg-green-500' : 'bg-orange-500'
            }`} />
          </div>
          
          {dataUpdateStatus ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">最新数据日期:</span>
                <span className="font-medium">{dataUpdateStatus.latest_date}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">落后天数:</span>
                <span className={`font-medium ${
                  dataUpdateStatus.days_behind === 0 ? 'text-green-600' :
                  dataUpdateStatus.days_behind <= 1 ? 'text-orange-600' : 'text-red-600'
                }`}>
                  {dataUpdateStatus.days_behind}天
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">数据新鲜度:</span>
                <span className={`font-medium ${
                  dataUpdateStatus.data_freshness_score >= 90 ? 'text-green-600' :
                  dataUpdateStatus.data_freshness_score >= 70 ? 'text-orange-600' : 'text-red-600'
                }`}>
                  {dataUpdateStatus.data_freshness_score.toFixed(1)}%
                </span>
              </div>
              
              <div className="mt-4 text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {dataUpdateStatus.total_stocks.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">总股票数量</div>
              </div>
              
              {dataUpdateStatus.needs_update && (
                <div className="mt-3 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-700">
                  <AlertCircle className="w-4 h-4 inline mr-1" />
                  建议更新数据
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500">加载中...</div>
          )}
        </div>

        {/* 定时调度器状态 */}
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">调度器状态</h3>
            <div className={`w-3 h-3 rounded-full ${
              schedulerStatus?.is_running ? 'bg-green-500' : 'bg-red-500'
            }`} />
          </div>
          
          {schedulerStatus ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">运行状态:</span>
                <span className={`font-medium ${
                  schedulerStatus.is_running ? 'text-green-600' : 'text-red-600'
                }`}>
                  {schedulerStatus.is_running ? '运行中' : '已停止'}
                </span>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">今日数据收集:</span>
                  <StatusBadge status={schedulerStatus.today_collection_status} />
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">今日股票筛选:</span>
                  <StatusBadge status={schedulerStatus.today_screening_status} />
                </div>
              </div>
              
              <div className="mt-4 pt-3 border-t">
                <div className="text-sm text-gray-600 mb-2">执行时间</div>
                <div className="flex justify-between">
                  <span className="text-sm">数据收集: {schedulerStatus.collection_time}</span>
                  <span className="text-sm">股票筛选: {schedulerStatus.screening_time}</span>
                </div>
              </div>
              
              {schedulerStatus.next_scheduled_time && (
                <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
                  <Timer className="w-4 h-4 inline mr-1" />
                  下次执行: {new Date(schedulerStatus.next_scheduled_time).toLocaleString()}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500">加载中...</div>
          )}
        </div>

        {/* 市值数据状态 */}
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">市值数据状态</h3>
            <div className={`w-3 h-3 rounded-full ${
              marketCapStatus?.completion_rate > 80 ? 'bg-green-500' : 'bg-orange-500'
            }`} />
          </div>
          
          {marketCapStatus ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">数据完整率:</span>
                <span className={`font-medium ${
                  marketCapStatus.completion_rate >= 90 ? 'text-green-600' :
                  marketCapStatus.completion_rate >= 70 ? 'text-orange-600' : 'text-red-600'
                }`}>
                  {marketCapStatus.completion_rate.toFixed(1)}%
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">已更新股票:</span>
                <span className="font-medium">
                  {marketCapStatus.updated_stocks_count.toLocaleString()} / {marketCapStatus.total_stocks_count.toLocaleString()}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">数据源:</span>
                <span className="font-medium text-blue-600">{marketCapStatus.data_source}</span>
              </div>
              
              {marketCapStatus.last_update_time && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">最后更新:</span>
                  <span className="text-sm font-medium">
                    {new Date(marketCapStatus.last_update_time).toLocaleDateString()}
                  </span>
                </div>
              )}
              
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      marketCapStatus.completion_rate >= 90 ? 'bg-green-500' :
                      marketCapStatus.completion_rate >= 70 ? 'bg-orange-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${marketCapStatus.completion_rate}%` }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500">加载中...</div>
          )}
        </div>
      </div>

      {/* 快速操作区 */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">快速操作</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={performManualDataCollection}
            disabled={operationInProgress !== null}
            className="flex flex-col items-center gap-3 p-4 border-2 border-dashed border-blue-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center gap-2">
              {operationInProgress === 'collection' ? (
                <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
              ) : (
                <Download className="w-6 h-6 text-blue-600" />
              )}
              <span className="font-medium text-blue-900">收集当日股票数据</span>
            </div>
            <span className="text-sm text-blue-600 text-center">
              从AkShare获取所有股票的价格、成交量、涨跌幅等数据
            </span>
            {operationInProgress === 'collection' && (
              <span className="text-xs text-blue-500">执行中...</span>
            )}
          </button>
          
          <button
            onClick={performManualStockScreening}
            disabled={operationInProgress !== null}
            className="flex flex-col items-center gap-3 p-4 border-2 border-dashed border-green-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center gap-2">
              {operationInProgress === 'screening' ? (
                <RefreshCw className="w-6 h-6 text-green-600 animate-spin" />
              ) : (
                <TrendingUp className="w-6 h-6 text-green-600" />
              )}
              <span className="font-medium text-green-900">执行强势股筛选</span>
            </div>
            <span className="text-sm text-green-600 text-center">
              基于收集的数据执行股票筛选算法
            </span>
            {operationInProgress === 'screening' && (
              <span className="text-xs text-green-500">执行中...</span>
            )}
          </button>
          
          <button
            onClick={performMarketCapUpdate}
            disabled={operationInProgress !== null}
            className="flex flex-col items-center gap-3 p-4 border-2 border-dashed border-purple-300 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center gap-2">
              {operationInProgress === 'market_cap' ? (
                <RefreshCw className="w-6 h-6 text-purple-600 animate-spin" />
              ) : (
                <Zap className="w-6 h-6 text-purple-600" />
              )}
              <span className="font-medium text-purple-900">更新市值和换手率</span>
            </div>
            <span className="text-sm text-purple-600 text-center">
              使用腾讯API补充股票市值和换手率数据
            </span>
            {operationInProgress === 'market_cap' && (
              <span className="text-xs text-purple-500">执行中...</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  // 状态徽章组件
  const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const getStatusConfig = (status: string) => {
      switch (status) {
        case 'completed':
          return { color: 'text-green-600 bg-green-100', icon: CheckCircle, text: '已完成' };
        case 'in_progress':
          return { color: 'text-blue-600 bg-blue-100', icon: Activity, text: '进行中' };
        case 'failed':
          return { color: 'text-red-600 bg-red-100', icon: AlertCircle, text: '失败' };
        default:
          return { color: 'text-gray-600 bg-gray-100', icon: Clock, text: '未开始' };
      }
    };

    const config = getStatusConfig(status);
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3 h-3" />
        {config.text}
      </span>
    );
  };

  // 渲染操作日志
  const renderOperationLogs = () => (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium">操作日志</h4>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
              autoRefresh ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {autoRefresh ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            自动刷新
          </button>
          <button
            onClick={() => setOperationLogs([])}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-800"
          >
            <Trash2 className="w-3 h-3" />
            清空
          </button>
        </div>
      </div>
      
      <div className="h-64 overflow-y-auto space-y-1">
        {operationLogs.map((log, index) => (
          <div
            key={index}
            className={`text-xs px-3 py-2 rounded flex items-start gap-2 ${
              log.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
              log.type === 'warning' ? 'bg-yellow-50 text-yellow-700 border border-yellow-200' :
              log.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
              'bg-gray-50 text-gray-700 border border-gray-200'
            }`}
          >
            <span className="text-gray-500 flex-shrink-0 font-mono">{log.timestamp}</span>
            <div className="flex-1">
              <span className="font-medium">[{log.operation}]</span> {log.message}
              {log.duration && <span className="text-gray-500 ml-1">({log.duration.toFixed(1)}s)</span>}
            </div>
          </div>
        ))}
        {operationLogs.length === 0 && (
          <div className="text-center text-gray-500 text-sm py-8">
            暂无操作记录
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 标题栏 */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">数据采集中心</h1>
              <p className="text-gray-600">管理股票数据的采集、更新和质量监控</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* 状态指示器 */}
            {dataUpdateStatus && schedulerStatus && (
              <div className="flex items-center gap-4 px-4 py-2 bg-gray-100 rounded-lg">
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${
                    dataUpdateStatus.is_up_to_date ? 'bg-green-500' : 'bg-orange-500'
                  }`} />
                  <span className="text-sm text-gray-600">数据状态</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${
                    schedulerStatus.is_running ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <span className="text-sm text-gray-600">调度器</span>
                </div>
              </div>
            )}
            
            {/* 刷新按钮 */}
            <button
              onClick={() => {
                fetchDataUpdateStatus();
                fetchSchedulerStatus();
                fetchMarketCapStatus();
              }}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              刷新状态
            </button>
          </div>
        </div>
      </div>
      
      {/* 主内容区 */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex">
          {/* 左侧主要内容 */}
          <div className="flex-1 overflow-y-auto p-6">
            {renderOverviewPanel()}
          </div>
          
          {/* 右侧日志面板 */}
          <div className="w-80 border-l bg-gray-50 p-4">
            {renderOperationLogs()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataCollectionCenterV2;