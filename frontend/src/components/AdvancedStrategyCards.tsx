import React, { useState } from 'react';
import { 
  Settings, Info,
  TrendingUp, Activity, BarChart3, Shield, Brain,
  Target, CheckCircle, Circle, Star
} from 'lucide-react';
import StrategyParameterModal from './StrategyParameterModal';

// 策略卡片数据类型
interface StrategyCard {
  id: string;
  name: string;
  shortName: string;
  description: string;
  category: string;
  categoryName: string;
  categoryIcon: React.ElementType;
  categoryColor: string;
  enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
  defaultParams: Record<string, any>;
  performance: {
    accuracy: number;
    avgScore: number;
    signalCount: number;
    winRate: number;
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  };
  tags: string[];
  level: 'BASIC' | 'INTERMEDIATE' | 'ADVANCED';
}

interface QuickTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  strategies: string[];
}

const AdvancedStrategyCards: React.FC = () => {
  const [selectedStrategies, setSelectedStrategies] = useState<Set<string>>(new Set());
  const [showParameterModal, setShowParameterModal] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'performance' | 'signals'>('performance');

  // 策略卡片数据
  const strategyCards: StrategyCard[] = [
    // 基础过滤策略
    {
      id: 'low_price_filter',
      name: '低价股过滤器',
      shortName: '低价过滤',
      description: '智能识别并过滤低于安全价格阈值的股票，有效规避垃圾股风险',
      category: 'basic_filter',
      categoryName: '基础过滤',
      categoryIcon: Shield,
      categoryColor: 'blue',
      enabled: true,
      weight: 1.0,
      parameters: { price_threshold: 6.0, bank_threshold: 3.0 },
      defaultParams: { price_threshold: 6.0, bank_threshold: 3.0 },
      performance: { accuracy: 93.3, avgScore: 80, signalCount: 150, winRate: 85.2, riskLevel: 'LOW' },
      tags: ['风险控制', '价格筛选', '基础策略'],
      level: 'BASIC'
    },
    {
      id: 'high_position_news_filter',
      name: '高位利好过滤器',
      shortName: '高位过滤',
      description: '识别高位利好出货陷阱，避免在主力获利回吐期接盘',
      category: 'basic_filter',
      categoryName: '基础过滤',
      categoryIcon: Shield,
      categoryColor: 'blue',
      enabled: true,
      weight: 1.0,
      parameters: { rise_threshold: 15.0, safe_threshold: 10.0 },
      defaultParams: { rise_threshold: 15.0, safe_threshold: 10.0 },
      performance: { accuracy: 93.3, avgScore: 75, signalCount: 120, winRate: 88.5, riskLevel: 'LOW' },
      tags: ['风险控制', '利好识别', '防套策略'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'ma_deviation_filter',
      name: '均线偏离检测器',
      shortName: '偏离检测',
      description: '监控股价相对均线的偏离程度，防止追高被套',
      category: 'basic_filter',
      categoryName: '基础过滤',
      categoryIcon: Shield,
      categoryColor: 'blue',
      enabled: true,
      weight: 1.0,
      parameters: { max_deviation: 20.0, warning_threshold: 15.0 },
      defaultParams: { max_deviation: 20.0, warning_threshold: 15.0 },
      performance: { accuracy: 93.3, avgScore: 85, signalCount: 200, winRate: 82.1, riskLevel: 'LOW' },
      tags: ['均线分析', '风险控制', '技术指标'],
      level: 'BASIC'
    },
    {
      id: 'gap_up_filter',
      name: '跳空风险识别器',
      shortName: '跳空识别',
      description: '识别连续跳空高开模式，预警追高风险',
      category: 'basic_filter',
      categoryName: '基础过滤',
      categoryIcon: Shield,
      categoryColor: 'blue',
      enabled: true,
      weight: 1.0,
      parameters: { gap_threshold: 3.0, consecutive_days: 3 },
      defaultParams: { gap_threshold: 3.0, consecutive_days: 3 },
      performance: { accuracy: 100, avgScore: 75, signalCount: 80, winRate: 90.0, riskLevel: 'LOW' },
      tags: ['跳空分析', '风险预警', '形态识别'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'turnover_filter',
      name: '换手率监控器',
      shortName: '换手监控',
      description: '监控异常换手率，识别主力资金异动',
      category: 'basic_filter',
      categoryName: '基础过滤',
      categoryIcon: Shield,
      categoryColor: 'blue',
      enabled: true,
      weight: 1.0,
      parameters: { high_threshold: 30.0, low_threshold: 0.5 },
      defaultParams: { high_threshold: 30.0, low_threshold: 0.5 },
      performance: { accuracy: 86.7, avgScore: 85, signalCount: 180, winRate: 78.9, riskLevel: 'MEDIUM' },
      tags: ['换手分析', '资金监控', '量能分析'],
      level: 'BASIC'
    },

    // 量价关系策略
    {
      id: 'volume_ratio_strategy',
      name: '智能量比分析器',
      shortName: '量比分析',
      description: '多维度量比分析，识别主力资金动向和异常交易信号',
      category: 'volume_price',
      categoryName: '量价关系',
      categoryIcon: BarChart3,
      categoryColor: 'green',
      enabled: true,
      weight: 0.8,
      parameters: { high_ratio: 2.0, low_ratio: 0.5, new_high_ratio: 1.5 },
      defaultParams: { high_ratio: 2.0, low_ratio: 0.5, new_high_ratio: 1.5 },
      performance: { accuracy: 100, avgScore: 80, signalCount: 250, winRate: 76.5, riskLevel: 'MEDIUM' },
      tags: ['量比分析', '主力监控', '资金流向'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'volume_price_relation',
      name: '量价协调分析器',
      shortName: '量价协调',
      description: '深度分析成交量与价格变化的协调性，判断趋势可持续性',
      category: 'volume_price',
      categoryName: '量价关系',
      categoryIcon: BarChart3,
      categoryColor: 'green',
      enabled: true,
      weight: 0.8,
      parameters: { volume_threshold: 1.2, price_threshold: 3.0 },
      defaultParams: { volume_threshold: 1.2, price_threshold: 3.0 },
      performance: { accuracy: 86.7, avgScore: 60, signalCount: 300, winRate: 72.8, riskLevel: 'MEDIUM' },
      tags: ['量价配合', '趋势分析', '协调性'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'volume_trend_analysis',
      name: '量能趋势追踪器',
      shortName: '量能追踪',
      description: '追踪成交量变化趋势，识别资金流入流出方向',
      category: 'volume_price',
      categoryName: '量价关系',
      categoryIcon: BarChart3,
      categoryColor: 'green',
      enabled: true,
      weight: 0.8,
      parameters: { trend_threshold: 1.2, momentum_threshold: 1.5 },
      defaultParams: { trend_threshold: 1.2, momentum_threshold: 1.5 },
      performance: { accuracy: 100, avgScore: 72, signalCount: 220, winRate: 74.2, riskLevel: 'MEDIUM' },
      tags: ['趋势追踪', '资金流向', '动量分析'],
      level: 'ADVANCED'
    },
    {
      id: 'low_volume_low_price',
      name: '底部机会发现器',
      shortName: '底部发现',
      description: '识别低量低价区域的潜在反转机会',
      category: 'volume_price',
      categoryName: '量价关系',
      categoryIcon: BarChart3,
      categoryColor: 'green',
      enabled: true,
      weight: 0.8,
      parameters: { price_ma_threshold: 1.0, volume_ratio_threshold: 0.8 },
      defaultParams: { price_ma_threshold: 1.0, volume_ratio_threshold: 0.8 },
      performance: { accuracy: 86.7, avgScore: 65, signalCount: 160, winRate: 68.5, riskLevel: 'HIGH' },
      tags: ['底部识别', '反转机会', '价值发现'],
      level: 'ADVANCED'
    },

    // 趋势跟随策略
    {
      id: 'ma_golden_cross',
      name: '黄金交叉捕获器',
      shortName: '黄金交叉',
      description: '精准识别均线金叉信号，捕捉趋势启动时机',
      category: 'trend_following',
      categoryName: '趋势跟随',
      categoryIcon: TrendingUp,
      categoryColor: 'purple',
      enabled: true,
      weight: 1.4,
      parameters: { cross_threshold: 1.005, pullback_threshold: 1.02 },
      defaultParams: { cross_threshold: 1.005, pullback_threshold: 1.02 },
      performance: { accuracy: 100, avgScore: 88, signalCount: 180, winRate: 82.5, riskLevel: 'LOW' },
      tags: ['金叉信号', '趋势启动', '均线系统'],
      level: 'BASIC'
    },
    {
      id: 'trend_momentum',
      name: '动能趋势分析器',
      shortName: '动能分析',
      description: '综合RSI、KDJ、MACD等指标，全面分析趋势动能',
      category: 'trend_following',
      categoryName: '趋势跟随',
      categoryIcon: TrendingUp,
      categoryColor: 'purple',
      enabled: true,
      weight: 1.3,
      parameters: { rsi_threshold: 30, kdj_threshold: 20, macd_threshold: 0 },
      defaultParams: { rsi_threshold: 30, kdj_threshold: 20, macd_threshold: 0 },
      performance: { accuracy: 100, avgScore: 100, signalCount: 200, winRate: 85.8, riskLevel: 'LOW' },
      tags: ['技术指标', '动能分析', '多指标融合'],
      level: 'ADVANCED'
    },
    {
      id: 'trend_reversal',
      name: '趋势反转识别器',
      shortName: '反转识别',
      description: '精准识别趋势反转时机，把握拐点机会',
      category: 'trend_following',
      categoryName: '趋势跟随',
      categoryIcon: TrendingUp,
      categoryColor: 'purple',
      enabled: true,
      weight: 1.2,
      parameters: { reversal_threshold: 0.9, top_threshold: 1.1 },
      defaultParams: { reversal_threshold: 0.9, top_threshold: 1.1 },
      performance: { accuracy: 100, avgScore: 75, signalCount: 140, winRate: 78.2, riskLevel: 'MEDIUM' },
      tags: ['反转信号', '拐点识别', '时机把握'],
      level: 'ADVANCED'
    },

    // 技术形态策略
    {
      id: 'support_resistance',
      name: '支撑阻力分析器',
      shortName: '支撑阻力',
      description: '基于关键支撑阻力位生成精准买卖信号',
      category: 'pattern_recognition',
      categoryName: '技术形态',
      categoryIcon: Activity,
      categoryColor: 'orange',
      enabled: true,
      weight: 1.3,
      parameters: { support_tolerance: 0.02, resistance_multiplier: 1.05 },
      defaultParams: { support_tolerance: 0.02, resistance_multiplier: 1.05 },
      performance: { accuracy: 66.7, avgScore: 45, signalCount: 100, winRate: 65.5, riskLevel: 'MEDIUM' },
      tags: ['支撑阻力', '关键位', '买卖信号'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'breakout_strategy',
      name: '突破形态猎手',
      shortName: '突破猎手',
      description: '识别各种突破形态，捕捉爆发性上涨机会',
      category: 'pattern_recognition',
      categoryName: '技术形态',
      categoryIcon: Activity,
      categoryColor: 'orange',
      enabled: true,
      weight: 1.4,
      parameters: { consolidation_threshold: 0.03, breakout_volume: 1.8 },
      defaultParams: { consolidation_threshold: 0.03, breakout_volume: 1.8 },
      performance: { accuracy: 80, avgScore: 60, signalCount: 120, winRate: 72.1, riskLevel: 'MEDIUM' },
      tags: ['突破形态', '爆发机会', '形态识别'],
      level: 'INTERMEDIATE'
    },
    {
      id: 'volume_pattern',
      name: '量价形态大师',
      shortName: '形态大师',
      description: '深度解析量价配合形态，洞察市场情绪变化',
      category: 'pattern_recognition',
      categoryName: '技术形态',
      categoryIcon: Activity,
      categoryColor: 'orange',
      enabled: true,
      weight: 1.2,
      parameters: { accumulation_threshold: 1.2, stagnation_threshold: 2.0 },
      defaultParams: { accumulation_threshold: 1.2, stagnation_threshold: 2.0 },
      performance: { accuracy: 86.7, avgScore: 60, signalCount: 150, winRate: 70.8, riskLevel: 'MEDIUM' },
      tags: ['量价形态', '市场情绪', '深度分析'],
      level: 'ADVANCED'
    },

    // 综合判断策略
    {
      id: 'comprehensive_analysis',
      name: 'AI智能决策大脑',
      shortName: '智能大脑',
      description: '融合多维度信号的人工智能决策系统，提供最优投资建议',
      category: 'comprehensive',
      categoryName: '综合判断',
      categoryIcon: Brain,
      categoryColor: 'red',
      enabled: true,
      weight: 2.0,
      parameters: { confidence_threshold: 0.7, signal_threshold: 80 },
      defaultParams: { confidence_threshold: 0.7, signal_threshold: 80 },
      performance: { accuracy: 95, avgScore: 85, signalCount: 500, winRate: 88.9, riskLevel: 'LOW' },
      tags: ['AI决策', '多维融合', '智能分析'],
      level: 'ADVANCED'
    }
  ];

  // 快速模板
  const quickTemplates: QuickTemplate[] = [
    {
      id: 'conservative',
      name: '稳健防守型',
      description: '注重风险控制，适合保守投资者',
      icon: Shield,
      color: 'blue',
      strategies: ['low_price_filter', 'ma_deviation_filter', 'turnover_filter', 'ma_golden_cross', 'comprehensive_analysis']
    },
    {
      id: 'aggressive',
      name: '激进进攻型',
      description: '追求高收益，适合激进投资者',
      icon: TrendingUp,
      color: 'red',
      strategies: ['volume_ratio_strategy', 'trend_momentum', 'breakout_strategy', 'comprehensive_analysis']
    },
    {
      id: 'technical',
      name: '技术分析型',
      description: '基于技术指标，适合技术派',
      icon: Activity,
      color: 'purple',
      strategies: ['ma_golden_cross', 'trend_momentum', 'support_resistance', 'breakout_strategy', 'volume_pattern']
    },
    {
      id: 'value',
      name: '价值发现型',
      description: '挖掘价值机会，适合价值投资',
      icon: Target,
      color: 'green',
      strategies: ['low_price_filter', 'low_volume_low_price', 'volume_trend_analysis', 'trend_reversal']
    }
  ];

  // 过滤和排序策略
  const filteredStrategies = strategyCards
    .filter(strategy => {
      const matchesCategory = filterCategory === 'all' || strategy.category === filterCategory;
      const matchesLevel = filterLevel === 'all' || strategy.level === filterLevel;
      const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           strategy.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           strategy.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
      return matchesCategory && matchesLevel && matchesSearch;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'performance':
          return b.performance.accuracy - a.performance.accuracy;
        case 'signals':
          return b.performance.signalCount - a.performance.signalCount;
        default:
          return 0;
      }
    });

  const toggleStrategy = (strategyId: string) => {
    const newSelected = new Set(selectedStrategies);
    if (newSelected.has(strategyId)) {
      newSelected.delete(strategyId);
    } else {
      newSelected.add(strategyId);
    }
    setSelectedStrategies(newSelected);
  };

  const applyTemplate = (template: QuickTemplate) => {
    setSelectedStrategies(new Set(template.strategies));
  };

  const getCurrentStrategy = (strategyId: string) => {
    return strategyCards.find(s => s.id === strategyId) || null;
  };

  const handleSaveParameters = (strategyId: string, parameters: Record<string, any>) => {
    console.log('保存策略参数:', strategyId, parameters);
  };

  const getPerformanceColor = (accuracy: number) => {
    if (accuracy >= 90) return 'text-green-600';
    if (accuracy >= 80) return 'text-blue-600';
    if (accuracy >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk: string) => {
    const colors = {
      LOW: 'text-green-600 bg-green-50',
      MEDIUM: 'text-yellow-600 bg-yellow-50',
      HIGH: 'text-red-600 bg-red-50'
    };
    return colors[risk as keyof typeof colors] || colors.MEDIUM;
  };

  const getLevelColor = (level: string) => {
    const colors = {
      BASIC: 'text-green-600 bg-green-50',
      INTERMEDIATE: 'text-blue-600 bg-blue-50',
      ADVANCED: 'text-purple-600 bg-purple-50'
    };
    return colors[level as keyof typeof colors] || colors.BASIC;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面头部 */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">🧠 高级策略配置中心</h1>
              <p className="text-lg text-gray-600">精选16个AI策略，智能组合，精准选股</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm text-gray-500">已选择策略</div>
                <div className="text-2xl font-bold text-blue-600">{selectedStrategies.size}/16</div>
              </div>
              <button className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg">
                🚀 开始筛选
              </button>
            </div>
          </div>

          {/* 快速模板 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {quickTemplates.map((template) => {
              const Icon = template.icon;
              return (
                <button
                  key={template.id}
                  onClick={() => applyTemplate(template)}
                  className={`p-4 rounded-lg border-2 border-dashed transition-all group ${
                    template.color === 'blue' ? 'border-blue-300 hover:border-blue-500 hover:bg-blue-50' :
                    template.color === 'green' ? 'border-green-300 hover:border-green-500 hover:bg-green-50' :
                    template.color === 'purple' ? 'border-purple-300 hover:border-purple-500 hover:bg-purple-50' :
                    'border-red-300 hover:border-red-500 hover:bg-red-50'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Icon className={`w-5 h-5 ${
                      template.color === 'blue' ? 'text-blue-600' :
                      template.color === 'green' ? 'text-green-600' :
                      template.color === 'purple' ? 'text-purple-600' :
                      'text-red-600'
                    }`} />
                    <span className="font-medium text-gray-900">{template.name}</span>
                  </div>
                  <p className="text-sm text-gray-600 text-left">{template.description}</p>
                  <div className="text-xs text-gray-500 mt-2">
                    包含 {template.strategies.length} 个策略
                  </div>
                </button>
              );
            })}
          </div>

          {/* 筛选和排序控件 */}
          <div className="flex flex-wrap items-center gap-4 mb-6 p-4 bg-white rounded-lg shadow-sm">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">搜索:</label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索策略名称或标签..."
                className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">分类:</label>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">全部分类</option>
                <option value="basic_filter">基础过滤</option>
                <option value="volume_price">量价关系</option>
                <option value="trend_following">趋势跟随</option>
                <option value="pattern_recognition">技术形态</option>
                <option value="comprehensive">综合判断</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">难度:</label>
              <select
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">全部难度</option>
                <option value="BASIC">基础</option>
                <option value="INTERMEDIATE">中级</option>
                <option value="ADVANCED">高级</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">排序:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="performance">按准确率</option>
                <option value="signals">按信号数</option>
                <option value="name">按名称</option>
              </select>
            </div>

            <div className="ml-auto text-sm text-gray-500">
              显示 {filteredStrategies.length} / {strategyCards.length} 个策略
            </div>
          </div>
        </div>

        {/* 策略卡片网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredStrategies.map((strategy) => {
            const isSelected = selectedStrategies.has(strategy.id);
            const Icon = strategy.categoryIcon;
            
            return (
              <div
                key={strategy.id}
                className={`relative bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:-translate-y-1 ${
                  isSelected ? 'ring-2 ring-blue-500 shadow-blue-200' : ''
                }`}
              >
                {/* 选择状态指示器 */}
                <button
                  onClick={() => toggleStrategy(strategy.id)}
                  className="absolute top-4 right-4 z-10"
                >
                  {isSelected ? (
                    <CheckCircle className="w-6 h-6 text-blue-600" />
                  ) : (
                    <Circle className="w-6 h-6 text-gray-400 hover:text-blue-600" />
                  )}
                </button>

                {/* 卡片头部 */}
                <div className={`p-4 text-white rounded-t-xl ${
                  strategy.categoryColor === 'blue' ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
                  strategy.categoryColor === 'green' ? 'bg-gradient-to-r from-green-500 to-green-600' :
                  strategy.categoryColor === 'purple' ? 'bg-gradient-to-r from-purple-500 to-purple-600' :
                  strategy.categoryColor === 'orange' ? 'bg-gradient-to-r from-orange-500 to-orange-600' :
                  'bg-gradient-to-r from-red-500 to-red-600'
                }`}>
                  <div className="flex items-center gap-3 mb-2">
                    <Icon className="w-6 h-6" />
                    <div>
                      <h3 className="font-bold text-lg">{strategy.shortName}</h3>
                      <p className="text-xs opacity-90">{strategy.categoryName}</p>
                    </div>
                  </div>
                  
                  {/* 标签和等级 */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(strategy.level)}`}>
                      {strategy.level === 'BASIC' ? '基础' : strategy.level === 'INTERMEDIATE' ? '中级' : '高级'}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(strategy.performance.riskLevel)}`}>
                      {strategy.performance.riskLevel === 'LOW' ? '低风险' : 
                       strategy.performance.riskLevel === 'MEDIUM' ? '中风险' : '高风险'}
                    </span>
                  </div>
                </div>

                {/* 卡片内容 */}
                <div className="p-4">
                  <h4 className="font-bold text-gray-900 mb-2">{strategy.name}</h4>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-3">{strategy.description}</p>

                  {/* 性能指标 */}
                  <div className="space-y-3 mb-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">准确率</span>
                      <span className={`font-bold ${getPerformanceColor(strategy.performance.accuracy)}`}>
                        {strategy.performance.accuracy}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">胜率</span>
                      <span className="font-bold text-green-600">{strategy.performance.winRate}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">信号数</span>
                      <span className="font-bold text-blue-600">{strategy.performance.signalCount}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">评分</span>
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 text-yellow-500 fill-current" />
                        <span className="font-bold text-yellow-600">{strategy.performance.avgScore}</span>
                      </div>
                    </div>
                  </div>

                  {/* 标签 */}
                  <div className="flex flex-wrap gap-1 mb-4">
                    {strategy.tags.slice(0, 3).map((tag) => (
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
                      onClick={() => setShowParameterModal(strategy.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                    >
                      <Settings className="w-4 h-4" />
                      <span className="text-sm">配置</span>
                    </button>
                    <button className="flex items-center justify-center px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg transition-colors">
                      <Info className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 策略参数配置模态框 */}
        <StrategyParameterModal
          strategy={getCurrentStrategy(showParameterModal || '')}
          isOpen={!!showParameterModal}
          onClose={() => setShowParameterModal(null)}
          onSave={handleSaveParameters}
        />
      </div>
    </div>
  );
};

export default AdvancedStrategyCards;