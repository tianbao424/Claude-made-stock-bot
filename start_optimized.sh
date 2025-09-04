#!/bin/bash

echo "🚀 启动优化版AI股票聊天助手..."
echo "📈 包含实时股票行情显示功能"
echo ""

# 检查是否在正确目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 启动后端服务
echo "🔧 启动后端服务 (http://localhost:8001)..."
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 检查后端健康状态
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ 后端服务启动成功"
else
    echo "❌ 后端服务启动失败"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 启动前端服务
echo "🎨 启动前端服务 (http://localhost:5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🎉 服务启动完成！"
echo "┌─────────────────────────────────────────┐"
echo "│  🌐 前端地址: http://localhost:5173     │"
echo "│  🔗 后端地址: http://localhost:8001     │"
echo "│  💊 健康检查: http://localhost:8001/health │"
echo "└─────────────────────────────────────────┘"
echo ""
echo "📊 功能特色:"
echo "  ✅ 股票信息搜索 (支持4600+股票)"
echo "  ✅ 实时行情展示 (AkShare数据)"
echo "  ✅ 专业界面设计 (优化版详情页)"
echo "  ✅ 自动数据刷新 (30秒间隔)"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 创建停止函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "uvicorn main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    echo "✅ 服务已停止"
    exit 0
}

# 捕获Ctrl+C信号
trap cleanup SIGINT

# 等待用户终止
wait