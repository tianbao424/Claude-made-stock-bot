import React, { useState } from 'react';
import { 
  Filter, Target, BarChart3, Download, 
  RefreshCw, Info, AlertCircle, CheckCircle, ArrowRight, Circle 
} from 'lucide-react';
import BasicFilterPanel from './BasicFilterPanel';
import BasicResultsTable from './BasicResultsTable';
import StrategySelector from './StrategySelector';
import ResultsComparison from './ResultsComparison';

// 基础筛选条件接口
interface BasicFilterCriteria {
  consecutive_days?: number;
  min_rise_percent?: number;
  min_volume?: number;
  min_market_cap?: number;
  market_filter: string[];
  exclude_st: boolean;
  exclude_new_stocks: boolean;
}

// 股票结果接口
interface StockResult {
  stock_code: string;
  stock_name: string;
  market: string;
  industry: string;
  consecutive_days: number;
  avg_rise_percent: number;
  total_volume: number;
  avg_volume: number;
  market_cap: number;
  pe_ratio: number;
  screening_date: string;
  strategy_score?: number;
  signal_type?: string;
  signal_strength?: string;
  risk_level?: string;
}

// 筛选阶段
type ScreeningStage = 'basic' | 'strategy' | 'complete';

const AdvancedStockScreening: React.FC = () => {
  // 筛选阶段状态
  const [currentStage, setCurrentStage] = useState<ScreeningStage>('basic');
  
  // 基础筛选状态
  const [basicCriteria, setBasicCriteria] = useState<BasicFilterCriteria>({
    market_filter: ['SH', 'SZ'],
    exclude_st: true,
    exclude_new_stocks: true
  });
  
  // 筛选结果状态
  const [basicResults, setBasicResults] = useState<StockResult[]>([]);
  const [strategyResults, setStrategyResults] = useState<StockResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>('');
  
  // 策略筛选状态
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [strategyConfigs, setStrategyConfigs] = useState<any[]>([]);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  // 执行基础筛选
  const handleBasicScreening = async () => {
    setLoading(true);
    setMessage('正在执行基础筛选...');
    
    try {
      const response = await fetch('/api/advanced-screening/basic', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(basicCriteria)
      });
      
      const result = await response.json();
      
      if (result.success) {
        setBasicResults(result.data.results);
        setMessage(`✅ 基础筛选完成，找到 ${result.data.results.length} 只股票`);
        setCurrentStage('strategy');
      } else {
        setMessage(`❌ 基础筛选失败: ${result.message}`);
      }
    } catch (error) {
      console.error('基础筛选失败:', error);
      setMessage('❌ 基础筛选请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 执行策略筛选
  const handleStrategyScreening = async () => {
    if (selectedStrategies.length === 0) {
      setMessage('请至少选择一个策略');
      return;
    }
    
    setLoading(true);
    setMessage('正在执行策略筛选...');
    
    try {
      // 使用基础筛选结果的股票代码作为候选
      const stockCodes = basicResults.map(stock => stock.stock_code);
      
      const response = await fetch('/api/advanced-screening/strategy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stock_codes: stockCodes,
          strategies: strategyConfigs,
          min_score: 60,
          sort_by: 'score'
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setStrategyResults(result.data.results);
        setMessage(`✅ 策略筛选完成，从 ${basicResults.length} 只股票中筛选出 ${result.data.results.length} 只`);
        setCurrentStage('complete');
      } else {
        setMessage(`❌ 策略筛选失败: ${result.message}`);
      }
    } catch (error) {
      console.error('策略筛选失败:', error);
      setMessage('❌ 策略筛选请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 重置筛选
  const handleReset = () => {
    setCurrentStage('basic');
    setBasicResults([]);
    setStrategyResults([]);
    setSelectedStrategies([]);
    setStrategyConfigs([]);
    setMessage('');
    setCurrentPage(1);
  };

  // 导出结果
  const handleExport = () => {
    const resultsToExport = currentStage === 'complete' ? strategyResults : basicResults;
    const dataStr = JSON.stringify(resultsToExport, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `stock_screening_results_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* 页面头部 */}
      <div className="flex-shrink-0 p-3 pb-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Filter className="w-7 h-7 text-blue-600" />
              高级股票筛选
            </h1>
            <p className="text-gray-600 mt-1">基础筛选 → 策略筛选的两阶段智能筛选</p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={handleExport}
              disabled={basicResults.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              导出结果
            </button>
            
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              重新筛选
            </button>
          </div>
        </div>
        
        {/* 进度指示器 */}
        <div className="mt-2 flex items-center gap-3">
          <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium ${
            currentStage === 'basic' ? 'bg-blue-100 text-blue-800' : 
            'bg-green-100 text-green-800'
          }`}>
            {currentStage === 'basic' ? 
              <Circle className="w-4 h-4" /> : 
              <CheckCircle className="w-4 h-4" />
            }
            基础筛选
            {basicResults.length > 0 && ` (${basicResults.length}只)`}
          </div>
          
          <ArrowRight className="w-4 h-4 text-gray-400" />
          
          <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium ${
            currentStage === 'basic' ? 'bg-gray-100 text-gray-500' :
            currentStage === 'strategy' ? 'bg-blue-100 text-blue-800' :
            'bg-green-100 text-green-800'
          }`}>
            {currentStage === 'complete' ? 
              <CheckCircle className="w-4 h-4" /> : 
              <Circle className="w-4 h-4" />
            }
            策略筛选
            {strategyResults.length > 0 && ` (${strategyResults.length}只)`}
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="flex-1 flex gap-3 overflow-hidden p-3 pt-2">
        {/* 左侧筛选面板 */}
        <div className="w-80 flex flex-col gap-4 min-h-0 overflow-hidden">
          {/* 基础筛选面板 */}
          <div className={`bg-white rounded-lg shadow-sm border flex flex-col flex-1 overflow-hidden ${
            currentStage === 'basic' ? 'ring-2 ring-blue-500' : ''
          }`}>
            <div className="p-4 bg-gray-50 border-b flex-shrink-0">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-600" />
                基础筛选条件
              </h3>
            </div>
            
            <div className="flex-1 min-h-0 overflow-hidden">
              <BasicFilterPanel
                criteria={basicCriteria}
                onChange={setBasicCriteria}
                onApply={handleBasicScreening}
                loading={loading && currentStage === 'basic'}
                disabled={currentStage !== 'basic'}
              />
            </div>
          </div>
          
          {/* 策略筛选面板 */}
          {currentStage !== 'basic' && (
            <div className={`bg-white rounded-lg shadow-sm border flex flex-col flex-1 overflow-hidden ${
              currentStage === 'strategy' ? 'ring-2 ring-blue-500' : ''
            }`}>
              <div className="p-4 bg-gray-50 border-b flex-shrink-0">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Target className="w-5 h-5 text-purple-600" />
                  策略筛选
                </h3>
              </div>
              
              <div className="flex-1 overflow-y-auto">
                <StrategySelector
                  selectedStrategies={selectedStrategies}
                  onStrategiesChange={setSelectedStrategies}
                  strategyConfigs={strategyConfigs}
                  onConfigsChange={setStrategyConfigs}
                  onApply={handleStrategyScreening}
                  loading={loading && currentStage === 'strategy'}
                  disabled={currentStage === 'complete'}
                  basicResultsCount={basicResults.length}
                />
              </div>
            </div>
          )}
        </div>

        {/* 右侧结果区域 */}
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-hidden">
          {/* 结果对比面板 - 紧凑化 */}
          {basicResults.length > 0 && (
            <div className="flex-shrink-0 -mb-2">
              <ResultsComparison
                basicCount={basicResults.length}
                strategyCount={strategyResults.length}
                appliedStrategies={selectedStrategies}
              />
            </div>
          )}
          
          {/* 状态消息 - 紧凑化 */}
          {message && (
            <div className={`flex-shrink-0 p-2 rounded-lg border flex items-center gap-2 text-sm ${
              message.includes('✅') ? 'bg-green-50 border-green-200 text-green-800' :
              message.includes('❌') ? 'bg-red-50 border-red-200 text-red-800' :
              'bg-blue-50 border-blue-200 text-blue-800'
            }`}>
              {message.includes('✅') ? <CheckCircle className="w-4 h-4" /> :
               message.includes('❌') ? <AlertCircle className="w-4 h-4" /> :
               <Info className="w-4 h-4" />
              }
              {message}
            </div>
          )}
          
          {/* 结果表格 */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden min-h-0">
            <BasicResultsTable
              results={currentStage === 'complete' ? strategyResults : basicResults}
              loading={loading}
              currentPage={currentPage}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
              onPageSizeChange={setPageSize}
              showStrategyColumns={currentStage === 'complete'}
            />
          </div>
          
          {/* 独立的分页控件 */}
          {((currentStage === 'complete' ? strategyResults : basicResults).length > 0) && (
            <div className="flex-shrink-0 bg-white rounded-lg shadow-sm border p-3">
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
                      <option value={15}>15</option>
                      <option value={20}>20</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                    <span className="text-sm text-gray-700">条</span>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    显示第 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, (currentStage === 'complete' ? strategyResults : basicResults).length)} 条，共 {(currentStage === 'complete' ? strategyResults : basicResults).length} 条
                  </div>
                </div>

                {/* 右侧：分页按钮 */}
                {Math.ceil((currentStage === 'complete' ? strategyResults : basicResults).length / pageSize) > 1 && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-l bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                    >
                      上一页
                    </button>
                    
                    <div className="flex">
                      {Array.from({ length: Math.min(Math.ceil((currentStage === 'complete' ? strategyResults : basicResults).length / pageSize), 7) }, (_, i) => {
                        const pageNum = i + 1;
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setCurrentPage(pageNum)}
                            className={`px-3 py-1 text-sm border-t border-b ${
                              i === 0 ? 'border-l' : ''
                            } ${
                              i === Math.min(Math.ceil((currentStage === 'complete' ? strategyResults : basicResults).length / pageSize), 7) - 1 ? 'border-r' : ''
                            } ${
                              pageNum === currentPage
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>
                    
                    <button
                      onClick={() => setCurrentPage(Math.min(Math.ceil((currentStage === 'complete' ? strategyResults : basicResults).length / pageSize), currentPage + 1))}
                      disabled={currentPage >= Math.ceil((currentStage === 'complete' ? strategyResults : basicResults).length / pageSize)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-r bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                    >
                      下一页
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdvancedStockScreening;