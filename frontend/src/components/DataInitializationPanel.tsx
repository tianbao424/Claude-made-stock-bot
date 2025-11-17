import React, { useState, useEffect, useRef } from 'react';
import { RefreshCw, CheckCircle, XCircle, Clock, AlertTriangle, Database, BarChart3, TrendingUp, Cpu } from 'lucide-react';

interface CollectionProgress {
  stage: string;
  status: string;
  current_task: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  progress_percent: number;
  start_time: string;
  estimated_remaining?: number;
  error_message?: string;
}

interface CollectionResult {
  success: boolean;
  total_stocks: number;
  collected_basic_info: number;
  collected_market_data: number;
  collected_financial_data: number;
  calculated_indicators: number;
  errors: string[];
  execution_time: number;
}

const DataInitializationPanel: React.FC = () => {
  const [isCollecting, setIsCollecting] = useState(false);
  const [progress, setProgress] = useState<CollectionProgress | null>(null);
  const [result, setResult] = useState<CollectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // 阶段显示名称映射
  const stageNames: { [key: string]: string } = {
    idle: '等待开始',
    preparing: '准备数据采集',
    stock_list: '采集股票基础信息',
    market_data: '采集实时行情数据',
    financial_data: '采集财务数据',
    technical_indicators: '计算技术指标',
    completed: '采集完成',
    error: '采集失败'
  };

  // 状态显示名称映射
  const statusNames: { [key: string]: string } = {
    waiting: '等待中',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败'
  };

  // 阶段图标映射
  const stageIcons: { [key: string]: React.ElementType } = {
    idle: Clock,
    preparing: RefreshCw,
    stock_list: Database,
    market_data: BarChart3,
    financial_data: TrendingUp,
    technical_indicators: Cpu,
    completed: CheckCircle,
    error: XCircle
  };

  // 建立WebSocket连接
  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8001/ws/data-progress');
    
    ws.onopen = () => {
      console.log('WebSocket连接已建立');
      wsRef.current = ws;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'progress_update') {
          setProgress(data.data);
        } else if (data.type === 'collection_complete') {
          setResult(data.data);
          setIsCollecting(false);
          showNotification('success', '数据采集完成', `成功采集了 ${data.data.total_stocks} 只股票的数据`);
        } else if (data.type === 'collection_error') {
          setError(data.data.error);
          setIsCollecting(false);
          showNotification('error', '数据采集失败', data.data.error);
        }
      } catch (err) {
        console.error('解析WebSocket消息失败:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      wsRef.current = null;
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };
  };

  // 断开WebSocket连接
  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  // 简单的通知函数
  const showNotification = (type: 'success' | 'error' | 'info', title: string, message: string) => {
    // 这里可以集成更复杂的通知系统，现在先用console
    console.log(`${type.toUpperCase()}: ${title} - ${message}`);
    
    // 显示简单的浮动消息
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg transition-all transform ${
      type === 'success' ? 'bg-green-100 border border-green-300 text-green-800' :
      type === 'error' ? 'bg-red-100 border border-red-300 text-red-800' :
      'bg-blue-100 border border-blue-300 text-blue-800'
    }`;
    notification.innerHTML = `
      <div class="font-medium">${title}</div>
      <div class="text-sm mt-1">${message}</div>
    `;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 3000);
  };

  // 启动数据初始化
  const startDataInitialization = async (forceRefresh: boolean = false) => {
    try {
      setIsCollecting(true);
      setProgress(null);
      setResult(null);
      setError(null);

      // 建立WebSocket连接
      connectWebSocket();

      // 发送初始化请求
      const response = await fetch('/api/data/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          force_refresh: forceRefresh
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || '启动数据采集失败');
      }

      showNotification('info', '数据采集已启动', '正在进行数据采集，请查看进度面板');

    } catch (err) {
      console.error('启动数据初始化失败:', err);
      setError(err instanceof Error ? err.message : '启动失败');
      setIsCollecting(false);
      disconnectWebSocket();
      
      showNotification('error', '启动失败', err instanceof Error ? err.message : '启动数据采集失败');
    }
  };

  // 获取采集状态
  const fetchCollectionStatus = async () => {
    try {
      const response = await fetch('/api/data/status');
      const data = await response.json();
      
      if (data.success) {
        setProgress(data.data);
        
        // 如果状态显示正在运行但本地状态不是，更新本地状态
        if (data.data.status === 'running' && !isCollecting) {
          setIsCollecting(true);
          connectWebSocket();
        }
      }
    } catch (err) {
      console.error('获取采集状态失败:', err);
    }
  };

  // 组件挂载时获取初始状态
  useEffect(() => {
    fetchCollectionStatus();
    
    // 组件卸载时断开WebSocket连接
    return () => {
      disconnectWebSocket();
    };
  }, []);

  // 格式化执行时间
  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}时${minutes}分${secs}秒`;
    } else if (minutes > 0) {
      return `${minutes}分${secs}秒`;
    } else {
      return `${secs}秒`;
    }
  };

  // 渲染进度条
  const renderProgress = () => {
    if (!progress) return null;

    const progressPercent = Math.round(progress.progress_percent);
    const StageIcon = stageIcons[progress.stage] || Clock;
    
    const statusColor = 
      progress.status === 'running' ? 'text-blue-600' :
      progress.status === 'completed' ? 'text-green-600' :
      progress.status === 'failed' ? 'text-red-600' :
      'text-gray-600';

    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <StageIcon className={`w-5 h-5 ${statusColor} ${progress.status === 'running' ? 'animate-spin' : ''}`} />
            <span className="font-medium text-gray-900">
              {stageNames[progress.stage] || progress.stage}
            </span>
          </div>
          <span className="text-sm font-medium text-gray-600">{progressPercent}%</span>
        </div>
        
        {/* 进度条 */}
        <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              progress.status === 'running' ? 'bg-blue-500' :
              progress.status === 'completed' ? 'bg-green-500' :
              progress.status === 'failed' ? 'bg-red-500' :
              'bg-gray-400'
            }`}
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>
        
        {/* 任务详情 */}
        <div className="text-sm text-gray-600 space-y-1">
          <div>当前任务: {progress.current_task}</div>
          {progress.total_items > 0 && (
            <div>
              进度: {progress.completed_items} / {progress.total_items}
              {progress.failed_items > 0 && ` (失败: ${progress.failed_items})`}
            </div>
          )}
          {progress.estimated_remaining && (
            <div>预计剩余: {formatDuration(progress.estimated_remaining)}</div>
          )}
        </div>
      </div>
    );
  };

  // 渲染结果统计
  const renderResult = () => {
    if (!result) return null;

    return (
      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <h3 className="font-medium text-green-900">采集完成统计</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">总股票数:</span>
            <span className="font-medium">{result.total_stocks}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">基础信息:</span>
            <span className="font-medium">{result.collected_basic_info}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">行情数据:</span>
            <span className="font-medium">{result.collected_market_data}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">财务数据:</span>
            <span className="font-medium">{result.collected_financial_data}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">技术指标:</span>
            <span className="font-medium">{result.calculated_indicators}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">执行时间:</span>
            <span className="font-medium">{formatDuration(result.execution_time)}</span>
          </div>
        </div>
        
        {result.errors && result.errors.length > 0 && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-800">发现 {result.errors.length} 个错误</span>
            </div>
            {showDetails && (
              <div className="max-h-24 overflow-y-auto text-xs text-yellow-700">
                {result.errors.slice(0, 5).map((error, index) => (
                  <div key={index} className="mb-1">{error}</div>
                ))}
                {result.errors.length > 5 && (
                  <div className="text-yellow-600">...还有 {result.errors.length - 5} 个错误</div>
                )}
              </div>
            )}
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs text-yellow-700 hover:text-yellow-800 underline mt-1"
            >
              {showDetails ? '隐藏详情' : '查看详情'}
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border p-3">
      <div className="flex items-center gap-2 mb-2">
        <Database className="w-4 h-4 text-blue-600" />
        <h2 className="text-base font-semibold text-gray-900">数据初始化</h2>
      </div>
      
      <p className="text-xs text-gray-600 mb-3">
        一键采集股票基础信息、实时行情、财务数据和技术指标，确保系统数据完整性。
      </p>

      {/* 操作按钮 */}
      <div className="flex flex-wrap gap-2 mb-3">
        <button
          onClick={() => startDataInitialization(false)}
          disabled={isCollecting}
          className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${isCollecting ? 'animate-spin' : ''}`} />
          {isCollecting ? '采集中...' : '开始数据采集'}
        </button>
        
        <button
          onClick={() => startDataInitialization(true)}
          disabled={isCollecting}
          className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          强制刷新全部数据
        </button>
        
        <button
          onClick={fetchCollectionStatus}
          disabled={isCollecting}
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Clock className="w-3 h-3" />
          查看状态
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <XCircle className="w-4 h-4 text-red-600" />
            <span className="font-medium text-red-800">采集失败</span>
          </div>
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-xs text-red-600 hover:text-red-800 underline mt-1"
          >
            关闭
          </button>
        </div>
      )}

      {/* 进度显示 */}
      {progress && renderProgress()}

      {/* 结果统计 */}
      {result && renderResult()}
      
      {/* 采集中提示 */}
      {isCollecting && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-blue-800">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span className="text-sm">数据采集进行中，请勿关闭浏览器...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataInitializationPanel;