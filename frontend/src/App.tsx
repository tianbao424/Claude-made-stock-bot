import React, { useState } from 'react';
import { BarChart3, MessageSquare, Settings, Menu, X, Database, Filter, Clock, Activity, TrendingUp } from 'lucide-react';
import StockPoolManager from './components/StockPoolManager';
import ChatInterface from './components/ChatInterface';
import StockInfoManager from './components/StockInfoManager';
import StockScreeningDashboard from './components/StockScreeningDashboard';
import ScreeningHistory from './components/ScreeningHistory';
import ScreeningConfig from './components/ScreeningConfig';
import PerformanceMonitor from './components/PerformanceMonitor';
import DeepAnalysisDashboard from './components/DeepAnalysisDashboard';
import './App.css';

type TabType = 'chat' | 'pool' | 'stockinfo' | 'screening' | 'history' | 'settings' | 'performance' | 'deep-analysis';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const tabs = [
    {
      id: 'chat' as TabType,
      name: '智能问答',
      icon: MessageSquare,
      component: <ChatInterface />,
    },
    {
      id: 'pool' as TabType,
      name: '股票池',
      icon: BarChart3,
      component: <StockPoolManager />,
    },
    {
      id: 'stockinfo' as TabType,
      name: '股票信息',
      icon: Database,
      component: <StockInfoManager />,
    },
    {
      id: 'screening' as TabType,
      name: '股票甄选',
      icon: Filter,
      component: <StockScreeningDashboard />,
    },
    {
      id: 'deep-analysis' as TabType,
      name: '深度分析',
      icon: TrendingUp,
      component: <DeepAnalysisDashboard />,
    },
    {
      id: 'history' as TabType,
      name: '筛选历史',
      icon: Clock,
      component: <ScreeningHistory />,
    },
    {
      id: 'settings' as TabType,
      name: '筛选配置',
      icon: Settings,
      component: <ScreeningConfig />,
    },
    {
      id: 'performance' as TabType,
      name: '性能监控',
      icon: Activity,
      component: <PerformanceMonitor />,
    },
  ];

  const currentTab = tabs.find(tab => tab.id === activeTab);

  return (
    <div className="h-screen bg-gray-50 flex">
      {/* 移动端遮罩 */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">股票助手</h1>
                <p className="text-sm text-gray-500">v2.0.0</p>
              </div>
            </div>
            
            {/* 移动端关闭按钮 */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 hover:bg-gray-100 rounded"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* 导航菜单 */}
          <nav className="flex-1 p-4">
            <div className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id);
                      setSidebarOpen(false);
                    }}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors
                      ${activeTab === tab.id
                        ? 'bg-blue-50 text-blue-600 border border-blue-200'
                        : 'text-gray-700 hover:bg-gray-100'
                      }
                    `}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.name}</span>
                  </button>
                );
              })}
            </div>
          </nav>

          {/* 底部信息 */}
          <div className="p-4 border-t">
            <div className="text-xs text-gray-500 space-y-1">
              <div>© 2024 AI股票助手</div>
              <div>智能股票分析工具</div>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col lg:ml-0 min-w-0">
        {/* 顶部栏 */}
        <header className="bg-white shadow-sm border-b px-6 py-4 lg:hidden">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>
            
            <h2 className="text-lg font-semibold text-gray-900">
              {currentTab?.name}
            </h2>
            
            <div className="w-9" /> {/* 占位符保持居中 */}
          </div>
        </header>

        {/* 内容区域 */}
        <main className="flex-1 overflow-hidden">
          {currentTab?.component}
        </main>
      </div>
    </div>
  );
};

export default App;