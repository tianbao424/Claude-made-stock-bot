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

// 策略分析数据类型
export interface StrategyAnalysisData {
  // 股票基本信息
  stock_code: string;
  stock_name: string;
  industry?: string;
  
  // 持仓信息
  shares?: number;
  avg_cost?: number;
  current_price?: number;
  market_value?: number;
  profit_loss_pct?: number;
  profit_loss_amount?: number;
  
  // 技术分析数据
  price_trend_30d?: number[];
  rsi?: number;
  macd_signal?: string;
  support_level?: number;
  resistance_level?: number;
  volume_status?: string;
  
  // 基本面数据
  pe_ratio?: number;
  pb_ratio?: number;
  roe?: number;
  financial_health?: string;
  recent_performance?: string;
  industry_position?: string;
  
  // 市场环境
  market_trend?: string;
  sector_performance?: string;
  market_sentiment?: string;
}

// AI生成的投资策略
export interface GeneratedStrategy {
  comprehensive_score: number;
  risk_level: 'low' | 'medium' | 'high';
  action_recommendation: 'buy' | 'hold' | 'reduce' | 'sell';
  target_price_min: number;
  target_price_max: number;
  timeframe: 'short' | 'medium' | 'long';
  position_suggestion: number; // 0-1
  analysis_summary: string;
  key_metrics: string[];
  risk_warnings: string[];
  action_plan: string[];
  confidence_level: number;
  
  // 额外分析内容
  technical_analysis?: string;
  fundamental_analysis?: string;
  market_context?: string;
}

// 策略分析记录
export interface StrategyAnalysis {
  id?: number;
  stock_pool_id: number;
  stock_code: string;
  stock_name?: string;
  
  // 分析时的持仓数据
  shares_at_analysis?: number;
  cost_at_analysis?: number;
  price_at_analysis?: number;
  market_value_at_analysis?: number;
  profit_loss_pct?: number;
  
  // AI策略结果
  comprehensive_score: number;
  risk_level: string;
  action_recommendation: string;
  target_price_min: number;
  target_price_max: number;
  timeframe: string;
  position_suggestion: number;
  
  // 分析内容
  analysis_summary: string;
  key_metrics: string[];
  risk_warnings: string[];
  action_plan: string[];
  technical_analysis?: string;
  fundamental_analysis?: string;
  market_context?: string;
  
  // 元数据
  analysis_date?: string;
  model_version?: string;
  confidence_level: number;
  created_at?: string;
}

// 策略分析请求
export interface StrategyAnalysisRequest {
  stock_pool_id: number;
}

// 策略分析响应
export interface StrategyAnalysisResponse extends StrategyAnalysis {
  stock_name: string;
  current_price?: number;
  price_at_analysis?: number;
}