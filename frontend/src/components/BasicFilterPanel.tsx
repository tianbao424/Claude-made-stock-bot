import React from 'react';
import { Play, RefreshCw, TrendingUp, BarChart3, DollarSign, Factory } from 'lucide-react';

interface BasicFilterCriteria {
  consecutive_days?: number;
  min_rise_percent?: number;
  min_volume?: number;
  min_market_cap?: number;
  market_filter: string[];
  exclude_st: boolean;
  exclude_new_stocks: boolean;
}

interface BasicFilterPanelProps {
  criteria: BasicFilterCriteria;
  onChange: (criteria: BasicFilterCriteria) => void;
  onApply: () => void;
  loading: boolean;
  disabled: boolean;
}

const BasicFilterPanel: React.FC<BasicFilterPanelProps> = ({
  criteria,
  onChange,
  onApply,
  loading,
  disabled
}) => {
  
  const updateCriteria = (updates: Partial<BasicFilterCriteria>) => {
    onChange({ ...criteria, ...updates });
  };

  const handleMarketFilterChange = (market: string, checked: boolean) => {
    const newMarketFilter = checked 
      ? [...criteria.market_filter, market]
      : criteria.market_filter.filter(m => m !== market);
    updateCriteria({ market_filter: newMarketFilter });
  };

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden">
      <div className="p-4 space-y-4">
      {/* 连续上涨天数 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-green-600" />
          连续上涨天数 (可选)
        </label>
        <input
          type="number"
          min="1"
          max="30"
          value={criteria.consecutive_days || ''}
          onChange={(e) => updateCriteria({ consecutive_days: e.target.value ? parseInt(e.target.value) : undefined })}
          placeholder="如：3 (表示连续上涨3天以上)"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          disabled={disabled}
        />
        <span className="text-xs text-gray-500 mt-1 block">设置股票连续上涨的最少天数</span>
      </div>

      {/* 涨幅条件 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-red-600" />
          最小涨幅 (可选)
        </label>
        <div className="relative">
          <input
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={criteria.min_rise_percent || ''}
            onChange={(e) => updateCriteria({ min_rise_percent: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="如：5.0 (表示涨幅超过5%)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={disabled}
          />
          <span className="absolute right-3 top-2 text-gray-500">%</span>
        </div>
        <span className="text-xs text-gray-500 mt-1 block">筛选涨幅超过此百分比的股票</span>
      </div>

      {/* 成交量条件 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-600" />
          最小成交量 (可选)
        </label>
        <div className="relative">
          <input
            type="number"
            min="0"
            value={criteria.min_volume || ''}
            onChange={(e) => updateCriteria({ min_volume: e.target.value ? parseInt(e.target.value) : undefined })}
            placeholder="如：10000 (表示成交量超过1万手)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={disabled}
          />
          <span className="absolute right-3 top-2 text-gray-500">手</span>
        </div>
        <span className="text-xs text-gray-500 mt-1 block">筛选成交量超过此数值的股票</span>
      </div>

      {/* 市值条件 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-yellow-600" />
          最小市值 (可选)
        </label>
        <div className="relative">
          <input
            type="number"
            min="0"
            step="0.1"
            value={criteria.min_market_cap || ''}
            onChange={(e) => updateCriteria({ min_market_cap: e.target.value ? parseFloat(e.target.value) : undefined })}
            placeholder="如：50 (表示市值超过50亿)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={disabled}
          />
          <span className="absolute right-3 top-2 text-gray-500">亿元</span>
        </div>
        <span className="text-xs text-gray-500 mt-1 block">筛选市值超过此数值的股票</span>
      </div>

      {/* 市场选择 */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          <Factory className="w-4 h-4 text-purple-600" />
          市场选择
        </h4>
        
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={criteria.market_filter.includes('SH')}
              onChange={(e) => handleMarketFilterChange('SH', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              disabled={disabled}
            />
            <span className="text-sm text-gray-700">上海证券交易所 (SH)</span>
          </label>
          
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={criteria.market_filter.includes('SZ')}
              onChange={(e) => handleMarketFilterChange('SZ', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              disabled={disabled}
            />
            <span className="text-sm text-gray-700">深圳证券交易所 (SZ)</span>
          </label>
        </div>
      </div>

      {/* 过滤选项 */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">过滤选项</h4>
        
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={criteria.exclude_st}
              onChange={(e) => updateCriteria({ exclude_st: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              disabled={disabled}
            />
            <span className="text-sm text-gray-700">排除ST股票</span>
          </label>
          
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={criteria.exclude_new_stocks}
              onChange={(e) => updateCriteria({ exclude_new_stocks: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              disabled={disabled}
            />
            <span className="text-sm text-gray-700">排除新股 (上市少于60天)</span>
          </label>
        </div>
      </div>

      {/* 快捷预设 */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">快捷预设</h4>
        
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => updateCriteria({
              consecutive_days: 3,
              min_rise_percent: 5.0,
              min_volume: 10000,
              min_market_cap: 50
            })}
            className="px-3 py-2 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
            disabled={disabled}
          >
            强势股
          </button>
          
          <button
            onClick={() => updateCriteria({
              consecutive_days: 2,
              min_rise_percent: 2.0,
              min_volume: 5000,
              min_market_cap: 30
            })}
            className="px-3 py-2 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
            disabled={disabled}
          >
            稳健股
          </button>
          
          <button
            onClick={() => updateCriteria({
              consecutive_days: 1,
              min_rise_percent: 9.5,
              min_volume: 50000,
              min_market_cap: 20
            })}
            className="px-3 py-2 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
            disabled={disabled}
          >
            涨停股
          </button>
          
          <button
            onClick={() => updateCriteria({
              consecutive_days: 5,
              min_rise_percent: 3.0,
              min_volume: 20000,
              min_market_cap: 100
            })}
            className="px-3 py-2 text-sm bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors"
            disabled={disabled}
          >
            大盘趋势股
          </button>
        </div>
      </div>
      
          {/* 执行按钮部分 */}
          <div className="pt-6 border-t mt-6">
            <button
              onClick={onApply}
              disabled={disabled || loading || criteria.market_filter.length === 0}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-base"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  正在执行基础筛选...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  执行基础筛选
                </>
              )}
            </button>
            
            {criteria.market_filter.length === 0 && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">⚠️ 请至少选择一个市场</p>
              </div>
            )}
            
            <div className="mt-3 text-xs text-gray-500 text-center">
              未填写的条件将不会参与筛选
            </div>
          </div>
      </div>
    </div>
  );
};

export default BasicFilterPanel;