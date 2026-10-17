# 学透 · 本地版安装与使用

本地版跑在家里的一台电脑上（Mac、Windows、Linux 都可以），手机连同一个 Wi-Fi，用浏览器访问。孩子的数据会自动同步到你自己的 **GitHub 私有仓库**。

> ⚠️ 代码所在的仓库是**公开的**。孩子的照片、错题、档案只放在**私有数据仓库**和本机上，不要放进代码仓库。

---

## 1. 准备软件（一次性，约 20 分钟）

下面的命令都在"终端"里输入：Mac 用"终端"（启动台 → 其他 → 终端），Windows 用 **PowerShell**（开始菜单搜索 PowerShell）。每装完一个软件，**关掉终端再重新打开**，新命令才能用。

| 软件 | 用途 | Mac | Windows |
|------|------|-----|---------|
| Git | 下载代码、同步数据 | 终端运行 `xcode-select --install`，弹窗点"安装" | 在 git-scm.com 下载 Git for Windows，一路默认安装 |
| uv | 管理 Python 环境 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Node.js 18 以上 | 构建网页（只在安装和升级时用） | nodejs.org 下载 LTS 版安装包 | 同左 |
| GitHub CLI | 登录 GitHub，让程序能自动推送数据 | cli.github.com 下载 macOS 安装包 | 不需要（Git for Windows 自带登录工具） |

装好后检查一下，能显示版本号就行：

```bash
git --version
uv --version
node --version
```

---

## 2. 登录 GitHub，建私有数据仓库（一次性）

1. 在 github.com 新建仓库，名字例如 `xuetou-data`，**一定选 Private（私有）**，勾上"Add a README file"，不要加协作者。
2. 给 GitHub 账号开启两步验证，并保存好恢复码。
3. 让这台电脑登录 GitHub，并把数据仓库下载到用户目录下：

   **Mac**：

   ```bash
   gh auth login        # 依次选 GitHub.com → HTTPS → Yes → Login with a web browser，按提示在浏览器里确认
   gh repo clone <你的账号>/xuetou-data ~/xuetou-data
   ```

   **Windows**（PowerShell）：

   ```powershell
   git clone https://github.com/<你的账号>/xuetou-data.git $HOME\xuetou-data
   ```

   第一次会弹出浏览器让你登录 GitHub，登录一次之后电脑会记住。

这一步成功，说明这台电脑有推送到数据仓库的权限，程序之后会用同样的权限自动同步。

---

## 3. 下载代码并安装（一次性）

```bash
git clone -b claude/mistake-mastery-product-6xj6q4 https://github.com/tianbao424/Claude-made-stock-bot.git
cd Claude-made-stock-bot/mistake-mastery
uv sync
uv run playwright install chromium
cd web
npm install
npm run build
cd ..
```

- `-b claude/mistake-mastery-product-6xj6q4`：代码现在还在这个分支上。合并进主分支之后，去掉这一段即可。
- `uv sync` 第一次会自动下载 Python 3.11+ 和依赖，要几分钟。
- `playwright install chromium` 下载生成 PDF 用的浏览器内核（约 150 MB）。

**下载很慢或失败（国内网络常见）**：

| 卡在哪一步 | 办法 |
|------------|------|
| `uv sync` 下载 Python 失败 | 先从 python.org 装 Python 3.12（Windows 安装时勾选"Add python.exe to PATH"），uv 会直接用它 |
| `uv sync` 下载依赖很慢 | 临时用镜像：Mac 运行 `UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/ uv sync`；Windows 先运行 `$env:UV_DEFAULT_INDEX="https://mirrors.aliyun.com/pypi/simple/"` 再 `uv sync`。这会改动 `uv.lock`，以后升级前先运行 `git checkout uv.lock` |
| `npm install` 很慢 | 先运行 `npm config set registry https://registry.npmmirror.com` |
| `playwright install chromium` 失败 | 可以跳过，改用电脑上的 Chrome：第 4 步在 `.env` 里填 `XT_CHROMIUM_PATH`（Mac：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`；Windows：`C:/Program Files/Google/Chrome/Application/chrome.exe`） |

---

## 4. 填写配置

还在 `mistake-mastery` 目录里：

```bash
cp .env.example .env                          # Windows 用：copy .env.example .env
uv run python -m app.tools.hash_password      # 设置家庭密码（至少 12 位，输入时不显示）
```

第二条命令会输出一行 `XT_FAMILY_PASSWORD_HASH=scrypt$...`，复制下来。然后打开 `.env`（Mac：`open -e .env`；Windows：`notepad .env`），至少填写：

- `XT_DATA_DIR`：第 2 步数据仓库的位置。Mac 例如 `/Users/你的用户名/xuetou-data`；Windows 例如 `C:/Users/你的用户名/xuetou-data`（**用正斜杠 /**）
- `XT_FAMILY_PASSWORD_HASH`：把这一行换成刚才复制的那一行
- `XT_DASHSCOPE_API_KEY`：阿里云百炼（通义千问）控制台 → API-KEY，需要实名认证
  - **改用小米 MiMo**：不填上面这一项，改成填 `XT_MIMO_API_KEY=tp-...`（小米 MiMo 开放平台 Token Plan 的密钥；`.env` 是早先复制的、里面没有这一行的，自己加一行），只填了 MiMo 的密钥时自动用 MiMo（两家都填了还想用 MiMo，再加一行 `XT_MODEL_PRESET=mimo`）。默认连 Token Plan 中国区的地址 `https://token-plan-cn.xiaomimimo.com/v1`；按量付费的账号在 `XT_MIMO_BASE_URL` 里改成控制台给的地址。识别、切题、解答用 `mimo-v2.6-flash`，讲解用 `mimo-v2.6-pro`（两个都能看图；旧的 `mimo-v2.5` 系列 2026 年 10 月 21 日停用）；型号以控制台为准，不对时在"我的 → 模型"里改
  - **改用 DeepSeek**：填 `XT_DEEPSEEK_API_KEY=sk-...`（DeepSeek 开放平台 → API keys），连 `https://api.deepseek.com/v1`，各任务都用能看图的 `deepseek-flash`。同时填了别家的密钥时，再加一行 `XT_MODEL_PRESET=deepseek`（已经有 `XT_MODEL_PRESET=...` 这一行的，改掉它）
  - 填了几家时按 通义千问 → MiMo → DeepSeek 的顺序选；`XT_MODEL_PRESET` 写了就按写的。第 5 步的 `bakeoff --check` 会列出用的是哪家、平台上有哪些型号
- 擦除接口：先保持 `XT_ERASER=local_color`（本地算法，只能擦红笔、蓝笔等彩色笔迹；黑笔作答擦不掉），第 5 步试过之后再换成效果最好的一家。换过之后，已经录入的错题在详情页点"重新擦除这一页"就能用新设置重擦

`.env` 里有密钥，只留在这台电脑上，不要发给别人，也不要提交到任何仓库（代码仓库已经设置为忽略它）。

---

## 5. 第 0 步：用真实卷子试水

```bash
uv run python -m app.tools.bakeoff --check            # 检查大模型、擦除接口、GitHub 是否连得上
uv run python -m app.tools.bakeoff 卷子1.jpg 卷子2.jpg  # 比较各家擦除效果，并看识别切题准不准
```

准备 5–10 张孩子最近的卷子照片，最好包含**几何图上的辅助线、电路图、红笔批改**。运行后用浏览器打开 `bakeoff-out/index.html` 并排对比，选效果最好的擦除接口填进 `.env` 的 `XT_ERASER`。看完可以删掉 `bakeoff-out/`（里面是孩子的卷子）。

---

## 6. 启动

每次使用前，打开终端，进入代码目录启动（终端窗口不要关，关了程序就停了）：

```bash
cd Claude-made-stock-bot/mistake-mastery
uv run python -m app
```

终端会显示：

```
  学透已启动
  · 这台电脑上打开：http://localhost:8000
  · 手机连同一个 Wi-Fi 打开：http://192.168.1.23:8000
```

1. 手机连上同一个 Wi-Fi，用浏览器打开第二个地址，输入家庭密码。
2. Safari 里点"分享 → 添加到主屏幕"，以后就像 App 一样打开。
3. 第一次进入时建一个孩子档案（用昵称即可）。

**电脑上用**：在运行程序的这台电脑上打开 `http://localhost:8000`；家里其他电脑、平板用上面那个局域网地址。界面按手机设计，在电脑上显示为居中的一栏。

**手机打不开时**：确认手机和电脑在同一个 Wi-Fi；电脑防火墙允许 8000 端口的入站连接（Mac 首次运行时会弹窗询问，选"允许"；Windows 弹出"Windows 安全中心"时勾选"专用网络"并点"允许访问"）。电脑开着代理或 VPN 软件时，关掉它的"增强模式 / TUN 模式"再试；终端没显示手机地址的话，在系统设置 → Wi-Fi → 详细信息里看本机 IP。

**启动时提示 XT_DATA_DIR 有问题**：按提示改 `.env`。数据仓库和程序要**并排放**（例如 `~/xuetou-data` 和 `~/Claude-made-stock-bot`），不要一个套在另一个里面，也不要放在 iCloud 等网盘里。

**电脑别睡着**：电脑睡眠后手机就连不上了。插着电源时把自动睡眠关掉（Mac：系统设置 → 电池/节能 → 接通电源时防止自动进入睡眠；Windows：设置 → 系统 → 电源 → 接通电源时"从不"睡眠）。

---

## 7. 日常使用

| 做什么 | 在哪里 |
|--------|--------|
| 卷子发回来了 | 底部 ➕ 拍照 → 选学科、整页 → 拍照上传 → 等半分钟 → 批量确认（老师判错的题已经预选好） |
| 打印擦除后的整张卷子 | 打印 → 原卷还原 → 选卷子 → 生成 PDF → 手机上"分享 → 打印"，或者在电脑上打印 |
| 只打印错题 | 错题本 → 选题打印；或者打印 → 错题重做单 |
| 看哪些知识点没学透 | 首页"掌握死角"；或者错题本 → 按知识点看：每个考点的掌握度、最该补的考点和原因，点进去能一键打印这个考点没学透的题 |
| 给孩子讲一个薄弱知识点 | 点进这个知识点 → 生成讲解（约半分钟）：要点、方法、他自己容易错在哪、例题 → "打印 / 单独看"给孩子看或打印 → 看完点"重做 N 道错题"。讲解是 AI 写的，有拿不准的地方对照课本 |
| 孩子做完了 | 用手机相机扫 PDF 右下角的二维码 → 逐题点 ✓ ½ ✗ → 保存 |
| 看数据有没有同步 | 我的 → GitHub 数据同步（改动后约 2 分钟自动推送） |
| 拿到了真题或区统考的 PDF | 我的 → 题库 → 导入卷子：选学科、年份、地区、考试，传试卷和"答案及评分标准" → 每页约半分钟 → 看一眼标 ⚠ 的题 |
| 想先试试某份卷子导入效果 | `uv run python -m app.tools.bank_try 试卷.pdf --answers 答案.pdf`：在临时文件夹里用真实大模型导入一遍，不写进数据仓库；生成 `bank-try-out/…/report.txt`（每道题的页码、答案、要核对的）和 `index.html`（每道题的截图），有问题把 report.txt 和 raw.jsonl 发给开发者 |

**关于 AI 答案**：拍到的题如果在题库里，直接用官方答案并显示出处（见 [docs/10](docs/10-question-bank.md)）；否则卷面上有老师写的答案时直接采用；都没有时由 AI 解答，标"AI 解答 · 待核"。v0.1 只用一个模型解答，请对照答案页或问老师核对；两家模型交叉校验在 v0.2 加入。

---

## 8. 升级、换电脑、出问题

| 场景 | 做法 |
|------|------|
| 升级到新版本 | 停掉程序（终端里按 Ctrl+C），在 `mistake-mastery` 目录依次运行 `git pull`、`uv sync`、`cd web`、`npm install`、`npm run build`、`cd ..`，再启动 |
| 换电脑或电脑坏了 | 在新电脑上做第 1–4 步（第 2 步只需 clone 已有的数据仓库），启动时会自动从数据仓库恢复全部数据 |
| 数据库出问题 | `uv run python -m app.tools.rebuild_index`，从数据仓库重建 |
| GitHub 推送失败 | 提交会先留在本机，程序自动重试；"我的"页面能看到错误信息 |
| 提示"今天的 AI 额度用完了" | 达到 `.env` 里的每日费用上限，第二天自动恢复；需要时调高 `XT_DAILY_COST_CAP_CNY` |
| 擦除效果不好 | 换一家擦除接口；或者先用夸克扫描王的"试卷去手写"处理照片，再用"不擦除"（`none`）上传 |

---

## 9. 开发者备注

```bash
uv run pytest                             # 后端测试（PDF 测试需要 Chromium）
cd web && npm run dev                     # 前端开发服务器，/api 转发到 8000 端口
```

**预览版**（不需要后端、发给家人先看看的单个页面）：同一套页面，后端换成浏览器里的模拟（`web/src/demo/`），
示例数据用真实后端处理两张合成的卷子生成（AI 部分是固定结果），不含真实孩子的信息。

```bash
uv run python web/demo/make_fixtures.py   # 生成 web/demo/fixtures.json（需要 Chromium）
cd web && npm run build:demo              # 输出 web/dist-demo/preview.html，约 4 MB
```

代码结构见 [docs/03 §13](docs/03-system-architecture.md)。
