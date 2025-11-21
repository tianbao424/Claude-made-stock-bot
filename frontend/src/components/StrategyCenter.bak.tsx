import React from 'react';

const StrategyCenter: React.FC = () => {
  return (
    <div className="h-full flex flex-col bg-gray-50 overflow-hidden p-6">
      <div className="max-w-7xl mx-auto w-full">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">策略中心</h1>
        <p className="text-lg text-gray-600 mb-6">管理和配置所有策略，打造您的专属投资系统</p>
        
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">策略中心正在加载...</h2>
          <p className="text-gray-600">如果看到此消息，说明组件已正确加载。</p>
          
          <div className="mt-4 p-4 bg-blue-50 rounded">
            <p className="text-sm text-blue-800">调试信息：</p>
            <ul className="mt-2 text-xs text-blue-700">
              <li>• React 版本: {React.version}</li>
              <li>• 组件已挂载: 是</li>
              <li>• localStorage 可用: {typeof Storage !== 'undefined' ? '是' : '否'}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategyCenter;