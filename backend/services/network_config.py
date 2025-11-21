#!/usr/bin/env python3
"""
网络连接优化配置
针对AkShare API的网络问题提供配置优化
"""

# 网络重试配置
NETWORK_CONFIG = {
    # 重试配置
    'max_retries': 3,
    'initial_backoff': 0.5,  # 初始退避时间（秒）
    'max_backoff': 30.0,     # 最大退避时间（秒）
    'backoff_multiplier': 2.0, # 退避倍数
    
    # 超时配置
    'request_timeout': 30.0,  # 单个请求超时时间
    'connect_timeout': 10.0,  # 连接超时时间
    
    # 批次配置
    'batch_size': 20,         # 每批处理的股票数量
    'batch_delay': 30.0,      # 批次间延迟时间（秒）
    'individual_delay': 0.3,  # 单个请求间延迟时间（秒）
    
    # 网络状态判断
    'failure_threshold': 10,  # 连续失败次数阈值
    'pause_duration': 120,    # 网络状况不佳时的暂停时间（秒）
    'recovery_threshold': 3,  # 恢复阈值（连续成功次数）
    
    # API接口优先级（1=最高优先级）
    'api_priority': {
        'tencent': 1,           # 腾讯财经接口
        'akshare_hist': 2,      # AkShare历史接口
        'akshare_em': 3,        # AkShare东财接口
        'akshare_daily': 4,     # AkShare日线接口
        'akshare_simple': 5,    # AkShare简化接口
    },
    
    # 错误类型处理
    'error_handling': {
        'connection_errors': [
            'Connection aborted',
            'RemoteDisconnected',
            'ConnectionResetError',
            'TimeoutError',
            'ConnectTimeout',
        ],
        'rate_limit_errors': [
            'HTTPError: 429',
            'Too Many Requests',
            'Rate limit exceeded',
        ],
        'temporary_errors': [
            'HTTPError: 502',
            'HTTPError: 503',
            'HTTPError: 504',
            'Bad Gateway',
            'Service Unavailable',
            'Gateway Timeout',
        ]
    },
    
    # 特殊处理的股票代码模式
    'special_handling': {
        # 科创板股票（688开头）- 可能需要特殊处理
        '688': {
            'delay_multiplier': 1.5,
            'max_retries': 2,
        },
        # 创业板股票（300开头）- 你遇到问题的股票
        '300': {
            'delay_multiplier': 2.0,
            'max_retries': 2,
            'use_alternative_api': True,
        },
        # 新股或ST股票可能需要特殊处理
        'st': {
            'delay_multiplier': 1.2,
            'skip_on_error': True,
        }
    }
}

# 网络优化建议
OPTIMIZATION_TIPS = {
    'best_practices': [
        "避免在交易时间（9:30-15:00）进行大量数据采集",
        "每批次之间保持足够的间隔时间",
        "监控连续失败次数，及时调整策略",
        "使用多个数据源进行回退",
        "对于问题股票，可以稍后重试"
    ],
    
    'timing_recommendations': {
        'optimal_hours': [
            '16:00-20:00',  # 交易结束后
            '21:00-23:00',  # 晚间
            '06:00-09:00',  # 早晨
        ],
        'avoid_hours': [
            '09:00-09:30',  # 开盘前准备
            '09:30-15:00',  # 交易时间
            '15:00-16:00',  # 收盘处理
        ]
    },
    
    'network_quality_indicators': {
        'excellent': {'success_rate': 0.95, 'avg_response_time': 2.0},
        'good': {'success_rate': 0.85, 'avg_response_time': 5.0},
        'fair': {'success_rate': 0.70, 'avg_response_time': 10.0},
        'poor': {'success_rate': 0.50, 'avg_response_time': 15.0},
        'terrible': {'success_rate': 0.30, 'avg_response_time': 30.0},
    }
}

def get_optimal_config_for_time():
    """根据当前时间获取最优配置"""
    from datetime import datetime
    now = datetime.now()
    hour = now.hour
    
    # 交易时间内使用更保守的配置
    if 9 <= hour <= 15:
        return {
            **NETWORK_CONFIG,
            'batch_size': 10,
            'batch_delay': 60.0,
            'individual_delay': 1.0,
            'max_retries': 2,
        }
    # 晚间和早晨可以更激进一些
    elif hour >= 21 or hour <= 6:
        return {
            **NETWORK_CONFIG,
            'batch_size': 30,
            'batch_delay': 15.0,
            'individual_delay': 0.2,
        }
    # 其他时间使用默认配置
    else:
        return NETWORK_CONFIG

def get_stock_specific_config(symbol: str):
    """根据股票代码获取特定配置"""
    config = NETWORK_CONFIG.copy()
    
    # 检查特殊处理规则
    for pattern, special_config in NETWORK_CONFIG['special_handling'].items():
        if symbol.startswith(pattern):
            # 应用特殊配置
            if 'delay_multiplier' in special_config:
                config['individual_delay'] *= special_config['delay_multiplier']
                config['batch_delay'] *= special_config['delay_multiplier']
            
            if 'max_retries' in special_config:
                config['max_retries'] = special_config['max_retries']
            
            break
    
    return config

def should_skip_stock(symbol: str, error_history: list) -> bool:
    """判断是否应该跳过某只股票"""
    
    # 检查是否是问题股票代码
    if symbol.startswith('300') and len(error_history) >= 3:
        # 创业板股票连续失败3次就跳过
        return True
    
    # 检查错误历史
    recent_errors = error_history[-5:]  # 最近5次错误
    connection_errors = sum(1 for error in recent_errors 
                          if any(err_type in str(error) 
                                for err_type in NETWORK_CONFIG['error_handling']['connection_errors']))
    
    # 如果最近5次中有4次是连接错误，跳过
    if connection_errors >= 4:
        return True
    
    return False

def estimate_completion_time(total_stocks: int, success_rate: float = 0.7) -> dict:
    """估算完成时间"""
    config = get_optimal_config_for_time()
    
    # 计算批次数
    batch_count = (total_stocks + config['batch_size'] - 1) // config['batch_size']
    
    # 估算每批次时间
    time_per_stock = config['individual_delay'] + (config['request_timeout'] / 2)
    time_per_batch = config['batch_size'] * time_per_stock + config['batch_delay']
    
    # 考虑失败重试的额外时间
    retry_overhead = (1 - success_rate) * config['max_retries'] * config['max_backoff']
    
    total_time = batch_count * time_per_batch + total_stocks * retry_overhead
    
    return {
        'total_time_seconds': total_time,
        'total_time_minutes': total_time / 60,
        'total_time_hours': total_time / 3600,
        'estimated_batches': batch_count,
        'time_per_batch_minutes': time_per_batch / 60,
    }

if __name__ == "__main__":
    # 测试配置
    print("🔧 网络配置测试")
    print("=" * 50)
    
    # 测试时间相关配置
    config = get_optimal_config_for_time()
    print(f"当前时间最优配置:")
    print(f"  批次大小: {config['batch_size']}")
    print(f"  批次延迟: {config['batch_delay']}秒")
    print(f"  单个延迟: {config['individual_delay']}秒")
    print()
    
    # 测试股票特定配置
    test_stocks = ['000001', '300001', '688001']
    for stock in test_stocks:
        stock_config = get_stock_specific_config(stock)
        print(f"股票 {stock} 配置:")
        print(f"  延迟: {stock_config['individual_delay']}秒")
        print(f"  重试次数: {stock_config['max_retries']}")
    print()
    
    # 测试完成时间估算
    estimation = estimate_completion_time(1000, 0.8)
    print(f"1000只股票预计完成时间:")
    print(f"  总时间: {estimation['total_time_hours']:.1f} 小时")
    print(f"  批次数: {estimation['estimated_batches']}")
    print(f"  每批次时间: {estimation['time_per_batch_minutes']:.1f} 分钟")