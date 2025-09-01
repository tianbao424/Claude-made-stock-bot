import { useState, useEffect } from 'react';
import { StockPool } from '../types';
import { stockPoolAPI } from '../services/api';

export const useStockPool = () => {
  const [stockPools, setStockPools] = useState<StockPool[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取所有股票池
  const fetchStockPools = async () => {
    setLoading(true);
    setError(null);
    try {
      const pools = await stockPoolAPI.getAll();
      setStockPools(pools);
    } catch (err) {
      setError('获取股票池失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 创建股票池
  const createStockPool = async (stockPool: Omit<StockPool, 'id' | 'created_at' | 'updated_at'>) => {
    setLoading(true);
    setError(null);
    try {
      const newPool = await stockPoolAPI.create(stockPool);
      setStockPools(prev => [...prev, newPool]);
      return newPool;
    } catch (err) {
      setError('创建股票池失败');
      console.error(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 更新股票池
  const updateStockPool = async (id: number, updates: Partial<StockPool>) => {
    setLoading(true);
    setError(null);
    try {
      const updatedPool = await stockPoolAPI.update(id, updates);
      setStockPools(prev => prev.map(pool => pool.id === id ? updatedPool : pool));
      return updatedPool;
    } catch (err) {
      setError('更新股票池失败');
      console.error(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 删除股票池
  const deleteStockPool = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      await stockPoolAPI.delete(id);
      setStockPools(prev => prev.filter(pool => pool.id !== id));
    } catch (err) {
      setError('删除股票池失败');
      console.error(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 根据类型筛选股票池
  const getStockPoolsByType = (poolType: 'holding' | 'potential') => {
    return stockPools.filter(pool => pool.pool_type === poolType);
  };

  // 搜索股票池
  const searchStockPools = (keyword: string) => {
    if (!keyword.trim()) return stockPools;
    
    return stockPools.filter(pool => 
      pool.stock_name.toLowerCase().includes(keyword.toLowerCase()) ||
      pool.stock_code.toLowerCase().includes(keyword.toLowerCase()) ||
      pool.notes?.toLowerCase().includes(keyword.toLowerCase()) ||
      pool.tags?.some(tag => tag.toLowerCase().includes(keyword.toLowerCase()))
    );
  };

  useEffect(() => {
    fetchStockPools();
  }, []);

  return {
    stockPools,
    loading,
    error,
    createStockPool,
    updateStockPool,
    deleteStockPool,
    getStockPoolsByType,
    searchStockPools,
    refetch: fetchStockPools,
  };
};