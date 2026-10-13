"""生成预览版（纯前端演示）用的示例数据。

用真实后端（AI 部分换成固定的模拟结果）处理两张合成的卷子照片，把接口返回的 JSON、
题目截图和生成的 PDF 页面打包成 web/demo/fixtures.json，供 `npm run build:demo` 使用。
全部是合成数据，不含任何真实孩子的信息。

运行：uv run python web/demo/make_fixtures.py（在 mistake-mastery 目录下）
"""

import base64
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz  # pymupdf
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

HERE = Path(__file__).parent
FONT = os.environ.get("XT_DEMO_FONT", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
PEN = (20, 30, 120)
RED = (225, 20, 20)


def _fonts():
    return ImageFont.truetype(FONT, 34), ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 30)


def _photo(paper: Image.Image, angle: float) -> bytes:
    photo = Image.new("RGB", (1500, 2050), (70, 60, 55))
    photo.paste(paper.rotate(angle, expand=True, fillcolor=(70, 60, 55)), (90, 100))
    buf = io.BytesIO()
    photo.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _cross(d: ImageDraw.ImageDraw, x: int, y: int) -> None:
    d.line([(x, y), (x + 100, y + 100)], fill=RED, width=7)
    d.line([(x + 100, y), (x, y + 100)], fill=RED, width=7)


def math_page() -> bytes:
    big, mid, hand = _fonts()
    W, H = 1240, 1754
    paper = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(paper)
    d.text((240, 40), "2026 海淀区九年级第一学期期中练习 · 数学", font=big, fill="black")
    d.text((80, int(0.08 * H) + 10), "1. 已知二次函数 y = x² - 2x，下列说法正确的是（　）", font=mid, fill="black")
    for i, t in enumerate(["A. 图象开口向下", "B. 对称轴是直线 x = 1", "C. 顶点坐标是 (1, 1)", "D. 与 y 轴交点为 (0, 2)"]):
        d.text((110, int(0.08 * H) + 54 + 44 * i), t, font=mid, fill="black")
    d.text((80, int(0.38 * H) + 10), "2. 如图，在△ABC 中，AB = AC，点 D、E 在 BC 上，", font=mid, fill="black")
    d.text((110, int(0.38 * H) + 54), "且 BD = CE。求证：AD = AE。", font=mid, fill="black")
    ax, ay = 860, int(0.38 * H) + 120
    d.polygon([(ax + 140, ay), (ax, ay + 220), (ax + 280, ay + 220)], outline="black", width=3)
    for label, (x, y) in {"A": (ax + 130, ay - 36), "B": (ax - 30, ay + 210), "C": (ax + 286, ay + 210)}.items():
        d.text((x, y), label, font=mid, fill="black")
    d.text((80, int(0.66 * H) + 10), "3. 计算：√12 - √3 = ______", font=mid, fill="black")
    d.text((560, int(0.08 * H) + 10), "A", font=hand, fill=PEN)
    d.text((110, int(0.38 * H) + 120), "证明：∵ AB = AC  ∴ ∠B = ∠C …", font=hand, fill=PEN)
    d.line([(ax + 140, ay), (ax + 140, ay + 220)], fill=PEN, width=3)
    d.text((440, int(0.66 * H) + 6), "√3", font=hand, fill=PEN)
    _cross(d, 1000, int(0.08 * H) + 60)
    _cross(d, 1000, int(0.38 * H) + 60)
    d.text((1100, int(0.66 * H)), "✓", font=big, fill=RED)
    return _photo(paper, 2)


def physics_page() -> bytes:
    big, mid, hand = _fonts()
    W, H = 1240, 1754
    paper = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(paper)
    d.text((300, 40), "九年级 10 月月考 · 物理", font=big, fill="black")
    d.text((80, int(0.08 * H) + 10), "1. 下列家用电器中，利用电流热效应工作的是（　）", font=mid, fill="black")
    for i, t in enumerate(["A. 电风扇", "B. 电视机", "C. 电饭锅", "D. 洗衣机"]):
        d.text((110 + 260 * i, int(0.08 * H) + 60), t, font=mid, fill="black")
    top = int(0.30 * H)
    d.text((80, top + 10), "2. 如图所示电路，电源电压保持 6V 不变，闭合开关 S，将滑动变阻器", font=mid, fill="black")
    d.text((110, top + 54), "的滑片 P 向右移动时，电流表示数______，电压表示数______。", font=mid, fill="black")
    # 电路图：电源、开关、定值电阻 R1、滑动变阻器 R2、电流表 A、电压表 V
    x0, y0, x1, y1 = 300, top + 140, 900, top + 420
    d.rectangle([x0, y0, x1, y1], outline="black", width=3)
    d.rectangle([450, y0 - 18, 560, y0 + 18], fill="white", outline="black", width=3)
    d.text((480, y0 - 60), "R₁", font=mid, fill="black")
    d.rectangle([650, y0 - 18, 790, y0 + 18], fill="white", outline="black", width=3)
    d.text((700, y0 - 60), "R₂", font=mid, fill="black")
    d.line([(720, y0 - 50), (720, y0 - 20)], fill="black", width=3)
    d.text((732, y0 - 56), "P", font=mid, fill="black")
    d.ellipse([x1 - 30, (y0 + y1) // 2 - 30, x1 + 30, (y0 + y1) // 2 + 30], fill="white", outline="black", width=3)
    d.text((x1 - 10, (y0 + y1) // 2 - 16), "A", font=mid, fill="black")
    d.line([(500, y1 + 0), (500, y1)], fill="black")
    d.rectangle([560, y1 - 30, 580, y1 + 30], fill="white", outline="white")
    d.line([(560, y1 - 30), (560, y1 + 30)], fill="black", width=4)
    d.line([(580, y1 - 16), (580, y1 + 16)], fill="black", width=4)
    d.ellipse([480, y0 + 100, 540, y0 + 160], fill="white", outline="black", width=3)
    d.text((500, y0 + 114), "V", font=mid, fill="black")
    d.line([(450, y0), (450, y0 + 130), (480, y0 + 130)], fill="black", width=3)
    d.line([(540, y0 + 130), (560, y0 + 130), (560, y0)], fill="black", width=3)
    d.text((x0 - 50, (y0 + y1) // 2 - 16), "S", font=mid, fill="black")
    d.text((200, top + 250), "变大", font=hand, fill=PEN)
    d.text((960, top + 250), "变大", font=hand, fill=PEN)
    d.line([(560, y0 + 18), (600, y0 + 90)], fill=PEN, width=3)  # 孩子画的电流方向
    d.text((80, int(0.62 * H) + 10), "3. 一个标有“220V 1100W”的电热水壶正常工作 5min，求：", font=mid, fill="black")
    d.text((110, int(0.62 * H) + 54), "(1) 通过它的电流；(2) 消耗的电能。", font=mid, fill="black")
    d.text((110, int(0.62 * H) + 120), "I = P/U = 1100W ÷ 220V = 5A", font=hand, fill=PEN)
    d.text((110, int(0.62 * H) + 170), "W = Pt = 1100W × 300s = 3.3×10⁵ J", font=hand, fill=PEN)
    _cross(d, 1000, int(0.08 * H) + 40)
    _cross(d, 1040, top + 150)
    d.text((1100, int(0.62 * H)), "✓", font=big, fill=RED)
    return _photo(paper, -1.5)


MATH = {
    "header": "2026 海淀区九年级第一学期期中练习 · 数学",
    "questions": [
        {"number_label": "1", "bbox": [55, 80, 950, 360], "question_type": "choice_single",
         "stem_md": "已知二次函数 $y=x^2-2x$，下列说法正确的是（　）",
         "options": [{"key": "A", "md": "图象开口向下"}, {"key": "B", "md": "对称轴是直线 $x=1$"},
                     {"key": "C", "md": "顶点坐标是 $(1,1)$"}, {"key": "D", "md": "与 $y$ 轴交点为 $(0,2)$"}],
         "grading": "wrong", "student_answer": "A", "teacher_answer": None, "has_figure": False},
        {"number_label": "2", "bbox": [55, 380, 950, 640], "question_type": "solve",
         "stem_md": "如图，在 $\\triangle ABC$ 中，$AB=AC$，点 $D$、$E$ 在 $BC$ 上，且 $BD=CE$。求证：$AD=AE$。",
         "grading": "partial", "score_text": "3/6", "student_answer": "证明：∵ AB = AC ∴ ∠B = ∠C …",
         "teacher_answer": "证 △ABD ≌ △ACE（SAS），得 AD = AE", "has_figure": True},
        {"number_label": "3", "bbox": [55, 660, 950, 940], "question_type": "fill",
         "stem_md": "计算：$\\sqrt{12}-\\sqrt{3}=$______", "grading": "right", "student_answer": "√3"},
    ]}
PHYSICS = {
    "header": "九年级 10 月月考 · 物理",
    "questions": [
        {"number_label": "1", "bbox": [55, 80, 950, 280], "question_type": "choice_single",
         "stem_md": "下列家用电器中，利用电流热效应工作的是（　）",
         "options": [{"key": "A", "md": "电风扇"}, {"key": "B", "md": "电视机"}, {"key": "C", "md": "电饭锅"},
                     {"key": "D", "md": "洗衣机"}],
         "grading": "wrong", "student_answer": "A", "has_figure": False},
        {"number_label": "2", "bbox": [55, 300, 950, 600], "question_type": "experiment",
         "stem_md": "如图所示电路，电源电压保持 $6\\,\\text{V}$ 不变，闭合开关 S，将滑动变阻器的滑片 P 向右移动时，"
                    "电流表示数______，电压表示数______。（选填“变大”“变小”或“不变”）",
         "grading": "wrong", "student_answer": "变大；变大", "has_figure": True},
        {"number_label": "3", "bbox": [55, 610, 950, 900], "question_type": "calc",
         "stem_md": "一个标有“220V 1100W”的电热水壶正常工作 5min，求：",
         "sub_questions": [{"no": "(1)", "md": "通过它的电流；"}, {"no": "(2)", "md": "消耗的电能。"}],
         "grading": "right", "student_answer": "5A；3.3×10⁵ J", "teacher_answer": "5 A；$3.3\\times10^5$ J"},
    ]}
CLASSIFY = {
    "math": {"1": (["M.FUN.QUAD.GRAPH"], "math.q8.choice_final", 2, ["CONCEPT"]),
             "2": (["M.GEO.TRI.CONG", "M.GEO.TRI.ISO"], "math.basic_calc", 3, ["RIGOR"]),
             "3": (["M.NUM.RAD.OPS"], "math.basic_calc", 1, [])},
    "physics": {"1": (["P.ELEC.POWER.JOULE"], "physics.single_choice", 1, ["CONCEPT"]),
                "2": (["P.ELEC.OHM.DYNAMIC", "P.ELEC.UIR.METER"], "physics.experiment", 3, ["P_CIRCUIT"]),
                "3": (["P.ELEC.POWER.CALC"], "physics.calc", 2, [])},
}
SOLVE = {
    "二次函数": ("B", "$y=x^2-2x=(x-1)^2-1$，开口向上，对称轴为直线 $x=1$，顶点 $(1,-1)$，与 $y$ 轴交于 $(0,0)$。故选 B。"),
    "热效应": ("C", "电饭锅把电能转化为内能，利用电流的热效应。电风扇、洗衣机主要转化为机械能，电视机主要转化为光能和声能。故选 C。"),
    "滑动变阻器": ("变小；变小",
                 "R₁ 与 R₂ 串联，电压表测 R₁ 两端电压。滑片向右移动，R₂ 接入电阻变大，总电阻变大，"
                 "由 $I=U/R$ 知电流变小；R₁ 两端电压 $U_1=IR_1$ 变小。"),
    "计算：": ("$\\sqrt{3}$", "$\\sqrt{12}=2\\sqrt{3}$，所以 $2\\sqrt{3}-\\sqrt{3}=\\sqrt{3}$。"),
}


def fake_llm(task: str, messages: list[dict]):
    text = json.dumps(messages, ensure_ascii=False)
    physics = "初三物理" in text or "初中物理" in text
    if task == "recognize":
        return PHYSICS if physics else MATH
    if task == "classify":
        rows = json.loads(messages[-1]["content"].split("【题目】")[1].split("对每道题输出")[0])
        table = CLASSIFY["physics" if physics else "math"]
        items = []
        for r in rows:
            kps, slot, diff, causes = table.get(r["number_label"], ([], None, 3, []))
            items.append({"id": r["id"], "kp_codes": kps, "bj_slot": slot, "difficulty": diff, "error_causes": causes})
        return {"items": items}
    if task == "solve":
        for key, (ans, sol) in SOLVE.items():
            if key in text:
                return {"final_answer": ans, "solution_md": sol, "confidence": 0.86}
        return {"final_answer": "（示例）", "solution_md": "（示例解答）", "confidence": 0.5}
    raise AssertionError(task)


def data_url(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def jpeg_url(raw: bytes, max_side: int, quality: int = 72) -> str:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return data_url(buf.getvalue(), "image/jpeg")


def pdf_pages(pdf: bytes) -> list[str]:
    out = []
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=100)
            out.append(jpeg_url(pix.tobytes("png"), 1200, 66))
    return out


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(tmp / "remote.git")], check=True)
    subprocess.run(["git", "clone", "-q", str(tmp / "remote.git"), str(tmp / "data")], check=True,
                   capture_output=True)
    settings = Settings(_env_file=None, data_dir=tmp / "data", family_password="demo", jobs_inline=True,
                        eraser="local_color", sync_debounce_seconds=3600,
                        chromium_path=os.environ.get("XT_CHROMIUM_PATH", ""))
    app = create_app(settings, start_background=False)
    app.state.ctx.llm.fake = fake_llm
    fx: dict = {"images": {}, "pdf": {}}
    with TestClient(app) as c:
        assert c.post("/api/login", json={"password": "demo"}).status_code == 200
        st = c.post("/api/students", json={"name": "小雨", "district": "haidian",
                                           "textbooks": {"math": "rjb", "physics": "rjb"}}).json()
        sid = st["id"]
        c.post(f"/api/students/{sid}/exams", json={"name": "期中", "kind": "midterm", "exam_date": "2026-11-04"})
        c.post(f"/api/students/{sid}/exams", json={"name": "期末", "kind": "final", "exam_date": "2027-01-13"})

        def upload(subject: str, kind: str, raw: bytes) -> str:
            r = c.post("/api/captures", data={"student_id": sid, "subject": subject, "mode": "page",
                                              "source_kind": kind},
                       files=[("files", ("page.jpg", raw, "image/jpeg"))]).json()
            assert c.get(f"/api/jobs/{r['job_id']}").json()["status"] == "done"
            return r["document_id"]

        phys = upload("physics", "monthly", physics_page())
        pc = c.get(f"/api/documents/{phys}/candidates").json()["items"]
        c.post(f"/api/documents/{phys}/confirm", json={"items": [
            {"instance_id": i["instance_id"], "selected": i["preselected"]} for i in pc]})
        pm = {m["number_label"]: m for m in c.get(f"/api/mistakes?student_id={sid}").json()}
        pj = c.post("/api/print-jobs", json={"student_id": sid, "template": "redo_sheet",
                                             "mistake_ids": [pm["1"]["id"], pm["2"]["id"]],
                                             "layout": {"with_key": True}}).json()["print_job_id"]
        c.post(f"/api/print-jobs/{pj}/results", json={"results": [{"seq": 1, "result": "correct"}]})
        fx["pdf"][pj] = pdf_pages(c.get(f"/api/print-jobs/{pj}/pdf").content)
        math_raw = math_page()
        fx["images"]["photo:math"] = jpeg_url(math_raw, 1200, 75)  # 预览版"用示例照片"上传的就是它
        math = upload("math", "midterm", math_raw)
        c.post("/api/sync")

        # 初始状态：物理月考已确认 2 道，数学期中待确认
        fx["student_id"] = sid
        fx["math_doc"], fx["phys_doc"] = math, phys
        fx["initial"] = {
            "students": c.get("/api/students").json(),
            "exams": c.get(f"/api/students/{sid}/exams").json(),
            "documents": {d: c.get(f"/api/documents/{d}").json() for d in (math, phys)},
            "candidates": {d: c.get(f"/api/documents/{d}/candidates").json() for d in (math, phys)},
            "mistakes": [c.get(f"/api/mistakes/{m['id']}").json() for m in c.get(f"/api/mistakes?student_id={sid}").json()],
            "print_jobs": [c.get(f"/api/print-jobs/{pj}").json()],
            "settings": c.get("/api/settings").json(),
            "sync": c.get("/api/sync/status").json(),
        }
        fx["curriculum"] = {s: c.get(f"/api/curriculum/{s}").json() for s in ("math", "physics")}
        for d in (math, phys):
            for p in fx["initial"]["documents"][d]["pages"]:
                for kind in ("corrected", "erased"):
                    fx["images"][f"page:{p['id']}:{kind}"] = jpeg_url(
                        c.get(f"/api/pages/{p['id']}/image?kind={kind}&max_side=1600").content, 1300, 70)
            for it in fx["initial"]["candidates"][d]["items"]:
                for kind in ("erased", "original"):
                    fx["images"][f"inst:{it['instance_id']}:{kind}"] = jpeg_url(
                        c.get(f"/api/instances/{it['instance_id']}/image?kind={kind}").content, 1000, 72)

        # 确认数学卷后的样子（三道题都确认，预览里勾哪几道就用哪几道）：错题详情和 PDF
        mc = fx["initial"]["candidates"][math]["items"]
        c.post(f"/api/documents/{math}/confirm", json={"items": [
            {"instance_id": i["instance_id"], "selected": True} for i in mc]})
        after = {m["instance_id"]: c.get(f"/api/mistakes/{m['id']}").json()
                 for m in c.get(f"/api/mistakes?student_id={sid}&subject=math").json()}
        fx["math_after_confirm"] = after
        # 错题重做单：预览里可能选到的每一种组合都事先生成好（按 redo_order 排列，带答案页）
        pool = [pm["1"], pm["2"]] + sorted(after.values(), key=lambda m: m["number_label"])
        fx["redo_order"] = [m["instance_id"] for m in pool]
        for r in range(1, len(pool) + 1):
            for combo in itertools.combinations(pool, r):
                rid = c.post("/api/print-jobs", json={"student_id": sid, "template": "redo_sheet",
                                                      "mistake_ids": [m["id"] for m in combo],
                                                      "layout": {"with_key": True}}).json()["print_job_id"]
                key = "redo:" + ",".join(sorted(m["instance_id"] for m in combo))
                fx["pdf"][key] = pdf_pages(c.get(f"/api/print-jobs/{rid}/pdf").content)
        for d in (math, phys):
            rj = c.post("/api/print-jobs", json={"student_id": sid, "template": "page_restore",
                                                 "document_id": d}).json()["print_job_id"]
            fx["pdf"][f"sample:page_restore:{d}"] = pdf_pages(c.get(f"/api/print-jobs/{rj}/pdf").content)
    out = HERE / "fixtures.json"
    out.write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
