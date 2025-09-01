import axios from 'axios';
import { StockPool, ApiResponse } from '../types';

const API_BASE_URL = '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// 股票池API
export const stockPoolAPI = {
  // 获取所有股票池
  getAll: async (): Promise<StockPool[]> => {
    const response = await api.get<ApiResponse<StockPool[]>>('/stock-pools');
    return response.data.data || [];
  },

  // 根据ID获取股票池
  getById: async (id: number): Promise<StockPool | null> => {
    const response = await api.get<ApiResponse<StockPool>>(`/stock-pools/${id}`);
    return response.data.data || null;
  },

  // 创建股票池
  create: async (stockPool: Omit<StockPool, 'id' | 'created_at' | 'updated_at'>): Promise<StockPool> => {
    const response = await api.post<ApiResponse<StockPool>>('/stock-pools', stockPool);
    return response.data.data!;
  },

  // 更新股票池
  update: async (id: number, stockPool: Partial<StockPool>): Promise<StockPool> => {
    const response = await api.put<ApiResponse<StockPool>>(`/stock-pools/${id}`, stockPool);
    return response.data.data!;
  },

  // 删除股票池
  delete: async (id: number): Promise<void> => {
    await api.delete(`/stock-pools/${id}`);
  },

  // 根据类型筛选
  getByType: async (poolType: 'holding' | 'potential'): Promise<StockPool[]> => {
    const response = await api.get<ApiResponse<StockPool[]>>(`/stock-pools/type/${poolType}`);
    return response.data.data || [];
  },
};