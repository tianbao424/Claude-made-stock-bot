import React, { useState, useEffect } from 'react';
import { X, Brain, TrendingUp, AlertTriangle, Target, Clock, Star, History } from 'lucide-react';
import { StrategyAnalysisResponse } from '../types';
import { strategyAPI } from '../services/api';

interface StrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: StrategyAnalysisResponse;
  stockPoolId: number;
}

const StrategyModal: React.FC<StrategyModalProps> = ({
  isOpen,
  onClose,
  analysis,
  stockPoolId
}) => {
  const [historyAnalyses, setHistoryAnalyses] = useState<StrategyAnalysisResponse[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // 加载历史分析
  const loadHistory = async () => {
    if (loadingHistory) return;
    
    setLoadingHistory(true);
    try {
      const history = await strategyAPI.getHistory(stockPoolId, 5);
      setHistoryAnalyses(history.filter(h => h.id !== analysis.id));
    } catch (error) {
      console.error('加载历史分析失败:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (isOpen && showHistory && historyAnalyses.length === 0) {
      loadHistory();
    }
  }, [isOpen, showHistory]);

  if (!isOpen) return null;

  const getRiskLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getRiskLevelText = (level: string) => {
    switch (level.toLowerCase()) {
      case 'low': return '低风险';
      case 'medium': return '中等风险';
      case 'high': return '高风险';
      default: return level;
    }
  };

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy': return 'text-green-600 bg-green-100';
      case 'hold': return 'text-blue-600 bg-blue-100';
      case 'reduce': return 'text-orange-600 bg-orange-100';
      case 'sell': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getActionText = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy': return '买入';
      case 'hold': return '持有';
      case 'reduce': return '减仓';
      case 'sell': return '卖出';
      default: return action;
    }
  };

  const getTimeframeText = (timeframe: string) => {
    switch (timeframe.toLowerCase()) {
      case 'short': return '短期';
      case 'medium': return '中期';
      case 'long': return '长期';
      default: return timeframe;
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleString('zh-CN');
    } catch {
      return dateStr;
    }
  };

  const HistoryItem: React.FC<{ history: StrategyAnalysisResponse }> = ({ history }) => (
    <div className="p-2 bg-gray-50 rounded-lg border">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1">
          <span className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded-full ${getRiskLevelColor(history.risk_level)}`}>
            {getRiskLevelText(history.risk_level)}
          </span>
          <span className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded-full ${getActionColor(history.action_recommendation)}`}>
            {getActionText(history.action_recommendation)}
          </span>
        </div>
        <span className="text-xs text-gray-500">{formatDate(history.created_at)}</span>
      </div>
      <p className="text-xs text-gray-700 line-clamp-2" style={{
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      }}>{history.analysis_summary}</p>
      <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
        <span>评分: {history.comprehensive_score.toFixed(1)}/10</span>
        <span>置信度: {(history.confidence_level * 100).toFixed(0)}%</span>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-gray-900 flex items-start justify-center z-50 p-2 sm:p-4 overflow-y-auto">
      <div className="bg-white rounded-lg max-w-6xl w-full my-4 flex flex-col min-h-[600px] shadow-2xl border border-gray-200">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-purple-100 to-blue-100 rounded-lg">
              <Brain className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">AI投资策略分析</h3>
              <p className="text-sm text-gray-600">
                {analysis.stock_name} ({analysis.stock_code}) - 当前价格：¥{analysis.current_price?.toFixed(2) || analysis.price_at_analysis?.toFixed(2) || 'N/A'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <History className="w-4 h-4" />
              {showHistory ? '隐藏历史' : '查看历史'}
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 bg-white">
          <div className={`grid ${showHistory ? 'lg:grid-cols-2 grid-cols-1' : 'grid-cols-1'} gap-4 p-4 bg-white`}>
            {/* 主要内容 */}
            <div className="space-y-4 bg-white">
              {/* 核心指标 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Star className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-gray-800">综合评分</span>
                  </div>
                  <div className="text-xl font-bold text-blue-600">
                    {analysis.comprehensive_score.toFixed(1)}/10
                  </div>
                </div>
                
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Target className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-800">置信度</span>
                  </div>
                  <div className="text-xl font-bold text-gray-600">
                    {(analysis.confidence_level * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* 操作建议 */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="text-center p-2 rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">风险等级</div>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getRiskLevelColor(analysis.risk_level)}`}>
                    {getRiskLevelText(analysis.risk_level)}
                  </span>
                </div>
                
                <div className="text-center p-2 rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">操作建议</div>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getActionColor(analysis.action_recommendation)}`}>
                    {getActionText(analysis.action_recommendation)}
                  </span>
                </div>
                
                <div className="text-center p-2 rounded-lg border">
                  <div className="text-xs text-gray-600 mb-1">投资周期</div>
                  <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
                    {getTimeframeText(analysis.timeframe)}
                  </span>
                </div>
              </div>

              {/* 目标价位 */}
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium text-gray-800">目标价位区间</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-gray-600">下限</div>
                    <div className="text-lg font-bold text-green-600">
                      ¥{analysis.target_price_min.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-gray-400">—</div>
                  <div>
                    <div className="text-xs text-gray-600">上限</div>
                    <div className="text-lg font-bold text-green-600">
                      ¥{analysis.target_price_max.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>

              {/* 分析摘要 */}
              <div>
                <h4 className="text-sm font-medium text-gray-800 mb-2">分析摘要</h4>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-700 leading-relaxed">{analysis.analysis_summary}</p>
                </div>
              </div>

              {/* 关键指标 */}
              {analysis.key_metrics && analysis.key_metrics.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-800 mb-2">关键指标</h4>
                  <div className="space-y-1">
                    {analysis.key_metrics.map((metric, index) => (
                      <div key={index} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mt-1.5 flex-shrink-0"></div>
                        <span className="text-xs text-gray-700">{metric}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 风险提示 */}
              {analysis.risk_warnings && analysis.risk_warnings.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                    <h4 className="text-sm font-medium text-gray-800">风险提示</h4>
                  </div>
                  <div className="space-y-1">
                    {analysis.risk_warnings.map((warning, index) => (
                      <div key={index} className="flex items-start gap-2 p-2 bg-red-50 rounded-lg border-l-3 border-red-300">
                        <span className="text-xs text-red-700">{warning}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 行动计划 */}
              {analysis.action_plan && analysis.action_plan.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-800 mb-2">行动计划</h4>
                  <div className="space-y-1">
                    {analysis.action_plan.map((plan, index) => (
                      <div key={index} className="flex items-start gap-2 p-2 bg-blue-50 rounded-lg">
                        <div className="w-5 h-5 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                          {index + 1}
                        </div>
                        <span className="text-xs text-gray-700">{plan}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 分析时间 */}
              <div className="text-xs text-gray-500 text-center pt-3 border-t">
                <div className="flex items-center justify-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>分析时间：{formatDate(analysis.created_at)}</span>
                </div>
              </div>
            </div>

            {/* 历史分析 */}
            {showHistory && (
              <div className="border-l pl-4 bg-white">
                <h4 className="text-sm font-medium text-gray-800 mb-3">历史分析记录</h4>
                {loadingHistory ? (
                  <div className="flex items-center justify-center py-6">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                  </div>
                ) : historyAnalyses.length > 0 ? (
                  <div className="space-y-2 max-h-[500px] overflow-y-auto">
                    {historyAnalyses.map((history) => (
                      <HistoryItem key={history.id} history={history} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-gray-500">
                    <Brain className="w-6 h-6 mx-auto mb-2 text-gray-400" />
                    <p className="text-xs">暂无历史分析记录</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategyModal;