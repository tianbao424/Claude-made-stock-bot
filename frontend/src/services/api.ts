import axios from 'axios';
import { StockPool, ApiResponse, StrategyAnalysis, StrategyAnalysisResponse } from '../types';

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
  timeout: 10000, // 默认超时10秒
});

// 为策略分析创建专门的API实例，使用更长的超时时间
export const strategyApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 策略分析超时60秒
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

// 添加股票到股票池的接口
export interface AddToPoolRequest {
  pool_type: 'holding' | 'potential';
  tags?: string[];
  notes?: string;
  shares?: number;
  avg_cost?: number;
}

export const addStockToPool = async (symbol: string, request: AddToPoolRequest): Promise<{success: boolean, message: string, data?: StockPool}> => {
  try {
    const response = await api.post<ApiResponse<StockPool>>(`/stocks/${symbol}/add-to-pool`, request);
    return {
      success: response.data.success,
      message: response.data.message || '添加成功',
      data: response.data.data
    };
  } catch (error: any) {
    if (error.response?.data?.success === false) {
      return {
        success: false,
        message: error.response.data.message || '添加失败'
      };
    }
    throw error;
  }
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

export const getStockPrice = async (symbol: string): Promise<number> => {
  try {
    const response = await api.get<ApiResponse<{ symbol: string, current_price: number }>>(`/stocks/${symbol}/price`);
    return response.data.data?.current_price || 0;
  } catch (error) {
    console.error('获取股票价格失败:', error);
    return 0;
  }
};

// 策略分析API
export const strategyAPI = {
  // 生成策略分析 - 使用长超时时间
  generateAnalysis: async (stockPoolId: number): Promise<StrategyAnalysisResponse> => {
    const response = await strategyApi.post<ApiResponse<StrategyAnalysisResponse>>(`/strategy/generate/${stockPoolId}`);
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.message || '策略分析生成失败');
    }
    return response.data.data;
  },

  // 获取策略分析历史
  getHistory: async (stockPoolId: number, limit: number = 10): Promise<StrategyAnalysisResponse[]> => {
    const response = await api.get<ApiResponse<StrategyAnalysisResponse[]>>(`/strategy/history/${stockPoolId}`, {
      params: { limit }
    });
    return response.data.data || [];
  },

  // 获取单个策略分析详情
  getAnalysis: async (strategyId: number): Promise<StrategyAnalysisResponse | null> => {
    try {
      const response = await api.get<ApiResponse<StrategyAnalysisResponse>>(`/strategy/${strategyId}`);
      return response.data.data || null;
    } catch (error) {
      console.error('获取策略分析详情失败:', error);
      return null;
    }
  }
};