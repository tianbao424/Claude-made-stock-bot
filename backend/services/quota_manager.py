"""
API配额管理器
处理各种外部服务的配额限制和降级策略
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class QuotaLimit:
    """配额限制配置"""
    service_name: str
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    current_minute_count: int = 0
    current_hour_count: int = 0
    current_day_count: int = 0
    last_reset_minute: int = 0
    last_reset_hour: int = 0
    last_reset_day: str = ""

class QuotaManager:
    """配额管理器"""
    
    def __init__(self):
        self.quotas: Dict[str, QuotaLimit] = {}
        self.fallback_enabled = True
        
        # 预定义常见服务的配额限制
        self._init_default_quotas()
    
    def _init_default_quotas(self):
        """初始化默认配额限制"""
        self.quotas["claude_api"] = QuotaLimit(
            service_name="claude_api",
            requests_per_minute=50,
            requests_per_hour=500,
            requests_per_day=5000
        )
        
        self.quotas["akshare_api"] = QuotaLimit(
            service_name="akshare_api", 
            requests_per_minute=20,
            requests_per_hour=200,
            requests_per_day=2000
        )
        
        self.quotas["strategy_screening"] = QuotaLimit(
            service_name="strategy_screening",
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500
        )
    
    def check_quota(self, service_name: str) -> bool:
        """检查服务配额是否可用"""
        if service_name not in self.quotas:
            logger.warning(f"未知服务 {service_name}，允许请求")
            return True
        
        quota = self.quotas[service_name]
        now = datetime.now()
        
        # 重置计数器
        self._reset_counters(quota, now)
        
        # 检查各级配额
        if quota.current_minute_count >= quota.requests_per_minute:
            logger.warning(f"服务 {service_name} 每分钟配额已用尽")
            return False
        
        if quota.current_hour_count >= quota.requests_per_hour:
            logger.warning(f"服务 {service_name} 每小时配额已用尽")
            return False
            
        if quota.current_day_count >= quota.requests_per_day:
            logger.warning(f"服务 {service_name} 每日配额已用尽")
            return False
        
        return True
    
    def record_request(self, service_name: str):
        """记录一次API请求"""
        if service_name not in self.quotas:
            return
        
        quota = self.quotas[service_name]
        now = datetime.now()
        
        # 重置计数器
        self._reset_counters(quota, now)
        
        # 增加计数
        quota.current_minute_count += 1
        quota.current_hour_count += 1
        quota.current_day_count += 1
        
        logger.debug(f"记录 {service_name} 请求: 分钟 {quota.current_minute_count}/{quota.requests_per_minute}")
    
    def _reset_counters(self, quota: QuotaLimit, now: datetime):
        """重置计数器"""
        current_minute = now.minute
        current_hour = now.hour
        current_day = now.strftime('%Y-%m-%d')
        
        # 重置分钟计数器
        if current_minute != quota.last_reset_minute:
            quota.current_minute_count = 0
            quota.last_reset_minute = current_minute
        
        # 重置小时计数器
        if current_hour != quota.last_reset_hour:
            quota.current_hour_count = 0
            quota.last_reset_hour = current_hour
        
        # 重置日计数器
        if current_day != quota.last_reset_day:
            quota.current_day_count = 0
            quota.last_reset_day = current_day
    
    def get_quota_status(self, service_name: str) -> Dict[str, Any]:
        """获取配额使用状态"""
        if service_name not in self.quotas:
            return {"error": f"未知服务: {service_name}"}
        
        quota = self.quotas[service_name]
        now = datetime.now()
        self._reset_counters(quota, now)
        
        return {
            "service": service_name,
            "minute_usage": f"{quota.current_minute_count}/{quota.requests_per_minute}",
            "hour_usage": f"{quota.current_hour_count}/{quota.requests_per_hour}",
            "day_usage": f"{quota.current_day_count}/{quota.requests_per_day}",
            "available": self.check_quota(service_name)
        }
    
    async def with_quota_check(self, service_name: str, func, *args, **kwargs):
        """带配额检查的函数调用"""
        if not self.check_quota(service_name):
            if self.fallback_enabled:
                logger.info(f"服务 {service_name} 配额不足，使用降级策略")
                return await self._fallback_strategy(service_name, func, *args, **kwargs)
            else:
                raise Exception(f"服务 {service_name} 的配额已用尽，请稍后重试")
        
        try:
            self.record_request(service_name)
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            return result
        except Exception as e:
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                logger.error(f"外部服务配额错误: {e}")
                if self.fallback_enabled:
                    return await self._fallback_strategy(service_name, func, *args, **kwargs)
                else:
                    raise
            else:
                raise
    
    async def _fallback_strategy(self, service_name: str, func, *args, **kwargs):
        """降级策略"""
        logger.info(f"执行 {service_name} 的降级策略")
        
        if service_name == "strategy_screening":
            # 策略筛选降级：返回模拟结果
            return {
                "success": True,
                "data": {
                    "results": [],
                    "message": "配额已用尽，请稍后重试或联系管理员",
                    "fallback": True
                }
            }
        
        elif service_name == "claude_api":
            # Claude API降级：返回基础响应
            return {
                "message": "AI分析服务暂时不可用，请稍后重试",
                "fallback": True
            }
        
        else:
            # 默认降级策略
            logger.warning(f"服务 {service_name} 配额不足，等待1分钟后重试")
            await asyncio.sleep(60)
            
            # 重试一次
            if self.check_quota(service_name):
                self.record_request(service_name)
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            else:
                raise Exception(f"配额限制：{service_name} 暂时不可用")

# 全局配额管理器实例
quota_manager = QuotaManager()

def get_quota_manager() -> QuotaManager:
    """获取配额管理器实例"""
    return quota_manager