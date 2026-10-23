---
name: daily-morning-news
description: >
  生成「每日股市早报」竖屏视频（约 3 分钟）：WebSearch 采集隔夜美股、上一交易日 A股/港股收盘、
  中美宏观数据、情绪指标与券商观点 → 写 report.json → 离线配音 + 渲染 + 片头 + 背景音乐合成 MP4
  → 自查 → 写 script.md（含数据来源）→ 推送到 daily-morning-news 分支。
  当用户说"出今天的早报"、"做股市早报视频"、"生成早报"、"每日早报"、"早报任务"、
  "补做某天的早报"、"重做早报视频"，或定时任务「每日股市早报视频」触发时使用本技能。
  也适用于修改早报的结构、时长、读音、片头、背景音乐、结尾语等流程问题。
---

# 每日股市早报

完整步骤和格式规范在 `daily-morning-news/ROUTINE_PROMPT.md`（唯一权威手册，先通读），
`report.json` 字段见 `daily-morning-news/README.md`。本技能补充手册之外的执行要点和自查脚本。

## 流程总览

1. **准备分支**：仓库根目录 `git fetch origin`；远端有 `daily-morning-news` 就
   `git checkout -B daily-morning-news origin/daily-morning-news`，否则按手册第 1 步创建（`--no-track`）。
   然后 `cd daily-morning-news && bash pipeline/setup.sh --with-asr`（含回听用的 ASR 模型）。
2. **采集数据**（手册第 2–3 步）：同一轮并行发多个 `extended` WebSearch。
3. **写 report.json**：以上一期 `reports/<上期>/report.json` 为模板，用一个 Python 脚本整体改写
   （放在 scratchpad，逐页替换 cards / bullets / sentences），不要手改 JSON。
4. **生成与自查**：
   ```bash
   S=../.claude/skills/daily-morning-news/scripts
   python3 pipeline/lint_say.py reports/$D/report.json ~/.cache/daily-morning-news/models  # 读音
   python3 $S/check_report.py reports/$D        # 字幕长度、页脚宽度、数据时点、结尾语
   bash pipeline/make_video.sh reports/$D       # 看最后的 duration
   python3 $S/asr_recheck.py reports/$D         # 回听「美股/港股」，读错的删缓存
   # 输出 bad>0 时重跑 make_video.sh 再回听，最多 3 轮
   ```
   然后用 Read 看 `reports/$D/build/contact_sheet.png`（溢出、重叠、截断）。
5. **script.md**（手册第 6 步）→ 再跑一次 `check_report.py` → 提交推送（手册第 7 步，只推 `daily-morning-news`）。
6. **汇报**：一段话 + 三大市场指数表格 + 存疑数据清单（手册第 8 步）。

## 数据核对要点

- **自洽校验**：每个指数都用「前收盘 ± 点数 = 收盘」「点数 ÷ 前收盘 ≈ 涨跌幅」核一遍；
  多个来源点位差零点几时，选与前一日收盘能对上的那组，并在 script.md 注明另一来源的数字。
- **FX168 速递**（fx168news.com/express/fastnews）一条就给齐当日所有指数的点数、涨跌点和涨跌幅，
  A股那条还含科创50、沪深300，是最好的交叉核对源。
- **盘中 ≠ 收盘**：WebSearch 常返回盘中快讯（"截至发稿"）、前一日数据或往年同月文章，逐条核对日期。
- 美国债市在哥伦布日、退伍军人节等休市而股市照常交易：美债收益率沿用上一交易日并注明。
- 中美重要数据（CPI/PPI/进出口/金融数据/非农）出片时若尚未公布，只写"今日公布"和机构预期；
  已公布的第二天要写实际值 vs 预期。
- 查不到的情绪指标（两融余额、CAPE、利差等）沿用上一期，在 script.md「数据缺口」逐项说明；
  按指数涨跌幅推算的估值（如沪深300 PE）要标明"推算"。
- 个股涨跌幅各来源矛盾时不写数字（写"继续走弱""盘中创新高"），或干脆不写。

## 文稿与画面要点

- **时长**：目标约 3 分钟，`make_video.sh` 输出的 duration **≤190 秒**（含 4.5 秒片头）。超了就删句、
  合并句，优先删宏观日历和情绪页里重复画面的内容。约 22–25 句。
- **字幕 ≤45 字**：`check_report.py` 会报；长句在分号处拆成两句，各自配 `hi`。
- **页脚来源**：`default_src` / `src` 过长会被截断（约 35 个汉字宽，英文字母按半个算）。
- **结尾固定**：展望页最后一句「祝您账户常红，天天开心！」，不口播免责声明（页脚已显示）。
- **数据时点五处**：开场 `data_note`、开场数据时点句（`hi: ["note"]`）、三个市场页的 `asof` 和第一句、script.md 开头。

## 读音要点

- 固定读音在 `pipeline/lexicon_extra.txt`：A股的 A 读 ei1、AI 读 ai1 ai4、美股/港股按三声变调读
  mei2 gu3 / gang2 gu3。当天特有词放 `report.json` 的 `lexicon_extra`（如 `大行 da4 hang2`、`富国银行 … yin2 hang2`、`长鑫 chang2 xin1`）。
- `lint_say.py` 的「·」提示要逐条看：含「行」的词（银行名、大行、行业）、「长」「重」「为」「处」「只」等多音字最常出错。
- `say` 里不能有英文字母（AI、A股除外）：PCB→印制电路板、CPI→消费者物价指数、PPI→生产者物价指数、VIX→恐慌指数。
- TTS 每次合成有随机性，开头的「美股方面」最容易被读糊，`asr_recheck.py` 会删掉读错的缓存让它重合成。
  ASR 把 mei2 gu3 听成「煤股」属于正确读音；A股的 ei1 ASR 基本认不出来，不必追。

## 资源

- `pipeline/assets/intro.mp4`（4.5 秒片头，由 `pipeline/make_intro.py` 生成）、`pipeline/assets/bgm.mp3`
  （原创香颂手风琴华尔兹，由 `pipeline/make_bgm.py` 生成，音量 `BGM_VOL`，默认 0.4）。`make_video.sh` 自动拼接和混音。
- 情绪判定阈值见 `.claude/skills/market-sentiment/SKILL.md`「指标全集」。
- 定时任务「每日股市早报视频」（工作日北京时间 07:36）唤醒固定会话执行本流程；暂停/恢复用 `update_trigger` 的 `enabled`。
