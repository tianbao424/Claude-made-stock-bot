---
name: market-sentiment
description: >
  基于霍华德·马克斯《投资最重要的事》第二十章"市场评估指南"完整 19 维度框架，
  对A股和美股市场进行情绪诊断、估值定位和狂热度预警，生成温度计仪表盘（HTML）
  与监测周报（Markdown）。覆盖经济基本面/信贷与资本市场/投资者行为/基金机制/
  资产表现/投资人风格 六大类共 19 个原书维度，其中 12 个有自动化数据源、7 个
  支持人工补充判定。包含 24+ 个核心量化指标，按"底层估值锚→中层股债性价比
  →上层情绪温度→信号层流动性"四层组织，每个指标自动判定"过热/偏热/中性
  /偏冷"四档状态。
  当用户说"市场情绪分析"、"市场温度"、"霍华德马克斯钟摆"、"A股美股情绪对比"、
  "情绪温度计"、"市场过热了吗"、"现在该加仓还是减仓"、"市盈率分位"、"恐惧贪婪"、
  "估值仪表盘"、"股债性价比"、"信用利差"、"VIX分析"、"CAPE比率"、"巴菲特指标"、
  "市场评估指南"、"19维度评估"、"投资钟摆位置"时必须触发本技能。
  也适用于"帮我看看现在是不是该卖出"、"市场是不是泡沫"、"散户是不是太疯狂"、
  "出一份市场监测周报"、"做一个情绪仪表盘"、"对比A股和美股估值"、"按霍华德
  四层框架分析"、"按马克斯19维度分析"、"贷款机构是不是急于放贷"、"资本市场宽松还是紧缩"、
  "投资者是乐观还是悲观"、"生成sentiment dashboard"等场景。
  即便用户没有明确说"情绪分析"，但只要问到"现在适合买股票吗"、"市场顶在哪里"、
  "牛市末期了吗"、"什么时候该减仓"，也应当主动触发本技能给出系统化诊断。
---

# 市场情绪分析 Skill

基于霍华德·马克斯（Howard Marks）的市场评估框架，对 A 股、美股市场进行**情绪温度诊断**。核心命题来自《投资最重要的事》第二十章："投资人的风险态度会周期性地在过度厌恶和过度容忍之间摆动，并以此驱动估值偏离基本面。"

本 skill 不预测点位，**只评估温度**——告诉你"现在偏热还是偏冷"，仓位决策由你自己做。

---

## 一、什么时候用这个 skill

触发场景：

- 用户问"市场情绪"、"市场温度"、"现在估值高不高"
- 用户问"该加仓还是减仓"、"是不是牛市末期"、"市场顶在哪"
- 用户问"霍华德·马克斯怎么看现在的市场"、"按钟摆理论现在在哪"
- 用户提到 VIX、CAPE、Buffett 指标、AAII、恐惧贪婪指数、ERP 等任一专业指标
- 用户要"生成市场监测周报"、"做一个情绪仪表盘"
- 用户对比 A 股和美股估值
- 用户问"散户是不是太疯狂了"、"基金发行火热说明什么"
- 用户上传财经数据要求做"温度判断"

不适合用：

- 单纯问个股走势、技术分析、K线形态 → 那是技术分析任务，不是情绪诊断
- 问宏观经济预测、GDP 走势 → 那是宏观研究任务
- 问具体某只基金/股票能不能买 → 本 skill 只判市场整体温度，不给个股建议

---

## 二、核心理论框架（霍华德·马克斯 19 维度完整版）

马克斯在《投资最重要的事》第 20 章给出了一份"市场评估指南"，用 19 个问题对当下市场做温度判定。每个问题都有两端（乐观 ↔ 悲观），把当下市场放在哪一端，就能看出"钟摆"摆到哪里了。

19 个维度分 6 大类。**完整对照表见 `references/framework.md`**，下面只列纲要：

### A 组：经济基本面（2 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 1 | 经济现状 | 生机勃勃 ↔ 停滞不前 |
| 2 | 经济展望 | 正面有利 ↔ 负面不利 |

### B 组：信贷与资本市场（6 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 3 | 贷款机构 | 急于放贷 ↔ 缄默谨慎 |
| 4 | 资本市场 | 宽松 ↔ 紧缩 |
| 5 | 资本供给 | 充足 ↔ 短缺 |
| 6 | 融资条款 | 宽松 ↔ 严格 |
| 7 | 利率水平 | 低 ↔ 高 |
| 8 | 利差水平 | 窄 ↔ 宽 |

### C 组：投资者行为（4 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 9 | 投资者情绪 | 乐观/自信/渴望买进 ↔ 悲观/忧虑/无心买进 |
| 10 | 资产持有人 | 乐于持有 ↔ 急于卖出离场 |
| 11 | 卖家 | 稀少 ↔ 众多 |
| 12 | 市场 | 人群拥挤 ↔ 乏人问津 |

### D 组：基金/媒介机制（1 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 13 | 基金 | 申购门槛高/每天发新基金 ↔ 向所有人开放/只有最好的能募资 |

### E 组：资产表现（4 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 14 | 近期业绩 | 强劲 ↔ 萎靡 |
| 15 | 资产价格 | 高 ↔ 低 |
| 16 | 预期收益 | 低 ↔ 高 |
| 17 | 风险 | 高 ↔ 低 |

### F 组：投资人风格与易犯错误（2 维）
| # | 维度 | 偏热 ↔ 偏冷 |
|---|---|---|
| 18 | 流行风格 | 激进/四处投资 ↔ 审慎且自律/精挑细选 |
| 19 | 易犯错误 | 买进太多/高价追涨/承受太多风险 ↔ 买进太少/离开市场/承受太少风险 |

当 14+ 维度都摆到"偏热"一端时，**风险/收益比已经变差**，按马克斯的话是"该降低进攻性"。反之 ≥10 个偏冷则是机会。

---

## 三、四层监测框架（频率匹配信号有效期）

七维度回答"市场冷热"，但具体指标变化速度不同。本 skill 按监测频率组织成四层：

```
🏛️ 底层 · 长期估值锚（季度级监测）
   Shiller CAPE、巴菲特指标、各指数PE分位

⚖️ 中层 · 股债性价比（季度级监测）
   隐含ERP、股息率-国债利差

🌡️ 上层 · 月度情绪温度（周度级监测）
   AAII、CNN恐贪、月度开户数、新发基金

⚡ 信号层 · 流动性与狂热（日度级监测）
   VIX、信用利差、融资余额、成交额、北向资金
```

**关键原则**：监测频率匹配信号有效期。每日看的指标不该用来做决策（噪音多），季度看的指标才是真正的方向标。

---

## 四、执行流程

```
Step 1  明确监测范围（A股/美股/两者，默认两者）

Step 2  调用 scripts/market_sentiment_monitor.py 拉数据
        → 24+ 个量化指标，按四层组织，每个自动判 hot/warm/neutral/cool

Step 3  生成 Markdown 周报（reports/sentiment_report_YYYY-MM-DD.md）

Step 4  生成 HTML 仪表盘（reports/sentiment_dashboard_YYYY-MM-DD.html）
        → 两列大卡片布局，A股左、美股右，按四层分组

Step 5  19 维度对照盘点（参考 references/framework.md 的映射表）
        → 量化维度由脚本结果填充
        → 半量化维度结合数据+常识判断
        → 纯定性维度（贷款机构/融资条款等）需在月度复盘时人工评估
        → 统计有多少个维度在"偏热端"

Step 6  基于汇总输出操作提示：
        - 量化层：过热数 vs 偏冷数
        - 19 维层：钟摆位置在哪一档（≥14偏热 / 10-13偏热 / 中性 / 6-9偏冷 / ≥10偏冷）

Step 7  把文件展示给用户（用 present_files）
```

---

## 五、脚本调用

### 完整运行

```bash
cd <skill-dir>/scripts
python3 market_sentiment_monitor.py
```

输出：
- `./reports/sentiment_report_YYYY-MM-DD.md` （Markdown 周报）
- `./reports/sentiment_dashboard_YYYY-MM-DD.html` （HTML 仪表盘）

### 按市场过滤

```bash
python3 market_sentiment_monitor.py --skip-us    # 只看A股
python3 market_sentiment_monitor.py --skip-cn    # 只看美股
```

### 邮件推送

```bash
export SMTP_HOST=smtp.qq.com SMTP_USER=xxx@qq.com SMTP_PASSWORD=xxx
python3 market_sentiment_monitor.py --email yourname@example.com
```

依赖安装：

```bash
pip install akshare pandas requests
```

---

## 六、指标全集（共 24+ 项）

### 底层 · 长期估值锚

| 市场 | 指标 | 数据源 | 判定逻辑 |
|---|---|---|---|
| 美股 | Shiller CAPE | multpl.com | >35 hot，>25 warm，<15 cool |
| 美股 | S&P 500 PE (TTM) | multpl.com | >28 hot，>22 warm |
| 美股 | Buffett 指标 | gurufocus | >150 hot，>120 warm |
| A股 | 沪深300 PE | akshare | 历史分位 >80 hot，<30 cool |
| A股 | 上证50 PE | akshare | 历史分位 >80 hot，<30 cool |
| A股 | 科创50 PE | akshare | >100 hot，>60 warm |

### 中层 · 股债性价比

| 市场 | 指标 | 数据源 | 判定逻辑 |
|---|---|---|---|
| 美股 | 隐含 ERP | multpl+FRED | <1 hot，<2 warm，>4 cool |
| A股 | 沪深300 ERP | akshare | >5 cool，<2 hot |
| A股 | 股息率-10Y国债 | 计算 | >0.5 cool |

### 上层 · 月度情绪温度

| 市场 | 指标 | 数据源 | 判定逻辑 |
|---|---|---|---|
| 美股 | AAII 散户看涨比 | aaii.com | >50 hot，看涨-看跌>25 hot |
| 美股 | CNN 恐惧贪婪 | CNN | >75 hot，>55 warm，<25 cool |
| 美股 | IPO 活跃度 | 占位 | 手动从 Renaissance Capital 更新 |
| A股 | 月度新开户 | 占位 | 手动从中登月报更新 |
| A股 | 新发基金数 | akshare | >30 warm |
| A股 | IPO 储备数 | akshare | >100 warm |

### 信号层 · 流动性与狂热

| 市场 | 指标 | 数据源 | 判定逻辑 |
|---|---|---|---|
| 美股 | VIX | FRED | <13 hot（极静反向警示），>30 cool |
| 美股 | 高收益债 OAS | FRED | <3 hot，>6 cool |
| 美股 | 投资级债 OAS | FRED | <1 hot，>2 cool |
| 美股 | 10Y-3M 期限利差 | FRED | <0 hot（倒挂） |
| 美股 | 10Y 美债收益率 | FRED | 跟踪变化幅度 |
| 美股 | 美元广义指数 | FRED | 跟踪 30 日变化 |
| A股 | 上交所融资余额 | akshare | 较30日均 +10% hot |
| A股 | 两市日成交额 | akshare | >25000亿 hot，<5000亿 cool |
| A股 | 北向资金（5日） | akshare | <-100亿 cool，>+100亿 warm |
| A股 | Shibor 1月 | akshare | <1.8 cool，>2.5 warm |

---

## 七、状态判定逻辑

每个指标输出四档状态之一：

| 状态 | 含义 | 颜色 | 建议 |
|---|---|---|---|
| 🔴 hot | 过热/警示 | 粉色 #FBEAF0 | 降低进攻性 |
| 🟠 warm | 偏热 | 米黄 #FAEEDA | 提高警惕 |
| ⚪ neutral | 中性 | 米灰 #F1EFE8 | 维持配置 |
| 🟢 cool | 偏冷/有安全边际 | 薄荷 #E1F5EE | 关注买入 |

判定规则两种：
- **绝对阈值**：适合 VIX、CAPE 这类有公认水位的指标
- **历史分位数**：适合所有 PE 指标，自动适应不同市场结构

总体提示：
- 过热数 ≥7 → "建议降低进攻性"
- 偏冷数 ≥4 → "关注买入机会"
- 其他 → "维持原配置"

---

## 八、输出物结构

### Markdown 周报（`sentiment_report_YYYY-MM-DD.md`）

```
# 市场情绪监测周报
## 概览
- 总指标数 / 各状态数量
## 🏛️ 底层 · 长期估值锚（季度级）
   ### 美股 | 表格
   ### A股 | 表格
## ⚖️ 中层 · 股债性价比（季度级）
## 🌡️ 上层 · 月度情绪温度（周度级）
## ⚡ 信号层 · 流动性与狂热（日度级）
## 操作提示
```

### HTML 仪表盘（`sentiment_dashboard_YYYY-MM-DD.html`）

两列大卡片布局：
- 顶部：标题 + 生成时间 + 四档汇总数 + 总体判断
- 主体：按四层垂直分组，每层左A股、右美股
- 每张卡片三段：「市场·指标名」「数值」「一句话注释」
- 底部：图例 + 数据异常折叠面板
- 响应式：手机自动单列

打开就是和参考截图视觉一致的样式（粉/橙/灰/绿配色，无依赖，纯 HTML+CSS）。

---

## 九、定时运行（推荐）

把这个 skill 接入定时调度，每周自动产出一份温度报告：

### macOS / Linux cron

```bash
# 每周日早上 9 点
0 9 * * 0 cd <skill-dir>/scripts && /usr/bin/python3 market_sentiment_monitor.py --email me@example.com >> cron.log 2>&1
```

### Windows 任务计划程序

新建基本任务 → 每周日 09:00 → 启动程序：
- 程序：`python.exe`
- 参数：`market_sentiment_monitor.py --email me@example.com`
- 起始位置：`<skill-dir>/scripts`

---

## 十、扩展指南

### 添加新指标

在 `scripts/market_sentiment_monitor.py` 中找到 `collect_us_indicators` 或 `collect_a_share_indicators`，按下面模板加一个函数，然后用 `safe_fetch` 包裹注册：

```python
def my_new_indicator():
    # 1. 拉数据
    data = some_data_source()
    # 2. 计算当前值
    latest = float(data["value"].iloc[-1])
    # 3. 判定状态
    if latest > THRESHOLD_HOT:
        status, note = "hot", "过热说明"
    elif latest < THRESHOLD_COOL:
        status, note = "cool", "偏冷说明"
    else:
        status, note = "neutral", ""
    # 4. 注册到 report
    report.add(Indicator(
        "指标显示名", latest, "%",
        "底层",           # 层级：底层/中层/上层/信号层
        "US",             # 市场：US/CN
        "市盈率",          # 维度：投资者情绪/市盈率/信用利差/信贷周期/证券发行
        "历史参考说明",     # historical_context
        status, note,
    ))

safe_fetch("My Indicator", my_new_indicator, report)
```

`safe_fetch` 会捕获异常并记录到报告末尾的"数据获取异常"区，不会让整个脚本崩溃。

### 添加推送渠道

`scripts/extensions.py` 提供了钉钉、企业微信、Telegram 推送函数，按需调用：

```python
from extensions import send_dingtalk, send_wecom, send_telegram, cnn_fear_greed
send_dingtalk(webhook_url, body_md)
```

### 自定义阈值

阈值散落在各采集函数里（如 `if val > 35: status="hot"`）。要做全局调优，可以把阈值抽到一个 dict 配置文件里，但目前简单起见就在函数内直接写。

---

## 十一、何时调用此 skill 而非直接搜索

**触发此 skill 的判据**：

- 用户期望得到**系统化的多指标诊断**，而不是单个数据点
- 用户提到任何一个本 skill 覆盖的指标名
- 用户的问题本质是"现在市场温度如何"

**不触发此 skill 的判据**：

- 用户只问"VIX 现在是多少" → 直接 web 搜一下报数字即可，不用跑整套脚本
- 用户问"今天 A 股涨跌幅" → 行情查询，与情绪诊断无关
- 用户问"帮我分析茅台" → 个股分析，应调用其他 skill

---

## 十二、重要参考

详细的指标定义、状态判定阈值、数据源说明，见：

- `references/framework.md` — 霍华德·马克斯七维度详解和判定规则
- `references/indicators.md` — 全部 24+ 指标的字段、数据源、判定逻辑速查表
- `references/monitoring-cadence.md` — 监测频率的设计原理和操作建议

脚本：

- `scripts/market_sentiment_monitor.py` — 主采集脚本
- `scripts/html_dashboard.py` — HTML 仪表盘渲染器
- `scripts/extensions.py` — 钉钉/企业微信/Telegram 推送扩展

资源：

- `assets/dashboard_sample.html` — 仪表盘样张，可直接打开看效果
- `assets/sample_report.md` — Markdown 周报样张
- `assets/19_dimensions_checklist.md` — 19 维度人工盘点工作表模板，每月填一份

---

_本 skill 输出仅为基于规则的统计提醒，不构成投资建议。马克斯的原话："我们也许永远不知道自己将去往何方，但最好搞清楚自己身在何处。"_
