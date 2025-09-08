// 股票池类型定义
export interface StockPool {
  id?: number;
  stock_code: string;
  stock_name: string;
  pool_type: 'holding' | 'potential';
  shares?: number;
  avg_cost?: number;
  current_price?: number;
  market_value?: number;
  tags?: string[];
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'query' | 'response' | 'error';
  content: string;
  timestamp?: string;
}

// 聊天消息类型
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
}