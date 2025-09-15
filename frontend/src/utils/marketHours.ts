/**
 * 股市交易时间工具类
 * 支持A股和港股的交易时间判断
 */

interface TradingSession {
  start: string; // HH:mm格式
  end: string;
}

interface MarketHours {
  sessions: TradingSession[];
  timezone: string;
}

// 股市交易时间配置
const MARKET_HOURS: Record<string, MarketHours> = {
  'A股': {
    sessions: [
      { start: '09:30', end: '11:30' }, // 上午交易
      { start: '13:00', end: '15:00' }  // 下午交易
    ],
    timezone: 'Asia/Shanghai'
  },
  '港股': {
    sessions: [
      { start: '09:30', end: '12:00' }, // 上午交易
      { start: '13:00', end: '16:00' }  // 下午交易
    ],
    timezone: 'Asia/Hong_Kong'
  }
};

// 节假日配置（简化版，实际应从API获取）
const HOLIDAYS_2024 = [
  '2024-01-01', // 元旦
  '2024-02-10', '2024-02-11', '2024-02-12', '2024-02-13', '2024-02-14', '2024-02-15', '2024-02-16', // 春节
  '2024-04-04', '2024-04-05', '2024-04-06', // 清明节
  '2024-05-01', '2024-05-02', '2024-05-03', // 劳动节
  '2024-06-10', // 端午节
  '2024-09-15', '2024-09-16', '2024-09-17', // 中秋节
  '2024-10-01', '2024-10-02', '2024-10-03', '2024-10-04', '2024-10-05', '2024-10-06', '2024-10-07', // 国庆节
];

/**
 * 判断当前是否为工作日
 */
export function isWeekday(date: Date = new Date()): boolean {
  const day = date.getDay();
  return day >= 1 && day <= 5; // 周一到周五
}

/**
 * 判断当前是否为节假日
 */
export function isHoliday(date: Date = new Date()): boolean {
  const dateStr = date.toISOString().split('T')[0];
  return HOLIDAYS_2024.includes(dateStr);
}

/**
 * 判断指定时间是否在交易时段内
 */
export function isInTradingHours(market: string, date: Date = new Date()): boolean {
  // 非工作日或节假日不交易
  if (!isWeekday(date) || isHoliday(date)) {
    return false;
  }

  const marketConfig = MARKET_HOURS[market];
  if (!marketConfig) {
    return false;
  }

  const currentTime = date.toTimeString().substr(0, 5); // HH:mm格式

  // 检查是否在任一交易时段内
  return marketConfig.sessions.some(session => {
    return currentTime >= session.start && currentTime <= session.end;
  });
}

/**
 * 判断当前是否为任一市场的交易时间
 */
export function isAnyMarketOpen(date: Date = new Date()): boolean {
  return Object.keys(MARKET_HOURS).some(market => 
    isInTradingHours(market, date)
  );
}

/**
 * 获取下一个交易时段的开始时间
 */
export function getNextTradingSession(market: string, date: Date = new Date()): Date | null {
  const marketConfig = MARKET_HOURS[market];
  if (!marketConfig) {
    return null;
  }

  // 如果是节假日，跳到下个工作日
  let nextDate = new Date(date);
  while (!isWeekday(nextDate) || isHoliday(nextDate)) {
    nextDate.setDate(nextDate.getDate() + 1);
    nextDate.setHours(0, 0, 0, 0);
  }

  const currentTime = nextDate.toTimeString().substr(0, 5);
  
  // 查找当天的下一个交易时段
  for (const session of marketConfig.sessions) {
    if (currentTime < session.start) {
      const [hours, minutes] = session.start.split(':').map(Number);
      nextDate.setHours(hours, minutes, 0, 0);
      return nextDate;
    }
  }

  // 当天没有更多交易时段，返回下个交易日的第一个时段
  nextDate.setDate(nextDate.getDate() + 1);
  while (!isWeekday(nextDate) || isHoliday(nextDate)) {
    nextDate.setDate(nextDate.getDate() + 1);
  }
  
  const [hours, minutes] = marketConfig.sessions[0].start.split(':').map(Number);
  nextDate.setHours(hours, minutes, 0, 0);
  return nextDate;
}

/**
 * 获取距离交易结束的时间（分钟）
 */
export function getMinutesUntilMarketClose(market: string, date: Date = new Date()): number | null {
  if (!isInTradingHours(market, date)) {
    return null;
  }

  const marketConfig = MARKET_HOURS[market];
  const currentTime = date.toTimeString().substr(0, 5);

  // 找到当前所在的交易时段
  for (const session of marketConfig.sessions) {
    if (currentTime >= session.start && currentTime <= session.end) {
      const [endHours, endMinutes] = session.end.split(':').map(Number);
      const endTime = new Date(date);
      endTime.setHours(endHours, endMinutes, 0, 0);
      
      return Math.floor((endTime.getTime() - date.getTime()) / (1000 * 60));
    }
  }

  return null;
}

/**
 * 根据市场状态推荐数据检查频率
 */
export interface CheckFrequencyConfig {
  interval: number; // 毫秒
  description: string;
  shouldCheck: boolean;
  nextCheckTime?: Date; // 下次检查时间
}

export function getRecommendedCheckFrequency(date: Date = new Date()): CheckFrequencyConfig {
  // 非交易日 - 不检查
  if (!isWeekday(date) || isHoliday(date)) {
    return {
      interval: 0,
      description: '休息日 - 暂停监控',
      shouldCheck: false
    };
  }

  // 交易时间 - 高频检查
  if (isAnyMarketOpen(date)) {
    return {
      interval: 60000, // 1分钟
      description: '交易时间 - 实时监控',
      shouldCheck: true
    };
  }

  // 交易日但非交易时间 - 仅在关键时点检查
  const currentTime = date.toTimeString().substr(0, 5);
  const currentHour = date.getHours();
  const currentMinute = date.getMinutes();
  
  // 开盘前准备时间 (8:30-9:30) - 仅在8:30检查一次
  if (currentHour === 8 && currentMinute >= 30) {
    return {
      interval: 0, // 单次检查，不重复
      description: '开盘前检查 - 准备交易',
      shouldCheck: currentMinute === 30, // 仅在8:30检查
      nextCheckTime: getNextCheckTime('pre_market', date)
    };
  }
  
  // 收盘后检查 (15:10-15:30) - 仅在15:10检查一次（A股收盘后）
  if (currentHour === 15 && currentMinute >= 10 && currentMinute < 30) {
    return {
      interval: 0, // 单次检查，不重复
      description: '收盘后检查 - 交易结束',
      shouldCheck: currentMinute === 10, // 仅在15:10检查
      nextCheckTime: getNextCheckTime('post_market', date)
    };
  }
  
  // 港股收盘后检查 (16:10-16:30) - 仅在16:10检查一次
  if (currentHour === 16 && currentMinute >= 10 && currentMinute < 30) {
    return {
      interval: 0, // 单次检查，不重复
      description: '港股收盘后检查 - 交易结束',
      shouldCheck: currentMinute === 10, // 仅在16:10检查
      nextCheckTime: getNextCheckTime('post_hk_market', date)
    };
  }
  
  // 其他时间 - 不检查
  return {
    interval: 0,
    description: '休市时间 - 暂停监控',
    shouldCheck: false,
    nextCheckTime: getNextCheckTime('next_session', date)
  };
}

/**
 * 获取下次检查时间
 */
function getNextCheckTime(checkType: string, date: Date): Date {
  const nextCheck = new Date(date);
  
  switch (checkType) {
    case 'pre_market':
      // 下次检查：当天15:10收盘后
      nextCheck.setHours(15, 10, 0, 0);
      if (nextCheck <= date) {
        // 如果已过15:10，则下次是16:10港股收盘后
        nextCheck.setHours(16, 10, 0, 0);
      }
      break;
      
    case 'post_market':
      // 下次检查：当天16:10港股收盘后
      nextCheck.setHours(16, 10, 0, 0);
      if (nextCheck <= date) {
        // 如果已过16:10，则下次是明天8:30开盘前
        nextCheck.setDate(nextCheck.getDate() + 1);
        nextCheck.setHours(8, 30, 0, 0);
        // 跳过周末和节假日
        while (!isWeekday(nextCheck) || isHoliday(nextCheck)) {
          nextCheck.setDate(nextCheck.getDate() + 1);
        }
      }
      break;
      
    case 'post_hk_market':
      // 下次检查：明天8:30开盘前
      nextCheck.setDate(nextCheck.getDate() + 1);
      nextCheck.setHours(8, 30, 0, 0);
      // 跳过周末和节假日
      while (!isWeekday(nextCheck) || isHoliday(nextCheck)) {
        nextCheck.setDate(nextCheck.getDate() + 1);
      }
      break;
      
    case 'next_session':
    default:
      // 根据当前时间决定下次检查时间
      const currentHour = date.getHours();
      
      if (currentHour < 8) {
        // 早于8点，下次检查8:30
        nextCheck.setHours(8, 30, 0, 0);
      } else if (currentHour < 15) {
        // 8点-15点之间，下次检查15:10
        nextCheck.setHours(15, 10, 0, 0);
      } else if (currentHour < 16) {
        // 15点-16点之间，下次检查16:10
        nextCheck.setHours(16, 10, 0, 0);
      } else {
        // 16点之后，下次检查明天8:30
        nextCheck.setDate(nextCheck.getDate() + 1);
        nextCheck.setHours(8, 30, 0, 0);
        // 跳过周末和节假日
        while (!isWeekday(nextCheck) || isHoliday(nextCheck)) {
          nextCheck.setDate(nextCheck.getDate() + 1);
        }
      }
      break;
  }
  
  return nextCheck;
}

/**
 * 获取市场状态摘要
 */
export function getMarketStatusSummary(date: Date = new Date()) {
  const aStockOpen = isInTradingHours('A股', date);
  const hkStockOpen = isInTradingHours('港股', date);
  
  return {
    isWeekday: isWeekday(date),
    isHoliday: isHoliday(date),
    aStockOpen,
    hkStockOpen,
    anyMarketOpen: aStockOpen || hkStockOpen,
    recommendedFrequency: getRecommendedCheckFrequency(date)
  };
}