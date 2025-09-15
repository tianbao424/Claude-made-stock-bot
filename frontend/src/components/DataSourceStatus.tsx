import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, Wifi, WifiOff, TrendingUp } from 'lucide-react';
import { getMarketStatusSummary, getRecommendedCheckFrequency } from '../utils/marketHours';

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
  const [autoRefresh, setAutoRefresh] = useState(false); // 默认关闭自动刷新
  const [refreshInterval, setRefreshInterval] = useState(300000); // 5分钟间隔
  const [smartMode, setSmartMode] = useState(true); // 智能模式：根据市场状态调整

  // 获取数据源状态（不强制检查）
  const fetchDataSourceStatus = async (forceCheck: boolean = false) => {
    try {
      const url = forceCheck 
        ? '/api/data-sources/status?force_check=true' 
        : '/api/data-sources/status';
      
      console.log(`[DataSource] ${forceCheck ? '强制检查' : '获取缓存状态'} - ${url}`);
      
      const response = await fetch(url);
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

  // 主动检查数据源（强制重新检查）
  const checkDataSources = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/data-sources/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const result = await response.json();
      if (result.success) {
        setStatus(result.data);
      }
    } catch (error) {
      console.error('检查数据源失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取当前市场状态和推荐检查频率
  const getSmartRefreshConfig = () => {
    const marketStatus = getMarketStatusSummary();
    const recommendedConfig = getRecommendedCheckFrequency();
    
    return {
      marketStatus,
      interval: smartMode ? recommendedConfig.interval : refreshInterval,
      shouldAutoRefresh: smartMode ? recommendedConfig.shouldCheck : autoRefresh,
      description: recommendedConfig.description
    };
  };

  // 初始加载和智能自动刷新
  useEffect(() => {
    fetchDataSourceStatus();
    
    let interval: NodeJS.Timeout;
    let timeout: NodeJS.Timeout;
    
    const scheduleNextCheck = () => {
      const config = getSmartRefreshConfig();
      
      // 清除现有的定时器
      if (interval) clearInterval(interval);
      if (timeout) clearTimeout(timeout);
      
      if (smartMode) {
        if (config.shouldAutoRefresh) {
          if (config.interval > 0) {
            // 交易时间：使用间隔定时器，只获取状态不强制检查
            interval = setInterval(() => {
              const currentConfig = getSmartRefreshConfig();
              if (currentConfig.shouldAutoRefresh) {
                fetchDataSourceStatus(false); // 不强制检查，只获取缓存状态
              }
            }, config.interval);
          } else {
            // 关键时点：执行强制检查
            const isKeyTimePoint = config.description.includes('开盘前检查') || 
                                 config.description.includes('收盘后检查');
            
            if (isKeyTimePoint) {
              checkDataSources(); // 关键时点强制检查
            } else {
              fetchDataSourceStatus(false); // 其他时间只获取状态
            }
            
            // 调度下次检查
            if (config.description.includes('下次检查')) {
              const nextCheckTime = config.description.match(/(\d{2}:\d{2})/);
              if (nextCheckTime) {
                const [hours, minutes] = nextCheckTime[1].split(':').map(Number);
                const now = new Date();
                const nextCheck = new Date(now);
                nextCheck.setHours(hours, minutes, 0, 0);
                
                // 如果时间已过，调整为明天
                if (nextCheck <= now) {
                  nextCheck.setDate(nextCheck.getDate() + 1);
                }
                
                const msUntilNextCheck = nextCheck.getTime() - now.getTime();
                if (msUntilNextCheck > 0 && msUntilNextCheck < 24 * 60 * 60 * 1000) {
                  timeout = setTimeout(scheduleNextCheck, msUntilNextCheck);
                }
              }
            }
          }
        }
      } else {
        // 手动模式：只获取状态，不强制检查
        if (autoRefresh && refreshInterval > 0) {
          interval = setInterval(() => fetchDataSourceStatus(false), refreshInterval);
        }
      }
    };
    
    scheduleNextCheck();
    
    return () => {
      if (interval) clearInterval(interval);
      if (timeout) clearTimeout(timeout);
    };
  }, [autoRefresh, refreshInterval, smartMode]);

  // 定时更新市场状态（每分钟检查一次是否需要调整刷新策略）
  useEffect(() => {
    const marketStatusInterval = setInterval(() => {
      // 触发重新渲染以更新市场状态显示
      setExpanded(prev => prev);
    }, 60000); // 1分钟检查一次

    return () => clearInterval(marketStatusInterval);
  }, []);

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
  const smartConfig = getSmartRefreshConfig();
  const { marketStatus } = smartConfig;
  
  return (
    <div className="bg-white rounded-lg shadow mb-4">
      {/* 主状态栏 */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <div className="relative">
            <Wifi className={`w-5 h-5 ${availabilityRate >= 50 ? 'text-green-500' : 'text-red-500'}`} />
            {marketStatus.anyMarketOpen && (
              <TrendingUp className="w-3 h-3 text-green-500 absolute -top-1 -right-1 animate-pulse" />
            )}
          </div>
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
              {/* 市场状态指示器 */}
              <span className={`text-xs px-2 py-1 rounded-full ${
                marketStatus.anyMarketOpen 
                  ? 'bg-green-100 text-green-700' 
                  : marketStatus.isWeekday && !marketStatus.isHoliday
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600'
              }`}>
                {marketStatus.anyMarketOpen ? '🔴 交易中' : 
                 marketStatus.isWeekday && !marketStatus.isHoliday ? '⏰ 休市' : '🏖️ 休息日'}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              最后检查: {new Date(status.last_check).toLocaleTimeString('zh-CN')}
              {smartMode && (
                <span className="ml-2 text-blue-600">
                  • {smartConfig.description}
                  {smartConfig.marketStatus.recommendedFrequency.nextCheckTime && (
                    <span className="ml-1 text-green-600">
                      (下次: {new Date(smartConfig.marketStatus.recommendedFrequency.nextCheckTime).toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })})
                    </span>
                  )}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSmartMode(!smartMode);
            }}
            className={`text-xs px-2 py-1 rounded ${
              smartMode ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {smartMode ? '🧠 智能模式' : '⚙️ 手动模式'}
          </button>
          
          {!smartMode && (
            <>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="text-xs px-2 py-1 rounded border border-gray-200"
                onClick={(e) => e.stopPropagation()}
              >
                <option value={60000}>1分钟</option>
                <option value={300000}>5分钟</option>
                <option value={600000}>10分钟</option>
                <option value={1800000}>30分钟</option>
              </select>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setAutoRefresh(!autoRefresh);
                }}
                className={`text-xs px-2 py-1 rounded ${
                  autoRefresh ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {autoRefresh ? '自动刷新' : '手动模式'}
              </button>
            </>
          )}
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              checkDataSources(); // 使用强制检查
            }}
            className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
            disabled={loading}
          >
            {loading ? '检查中...' : '立即检查'}
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
          
          {/* 市场状态和说明 */}
          <div className="mt-4 space-y-3">
            {/* 市场状态详情 */}
            <div className={`p-3 rounded-lg ${
              marketStatus.anyMarketOpen 
                ? 'bg-green-50 border border-green-200' 
                : 'bg-blue-50 border border-blue-200'
            }`}>
              <div className={`text-xs font-medium ${
                marketStatus.anyMarketOpen ? 'text-green-800' : 'text-blue-800'
              }`}>
                📈 市场状态
              </div>
              <div className={`text-xs mt-1 ${
                marketStatus.anyMarketOpen ? 'text-green-700' : 'text-blue-700'
              }`}>
                • A股: {marketStatus.aStockOpen ? '🔴 交易中 (9:30-11:30, 13:00-15:00)' : '⏸️ 休市'}
                <br />
                • 港股: {marketStatus.hkStockOpen ? '🔴 交易中 (9:30-12:00, 13:00-16:00)' : '⏸️ 休市'}
                <br />
                • 智能检查: {smartConfig.description}
              </div>
            </div>

            {/* 数据源说明 */}
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-700">
                <strong>📡 数据源说明:</strong>
                <ul className="mt-1 space-y-1 ml-4 list-disc">
                  <li><strong>东方财富个股</strong>: 主要数据源，提供准确的A股数据</li>
                  <li><strong>新浪数据</strong>: 备用数据源，响应速度快</li>
                  <li><strong>模拟数据</strong>: 兜底方案，所有数据源失败时启用</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataSourceStatus;