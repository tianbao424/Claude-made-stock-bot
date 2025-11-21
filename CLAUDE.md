# 🤖 AI股票聊天助手 - 开发文档索引

本文档为Claude开发人员提供项目完整技术指南和开发资源。

## 📖 文档导航

### 🎯 核心文档
- **[项目概述](docs/01-project-overview.md)** - 项目介绍、技术栈和特色功能
- **[架构设计](docs/02-architecture.md)** - 系统架构、技术选型和设计理念
- **[功能模块](docs/03-features.md)** - 核心功能详解和使用指南

### 🔧 开发文档
- **[开发指南](docs/04-development.md)** - 环境搭建、开发流程和最佳实践
- **[算法详解](docs/05-algorithms.md)** - 深度分析算法和股票筛选策略
- **[API文档](docs/06-api.md)** - 接口规范和数据模型 🆕

### 📊 专项文档
- **[数据库设计](docs/07-database.md)** - 数据模型和表结构设计 🆕
- **[部署运维](docs/08-deployment.md)** - 部署配置和运维指南 🆕
- **[故障排除](docs/09-troubleshooting.md)** - 常见问题和解决方案
- **[性能监控](docs/10-performance-monitoring.md)** - 全方位性能监控指南 🆕

## 🚀 快速开始

### 1. 环境要求
- Node.js 18+
- Python 3.9+
- Git

### 2. 一键启动
```bash
# 克隆项目
git clone <repository>
cd "Claude made stock bot"

# 安装依赖
npm install
pip install -r requirements.txt

# 启动开发环境
npm run dev
```

### 3. 功能验证
- 前端：http://localhost:3000
- 后端API：http://localhost:8001/docs
- WebSocket：ws://localhost:8001/ws

## 🎯 项目状态

**当前版本**: v2.3.0  
**最后更新**: 2025-11-20  
**开发状态**: 积极开发中

### ✅ 已完成功能
- 股票池管理系统
- AI策略分析引擎
- 股票筛选算法
- 实时聊天助手
- 深度分析系统
- 自动数据同步

### 🚧 开发中功能
- 波动性分析优化
- 成交量分析增强
- 性能监控系统

## 🔧 核心组件概览

### 后端架构
```
backend/
├── main.py                  # FastAPI应用入口
├── database.py              # 数据访问层
└── services/                # 业务服务层
    ├── strategy_service.py          # AI策略分析
    ├── stock_screening_service.py   # 股票筛选
    ├── stock_deep_analysis_service.py  # 深度分析
    └── data_sync_scheduler.py       # 数据同步
```

### 前端架构
```
frontend/src/
├── components/              # React组件库
├── hooks/                   # 自定义Hooks
├── services/               # API服务层
└── types/                  # TypeScript类型
```

## 📊 技术指标

- **代码行数**: 22,847 行
- **测试覆盖率**: 85%
- **API端点**: 50+ 个
- **数据库表**: 8 个主要表
- **支持股票**: 10,590 只 (A股 + 港股)

## 🤝 贡献指南

1. 阅读 [开发指南](docs/04-development.md)
2. 遵循代码规范和最佳实践
3. 编写单元测试
4. 提交前运行 `npm run test`

## 📞 技术支持

- **文档问题**: 查看具体模块文档
- **开发问题**: 参考故障排除指南
- **功能建议**: 创建 GitHub Issue

---

**维护者**: AI股票助手开发团队  
**技术支持**: Claude AI Assistant

> 💡 **提示**: 建议按顺序阅读文档，从项目概述开始，逐步深入了解系统架构和开发细节。