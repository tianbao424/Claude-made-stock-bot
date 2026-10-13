# 每日股市早报（Daily Morning News）

每个交易日早上自动生成一条竖屏股市早报视频（1080×1920，标准普通话配音 + 字幕），内容包括：

开场 → 美股 → A股 → 港股 → 宏观数据 → 市场情绪（[market-sentiment skill](../.claude/skills/market-sentiment/SKILL.md)，霍华德·马克斯四层框架）→ 今日复盘与后市展望

示例：[reports/2026-10-12/](reports/2026-10-12/)

## 工作方式

```
Claude 定时任务（周一至周五 北京时间 07:36）
  └─ 唤醒固定的「每日股市早报机器人」云端会话（已挂载本仓库），按 ROUTINE_PROMPT.md 执行
       1. WebSearch 收集隔夜美股、A股/港股收盘、宏观数据、情绪指标、机构观点
       2. 写 reports/<日期>/report.json（数据 + 逐句文稿）
       3. pipeline/make_video.sh：读音检查 → 离线 TTS 配音 → 逐句渲染画面 → ffmpeg 合成（开头拼接 pipeline/assets/intro.mp4 片头，字幕自动后移）
       4. 检查拼图、写 script.md（文稿 + 数据来源）
       5. 提交并推送到 daily-morning-news 分支
```

为什么由 Claude 而不是纯脚本采集数据：运行环境的网络策略拦截了行情接口（东方财富、新浪、FRED、CNN 等），只能通过网页搜索获取并交叉核对；宏观解读、情绪判定和后市展望也需要分析判断。

**每日产出推送到 `daily-morning-news` 分支**的 `daily-morning-news/reports/<日期>/` 目录，不会写入 `develop`。

## 目录

```
daily-morning-news/
├── ROUTINE_PROMPT.md        # 定时任务每天执行的完整步骤（改流程就改这里）
├── pipeline/
│   ├── setup.sh             # 安装依赖 + 下载离线语音模型（~130MB，缓存在 ~/.cache，不提交）
│   ├── make_video.sh        # report.json → 配音 / 字幕 / 视频
│   ├── assets/intro.mp4     # 15 秒片头，自动拼在每期视频开头（INTRO_VIDEO= 可跳过）
│   ├── lint_say.py          # 朗读文本检查（字母数字残留、多音字）
│   ├── synth.py             # 逐句 TTS，按句缓存
│   ├── render.py            # 逐句渲染画面 + 检查用拼图
│   ├── qa_asr.py            # 可选：语音识别回听
│   └── lexicon_extra.txt    # 读音补充词典（多音字、银行名等）
└── reports/<YYYY-MM-DD>/
    ├── report.json          # 当天的数据和文稿（唯一输入）
    ├── morning_news_<日期>.mp4
    ├── narration.mp3        # 纯配音，可铺到其他画面上
    ├── subtitles.srt        # 字幕，可直接导入剪映
    └── script.md            # 文稿 + 数据来源
```

## 手动生成

```bash
cd daily-morning-news
bash pipeline/setup.sh                        # 首次运行
bash pipeline/make_video.sh reports/2026-10-12
```

改了 `report.json` 后重跑即可，未改动的句子会复用缓存的配音。

## report.json 格式

```jsonc
{
  "date": "2026-10-12",
  "title": "股市早报",
  "date_display": "2026年10月12日 周一",      // 页眉
  "intro_date": "2026年10月12日  星期一",     // 开场页
  "default_src": "数据来源：……",              // 页脚（各页可用 src 覆盖）
  "data_note": [["美股", "北京时间今晨收盘（美东10月12日）"],
                ["A股 · 港股", "上一交易日（10月12日）收盘"]],  // 开场页的数据时点说明框
  "lexicon_extra": ["某词 pin1 yin1"],        // 可选：当天额外读音
  "slides": [ /* 按顺序 */ ]
}
```

每页都有 `sentences`：`[{ "sub": 字幕, "say": 朗读文本, "hi": [高亮的元素] }]`。
`sub` 用阿拉伯数字；`say` 的数字一律写成汉字（"百分之零点四三""三千七百九十七点二四点"），
英文只允许 `AI`、`A股`（会自动替换），其他缩写写中文。除开场页外，每页的 `tab` 是顶部标签名，`asof` 显示为右上角的金色数据时点标签。

**数据时点**：8 点出片时，美股是北京时间当天凌晨收盘的交易日，A股和港股是上一交易日收盘。开场说明框、开场播报、各市场页的 `asof` 和第一句、`script.md` 开头都必须写明，固定格式见 [ROUTINE_PROMPT.md](ROUTINE_PROMPT.md) 第 2 步。

| type | 字段 | hi 取值 |
|---|---|---|
| `intro` | `chips: [[市场, 指数, "+0.83%", "up"/"down"], ...]`（3 个）；数据时点取顶层 `data_note` | `chips`、`note` |
| `market` | `tab`, `asof`, `cards: [[名称, 点位, 涨跌幅, 方向]]`（≤4），`bullets: [[[文字, 颜色], ...]]`（≤5 行，颜色 `null`/`up`/`down`/`gold`/`sub`） | `c0`…、`b0`… |
| `macro` | `tab`, `asof`, `src`, `groups: [[标题, gid, rows]]`，`cn`/`us` 行为 `[名称, 数值, 说明]`，`cal` 行为 `[日期, 事件]` | `cn0`、`us1`、`cal0`… |
| `sentiment` | `tab`, `asof`, `src`, `verdict: [结论, 建议]`, `counts: {hot,warm,neutral,cool}`, `cols: [[标题, gid, [[名称, 数值, 状态]]]]`（左 A股 ≤9、右 美股 ≤9） | `cn0`、`us0`…、`banner` |
| `outlook` | `tab`, `asof`, `src`, `banner: {label, headline, stats: [[文字, 方向或null]]}`, `cards: [[市场, gid, 标签, [要点]]]`, `scen: [[条件, 结果, up/down]]`, `scen_card: "us"` | `banner`、`a`、`hk`、`us`、`scen` |

## 注意事项

- **配音模型许可**：当前用的是 sherpa-onnx 的 `matcha-icefall-zh-baker`，训练数据（标贝）**仅限非商业用途**。账号如有商业变现，请换用可商用的 TTS（如 Azure、火山引擎、阿里云，或开源可商用的 Kokoro）。
- **数据准确性**：数据来自网页搜索结果并经交叉核对，仍可能有误；发布前建议对照行情软件核对主要指数。
- **仓库体积**：每条视频约 5–6MB，每年约 1.5GB。如需控制体积，可定期清理旧视频，或改为上传到对象存储 / GitHub Releases。
- 内容仅供参考，不构成投资建议。
