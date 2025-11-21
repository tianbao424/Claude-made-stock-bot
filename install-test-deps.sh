#!/bin/bash

echo "🔧 安装测试依赖..."

# 安装前端测试依赖
echo "📦 安装前端测试依赖..."
cd frontend
npm install --no-audit --no-fund \
    vitest@^2.1.6 \
    @testing-library/react@^16.1.0 \
    @testing-library/jest-dom@^6.6.5 \
    @testing-library/user-event@^14.5.2 \
    jsdom@^26.0.0

if [ $? -eq 0 ]; then
    echo "✅ 前端测试依赖安装完成"
else
    echo "❌ 前端测试依赖安装失败"
    exit 1
fi

cd ..

# 安装Python测试依赖
echo "🐍 安装Python测试依赖..."
pip3 install --quiet \
    pytest>=7.0.0 \
    pytest-asyncio>=0.21.0 \
    pytest-cov>=4.0.0 \
    httpx>=0.24.0

if [ $? -eq 0 ]; then
    echo "✅ Python测试依赖安装完成"
else
    echo "❌ Python测试依赖安装失败"
    exit 1
fi

echo "🎉 所有测试依赖安装完成！"
echo ""
echo "现在可以运行以下测试命令："
echo "  npm run test:backend:unit     # 后端单元测试"
echo "  npm run test:frontend         # 前端测试"  
echo "  npm run test                  # 所有测试"