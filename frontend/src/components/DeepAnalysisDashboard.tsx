import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Search, 
  Play, 
  RefreshCw,
  AlertTriangle,
  Target,
  BarChart3,
  Activity
} from 'lucide-react';

interface DeepAnalysisResult {
  stock_code: string;
  stock_name: string;
  analysis_date: string;
  overall_score: number;
  investment_grade: string;
  recommendation: string;
  risk_level: string;
  is_low_volatility_breakout: boolean;
  is_volume_price_coordinated: boolean;
  is_worthy_of_attention: boolean;
}

const DeepAnalysisDashboard: React.FC = () => {
  const [analysisResults, setAnalysisResults] = useState<DeepAnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stockCodes, setStockCodes] = useState('');
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'results' | 'worthy'>('results');

  useEffect(() => {
    loadAnalysisResults();
  }, []);

  const loadAnalysisResults = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/deep-analysis/results?limit=50');
      const data = await response.json();
      if (data.success) {
        setAnalysisResults(data.data || []);
      } else {
        setError('加载分析结果失败');
      }
    } catch (err) {
      console.error('加载分析结果失败:', err);
      setError('网络错误，请检查连接');
    } finally {
      setLoading(false);
    }
  };

  const handleManualAnalysis = async () => {
    if (!stockCodes.trim()) {
      setError('请输入股票代码');
      return;
    }

    setAnalysisLoading(true);
    setError(null);

    try {
      const codes = stockCodes.split(/[,，\s]+/).filter(code => code.trim());
      const response = await fetch('/api/deep-analysis/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stock_codes: codes,
          save_results: true
        })
      });

      const data = await response.json();
      if (data.success) {
        setStockCodes('');
        await loadAnalysisResults();
      } else {
        setError(data.message || '分析失败');
      }
    } catch (err) {
      setError('分析请求失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A': return 'text-green-600 bg-green-100';
      case 'B': return 'text-blue-600 bg-blue-100';
      case 'C': return 'text-yellow-600 bg-yellow-100';
      case 'D': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">正在初始化深度分析控制台</h2>
          <p className="text-gray-600">正在加载分析数据和配置...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-4 lg:p-6 max-w-7xl mx-auto overflow-hidden">
      {/* 头部 */}
      <div className="mb-6 flex-shrink-0">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">深度分析控制台</h1>
        <p className="text-gray-600">智能识别低波动突破模式，自动管理投资机会</p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg flex items-center gap-2 flex-shrink-0">
          <AlertTriangle className="w-5 h-5" />
          {error}
          <button 
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      {/* 手动分析 */}
      <div className="mb-6 bg-white rounded-lg shadow p-6 flex-shrink-0">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Search className="w-5 h-5 text-blue-600" />
          手动深度分析
        </h3>
        <div className="flex gap-4">
          <div className="flex-1">
            <textarea
              value={stockCodes}
              onChange={(e) => setStockCodes(e.target.value)}
              placeholder="例如: 000001, 600519, 000858"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
            />
          </div>
          <button
            onClick={handleManualAnalysis}
            disabled={analysisLoading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white py-2 px-6 rounded-md flex items-center gap-2"
          >
            {analysisLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {analysisLoading ? '分析中...' : '开始分析'}
          </button>
        </div>
      </div>

      {/* 标签页导航 */}
      <div className="mb-4 flex-shrink-0">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'results', name: '分析结果', icon: BarChart3 },
              { id: 'worthy', name: '值得关注', icon: TrendingUp }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {activeTab === 'results' && (
          <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden flex flex-col min-h-0">
            {/* 分析结果信息 */}
            <div className="px-6 py-3 bg-gray-50 border-b text-sm text-gray-600 flex-shrink-0">
              <span>共 {analysisResults.length} 条分析结果</span>
            </div>
            
            {/* 表格 */}
            <div className="flex-1 overflow-x-auto overflow-y-auto">
              {analysisResults.length > 0 ? (
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票信息
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        评分等级
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        分析特征
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        风险评估
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        分析日期
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        建议
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {analysisResults.map((result, index) => (
                      <tr key={index} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{result.stock_name}</div>
                              <div className="text-sm text-gray-500 font-mono">{result.stock_code}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-1">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getGradeColor(result.investment_grade)}`}>
                              {result.investment_grade}级
                            </span>
                            <span className={`text-sm font-medium ${getScoreColor(result.overall_score)}`}>
                              {result.overall_score.toFixed(1)}分
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            {result.is_low_volatility_breakout && (
                              <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                                低波动突破
                              </span>
                            )}
                            {result.is_volume_price_coordinated && (
                              <span className="inline-flex px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                                量价配合
                              </span>
                            )}
                            {result.is_worthy_of_attention && (
                              <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                                值得关注
                              </span>
                            )}
                            {!result.is_low_volatility_breakout && !result.is_volume_price_coordinated && !result.is_worthy_of_attention && (
                              <span className="text-xs text-gray-400">暂无特征</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRiskColor(result.risk_level)}`}>
                            {result.risk_level === 'low' ? '低风险' : result.risk_level === 'medium' ? '中风险' : '高风险'}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-900">{result.analysis_date}</div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap text-center">
                          <div className="text-sm font-medium text-blue-600">{result.recommendation}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex items-center justify-center h-32">
                  <div className="text-center">
                    <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">暂无分析结果</h3>
                    <p className="text-gray-600">请使用上方的手动分析功能来分析股票</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'worthy' && (
          <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden flex flex-col min-h-0">
            {/* 值得关注股票信息 */}
            <div className="px-6 py-3 bg-gray-50 border-b text-sm text-gray-600 flex-shrink-0">
              <span>共 {analysisResults.filter(stock => stock.is_worthy_of_attention).length} 只值得关注的股票</span>
            </div>
            
            {/* 表格 */}
            <div className="flex-1 overflow-x-auto overflow-y-auto">
              {analysisResults.filter(stock => stock.is_worthy_of_attention).length > 0 ? (
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票信息
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        评分等级
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        特色标签
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        风险评估
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        分析日期
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        投资建议
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {analysisResults.filter(stock => stock.is_worthy_of_attention).map((stock, index) => (
                      <tr key={index} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{stock.stock_name}</div>
                              <div className="text-sm text-gray-500 font-mono">{stock.stock_code}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap">
                          <div className="flex flex-col gap-1">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getGradeColor(stock.investment_grade)}`}>
                              {stock.investment_grade}级
                            </span>
                            <span className={`text-sm font-medium ${getScoreColor(stock.overall_score)}`}>
                              {stock.overall_score.toFixed(1)}分
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                              值得关注
                            </span>
                            {stock.is_low_volatility_breakout && (
                              <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                                低波动突破
                              </span>
                            )}
                            {stock.is_volume_price_coordinated && (
                              <span className="inline-flex px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                                量价配合
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRiskColor(stock.risk_level)}`}>
                            {stock.risk_level === 'low' ? '低风险' : stock.risk_level === 'medium' ? '中风险' : '高风险'}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-900">{stock.analysis_date}</div>
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap text-center">
                          <div className="text-sm font-medium text-green-600">{stock.recommendation}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex items-center justify-center h-32">
                  <div className="text-center">
                    <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">暂无值得关注的股票</h3>
                    <p className="text-gray-600">
                      符合低波动突破条件的优质股票将会显示在这里
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeepAnalysisDashboard;