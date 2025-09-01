"""
AI股票聊天助手 - 配置管理模块
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用程序配置类"""
    
    def __init__(self):
        # =============================================================================
        # AI服务配置 (必需)
        # =============================================================================
        self.base_url = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.api_key = os.getenv("API_KEY", "")
        self.model = os.getenv("MODEL", "qwen-coder-plus")
        
        # =============================================================================
        # 数据源配置 (必需)
        # =============================================================================
        self.akshare_mcp_path = os.getenv("AKSHARE_MCP_PATH", "")
        
        # =============================================================================
        # Web服务配置 (可选)
        # =============================================================================
        self.server_host = os.getenv("SERVER_HOST", "0.0.0.0")
        self.server_port = int(os.getenv("SERVER_PORT", "8001"))
        
        # =============================================================================
        # 数据库配置 (可选)
        # =============================================================================
        self.database_path = os.getenv("DATABASE_PATH", "backend/stock_pool.db")
        
        # =============================================================================
        # 应用配置 (可选)
        # =============================================================================
        self.debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # =============================================================================
        # WebSocket配置 (可选)
        # =============================================================================
        self.ws_heartbeat_interval = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
        self.ws_timeout = int(os.getenv("WS_TIMEOUT", "300"))


# 全局配置实例
settings = Settings()


def validate_config() -> bool:
    """
    验证配置是否完整
    
    Returns:
        bool: 配置是否有效
    """
    required_fields = [
        ("API_KEY", settings.api_key),
        ("AKSHARE_MCP_PATH", settings.akshare_mcp_path)
    ]
    
    missing_fields = []
    invalid_fields = []
    
    for field_name, field_value in required_fields:
        if not field_value or field_value.strip() == "":
            missing_fields.append(field_name)
        elif field_name == "AKSHARE_MCP_PATH" and not os.path.exists(field_value.split()[0]):
            invalid_fields.append(f"{field_name} (路径不存在)")
    
    if missing_fields:
        print(f"❌ 缺少必要的配置项: {', '.join(missing_fields)}")
        print("请在 .env 文件中设置这些配置项")
        return False
    
    if invalid_fields:
        print(f"⚠️ 配置项无效: {', '.join(invalid_fields)}")
        print("请检查路径是否正确")
        return False
    
    return True


def print_config_summary():
    """打印配置摘要信息"""
    print("📋 当前配置:")
    print(f"   🤖 AI模型: {settings.model}")
    print(f"   🌐 服务地址: http://{settings.server_host}:{settings.server_port}")
    print(f"   💾 数据库: {settings.database_path}")
    print(f"   🐛 调试模式: {'开启' if settings.debug else '关闭'}")
    print(f"   📝 日志级别: {settings.log_level}")
    print(f"   🔗 MCP路径: {settings.akshare_mcp_path[:50]}...")


def get_required_env_vars():
    """获取必需的环境变量列表"""
    return [
        ("API_KEY", "阿里云DashScope API密钥"),
        ("AKSHARE_MCP_PATH", "AkShare MCP服务器Python路径")
    ]


def get_optional_env_vars():
    """获取可选的环境变量列表"""
    return [
        ("BASE_URL", f"API服务地址 (默认: {settings.base_url})"),
        ("MODEL", f"AI模型名称 (默认: {settings.model})"),
        ("SERVER_HOST", f"服务器主机 (默认: {settings.server_host})"),
        ("SERVER_PORT", f"服务器端口 (默认: {settings.server_port})"),
        ("DATABASE_PATH", f"数据库路径 (默认: {settings.database_path})"),
        ("DEBUG", f"调试模式 (默认: {settings.debug})"),
        ("LOG_LEVEL", f"日志级别 (默认: {settings.log_level})")
    ]


if __name__ == "__main__":
    # 配置验证脚本
    print("🔧 AI股票聊天助手 - 配置验证")
    print("=" * 60)
    print()
    
    # 检查.env文件是否存在
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"⚠️ 环境配置文件 {env_file} 不存在")
        print("请复制 .env.template 为 .env 并填入配置信息")
        print()
        
        # 显示需要配置的项目
        print("📋 必需配置项:")
        for var_name, description in get_required_env_vars():
            print(f"   • {var_name}: {description}")
        
        print()
        print("📋 可选配置项:")
        for var_name, description in get_optional_env_vars():
            print(f"   • {var_name}: {description}")
        
        exit(1)
    
    print(f"✅ 找到环境配置文件: {env_file}")
    print()
    
    # 验证配置
    if validate_config():
        print("✅ 配置验证通过")
        print()
        print_config_summary()
        print()
        print("🚀 可以运行以下命令启动应用:")
        print("   ./scripts/start.sh")
        print("   或者")
        print("   python3 backend/main.py")
    else:
        print()
        print("❌ 配置验证失败")
        print("请编辑 .env 文件并填入正确的配置信息")
        
        print()
        print("📋 必需配置项:")
        for var_name, description in get_required_env_vars():
            current_value = os.getenv(var_name, "")
            status = "✅" if current_value else "❌"
            print(f"   {status} {var_name}: {description}")
        
        exit(1)