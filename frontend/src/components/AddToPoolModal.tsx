import React, { useState } from 'react';
import { X, Plus, Trash2, AlertCircle, CheckCircle } from 'lucide-react';
import { StockInfo } from '../services/api';
import { addStockToPool, AddToPoolRequest } from '../services/api';

interface AddToPoolModalProps {
  isOpen: boolean;
  onClose: () => void;
  stock: StockInfo;
  onSuccess?: (message: string) => void;
}

const AddToPoolModal: React.FC<AddToPoolModalProps> = ({
  isOpen,
  onClose,
  stock,
  onSuccess
}) => {
  const [poolType, setPoolType] = useState<'holding' | 'potential'>('potential');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [notes, setNotes] = useState('');
  const [shares, setShares] = useState<number | ''>('');
  const [avgCost, setAvgCost] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 重置表单
  const resetForm = () => {
    setPoolType('potential');
    setTags([]);
    setNewTag('');
    setNotes('');
    setShares('');
    setAvgCost('');
    setError(null);
    setSuccess(null);
  };

  // 关闭Modal
  const handleClose = () => {
    resetForm();
    onClose();
  };

  // 添加标签
  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  // 删除标签
  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  // 处理键盘事件
  const handleTagKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  // 提交添加
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const request: AddToPoolRequest = {
        pool_type: poolType,
        tags: tags,
        notes: notes.trim(),
        shares: poolType === 'holding' ? Number(shares) || 0 : undefined,
        avg_cost: poolType === 'holding' ? Number(avgCost) || 0 : undefined
      };
      
      // 验证持仓股票必填字段
      if (poolType === 'holding') {
        if (!shares || Number(shares) <= 0) {
          setError('持仓股票必须填写股数');
          return;
        }
        if (!avgCost || Number(avgCost) <= 0) {
          setError('持仓股票必须填写平均成本');
          return;
        }
      }

      const result = await addStockToPool(stock.symbol, request);
      
      if (result.success) {
        setSuccess(result.message);
        onSuccess?.(result.message);
        setTimeout(() => {
          handleClose();
        }, 1500);
      } else {
        setError(result.message);
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || '添加失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full max-h-[85vh] overflow-y-auto flex flex-col">
        {/* Modal头部 */}
        <div className="flex items-center justify-between p-6 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            添加股票到股票池
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal内容 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* 股票信息 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-gray-900">{stock.name}</h4>
                <p className="text-sm text-gray-600 font-mono">{stock.symbol}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                stock.market === 'SH' ? 'bg-red-100 text-red-700' :
                stock.market === 'SZ' ? 'bg-green-100 text-green-700' :
                'bg-blue-100 text-blue-700'
              }`}>
                {stock.market === 'SH' ? '上交所' : 
                 stock.market === 'SZ' ? '深交所' : '港交所'}
              </span>
            </div>
            {stock.industry && (
              <p className="text-sm text-gray-500 mt-1">行业: {stock.industry}</p>
            )}
          </div>

          {/* 成功消息 */}
          {success && (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-sm text-green-700">{success}</span>
            </div>
          )}

          {/* 错误消息 */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          {/* 股票池类型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              股票池类型 *
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="holding"
                  checked={poolType === 'holding'}
                  onChange={(e) => setPoolType(e.target.value as 'holding')}
                  className="text-blue-600 focus:ring-blue-500"
                  disabled={loading}
                />
                <span className="ml-2 text-sm text-gray-700">持仓股票 - 已持有的股票</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="potential"
                  checked={poolType === 'potential'}
                  onChange={(e) => setPoolType(e.target.value as 'potential')}
                  className="text-blue-600 focus:ring-blue-500"
                  disabled={loading}
                />
                <span className="ml-2 text-sm text-gray-700">关注标的 - 潜在投资标的</span>
              </label>
            </div>
          </div>

          {/* 标签管理 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              标签
            </label>
            
            {/* 现有标签 */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                  >
                    {tag}
                    <button
                      onClick={() => removeTag(tag)}
                      className="text-blue-500 hover:text-blue-700"
                      disabled={loading}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            
            {/* 添加新标签 */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="输入标签名称"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={handleTagKeyPress}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                disabled={loading}
              />
              <button
                onClick={addTag}
                disabled={!newTag.trim() || loading}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* 持仓信息 */}
          {poolType === 'holding' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  股数 *
                </label>
                <input
                  type="number"
                  value={shares}
                  onChange={(e) => setShares(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="输入持有股数"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                  min="1"
                  step="1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  平均成本 *
                </label>
                <input
                  type="number"
                  value={avgCost}
                  onChange={(e) => setAvgCost(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="输入平均成本价格"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                  min="0"
                  step="0.01"
                />
              </div>
            </div>
          )}

          {/* 备注 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              备注
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="添加备注信息（可选）"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={loading}
            />
          </div>
        </div>

        {/* Modal底部 */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50 flex-shrink-0">
          <button
            onClick={handleClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || success !== null}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {loading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
            {loading ? '添加中...' : '确认添加'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddToPoolModal;