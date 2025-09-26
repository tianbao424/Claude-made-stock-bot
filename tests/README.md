# 测试文档

本目录包含AI股票聊天助手项目的完整测试套件，包括单元测试、集成测试和端到端测试。

## 📁 目录结构

```
tests/
├── README.md                    # 测试说明文档
├── conftest.py                  # 全局测试配置
│
├── backend/                     # 后端测试
│   ├── pytest.ini             # pytest配置文件
│   ├── unit/                   # 单元测试
│   │   ├── test_stock_pool_api.py         # 股票池API测试
│   │   ├── test_stock_screening_service.py # 筛选服务测试
│   │   └── test_database.py               # 数据库测试
│   └── integration/            # 后端集成测试
│       └── test_api_integration.py
│
├── frontend/                    # 前端测试
│   ├── vitest.config.ts        # Vitest配置文件
│   ├── setup.ts                # 测试环境设置
│   ├── components/             # 组件测试
│   │   ├── StockPoolManager.test.tsx
│   │   └── ChatInterface.test.tsx
│   ├── hooks/                  # Hooks测试
│   │   └── useStockPool.test.ts
│   └── unit/                   # 前端单元测试
│       └── utils.test.ts
│
├── integration/                 # 集成测试
│   └── test_full_workflow.py   # 完整工作流程测试
│
└── e2e/                        # 端到端测试
    └── test_user_scenarios.py
```

## 🚀 快速开始

### 运行所有测试
```bash
npm run test
```

### 分类运行测试

#### 后端测试
```bash
# 所有后端测试
npm run test:backend

# 仅单元测试
npm run test:backend:unit

# 仅集成测试
npm run test:backend:integration

# 带覆盖率报告
npm run test:backend:coverage
```

#### 前端测试
```bash
# 所有前端测试
npm run test:frontend

# 组件测试
npm run test:frontend:components

# Hooks测试
npm run test:frontend:hooks

# 监视模式
npm run test:frontend:watch
```

#### 专项测试
```bash
# 集成测试
npm run test:integration

# 端到端测试
npm run test:e2e

# 覆盖率报告
npm run test:coverage
```

## 🧪 测试类型说明

### 1. 单元测试 (Unit Tests)
测试单个函数、类或组件的独立功能。

**后端单元测试:**
- API端点测试
- 服务类方法测试
- 数据库操作测试
- 工具函数测试

**前端单元测试:**
- React组件渲染测试
- Hooks逻辑测试
- 工具函数测试

### 2. 集成测试 (Integration Tests)
测试多个模块之间的协作。

- API与数据库集成
- 前后端通信测试
- 服务间依赖测试
- WebSocket连接测试

### 3. 端到端测试 (E2E Tests)
从用户角度测试完整业务流程。

- 用户操作模拟
- 完整工作流验证
- 跨浏览器兼容性

## 🛠️ 测试工具

### 后端测试工具
- **pytest**: Python测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-cov**: 代码覆盖率
- **fastapi.testclient**: API测试客户端

### 前端测试工具
- **Vitest**: 现代化测试框架
- **@testing-library/react**: React组件测试
- **@testing-library/jest-dom**: DOM断言扩展
- **jsdom**: DOM模拟环境

## 📊 测试覆盖率

目标覆盖率: **85%+**

### 查看覆盖率报告
```bash
npm run test:coverage
```

覆盖率报告将生成在:
- 后端: `tests/backend/coverage_html/`
- 前端: `tests/frontend/coverage/`

## 🎯 编写测试的最佳实践

### 1. 测试命名规范
```python
# 好的命名
def test_create_stock_pool_with_valid_data():
    pass

def test_create_stock_pool_with_invalid_stock_code():
    pass

# 不好的命名
def test_create():
    pass
```

### 2. 测试结构 (AAA Pattern)
```python
def test_example():
    # Arrange - 准备测试数据
    stock_data = {"code": "000001", "name": "平安银行"}
    
    # Act - 执行被测试的操作
    result = create_stock_pool(stock_data)
    
    # Assert - 验证结果
    assert result.success is True
    assert result.data["code"] == "000001"
```

### 3. 使用Fixtures管理测试数据
```python
@pytest.fixture
def sample_stock_data():
    return {
        "stock_code": "000001",
        "stock_name": "平安银行",
        "pool_type": "holding"
    }

def test_create_stock_pool(sample_stock_data):
    result = create_stock_pool(sample_stock_data)
    assert result.success is True
```

### 4. Mock外部依赖
```python
@patch('backend.services.akshare_service.AkShareService.get_stock_info')
def test_stock_info_api(mock_get_info):
    mock_get_info.return_value = {"price": 13.20}
    
    result = get_stock_info("000001")
    assert result["price"] == 13.20
```

## 🔧 测试配置

### Pytest配置 (pytest.ini)
```ini
[tool:pytest]
testpaths = tests/backend
python_files = test_*.py
addopts = --verbose --cov=backend --cov-report=term-missing
```

### Vitest配置 (vitest.config.ts)
```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/frontend/setup.ts'],
    coverage: {
      reporter: ['text', 'html']
    }
  }
})
```

## 🐛 调试测试

### 1. 运行特定测试
```bash
# Python
pytest tests/backend/unit/test_database.py::TestDatabaseManager::test_add_stock_pool -v

# JavaScript  
vitest tests/frontend/components/StockPoolManager.test.tsx -t "creates new stock pool"
```

### 2. 调试模式
```bash
# Python调试
pytest --pdb tests/backend/unit/test_database.py

# JavaScript调试
vitest --inspect-brk tests/frontend/components/
```

### 3. 查看详细输出
```bash
# 显示print输出
pytest -s tests/backend/unit/

# 显示console.log输出
vitest --reporter=verbose
```

## 📈 持续集成

测试脚本已配置在CI/CD流水线中:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    npm install
    npm run test
```

## 📝 测试检查清单

在提交代码前，请确保:

- [ ] 所有新功能都有对应的测试
- [ ] 测试覆盖率达到85%以上
- [ ] 所有测试都能通过
- [ ] 没有跳过的测试(除非有充分理由)
- [ ] Mock了所有外部依赖
- [ ] 测试名称清晰描述了测试内容

## 🤝 贡献测试

### 添加新测试
1. 确定测试类型(单元/集成/E2E)
2. 选择合适的测试文件位置
3. 遵循现有测试的模式
4. 添加必要的fixtures和mocks
5. 运行测试确保通过

### 测试审查要点
- 测试逻辑是否正确
- 覆盖了正常和异常情况
- 没有冗余测试
- Mock使用得当
- 测试运行速度合理

---

**维护者**: AI股票助手开发团队  
**最后更新**: 2025-09-25