import React, { useState, useEffect } from 'react';
import { Clock, Filter, TrendingUp, Calendar, RefreshCw, Eye, Trash2 } from 'lucide-react';

interface HistoryRecord {
  id: number;
  screening_date: string;
  screening_type: string;
  criteria_met: string;
  result_count: number;
  created_at: string;
}

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
}

const ScreeningHistory: React.FC = () => {
  const [historyRecords, setHistoryRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<HistoryRecord | null>(null);
  const [selectedResults, setSelectedResults] = useState<ScreeningResult[]>([]);
  const [showResults, setShowResults] = useState(false);

  // 获取筛选历史记录
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/screening/history?limit=50');
      const data = await response.json();
      
      if (data.success) {
        // 按日期分组统计历史记录
        const groupedData = data.data.reduce((acc: any, record: any) => {
          const key = `${record.screening_date}_${record.screening_type}`;
          if (!acc[key]) {
            acc[key] = {
              id: record.id,
              screening_date: record.screening_date,
              screening_type: record.screening_type,
              criteria_met: record.criteria_met,
              result_count: 0,
              created_at: record.created_at
            };
          }
          acc[key].result_count++;
          return acc;
        }, {});
        
        setHistoryRecords(Object.values(groupedData));
      }
    } catch (error) {
      console.error('获取筛选历史失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取特定历史记录的详细结果
  const fetchHistoryResults = async (record: HistoryRecord) => {
    try {
      const response = await fetch(`/api/screening/history-results?date=${record.screening_date}&type=${record.screening_type}`);
      const data = await response.json();
      
      if (data.success) {
        setSelectedResults(data.data);
        setSelectedRecord(record);
        setShowResults(true);
      }
    } catch (error) {
      console.error('获取历史结果失败:', error);
    }
  };

  // 删除历史记录
  const deleteHistory = async (record: HistoryRecord) => {
    if (!confirm('确定要删除这条历史记录吗？')) return;
    
    try {
      const response = await fetch(`/api/screening/history/${record.id}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        fetchHistory(); // 刷新列表
      }
    } catch (error) {
      console.error('删除历史记录失败:', error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const parseCriteria = (criteriaStr: string) => {
    try {
      const criteria = JSON.parse(criteriaStr);
      return `连续${criteria.min_consecutive_days}天涨幅超过${criteria.min_rise_percent}%`;
    } catch {
      return '筛选条件解析失败';
    }
  };

  return (
    <div className="h-screen flex flex-col p-4 lg:p-6 max-w-7xl mx-auto">
      {/* 头部 */}
      <div className="flex-shrink-0 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Clock className="w-7 h-7 text-blue-600" />
              筛选历史
            </h1>
            <p className="text-gray-600 mt-1">查看历史筛选记录和结果</p>
          </div>
          
          <button
            onClick={fetchHistory}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* 历史记录列表 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden">
        <div className="p-4 border-b bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Filter className="w-5 h-5 text-green-600" />
            历史记录
          </h2>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
                <p className="text-gray-600">正在加载历史记录...</p>
              </div>
            </div>
          ) : historyRecords.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      筛选日期
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      筛选类型
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      筛选条件
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      结果数量
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {historyRecords.map((record, index) => (
                    <tr key={record.id || index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 text-blue-500 mr-2" />
                          <span className="text-sm font-medium text-gray-900">
                            {formatDate(record.screening_date)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          强势股筛选
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {parseCriteria(record.criteria_met)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center">
                          <TrendingUp className="w-4 h-4 text-red-500 mr-1" />
                          <span className="text-sm font-medium text-red-600">
                            {record.result_count} 只
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-500">
                          {formatDateTime(record.created_at)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => fetchHistoryResults(record)}
                            className="text-blue-600 hover:text-blue-800 p-1 rounded transition-colors"
                            title="查看详细结果"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteHistory(record)}
                            className="text-red-600 hover:text-red-800 p-1 rounded transition-colors"
                            title="删除记录"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">暂无历史记录</h3>
                <p className="text-gray-600">
                  还没有执行过股票筛选，去执行一次筛选来创建历史记录吧
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 详细结果弹窗 */}
      {showResults && selectedRecord && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {formatDate(selectedRecord.screening_date)} 筛选结果
                </h3>
                <p className="text-sm text-gray-600">
                  {parseCriteria(selectedRecord.criteria_met)} - 共 {selectedResults.length} 只股票
                </p>
              </div>
              <button
                onClick={() => setShowResults(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 overflow-auto max-h-[60vh]">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">股票代码</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">股票名称</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">市场</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">连续天数</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">平均涨幅</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">平均成交量</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {selectedResults.map((result, index) => (
                    <tr key={result.stock_code || index} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-medium text-blue-600">{result.stock_code}</td>
                      <td className="px-4 py-2 text-sm text-gray-900">{result.stock_name}</td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {result.market}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-900">{result.consecutive_days} 天</td>
                      <td className="px-4 py-2 text-sm font-medium text-red-600">+{result.avg_rise_percent.toFixed(2)}%</td>
                      <td className="px-4 py-2 text-sm text-gray-900">{(result.avg_volume / 10000).toFixed(2)}万</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScreeningHistory;