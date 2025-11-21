import React, { useState } from 'react';
import { 
  Shield, TrendingUp, Activity, AlertTriangle, Play, 
  Edit2, Trash2, ChevronDown, ChevronRight, Settings 
} from 'lucide-react';

// 策略预设卡片类型
interface StrategyPreset {
  id: string;
  name: string;
  description: string;
  category: string;
  isDefault?: boolean;
  criteria: {
    screening_type: string;
    min_consecutive_days: number;
    min_rise_percent: number;
    min_volume: number;
    market_filter: string[];
    additional_params?: Record<string, any>;
  };
  tags: string[];
  color: string;
  performance?: {
    accuracy: number;
    signals: number;
    winRate: number;
  };
}

// 策略分组
interface StrategyCategory {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  strategies: StrategyPreset[];
}

const StrategyPresetCards: React.FC = () => {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['basic_filter']));
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  // 策略分组数据
  const strategyCategories: StrategyCategory[] = [
    {
      id: 'basic_filter',
      name: '基础过滤',
      description: '低价股、换手率等 → 剔除风险票',
      icon: Shield,
      color: 'blue',
      strategies: [
        {
          id: 'low_price_shield',
          name: '低价防护盾',
          description: '过滤6元以下低价股，避免垃圾股陷阱',
          category: 'basic_filter',
          isDefault: true,
          criteria: {
            screening_type: 'low_price_filter',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { price_threshold: 6.0 }
          },
          tags: ['风险控制', '价格筛选'],
          color: 'blue',
          performance: { accuracy: 93, signals: 150, winRate: 85 }
        },
        {
          id: 'turnover_guardian',
          name: '换手率守护者',
          description: '监控异常换手率，识别主力异动',
          category: 'basic_filter',
          criteria: {
            screening_type: 'turnover_filter',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { high_threshold: 30, low_threshold: 0.5 }
          },
          tags: ['换手监控', '主力识别'],
          color: 'orange',
          performance: { accuracy: 87, signals: 180, winRate: 79 }
        },
        {
          id: 'gap_risk_detector',
          name: '跳空风险探测器',
          description: '识别连续跳空高开的风险信号',
          category: 'basic_filter',
          criteria: {
            screening_type: 'gap_up_filter',
            min_consecutive_days: 2,
            min_rise_percent: 3.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ']
          },
          tags: ['跳空识别', '风险预警'],
          color: 'red',
          performance: { accuracy: 91, signals: 80, winRate: 88 }
        },
        {
          id: 'high_position_filter',
          name: '高位利好过滤网',
          description: '避免高位利好出货的接盘风险',
          category: 'basic_filter',
          criteria: {
            screening_type: 'high_position_news',
            min_consecutive_days: 1,
            min_rise_percent: 15.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ']
          },
          tags: ['高位识别', '利好过滤'],
          color: 'purple',
          performance: { accuracy: 89, signals: 120, winRate: 82 }
        }
      ]
    },
    {
      id: 'trend_analysis',
      name: '趋势判断',
      description: '日线均线突破、缩量/放量特征',
      icon: TrendingUp,
      color: 'green',
      strategies: [
        {
          id: 'ma_breakthrough',
          name: '均线突破猎手',
          description: '捕捉日线均线突破的黄金时机',
          category: 'trend_analysis',
          isDefault: true,
          criteria: {
            screening_type: 'ma_golden_cross',
            min_consecutive_days: 1,
            min_rise_percent: 2.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ']
          },
          tags: ['均线突破', '黄金交叉'],
          color: 'green',
          performance: { accuracy: 85, signals: 200, winRate: 78 }
        },
        {
          id: 'volume_shrink_rise',
          name: '缩量上涨精选',
          description: '筛选缩量上涨的控盘强势股',
          category: 'trend_analysis',
          criteria: {
            screening_type: 'shrink_volume_rise',
            min_consecutive_days: 2,
            min_rise_percent: 3.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { max_volume_ratio: 0.8 }
          },
          tags: ['缩量上涨', '控盘股'],
          color: 'blue',
          performance: { accuracy: 82, signals: 150, winRate: 75 }
        },
        {
          id: 'volume_expand_confirm',
          name: '放量确认器',
          description: '识别放量突破的确认信号',
          category: 'trend_analysis',
          criteria: {
            screening_type: 'volume_breakout',
            min_consecutive_days: 1,
            min_rise_percent: 4.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { min_volume_ratio: 1.5 }
          },
          tags: ['放量突破', '确认信号'],
          color: 'red',
          performance: { accuracy: 79, signals: 180, winRate: 73 }
        },
        {
          id: 'trend_momentum',
          name: '趋势动能分析师',
          description: '综合分析趋势的持续性和强度',
          category: 'trend_analysis',
          criteria: {
            screening_type: 'trend_momentum',
            min_consecutive_days: 3,
            min_rise_percent: 5.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ']
          },
          tags: ['趋势动能', '持续性'],
          color: 'purple',
          performance: { accuracy: 88, signals: 160, winRate: 81 }
        }
      ]
    },
    {
      id: 'intraday_monitor',
      name: '分时监控',
      description: '盘口量能、尾盘跳水、白黄线乖离',
      icon: Activity,
      color: 'orange',
      strategies: [
        {
          id: 'intraday_volume',
          name: '盘口量能雷达',
          description: '实时监控盘中量能变化异动',
          category: 'intraday_monitor',
          isDefault: true,
          criteria: {
            screening_type: 'intraday_volume',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { monitor_interval: 5 }
          },
          tags: ['盘口监控', '量能异动'],
          color: 'orange',
          performance: { accuracy: 75, signals: 300, winRate: 68 }
        },
        {
          id: 'late_dive_alert',
          name: '尾盘跳水预警',
          description: '识别尾盘大幅下跌的风险信号',
          category: 'intraday_monitor',
          criteria: {
            screening_type: 'late_session_dive',
            min_consecutive_days: 1,
            min_rise_percent: -3.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { time_window: '14:30-15:00' }
          },
          tags: ['尾盘监控', '跳水预警'],
          color: 'red',
          performance: { accuracy: 83, signals: 120, winRate: 77 }
        },
        {
          id: 'line_divergence',
          name: '白黄线乖离仪',
          description: '监控分时图白黄线乖离程度',
          category: 'intraday_monitor',
          criteria: {
            screening_type: 'line_divergence',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { divergence_threshold: 2.0 }
          },
          tags: ['分时监控', '乖离分析'],
          color: 'blue',
          performance: { accuracy: 71, signals: 250, winRate: 65 }
        },
        {
          id: 'power_surge_detector',
          name: '拉升力度检测器',
          description: '识别盘中快速拉升的爆发股',
          category: 'intraday_monitor',
          criteria: {
            screening_type: 'power_surge',
            min_consecutive_days: 1,
            min_rise_percent: 5.0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { surge_time: 30 }
          },
          tags: ['快速拉升', '爆发股'],
          color: 'green',
          performance: { accuracy: 69, signals: 180, winRate: 62 }
        }
      ]
    },
    {
      id: 'risk_control',
      name: '风控策略',
      description: '止盈止损、持股数≤3、大赚后空仓提醒',
      icon: AlertTriangle,
      color: 'red',
      strategies: [
        {
          id: 'dynamic_stop_loss',
          name: '动态止盈止损',
          description: '智能调整止盈止损位，保护利润',
          category: 'risk_control',
          isDefault: true,
          criteria: {
            screening_type: 'dynamic_stop',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { profit_target: 10, stop_loss: 5 }
          },
          tags: ['止盈止损', '动态调整'],
          color: 'red',
          performance: { accuracy: 92, signals: 100, winRate: 85 }
        },
        {
          id: 'position_limit',
          name: '持仓数量管控',
          description: '严格控制持股数量不超过3只',
          category: 'risk_control',
          criteria: {
            screening_type: 'position_limit',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { max_positions: 3 }
          },
          tags: ['仓位控制', '分散风险'],
          color: 'orange',
          performance: { accuracy: 95, signals: 50, winRate: 88 }
        },
        {
          id: 'profit_taking_alert',
          name: '大赚空仓提醒',
          description: '大幅盈利后提醒空仓休息',
          category: 'risk_control',
          criteria: {
            screening_type: 'profit_alert',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { profit_threshold: 20 }
          },
          tags: ['盈利提醒', '情绪控制'],
          color: 'green',
          performance: { accuracy: 90, signals: 30, winRate: 87 }
        },
        {
          id: 'drawdown_protection',
          name: '回撤保护盾',
          description: '监控账户回撤，及时止损',
          category: 'risk_control',
          criteria: {
            screening_type: 'drawdown_protection',
            min_consecutive_days: 1,
            min_rise_percent: 0,
            min_volume: 0,
            market_filter: ['SH', 'SZ'],
            additional_params: { max_drawdown: 10 }
          },
          tags: ['回撤控制', '资金保护'],
          color: 'purple',
          performance: { accuracy: 88, signals: 40, winRate: 83 }
        }
      ]
    }
  ];

  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const applyPreset = (preset: StrategyPreset) => {
    setSelectedPreset(preset.id);
    console.log('应用策略预设:', preset);
    // 这里可以调用实际的筛选API
  };

  const getColorClasses = (color: string) => {
    const colorMap: Record<string, { card: string; button: string; icon: string }> = {
      blue: {
        card: 'border-blue-200 bg-blue-50',
        button: 'bg-blue-600 hover:bg-blue-700',
        icon: 'text-blue-600'
      },
      green: {
        card: 'border-green-200 bg-green-50',
        button: 'bg-green-600 hover:bg-green-700',
        icon: 'text-green-600'
      },
      orange: {
        card: 'border-orange-200 bg-orange-50',
        button: 'bg-orange-600 hover:bg-orange-700',
        icon: 'text-orange-600'
      },
      red: {
        card: 'border-red-200 bg-red-50',
        button: 'bg-red-600 hover:bg-red-700',
        icon: 'text-red-600'
      },
      purple: {
        card: 'border-purple-200 bg-purple-50',
        button: 'bg-purple-600 hover:bg-purple-700',
        icon: 'text-purple-600'
      }
    };
    return colorMap[color] || colorMap.blue;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* 页面头部 */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Settings className="w-8 h-8 text-green-600" />
            <h1 className="text-3xl font-bold text-gray-900">筛选预设</h1>
          </div>
          <p className="text-lg text-gray-600">
            基于实战经验的股票筛选策略预设，一键应用专业筛选条件
          </p>
        </div>

        {/* 策略分组 */}
        <div className="space-y-6">
          {strategyCategories.map((category) => {
            const isExpanded = expandedCategories.has(category.id);
            const Icon = category.icon;
            const colors = getColorClasses(category.color);

            return (
              <div key={category.id} className="bg-white rounded-lg shadow-sm border overflow-hidden">
                {/* 分组头部 */}
                <button
                  onClick={() => toggleCategory(category.id)}
                  className="w-full px-6 py-4 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <Icon className={`w-6 h-6 ${colors.icon}`} />
                    <div className="text-left">
                      <h2 className="text-xl font-bold text-gray-900">{category.name}</h2>
                      <p className="text-sm text-gray-600">{category.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-500">
                      {category.strategies.length} 个策略
                    </span>
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-500" />
                    )}
                  </div>
                </button>

                {/* 策略卡片网格 */}
                {isExpanded && (
                  <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {category.strategies.map((strategy) => {
                        const strategyColors = getColorClasses(strategy.color);
                        const isSelected = selectedPreset === strategy.id;

                        return (
                          <div
                            key={strategy.id}
                            className={`border rounded-lg p-4 transition-all duration-200 hover:shadow-md ${
                              strategy.isDefault ? 'border-blue-300 bg-blue-50' : 
                              isSelected ? 'border-green-300 bg-green-50 shadow-md' : 
                              'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            {/* 卡片头部 */}
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <h3 className="font-bold text-gray-900">{strategy.name}</h3>
                                  {strategy.isDefault && (
                                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                      默认
                                    </span>
                                  )}
                                  {isSelected && (
                                    <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                                      已选
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 line-clamp-2">{strategy.description}</p>
                              </div>
                            </div>

                            {/* 策略参数 */}
                            <div className="space-y-2 mb-4">
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-500">连续天数:</span>
                                <span className="font-medium">{strategy.criteria.min_consecutive_days} 天</span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-500">最小涨幅:</span>
                                <span className="font-medium text-red-600">
                                  {strategy.criteria.min_rise_percent}%
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-500">市场:</span>
                                <span className="font-medium">
                                  {strategy.criteria.market_filter.join(', ')}
                                </span>
                              </div>
                            </div>

                            {/* 性能指标 */}
                            {strategy.performance && (
                              <div className="space-y-2 mb-4 p-3 bg-gray-50 rounded">
                                <div className="flex justify-between text-xs">
                                  <span className="text-gray-500">准确率:</span>
                                  <span className="font-medium text-green-600">
                                    {strategy.performance.accuracy}%
                                  </span>
                                </div>
                                <div className="flex justify-between text-xs">
                                  <span className="text-gray-500">信号数:</span>
                                  <span className="font-medium text-blue-600">
                                    {strategy.performance.signals}
                                  </span>
                                </div>
                                <div className="flex justify-between text-xs">
                                  <span className="text-gray-500">胜率:</span>
                                  <span className="font-medium text-purple-600">
                                    {strategy.performance.winRate}%
                                  </span>
                                </div>
                              </div>
                            )}

                            {/* 标签 */}
                            <div className="flex flex-wrap gap-1 mb-4">
                              {strategy.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>

                            {/* 操作按钮 */}
                            <div className="flex gap-2">
                              <button
                                onClick={() => applyPreset(strategy)}
                                className={`flex-1 px-4 py-2 text-white rounded-lg transition-colors ${strategyColors.button}`}
                              >
                                <div className="flex items-center justify-center gap-2">
                                  <Play className="w-4 h-4" />
                                  <span className="font-medium">应用</span>
                                </div>
                              </button>
                              
                              {!strategy.isDefault && (
                                <>
                                  <button className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors">
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors">
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default StrategyPresetCards;