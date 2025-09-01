import React, { useState, useEffect } from 'react';
import { X, Plus, Minus, Tag, FileText } from 'lucide-react';
import { StockPool } from '../types';

interface StockPoolFormProps {
  stock?: StockPool | null;
  onSubmit: (stockData: Omit<StockPool, 'id' | 'created_at' | 'updated_at'>) => void;
  onCancel: () => void;
}

const StockPoolForm: React.FC<StockPoolFormProps> = ({ stock, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    stock_code: '',
    stock_name: '',
    pool_type: 'holding' as 'holding' | 'potential',
    tags: [''],
    notes: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (stock) {
      setFormData({
        stock_code: stock.stock_code,
        stock_name: stock.stock_name,
        pool_type: stock.pool_type,
        tags: stock.tags || [''],
        notes: stock.notes || '',
      });
    }
  }, [stock]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // 清除相关错误
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleTagChange = (index: number, value: string) => {
    const newTags = [...formData.tags];
    newTags[index] = value;
    setFormData(prev => ({
      ...prev,
      tags: newTags
    }));
  };

  const addTag = () => {
    setFormData(prev => ({
      ...prev,
      tags: [...prev.tags, '']
    }));
  };

  const removeTag = (index: number) => {
    if (formData.tags.length > 1) {
      const newTags = formData.tags.filter((_, i) => i !== index);
      setFormData(prev => ({
        ...prev,
        tags: newTags
      }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.stock_code.trim()) {
      newErrors.stock_code = '股票代码不能为空';
    } else if (!/^[0-9A-Za-z]{6}$/.test(formData.stock_code.trim())) {
      newErrors.stock_code = '股票代码格式不正确（应为6位数字或字母）';
    }

    if (!formData.stock_name.trim()) {
      newErrors.stock_name = '股票名称不能为空';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    // 过滤空标签
    const filteredTags = formData.tags.filter(tag => tag.trim() !== '');

    onSubmit({
      stock_code: formData.stock_code.trim().toUpperCase(),
      stock_name: formData.stock_name.trim(),
      pool_type: formData.pool_type,
      tags: filteredTags.length > 0 ? filteredTags : undefined,
      notes: formData.notes.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg w-full max-w-md max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            {stock ? '编辑股票' : '添加股票'}
          </h2>
          <button
            onClick={onCancel}
            className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 表单内容 */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* 股票代码 */}
          <div className="mb-4">
            <label htmlFor="stock_code" className="block text-sm font-medium text-gray-700 mb-1">
              股票代码 *
            </label>
            <input
              type="text"
              id="stock_code"
              name="stock_code"
              value={formData.stock_code}
              onChange={handleInputChange}
              placeholder="例：000001"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.stock_code ? 'border-red-500' : 'border-gray-300'
              }`}
              maxLength={6}
            />
            {errors.stock_code && (
              <p className="mt-1 text-sm text-red-600">{errors.stock_code}</p>
            )}
          </div>

          {/* 股票名称 */}
          <div className="mb-4">
            <label htmlFor="stock_name" className="block text-sm font-medium text-gray-700 mb-1">
              股票名称 *
            </label>
            <input
              type="text"
              id="stock_name"
              name="stock_name"
              value={formData.stock_name}
              onChange={handleInputChange}
              placeholder="例：平安银行"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.stock_name ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {errors.stock_name && (
              <p className="mt-1 text-sm text-red-600">{errors.stock_name}</p>
            )}
          </div>

          {/* 股票池类型 */}
          <div className="mb-4">
            <label htmlFor="pool_type" className="block text-sm font-medium text-gray-700 mb-1">
              股票池类型 *
            </label>
            <select
              id="pool_type"
              name="pool_type"
              value={formData.pool_type}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="holding">持仓股票</option>
              <option value="potential">潜在标的</option>
            </select>
          </div>

          {/* 标签 */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                <Tag className="w-4 h-4 inline mr-1" />
                标签
              </label>
              <button
                type="button"
                onClick={addTag}
                className="text-blue-600 hover:text-blue-700 text-sm flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                添加标签
              </button>
            </div>
            {formData.tags.map((tag, index) => (
              <div key={index} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={tag}
                  onChange={(e) => handleTagChange(index, e.target.value)}
                  placeholder="输入标签"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                {formData.tags.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeTag(index)}
                    className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* 备注 */}
          <div className="mb-6">
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
              <FileText className="w-4 h-4 inline mr-1" />
              备注
            </label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              placeholder="输入备注信息..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* 按钮组 */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              {stock ? '更新' : '添加'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default StockPoolForm;