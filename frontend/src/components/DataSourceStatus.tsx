import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, Wifi, WifiOff } from 'lucide-react';

// 数据源状态接口
interface DataSourceInfo {
  available: boolean;
  last_check: string;
  error_message?: string;
  response_time_ms?: number;
}

interface DataSourceSummary {
  total_sources: number;
  available_sources: number;
  last_check: string;
  sources: Record<string, DataSourceInfo>;
}

// 数据源显示名称映射
const DATA_SOURCE_NAMES: Record<string, string> = {
  'eastmoney_a': '东方财富A股',
  'eastmoney_hk': '东方财富港股',
  'sina_a': '新浪A股',
  'sina_hk': '新浪港股', 
  'individual_em': '东方财富个股',
  'mock': '模拟数据'
};

// 数据源状态指示器组件
const DataSourceStatus: React.FC = () => {
  const [status, setStatus] = useState<DataSourceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取数据源状态
  const fetchDataSourceStatus = async () => {
    try {
      const response = await fetch('/api/data-sources/status');
      const result = await response.json();
      if (result.success) {
        setStatus(result.data);
      }
    } catch (error) {
      console.error('获取数据源状态失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载和自动刷新
  useEffect(() => {
    fetchDataSourceStatus();
    
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchDataSourceStatus, 30000); // 30秒刷新
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // 获取状态颜色
  const getStatusColor = (available: boolean, isSimulated: boolean = false) => {
    if (isSimulated) return 'text-yellow-500';
    return available ? 'text-green-500' : 'text-red-500';
  };

  // 获取状态图标
  const getStatusIcon = (available: boolean, isSimulated: boolean = false) => {
    if (isSimulated) return <Clock className="w-4 h-4" />;
    return available ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />;
  };

  // 格式化响应时间
  const formatResponseTime = (time?: number) => {
    if (!time) return '';
    if (time < 1000) return `${time}ms`;
    return `${(time / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span className="text-sm text-gray-600">检查数据源状态...</span>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
        <div className="flex items-center space-x-2">
          <WifiOff className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-600">无法获取数据源状态</span>
        </div>
      </div>
    );
  }

  const availabilityRate = Math.round((status.available_sources / status.total_sources) * 100);
  
  return (
    <div className="bg-white rounded-lg shadow mb-4">
      {/* 主状态栏 */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <Wifi className={`w-5 h-5 ${availabilityRate >= 50 ? 'text-green-500' : 'text-red-500'}`} />
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-900">数据源状态</span>
              <span className={`text-xs px-2 py-1 rounded-full ${
                availabilityRate >= 80 ? 'bg-green-100 text-green-700' :
                availabilityRate >= 50 ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                {status.available_sources}/{status.total_sources} 可用 ({availabilityRate}%)
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              最后检查: {new Date(status.last_check).toLocaleTimeString('zh-CN')}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setAutoRefresh(!autoRefresh);
            }}
            className={`text-xs px-2 py-1 rounded ${
              autoRefresh ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {autoRefresh ? '自动刷新' : '手动刷新'}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchDataSourceStatus();
            }}
            className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            立即刷新
          </button>
          <span className={`text-sm transform transition-transform ${expanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </div>

      {/* 详细状态 */}
      {expanded && (
        <div className="border-t border-gray-100 p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(status.sources).map(([sourceKey, sourceInfo]) => {
              const isSimulated = sourceKey === 'mock';
              return (
                <div
                  key={sourceKey}
                  className={`p-3 rounded-lg border ${
                    sourceInfo.available 
                      ? isSimulated 
                        ? 'border-yellow-200 bg-yellow-50' 
                        : 'border-green-200 bg-green-50'
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(sourceInfo.available, isSimulated)}
                      <span className="text-sm font-medium text-gray-900">
                        {DATA_SOURCE_NAMES[sourceKey] || sourceKey}
                      </span>
                    </div>
                    <span className={`text-xs ${getStatusColor(sourceInfo.available, isSimulated)}`}>
                      {sourceInfo.available ? '可用' : '不可用'}
                    </span>
                  </div>
                  
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>检查时间: {new Date(sourceInfo.last_check).toLocaleTimeString('zh-CN')}</div>
                    {sourceInfo.response_time_ms && (
                      <div>响应时间: {formatResponseTime(sourceInfo.response_time_ms)}</div>
                    )}
                    {sourceInfo.error_message && (
                      <div className="text-red-600 break-all">
                        错误: {sourceInfo.error_message.length > 40 
                          ? sourceInfo.error_message.substring(0, 40) + '...' 
                          : sourceInfo.error_message}
                      </div>
                    )}
                    {isSimulated && (
                      <div className="text-yellow-600">
                        💡 备用数据源，用于测试和兜底
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* 说明文字 */}
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <div className="text-xs text-blue-700">
              <strong>数据源说明:</strong>
              <ul className="mt-1 space-y-1 ml-4 list-disc">
                <li><strong>东方财富个股</strong>: 当前主要数据源，提供准确的A股数据</li>
                <li><strong>新浪数据</strong>: 备用数据源，响应速度快</li>
                <li><strong>模拟数据</strong>: 兜底方案，所有数据源失败时启用</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataSourceStatus;