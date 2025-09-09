import React, { useState } from 'react';
import { Brain, Loader, AlertCircle } from 'lucide-react';
import { strategyAPI } from '../services/api';
import { StrategyAnalysisResponse } from '../types';

interface StrategyAnalysisButtonProps {
  stockPoolId: number;
  stockName: string;
  stockCode: string;
  disabled?: boolean;
  onAnalysisComplete?: (analysis: StrategyAnalysisResponse) => void;
  onError?: (error: string) => void;
}

const StrategyAnalysisButton: React.FC<StrategyAnalysisButtonProps> = ({
  stockPoolId,
  stockName,
  stockCode,
  disabled = false,
  onAnalysisComplete,
  onError
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');

  const handleAnalysis = async () => {
    setLoading(true);
    setError(null);
    setProgress('准备中...');

    try {
      // 显示进度
      const progressSteps = [
        '收集技术指标数据...',
        '获取财务数据...',
        '分析市场环境...',
        'AI策略生成中...',
        '保存分析结果...'
      ];

      let stepIndex = 0;
      const progressInterval = setInterval(() => {
        if (stepIndex < progressSteps.length) {
          setProgress(progressSteps[stepIndex]);
          stepIndex++;
        }
      }, 8000); // 每8秒更新一次进度

      const analysis = await strategyAPI.generateAnalysis(stockPoolId);
      
      clearInterval(progressInterval);
      setProgress('完成！');
      
      // 成功回调
      onAnalysisComplete?.(analysis);
      
    } catch (err: any) {
      setProgress('');
      let errorMessage = 'AI策略分析生成失败';
      
      if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        errorMessage = '分析超时，请稍后重试。数据收集和AI分析需要较长时间...';
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      onError?.(errorMessage);
      
      // 5秒后清除错误信息（延长显示时间）
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
      setProgress('');
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleAnalysis}
        disabled={disabled || loading}
        className={`
          flex items-center gap-1 p-1 rounded transition-colors
          ${loading 
            ? 'bg-blue-50 text-blue-600 cursor-not-allowed' 
            : disabled
            ? 'text-gray-400 cursor-not-allowed'
            : 'text-blue-600 hover:text-blue-800 hover:bg-blue-50'
          }
        `}
        title={loading ? '正在生成策略分析...' : `为${stockName}生成AI投资策略`}
      >
        {loading ? (
          <>
            <Loader className="w-4 h-4 animate-spin" />
            <span className="text-xs">分析中</span>
          </>
        ) : (
          <>
            <Brain className="w-4 h-4" />
            <span className="text-xs">AI策略</span>
          </>
        )}
      </button>

      {/* 错误提示 */}
      {error && (
        <div className="absolute top-full left-0 mt-2 p-3 bg-red-50 border-2 border-red-200 rounded-lg shadow-xl z-20 min-w-80 max-w-96">
          <div className="flex items-start gap-2 text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-sm mb-1">分析失败</div>
              <span className="text-sm leading-relaxed">{error}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StrategyAnalysisButton;