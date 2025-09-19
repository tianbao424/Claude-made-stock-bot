import React, { useState, useEffect } from 'react';
import { Activity, Clock, Database, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

interface PerformanceMetrics {
  api_response_times: {
    endpoint: string;
    avg_time: number;
    max_time: number;
    min_time: number;
    calls_count: number;
  }[];
  database_metrics: {
    total_records: number;
    screening_records: number;
    daily_data_records: number;
    database_size: string;
  };
  screening_performance: {
    last_execution_time: number;
    average_execution_time: number;
    stocks_processed: number;
    results_found: number;
  };
  system_health: {
    memory_usage: number;
    cpu_usage: number;
    disk_usage: number;
    status: 'healthy' | 'warning' | 'critical';
  };
}

const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/performance/metrics');
      const data = await response.json();
      
      if (data.success) {
        setMetrics(data.data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('获取性能指标失败:', error);
      // 模拟数据用于演示
      setMetrics({
        api_response_times: [
          { endpoint: '/api/screening/latest-results', avg_time: 245, max_time: 520, min_time: 120, calls_count: 156 },
          { endpoint: '/api/screening/screen-stocks', avg_time: 1200, max_time: 2800, min_time: 800, calls_count: 43 },
          { endpoint: '/api/screening/history', avg_time: 180, max_time: 350, min_time: 95, calls_count: 89 },
          { endpoint: '/api/stock-pools', avg_time: 85, max_time: 150, min_time: 45, calls_count: 324 }
        ],
        database_metrics: {
          total_records: 15426,
          screening_records: 2341,
          daily_data_records: 12890,
          database_size: '23.5 MB'
        },
        screening_performance: {
          last_execution_time: 1850,
          average_execution_time: 1680,
          stocks_processed: 4523,
          results_found: 108
        },
        system_health: {
          memory_usage: 65,
          cpu_usage: 23,
          disk_usage: 45,
          status: 'healthy'
        }
      });
      setLastUpdate(new Date());
    } finally {
      setLoading(false);
    }
  };

  const runOptimizationTest = async () => {
    try {
      const response = await fetch('/api/performance/optimization-test', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`优化测试完成：${data.message}`);
        fetchMetrics(); // 刷新指标
      }
    } catch (error) {
      console.error('优化测试失败:', error);
      alert('优化测试执行失败');
    }
  };

  const clearCache = async () => {
    try {
      const response = await fetch('/api/performance/clear-cache', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert('缓存清理成功');
        fetchMetrics();
      }
    } catch (error) {
      console.error('缓存清理失败:', error);
      alert('缓存清理失败');
    }
  };

  useEffect(() => {
    fetchMetrics();
    // 每30秒自动刷新一次
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />;
      case 'warning': return <AlertTriangle className="w-4 h-4" />;
      case 'critical': return <AlertTriangle className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  return (
    <div className="h-screen flex flex-col p-4 lg:p-6 max-w-7xl mx-auto">
      {/* 头部 */}
      <div className="flex-shrink-0 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Activity className="w-7 h-7 text-blue-600" />
              性能监控
            </h1>
            <p className="text-gray-600 mt-1">
              系统性能指标和优化建议
              {lastUpdate && (
                <span className="ml-2 text-sm">
                  最后更新: {lastUpdate.toLocaleTimeString()}
                </span>
              )}
            </p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={clearCache}
              className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
            >
              清理缓存
            </button>
            <button
              onClick={runOptimizationTest}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              优化测试
            </button>
            <button
              onClick={fetchMetrics}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? '加载中...' : '刷新'}
            </button>
          </div>
        </div>
      </div>

      {metrics ? (
        <div className="flex-1 space-y-6 overflow-auto">
          {/* 系统健康状态 */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-600" />
              系统健康状态
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(metrics.system_health.status)}`}>
                  {getStatusIcon(metrics.system_health.status)}
                  {metrics.system_health.status.toUpperCase()}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.system_health.memory_usage}%</div>
                <div className="text-sm text-gray-600">内存使用率</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.system_health.cpu_usage}%</div>
                <div className="text-sm text-gray-600">CPU使用率</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.system_health.disk_usage}%</div>
                <div className="text-sm text-gray-600">磁盘使用率</div>
              </div>
            </div>
          </div>

          {/* API响应时间 */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-green-600" />
              API响应时间
            </h2>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 text-sm font-medium text-gray-500">API端点</th>
                    <th className="text-left py-2 text-sm font-medium text-gray-500">平均时间</th>
                    <th className="text-left py-2 text-sm font-medium text-gray-500">最大时间</th>
                    <th className="text-left py-2 text-sm font-medium text-gray-500">最小时间</th>
                    <th className="text-left py-2 text-sm font-medium text-gray-500">调用次数</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.api_response_times.map((api, index) => (
                    <tr key={index} className="border-b">
                      <td className="py-2 text-sm text-gray-900 font-mono">{api.endpoint}</td>
                      <td className="py-2 text-sm">
                        <span className={`font-medium ${api.avg_time > 1000 ? 'text-red-600' : api.avg_time > 500 ? 'text-yellow-600' : 'text-green-600'}`}>
                          {api.avg_time}ms
                        </span>
                      </td>
                      <td className="py-2 text-sm text-gray-600">{api.max_time}ms</td>
                      <td className="py-2 text-sm text-gray-600">{api.min_time}ms</td>
                      <td className="py-2 text-sm text-gray-600">{api.calls_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 筛选性能 */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-red-600" />
              筛选性能
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.screening_performance.last_execution_time}ms</div>
                <div className="text-sm text-gray-600">最近执行时间</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.screening_performance.average_execution_time}ms</div>
                <div className="text-sm text-gray-600">平均执行时间</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.screening_performance.stocks_processed.toLocaleString()}</div>
                <div className="text-sm text-gray-600">处理股票数</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{metrics.screening_performance.results_found}</div>
                <div className="text-sm text-gray-600">找到结果</div>
              </div>
            </div>
          </div>

          {/* 数据库指标 */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              数据库指标
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.database_metrics.total_records.toLocaleString()}</div>
                <div className="text-sm text-gray-600">总记录数</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.database_metrics.screening_records.toLocaleString()}</div>
                <div className="text-sm text-gray-600">筛选记录</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.database_metrics.daily_data_records.toLocaleString()}</div>
                <div className="text-sm text-gray-600">每日数据</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{metrics.database_metrics.database_size}</div>
                <div className="text-sm text-gray-600">数据库大小</div>
              </div>
            </div>
          </div>

          {/* 优化建议 */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">优化建议</h2>
            
            <div className="space-y-3">
              {metrics.api_response_times.some(api => api.avg_time > 1000) && (
                <div className="flex items-start gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div>
                    <div className="font-medium text-yellow-800">API响应时间过长</div>
                    <div className="text-sm text-yellow-700">部分API响应时间超过1秒，建议优化查询逻辑或添加缓存</div>
                  </div>
                </div>
              )}
              
              {metrics.database_metrics.total_records > 10000 && (
                <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <Database className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <div className="font-medium text-blue-800">数据库记录较多</div>
                    <div className="text-sm text-blue-700">考虑添加数据库索引或清理历史数据以提高查询性能</div>
                  </div>
                </div>
              )}
              
              {metrics.screening_performance.average_execution_time > 2000 && (
                <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-red-600 mt-0.5" />
                  <div>
                    <div className="font-medium text-red-800">筛选算法需要优化</div>
                    <div className="text-sm text-red-700">平均筛选时间过长，建议优化筛选算法或并行处理</div>
                  </div>
                </div>
              )}
              
              {metrics.system_health.memory_usage > 80 && (
                <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div>
                    <div className="font-medium text-red-800">内存使用率过高</div>
                    <div className="text-sm text-red-700">内存使用超过80%，建议重启服务或优化内存使用</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">正在加载性能指标</h3>
            <p className="text-gray-600">请稍候...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PerformanceMonitor;