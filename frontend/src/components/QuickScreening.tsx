import React, { useState, useEffect } from 'react';
import { 
  Zap, Shield, TrendingUp, Target, Brain,
  Play, ChevronRight
} from 'lucide-react';

interface QuickTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  category: string;
  detail: string;
  strategies: string[];
  strategyNames: string[];  // 添加策略名称列表
  performance: {
    avgReturn: number;
    winRate: number;
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  };
}

const QuickScreening: React.FC = () => {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [isScreening, setIsScreening] = useState(false);
  const [savedParameters, setSavedParameters] = useState<Record<string, Record<string, any>>>({});

  // 从 localStorage 加载保存的参数
  useEffect(() => {
    const saved = localStorage.getItem('strategy_parameters');
    if (saved) {
      setSavedParameters(JSON.parse(saved));
    }
  }, []);

  const quickTemplates: QuickTemplate[] = [
    {
      id: 'steady',
      name: '稳健防守型',
      description: '注重风险控制，适合保守投资者',
      icon: Shield,
      color: 'blue',
      category: '保守型',
      detail: '基础过滤+风控为主，规避高风险',
      strategies: ['low_price_filter', 'ma_deviation_filter', 'turnover_filter', 'dynamic_stop_loss'],
      strategyNames: ['低价股过滤', '均线偏离过滤', '换手率监控', '动态止盈止损'],
      performance: {
        avgReturn: 12.5,
        winRate: 85,
        riskLevel: 'LOW'
      }
    },
    {
      id: 'balanced',
      name: '均衡成长型',
      description: '风险收益平衡，适合大多数投资者',
      icon: Target,
      color: 'green',
      category: '均衡型',
      detail: '趋势跟随+适度风控，稳中求胜',
      strategies: ['ma_golden_cross', 'volume_ratio_strategy', 'trend_momentum', 'position_limit'],
      strategyNames: ['均线金叉', '量比分析策略', '趋势动能', '持股数控制'],
      performance: {
        avgReturn: 18.3,
        winRate: 75,
        riskLevel: 'MEDIUM'
      }
    },
    {
      id: 'aggressive',
      name: '激进进攻型',
      description: '追求高收益，能承受较大波动',
      icon: TrendingUp,
      color: 'red',
      category: '激进型',
      detail: '突破追涨+快进快出，高风险高收益',
      strategies: ['breakout_strategy', 'power_surge_detector', 'volume_expand_confirm'],
      strategyNames: ['突破策略', '强势爆发检测', '放量确认'],
      performance: {
        avgReturn: 26.8,
        winRate: 65,
        riskLevel: 'HIGH'
      }
    },
    {
      id: 'ai_smart',
      name: 'AI智能优选',
      description: '人工智能动态调整，自适应市场',
      icon: Brain,
      color: 'purple',
      category: 'AI型',
      detail: '智能组合+动态权重，全天候适应',
      strategies: ['comprehensive_analysis', 'trend_reversal', 'volume_pattern'],
      strategyNames: ['综合分析策略', '趋势反转', '量价配合形态'],
      performance: {
        avgReturn: 22.5,
        winRate: 82,
        riskLevel: 'MEDIUM'
      }
    }
  ];

  const getRiskColor = (risk: string) => {
    const colors = {
      LOW: 'text-green-600 bg-green-50',
      MEDIUM: 'text-yellow-600 bg-yellow-50',
      HIGH: 'text-red-600 bg-red-50'
    };
    return colors[risk as keyof typeof colors] || colors.MEDIUM;
  };

  const getRiskText = (risk: string) => {
    const texts = {
      LOW: '低风险',
      MEDIUM: '中风险',
      HIGH: '高风险'
    };
    return texts[risk as keyof typeof texts] || '中风险';
  };

  const handleQuickScreen = async (template: QuickTemplate) => {
    setSelectedTemplate(template.id);
    setIsScreening(true);
    
    try {
      // 构建策略配置，使用保存的参数
      const strategyConfigs = template.strategies.map(strategyId => ({
        strategy_id: strategyId,
        enabled: true,
        parameters: savedParameters[strategyId] || {},
        weight: 1.0
      }));

      console.log('执行快速筛选:', {
        template: template.name,
        strategies: strategyConfigs
      });

      // TODO: 调用实际的筛选API
      // const response = await fetch('/api/advanced-screening', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     strategies: strategyConfigs,
      //     market_filter: ['SH', 'SZ'],
      //     limit: 50
      //   })
      // });

      // 模拟延迟
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      alert(`${template.name} 筛选完成！`);
    } catch (error) {
      console.error('筛选失败:', error);
      alert('筛选失败，请稍后重试');
    } finally {
      setIsScreening(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-gray-50 to-blue-50 overflow-hidden">
      <div className="flex-1 flex flex-col p-6 max-w-5xl mx-auto w-full overflow-hidden">
        {/* 页面头部 */}
        <div className="text-center mb-6 flex-shrink-0">
          <div className="inline-flex items-center gap-3 mb-4">
            <Zap className="w-10 h-10 text-yellow-500" />
            <h1 className="text-4xl font-bold text-gray-900">快速筛选</h1>
          </div>
          <p className="text-xl text-gray-600">一键应用专业策略组合，快速发现投资机会</p>
        </div>

        {/* 模板卡片网格 - 可滚动区域 */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6">
          {quickTemplates.map((template) => {
            const Icon = template.icon;
            const isSelected = selectedTemplate === template.id;
            
            return (
              <div
                key={template.id}
                className={`relative bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1 overflow-hidden ${
                  isSelected ? 'ring-4 ring-blue-500 ring-opacity-50' : ''
                }`}
              >
                {/* 卡片头部彩条 */}
                <div className={`h-2 bg-gradient-to-r ${
                  template.color === 'blue' ? 'from-blue-400 to-blue-600' :
                  template.color === 'green' ? 'from-green-400 to-green-600' :
                  template.color === 'red' ? 'from-red-400 to-red-600' :
                  'from-purple-400 to-purple-600'
                }`} />

                <div className="p-6">
                  {/* 图标和标题 */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-xl ${
                        template.color === 'blue' ? 'bg-blue-100' :
                        template.color === 'green' ? 'bg-green-100' :
                        template.color === 'red' ? 'bg-red-100' :
                        'bg-purple-100'
                      }`}>
                        <Icon className={`w-8 h-8 ${
                          template.color === 'blue' ? 'text-blue-600' :
                          template.color === 'green' ? 'text-green-600' :
                          template.color === 'red' ? 'text-red-600' :
                          'text-purple-600'
                        }`} />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900">{template.name}</h3>
                        <p className="text-sm text-gray-500">{template.category}</p>
                      </div>
                    </div>
                  </div>

                  {/* 描述 */}
                  <p className="text-gray-600 mb-2">{template.description}</p>
                  <p className="text-sm text-gray-500 mb-4">{template.detail}</p>

                  {/* 包含的策略列表 */}
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 font-medium mb-2">包含策略：</p>
                    <div className="flex flex-wrap gap-1">
                      {template.strategyNames.map((strategyName, index) => (
                        <span
                          key={index}
                          className={`text-xs px-2 py-1 rounded-full ${
                            template.color === 'blue' ? 'bg-blue-100 text-blue-700' :
                            template.color === 'green' ? 'bg-green-100 text-green-700' :
                            template.color === 'red' ? 'bg-red-100 text-red-700' :
                            'bg-purple-100 text-purple-700'
                          }`}
                        >
                          {strategyName}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* 性能指标 */}
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900">{template.performance.avgReturn}%</div>
                      <div className="text-xs text-gray-500">平均收益</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{template.performance.winRate}%</div>
                      <div className="text-xs text-gray-500">胜率</div>
                    </div>
                    <div className="text-center">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getRiskColor(template.performance.riskLevel)}`}>
                        {getRiskText(template.performance.riskLevel)}
                      </span>
                    </div>
                  </div>

                  {/* 应用按钮 */}
                  <button
                    onClick={() => handleQuickScreen(template)}
                    disabled={isScreening && selectedTemplate === template.id}
                    className={`w-full py-3 px-4 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
                      isScreening && selectedTemplate === template.id
                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                        : template.color === 'blue' ? 'bg-blue-600 hover:bg-blue-700 text-white' :
                          template.color === 'green' ? 'bg-green-600 hover:bg-green-700 text-white' :
                          template.color === 'red' ? 'bg-red-600 hover:bg-red-700 text-white' :
                          'bg-purple-600 hover:bg-purple-700 text-white'
                    }`}
                  >
                    {isScreening && selectedTemplate === template.id ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-gray-500 border-t-transparent" />
                        <span>筛选中...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5" />
                        <span>立即使用</span>
                        <ChevronRight className="w-5 h-5" />
                      </>
                    )}
                  </button>
                </div>

                {/* 选中标记 */}
                {isSelected && (
                  <div className="absolute top-4 right-4">
                    <div className="bg-blue-600 text-white text-xs px-3 py-1 rounded-full">
                      已选择
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          </div>

          {/* 使用说明 */}
          <div className="mt-12 bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">使用说明</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
            <div>
              <div className="font-medium text-gray-900 mb-1">1. 选择模板</div>
              <p>根据您的风险偏好和投资目标选择合适的策略模板</p>
            </div>
            <div>
              <div className="font-medium text-gray-900 mb-1">2. 一键筛选</div>
              <p>点击"立即使用"自动应用预设的策略组合进行筛选</p>
            </div>
            <div>
              <div className="font-medium text-gray-900 mb-1">3. 查看结果</div>
              <p>筛选完成后查看符合条件的股票列表和买卖建议</p>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuickScreening;