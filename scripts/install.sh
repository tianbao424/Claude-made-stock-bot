#!/bin/bash

# 安装脚本 - 股票聊天机器人
# Usage: ./scripts/install.sh

echo "📦 安装股票聊天机器人..."

# 检查Python版本
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python版本检查通过: $python_version"
else
    echo "❌ Python版本过低: $python_version, 需要 >= $required_version"
    exit 1
fi

# 安装后端依赖
echo "📚 安装后端依赖..."
pip3 install -r backend/requirements.txt

# 安装原始stock_bot依赖
echo "📚 安装stock_bot依赖..."
pip3 install -r requirements.txt

# 复制环境配置模板
if [ ! -f ".env" ]; then
    echo "📋 创建环境配置文件..."
    cp config/.env.template .env
    echo "⚠️  请编辑 .env 文件，填入您的API密钥和MCP路径"
else
    echo "✅ 环境配置文件已存在"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，配置API密钥"
echo "2. 运行: ./scripts/start.sh"
echo ""