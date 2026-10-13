# 学透 · 本地版安装与使用

本地版跑在家里的一台电脑上（Mac、Windows、Linux 都可以），手机连同一个 Wi-Fi，用浏览器访问。孩子的数据会自动同步到你自己的 **GitHub 私有仓库**。

> ⚠️ 代码所在的仓库是**公开的**。孩子的照片、错题、档案只放在**私有数据仓库**和本机上，不要放进代码仓库。

---

## 1. 准备软件（一次性）

| 软件 | 用途 | 安装 |
|------|------|------|
| Git | 下载代码、同步数据 | Mac：终端运行 `xcode-select --install`；Windows：安装 Git for Windows |
| uv | 管理 Python 环境 | 见 uv 官网的安装说明（一条命令） |
| Node.js 18+ | 构建手机上看到的网页（只在安装和升级时用） | Node.js 官网下载 LTS 版本 |

---

## 2. 建私有数据仓库（一次性）

1. 在 GitHub 新建仓库，名字例如 `xuetou-data`，**一定选 Private（私有）**，不要加协作者。
2. 给 GitHub 账号开启两步验证，并保存好恢复码。
3. 把它克隆到电脑上，例如：

```bash
git clone git@github.com:<你的账号>/xuetou-data.git ~/xuetou-data
```

这一步能成功，说明这台电脑已经有推送到 GitHub 的权限，程序之后会用同样的权限自动同步。

---

## 3. 下载代码并安装（一次性）

```bash
git clone https://github.com/tianbao424/Claude-made-stock-bot.git
cd Claude-made-stock-bot/mistake-mastery

uv sync                                   # 安装 Python 依赖
uv run playwright install chromium        # 生成 PDF 用的浏览器内核
cd web && npm install && npm run build && cd ..   # 构建网页
```

---

## 4. 填写配置

```bash
cp .env.example .env
uv run python -m app.tools.hash_password   # 设置家庭密码，把输出的一行粘贴到 .env
```

然后用文本编辑器打开 `.env`，至少填写：

- `XT_DATA_DIR`：第 2 步克隆的数据仓库路径，例如 `/Users/xxx/xuetou-data`
- `XT_FAMILY_PASSWORD_HASH`：上一步生成的那一行
- `XT_DASHSCOPE_API_KEY`：阿里云百炼（通义千问）的 API Key，需要实名认证
- 擦除接口：先保持 `XT_ERASER=local_color`（本地算法，只能擦红笔、蓝笔等彩色笔迹），第 5 步试过之后再换成效果最好的一家

---

## 5. 第 0 步：用真实卷子试水

```bash
uv run python -m app.tools.bakeoff --check            # 检查大模型、擦除接口、GitHub 是否连得上
uv run python -m app.tools.bakeoff 卷子1.jpg 卷子2.jpg  # 比较各家擦除效果，并看识别切题准不准
```

准备 5–10 张孩子最近的卷子照片，最好包含**几何图上的辅助线、电路图、红笔批改**。运行后用浏览器打开 `bakeoff-out/index.html` 并排对比，选效果最好的擦除接口填进 `.env` 的 `XT_ERASER`。看完可以删掉 `bakeoff-out/`（里面是孩子的卷子）。

---

## 6. 启动

```bash
uv run python -m app
```

终端会显示类似 `http://192.168.1.23:8000` 的地址：

1. 手机连上同一个 Wi-Fi，用浏览器打开这个地址，输入家庭密码。
2. Safari 里点"分享 → 添加到主屏幕"，以后就像 App 一样打开。
3. 第一次进入时建一个孩子档案（用昵称即可）。

**电脑上用**：在运行程序的这台电脑上打开 `http://localhost:8000`；家里其他电脑、平板用上面那个局域网地址。界面按手机设计，在电脑上显示为居中的一栏。

**手机打不开时**：确认手机和电脑在同一个 Wi-Fi；电脑防火墙允许 8000 端口的入站连接（Mac 首次运行时会弹窗询问，选"允许"）。

---

## 7. 日常使用

| 做什么 | 在哪里 |
|--------|--------|
| 卷子发回来了 | 底部 ➕ 拍照 → 选学科、整页 → 拍照上传 → 等半分钟 → 批量确认（老师判错的题已经预选好） |
| 打印擦除后的整张卷子 | 打印 → 原卷还原 → 选卷子 → 生成 PDF → 手机上"分享 → 打印"，或者在电脑上打印 |
| 只打印错题 | 错题本 → 选题打印；或者打印 → 错题重做单 |
| 孩子做完了 | 用手机相机扫 PDF 右下角的二维码 → 逐题点 ✓ ½ ✗ → 保存 |
| 看数据有没有同步 | 我的 → GitHub 数据同步（改动后约 2 分钟自动推送） |

**关于 AI 答案**：卷面上有老师写的答案时直接采用；没有时由 AI 解答，标"AI 解答 · 待核"。v0.1 只用一个模型解答，请对照答案页或问老师核对；两家模型交叉校验在 v0.2 加入。

---

## 8. 升级、换电脑、出问题

| 场景 | 做法 |
|------|------|
| 升级到新版本 | `git pull`，然后 `uv sync`，`cd web && npm install && npm run build`，再重启 |
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
