#!/bin/bash

echo "🧪 AI股票聊天助手 - 测试系统状态检查"
echo "======================================="

# 检查后端测试
echo ""
echo "🐍 后端测试状态："
echo "---------------"
if command -v python3 &> /dev/null && python3 -c "import pytest" 2>/dev/null; then
    echo "✅ Python + pytest: 已安装"
    echo "📊 运行后端单元测试..."
    cd tests && python3 -m pytest backend/unit/ -q --tb=no
    test_result=$?
    if [ $test_result -eq 0 ]; then
        echo "✅ 后端单元测试: 全部通过"
    else
        echo "⚠️ 后端单元测试: 部分失败"
    fi
    cd ..
else
    echo "❌ Python + pytest: 未安装"
fi

# 检查前端测试
echo ""
echo "⚛️ 前端测试状态："
echo "---------------"
if [ -f "frontend/node_modules/.bin/vitest" ]; then
    echo "✅ Vitest: 已安装"
    echo "📊 前端测试配置: 已就绪"
else
    echo "❌ Vitest: 未安装"
    echo "💡 运行以安装: npm run install:test-deps"
fi

# 检查测试文件数量
echo ""
echo "📁 测试文件统计："
echo "---------------"
backend_tests=$(find tests/backend -name "*.py" -type f | grep -v __pycache__ | wc -l | tr -d ' ')
frontend_tests=$(find tests/frontend -name "*.test.*" -type f 2>/dev/null | wc -l | tr -d ' ')
integration_tests=$(find tests/integration -name "*.py" -type f 2>/dev/null | wc -l | tr -d ' ')
e2e_tests=$(find tests/e2e -name "*.py" -type f 2>/dev/null | wc -l | tr -d ' ')

echo "📄 后端测试文件: $backend_tests 个"
echo "📄 前端测试文件: $frontend_tests 个" 
echo "📄 集成测试文件: $integration_tests 个"
echo "📄 E2E测试文件: $e2e_tests 个"

total_tests=$((backend_tests + frontend_tests + integration_tests + e2e_tests))
echo "📊 测试文件总数: $total_tests 个"

# 可用命令
echo ""
echo "🚀 可用测试命令："
echo "---------------"
echo "npm run test:backend:unit     # 后端单元测试 ✅"
echo "npm run test:frontend         # 前端测试 (需安装依赖)"
echo "npm run test:integration      # 集成测试 (需配置)"
echo "npm run test:e2e              # E2E测试 (需配置)"
echo "npm run test                  # 完整测试套件"

echo ""
echo "💡 安装所有测试依赖: npm run install:test-deps"
echo ""