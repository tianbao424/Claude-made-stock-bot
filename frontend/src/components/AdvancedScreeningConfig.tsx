import React, { useState } from 'react';
import { 
  Settings, Filter, 
  TrendingUp, Activity, BarChart3, Layers, Target,
  Info, ChevronDown, ChevronRight,
  Shield, Brain
} from 'lucide-react';
import StrategyParameterModal from './StrategyParameterModal';

// 策略分组定义
interface StrategyGroup {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  strategies: Strategy[];
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
  defaultParams: Record<string, any>;
  performance?: {
    accuracy: number;
    avgScore: number;
    signalCount: number;
  };
}

interface ScreeningTemplate {
  id: string;
  name: string;
  description: string;
  strategyConfig: Record<string, boolean>;
  parameters: Record<string, any>;
  isDefault: boolean;
}

const AdvancedScreeningConfig: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'strategies' | 'templates' | 'performance'>('strategies');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['basic_filter']));
  const [selectedStrategies, setSelectedStrategies] = useState<Set<string>>(new Set());
  const [showParameterModal, setShowParameterModal] = useState<string | null>(null);

  // 策略分组数据
  const strategyGroups: StrategyGroup[] = [
    {
      id: 'basic_filter',
      name: '基础过滤策略',
      description: '过滤掉不符合基本条件的股票',
      icon: Shield,
      color: 'blue',
      strategies: [
        {
          id: 'low_price_filter',
          name: '低价股过滤',
          description: '过滤低于指定价格的股票，避免垃圾股风险',
          enabled: true,
          weight: 1.0,
          parameters: { price_threshold: 6.0, bank_threshold: 3.0 },
          defaultParams: { price_threshold: 6.0, bank_threshold: 3.0 },
          performance: { accuracy: 93.3, avgScore: 80, signalCount: 150 }
        },
        {
          id: 'high_position_news_filter',
          name: '高位利好过滤',
          description: '避免高位利好消息的获利回吐风险',
          enabled: true,
          weight: 1.0,
          parameters: { rise_threshold: 15.0, safe_threshold: 10.0 },
          defaultParams: { rise_threshold: 15.0, safe_threshold: 10.0 },
          performance: { accuracy: 93.3, avgScore: 75, signalCount: 120 }
        },
        {
          id: 'ma_deviation_filter',
          name: '均线偏离过滤',
          description: '识别价格偏离均线过远的风险股票',
          enabled: true,
          weight: 1.0,
          parameters: { max_deviation: 20.0, warning_threshold: 15.0 },
          defaultParams: { max_deviation: 20.0, warning_threshold: 15.0 },
          performance: { accuracy: 93.3, avgScore: 85, signalCount: 200 }
        },
        {
          id: 'gap_up_filter',
          name: '跳空高开过滤',
          description: '识别连续跳空高开的风险信号',
          enabled: true,
          weight: 1.0,
          parameters: { gap_threshold: 3.0, consecutive_days: 3 },
          defaultParams: { gap_threshold: 3.0, consecutive_days: 3 },
          performance: { accuracy: 100, avgScore: 75, signalCount: 80 }
        },
        {
          id: 'turnover_filter',
          name: '换手率异常过滤',
          description: '过滤换手率异常高或异常低的股票',
          enabled: true,
          weight: 1.0,
          parameters: { high_threshold: 30.0, low_threshold: 0.5 },
          defaultParams: { high_threshold: 30.0, low_threshold: 0.5 },
          performance: { accuracy: 86.7, avgScore: 85, signalCount: 180 }
        }
      ]
    },
    {
      id: 'volume_price',
      name: '量价关系策略',
      description: '分析成交量与价格的配合关系',
      icon: BarChart3,
      color: 'green',
      strategies: [
        {
          id: 'volume_ratio_strategy',
          name: '量比分析策略',
          description: '多维度量比分析，识别异常量能',
          enabled: true,
          weight: 0.8,
          parameters: { high_ratio: 2.0, low_ratio: 0.5, new_high_ratio: 1.5 },
          defaultParams: { high_ratio: 2.0, low_ratio: 0.5, new_high_ratio: 1.5 },
          performance: { accuracy: 100, avgScore: 80, signalCount: 250 }
        },
        {
          id: 'volume_price_relation',
          name: '量价关系策略',
          description: '分析量价配合的协调性',
          enabled: true,
          weight: 0.8,
          parameters: { volume_threshold: 1.2, price_threshold: 3.0 },
          defaultParams: { volume_threshold: 1.2, price_threshold: 3.0 },
          performance: { accuracy: 86.7, avgScore: 60, signalCount: 300 }
        },
        {
          id: 'volume_trend_analysis',
          name: '量能趋势分析',
          description: '追踪资金流向和量能变化趋势',
          enabled: true,
          weight: 0.8,
          parameters: { trend_threshold: 1.2, momentum_threshold: 1.5 },
          defaultParams: { trend_threshold: 1.2, momentum_threshold: 1.5 },
          performance: { accuracy: 100, avgScore: 72, signalCount: 220 }
        },
        {
          id: 'low_volume_low_price',
          name: '低量低价策略',
          description: '识别底部区域的潜在机会',
          enabled: true,
          weight: 0.8,
          parameters: { price_ma_threshold: 1.0, volume_ratio_threshold: 0.8 },
          defaultParams: { price_ma_threshold: 1.0, volume_ratio_threshold: 0.8 },
          performance: { accuracy: 86.7, avgScore: 65, signalCount: 160 }
        }
      ]
    },
    {
      id: 'trend_following',
      name: '趋势跟随策略',
      description: '识别和跟随市场趋势',
      icon: TrendingUp,
      color: 'purple',
      strategies: [
        {
          id: 'ma_golden_cross',
          name: '均线金叉策略',
          description: '识别均线金叉和多头排列信号',
          enabled: true,
          weight: 1.4,
          parameters: { cross_threshold: 1.005, pullback_threshold: 1.02 },
          defaultParams: { cross_threshold: 1.005, pullback_threshold: 1.02 },
          performance: { accuracy: 100, avgScore: 88, signalCount: 180 }
        },
        {
          id: 'trend_momentum',
          name: '趋势动能策略',
          description: '基于技术指标的趋势动能分析',
          enabled: true,
          weight: 1.3,
          parameters: { rsi_threshold: 30, kdj_threshold: 20, macd_threshold: 0 },
          defaultParams: { rsi_threshold: 30, kdj_threshold: 20, macd_threshold: 0 },
          performance: { accuracy: 100, avgScore: 100, signalCount: 200 }
        },
        {
          id: 'trend_reversal',
          name: '趋势反转策略',
          description: '识别趋势反转的关键时机',
          enabled: true,
          weight: 1.2,
          parameters: { reversal_threshold: 0.9, top_threshold: 1.1 },
          defaultParams: { reversal_threshold: 0.9, top_threshold: 1.1 },
          performance: { accuracy: 100, avgScore: 75, signalCount: 140 }
        }
      ]
    },
    {
      id: 'pattern_recognition',
      name: '技术形态策略',
      description: '识别重要的技术分析形态',
      icon: Activity,
      color: 'orange',
      strategies: [
        {
          id: 'support_resistance',
          name: '支撑阻力策略',
          description: '基于关键支撑阻力位的交易信号',
          enabled: true,
          weight: 1.3,
          parameters: { support_tolerance: 0.02, resistance_multiplier: 1.05 },
          defaultParams: { support_tolerance: 0.02, resistance_multiplier: 1.05 },
          performance: { accuracy: 66.7, avgScore: 45, signalCount: 100 }
        },
        {
          id: 'breakout_strategy',
          name: '突破策略',
          description: '识别各种突破形态的买入机会',
          enabled: true,
          weight: 1.4,
          parameters: { consolidation_threshold: 0.03, breakout_volume: 1.8 },
          defaultParams: { consolidation_threshold: 0.03, breakout_volume: 1.8 },
          performance: { accuracy: 80, avgScore: 60, signalCount: 120 }
        },
        {
          id: 'volume_pattern',
          name: '量价配合形态',
          description: '深度分析量价配合的技术形态',
          enabled: true,
          weight: 1.2,
          parameters: { accumulation_threshold: 1.2, stagnation_threshold: 2.0 },
          defaultParams: { accumulation_threshold: 1.2, stagnation_threshold: 2.0 },
          performance: { accuracy: 86.7, avgScore: 60, signalCount: 150 }
        }
      ]
    },
    {
      id: 'comprehensive',
      name: '综合判断策略',
      description: '整合多维度信号的智能决策',
      icon: Brain,
      color: 'red',
      strategies: [
        {
          id: 'comprehensive_analysis',
          name: '综合分析策略',
          description: '智能综合分析系统，动态权重调整',
          enabled: true,
          weight: 2.0,
          parameters: { confidence_threshold: 0.7, signal_threshold: 80 },
          defaultParams: { confidence_threshold: 0.7, signal_threshold: 80 },
          performance: { accuracy: 95, avgScore: 85, signalCount: 500 }
        }
      ]
    }
  ];

  // 预设模板
  const defaultTemplates: ScreeningTemplate[] = [
    {
      id: 'conservative',
      name: '稳健型筛选',
      description: '注重风险控制，适合稳健投资者',
      strategyConfig: {
        'low_price_filter': true,
        'ma_deviation_filter': true,
        'turnover_filter': true,
        'ma_golden_cross': true,
        'comprehensive_analysis': true
      },
      parameters: {},
      isDefault: true
    },
    {
      id: 'aggressive',
      name: '激进型筛选',
      description: '追求高收益，承担较高风险',
      strategyConfig: {
        'volume_ratio_strategy': true,
        'trend_momentum': true,
        'breakout_strategy': true,
        'comprehensive_analysis': true
      },
      parameters: {},
      isDefault: true
    },
    {
      id: 'technical',
      name: '技术分析型',
      description: '基于技术指标和形态分析',
      strategyConfig: {
        'ma_golden_cross': true,
        'trend_momentum': true,
        'support_resistance': true,
        'breakout_strategy': true,
        'volume_pattern': true
      },
      parameters: {},
      isDefault: true
    }
  ];

  const toggleGroup = (groupId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  const toggleStrategy = (strategyId: string) => {
    const newSelected = new Set(selectedStrategies);
    if (newSelected.has(strategyId)) {
      newSelected.delete(strategyId);
    } else {
      newSelected.add(strategyId);
    }
    setSelectedStrategies(newSelected);
  };

  const applyTemplate = (template: ScreeningTemplate) => {
    const newSelected = new Set<string>();
    Object.entries(template.strategyConfig).forEach(([strategyId, enabled]) => {
      if (enabled) {
        newSelected.add(strategyId);
      }
    });
    setSelectedStrategies(newSelected);
  };

  const handleSaveParameters = (strategyId: string, parameters: Record<string, any>) => {
    // 这里可以调用API保存参数
    console.log('保存策略参数:', strategyId, parameters);
  };

  const getCurrentStrategy = (strategyId: string): Strategy | null => {
    // 从所有策略组中查找策略
    for (const group of strategyGroups) {
      const strategy = group.strategies.find(s => s.id === strategyId);
      if (strategy) return strategy;
    }
    return null;
  };

  const getColorClasses = (color: string) => {
    const colorMap: Record<string, string> = {
      blue: 'text-blue-600 bg-blue-50 border-blue-200',
      green: 'text-green-600 bg-green-50 border-green-200',
      purple: 'text-purple-600 bg-purple-50 border-purple-200',
      orange: 'text-orange-600 bg-orange-50 border-orange-200',
      red: 'text-red-600 bg-red-50 border-red-200'
    };
    return colorMap[color] || colorMap.blue;
  };

  const renderStrategyCard = (strategy: Strategy, groupColor: string) => {
    const isSelected = selectedStrategies.has(strategy.id);
    const colorClasses = getColorClasses(groupColor);
    
    return (
      <div
        key={strategy.id}
        className={`border rounded-lg p-4 transition-all duration-200 ${
          isSelected 
            ? `${colorClasses} shadow-md scale-105` 
            : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
        }`}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => toggleStrategy(strategy.id)}
              className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                isSelected 
                  ? `border-${groupColor}-500 bg-${groupColor}-500` 
                  : 'border-gray-300'
              }`}
            >
              {isSelected && <div className="w-2 h-2 bg-white rounded-sm"></div>}
            </button>
            
            <div>
              <h4 className="font-medium text-gray-900">{strategy.name}</h4>
              <p className="text-sm text-gray-600 mt-1">{strategy.description}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowParameterModal(strategy.id)}
              className="p-1 text-gray-400 hover:text-gray-600"
              title="配置参数"
            >
              <Settings size={16} />
            </button>
            <button className="p-1 text-gray-400 hover:text-gray-600" title="查看详情">
              <Info size={16} />
            </button>
          </div>
        </div>

        {strategy.performance && (
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <Target size={14} className="text-green-500" />
              <span className="text-gray-600">准确率: {strategy.performance.accuracy}%</span>
            </div>
            <div className="flex items-center gap-1">
              <Target size={14} className="text-blue-500" />
              <span className="text-gray-600">评分: {strategy.performance.avgScore}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Filter className="text-blue-600" size={24} />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">高级筛选配置</h2>
              <p className="text-sm text-gray-600">配置和管理股票筛选策略</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">
              已选择 {selectedStrategies.size} 个策略
            </span>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              开始筛选
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex space-x-8 px-6">
          {[
            { id: 'strategies', name: '策略配置', icon: Settings },
            { id: 'templates', name: '预设模板', icon: Layers },
            { id: 'performance', name: '性能监控', icon: Activity }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon size={16} />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-6">
        {activeTab === 'strategies' && (
          <div className="space-y-6">
            {strategyGroups.map((group) => {
              const isExpanded = expandedGroups.has(group.id);
              const Icon = group.icon;
              
              return (
                <div key={group.id} className="border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`text-${group.color}-600`} size={20} />
                      <div className="text-left">
                        <h3 className="font-medium text-gray-900">{group.name}</h3>
                        <p className="text-sm text-gray-600">{group.description}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-500">
                        {group.strategies.length} 个策略
                      </span>
                      {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                    </div>
                  </button>
                  
                  {isExpanded && (
                    <div className="p-4 space-y-4">
                      {group.strategies.map((strategy) => 
                        renderStrategyCard(strategy, group.color)
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'templates' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {defaultTemplates.map((template) => (
              <div
                key={template.id}
                className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
                  template.isDefault ? 'border-blue-200 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                      {template.name}
                      {template.isDefault && (
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                          预设
                        </span>
                      )}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                  </div>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="text-sm">
                    <span className="text-gray-500">包含策略: </span>
                    <span className="font-medium">
                      {Object.values(template.strategyConfig).filter(Boolean).length} 个
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => applyTemplate(template)}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  应用模板
                </button>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="text-center py-12">
            <Activity size={48} className="text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">性能监控</h3>
            <p className="text-gray-600">策略性能监控功能开发中...</p>
          </div>
        )}
      </div>

      {/* 策略参数配置模态框 */}
      <StrategyParameterModal
        strategy={getCurrentStrategy(showParameterModal || '')}
        isOpen={!!showParameterModal}
        onClose={() => setShowParameterModal(null)}
        onSave={handleSaveParameters}
      />
    </div>
  );
};

export default AdvancedScreeningConfig;