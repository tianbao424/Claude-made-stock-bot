#!/bin/bash

# 🛑 AI股票聊天助手 - 服务停止脚本
echo "🛑 正在关闭AI股票聊天助手服务..."
echo "=================================="

# 查找并关闭相关进程
echo "📍 查找运行中的服务进程..."

# 查找npm dev进程
NPM_PIDS=$(ps aux | grep -E "npm.*dev" | grep -v grep | awk '{print $2}')
# 查找concurrently进程  
CONCURRENTLY_PIDS=$(ps aux | grep "concurrently" | grep -v grep | awk '{print $2}')
# 查找vite进程
VITE_PIDS=$(ps aux | grep "vite" | grep -v grep | awk '{print $2}')
# 查找后端Python进程
PYTHON_PIDS=$(lsof -ti:8001 2>/dev/null)

# 收集所有需要关闭的PID
ALL_PIDS="$NPM_PIDS $CONCURRENTLY_PIDS $VITE_PIDS $PYTHON_PIDS"

if [ -z "$ALL_PIDS" ]; then
    echo "✅ 没有发现运行中的服务进程"
else
    echo "🔍 发现以下进程需要关闭:"
    for pid in $ALL_PIDS; do
        if [ -n "$pid" ]; then
            PROCESS_INFO=$(ps -p $pid -o pid,comm,args --no-headers 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo "   PID $pid: $PROCESS_INFO"
            fi
        fi
    done
    
    echo ""
    echo "🛑 正在关闭服务..."
    
    # 优雅关闭进程
    for pid in $ALL_PIDS; do
        if [ -n "$pid" ]; then
            if kill -0 $pid 2>/dev/null; then
                echo "   关闭进程 $pid..."
                kill -TERM $pid 2>/dev/null
            fi
        fi
    done
    
    # 等待进程关闭
    echo "⏳ 等待进程关闭..."
    sleep 3
    
    # 检查是否还有顽固进程需要强制关闭
    for pid in $ALL_PIDS; do
        if [ -n "$pid" ]; then
            if kill -0 $pid 2>/dev/null; then
                echo "   强制关闭进程 $pid..."
                kill -KILL $pid 2>/dev/null
            fi
        fi
    done
fi

echo ""
echo "🧪 验证服务状态..."

# 检查端口是否已释放
if lsof -i:3000 >/dev/null 2>&1; then
    echo "⚠️  端口3000仍被占用"
else
    echo "✅ 端口3000已释放"
fi

if lsof -i:8001 >/dev/null 2>&1; then
    echo "⚠️  端口8001仍被占用"  
else
    echo "✅ 端口8001已释放"
fi

# 检查前端服务
if curl -s "http://localhost:3000" --connect-timeout 2 >/dev/null; then
    echo "⚠️  前端服务仍在响应"
else
    echo "✅ 前端服务已停止"
fi

# 检查后端服务
if curl -s "http://localhost:8001/health" --connect-timeout 2 >/dev/null; then
    echo "⚠️  后端服务仍在响应"
else
    echo "✅ 后端服务已停止"
fi

echo ""
echo "🎉 服务停止完成！"
echo "=================================="
echo "💡 提示: 如需重新启动服务，请运行: npm run dev"