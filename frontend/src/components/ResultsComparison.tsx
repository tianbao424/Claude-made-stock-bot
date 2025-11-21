import React from 'react';
import { TrendingUp, Target, ArrowRight, BarChart3, Percent, Award } from 'lucide-react';

interface ResultsComparisonProps {
  basicCount: number;
  strategyCount: number;
  appliedStrategies: string[];
}

const ResultsComparison: React.FC<ResultsComparisonProps> = ({
  basicCount,
  strategyCount,
  appliedStrategies
}) => {
  // 计算筛选效率
  const filterEfficiency = basicCount > 0 ? (strategyCount / basicCount * 100) : 0;
  
  // 策略名称映射
  const strategyNames: Record<string, string> = {
    'low_price_filter': '低价股过滤',
    'volume_ratio_strategy': '成交量比率',
    'ma_golden_cross': '均线金叉',
    'rsi_oversold': 'RSI超卖',
    'macd_divergence': 'MACD背离',
    'breakout_strategy': '突破策略'
  };

  // 获取筛选状态的样式
  const getFilterStatusStyle = () => {
    if (strategyCount === 0) return 'text-gray-600';
    if (filterEfficiency > 50) return 'text-yellow-600';
    if (filterEfficiency > 20) return 'text-blue-600';
    return 'text-green-600';
  };

  const getFilterStatusText = () => {
    if (strategyCount === 0) return '待筛选';
    if (filterEfficiency > 50) return '筛选宽松';
    if (filterEfficiency > 20) return '筛选适中';
    return '筛选严格';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border p-2">
      {/* 主要对比数据 - 单行显示 */}
      <div className="flex items-center gap-4">
        {/* 基础筛选结果 */}
        <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex items-center gap-2">
            <div>
              <p className="text-xs text-blue-600">基础筛选</p>
              <p className="text-base font-bold text-blue-900">{basicCount}</p>
            </div>
            <span className="text-xs text-blue-600">只</span>
          </div>
        </div>

        {/* 箭头 */}
        <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />

        {/* 策略筛选结果 */}
        <div className={`flex items-center gap-2 border rounded-lg px-3 py-1.5 ${
          strategyCount > 0 
            ? 'bg-green-50 border-green-200' 
            : 'bg-gray-50 border-gray-200'
        }`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            strategyCount > 0 
              ? 'bg-green-100' 
              : 'bg-gray-100'
          }`}>
            <Target className={`w-4 h-4 ${
              strategyCount > 0 
                ? 'text-green-600' 
                : 'text-gray-400'
            }`} />
          </div>
          <div className="flex items-center gap-2">
            <div>
              <p className={`text-xs ${
                strategyCount > 0 
                  ? 'text-green-600' 
                  : 'text-gray-500'
              }`}>策略筛选</p>
              <p className={`text-base font-bold ${
                strategyCount > 0 
                  ? 'text-green-900' 
                  : 'text-gray-500'
              }`}>
                {strategyCount > 0 ? strategyCount : '-'}
              </p>
            </div>
            <span className={`text-xs ${
              strategyCount > 0 
                ? 'text-green-600' 
                : 'text-gray-500'
            }`}>只</span>
          </div>
        </div>
        
        {/* 通过率 */}
        {strategyCount > 0 && (
          <div className="ml-auto flex items-center gap-2">
            <Percent className="w-4 h-4 text-purple-600" />
            <span className={`text-sm font-medium ${getFilterStatusStyle()}`}>
              {getFilterStatusText()} ({filterEfficiency.toFixed(1)}%)
            </span>
          </div>
        )}

        {/* 应用的策略 - 简化显示 */}
        {appliedStrategies.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-purple-700">
            <Award className="w-3 h-3" />
            <span>{appliedStrategies.length}个策略</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsComparison;