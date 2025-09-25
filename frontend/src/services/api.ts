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

// 为深度分析创建专门的API实例，使用更长的超时时间
export const deepAnalysisApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 深度分析超时120秒
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

// 深度分析API接口定义
export interface DeepAnalysisRequest {
  stock_codes: string[];
  save_results?: boolean;
}

export interface DeepAnalysisResult {
  stock_code: string;
  stock_name: string;
  analysis_date: string;
  overall_score: number;
  investment_grade: string;
  recommendation: string;
  risk_level: string;
  is_low_volatility_breakout: boolean;
  is_volume_price_coordinated: boolean;
  is_worthy_of_attention: boolean;
  volatility_analysis: {
    sideways_period_days: number;
    has_breakout: boolean;
    breakout_direction: string;
    volatility_score: number;
    pattern_quality: string;
  };
  volume_analysis: {
    has_volume_breakout: boolean;
    volume_score: number;
    money_flow_direction: string;
    price_volume_trend: string;
  };
  entry_suggestions: string[];
  position_size_suggestion: string;
  holding_period_suggestion: string;
}

export interface AutoPoolConfig {
  min_overall_score: number;
  min_volatility_score: number;
  min_volume_score: number;
  require_low_volatility_breakout: boolean;
  require_volume_coordination: boolean;
  min_sideways_days: number;
  allowed_investment_grades: string[];
  max_risk_level: string;
  auto_add_enabled: boolean;
  avoid_duplicates: boolean;
  max_auto_additions_per_day: number;
}

export interface AutoPoolStats {
  date: string;
  daily_additions_used: number;
  daily_quota_remaining: number;
  auto_add_enabled: boolean;
  config: AutoPoolConfig;
}

export interface ProcessingReport {
  total_analyzed: number;
  qualified_stocks: number;
  new_qualified_stocks: number;
  added_to_pool: number;
  daily_additions_used: number;
  daily_quota_remaining: number;
  qualified_stock_details: any[];
  added_stock_details: any[];
}

// 深度分析API
export const deepAnalysisAPI = {
  // 执行深度分析
  analyze: async (request: DeepAnalysisRequest): Promise<DeepAnalysisResult[]> => {
    const response = await deepAnalysisApi.post<ApiResponse<DeepAnalysisResult[]>>('/deep-analysis/analyze', request);
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.message || '深度分析失败');
    }
    return response.data.data;
  },

  // 获取分析结果
  getResults: async (stockCode?: string, limit: number = 50): Promise<any[]> => {
    const params: any = { limit };
    if (stockCode) {
      params.stock_code = stockCode;
    }
    
    const response = await api.get<ApiResponse<any[]>>('/deep-analysis/results', { params });
    return response.data.data || [];
  },

  // 获取值得关注的股票
  getWorthyStocks: async (limit: number = 20): Promise<any[]> => {
    const response = await api.get<ApiResponse<any[]>>('/deep-analysis/worthy-stocks', {
      params: { limit }
    });
    return response.data.data || [];
  }
};

// 自动池管理API
export const autoPoolAPI = {
  // 处理筛选结果
  processScreening: async (): Promise<ProcessingReport> => {
    const response = await api.post<ApiResponse<ProcessingReport>>('/auto-pool/process-screening');
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.message || '处理筛选结果失败');
    }
    return response.data.data;
  },

  // 获取配置
  getConfig: async (): Promise<AutoPoolStats> => {
    const response = await api.get<ApiResponse<AutoPoolStats>>('/auto-pool/config');
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.message || '获取配置失败');
    }
    return response.data.data;
  },

  // 更新配置
  updateConfig: async (config: AutoPoolConfig): Promise<AutoPoolStats> => {
    const response = await api.put<ApiResponse<AutoPoolStats>>('/auto-pool/config', config);
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.message || '更新配置失败');
    }
    return response.data.data;
  },

  // 获取处理记录
  getRecords: async (days: number = 7): Promise<any[]> => {
    const response = await api.get<ApiResponse<any[]>>('/auto-pool/records', {
      params: { days }
    });
    return response.data.data || [];
  }
};