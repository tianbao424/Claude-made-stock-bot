import React, { useState, useEffect } from 'react';
import { Settings, Plus, Edit2, Trash2, Save, X, Filter } from 'lucide-react';

interface ScreeningPreset {
  id: string;
  name: string;
  description: string;
  criteria: {
    screening_type: string;
    min_consecutive_days: number;
    min_rise_percent: number;
    min_volume: number;
    market_filter: string[];
  };
  is_default: boolean;
  created_at: string;
}

const ScreeningConfig: React.FC = () => {
  const [presets, setPresets] = useState<ScreeningPreset[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingPreset, setEditingPreset] = useState<ScreeningPreset | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    min_consecutive_days: 3,
    min_rise_percent: 7.0,
    min_volume: 0,
    market_filter: ['SH', 'SZ']
  });

  // 默认预设
  const defaultPresets: ScreeningPreset[] = [
    {
      id: 'default_strong',
      name: '强势上涨(默认)',
      description: '连续3天涨幅超过7%的股票',
      criteria: {
        screening_type: 'strong_rise_3d',
        min_consecutive_days: 3,
        min_rise_percent: 7.0,
        min_volume: 0,
        market_filter: ['SH', 'SZ']
      },
      is_default: true,
      created_at: new Date().toISOString()
    },
    {
      id: 'conservative',
      name: '稳健增长',
      description: '连续5天涨幅超过5%的股票',
      criteria: {
        screening_type: 'conservative_rise',
        min_consecutive_days: 5,
        min_rise_percent: 5.0,
        min_volume: 0,
        market_filter: ['SH', 'SZ']
      },
      is_default: false,
      created_at: new Date().toISOString()
    },
    {
      id: 'aggressive',
      name: '激进策略',
      description: '连续2天涨幅超过10%的股票',
      criteria: {
        screening_type: 'aggressive_rise',
        min_consecutive_days: 2,
        min_rise_percent: 10.0,
        min_volume: 100000,
        market_filter: ['SH', 'SZ']
      },
      is_default: false,
      created_at: new Date().toISOString()
    }
  ];

  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = () => {
    // 从localStorage加载自定义预设，合并默认预设
    const savedPresets = localStorage.getItem('screening_presets');
    const customPresets = savedPresets ? JSON.parse(savedPresets) : [];
    setPresets([...defaultPresets, ...customPresets]);
  };

  const savePresets = (newPresets: ScreeningPreset[]) => {
    // 只保存非默认预设到localStorage
    const customPresets = newPresets.filter(p => !p.is_default);
    localStorage.setItem('screening_presets', JSON.stringify(customPresets));
    setPresets(newPresets);
  };

  const handleSave = () => {
    const newPreset: ScreeningPreset = {
      id: editingPreset?.id || `custom_${Date.now()}`,
      name: formData.name,
      description: formData.description,
      criteria: {
        screening_type: 'custom',
        min_consecutive_days: formData.min_consecutive_days,
        min_rise_percent: formData.min_rise_percent,
        min_volume: formData.min_volume,
        market_filter: formData.market_filter
      },
      is_default: false,
      created_at: editingPreset?.created_at || new Date().toISOString()
    };

    if (editingPreset) {
      // 编辑现有预设
      const updatedPresets = presets.map(p => p.id === editingPreset.id ? newPreset : p);
      savePresets(updatedPresets);
    } else {
      // 添加新预设
      savePresets([...presets, newPreset]);
    }

    resetForm();
  };

  const handleEdit = (preset: ScreeningPreset) => {
    setEditingPreset(preset);
    setFormData({
      name: preset.name,
      description: preset.description,
      min_consecutive_days: preset.criteria.min_consecutive_days,
      min_rise_percent: preset.criteria.min_rise_percent,
      min_volume: preset.criteria.min_volume,
      market_filter: preset.criteria.market_filter
    });
    setShowForm(true);
  };

  const handleDelete = (preset: ScreeningPreset) => {
    if (preset.is_default) {
      alert('默认预设不能删除');
      return;
    }
    
    if (confirm(`确定要删除预设"${preset.name}"吗？`)) {
      const updatedPresets = presets.filter(p => p.id !== preset.id);
      savePresets(updatedPresets);
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingPreset(null);
    setFormData({
      name: '',
      description: '',
      min_consecutive_days: 3,
      min_rise_percent: 7.0,
      min_volume: 0,
      market_filter: ['SH', 'SZ']
    });
  };

  const applyPreset = (preset: ScreeningPreset) => {
    // 通过事件传递给主界面
    const event = new CustomEvent('applyScreeningPreset', {
      detail: preset.criteria
    });
    window.dispatchEvent(event);
    alert(`已应用预设: ${preset.name}`);
  };

  return (
    <div className="h-screen flex flex-col p-4 lg:p-6 max-w-7xl mx-auto">
      {/* 头部 */}
      <div className="flex-shrink-0 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Settings className="w-7 h-7 text-blue-600" />
              筛选配置
            </h1>
            <p className="text-gray-600 mt-1">管理股票筛选条件预设</p>
          </div>
          
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建预设
          </button>
        </div>
      </div>

      {/* 预设列表 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border overflow-hidden">
        <div className="p-4 border-b bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Filter className="w-5 h-5 text-green-600" />
            筛选预设
          </h2>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {presets.map((preset) => (
              <div
                key={preset.id}
                className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
                  preset.is_default ? 'border-blue-200 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                      {preset.name}
                      {preset.is_default && (
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                          默认
                        </span>
                      )}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">{preset.description}</p>
                  </div>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="text-sm">
                    <span className="text-gray-500">连续天数: </span>
                    <span className="font-medium">{preset.criteria.min_consecutive_days} 天</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">最小涨幅: </span>
                    <span className="font-medium text-red-600">{preset.criteria.min_rise_percent}%</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">市场: </span>
                    <span className="font-medium">{preset.criteria.market_filter.join(', ')}</span>
                  </div>
                  {preset.criteria.min_volume > 0 && (
                    <div className="text-sm">
                      <span className="text-gray-500">最小成交量: </span>
                      <span className="font-medium">{(preset.criteria.min_volume / 10000).toFixed(2)}万</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => applyPreset(preset)}
                    className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    应用
                  </button>
                  {!preset.is_default && (
                    <>
                      <button
                        onClick={() => handleEdit(preset)}
                        className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        title="编辑"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(preset)}
                        className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 新建/编辑表单弹窗 */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingPreset ? '编辑预设' : '新建预设'}
              </h3>
              <button
                onClick={resetForm}
                className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  预设名称
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="输入预设名称"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  预设描述
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={2}
                  placeholder="输入预设描述"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    连续天数
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={formData.min_consecutive_days}
                    onChange={(e) => setFormData({ ...formData, min_consecutive_days: parseInt(e.target.value) || 3 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    最小涨幅 (%)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    step="0.1"
                    value={formData.min_rise_percent}
                    onChange={(e) => setFormData({ ...formData, min_rise_percent: parseFloat(e.target.value) || 7.0 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  市场选择
                </label>
                <select
                  value={formData.market_filter.join(',')}
                  onChange={(e) => setFormData({
                    ...formData,
                    market_filter: e.target.value.split(',').filter(m => m)
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="SH,SZ">A股 (沪深)</option>
                  <option value="SH">上海A股</option>
                  <option value="SZ">深圳A股</option>
                  <option value="HK">港股</option>
                  <option value="SH,SZ,HK">全市场</option>
                </select>
              </div>
            </div>

            <div className="p-4 border-t flex items-center gap-3 justify-end">
              <button
                onClick={resetForm}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScreeningConfig;