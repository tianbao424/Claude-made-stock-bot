"""
股市交易时间工具类（后端版本）
支持A股和港股的交易时间判断
"""
from datetime import datetime, time
from typing import Dict, List

# 节假日配置（简化版，实际应从API获取）
HOLIDAYS_2024 = [
    '2024-01-01', # 元旦
    '2024-02-10', '2024-02-11', '2024-02-12', '2024-02-13', 
    '2024-02-14', '2024-02-15', '2024-02-16', # 春节
    '2024-04-04', '2024-04-05', '2024-04-06', # 清明节
    '2024-05-01', '2024-05-02', '2024-05-03', # 劳动节
    '2024-06-10', # 端午节
    '2024-09-15', '2024-09-16', '2024-09-17', # 中秋节
    '2024-10-01', '2024-10-02', '2024-10-03', '2024-10-04',
    '2024-10-05', '2024-10-06', '2024-10-07', # 国庆节
]

# 2025年节假日配置
HOLIDAYS_2025 = [
    '2025-01-01', # 元旦
    '2025-01-28', '2025-01-29', '2025-01-30', '2025-01-31', 
    '2025-02-03', '2025-02-04', # 春节
    '2025-04-05', '2025-04-06', '2025-04-07', # 清明节
    '2025-05-01', '2025-05-02', '2025-05-05', # 劳动节
    '2025-05-31', # 端午节
    '2025-10-01', '2025-10-02', '2025-10-03', '2025-10-06',
    '2025-10-07', '2025-10-08', # 国庆节
]

# 合并节假日配置
ALL_HOLIDAYS = HOLIDAYS_2024 + HOLIDAYS_2025

def isWeekday(date: datetime = None) -> bool:
    """判断是否为工作日"""
    if date is None:
        date = datetime.now()
    day = date.weekday()
    return day < 5  # 0-4 表示周一到周五

def isHoliday(date: datetime = None) -> bool:
    """判断是否为节假日"""
    if date is None:
        date = datetime.now()
    date_str = date.strftime('%Y-%m-%d')
    return date_str in ALL_HOLIDAYS

def isAnyMarketOpen(date: datetime = None) -> bool:
    """判断是否有任何市场开盘"""
    if date is None:
        date = datetime.now()
    
    if not isWeekday(date) or isHoliday(date):
        return False
    
    current_time = date.time()
    
    # A股和港股交易时间检查
    # 上午时段：9:30-11:30 (A股) / 9:30-12:00 (港股)
    morning_start = time(9, 30)
    a_morning_end = time(11, 30)
    hk_morning_end = time(12, 0)
    
    # 下午时段：13:00-15:00 (A股) / 13:00-16:00 (港股)  
    afternoon_start = time(13, 0)
    a_afternoon_end = time(15, 0)
    hk_afternoon_end = time(16, 0)
    
    # 检查是否在任一交易时段内
    in_morning = morning_start <= current_time <= hk_morning_end
    in_afternoon = afternoon_start <= current_time <= hk_afternoon_end
    
    return in_morning or in_afternoon

def getRecommendedCheckFrequency(date: datetime = None) -> Dict:
    """根据市场状态推荐检查频率"""
    if date is None:
        date = datetime.now()
    
    # 非交易日 - 不检查
    if not isWeekday(date) or isHoliday(date):
        return {
            'interval': 0,
            'description': '休息日 - 暂停监控',
            'shouldCheck': False
        }
    
    # 交易时间 - 高频检查
    if isAnyMarketOpen(date):
        return {
            'interval': 60000,  # 1分钟
            'description': '交易时间 - 实时监控',
            'shouldCheck': True
        }
    
    # 交易日但非交易时间 - 仅在关键时点检查
    current_hour = date.hour
    current_minute = date.minute
    
    # 开盘前准备时间 (8:30) - 仅在8:30检查一次
    if current_hour == 8 and current_minute >= 30:
        return {
            'interval': 0,  # 单次检查，不重复
            'description': '开盘前检查 - 准备交易',
            'shouldCheck': current_minute == 30,  # 仅在8:30检查
            'nextCheckTime': getNextCheckTime('pre_market', date)
        }
    
    # 收盘后检查 (15:10) - 仅在15:10检查一次（A股收盘后）
    if current_hour == 15 and 10 <= current_minute < 30:
        return {
            'interval': 0,  # 单次检查，不重复
            'description': '收盘后检查 - 交易结束',
            'shouldCheck': current_minute == 10,  # 仅在15:10检查
            'nextCheckTime': getNextCheckTime('post_market', date)
        }
    
    # 港股收盘后检查 (16:10) - 仅在16:10检查一次
    if current_hour == 16 and 10 <= current_minute < 30:
        return {
            'interval': 0,  # 单次检查，不重复
            'description': '港股收盘后检查 - 交易结束',
            'shouldCheck': current_minute == 10,  # 仅在16:10检查
            'nextCheckTime': getNextCheckTime('post_hk_market', date)
        }
    
    # 其他时间 - 不检查
    return {
        'interval': 0,
        'description': '休市时间 - 暂停监控',
        'shouldCheck': False,
        'nextCheckTime': getNextCheckTime('next_session', date)
    }

def getNextCheckTime(check_type: str, date: datetime) -> str:
    """获取下次检查时间"""
    from datetime import datetime, timedelta
    
    next_check = datetime(date.year, date.month, date.day)
    
    if check_type == 'pre_market':
        # 下次检查：当天15:10收盘后
        next_check = next_check.replace(hour=15, minute=10, second=0, microsecond=0)
        if next_check <= date:
            # 如果已过15:10，则下次是16:10港股收盘后
            next_check = next_check.replace(hour=16, minute=10)
    
    elif check_type == 'post_market':
        # 下次检查：当天16:10港股收盘后
        next_check = next_check.replace(hour=16, minute=10, second=0, microsecond=0)
        if next_check <= date:
            # 如果已过16:10，则下次是明天8:30开盘前
            next_check += timedelta(days=1)
            next_check = next_check.replace(hour=8, minute=30)
            # 跳过周末和节假日
            while not isWeekday(next_check) or isHoliday(next_check):
                next_check += timedelta(days=1)
    
    elif check_type == 'post_hk_market':
        # 下次检查：明天8:30开盘前
        next_check += timedelta(days=1)
        next_check = next_check.replace(hour=8, minute=30, second=0, microsecond=0)
        # 跳过周末和节假日
        while not isWeekday(next_check) or isHoliday(next_check):
            next_check += timedelta(days=1)
    
    else:  # 'next_session' 或其他
        # 根据当前时间决定下次检查时间
        current_hour = date.hour
        
        if current_hour < 8:
            # 早于8点，下次检查8:30
            next_check = next_check.replace(hour=8, minute=30, second=0, microsecond=0)
        elif current_hour < 15:
            # 8点-15点之间，下次检查15:10
            next_check = next_check.replace(hour=15, minute=10, second=0, microsecond=0)
        elif current_hour < 16:
            # 15点-16点之间，下次检查16:10
            next_check = next_check.replace(hour=16, minute=10, second=0, microsecond=0)
        else:
            # 16点之后，下次检查明天8:30
            next_check += timedelta(days=1)
            next_check = next_check.replace(hour=8, minute=30, second=0, microsecond=0)
            # 跳过周末和节假日
            while not isWeekday(next_check) or isHoliday(next_check):
                next_check += timedelta(days=1)
    
    return next_check.isoformat()

def getMarketStatusSummary(date: datetime = None) -> Dict:
    """获取市场状态摘要"""
    if date is None:
        date = datetime.now()
    
    current_time = date.time()
    
    # A股交易时间判断
    a_morning = time(9, 30) <= current_time <= time(11, 30)
    a_afternoon = time(13, 0) <= current_time <= time(15, 0)
    a_stock_open = (a_morning or a_afternoon) and isWeekday(date) and not isHoliday(date)
    
    # 港股交易时间判断
    hk_morning = time(9, 30) <= current_time <= time(12, 0)
    hk_afternoon = time(13, 0) <= current_time <= time(16, 0)
    hk_stock_open = (hk_morning or hk_afternoon) and isWeekday(date) and not isHoliday(date)
    
    return {
        'isWeekday': isWeekday(date),
        'isHoliday': isHoliday(date),
        'aStockOpen': a_stock_open,
        'hkStockOpen': hk_stock_open,
        'anyMarketOpen': a_stock_open or hk_stock_open,
        'recommendedFrequency': getRecommendedCheckFrequency(date)
    }