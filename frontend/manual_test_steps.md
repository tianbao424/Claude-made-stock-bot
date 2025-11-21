# 高级筛选功能测试步骤

## 前端运行状态
- 前端应该运行在: http://localhost:3001/ (由于3000端口被占用)
- 后端应该运行在: http://localhost:8001/

## 手动测试步骤

1. **打开前端**
   ```
   在浏览器中访问: http://localhost:3001/
   ```

2. **找到高级筛选标签**
   - 在左侧导航栏中查找 "高级筛选" 按钮
   - 图标应该是一个目标/靶心图标 (Target)

3. **点击高级筛选**
   - 点击 "高级筛选" 标签
   - 页面应该切换到高级筛选界面

4. **检查页面加载**
   - 应该看到 "高级股票筛选" 标题
   - 左侧应该有 "基础筛选条件" 面板
   - 右侧应该是空的结果区域
   - 顶部应该有进度指示器

5. **测试基础筛选**
   - 调整筛选条件 (天数、涨幅、成交量等)
   - 点击 "执行基础筛选" 按钮
   - 应该显示筛选结果

6. **如果出现白屏，检查浏览器开发者工具**
   - 按 F12 打开开发者工具
   - 查看 Console 标签页的错误信息
   - 查看 Network 标签页的网络请求

## 常见问题排查

### 问题1: 白屏
- 原因: React组件渲染错误
- 解决: 检查Console错误，修复组件代码

### 问题2: 标签页不存在
- 原因: App.tsx中的路由配置问题
- 解决: 检查tabs数组中是否包含advanced-screening

### 问题3: 组件加载错误
- 原因: 组件导入路径错误或依赖缺失
- 解决: 检查import语句和组件文件路径

## 当前实现状态
✅ AdvancedStockScreening 主组件
✅ BasicFilterPanel 基础筛选面板  
✅ BasicResultsTable 结果表格
✅ StrategySelector 策略选择器
✅ ResultsComparison 结果对比
✅ 后端API端点 (/api/advanced-screening/basic, /api/advanced-screening/strategy)
✅ 集成到App.tsx导航中

## 下一步
如果测试发现问题，需要：
1. 修复JavaScript/React错误
2. 完善错误处理
3. 优化用户体验