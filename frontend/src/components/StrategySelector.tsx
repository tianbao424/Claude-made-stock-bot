import React, { useState, useEffect } from 'react';
import { RefreshCw, Target, Eye, CheckCircle, Circle, Info, AlertCircle } from 'lucide-react';

interface StrategyConfig {
  strategy_id: string;
  enabled: boolean;
  parameters: Record<string, any>;
  weight: number;
}

interface StrategySelectorProps {
  selectedStrategies: string[];
  onStrategiesChange: (strategies: string[]) => void;
  strategyConfigs: StrategyConfig[];
  onConfigsChange: (configs: StrategyConfig[]) => void;
  onApply: () => void;
  loading: boolean;
  disabled: boolean;
  basicResultsCount: number;
}

// 完整的策略定义 - 从策略中心整合
const availableStrategies = [
  // 基础过滤策略
  {
    id: 'low_price_filter',
    name: '低价股过滤',
    description: '过滤低于指定价格的普通股票，避免垃圾股风险',
    category: '基础过滤',
    defaultParams: { price_threshold: 6.0 },
    weight: 1.0
  },
  {
    id: 'bank_low_price_filter',
    name: '银行低价股策略',
    description: '专门针对银行股的低价过滤策略，可配置价格阈值',
    category: '基础过滤',
    defaultParams: { price_threshold: 3.5 },
    weight: 1.2
  },
  {
    id: 'turnover_filter',
    name: '换手率监控',
    description: '过滤换手率异常的股票',
    category: '基础过滤',
    defaultParams: { high_threshold: 30.0, low_threshold: 0.5 },
    weight: 1.0
  },
  {
    id: 'gap_up_filter',
    name: '跳空高开过滤',
    description: '识别连续跳空高开的风险信号',
    category: '基础过滤',
    defaultParams: { gap_threshold: 3.0, consecutive_days: 2 },
    weight: 1.0
  },
  {
    id: 'high_position_filter',
    name: '高位利好过滤',
    description: '避免高位利好出货陷阱',
    category: '基础过滤',
    defaultParams: { rise_threshold: 15.0 },
    weight: 1.0
  },
  
  // 趋势判断策略
  {
    id: 'ma_golden_cross',
    name: '均线金叉',
    description: '捕捉均线金叉买入信号',
    category: '趋势判断',
    defaultParams: { short_ma: 5, long_ma: 20, min_volume_ratio: 1.2 },
    weight: 1.4
  },
  {
    id: 'volume_shrink_rise',
    name: '缩量上涨',
    description: '识别缩量上涨的控盘股',
    category: '趋势判断',
    defaultParams: { volume_ratio: 0.8 },
    weight: 1.2
  },
  {
    id: 'volume_expand_breakout',
    name: '放量突破',
    description: '识别放量突破的爆发机会',
    category: '趋势判断',
    defaultParams: { volume_ratio: 1.5, breakout_percent: 3.0 },
    weight: 1.3
  },
  {
    id: 'trend_momentum',
    name: '趋势动能',
    description: '综合分析趋势的持续性',
    category: '趋势判断',
    defaultParams: { momentum_threshold: 70 },
    weight: 1.3
  },
  
  // 分时监控策略
  {
    id: 'bid_ask_monitor',
    name: '盘口量能监控',
    description: '实时监控盘口大单异动',
    category: '分时监控',
    defaultParams: { large_order_threshold: 500000 },
    weight: 1.0
  },
  {
    id: 'late_dive_alert',
    name: '尾盘跳水预警',
    description: '识别尾盘异常下跌',
    category: '分时监控',
    defaultParams: { dive_threshold: -3.0, time_window: '14:30' },
    weight: 1.1
  },
  {
    id: 'white_yellow_divergence',
    name: '白黄线乖离',
    description: '监控分时图异常乖离',
    category: '分时监控',
    defaultParams: { divergence_threshold: 2.0 },
    weight: 1.0
  },
  
  // 风控策略
  {
    id: 'dynamic_stop_profit_loss',
    name: '动态止盈止损',
    description: '智能调整止盈止损位',
    category: '风控策略',
    defaultParams: { profit_target: 10, stop_loss: 5 },
    weight: 1.5
  },
  {
    id: 'position_control',
    name: '持股数控制',
    description: '限制持股数量不超过3只',
    category: '风控策略',
    defaultParams: { max_positions: 3 },
    weight: 1.0
  },
  {
    id: 'profit_rest_reminder',
    name: '大赚空仓提醒',
    description: '大幅盈利后提醒休息',
    category: '风控策略',
    defaultParams: { profit_threshold: 20 },
    weight: 1.0
  }
];

const StrategySelector: React.FC<StrategySelectorProps> = ({
  selectedStrategies,
  onStrategiesChange,
  strategyConfigs,
  onConfigsChange,
  onApply,
  loading,
  disabled,
  basicResultsCount
}) => {
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [estimatedResults, setEstimatedResults] = useState<number>(0);
  const [parametersVersion, setParametersVersion] = useState<number>(0);

  // 初始化策略配置
  useEffect(() => {
    const configs = selectedStrategies.map(strategyId => {
      const existingConfig = strategyConfigs.find(c => c.strategy_id === strategyId);
      if (existingConfig) return existingConfig;
      
      const strategy = availableStrategies.find(s => s.id === strategyId);
      
      // 从 localStorage 读取用户配置的参数
      const savedParametersStr = localStorage.getItem('strategy_parameters') || '{}';
      const savedParameters = JSON.parse(savedParametersStr);
      const userParams = savedParameters[strategyId] || {};
      
      // 合并默认参数和用户配置参数
      const finalParams = { ...strategy?.defaultParams, ...userParams };
      
      return {
        strategy_id: strategyId,
        enabled: true,
        parameters: finalParams,
        weight: strategy?.weight || 1.0
      };
    });
    onConfigsChange(configs);
  }, [selectedStrategies, parametersVersion]);

  // 监听 localStorage 中策略参数的变化
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'strategy_parameters') {
        setParametersVersion(prev => prev + 1);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // 估算策略筛选结果
  useEffect(() => {
    if (selectedStrategies.length === 0) {
      setEstimatedResults(0);
      return;
    }
    
    // 简单的估算逻辑：根据策略数量和基础结果数量
    const baseFilterRate = 0.3; // 基础过滤率30%
    const strategyFilterRate = Math.pow(0.7, selectedStrategies.length); // 每个策略降低30%
    const estimated = Math.floor(basicResultsCount * baseFilterRate * strategyFilterRate);
    setEstimatedResults(Math.max(1, estimated));
  }, [selectedStrategies, basicResultsCount]);

  // 切换策略选择
  const toggleStrategy = (strategyId: string) => {
    if (selectedStrategies.includes(strategyId)) {
      onStrategiesChange(selectedStrategies.filter(id => id !== strategyId));
    } else {
      onStrategiesChange([...selectedStrategies, strategyId]);
    }
  };

  // 刷新策略参数（从 localStorage 重新加载）
  const refreshParameters = () => {
    setParametersVersion(prev => prev + 1);
  };

  // 按分类分组策略
  const strategiesByCategory = availableStrategies.reduce((acc, strategy) => {
    if (!acc[strategy.category]) {
      acc[strategy.category] = [];
    }
    acc[strategy.category].push(strategy);
    return acc;
  }, {} as Record<string, typeof availableStrategies>);

  return (
    <div className="p-4 space-y-4">
      {/* 策略筛选说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-blue-800 font-medium">策略筛选说明</p>
              <p className="text-blue-700 mt-1">
                将对 <span className="font-medium">{basicResultsCount}</span> 只基础筛选结果应用所选策略
              </p>
              {selectedStrategies.length > 0 && (
                <p className="text-blue-700 mt-1">
                  预计筛选出 <span className="font-medium text-blue-800">{estimatedResults}</span> 只股票
                </p>
              )}
            </div>
          </div>
          <button
            onClick={refreshParameters}
            className="flex items-center gap-1 px-2 py-1 text-xs text-blue-700 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
            title="刷新策略参数"
          >
            <RefreshCw className="w-3 h-3" />
            刷新参数
          </button>
        </div>
      </div>

      {/* 策略选择 */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700">选择策略</h4>
        
        {Object.entries(strategiesByCategory).map(([category, strategies]) => (
          <div key={category} className="space-y-2">
            <h5 className="text-xs font-medium text-gray-600 uppercase tracking-wider">
              {category}
            </h5>
            
            {strategies.map(strategy => {
              const isSelected = selectedStrategies.includes(strategy.id);
              const config = strategyConfigs.find(c => c.strategy_id === strategy.id);
              
              return (
                <div key={strategy.id} className="space-y-2">
                  <div
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                    onClick={() => !disabled && toggleStrategy(strategy.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {isSelected ? (
                          <CheckCircle className="w-5 h-5 text-blue-600" />
                        ) : (
                          <Circle className="w-5 h-5 text-gray-400" />
                        )}
                        
                        <div>
                          <h6 className="text-sm font-medium text-gray-900">
                            {strategy.name}
                          </h6>
                          <p className="text-xs text-gray-600">
                            {strategy.description}
                          </p>
                        </div>
                      </div>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedStrategy(
                            expandedStrategy === strategy.id ? null : strategy.id
                          );
                        }}
                        className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-100 rounded transition-colors"
                        title="查看策略详情"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  
                  {/* 策略详情 */}
                  {expandedStrategy === strategy.id && (
                    <div className="ml-8 p-3 bg-gray-50 rounded-lg border">
                      <h6 className="text-sm font-medium text-gray-700 mb-3">策略详情</h6>
                      
                      <div className="space-y-3">
                        {/* 策略描述 */}
                        <div>
                          <h6 className="text-xs font-medium text-gray-600 mb-1">策略说明</h6>
                          <p className="text-xs text-gray-700">{strategy.description}</p>
                        </div>
                        
                        {/* 策略分类 */}
                        <div>
                          <h6 className="text-xs font-medium text-gray-600 mb-1">策略分类</h6>
                          <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                            {strategy.category}
                          </span>
                        </div>

                        {/* 当前配置参数（只读显示） */}
                        {isSelected && config && Object.keys(config.parameters).length > 0 && (
                          <div>
                            <h6 className="text-xs font-medium text-gray-600 mb-2">当前配置参数</h6>
                            <div className="bg-white border rounded p-2 space-y-1">
                              <div className="flex justify-between text-xs">
                                <span className="text-gray-600">策略权重:</span>
                                <span className="font-medium">{config.weight}</span>
                              </div>
                              {Object.entries(config.parameters).map(([paramKey, value]) => (
                                <div key={paramKey} className="flex justify-between text-xs">
                                  <span className="text-gray-600">{paramKey.replace(/_/g, ' ')}:</span>
                                  <span className="font-medium">{value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}


                        {/* 操作提示 */}
                        <div className="mt-3 pt-2 border-t border-gray-200">
                          <p className="text-xs text-gray-500">
                            💡 要修改策略参数，请前往策略中心进行配置
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* 已选策略汇总 */}
      {selectedStrategies.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <h4 className="text-sm font-medium text-green-800 mb-2">
            已选策略 ({selectedStrategies.length}个)
          </h4>
          <div className="space-y-1">
            {selectedStrategies.map(strategyId => {
              const strategy = availableStrategies.find(s => s.id === strategyId);
              const config = strategyConfigs.find(c => c.strategy_id === strategyId);
              return (
                <div key={strategyId} className="flex items-center justify-between text-sm">
                  <span className="text-green-700">{strategy?.name}</span>
                  <span className="text-green-600">权重: {config?.weight || 1.0}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 执行按钮 */}
      <div className="pt-4 border-t">
        <button
          onClick={onApply}
          disabled={disabled || loading || selectedStrategies.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              策略筛选中...
            </>
          ) : (
            <>
              <Target className="w-4 h-4" />
              执行策略筛选
            </>
          )}
        </button>
        
        {selectedStrategies.length === 0 && (
          <div className="mt-2 flex items-center gap-1 text-xs text-red-600">
            <AlertCircle className="w-3 h-3" />
            请至少选择一个策略
          </div>
        )}
        
        {selectedStrategies.length > 0 && (
          <p className="mt-2 text-xs text-gray-600 text-center">
            将对 {basicResultsCount} 只股票应用 {selectedStrategies.length} 个策略
          </p>
        )}
      </div>
    </div>
  );
};

export default StrategySelector;