import React, { useState, useEffect } from 'react';
import { AlertTriangle, PlayCircle, RefreshCw, CheckCircle, Clock } from 'lucide-react';

interface FullInitializationProgress {
  stage: string;
  current_task: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  progress_percent: number;
  elapsed_seconds: number;
  estimated_remaining_seconds?: number;
}

interface FullInitializationResult {
  success: boolean;
  total_duration: number;
  stages_completed: string[];
  stages_failed: string[];
  stats: Record<string, number>;
  errors: string[];
}

interface FullInitializationConfig {
  confirm_cleanup: boolean;
  include_strategy_cleanup: boolean;
  include_a_stocks: boolean;
  include_hk_stocks: boolean;
  include_realtime: boolean;
  include_historical: boolean;
  include_financial: boolean;
}

const STAGE_NAMES: Record<string, string> = {
  cleanup: '清理现有数据',
  a_stocks: '获取A股列表',
  hk_stocks: '获取港股列表', 
  realtime: '获取实时数据',
  historical: '获取历史数据',
  financial: '获取财务数据'
};

const FullDataInitializer: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [progress, setProgress] = useState<FullInitializationProgress | null>(null);
  const [result, setResult] = useState<FullInitializationResult | null>(null);

  const [config, setConfig] = useState<FullInitializationConfig>({
    confirm_cleanup: false,
    include_strategy_cleanup: false,
    include_a_stocks: true,
    include_hk_stocks: true,
    include_realtime: true,
    include_historical: true,
    include_financial: true
  });

  // 轮询获取进度
  useEffect(() => {
    let progressTimer: NodeJS.Timeout;
    
    if (isInitializing) {
      progressTimer = setInterval(async () => {
        try {
          const response = await fetch('/api/data-collection/full-initialize/progress');
          const data = await response.json();
          
          if (data.success && data.data) {
            setProgress(data.data);
          }
        } catch (error) {
          console.error('获取进度失败:', error);
        }
      }, 1000);
    }

    return () => {
      if (progressTimer) {
        clearInterval(progressTimer);
      }
    };
  }, [isInitializing]);

  const showConfirmModal = () => {
    setIsModalVisible(true);
    setResult(null);
    setProgress(null);
  };

  const handleConfirm = async () => {
    if (!config.confirm_cleanup) {
      alert('必须确认清理现有数据才能继续');
      return;
    }

    setIsInitializing(true);
    setProgress(null);
    setResult(null);

    try {
      const response = await fetch('/api/data-collection/full-initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      const data = await response.json();
      
      if (data.success) {
        setResult(data.data);
      } else {
        throw new Error(data.message || '初始化失败');
      }
    } catch (error: any) {
      alert(`初始化失败: ${error.message || '请检查网络连接和服务器状态'}`);
    } finally {
      setIsInitializing(false);
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setIsInitializing(false);
    setProgress(null);
    setResult(null);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}分${secs}秒`;
  };

  const renderProgressContent = () => {
    if (result) {
      return (
        <div className="space-y-4">
          <div className={`p-4 rounded-lg border ${result.success ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
            <div className="flex items-center gap-2">
              {result.success ? <CheckCircle className="w-5 h-5 text-green-600" /> : <AlertTriangle className="w-5 h-5 text-yellow-600" />}
              <h3 className="font-medium">
                {result.success ? '全量初始化成功完成！' : '全量初始化部分失败'}
              </h3>
            </div>
            <div className="mt-2 text-sm">
              <p>总耗时: {formatDuration(result.total_duration)}</p>
              <p>完成阶段: {result.stages_completed.map(stage => STAGE_NAMES[stage] || stage).join(', ')}</p>
              {result.stages_failed.length > 0 && (
                <p className="text-red-600">失败阶段: {result.stages_failed.map(stage => STAGE_NAMES[stage] || stage).join(', ')}</p>
              )}
            </div>
          </div>
          
          <div className="bg-white border rounded-lg p-4">
            <h4 className="font-medium mb-2">统计数据</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(result.stats).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="font-medium">{key.replace(/_/g, ' ')}: </span>
                  <span>{value?.toLocaleString() || 0}</span>
                </div>
              ))}
            </div>
          </div>

          {result.errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h4 className="font-medium text-red-800 mb-2">错误信息</h4>
              <div className="space-y-2">
                {result.errors.slice(0, 3).map((error, index) => (
                  <div key={index} className="text-sm text-red-600 bg-red-100 p-2 rounded">
                    {error}
                  </div>
                ))}
                {result.errors.length > 3 && (
                  <div className="text-sm text-red-600">
                    还有 {result.errors.length - 3} 个错误...
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    if (progress) {
      return (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
              <h3 className="font-medium">正在执行: {STAGE_NAMES[progress.stage] || progress.stage}</h3>
            </div>
            <p className="text-sm text-blue-700">{progress.current_task}</p>
          </div>
          
          <div className="bg-white border rounded-lg p-4">
            <div className="flex justify-between text-sm mb-2">
              <span>{progress.completed_items}/{progress.total_items}</span>
              <span>{progress.progress_percent.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress.progress_percent}%` }}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>已耗时: {formatDuration(progress.elapsed_seconds)}</span>
            </div>
            {progress.estimated_remaining_seconds && (
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>预计剩余: {formatDuration(progress.estimated_remaining_seconds)}</span>
              </div>
            )}
          </div>
          
          {progress.failed_items > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                <span className="text-sm">已失败 {progress.failed_items} 项</span>
              </div>
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <>
      <button
        onClick={showConfirmModal}
        disabled={isInitializing}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <PlayCircle className="w-5 h-5" />
        全量数据初始化
      </button>

      {isModalVisible && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <h2 className="text-xl font-semibold">全量数据初始化</h2>
              </div>
            </div>

            <div className="p-6">
              {!isInitializing && !result && (
                <div className="space-y-6">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                      <span className="font-medium text-yellow-800">重要提醒</span>
                    </div>
                    <p className="text-sm text-yellow-700">
                      此操作将清理股票历史数据并重新初始化数据库。这是一个耗时较长的操作，可能需要30-60分钟。
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-medium mb-3">初始化流程</h3>
                    <p className="text-gray-600 mb-3">本次初始化将按以下顺序执行：</p>
                    <ol className="list-decimal list-inside space-y-1 text-sm">
                      <li><strong>清理现有数据</strong> - 清空历史交易数据和股票池数据</li>
                      <li><strong>获取A股列表</strong> - 从数据源获取最新A股列表</li>
                      <li><strong>获取港股列表</strong> - 从数据源获取最新港股列表</li>
                      <li><strong>获取实时数据</strong> - 获取所有股票的当前行情数据</li>
                      <li><strong>获取历史数据</strong> - 获取每只股票的30天历史行情</li>
                      <li><strong>获取财务数据</strong> - 获取股票的基本财务信息</li>
                    </ol>
                  </div>

                  <div className="border-t pt-4">
                    <div className="space-y-4">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={config.confirm_cleanup}
                          onChange={(e) => setConfig({ ...config, confirm_cleanup: e.target.checked })}
                          className="rounded border-gray-300"
                        />
                        <span className="font-medium text-red-600">
                          我确认要清理历史数据并重新初始化
                        </span>
                      </label>
                      
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <label className="flex items-start space-x-2">
                          <input
                            type="checkbox"
                            checked={config.include_strategy_cleanup}
                            onChange={(e) => setConfig({ ...config, include_strategy_cleanup: e.target.checked })}
                            className="rounded border-gray-300 mt-1"
                          />
                          <div>
                            <span className="font-medium text-blue-800">
                              同时清理策略分析数据
                            </span>
                            <p className="text-sm text-blue-600 mt-1">
                              勾选此项会删除所有历史策略分析结果。如果您想保留之前的策略分析工作，请不要勾选此项。
                            </p>
                          </div>
                        </label>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">初始化选项</h4>
                        <div className="grid grid-cols-2 gap-3">
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={config.include_a_stocks}
                              onChange={(e) => setConfig({ ...config, include_a_stocks: e.target.checked })}
                              className="rounded border-gray-300"
                            />
                            <span>获取A股列表</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={config.include_hk_stocks}
                              onChange={(e) => setConfig({ ...config, include_hk_stocks: e.target.checked })}
                              className="rounded border-gray-300"
                            />
                            <span>获取港股列表</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={config.include_realtime}
                              onChange={(e) => setConfig({ ...config, include_realtime: e.target.checked })}
                              className="rounded border-gray-300"
                            />
                            <span>获取实时数据</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={config.include_historical}
                              onChange={(e) => setConfig({ ...config, include_historical: e.target.checked })}
                              className="rounded border-gray-300"
                            />
                            <span>获取30天历史数据</span>
                          </label>
                          <label className="flex items-center space-x-2 col-span-2">
                            <input
                              type="checkbox"
                              checked={config.include_financial}
                              onChange={(e) => setConfig({ ...config, include_financial: e.target.checked })}
                              className="rounded border-gray-300"
                            />
                            <span>获取财务数据</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {(isInitializing || result) && (
                <div>{renderProgressContent()}</div>
              )}
            </div>

            <div className="p-6 border-t bg-gray-50 flex justify-end gap-3">
              {isInitializing || result ? (
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300"
                >
                  {result ? '关闭' : '取消'}
                </button>
              ) : (
                <>
                  <button
                    onClick={handleCancel}
                    className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={!config.confirm_cleanup}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    确认执行
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default FullDataInitializer;