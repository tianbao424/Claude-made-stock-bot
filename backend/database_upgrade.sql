-- 数据库升级脚本 - 高级选股策略支持
-- 创建时间: 2025-01-06
-- 版本: v2.0

-- 技术指标表
CREATE TABLE IF NOT EXISTS stock_technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    
    -- 移动平均线
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma60 REAL,
    
    -- 量价指标
    volume_ratio REAL,        -- 量比
    turnover_rate REAL,       -- 换手率
    avg_volume_5d REAL,       -- 5日平均成交量
    avg_volume_20d REAL,      -- 20日平均成交量
    
    -- 技术指标
    kdj_k REAL,
    kdj_d REAL,
    kdj_j REAL,
    rsi_6 REAL,
    rsi_12 REAL,
    rsi_24 REAL,
    macd_dif REAL,
    macd_dea REAL,
    macd_hist REAL,
    obv REAL,
    
    -- 形态指标
    is_new_high BOOLEAN DEFAULT 0,    -- 是否创新高
    is_limit_up BOOLEAN DEFAULT 0,    -- 是否涨停
    has_gap_up BOOLEAN DEFAULT 0,     -- 是否向上跳空
    gap_ratio REAL,                   -- 跳空幅度
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tech_stock_date ON stock_technical_indicators(stock_code, trade_date);
CREATE INDEX IF NOT EXISTS idx_tech_trade_date ON stock_technical_indicators(trade_date);
CREATE INDEX IF NOT EXISTS idx_tech_stock_code ON stock_technical_indicators(stock_code);

-- 高级筛选结果表
CREATE TABLE IF NOT EXISTS advanced_screening_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    screening_date TEXT NOT NULL,
    
    -- 策略信息
    strategy_type TEXT NOT NULL,      -- 策略类型：daily/intraday/risk
    signal_type TEXT NOT NULL,        -- 信号类型：buy/sell/hold/wait
    signal_strength TEXT NOT NULL,    -- 信号强度：strong/medium/weak
    
    -- 分析结果
    score REAL NOT NULL,              -- 综合评分 0-100
    confidence REAL,                  -- 置信度 0-1
    reason TEXT,                      -- 触发原因
    risk_level TEXT,                  -- 风险等级：low/medium/high
    
    -- 技术数据
    current_price REAL,
    target_price REAL,
    stop_loss_price REAL,
    technical_data TEXT,              -- JSON格式的详细技术数据
    
    -- 策略详情
    strategies_passed TEXT,           -- JSON数组：通过的策略列表
    strategies_failed TEXT,           -- JSON数组：未通过的策略列表
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, screening_date, strategy_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_adv_screening_date ON advanced_screening_results(screening_date);
CREATE INDEX IF NOT EXISTS idx_adv_stock_code ON advanced_screening_results(stock_code);
CREATE INDEX IF NOT EXISTS idx_adv_signal_type ON advanced_screening_results(signal_type);
CREATE INDEX IF NOT EXISTS idx_adv_score ON advanced_screening_results(score);

-- 实时信号表
CREATE TABLE IF NOT EXISTS realtime_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    signal_time TEXT NOT NULL,
    
    -- 信号信息
    signal_type TEXT NOT NULL,        -- buy/sell/hold/alert
    price REAL NOT NULL,
    volume REAL,
    strategy_name TEXT NOT NULL,      -- 触发的策略名称
    
    -- 紧急程度
    urgency TEXT NOT NULL,            -- high/medium/low
    
    -- 详细信息
    details TEXT,                     -- JSON格式的详细信息
    message TEXT,                     -- 用户友好的消息
    
    -- 状态管理
    is_processed BOOLEAN DEFAULT 0,   -- 是否已处理
    is_notified BOOLEAN DEFAULT 0,    -- 是否已通知
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_rt_signal_time ON realtime_signals(signal_time);
CREATE INDEX IF NOT EXISTS idx_rt_stock_code ON realtime_signals(stock_code);
CREATE INDEX IF NOT EXISTS idx_rt_urgency ON realtime_signals(urgency);
CREATE INDEX IF NOT EXISTS idx_rt_processed ON realtime_signals(is_processed);

-- 策略配置表
CREATE TABLE IF NOT EXISTS strategy_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',  -- 用户ID（未来多用户支持）
    config_name TEXT NOT NULL,
    config_type TEXT NOT NULL,       -- daily/intraday/risk
    
    -- 配置数据
    config_data TEXT NOT NULL,       -- JSON格式的配置
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, config_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_strategy_config_user ON strategy_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_strategy_config_type ON strategy_configs(config_type);

-- 迁移历史表
CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    migration_version TEXT DEFAULT '2.0',
    description TEXT,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 插入迁移记录
INSERT OR IGNORE INTO migration_history (migration_name, description) 
VALUES ('001_add_technical_indicators', '添加技术指标和高级筛选支持表');

-- 检查表是否创建成功
SELECT name FROM sqlite_master WHERE type='table' AND name IN (
    'stock_technical_indicators',
    'advanced_screening_results', 
    'realtime_signals',
    'strategy_configs',
    'migration_history'
);