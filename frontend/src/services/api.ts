import axios from 'axios';
import { StockPool, ApiResponse } from '../types';

export interface StockInfo {
  symbol: string;
  name: string;
  short_name: string;
  market: string;
  industry: string;
  sector?: string;
  market_cap?: number;
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  listing_date?: string;
  is_active?: boolean;
}

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

// 股票搜索API
export const searchStocks = async (query: string, limit: number = 20): Promise<StockInfo[]> => {
  try {
    const response = await api.get<ApiResponse<StockInfo[]>>('/stocks/search', {
      params: { query, limit }
    });
    return response.data.data || [];
  } catch (error) {
    console.error('股票搜索失败:', error);
    return [];
  }
};

export const getStockInfo = async (symbol: string): Promise<StockInfo | null> => {
  try {
    const response = await api.get<ApiResponse<StockInfo>>(`/stocks/info/${symbol}`);
    return response.data.data || null;
  } catch (error) {
    console.error('获取股票信息失败:', error);
    return null;
  }
};

export const getStockStats = async () => {
  try {
    const response = await api.get<ApiResponse<{ total_stocks: number }>>('/stocks/stats');
    return response.data.data;
  } catch (error) {
    console.error('获取股票统计失败:', error);
    return null;
  }
};