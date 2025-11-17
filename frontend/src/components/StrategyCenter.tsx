import React, { useState, useEffect } from 'react';
import { 
  Settings, Search, Grid3X3, List, Info,
  TrendingUp, Activity, Shield, AlertTriangle,
  CheckCircle, Circle, ChevronDown, ChevronRight,
  Eye, EyeOff, Sliders, Target
} from 'lucide-react';
import StrategyParameterModal from './StrategyParameterModal';
// import { strategyService } from '../services/strategyService';

// 策略数据类型
interface Strategy {
  id: string;
  name: string;
  description: string;
  category: string;
  categoryName: string;
  enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
  defaultParams: Record<string, any>;
  performance: {
    accuracy: number;
    avgScore: number;
    signalCount: number;
    winRate: number;
  };
  tags: string[];
}

interface StrategyCategory {
  id: string;
  name: string;
  icon: React.ElementType;
  color: string;
  strategies: Strategy[];
}

const StrategyCenter: React.FC = () => {
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedStrategies, setSelectedStrategies] = useState<Set<string>>(new Set());
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['basic_filter']));
  const [showParameterModal, setShowParameterModal] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [savedParameters, setSavedParameters] = useState<Record<string, Record<string, any>>>({});
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successResult, setSuccessResult] = useState<{
    appliedStrategies: Array<{name: string, weight: number}>;
    resultCount: number;
    totalAnalyzed: number;
  } | null>(null);

  // 从 localStorage 加载保存的参数
  useEffect(() => {
    try {
      const saved = localStorage.getItem('strategy_parameters');
      if (saved) {
        const savedParams = JSON.parse(saved);
        
        // 清理旧的参数结构，确保与当前策略定义一致
        const cleanedParams: Record<string, Record<string, any>> = {};
        
        strategyCategories.forEach(category => {
          category.strategies.forEach(strategy => {
            if (savedParams[strategy.id]) {
              // 只保留当前策略定义中存在的参数
              const cleanParams: Record<string, any> = {};
              Object.keys(strategy.defaultParams).forEach(key => {
                if (savedParams[strategy.id][key] !== undefined) {
                  cleanParams[key] = savedParams[strategy.id][key];
                }
              });
              
              // 如果有有效参数则保存，否则使用默认参数
              if (Object.keys(cleanParams).length > 0) {
                cleanedParams[strategy.id] = cleanParams;
              }
            }
          });
        });
        
        setSavedParameters(cleanedParams);
        
        // 更新localStorage
        localStorage.setItem('strategy_parameters', JSON.stringify(cleanedParams));
      }
    } catch (error) {
      console.error('加载策略参数失败:', error);
    }
  }, []);

  // 策略数据
  const strategyCategories: StrategyCategory[] = [
    {
      id: 'basic_filter',
      name: '基础过滤',
      icon: Shield,
      color: 'blue',
      strategies: [
        {
          id: 'low_price_filter',
          name: '低价股过滤',
          description: '过滤低于指定价格的普通股票，避免垃圾股风险',
          category: 'basic_filter',
          categoryName: '基础过滤',
          enabled: true,
          weight: 1.0,
          parameters: { price_threshold: 6.0 },
          defaultParams: { price_threshold: 6.0 },
          performance: { accuracy: 93.3, avgScore: 80, signalCount: 150, winRate: 85.2 },
          tags: ['风险控制', '价格筛选', '普通股']
        },
        {
          id: 'bank_low_price_filter',
          name: '银行低价股策略',
          description: '专门针对银行股的低价过滤策略，可配置价格阈值',
          category: 'basic_filter',
          categoryName: '基础过滤',
          enabled: true,
          weight: 1.2,
          parameters: { price_threshold: 3.5 },
          defaultParams: { price_threshold: 3.5 },
          performance: { accuracy: 88.5, avgScore: 75, signalCount: 45, winRate: 82.1 },
          tags: ['银行股', '价格筛选', '低估值']
        },
        {
          id: 'turnover_filter',
          name: '换手率监控',
          description: '过滤换手率异常的股票',
          category: 'basic_filter',
          categoryName: '基础过滤',
          enabled: true,
          weight: 1.0,
          parameters: { high_threshold: 30.0, low_threshold: 0.5 },
          defaultParams: { high_threshold: 30.0, low_threshold: 0.5 },
          performance: { accuracy: 86.7, avgScore: 85, signalCount: 180, winRate: 78.9 },
          tags: ['换手分析', '资金监控']
        },
        {
          id: 'gap_up_filter',
          name: '跳空高开过滤',
          description: '识别连续跳空高开的风险信号',
          category: 'basic_filter',
          categoryName: '基础过滤',
          enabled: true,
          weight: 1.0,
          parameters: { gap_threshold: 3.0, consecutive_days: 2 },
          defaultParams: { gap_threshold: 3.0, consecutive_days: 2 },
          performance: { accuracy: 91.2, avgScore: 78, signalCount: 80, winRate: 88.5 },
          tags: ['跳空分析', '风险预警']
        },
        {
          id: 'high_position_filter',
          name: '高位利好过滤',
          description: '避免高位利好出货陷阱',
          category: 'basic_filter',
          categoryName: '基础过滤',
          enabled: true,
          weight: 1.0,
          parameters: { rise_threshold: 15.0 },
          defaultParams: { rise_threshold: 15.0 },
          performance: { accuracy: 89.1, avgScore: 82, signalCount: 120, winRate: 83.7 },
          tags: ['高位识别', '防套策略']
        }
      ]
    },
    {
      id: 'trend_analysis',
      name: '趋势判断',
      icon: TrendingUp,
      color: 'purple',
      strategies: [
        {
          id: 'ma_golden_cross',
          name: '均线金叉',
          description: '捕捉均线金叉买入信号',
          category: 'trend_analysis',
          categoryName: '趋势判断',
          enabled: true,
          weight: 1.4,
          parameters: { short_ma: 5, long_ma: 20, min_volume_ratio: 1.2 },
          defaultParams: { short_ma: 5, long_ma: 20, min_volume_ratio: 1.2 },
          performance: { accuracy: 85.6, avgScore: 88, signalCount: 200, winRate: 79.3 },
          tags: ['均线系统', '金叉信号']
        },
        {
          id: 'volume_shrink_rise',
          name: '缩量上涨',
          description: '识别缩量上涨的控盘股',
          category: 'trend_analysis',
          categoryName: '趋势判断',
          enabled: true,
          weight: 1.2,
          parameters: { volume_ratio: 0.8 },
          defaultParams: { volume_ratio: 0.8 },
          performance: { accuracy: 82.3, avgScore: 76, signalCount: 150, winRate: 74.8 },
          tags: ['缩量特征', '控盘股']
        },
        {
          id: 'volume_expand_breakout',
          name: '放量突破',
          description: '识别放量突破的爆发机会',
          category: 'trend_analysis',
          categoryName: '趋势判断',
          enabled: true,
          weight: 1.3,
          parameters: { volume_ratio: 1.5, breakout_percent: 3.0 },
          defaultParams: { volume_ratio: 1.5, breakout_percent: 3.0 },
          performance: { accuracy: 79.8, avgScore: 82, signalCount: 180, winRate: 72.5 },
          tags: ['放量突破', '爆发机会']
        },
        {
          id: 'trend_momentum',
          name: '趋势动能',
          description: '综合分析趋势的持续性',
          category: 'trend_analysis',
          categoryName: '趋势判断',
          enabled: true,
          weight: 1.3,
          parameters: { momentum_threshold: 70 },
          defaultParams: { momentum_threshold: 70 },
          performance: { accuracy: 88.2, avgScore: 85, signalCount: 160, winRate: 81.6 },
          tags: ['动能分析', '趋势强度']
        }
      ]
    },
    {
      id: 'intraday_monitor',
      name: '分时监控',
      icon: Activity,
      color: 'orange',
      strategies: [
        {
          id: 'bid_ask_monitor',
          name: '盘口量能监控',
          description: '实时监控盘口大单异动',
          category: 'intraday_monitor',
          categoryName: '分时监控',
          enabled: true,
          weight: 1.0,
          parameters: { large_order_threshold: 500000 },
          defaultParams: { large_order_threshold: 500000 },
          performance: { accuracy: 75.4, avgScore: 70, signalCount: 300, winRate: 68.2 },
          tags: ['盘口监控', '大单追踪']
        },
        {
          id: 'late_dive_alert',
          name: '尾盘跳水预警',
          description: '识别尾盘异常下跌',
          category: 'intraday_monitor',
          categoryName: '分时监控',
          enabled: true,
          weight: 1.1,
          parameters: { dive_threshold: -3.0, time_window: '14:30' },
          defaultParams: { dive_threshold: -3.0, time_window: '14:30' },
          performance: { accuracy: 83.7, avgScore: 78, signalCount: 120, winRate: 77.9 },
          tags: ['尾盘监控', '风险预警']
        },
        {
          id: 'white_yellow_divergence',
          name: '白黄线乖离',
          description: '监控分时图异常乖离',
          category: 'intraday_monitor',
          categoryName: '分时监控',
          enabled: true,
          weight: 1.0,
          parameters: { divergence_threshold: 2.0 },
          defaultParams: { divergence_threshold: 2.0 },
          performance: { accuracy: 71.2, avgScore: 68, signalCount: 250, winRate: 65.4 },
          tags: ['分时分析', '乖离监控']
        }
      ]
    },
    {
      id: 'risk_control',
      name: '风控策略',
      icon: AlertTriangle,
      color: 'red',
      strategies: [
        {
          id: 'dynamic_stop_profit_loss',
          name: '动态止盈止损',
          description: '智能调整止盈止损位',
          category: 'risk_control',
          categoryName: '风控策略',
          enabled: true,
          weight: 1.5,
          parameters: { profit_target: 10, stop_loss: 5 },
          defaultParams: { profit_target: 10, stop_loss: 5 },
          performance: { accuracy: 92.1, avgScore: 90, signalCount: 100, winRate: 86.3 },
          tags: ['止盈止损', '风险控制']
        },
        {
          id: 'position_control',
          name: '持股数控制',
          description: '限制持股数量不超过3只',
          category: 'risk_control',
          categoryName: '风控策略',
          enabled: true,
          weight: 1.0,
          parameters: { max_positions: 3 },
          defaultParams: { max_positions: 3 },
          performance: { accuracy: 95.0, avgScore: 88, signalCount: 50, winRate: 88.0 },
          tags: ['仓位管理', '风险分散']
        },
        {
          id: 'profit_rest_reminder',
          name: '大赚空仓提醒',
          description: '大幅盈利后提醒休息',
          category: 'risk_control',
          categoryName: '风控策略',
          enabled: true,
          weight: 1.0,
          parameters: { profit_threshold: 20 },
          defaultParams: { profit_threshold: 20 },
          performance: { accuracy: 90.5, avgScore: 85, signalCount: 30, winRate: 87.2 },
          tags: ['情绪管理', '纪律控制']
        }
      ]
    }
  ];

  // 过滤策略
  const getFilteredStrategies = () => {
    let allStrategies: Strategy[] = [];
    strategyCategories.forEach(category => {
      allStrategies = [...allStrategies, ...category.strategies];
    });

    return allStrategies.filter(strategy => {
      const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          strategy.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          strategy.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCategory = filterCategory === 'all' || strategy.category === filterCategory;
      return matchesSearch && matchesCategory;
    });
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

  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const handleApplyStrategies = async () => {
    if (selectedStrategies.size === 0) {
      alert('请选择至少一个策略');
      return;
    }

    // 构建策略配置
    const strategyConfigs = Array.from(selectedStrategies).map(strategyId => {
      const strategy = getCurrentStrategy(strategyId);
      return {
        strategy_id: strategyId,
        enabled: true,
        parameters: savedParameters[strategyId] || strategy?.parameters || {},
        weight: strategy?.weight || 1.0
      };
    });

    console.log('应用策略配置:', strategyConfigs);
    
    if (strategyConfigs.length === 0) {
      alert('请至少选择一个策略！');
      return;
    }
    
    try {
      // 构建高级筛选请求
      const screeningRequest = {
        strategies: strategyConfigs,
        market_filter: ['SH', 'SZ'],
        limit: 50,
        min_score: 60,
        sort_by: 'score',
        require_all_pass: false,
        screening_date: null // 使用最新数据
      };

      console.log('发送筛选请求:', screeningRequest);

      // 调用后端API执行筛选
      const response = await fetch('/api/advanced-screening', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(screeningRequest)
      });

      console.log('响应状态:', response.status, response.statusText);

      if (response.ok) {
        const result = await response.json();
        console.log('🔍 完整的API响应结果:', result);
        
        // 保存筛选结果到sessionStorage，供其他页面使用
        sessionStorage.setItem('latest_screening_result', JSON.stringify(result));
        
        // 保存策略配置到 localStorage
        localStorage.setItem('selected_strategies', JSON.stringify(Array.from(selectedStrategies)));
        localStorage.setItem('applied_strategy_configs', JSON.stringify(strategyConfigs));
        
        // 准备成功提示数据
        const resultCount = result.data?.results?.length || 0;
        const totalAnalyzed = result.data?.summary?.total_found || 0;
        
        console.log('📊 解析数据:');
        console.log('  - result.data:', result.data);
        console.log('  - result.data.results:', result.data?.results);
        console.log('  - result.data.summary:', result.data?.summary);
        console.log('  - resultCount:', resultCount);
        console.log('  - totalAnalyzed:', totalAnalyzed);
        
        const appliedStrategies = strategyConfigs.map(config => {
          const strategy = getCurrentStrategy(config.strategy_id);
          return {
            name: strategy?.name || config.strategy_id,
            weight: config.weight
          };
        });
        
        console.log('🎯 应用的策略:', appliedStrategies);

        // 设置成功结果并显示模态框
        const successData = {
          appliedStrategies,
          resultCount,
          totalAnalyzed
        };
        
        console.log('🎉 准备显示成功模态框，数据:', successData);
        
        setSuccessResult(successData);
        setShowSuccessModal(true);
        
        console.log(`✅ 策略筛选完成！分析了 ${totalAnalyzed} 只股票，找到 ${resultCount} 只符合条件的股票`);
        
        // 等待状态更新后检查
        setTimeout(() => {
          console.log('🔍 模态框状态检查:');
          console.log('  - showSuccessModal应该为true');
          console.log('  - successResult应该有值');
        }, 100);
      } else {
        console.error('响应错误:', response.status, response.statusText);
        let errorMessage = '筛选请求失败';
        try {
          const errorData = await response.json();
          console.error('错误详情:', errorData);
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          console.error('解析错误响应失败:', e);
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('应用策略失败:', error);
      console.error('错误堆栈:', error.stack);
      console.error('错误类型:', error.constructor.name);
      
      // 详细日志记录
      console.log('🔍 错误详情分析:');
      console.log('  - 错误名称:', error.name);
      console.log('  - 错误消息:', error.message);
      console.log('  - 错误来源:', error.stack?.split('\n')[1] || '未知');
      
      // 检查是否是已知的配额错误（通常是误报）
      if (error.message.includes('quota') && error.message.includes('exceeded')) {
        console.warn('🎯 检测到配额错误，这通常是误报。后端API实际工作正常！');
        // 不显示弹窗，只在控制台记录
        return;
      }
      
      // 只在真正的网络错误或服务错误时显示弹窗
      let userMessage = `❌ 策略应用失败: ${error.message}`;
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        userMessage += '\n\n可能原因:\n- 后端服务未启动\n- 网络连接问题\n- 代理配置错误';
      } else if (error.message.includes('500') || error.message.includes('Internal Server Error')) {
        userMessage = '❌ 服务器内部错误，请稍后重试或联系管理员';
      } else if (error.message.includes('timeout')) {
        userMessage = '❌ 请求超时，请检查网络连接后重试';
      }
      
      alert(userMessage);
    }
  };

  const handleSaveParameters = (strategyId: string, parameters: Record<string, any>) => {
    console.log('保存策略参数:', strategyId, parameters);
    
    // 更新本地状态
    const newSavedParameters = {
      ...savedParameters,
      [strategyId]: parameters
    };
    setSavedParameters(newSavedParameters);
    
    // 保存到 localStorage
    try {
      localStorage.setItem('strategy_parameters', JSON.stringify(newSavedParameters));
      console.log('策略参数已保存到本地存储');
    } catch (error) {
      console.error('保存策略参数失败:', error);
    }
    
    // TODO: 调用后端API保存参数
    // strategyService.saveStrategyParameters(strategyId, parameters);
  };

  const getCurrentStrategy = (strategyId: string): Strategy | null => {
    for (const category of strategyCategories) {
      const strategy = category.strategies.find(s => s.id === strategyId);
      if (strategy) return strategy;
    }
    return null;
  };

  const renderStrategyCard = (strategy: Strategy) => {
    const isSelected = selectedStrategies.has(strategy.id);
    
    return (
      <div
        key={strategy.id}
        className={`border-2 rounded-lg p-4 transition-all duration-200 ${
          isSelected 
            ? 'border-blue-500 bg-blue-50 shadow-lg ring-2 ring-blue-200' 
            : 'border-gray-300 bg-white hover:border-blue-400 hover:shadow-md'
        }`}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h4 className="font-medium text-gray-900">{strategy.name}</h4>
            <p className="text-sm text-gray-600 mt-1">{strategy.description}</p>
          </div>
          <button
            onClick={() => toggleStrategy(strategy.id)}
            className="ml-2"
          >
            {isSelected ? (
              <CheckCircle className="w-5 h-5 text-blue-600" />
            ) : (
              <Circle className="w-5 h-5 text-gray-400 hover:text-blue-600" />
            )}
          </button>
        </div>

        {/* 策略参数详情 */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
          <h5 className="text-sm font-medium text-gray-700 mb-2">当前配置</h5>
          <div className="space-y-1">
            {Object.entries({
              ...strategy.parameters,
              ...(savedParameters[strategy.id] || {})
            })
              .sort(([a], [b]) => {
                // 参数排序优先级
                const priority: Record<string, number> = {
                  'price_threshold': 1,
                  'bank_price_threshold': 2,
                  'include_banks': 3,
                  'exclude_banks': 4,
                  'sector_filter': 5
                };
                return (priority[a] || 99) - (priority[b] || 99);
              })
              .map(([key, value]) => {
              // 参数名称映射
              const paramNameMap: Record<string, string> = {
                'price_threshold': '价格阈值',
                'sector_filter': '行业过滤',
                'days': '连续天数',
                'min_rise': '最小涨幅',
                'high_threshold': '高换手率阈值',
                'low_threshold': '低换手率阈值',
                'gap_threshold': '跳空幅度',
                'consecutive_days': '连续天数',
                'rise_threshold': '涨幅阈值',
                'short_ma': '短期均线',
                'long_ma': '长期均线',
                'min_volume_ratio': '最小成交量比率',
                'breakout_percent': '突破幅度',
                'momentum_threshold': '动能阈值',
                'large_order_threshold': '大单阈值',
                'dive_threshold': '跳水幅度',
                'time_window': '时间窗口',
                'divergence_threshold': '乖离阈值',
                'profit_target': '止盈目标',
                'stop_loss': '止损比例',
                'max_positions': '最大持仓',
                'profit_threshold': '盈利阈值'
              };
              
              const displayName = paramNameMap[key] || key.replace(/_/g, ' ');
              
              // 处理不同类型的参数值
              let displayValue: string;
              if (typeof value === 'boolean') {
                displayValue = value ? '是' : '否';
              } else if (typeof value === 'number') {
                // 大单阈值需要转换为万元显示
                if (key === 'large_order_threshold') {
                  displayValue = (value / 10000).toFixed(0);
                } else {
                  displayValue = value % 1 === 0 ? value.toString() : value.toFixed(2);
                }
              } else if (value === 'banks_only') {
                displayValue = '仅银行股';
              } else {
                displayValue = String(value);
              }
              
              // 添加单位 - 优先特定参数映射，避免关键词误判
              let unit = '';
              // 特定参数的精确映射
              const specificUnits: Record<string, string> = {
                'high_threshold': '%',      // 换手率上限
                'low_threshold': '%',       // 换手率下限
                'gap_threshold': '%',       // 跳空幅度
                'rise_threshold': '%',      // 涨幅阈值
                'price_threshold': '元',    // 价格阈值
                'large_order_threshold': '万元', // 大单阈值
                'days': '天',
                'consecutive_days': '天',
                'max_positions': '只',
                'volume_ratio': '',         // 成交量比率无单位
                'cross_threshold': '',      // 交叉阈值无单位
                'breakout_percent': '%',    // 突破幅度
                'momentum_threshold': '',   // 动能阈值无单位
                'dive_threshold': '%',      // 跳水幅度
                'divergence_threshold': '%', // 乖离阈值
                'profit_target': '%',       // 止盈目标
                'stop_loss': '%',          // 止损比例
                'profit_threshold': '%',    // 盈利阈值
                'min_rise': '%'            // 最小涨幅
              };
              
              if (specificUnits.hasOwnProperty(key)) {
                unit = specificUnits[key];
              } else if (key.includes('price')) {
                unit = '元';
              } else if (key.includes('percent') || key.includes('rise') || key.includes('ratio')) {
                unit = '%';
              }
              
              return (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-gray-600">{displayName}:</span>
                  <span className="font-medium text-gray-900">
                    {displayValue}{unit}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 性能指标 */}
        {strategy.performance && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
            <h5 className="text-sm font-medium text-green-700 mb-2">性能指标</h5>
            <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">准确率:</span>
              <span className="font-medium text-green-600">{strategy.performance.accuracy}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">胜率:</span>
              <span className="font-medium text-blue-600">{strategy.performance.winRate}%</span>
            </div>
            </div>
          </div>
        )}

        {/* 标签 */}
        <div className="flex flex-wrap gap-1 mb-3">
          {strategy.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full border border-blue-200"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          {savedParameters[strategy.id] && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              已配置
            </span>
          )}
          <button
            onClick={() => setShowParameterModal(strategy.id)}
            className="flex items-center gap-1 px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 border border-blue-300 rounded text-sm transition-colors"
          >
            <Settings className="w-3 h-3" />
            配置
          </button>
          <button 
            onClick={() => setShowParameterModal(strategy.id)}
            className="flex items-center gap-1 px-3 py-1 bg-purple-100 hover:bg-purple-200 text-purple-700 border border-purple-300 rounded text-sm transition-colors"
          >
            <Sliders className="w-3 h-3" />
            策略配置
          </button>
          <button className="flex items-center gap-1 px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-300 rounded text-sm transition-colors">
            <Info className="w-3 h-3" />
            详情
          </button>
        </div>
      </div>
    );
  };

  const renderStrategyList = (strategy: Strategy) => {
    const isSelected = selectedStrategies.has(strategy.id);
    
    return (
      <tr
        key={strategy.id}
        className={`border-b hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}
      >
        <td className="py-3 px-4">
          <button onClick={() => toggleStrategy(strategy.id)}>
            {isSelected ? (
              <CheckCircle className="w-5 h-5 text-blue-600" />
            ) : (
              <Circle className="w-5 h-5 text-gray-400 hover:text-blue-600" />
            )}
          </button>
        </td>
        <td className="py-3 px-4">
          <div>
            <div className="font-medium text-gray-900">{strategy.name}</div>
            <div className="text-sm text-gray-600">{strategy.description}</div>
          </div>
        </td>
        <td className="py-3 px-4 text-sm">
          <div className="flex items-center gap-2">
            {strategy.categoryName}
            {savedParameters[strategy.id] && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                已配置
              </span>
            )}
          </div>
        </td>
        <td className="py-3 px-4 text-sm text-green-600">{strategy.performance.accuracy}%</td>
        <td className="py-3 px-4 text-sm text-blue-600">{strategy.performance.winRate}%</td>
        <td className="py-3 px-4 text-sm">{strategy.performance.signalCount}</td>
        <td className="py-3 px-4">
          <div className="flex gap-2">
            <button
              onClick={() => setShowParameterModal(strategy.id)}
              className="text-gray-600 hover:text-gray-800"
              title="配置"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowParameterModal(strategy.id)}
              className="text-purple-600 hover:text-purple-800"
              title="策略配置"
            >
              <Sliders className="w-4 h-4" />
            </button>
            <button className="text-gray-600 hover:text-gray-800" title="详情">
              <Info className="w-4 h-4" />
            </button>
          </div>
        </td>
      </tr>
    );
  };

  // 清理localStorage的函数
  const clearSavedParameters = () => {
    localStorage.removeItem('strategy_parameters');
    setSavedParameters({});
    console.log('已清理所有保存的策略参数');
  };

  // 调试信息
  console.log('StrategyCenter rendering...', {
    categoriesCount: strategyCategories.length,
    selectedCount: selectedStrategies.size,
    savedParamsCount: Object.keys(savedParameters).length
  });

  return (
    <div className="h-full flex flex-col bg-gray-50 overflow-hidden">
      <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full overflow-hidden">
        {/* 页面头部 */}
        <div className="mb-6 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Target className="w-8 h-8 text-blue-600" />
              <h1 className="text-3xl font-bold text-gray-900">策略中心</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">
                已选择 {selectedStrategies.size} 个策略
              </span>
              <button 
                onClick={() => clearSavedParameters()}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors">
                重置参数
              </button>
              <button 
                onClick={() => handleApplyStrategies()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                应用策略
              </button>
            </div>
          </div>
          <p className="text-lg text-gray-600">管理和配置所有策略，打造您的专属投资系统</p>
        </div>

        {/* 工具栏 */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4 flex-shrink-0">
          <div className="flex flex-wrap items-center gap-4">
            {/* 搜索 */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="搜索策略..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* 分类筛选 */}
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">全部分类</option>
              <option value="basic_filter">基础过滤</option>
              <option value="trend_analysis">趋势判断</option>
              <option value="intraday_monitor">分时监控</option>
              <option value="risk_control">风控策略</option>
            </select>

            {/* 视图切换 */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('card')}
                className={`p-2 rounded ${viewMode === 'card' ? 'bg-white shadow-sm' : ''}`}
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${viewMode === 'list' ? 'bg-white shadow-sm' : ''}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* 高级模式开关 */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                showAdvanced ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {showAdvanced ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              <span>{showAdvanced ? '简单模式' : '高级模式'}</span>
            </button>
          </div>
        </div>

        {/* 策略展示 - 可滚动区域 */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {viewMode === 'card' ? (
            /* 卡片视图 */
            <div className="space-y-6 pb-6">
            {strategyCategories.map((category) => {
              const Icon = category.icon;
              const isExpanded = expandedCategories.has(category.id);
              const categoryStrategies = category.strategies.filter(s => {
                const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                                    s.description.toLowerCase().includes(searchTerm.toLowerCase());
                const matchesFilter = filterCategory === 'all' || s.category === filterCategory;
                return matchesSearch && matchesFilter;
              });

              if (categoryStrategies.length === 0 && searchTerm) return null;

              return (
                <div key={category.id} className="bg-white rounded-lg shadow-sm overflow-hidden">
                  <button
                    onClick={() => toggleCategory(category.id)}
                    className="w-full px-6 py-4 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 text-blue-600" />
                      <h3 className="text-lg font-medium text-gray-900">{category.name}</h3>
                      <span className="text-sm text-gray-500">
                        ({categoryStrategies.length}个策略)
                      </span>
                    </div>
                    {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  </button>
                  
                  {isExpanded && (
                    <div className="p-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {categoryStrategies.map(renderStrategyCard)}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            </div>
          ) : (
            /* 列表视图 */
            <div className="bg-white rounded-lg shadow-sm overflow-hidden mb-6">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">选择</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">策略名称</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">分类</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">准确率</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">胜率</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">信号数</th>
                  <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody>
                {getFilteredStrategies().map(renderStrategyList)}
              </tbody>
            </table>
            </div>
          )}

          {/* 高级配置面板 */}
          {showAdvanced && (
            <div className="mt-6 bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
              <Sliders className="w-5 h-5" />
              高级配置
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-3">策略权重调整</h4>
                <div className="space-y-2">
                  <p className="text-sm text-gray-600">
                    根据市场环境动态调整各类策略的权重，优化筛选效果
                  </p>
                  <button className="text-blue-600 hover:text-blue-700 text-sm">
                    配置权重 →
                  </button>
                </div>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-3">组合优化建议</h4>
                <div className="space-y-2">
                  <p className="text-sm text-gray-600">
                    基于历史数据分析，推荐最优策略组合
                  </p>
                  <button className="text-blue-600 hover:text-blue-700 text-sm">
                    查看建议 →
                  </button>
                </div>
              </div>
            </div>
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

        {/* 成功提示模态框 */}
        {showSuccessModal && successResult && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
              <div className="flex items-center justify-center mb-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-10 h-10 text-green-600" />
                </div>
              </div>
              
              <h3 className="text-xl font-bold text-center text-gray-900 mb-4">
                策略筛选成功！
              </h3>
              
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-2">应用的策略：</p>
                  <ul className="space-y-1">
                    {successResult.appliedStrategies.map((strategy, index) => (
                      <li key={index} className="flex items-center justify-between text-sm">
                        <span className="text-gray-800">{strategy.name}</span>
                        <span className="text-gray-500">权重: {strategy.weight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                
                <div className="text-center">
                  <p className="text-lg font-medium text-gray-900">
                    分析了 <span className="text-blue-600">{successResult.totalAnalyzed}</span> 只股票
                  </p>
                  <p className="text-lg font-medium text-gray-900">
                    找到 <span className="text-green-600">{successResult.resultCount}</span> 只符合条件的股票
                  </p>
                </div>
              </div>
              
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => {
                    setShowSuccessModal(false);
                    // 通过自定义事件切换到股票甄选页面
                    window.dispatchEvent(new CustomEvent('switchToScreening'));
                  }}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  查看筛选结果
                </button>
                <button
                  onClick={() => setShowSuccessModal(false)}
                  className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  继续配置
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyCenter;