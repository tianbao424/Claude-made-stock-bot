import React, { useState, useEffect } from 'react';
import { X, Save, RotateCcw, Info, AlertTriangle } from 'lucide-react';

interface ParameterConfig {
  key: string;
  name: string;
  description: string;
  type: 'number' | 'boolean' | 'select' | 'range';
  value: any;
  defaultValue: any;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: any; label: string }[];
  unit?: string;
  validation?: {
    required?: boolean;
    min?: number;
    max?: number;
    message?: string;
  };
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, any>;
  defaultParams: Record<string, any>;
}

// interface SavedParameters {
//   [strategyId: string]: Record<string, any>;
// }

interface Props {
  strategy: Strategy | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (strategyId: string, parameters: Record<string, any>) => void;
}

const StrategyParameterModal: React.FC<Props> = ({ strategy, isOpen, onClose, onSave }) => {
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (strategy) {
      setParameters({ ...strategy.parameters });
      setErrors({});
      setHasChanges(false);
    }
  }, [strategy]);

  if (!isOpen || !strategy) return null;

  // 获取策略的参数配置定义
  const getParameterConfigs = (strategyId: string): ParameterConfig[] => {
    const configMap: Record<string, ParameterConfig[]> = {
      'low_price_filter': [
        {
          key: 'price_threshold',
          name: '价格阈值',
          description: '低于此价格的普通股票将被过滤',
          type: 'number',
          value: parameters.price_threshold || 6.0,
          defaultValue: 6.0,
          min: 1.0,
          max: 20.0,
          step: 0.1,
          unit: '元',
          validation: { required: true, min: 1.0, max: 20.0 }
        }
      ],
      'bank_low_price_filter': [
        {
          key: 'price_threshold',
          name: '银行股价格阈值',
          description: '低于此价格的银行股将被过滤',
          type: 'number',
          value: parameters.price_threshold || 3.5,
          defaultValue: 3.5,
          min: 1.0,
          max: 10.0,
          step: 0.1,
          unit: '元',
          validation: { required: true, min: 1.0, max: 10.0 }
        }
      ],
      'high_position_news_filter': [
        {
          key: 'rise_threshold',
          name: '涨幅警戒线',
          description: '超过此涨幅时需要谨慎',
          type: 'number',
          value: parameters.rise_threshold || 15.0,
          defaultValue: 15.0,
          min: 5.0,
          max: 200.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 5.0, max: 200.0 }
        },
        {
          key: 'safe_threshold',
          name: '安全涨幅线',
          description: '此涨幅以下认为相对安全',
          type: 'number',
          value: parameters.safe_threshold || 10.0,
          defaultValue: 10.0,
          min: 3.0,
          max: 30.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 3.0, max: 30.0 }
        }
      ],
      'ma_deviation_filter': [
        {
          key: 'max_deviation',
          name: '最大偏离度',
          description: '价格偏离均线的最大容忍度',
          type: 'number',
          value: parameters.max_deviation || 20.0,
          defaultValue: 20.0,
          min: 5.0,
          max: 50.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 5.0, max: 50.0 }
        },
        {
          key: 'warning_threshold',
          name: '警告阈值',
          description: '偏离度警告线',
          type: 'number',
          value: parameters.warning_threshold || 15.0,
          defaultValue: 15.0,
          min: 3.0,
          max: 30.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 3.0, max: 30.0 }
        }
      ],
      'volume_ratio_strategy': [
        {
          key: 'high_ratio',
          name: '高量比阈值',
          description: '超过此量比视为放量',
          type: 'number',
          value: parameters.high_ratio || 2.0,
          defaultValue: 2.0,
          min: 1.2,
          max: 10.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.2, max: 10.0 }
        },
        {
          key: 'low_ratio',
          name: '低量比阈值',
          description: '低于此量比视为缩量',
          type: 'number',
          value: parameters.low_ratio || 0.5,
          defaultValue: 0.5,
          min: 0.1,
          max: 1.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 0.1, max: 1.0 }
        }
      ],
      'ma_golden_cross': [
        {
          key: 'short_ma',
          name: '短期均线',
          description: '短期移动平均线的周期',
          type: 'number',
          value: parameters.short_ma || 5,
          defaultValue: 5,
          min: 3,
          max: 10,
          step: 1,
          unit: '日',
          validation: { required: true, min: 3, max: 10 }
        },
        {
          key: 'long_ma',
          name: '长期均线',
          description: '长期移动平均线的周期',
          type: 'number',
          value: parameters.long_ma || 20,
          defaultValue: 20,
          min: 10,
          max: 60,
          step: 1,
          unit: '日',
          validation: { required: true, min: 10, max: 60 }
        },
        {
          key: 'min_volume_ratio',
          name: '最小成交量比率',
          description: '金叉时的最小成交量放大倍数',
          type: 'number',
          value: parameters.min_volume_ratio || 1.2,
          defaultValue: 1.2,
          min: 1.0,
          max: 3.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.0, max: 3.0 }
        }
      ],
      'comprehensive_analysis': [
        {
          key: 'confidence_threshold',
          name: '置信度阈值',
          description: '信号的最低置信度要求',
          type: 'range',
          value: parameters.confidence_threshold || 0.7,
          defaultValue: 0.7,
          min: 0.1,
          max: 1.0,
          step: 0.1,
          unit: '',
          validation: { required: true, min: 0.1, max: 1.0 }
        },
        {
          key: 'signal_threshold',
          name: '信号强度阈值',
          description: '信号的最低强度要求',
          type: 'number',
          value: parameters.signal_threshold || 80,
          defaultValue: 80,
          min: 50,
          max: 100,
          step: 5,
          unit: '分',
          validation: { required: true, min: 50, max: 100 }
        }
      ],
      'turnover_filter': [
        {
          key: 'high_threshold',
          name: '换手率上限',
          description: '换手率过高警戒线',
          type: 'number',
          value: parameters.high_threshold || 30.0,
          defaultValue: 30.0,
          min: 10.0,
          max: 50.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 10.0, max: 50.0 }
        },
        {
          key: 'low_threshold',
          name: '换手率下限',
          description: '换手率过低警戒线',
          type: 'number',
          value: parameters.low_threshold || 0.5,
          defaultValue: 0.5,
          min: 0.1,
          max: 2.0,
          step: 0.1,
          unit: '%',
          validation: { required: true, min: 0.1, max: 2.0 }
        }
      ],
      'gap_up_filter': [
        {
          key: 'gap_threshold',
          name: '跳空幅度',
          description: '跳空高开的最小幅度',
          type: 'number',
          value: parameters.gap_threshold || 3.0,
          defaultValue: 3.0,
          min: 1.0,
          max: 10.0,
          step: 0.5,
          unit: '%',
          validation: { required: true, min: 1.0, max: 10.0 }
        },
        {
          key: 'consecutive_days',
          name: '连续天数',
          description: '连续跳空高开天数',
          type: 'number',
          value: parameters.consecutive_days || 2,
          defaultValue: 2,
          min: 1,
          max: 5,
          step: 1,
          unit: '天',
          validation: { required: true, min: 1, max: 5 }
        }
      ],
      'high_position_filter': [
        {
          key: 'rise_threshold',
          name: '涨幅阈值',
          description: '近期涨幅警戒线',
          type: 'number',
          value: parameters.rise_threshold || 15.0,
          defaultValue: 15.0,
          min: 10.0,
          max: 200.0,
          step: 1.0,
          unit: '%',
          validation: { required: true, min: 10.0, max: 200.0 }
        }
      ],
      'volume_shrink_rise': [
        {
          key: 'volume_ratio',
          name: '缩量比例',
          description: '成交量缩减比例',
          type: 'number',
          value: parameters.volume_ratio || 0.8,
          defaultValue: 0.8,
          min: 0.3,
          max: 0.9,
          step: 0.1,
          unit: '',
          validation: { required: true, min: 0.3, max: 0.9 }
        }
      ],
      'volume_expand_breakout': [
        {
          key: 'volume_ratio',
          name: '放量倍数',
          description: '成交量放大倍数',
          type: 'number',
          value: parameters.volume_ratio || 1.5,
          defaultValue: 1.5,
          min: 1.2,
          max: 5.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.2, max: 5.0 }
        },
        {
          key: 'breakout_percent',
          name: '突破幅度',
          description: '价格突破幅度',
          type: 'number',
          value: parameters.breakout_percent || 3.0,
          defaultValue: 3.0,
          min: 1.0,
          max: 10.0,
          step: 0.5,
          unit: '%',
          validation: { required: true, min: 1.0, max: 10.0 }
        }
      ],
      'trend_momentum': [
        {
          key: 'momentum_threshold',
          name: '动能阈值',
          description: '趋势动能的最小要求',
          type: 'number',
          value: parameters.momentum_threshold || 70,
          defaultValue: 70,
          min: 50,
          max: 100,
          step: 5,
          unit: '',
          validation: { required: true, min: 50, max: 100 }
        }
      ],
      'bid_ask_monitor': [
        {
          key: 'large_order_threshold',
          name: '大单阈值',
          description: '大单的金额门槛',
          type: 'number',
          value: parameters.large_order_threshold || 500000,
          defaultValue: 500000,
          min: 100000,
          max: 5000000,
          step: 100000,
          unit: '元',
          validation: { required: true, min: 100000, max: 5000000 }
        }
      ],
      'late_dive_alert': [
        {
          key: 'dive_threshold',
          name: '跳水幅度',
          description: '尾盘跳水的幅度阈值',
          type: 'number',
          value: parameters.dive_threshold || -3.0,
          defaultValue: -3.0,
          min: -10.0,
          max: -1.0,
          step: 0.5,
          unit: '%',
          validation: { required: true, min: -10.0, max: -1.0 }
        },
        {
          key: 'time_window',
          name: '时间窗口',
          description: '监控开始时间',
          type: 'select',
          value: parameters.time_window || '14:30',
          defaultValue: '14:30',
          options: [
            { value: '14:00', label: '14:00' },
            { value: '14:30', label: '14:30' },
            { value: '14:45', label: '14:45' }
          ],
          validation: { required: true }
        }
      ],
      'white_yellow_divergence': [
        {
          key: 'divergence_threshold',
          name: '乖离度阈值',
          description: '白黄线乖离度警戒值',
          type: 'number',
          value: parameters.divergence_threshold || 2.0,
          defaultValue: 2.0,
          min: 0.5,
          max: 5.0,
          step: 0.1,
          unit: '%',
          validation: { required: true, min: 0.5, max: 5.0 }
        }
      ],
      'dynamic_stop_profit_loss': [
        {
          key: 'profit_target',
          name: '止盈目标',
          description: '动态止盈的目标收益率',
          type: 'number',
          value: parameters.profit_target || 10,
          defaultValue: 10,
          min: 5,
          max: 30,
          step: 1,
          unit: '%',
          validation: { required: true, min: 5, max: 30 }
        },
        {
          key: 'stop_loss',
          name: '止损线',
          description: '动态止损的最大亏损率',
          type: 'number',
          value: parameters.stop_loss || 5,
          defaultValue: 5,
          min: 2,
          max: 10,
          step: 1,
          unit: '%',
          validation: { required: true, min: 2, max: 10 }
        }
      ],
      'position_control': [
        {
          key: 'max_positions',
          name: '最大持仓数',
          description: '同时持有的最大股票数量',
          type: 'number',
          value: parameters.max_positions || 3,
          defaultValue: 3,
          min: 1,
          max: 10,
          step: 1,
          unit: '只',
          validation: { required: true, min: 1, max: 10 }
        }
      ],
      'profit_rest_reminder': [
        {
          key: 'profit_threshold',
          name: '盈利阈值',
          description: '触发休息提醒的盈利率',
          type: 'number',
          value: parameters.profit_threshold || 20,
          defaultValue: 20,
          min: 10,
          max: 50,
          step: 5,
          unit: '%',
          validation: { required: true, min: 10, max: 50 }
        }
      ],
      'trend_reversal': [
        {
          key: 'reversal_threshold',
          name: '反转阈值',
          description: '趋势反转的识别阈值',
          type: 'number',
          value: parameters.reversal_threshold || 0.9,
          defaultValue: 0.9,
          min: 0.5,
          max: 1.0,
          step: 0.1,
          unit: '',
          validation: { required: true, min: 0.5, max: 1.0 }
        },
        {
          key: 'top_threshold',
          name: '顶部阈值',
          description: '顶部反转的识别阈值',
          type: 'number',
          value: parameters.top_threshold || 1.1,
          defaultValue: 1.1,
          min: 1.0,
          max: 1.5,
          step: 0.1,
          unit: '',
          validation: { required: true, min: 1.0, max: 1.5 }
        }
      ],
      'support_resistance': [
        {
          key: 'support_tolerance',
          name: '支撑容差',
          description: '支撑位的容差范围',
          type: 'number',
          value: parameters.support_tolerance || 0.02,
          defaultValue: 0.02,
          min: 0.01,
          max: 0.05,
          step: 0.01,
          unit: '',
          validation: { required: true, min: 0.01, max: 0.05 }
        },
        {
          key: 'resistance_multiplier',
          name: '阻力倍数',
          description: '阻力位的计算倍数',
          type: 'number',
          value: parameters.resistance_multiplier || 1.05,
          defaultValue: 1.05,
          min: 1.01,
          max: 1.10,
          step: 0.01,
          unit: '',
          validation: { required: true, min: 1.01, max: 1.10 }
        }
      ],
      'breakout_strategy': [
        {
          key: 'consolidation_threshold',
          name: '盘整阈值',
          description: '横盘整理的波动范围',
          type: 'number',
          value: parameters.consolidation_threshold || 0.03,
          defaultValue: 0.03,
          min: 0.01,
          max: 0.10,
          step: 0.01,
          unit: '',
          validation: { required: true, min: 0.01, max: 0.10 }
        },
        {
          key: 'breakout_volume',
          name: '突破量能',
          description: '突破时的量能要求',
          type: 'number',
          value: parameters.breakout_volume || 1.8,
          defaultValue: 1.8,
          min: 1.2,
          max: 3.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.2, max: 3.0 }
        }
      ],
      'volume_pattern': [
        {
          key: 'accumulation_threshold',
          name: '吸筹阈值',
          description: '主力吸筹的量能特征',
          type: 'number',
          value: parameters.accumulation_threshold || 1.2,
          defaultValue: 1.2,
          min: 1.0,
          max: 2.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.0, max: 2.0 }
        },
        {
          key: 'stagnation_threshold',
          name: '滞涨阈值',
          description: '量价背离的识别阈值',
          type: 'number',
          value: parameters.stagnation_threshold || 2.0,
          defaultValue: 2.0,
          min: 1.5,
          max: 3.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.5, max: 3.0 }
        }
      ],
      'volume_price_relation': [
        {
          key: 'volume_threshold',
          name: '量能阈值',
          description: '量价配合的量能要求',
          type: 'number',
          value: parameters.volume_threshold || 1.2,
          defaultValue: 1.2,
          min: 1.0,
          max: 3.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.0, max: 3.0 }
        },
        {
          key: 'price_threshold',
          name: '价格阈值',
          description: '量价配合的价格变化要求',
          type: 'number',
          value: parameters.price_threshold || 3.0,
          defaultValue: 3.0,
          min: 1.0,
          max: 10.0,
          step: 0.5,
          unit: '%',
          validation: { required: true, min: 1.0, max: 10.0 }
        }
      ],
      'volume_trend_analysis': [
        {
          key: 'trend_threshold',
          name: '趋势阈值',
          description: '量能趋势的识别阈值',
          type: 'number',
          value: parameters.trend_threshold || 1.2,
          defaultValue: 1.2,
          min: 1.0,
          max: 2.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.0, max: 2.0 }
        },
        {
          key: 'momentum_threshold',
          name: '动量阈值',
          description: '量能动量的最小要求',
          type: 'number',
          value: parameters.momentum_threshold || 1.5,
          defaultValue: 1.5,
          min: 1.0,
          max: 3.0,
          step: 0.1,
          unit: '倍',
          validation: { required: true, min: 1.0, max: 3.0 }
        }
      ],
      'low_volume_low_price': [
        {
          key: 'price_ma_threshold',
          name: '价格均线比',
          description: '价格相对均线的位置',
          type: 'number',
          value: parameters.price_ma_threshold || 1.0,
          defaultValue: 1.0,
          min: 0.8,
          max: 1.2,
          step: 0.05,
          unit: '',
          validation: { required: true, min: 0.8, max: 1.2 }
        },
        {
          key: 'volume_ratio_threshold',
          name: '成交量比率',
          description: '成交量萎缩的比率',
          type: 'number',
          value: parameters.volume_ratio_threshold || 0.8,
          defaultValue: 0.8,
          min: 0.3,
          max: 1.0,
          step: 0.1,
          unit: '',
          validation: { required: true, min: 0.3, max: 1.0 }
        }
      ]
    };

    return configMap[strategyId] || [];
  };

  const parameterConfigs = getParameterConfigs(strategy.id);

  const handleParameterChange = (key: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }));
    setHasChanges(true);
    
    // 清除该字段的错误
    if (errors[key]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  const validateParameters = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    parameterConfigs.forEach(config => {
      const value = parameters[config.key];
      
      if (config.validation?.required && (value === undefined || value === null || value === '')) {
        newErrors[config.key] = '此参数必填';
        return;
      }
      
      if (config.type === 'number' && typeof value === 'number') {
        if (config.validation?.min !== undefined && value < config.validation.min) {
          newErrors[config.key] = `值不能小于 ${config.validation.min}`;
        }
        if (config.validation?.max !== undefined && value > config.validation.max) {
          newErrors[config.key] = `值不能大于 ${config.validation.max}`;
        }
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateParameters()) {
      onSave(strategy.id, parameters);
      onClose();
    }
  };

  const handleReset = () => {
    setParameters({ ...strategy.defaultParams });
    setErrors({});
    setHasChanges(true);
  };

  const renderParameterInput = (config: ParameterConfig) => {
    const hasError = !!errors[config.key];
    
    return (
      <div key={config.key} className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-gray-700">
            {config.name}
            {config.validation?.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          {config.unit && (
            <span className="text-xs text-gray-500">{config.unit}</span>
          )}
        </div>
        
        <div className="space-y-1">
          {config.type === 'number' && (
            <input
              type="number"
              value={config.value}
              onChange={(e) => handleParameterChange(config.key, parseFloat(e.target.value) || 0)}
              min={config.min}
              max={config.max}
              step={config.step}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                hasError ? 'border-red-300' : 'border-gray-300'
              }`}
            />
          )}
          
          {config.type === 'range' && (
            <div className="space-y-2">
              <input
                type="range"
                value={config.value}
                onChange={(e) => handleParameterChange(config.key, parseFloat(e.target.value))}
                min={config.min}
                max={config.max}
                step={config.step}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>{config.min}</span>
                <span className="font-medium">{config.value}</span>
                <span>{config.max}</span>
              </div>
            </div>
          )}
          
          {config.type === 'boolean' && (
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={config.value}
                onChange={(e) => handleParameterChange(config.key, e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">启用</span>
            </label>
          )}
          
          {config.type === 'select' && config.options && (
            <select
              value={config.value}
              onChange={(e) => handleParameterChange(config.key, e.target.value)}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                hasError ? 'border-red-300' : 'border-gray-300'
              }`}
            >
              {config.options.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
          
          {hasError && (
            <div className="flex items-center gap-1 text-red-600 text-xs">
              <AlertTriangle size={14} />
              {errors[config.key]}
            </div>
          )}
        </div>
        
        {config.description && (
          <p className="text-xs text-gray-500 flex items-start gap-1">
            <Info size={12} className="mt-0.5 flex-shrink-0" />
            {config.description}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{strategy.name} - 参数配置</h3>
              <p className="text-sm text-gray-600 mt-1">{strategy.description}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {parameterConfigs.length > 0 ? (
            <div className="space-y-6">
              {parameterConfigs.map(renderParameterInput)}
            </div>
          ) : (
            <div className="text-center py-8">
              <Info size={48} className="text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">暂无可配置参数</h4>
              <p className="text-gray-600">此策略使用默认配置，无需额外参数。</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {parameterConfigs.length > 0 && (
          <div className="border-t px-6 py-4 bg-gray-50">
            <div className="flex items-center justify-between">
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                <RotateCcw size={16} />
                重置为默认
              </button>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={!hasChanges}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    hasChanges
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  <Save size={16} />
                  保存配置
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyParameterModal;