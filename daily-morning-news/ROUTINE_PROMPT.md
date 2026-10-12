# 每日股市早报 · 定时任务执行手册

由 Claude 定时任务在每个交易日（周一至周五）北京时间 07:36 启动的全新云端会话执行，目标 8:00 左右出片。
全程自主完成，不要停下来等人确认。

## 0. 原则

- **只用真实数据**：查不到的就删掉该项或写"待公布"，绝不编造或"估计"成事实。关键数字至少两个来源交叉核对，并检查自洽（点数变化 ÷ 前收盘 ≈ 涨跌幅）。
- **获取方式**：运行环境拦截了行情接口（东方财富、新浪、腾讯、FRED、multpl、CNN 等直连都返回 403），WebFetch 也无法解析这些域名，所以数据一律用 **WebSearch**（重要的用 `extended` 模式，同一轮并行发出多个查询）。WebSearch 返回的是摘要，务必核对日期，不要把往年同月的数据当成今年的。
- 观点要有依据，用"大概率 / 或 / 有望"等措辞，不预测具体点位，不推荐个股，结尾保留免责声明。

## 1. 准备分支和环境

```bash
cd "$(git rev-parse --show-toplevel)"
git fetch origin
if git ls-remote --exit-code --heads origin daily-morning-news >/dev/null; then
  git checkout -B daily-morning-news origin/daily-morning-news
  # develop 合入了更新的流水线时，先同步过来
  if git cat-file -e origin/develop:daily-morning-news/pipeline/render.py 2>/dev/null; then
    git merge --no-edit origin/develop || { git merge --abort; echo "合并 develop 冲突，沿用当前分支的流水线"; }
  fi
else
  BASE=origin/develop
  git cat-file -e origin/develop:daily-morning-news/pipeline/render.py 2>/dev/null || BASE=origin/claude/kind-feynman-6hv106
  git checkout -B daily-morning-news "$BASE"
fi
cd daily-morning-news && bash pipeline/setup.sh
D=$(TZ=Asia/Shanghai date +%F); mkdir -p reports/$D
PREV=$(ls -d reports/20*/ | grep -v "$D" | sort | tail -1)   # 上一期，作为模板
echo "D=$D PREV=$PREV"
```

注意：每次 Bash 调用之间 shell 变量不会保留，后续命令里直接写出具体日期和路径。

## 2. 数据口径

- **美股**：最近一个已收盘的交易日（周二至周五早上是前一天，周一早上是上周五）。
- **A股 / 港股**：最近一个已收盘的交易日（周一早上是上周五；节假日顺延）。
- 若今天 A 股休市（法定节假日），仍然出片：开场说明"今日A股休市"，A股页用最近交易日数据并在 `asof` 注明日期。
- 每页 `asof` 写清楚数据时点，例如 "10月12日（周一）收盘"。

## 3. 采集数据（WebSearch）

第一轮并行发出：

1. **美股收盘**：道指、标普500、纳指的收盘点位和涨跌幅；主要驱动因素；表现突出的板块/个股；10年期美债收益率。
2. **A股收盘**：上证指数、深证成指、创业板指、科创50 的点位和涨跌幅；两市成交额及较前一交易日变化；涨跌家数；领涨/领跌板块和代表个股。
3. **港股收盘**：恒生指数、恒生科技指数、国企指数；板块和个股表现。
4. **宏观**：过去 1–2 天中美已公布的宏观数据（PMI、CPI/PPI、进出口、金融数据、非农、议息会议等）；本周/今天将公布的重要数据和事件，以及市场预期。
5. **机构观点**：近 3 天券商、机构对 A 股/港股/美股后市的研判。

第二轮：**情绪指标**。先读 `../.claude/skills/market-sentiment/SKILL.md`，按其中的阈值判定四档状态。逐项更新上一期 `report.json` 情绪页里的指标：

- 美股：席勒 CAPE、标普500 PE、隐含 ERP（= 1/CAPE − 10年美债）、CNN 恐惧贪婪、AAII 看涨比、VIX、高收益债利差、投资级债利差、10年期美债
- A股：沪深300 PE（及历史分位）、科创50 PE、制造业 PMI、沪深300 ERP（= 1/PE − 10年国债）、股息率−国债（≈ 0.4/PE − 10年国债）、两市成交额、两融余额

查不到最新值的：变化缓慢的指标（PE、CAPE、PMI）可沿用上一期，并在卡片名里注明月份；其余剔除，同时修改计数。
总体结论按 skill 规则：过热 ≥7 →「建议降低进攻性」；偏冷 ≥4 →「关注买入机会」；否则「中性区间，维持原配置」。

## 4. 撰写 reports/$D/report.json

复制 `$PREV/report.json` 作为模板，整体改写（格式见 README「report.json 格式」）。页面顺序：开场 → 美股 → A股 → 港股 → 宏观 → 情绪 → 展望。

**文稿结构**（总时长 4–6 分钟，约 50 句）：
- 开场 3 句：问候；"今天是二零二六年十月十三日，星期二。"；"一起来看美股、A股和港股的最新表现。"
- 美股 / A股 / 港股：概况 → 各指数点位涨跌 → 驱动因素/成交/板块/个股
- 宏观：已公布数据 → 海外数据 → 本周/今日日历与预期
- 情绪：框架说明 → 美股估值与情绪 → A股 → 计数与结论
- 展望：上一交易日盘面特点（一句话概括，如"权重稳、成长弱"）→ A股 / 港股 / 美股短期预期及依据 → 关键事件的情景分析 → 整体结论 →「以上内容仅供参考，不构成投资建议。」→「我们下期再见。」

**sub / say 规则**：
- `sub` 是字幕（阿拉伯数字），`say` 是朗读文本，两者意思一致。
- `say` 的数字全部写成汉字：百分之零点四三、三千七百九十七点二四点、一点五四万亿元、二零二六年（年份逐字读）、标普五百、科创五十、沪深三百。
- 英文只保留 `AI`、`A股`（流水线会替换成正确读音）；其他缩写写中文：PMI→采购经理指数，CPI→消费者物价指数，VIX→恐慌指数，CAPE→席勒市盈率，ERP→股权风险溢价。
- 避免单独的多音字，例如"为""处"（"PMI为50.1%"写成"录得"，"处于"写成"位于"或"在"），也避免"1167只股票"里的"只"（写成"家"）。
- 每句字幕不超过约 45 字（最多 3 行），长句拆开。
- `hi` 标出每句对应的卡片或要点，让画面跟着播报高亮。

**画面文字长度**（超出会溢出）：指数卡名称 ≤8 字；要点每行 ≤22 字；宏观行说明 ≤22 字；情绪卡名称 ≤8 字、数值 ≤7 字符；展望要点每行 ≤20 字；展望情景的条件和结果合计 ≤24 字。

## 5. 生成与检查

```bash
bash pipeline/make_video.sh reports/$D
```

- 修掉 lint 输出里的 ✗ 项；逐条看 · 项，读音不对的加到 `report.json` 的 `lexicon_extra`（如 `"行长 hang2 zhang3"`）或换说法。
- 用 Read 工具查看 `reports/$D/build/contact_sheet.png`，检查文字溢出、重叠、空白。有问题改 `report.json` 后重跑（只会重新合成改动的句子）。
- 可选回听：`bash pipeline/setup.sh --with-asr && python3 pipeline/qa_asr.py reports/$D ~/.cache/daily-morning-news/models`（小模型对专有名词常误判，仅作参考）。

## 6. 写 reports/$D/script.md

包括：标题、各市场的数据时点、逐段文稿（用字幕文本）、**数据来源**（实际用到的 URL，Markdown 链接）、数据缺口或存疑说明。

## 7. 提交并推送

```bash
git add reports/$D            # build/ 已被 .gitignore 忽略
git commit -m "daily: 股市早报 $D"
git push -u origin daily-morning-news   # 网络失败按 2/4/8/16 秒退避重试，最多 4 次
```

- **只推送 `daily-morning-news` 分支**，不要推送 develop 或其他分支，不要改动 `pipeline/`（除非流水线报错必须修复，修复后在最终回复里说明）。
- 这个分支只存放每日产出：如果环境要求为推送的分支建 PR，建一个标题为「每日股市早报产出」的草稿 PR；已经有就不要重复创建。

## 8. 最终回复

一段话：今天的核心结论；美股、A股、港股的主要指数涨跌；视频在 GitHub 上的路径；存疑或缺失的数据。
