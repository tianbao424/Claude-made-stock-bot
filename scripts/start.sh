#!/bin/bash

# 启动脚本 - 股票聊天机器人
# Usage: ./scripts/start.sh

echo "🚀 启动股票聊天机器人..."

# 检查环境文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件，请复制 config/.env.template 并配置"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 安装依赖
echo "📦 检查依赖..."
pip3 install -r backend/requirements.txt

# 启动服务
echo "🌟 启动服务中..."
python3 backend/main.py