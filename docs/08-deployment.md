# 🚀 部署运维指南

## 🎯 部署概述

本文档详细介绍了AI股票聊天助手在不同环境下的部署方案，包括开发环境、测试环境和生产环境的配置指南。

## 🔧 环境配置

### 系统要求

#### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM  
- **存储**: 20GB可用空间
- **网络**: 稳定的互联网连接

#### 推荐配置
- **CPU**: 4核心以上
- **内存**: 8GB RAM以上
- **存储**: 50GB SSD
- **网络**: 100Mbps带宽

#### 软件依赖
- **Node.js**: 18.0+ (LTS版本)
- **Python**: 3.9+
- **Git**: 最新版本
- **PM2**: 进程管理器(生产环境)
- **Nginx**: 反向代理(可选)

### 环境变量配置

创建 `.env` 配置文件：

```bash
# 应用配置
NODE_ENV=production
PORT=8001
HOST=0.0.0.0

# 数据库配置
DATABASE_URL=./stock_pool.db
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_INTERVAL=24

# API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=qwen-coder-plus

# AkShare配置
AKSHARE_CACHE_TTL=300
AKSHARE_REQUEST_TIMEOUT=30

# 安全配置
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
JWT_SECRET=your_jwt_secret
API_RATE_LIMIT=100

# 日志配置
LOG_LEVEL=info
LOG_FILE=logs/app.log
LOG_MAX_SIZE=10mb
LOG_MAX_FILES=5

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
```

## 🐳 Docker部署

### Dockerfile
```dockerfile
# 多阶段构建Dockerfile
FROM node:18-alpine AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package*.json ./
RUN npm ci --only=production --silent

# 复制前端源码并构建
COPY frontend/ .
RUN npm run build

FROM python:3.9-slim AS backend

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY backend/ ./backend/

# 复制前端构建结果
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# 创建非root用户
RUN useradd -m -u 1000 stockbot && \
    chown -R stockbot:stockbot /app

USER stockbot

# 创建必要目录
RUN mkdir -p logs data

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8001:8001"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=/app/data/stock_pool.db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    depends_on:
      - redis
    networks:
      - stock-bot-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./logs:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - stock-bot-network

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - stock-bot-network

volumes:
  redis_data:

networks:
  stock-bot-network:
    driver: bridge
```

### 构建和启动
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

## 🌐 Nginx配置

### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server app:8001;
    }

    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;

    server {
        listen 80;
        server_name your-domain.com;
        
        # HTTP重定向到HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL证书配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # 前端静态文件
        location / {
            root /app/frontend/dist;
            try_files $uri $uri/ /index.html;
            
            # 静态资源缓存
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # API代理
        location /api {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 超时配置
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # WebSocket代理
        location /ws {
            limit_req zone=ws burst=10 nodelay;
            
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket特定配置
            proxy_read_timeout 86400;
            proxy_send_timeout 86400;
        }

        # 健康检查
        location /health {
            proxy_pass http://backend;
            access_log off;
        }

        # 日志配置
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
    }
}
```

## ⚡ PM2进程管理

### ecosystem.config.js
```javascript
module.exports = {
  apps: [{
    name: 'stock-bot-api',
    script: 'backend/main.py',
    interpreter: 'python3',
    args: '-m uvicorn main:app --host 0.0.0.0 --port 8001',
    cwd: '/app',
    instances: 'max',
    exec_mode: 'cluster',
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 8001
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s'
  }],

  deploy: {
    production: {
      user: 'deploy',
      host: 'your-server.com',
      ref: 'origin/main',
      repo: 'git@github.com:your-repo/stock-bot.git',
      path: '/var/www/stock-bot',
      'post-deploy': 'npm install && npm run build && pm2 reload ecosystem.config.js --env production'
    }
  }
};
```

### PM2命令
```bash
# 启动应用
pm2 start ecosystem.config.js --env production

# 查看状态
pm2 status

# 查看日志
pm2 logs stock-bot-api

# 重启应用
pm2 restart stock-bot-api

# 停止应用
pm2 stop stock-bot-api

# 删除应用
pm2 delete stock-bot-api

# 保存PM2配置
pm2 save

# 设置开机自启
pm2 startup
```

## 📊 监控和日志

### 应用监控配置
```python
# monitoring.py
import psutil
import logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Prometheus指标
REQUEST_COUNT = Counter('http_requests_total', 'HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_CONNECTIONS = Gauge('websocket_connections_active', 'Active WebSocket connections')
SYSTEM_CPU = Gauge('system_cpu_percent', 'System CPU usage')
SYSTEM_MEMORY = Gauge('system_memory_percent', 'System memory usage')

class MonitoringService:
    def __init__(self):
        self.setup_logging()
        if os.getenv('ENABLE_METRICS', 'false').lower() == 'true':
            self.start_metrics_server()
    
    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.getenv('LOG_FILE', 'logs/app.log')),
                logging.StreamHandler()
            ]
        )
    
    def start_metrics_server(self):
        """启动Prometheus指标服务器"""
        metrics_port = int(os.getenv('METRICS_PORT', '9090'))
        start_http_server(metrics_port)
        logging.info(f"Metrics server started on port {metrics_port}")
    
    def collect_system_metrics(self):
        """收集系统指标"""
        SYSTEM_CPU.set(psutil.cpu_percent())
        SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
```

### 日志轮转配置
```bash
# /etc/logrotate.d/stock-bot
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 stockbot stockbot
    postrotate
        pm2 reload stock-bot-api
    endscript
}
```

## 🔒 安全配置

### SSL证书配置
```bash
# 使用Let's Encrypt免费SSL证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 防火墙配置
```bash
# UFW防火墙配置
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow 22

# 允许HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 查看状态
sudo ufw status
```

### Fail2Ban配置
```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
```

## 📈 性能优化

### 数据库优化
```bash
#!/bin/bash
# db_maintenance.sh - 数据库维护脚本

DB_PATH="/app/data/stock_pool.db"

# 数据库优化
sqlite3 $DB_PATH "PRAGMA optimize;"
sqlite3 $DB_PATH "VACUUM;"
sqlite3 $DB_PATH "REINDEX;"

# 数据清理
sqlite3 $DB_PATH "DELETE FROM stock_screening WHERE screening_date < date('now', '-90 days');"
sqlite3 $DB_PATH "DELETE FROM daily_stock_changes WHERE trade_date < date('now', '-180 days');"

echo "数据库维护完成"
```

### 缓存配置
```python
# cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def cache_result(key_prefix: str, ttl: int = 300):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            
            return result
        return wrapper
    return decorator
```

## 🔄 备份和恢复

### 自动备份脚本
```bash
#!/bin/bash
# backup.sh - 自动备份脚本

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
sqlite3 /app/data/stock_pool.db ".backup ${BACKUP_DIR}/db_${TIMESTAMP}.db"

# 配置文件备份
cp /app/.env "${BACKUP_DIR}/env_${TIMESTAMP}"

# 日志备份
tar -czf "${BACKUP_DIR}/logs_${TIMESTAMP}.tar.gz" /app/logs/

# 上传到云存储（可选）
# aws s3 cp $BACKUP_DIR s3://your-backup-bucket/stock-bot/ --recursive

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "备份完成: $TIMESTAMP"
```

### 定时任务配置
```bash
# 编辑crontab
crontab -e

# 添加以下任务
# 每天凌晨2点备份
0 2 * * * /app/scripts/backup.sh

# 每天凌晨3点数据库维护
0 3 * * * /app/scripts/db_maintenance.sh

# 每周日凌晨清理日志
0 4 * * 0 find /app/logs -name "*.log" -mtime +7 -delete
```

## 🚨 故障恢复

### 健康检查
```python
# health_check.py
from fastapi import APIRouter
import sqlite3
import requests

router = APIRouter()

@router.get("/health")
async def health_check():
    """应用健康检查"""
    checks = {
        "database": check_database(),
        "external_api": check_external_apis(),
        "memory": check_memory_usage(),
        "disk": check_disk_space()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return {"status": "healthy" if all_healthy else "unhealthy", "checks": checks}

def check_database():
    """检查数据库连接"""
    try:
        with sqlite3.connect("/app/data/stock_pool.db") as conn:
            conn.execute("SELECT 1")
        return True
    except:
        return False
```

### 故障切换
```bash
#!/bin/bash
# failover.sh - 故障切换脚本

# 检查主服务状态
if ! curl -f http://localhost:8001/health; then
    echo "主服务异常，启动恢复流程"
    
    # 停止异常服务
    pm2 stop stock-bot-api
    
    # 检查并修复数据库
    sqlite3 /app/data/stock_pool.db "PRAGMA integrity_check;"
    
    # 重启服务
    pm2 start stock-bot-api
    
    # 发送告警
    curl -X POST https://hooks.slack.com/your-webhook \
      -H 'Content-type: application/json' \
      --data '{"text":"Stock Bot服务已自动恢复"}'
fi
```

## 📋 部署检查清单

### 部署前检查
- [ ] 环境变量配置完成
- [ ] SSL证书配置正确
- [ ] 防火墙规则设置
- [ ] 备份策略配置
- [ ] 监控系统部署
- [ ] 日志轮转配置
- [ ] 性能测试通过

### 部署后验证
- [ ] 应用服务正常启动
- [ ] 数据库连接正常
- [ ] API接口响应正常
- [ ] WebSocket连接正常
- [ ] 静态文件访问正常
- [ ] 健康检查通过
- [ ] 监控指标正常
- [ ] 日志输出正常

---

遵循这套部署指南，可以确保AI股票聊天助手在生产环境中稳定、安全、高效地运行。定期执行维护任务和监控检查，能够及时发现和解决潜在问题。