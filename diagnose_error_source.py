#!/usr/bin/env python3
"""
诊断英文配额错误的来源
"""
import sys
import traceback
import logging

# 设置日志记录所有异常
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 重写Exception类来追踪所有异常
original_exception_init = Exception.__init__

def traced_exception_init(self, *args, **kwargs):
    # 检查是否是我们要找的英文错误
    if args and isinstance(args[0], str) and "The quota has been exceeded" in args[0]:
        print("🎯 发现英文配额错误！")
        print("🔍 错误信息:", args[0])
        print("🔍 调用堆栈:")
        traceback.print_stack()
        print("=" * 80)
    
    # 调用原始的__init__
    return original_exception_init(self, *args, **kwargs)

# 替换Exception的__init__方法
Exception.__init__ = traced_exception_init

print("✅ 错误追踪器已启动")
print("📡 现在所有包含 'The quota has been exceeded' 的异常都会被追踪")

if __name__ == "__main__":
    # 模拟触发配额错误
    try:
        from backend.services.quota_manager import get_quota_manager
        quota_manager = get_quota_manager()
        
        # 强制触发配额错误
        print("🧪 手动触发配额错误...")
        result = quota_manager.with_quota_check("test_service", lambda: "test")
        print("❌ 没有触发错误")
        
    except Exception as e:
        print(f"✅ 捕获到错误: {e}")
        print(f"✅ 错误类型: {type(e)}")