# 学透（mistake-mastery）· 给 AI 编程助手的说明

> 仓库根目录的 `CLAUDE.md` 和 `docs/` 讲的是**股票机器人**项目，和学透无关。在 `mistake-mastery/` 下工作时以本文件为准。

## 这是什么

给自家一个北京初三孩子用的数学、物理错题工具，**家庭自用、非商业**。家长在家里电脑上运行（本地版），手机连同一个 Wi-Fi 用浏览器访问；数据自动同步到家长自己的 GitHub **私有**数据仓库。

用的人是不写代码的家长：界面文字、报错、命令行输出都用**简体中文大白话**，说清楚"该怎么办"，不堆术语。

## 必须遵守

1. **本仓库是公开的。** 孩子的任何数据都不能进来：照片、错题、作答、所在区、学校、姓名、考试日期、真实卷子（包括截图和导入结果）。
   - 测试和示例只用虚构或合成的数据。
   - 家长发来的真实卷子只放在临时目录里用，不提交；文档里描述真卷测试时不写学校名。
   - `bakeoff-out/`、`bank-try-out/`、`data/`、`.env` 已被 `.gitignore` 排除，不要改。
2. **密钥只放 `.env`**（前缀 `XT_`，见 `app/config.py`），不写进代码、文档、日志、提交信息。不要让用户把密钥贴到对话里；需要核对时只显示开头 3 个字符（见 `app/tools/bakeoff.py` 的 `key_report`）。
3. **发给大模型的内容不带孩子的名字**（讲解提示词只发错题和掌握情况）。
4. **官方答案优先。** 答案来源的优先级：题库官方答案 > 老师卷面订正 > 答案页 > 家长填写 > AI 解答（标"待核"）。AI 只负责核对和提醒，不能覆盖官方答案。
5. **改了提示词就升版本号**（`app/services/prompts.py` 里的 `*_VERSION`）。大模型结果按（模型、提示词版本、消息）缓存，不升版本会继续用旧结果。
6. **测试不调用真实接口。** 大模型用 `ctx.llm.fake` 注入固定输出，后台任务在测试里用 `jobs_inline=True` 同步执行（见 `tests/conftest.py`）。

## 常用命令（都在 `mistake-mastery/` 下运行）

```bash
uv sync                                    # 安装后端依赖
uv run pytest -q                           # 全部测试（生成 PDF 的测试需要 Chromium：uv run playwright install chromium）
uv run python -m app                       # 启动（0.0.0.0:8000）；启动前检查 XT_DATA_DIR 和 .env
cd web && npm install && npm run build     # 构建前端，后端直接提供 web/dist
cd web && npm run typecheck                # 前端类型检查
cd web && npm run dev                      # 前端开发服务器，/api 转发到 8000

uv run python -m app.tools.bakeoff --check # 检查密钥、模型（含看图）、擦除接口、GitHub 连通性
uv run python -m app.tools.bank_try 试卷.pdf --answers 答案.pdf --subject physics
                                           # 在临时目录用真实模型试导入，输出 bank-try-out/ 下的报告
uv run python web/demo/make_fixtures.py    # 重新生成预览版示例数据（需要 Chromium）
cd web && npm run build:demo               # 预览版单页 web/dist-demo/preview.html
```

## 代码结构

```
app/
  main.py · __main__.py   应用入口；启动命令（启动前检查、显示手机访问地址）
  config.py               配置（.env，前缀 XT_）
  context.py              把数据库、存储、大模型、任务队列、同步装在一起
  db.py · models.py       SQLite 与数据表；__sync__ 标明是否导出到数据仓库
  jobs.py                 进程内持久任务队列（ctx.jobs.register / submit）
  api/                    接口：auth、core、capture、mistakes、knowledge、printing、bank
  services/
    capture.py            拍照采集管线：矫正 → 识别切题 → 分类 → 确认
    bank.py               题库导入（PDF 文字层定位、跨页合并、阅读材料、答案对应、AI 核对与答案比对）、录入时匹配
    mastery.py            错题状态机（三道关 + 回炉）
    knowledge.py          知识点掌握度、掌握死角
    lessons.py            知识点讲解
    printing.py           错题重做单排版（Chromium 生成 PDF）
    sync.py               导出 JSONL、提交并推送到数据仓库
    prompts.py            全部提示词和版本号
  adapters/               imaging（OpenCV）、pdf（pdfium）、eraser（各家去手写）、llm（OpenAI 兼容客户端）
  curriculum/             知识点树、错因、题型、北京中考题位（YAML）
  tools/                  bakeoff、bank_try、rebuild_index、hash_password
web/src/                  React 前端：pages/、api.ts（接口类型）、demo/（预览版的浏览器内模拟后端）
web/demo/                 预览版示例数据生成脚本
tests/                    pytest；conftest.py 里有假大模型和临时数据仓库
docs/                     设计文档 01–10
```

## 改动时的约定

- **数据表**：新加列会在启动时自动补上（`db.add_missing_columns`，新列一律可空）；不要改名或删列，旧数据仓库里的 JSONL 还要能导入。新表要设 `__sync__`（`"table"` / `"monthly"` / `None`），导出 → 导入 → 再导出必须逐字节一致（有测试）。
- **知识点编码**（`app/curriculum/*.yaml`）：数据里引用了这些编码，不要改名或删除。分类只在最细的考点里选，模型给的编码用 `Curriculum.resolve` 对到清单上。
- **大模型**：各任务的默认模型和三套搭配（`qwen` / `mimo` / `deepseek`）在 `app/adapters/llm.py`；接口报错要用 `explain_error` 翻译成"该怎么办"。拿不到官方答案时，AI 对要看图的题给的答案不可靠，界面上必须标"待核"。
- **后台任务**：耗时的事（识别、导入、核对、讲解）放进任务队列，用 `handle.progress()` 报进度；单个任务里可以并发调用大模型（例如 `bank.verify_paper` 4 道同时问），但保存结果放回调用方线程（`handle.progress` 也只在调用方线程里调）。
- **接口变了**：同步更新 `web/src/api.ts` 的类型、`web/src/demo/mock.ts` 的模拟，以及 `web/demo/make_fixtures.py`。
- **文档跟着改**：表和接口 → `docs/04`；模型和提示词 → `docs/05`；状态机、掌握度、讲解 → `docs/06`；题库 → `docs/10`；家长要做的操作 → `SETUP.md`；进度 → `README.md` 的"状态"。
- **代码风格**：注释和文档用中文，写清楚"为什么"；照着周围代码的写法来。

## 设计文档

先读 `README.md`（一页纸、已定的决策、文档目录），再按需看：

| 文件 | 内容 |
|---|---|
| `docs/01-product-requirements.md` | 需求、使用场景、"学透"的定义 |
| `docs/02-ux-design.md` | 页面与交互、打印模板、文案语气 |
| `docs/03-system-architecture.md` | 架构、数据存 GitHub、图像管线、排版、代码目录 |
| `docs/04-data-model-and-api.md` | 数据表、题目 JSON、接口、同步格式 |
| `docs/05-ai-design.md` | 模型搭配与切换、分类、解答与核对 |
| `docs/06-mastery-algorithm.md` | 状态机、三道关、复习调度、知识点掌握度、讲解 |
| `docs/07-beijing-curriculum.md` | 北京中考结构、知识点树、错因字典 |
| `docs/08-privacy-vendors-and-tools.md` | 隐私规则、各家接口 |
| `docs/09-roadmap.md` | 版本计划 |
| `docs/10-question-bank.md` | 题库导入，以及用真卷子、真实模型测过的结果 |
