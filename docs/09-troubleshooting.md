# 🔧 故障排除指南

## 🎯 数据收集相关问题

### 问题 1: 数据收集不完整
**症状**: 数据库中某日只有几百条数据，而不是正常的5000+条

**可能原因**:
- API调用限制或网络问题
- 数据源接口变更
- 系统负载过高导致超时

**排查步骤**:
```bash
# 1. 检查数据库中的数据量
sqlite3 backend/stock_pool.db "
SELECT trade_date, COUNT(*) as count 
FROM daily_stock_changes 
WHERE trade_date >= date('now', '-7 days')
GROUP BY trade_date 
ORDER BY trade_date DESC;
"

# 2. 检查后端日志
tail -f backend.log | grep "数据收集\|collect_daily_data"

# 3. 手动重新收集数据
# 访问 http://localhost:3000 -> 股票甄选 -> 点击"初始化数据"
```

**解决方案**:
1. **临时解决**: 手动点击"初始化数据"按钮
2. **长期解决**: 
   - 调整批处理大小: 修改 `batch_size` 从50降至20
   - 增加重试机制
   - 使用多个数据源备份

### 问题 2: 自动数据收集未执行
**症状**: 每天18:00后没有新的筛选结果

**排查步骤**:
```bash
# 1. 检查调度器是否运行
curl http://localhost:8001/api/scheduler/status

# 2. 检查系统时间和时区
date
timedatectl status  # Linux
```

**解决方案**:
```python
# 检查调度器配置
# 文件: backend/services/data_sync_scheduler.py
schedule.every().day.at("17:00").do(
    self._conditional_daily_data_collection
).tag('daily_data_collection')
```

### 问题 3: 数据日期不一致
**症状**: 界面显示的数据日期和实际数据日期不匹配

**原因**: 筛选使用的是执行日期而非数据日期

**解决方案**: 
系统已在v2.2版本中修复，确保使用实际数据日期。如果仍有问题：
```bash
# 清除旧的筛选结果
sqlite3 backend/stock_pool.db "DELETE FROM stock_screening WHERE screening_date > date('now', '-1 day');"

# 重新执行筛选
curl -X POST http://localhost:8001/api/screening/manual-trigger
```

## 🔍 股票筛选相关问题

### 问题 4: 筛选结果为空
**症状**: 筛选完成但没有找到符合条件的股票

**可能原因**:
- 筛选条件过于严格
- 市场行情不佳，没有强势股票
- 数据不完整

**排查步骤**:
```bash
# 1. 检查数据完整性
sqlite3 backend/stock_pool.db "
SELECT COUNT(*) 
FROM daily_stock_changes 
WHERE trade_date = date('now') 
AND change_percent > 7;
"

# 2. 降低筛选条件测试
# 前端: 连续天数改为1天，涨幅改为5%
```

**解决方案**:
1. 适当降低筛选条件
2. 使用"自定义筛选"测试不同参数
3. 检查数据收集是否正常

### 问题 5: 深度分析失败
**症状**: 点击"深度分析"按钮无响应或报错

**可能原因**:
- MCP连接问题
- AI模型服务不可用
- 数据不足

**排查步骤**:
```bash
# 1. 检查MCP连接
curl http://localhost:8001/api/chat/health

# 2. 检查AI服务状态
# 查看后端日志中的MCP相关错误
```

## 🗄️ 数据库相关问题

### 问题 6: 数据库损坏
**症状**: 应用启动失败，数据库相关错误

**解决方案**:
```bash
# 1. 备份现有数据库
cp backend/stock_pool.db backend/stock_pool.db.backup

# 2. 检查数据库完整性
sqlite3 backend/stock_pool.db "PRAGMA integrity_check;"

# 3. 如果数据库损坏，重新初始化
rm backend/stock_pool.db
# 重启应用，会自动创建新数据库
```

### 问题 7: 数据库过大
**症状**: 数据库文件超过100MB，系统变慢

**解决方案**:
```bash
# 1. 清理旧数据（保留最近30天）
sqlite3 backend/stock_pool.db "
DELETE FROM daily_stock_changes 
WHERE trade_date < date('now', '-30 days');

DELETE FROM stock_screening 
WHERE screening_date < date('now', '-30 days');

VACUUM;
"

# 2. 检查数据库大小
du -h backend/stock_pool.db
```

## 🌐 网络和API问题

### 问题 8: API限制和超时
**症状**: 大量"获取股票历史数据失败"的日志

**解决方案**:
```python
# 调整API调用参数
# 文件: backend/services/stock_screening_service.py

# 1. 减少并发数量
batch_size = 20  # 从50降至20

# 2. 增加延迟
await asyncio.sleep(0.2)  # 从0.1秒增至0.2秒

# 3. 增加超时时间
timeout=10.0  # 从5秒增至10秒
```

### 问题 9: 网络连接问题
**症状**: 间歇性的网络错误

**排查步骤**:
```bash
# 1. 测试网络连接
ping akshare.com
curl -I "https://quote.eastmoney.com"

# 2. 检查DNS解析
nslookup akshare.com
```

## 🔄 系统运行问题

### 问题 10: 内存使用过高
**症状**: 系统运行一段时间后内存占用很高

**解决方案**:
```python
# 1. 启用垃圾回收
import gc
gc.collect()  # 在数据收集后调用

# 2. 限制数据批次大小
batch_size = 20  # 减少批次大小
```

### 问题 11: 前端界面异常
**症状**: 前端显示错误或数据不更新

**解决方案**:
```bash
# 1. 清除浏览器缓存
# Chrome: Ctrl+Shift+R (硬刷新)

# 2. 检查后端连接
curl http://localhost:8001/api/health

# 3. 重启前端服务
cd frontend
npm run dev
```

## 📋 日常维护检查清单

### 每日检查
- [ ] 检查数据收集是否正常（每日数据量应>4000条）
- [ ] 检查筛选结果是否更新
- [ ] 查看系统日志是否有异常

### 每周检查  
- [ ] 检查数据库大小，必要时清理旧数据
- [ ] 检查系统性能，重启服务释放内存
- [ ] 备份重要配置和数据

### 每月检查
- [ ] 更新依赖包版本
- [ ] 检查数据完整性
- [ ] 优化数据库性能

## 🆘 紧急恢复步骤

如果系统完全无法工作：

```bash
# 1. 停止所有服务
pkill -f "python main.py"
pkill -f "npm run dev"

# 2. 备份数据
cp backend/stock_pool.db backup/

# 3. 重新部署
git pull origin main
pip install -r requirements.txt
cd frontend && npm install

# 4. 启动服务
python backend/main.py &
cd frontend && npm run dev &

# 5. 重新初始化数据
# 访问界面点击"初始化数据"
```

## 📞 获取支持

- **文档问题**: 查看 [项目概述](01-project-overview.md)
- **API问题**: 查看 [API文档](06-api.md)
- **架构问题**: 查看 [架构设计](02-architecture.md)
- **算法问题**: 查看 [算法详解](05-algorithms.md)

---

**记住**: 大部分问题都可以通过重新初始化数据来解决。如果遇到复杂问题，请先备份数据，然后按照故障排除步骤逐一检查。