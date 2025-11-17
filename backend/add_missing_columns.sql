-- 添加缺失的列到技术指标表
-- 创建时间: 2025-01-19

-- 添加均线多头排列标志
ALTER TABLE stock_technical_indicators ADD COLUMN is_bullish_aligned BOOLEAN DEFAULT 0;

-- 添加其他可能缺失的趋势相关列
ALTER TABLE stock_technical_indicators ADD COLUMN trend_strength REAL DEFAULT 0;
ALTER TABLE stock_technical_indicators ADD COLUMN trend_direction TEXT DEFAULT 'neutral';

-- 显示更新结果
SELECT '✅ 成功添加缺失的列到 stock_technical_indicators 表' as message;