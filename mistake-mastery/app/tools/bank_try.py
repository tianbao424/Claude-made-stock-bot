"""试导入一套卷子：用真实的大模型跑一遍题库导入，看切题准不准、答案对没对上，不动你的数据仓库。

用法（在 mistake-mastery 目录下）：
    uv run python -m app.tools.bank_try 试卷.pdf
    uv run python -m app.tools.bank_try 试卷.pdf --answers 答案.pdf --subject physics
    uv run python -m app.tools.bank_try 试卷.pdf --pages 1-3 --no-verify     # 只试前 3 页，不让 AI 核对，省钱

结果写到 bank-try-out/ 下的一个新文件夹：
- report.txt：每道题在哪几页、答案、要核对的地方、出错信息（可以直接发给开发者看）
- index.html：每道题的截图（单个文件，图片都在里面）
- raw.jsonl：每次调用大模型的返回结果（不含密钥），排查问题用
卷子导入在临时文件夹里进行，跑完就删掉，不会写进你的数据仓库。
"""

import argparse
import base64
import html
import io
import json
import shutil
import tempfile
import time
from pathlib import Path

import pypdfium2 as pdfium

from app.adapters import imaging
from app.config import Settings
from app.context import AppContext
from app.jobs import JobHandle
from app.models import AiCall, BankItem, BankPaper, Question
from app.services import bank
from app.tools.bakeoff import key_report


def _subset(data: bytes, pages: str | None) -> bytes:
    """--pages 1-3,5：只留这几页。"""
    if not pages:
        return data
    keep: list[int] = []
    for part in pages.split(","):
        a, _, b = part.strip().partition("-")
        keep += list(range(int(a), int(b or a) + 1))
    src = pdfium.PdfDocument(data)
    new = pdfium.PdfDocument.new()
    new.import_pages(src, [p - 1 for p in keep if 0 < p <= len(src)])
    buf = io.BytesIO()
    new.save(buf)
    return buf.getvalue()


def _guess_subject(name: str) -> str:
    return "physics" if "物理" in name or "physics" in name.lower() else "math"


def _page_count(name: str, data: bytes) -> int:
    try:
        return len(pdfium.PdfDocument(data)) if name.lower().endswith(".pdf") else 1
    except Exception:  # noqa: BLE001
        return 1


def run(paper: Path, answers: Path | None, subject: str, out_root: Path, *, pages: str | None = None,
        verify: bool = True, settings: Settings | None = None, fake=None) -> Path:  # noqa: ANN001
    """导入并写报告，返回报告所在的文件夹。settings / fake 给测试用。
    一边跑一边打印进度；中途按 Ctrl+C 会停下，已经拿到的结果照样写进报告。"""
    tmp = Path(tempfile.mkdtemp(prefix="xuetou-bank-try-"))
    out = out_root / f"{paper.stem[:40]}-{time.strftime('%m%d-%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    original_progress = JobHandle.progress

    def progress(self: JobHandle, stage: str, pct: int) -> None:
        original_progress(self, stage, pct)
        print(f"  {int(time.time() - started):4d} 秒  {pct:3d}%  {stage}", flush=True)

    JobHandle.progress = progress
    try:
        if settings is None:
            settings = Settings(data_dir=tmp, sync_enabled=False, jobs_inline=True)
        else:
            settings = settings.model_copy(update={"data_dir": tmp, "sync_enabled": False, "jobs_inline": True})
        ctx = AppContext(settings)
        bank.register(ctx)
        ctx.llm.fake = fake

        raw: list[dict] = []
        original = ctx.llm.chat_json

        def logged(task, messages, **kw):  # noqa: ANN001, ANN202
            t0 = time.time()
            try:
                result = original(task, messages, **kw)
            except Exception as exc:
                raw.append({"task": task, "seconds": round(time.time() - t0, 1), "error": str(exc)})
                print(f"                  ✗ AI 调用失败（{time.time() - t0:.0f} 秒）：{str(exc)[:200]}", flush=True)
                raise
            raw.append({"task": task, "seconds": round(time.time() - t0, 1), "output": result})
            print(f"                  AI 返回（{task}，{time.time() - t0:.0f} 秒）", flush=True)
            return result

        ctx.llm.chat_json = logged

        paper_files = [(paper.name, _subset(paper.read_bytes(), pages) if paper.suffix.lower() == ".pdf"
                        else paper.read_bytes())]
        answer_files = [(answers.name, answers.read_bytes())] if answers else []
        n = sum(_page_count(name, data) for name, data in paper_files + answer_files)
        print(f"开始导入：一共 {n} 页。AI 每看一页大约要半分钟到两分钟，请耐心等，下面会一直显示进度。\n"
              "中途按 Ctrl+C 会停下，已经拿到的结果照样写进报告。", flush=True)
        failure = ""
        pid = None
        try:
            pid, _ = bank.create_paper(ctx, subject=subject, title="", year=None, region=None, exam_kind="other",
                                       paper_files=paper_files, answer_files=answer_files, verify=verify)
        except KeyboardInterrupt:
            failure = "中途按 Ctrl+C 停下了，下面是停下前拿到的结果"
        except Exception as exc:  # noqa: BLE001 —— 失败原因也写进报告
            failure = f"{type(exc).__name__}: {exc}"
        seconds = time.time() - started

        lines: list[str] = []
        cards: list[str] = []
        with ctx.db.session() as s:
            spent = sum(c.cost_cny or 0 for c in s.query(AiCall))
            calls = s.query(AiCall).count()
            # 中途出错或停下时 create_paper 没有返回，临时数据库里只有这一套卷子
            p = s.get(BankPaper, pid) if pid else s.query(BankPaper).first()
            pid = p.id if p else None
            subj, title = ("物理" if subject == "physics" else "数学"), (p.title if p else paper.name)
            lines.append(f"== {title if subj in title else f'{title}（{subj}）'} ==")
            lines.append(f"文件：{paper.name}{f' + {answers.name}' if answers else ''}{f'（第 {pages} 页）' if pages else ''}")
            lines.append(f"模型：bank={ctx.llm.models.get('bank')}  classify={ctx.llm.models.get('classify')}"
                         f"  solve={ctx.llm.models.get('solve')}")
            lines.append(f"用时 {int(seconds // 60)} 分 {int(seconds % 60)} 秒；AI 调用 {calls} 次，估算费用 ¥{spent:.2f}")
            if failure or (p and p.status == "failed"):
                lines.append(f"❌ 没有导入完：{failure or p.error}")
            if p:
                kinds = {"questions": "试题", "answers": "答案", "mixed": "试题+答案", "other": "其他"}
                lines.append("页面：" + "  ".join(f"{pg['n']}{kinds.get(pg.get('kind'), '?')}" for pg in p.pages))
                st = p.stats or {}
                lines.append(f"题目 {st.get('questions', 0)} 道：有官方答案 {st.get('official', 0)}，"
                             f"没答案 {st.get('no_answer', 0)}，⚠ 待核对 {st.get('to_review', 0)}，"
                             f"还没核对 {st.get('unchecked', 0)}")
                if st.get("unmatched_answers"):
                    lines.append(f"没对上题号的答案：{st['unmatched_answers']}")
                if p.error:
                    lines.append("出错：" + p.error.replace("\n", "；"))
                lines.append("")
                rows = (s.query(BankItem, Question).join(Question, BankItem.question_id == Question.id)
                        .filter(BankItem.paper_id == pid).order_by(BankItem.seq).all())
                for item, q in rows:
                    pgs = sorted({r["page"] for r in item.regions})
                    ans = ((q.answer or {}).get("final") or "（没有）").replace("\n", " ")
                    notes = []
                    if (item.flags or {}).get("answer_in_crop"):
                        notes.append("截图里能看到答案")
                    if bank.needs_review(q):
                        notes.append(f"⚠ AI 解出 {((q.verification or {}).get('ai_answer') or '')[:30]}")
                    lines.append(f"  第 {item.number_label or '?'} 题  第 {'、'.join(map(str, pgs))} 页  "
                                 f"答案 {ans[:40]}{'  ' + '；'.join(notes) if notes else ''}")
                    try:
                        img = bank.question_image(ctx, p, item.regions)
                        b64 = base64.b64encode(imaging.encode_jpeg(imaging.resize_max(img, 1100)[0], 78)).decode()
                        pic = f"<img src='data:image/jpeg;base64,{b64}'>"
                    except Exception as exc:  # noqa: BLE001
                        pic = f"<p class='err'>截图失败：{html.escape(str(exc))}</p>"
                    cards.append(f"<section><h2>第 {html.escape(item.number_label or '?')} 题 · 第 {'、'.join(map(str, pgs))} 页"
                                 f"</h2><p>答案：{html.escape(ans)}{'　' + html.escape('；'.join(notes)) if notes else ''}"
                                 f"</p>{pic}</section>")
        report = "\n".join(lines) + "\n"
        (out / "report.txt").write_text(report, encoding="utf-8")
        (out / "raw.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw), encoding="utf-8")
        (out / "index.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>试导入</title><style>body{font:14px system-ui;margin:16px;"
            "max-width:900px}section{border-top:1px solid #ccc;padding:8px 0}h2{font-size:15px;margin:4px 0}"
            "img{max-width:100%;border:1px solid #c00}.err{color:#c00}pre{white-space:pre-wrap}</style>"
            f"<pre>{html.escape(report)}</pre>{''.join(cards)}", encoding="utf-8")
        print(report)
        return out
    finally:
        JobHandle.progress = original_progress
        try:
            ctx.db.dispose()  # type: ignore[possibly-undefined]
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    p = argparse.ArgumentParser(description="用真实的大模型试导入一套卷子（不动数据仓库）")
    p.add_argument("paper", type=Path, help="试卷 PDF（或一张照片）")
    p.add_argument("--answers", type=Path, help="答案及评分标准 PDF（答案就在试卷里的不用传）")
    p.add_argument("--subject", choices=["math", "physics"], help="不填就按文件名猜（含“物理”的算物理）")
    p.add_argument("--pages", help="只试这几页，例如 1-3 或 1,2,5")
    p.add_argument("--no-verify", action="store_true", help="不让 AI 独立解一遍核对答案（省钱）")
    args = p.parse_args()
    lines, usable = key_report(Settings())
    print("\n".join(lines))
    if not usable:
        raise SystemExit(1)
    out = run(args.paper, args.answers, args.subject or _guess_subject(args.paper.name), Path("bank-try-out"),
              pages=args.pages, verify=not args.no_verify)
    print(f"截图：用浏览器打开 {out.resolve() / 'index.html'}")
    print(f"把 {out / 'report.txt'} 和 {out / 'raw.jsonl'} 发给开发者就能看出哪里不对（里面没有密钥）。")


if __name__ == "__main__":
    main()
