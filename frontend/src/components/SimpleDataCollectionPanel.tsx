import React, { useState, useEffect } from 'react';
import {
  Database, RefreshCw, Download, TrendingUp,
  AlertCircle, CheckCircle, Activity, 
  Sparkles, FileSearch, Zap, Target,
  Info, Eye, Trash2
} from 'lucide-react';

// 简化的数据更新状态接口
interface SimpleDataStatus {
  latest_date: string;
  total_stocks: number;
  is_up_to_date: boolean;
  data_freshness_score: number;
}

// 简化的操作结果接口
interface SimpleOperationResult {
  success: boolean;
  message: string;
  records_processed: number;
  duration_seconds: number;
}

const SimpleDataCollectionPanel: React.FC = () => {
  const [dataStatus, setDataStatus] = useState<SimpleDataStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [operationLogs, setOperationLogs] = useState<string[]>([]);
  const [selectedOperation, setSelectedOperation] = useState<string>('');

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

  // 获取基本数据状态
  const fetchBasicStatus = async () => {
    try {
      const response = await fetch('/api/data-status/update-status');
      if (response.ok) {
        const data = await response.json();
        setDataStatus(data);
      }
    } catch (error) {
      console.error('获取数据状态失败:', error);
    }
  };

  // 手动数据收集
  const handleDataCollection = async () => {
    setSelectedOperation('数据收集');
    addLog('🚀 开始手动执行数据收集...');
    
    try {
      const response = await fetch('/api/data-sync/manual/collection', {
        method: 'POST'
      });
      
      const result: SimpleOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 数据收集成功: ${result.records_processed} 条记录 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 数据收集失败: ${result.message}`);
      }
    } catch (error) {
      addLog(`❌ 数据收集异常: ${error}`);
    }
    
    setSelectedOperation('');
    fetchBasicStatus();
  };

  // 手动股票筛选
  const handleStockScreening = async () => {
    setSelectedOperation('股票筛选');
    addLog('🔍 开始手动执行股票筛选...');
    
    try {
      const response = await fetch('/api/data-sync/manual/screening', {
        method: 'POST'
      });
      
      const result: SimpleOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 股票筛选完成: 发现 ${result.records_processed} 只符合条件的股票`);
      } else {
        addLog(`❌ 股票筛选失败: ${result.message}`);
      }
    } catch (error) {
      addLog(`❌ 股票筛选异常: ${error}`);
    }
    
    setSelectedOperation('');
  };

  // 市值更新
  const handleMarketCapUpdate = async () => {
    setSelectedOperation('市值更新');
    addLog('💰 开始手动更新市值数据...');
    
    try {
      const response = await fetch('/api/market-data/manual-update', {
        method: 'POST'
      });
      
      const result: SimpleOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 市值更新完成: ${result.records_processed} 只股票 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 市值更新失败: ${result.message}`);
      }
    } catch (error) {
      addLog(`❌ 市值更新异常: ${error}`);
    }
    
    setSelectedOperation('');
    fetchBasicStatus();
  };

  // 强制统一采集
  const handleForceCollection = async () => {
    setSelectedOperation('强制采集');
    addLog('⚡ 开始强制统一数据采集...');
    
    try {
      const response = await fetch('/api/unified-collection/force-collect', {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result: SimpleOperationResult = await response.json();
      
      if (result.success) {
        addLog(`✅ 强制采集完成: ${result.records_processed} 条记录 (${result.duration_seconds.toFixed(1)}s)`);
      } else {
        addLog(`❌ 强制采集失败: ${result.message}`);
      }
    } catch (error) {
      addLog(`❌ 强制采集异常: ${error}`);
    }
    
    setSelectedOperation('');
    fetchBasicStatus();
  };

  // 清空日志
  const clearLogs = () => {
    setOperationLogs([]);
    addLog('🧹 操作日志已清空');
  };

  // 刷新所有数据
  const refreshData = async () => {
    setIsLoading(true);
    try {
      await fetchBasicStatus();
      addLog('📊 数据状态刷新完成');
    } catch (error) {
      addLog(`❌ 数据刷新失败: ${error}`);
    }
    setIsLoading(false);
  };

  // 初始化
  useEffect(() => {
    refreshData();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* 页面标题 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">数据采集中心</h1>
                <p className="text-gray-600">管理股票数据的采集、更新和质量监控（统一腾讯API）</p>
              </div>
            </div>
            
            <button
              onClick={refreshData}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>刷新状态</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* 左侧：状态显示 */}
          <div className="space-y-6">
            
            {/* 数据状态卡片 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">数据更新状态</h2>
                <div className={`w-3 h-3 rounded-full ${
                  dataStatus?.is_up_to_date ? 'bg-green-500' : 'bg-orange-500'
                } animate-pulse`}></div>
              </div>
              
              {dataStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">最新数据日期:</span>
                    <span className="font-mono text-lg font-semibold text-gray-900">
                      {dataStatus.latest_date}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">数据新鲜度:</span>
                    <span className={`font-semibold ${
                      dataStatus.data_freshness_score >= 90 ? 'text-green-600' : 'text-orange-600'
                    }`}>
                      {dataStatus.data_freshness_score.toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">
                        {dataStatus.total_stocks.toLocaleString()}
                      </div>
                      <div className="text-sm text-blue-600 font-medium">总股票数量</div>
                    </div>
                  </div>
                  
                  {!dataStatus.is_up_to_date && (
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

            {/* 系统信息 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">系统信息</h2>
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-purple-500" />
                  <span className="text-sm text-purple-600 font-medium">腾讯API</span>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">数据源:</span>
                  <span className="font-semibold text-purple-600">腾讯财经API</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">采集方式:</span>
                  <span className="font-semibold text-gray-900">统一批量采集</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">自动发现:</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm font-medium">
                    已启用
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 右侧：操作和日志 */}
          <div className="space-y-6">
            
            {/* 快速操作 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">快速操作</h2>
              
              <div className="grid grid-cols-1 gap-3">
                
                <button
                  onClick={handleDataCollection}
                  disabled={selectedOperation === '数据收集'}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white p-4 rounded-lg transition-colors flex items-center justify-center space-x-3"
                >
                  {selectedOperation === '数据收集' ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Download className="w-5 h-5" />
                  )}
                  <span className="font-medium">统一数据收集</span>
                </button>

                <button
                  onClick={handleForceCollection}
                  disabled={selectedOperation === '强制采集'}
                  className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white p-4 rounded-lg transition-colors flex items-center justify-center space-x-3"
                >
                  {selectedOperation === '强制采集' ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Zap className="w-5 h-5" />
                  )}
                  <span className="font-medium">强制统一采集</span>
                </button>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handleStockScreening}
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

                  <button
                    onClick={handleMarketCapUpdate}
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
                <button
                  onClick={clearLogs}
                  className="text-gray-400 hover:text-red-600 transition-colors"
                  title="清空日志"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
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

export default SimpleDataCollectionPanel;