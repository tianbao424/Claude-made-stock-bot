import React, { useState } from 'react';
import { Plus, Search, Edit, Trash2 } from 'lucide-react';
import { StockPool } from '../types';
import { useStockPool } from '../hooks/useStockPool';
import StockPoolForm from './StockPoolForm';

const StockPoolManager: React.FC = () => {
  const {
    stockPools,
    loading,
    error,
    createStockPool,
    updateStockPool,
    deleteStockPool,
    getStockPoolsByType,
    searchStockPools,
  } = useStockPool();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<'all' | 'holding' | 'potential'>('all');
  const [showForm, setShowForm] = useState(false);
  const [editingStock, setEditingStock] = useState<StockPool | null>(null);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(5);

  // 筛选股票池
  const filteredStocks = React.useMemo(() => {
    let filtered = searchTerm ? searchStockPools(searchTerm) : stockPools;
    
    if (selectedType !== 'all') {
      filtered = filtered.filter(stock => stock.pool_type === selectedType);
    }
    
    return filtered;
  }, [stockPools, searchTerm, selectedType, searchStockPools]);

  // 分页计算
  const totalPages = Math.ceil(filteredStocks.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedStocks = filteredStocks.slice(startIndex, startIndex + itemsPerPage);

  // 重置页码当筛选条件改变时
  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedType]);

  const handleCreateStock = async (stockData: Omit<StockPool, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      await createStockPool(stockData);
      setShowForm(false);
    } catch (error) {
      console.error('创建股票失败:', error);
    }
  };

  const handleUpdateStock = async (stockData: Omit<StockPool, 'id' | 'created_at' | 'updated_at'>) => {
    if (!editingStock?.id) return;
    
    try {
      await updateStockPool(editingStock.id, stockData);
      setEditingStock(null);
      setShowForm(false);
    } catch (error) {
      console.error('更新股票失败:', error);
    }
  };

  const handleDeleteStock = async (id: number) => {
    if (window.confirm('确定要删除这只股票吗？')) {
      try {
        await deleteStockPool(id);
      } catch (error) {
        console.error('删除股票失败:', error);
      }
    }
  };

  const handleEditStock = (stock: StockPool) => {
    setEditingStock(stock);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingStock(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">股票池管理</h1>
        <p className="text-gray-600">管理您的持仓股票和潜在投资标的</p>
      </div>

      {/* 控制栏 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4 flex-1">
          {/* 搜索框 */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="搜索股票代码、名称或标签..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full"
            />
          </div>

          {/* 类型筛选 */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as 'all' | 'holding' | 'potential')}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">全部</option>
            <option value="holding">持仓股票</option>
            <option value="potential">潜在标的</option>
          </select>
        </div>

        {/* 添加按钮 */}
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          添加股票
        </button>
      </div>

      {/* 统计信息 */}
      <div className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-2xl font-bold text-blue-600">{stockPools.length}</div>
          <div className="text-blue-800">总股票数</div>
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-600">
            {getStockPoolsByType('holding').length}
          </div>
          <div className="text-green-800">持仓股票</div>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {getStockPoolsByType('potential').length}
          </div>
          <div className="text-yellow-800">潜在标的</div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* 股票表格 */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : filteredStocks.length > 0 ? (
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          {/* 分页信息 */}
          <div className="px-6 py-3 bg-gray-50 border-b text-sm text-gray-600 flex items-center justify-between">
            <span>共 {filteredStocks.length} 只股票</span>
            {totalPages > 1 && (
              <span>第 {currentPage} 页，共 {totalPages} 页</span>
            )}
          </div>
          
          {/* 表格 */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    股票信息
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    持仓信息
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    标签
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    备注
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedStocks.map((stock) => (
                  <tr key={stock.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{stock.stock_name}</div>
                          <div className="text-sm text-gray-500 font-mono">{stock.stock_code}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        stock.pool_type === 'holding' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {stock.pool_type === 'holding' ? '持仓' : '关注'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {stock.pool_type === 'holding' ? (
                        <div className="text-sm">
                          <div className="text-gray-900">股数: {stock.shares || 0}</div>
                          <div className="text-gray-500">成本: ¥{(stock.avg_cost || 0).toFixed(2)}</div>
                          <div className="text-gray-500">现价: ¥{(stock.current_price || 0).toFixed(2)}</div>
                          <div className={`font-medium ${(stock.market_value || 0) >= (stock.shares || 0) * (stock.avg_cost || 0) ? 'text-green-600' : 'text-red-600'}`}>
                            市值: ¥{(stock.market_value || 0).toFixed(2)}
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {stock.tags && stock.tags.length > 0 ? (
                          stock.tags.map((tag, index) => (
                            <span
                              key={index}
                              className="inline-flex px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                            >
                              {tag}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400">暂无标签</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 max-w-xs">
                        {stock.notes ? (
                          <div className="truncate" title={stock.notes}>{stock.notes}</div>
                        ) : (
                          <span className="text-gray-400">暂无备注</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEditStock(stock)}
                          className="text-blue-600 hover:text-blue-800 p-1 hover:bg-blue-50 rounded transition-colors"
                          title="编辑"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => stock.id && handleDeleteStock(stock.id)}
                          className="text-red-600 hover:text-red-800 p-1 hover:bg-red-50 rounded transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分页控件 */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                显示第 {startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredStocks.length)} 项，共 {filteredStocks.length} 项
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                >
                  上一页
                </button>
                <span className="text-sm text-gray-600">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg mb-4">
            {searchTerm || selectedType !== 'all' ? '没有找到匹配的股票' : '还没有添加股票'}
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            添加第一只股票
          </button>
        </div>
      )}

      {/* 股票表单弹窗 */}
      {showForm && (
        <StockPoolForm
          stock={editingStock}
          onSubmit={editingStock ? handleUpdateStock : handleCreateStock}
          onCancel={handleCloseForm}
        />
      )}
    </div>
  );
};

export default StockPoolManager;