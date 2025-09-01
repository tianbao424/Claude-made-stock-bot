# 配置说明文档

## 📁 配置文件结构

```
config/
├── settings.py     # 配置管理模块
└── README.md      # 本文档
```

## ⚙️ 配置管理

### settings.py
基于Pydantic的配置管理模块，提供：
- 类型安全的配置验证
- 环境变量自动读取
- 配置项默认值管理
- 多种环境变量名称支持

### 使用方式

```python
from config.settings import settings

# 获取配置
api_key = settings.api_key
server_port = settings.server_port

# 验证配置
from config.settings import validate_config
if validate_config():
    print("配置有效")
```

### 配置验证

```bash
# 验证当前配置
python3 config/settings.py
```

## 🔧 环境变量

### 必需配置
- `API_KEY`: AI服务API密钥
- `AKSHARE_MCP_PATH`: AkShare MCP服务器Python路径

### 可选配置
- `BASE_URL`: API服务地址 (默认: DashScope)
- `MODEL`: AI模型名称 (默认: qwen-coder-plus)
- `SERVER_HOST`: Web服务主机 (默认: 0.0.0.0)
- `SERVER_PORT`: Web服务端口 (默认: 8001)
- `DATABASE_PATH`: 数据库路径 (默认: backend/stock_pool.db)
- `DEBUG`: 调试模式 (默认: False)
- `LOG_LEVEL`: 日志级别 (默认: INFO)

## 🔄 配置更新流程

1. 修改 `.env` 文件中的配置值
2. 运行 `python3 config/settings.py` 验证配置
3. 重启应用程序使配置生效