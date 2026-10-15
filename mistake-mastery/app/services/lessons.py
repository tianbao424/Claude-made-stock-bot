"""知识点讲解：AI 按孩子在这个知识点上的错题写一份讲解（要点、方法、易错点、例题、自查），见 docs/06 §6.2。

- 材料：孩子在这个知识点（含下级）上的错题（没学透的在前，最多 6 道，带孩子的作答、正确答案、错因），
  加上题库里有官方答案的同类题（最多 3 道）。讲解里的易错点和例题引用材料编号（M1、B1），页面上可以点过去。
- 每个孩子每个知识点存一份；又录入了这个知识点的错题时提示"可以重新生成"，不自动重写（要花钱）。
"""

from typing import TYPE_CHECKING

from app.adapters.llm import LLMError
from app.ids import now_iso
from app.jobs import JobHandle
from app.models import (Job, KpLesson, Mistake, Question, QuestionInstance, QuestionKp, SourceDocument, SourcePage,
                        Student)
from app.services import knowledge, mastery, prompts

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.context import AppContext

MAX_MISTAKES = 6
MAX_BANK = 3
OPEN_FIRST = {mastery.STUBBORN: 0, mastery.TO_REDO: 1, mastery.TO_TUTOR: 1, mastery.TO_VARIANT: 2,
              mastery.TO_REVIEW: 3, mastery.MASTERED: 4}
SOURCE_NAMES = {"official": "题库官方答案", "teacher": "老师写在卷面上的答案", "answer_key": "答案页",
                "manual": "家长填写", "ai_unverified": "AI 解答 · 待核", "ai_verified": "AI 解答 · 已交叉校验"}
LEVEL_NAMES = {"weak": "薄弱", "medium": "待加强", "good": "较好", "none": "暂无数据"}


def _clip(text: object, n: int) -> str:
    t = str(text or "").strip()
    return t if len(t) <= n else t[:n] + "……"


def kp_mistake_ids(s: "Session", student_id: str, code: str) -> set[str]:
    """孩子在这个知识点（含下级）上的全部错题。"""
    qids = s.query(QuestionKp.question_id).filter((QuestionKp.kp_code == code) | QuestionKp.kp_code.like(f"{code}.%"))
    return {m.id for m in s.query(Mistake).filter(Mistake.student_id == student_id, Mistake.question_id.in_(qids))}


def _mistake_label(s: "Session", m: Mistake) -> str:
    inst = s.get(QuestionInstance, m.first_instance_id) if m.first_instance_id else None
    page = s.get(SourcePage, inst.page_id) if inst else None
    doc = s.get(SourceDocument, page.document_id) if page else None
    title = (doc.title if doc else None) or "错题"
    return f"{title} · 第 {inst.number_label} 题" if inst and inst.number_label else title


def gather(ctx: "AppContext", s: "Session", student_id: str, code: str) -> tuple[list[dict], dict]:
    """写讲解用的材料（lesson_messages 的参数）和 basis（用到了哪些错题、编号对应什么）。"""
    cur = ctx.curriculum
    kp = cur.kps[code]
    student = s.get(Student, student_id)
    stats = knowledge.compute(s, cur, student_id, kp.subject)
    x = stats.get(code)
    causes = {c["code"]: c["name"] for c in cur.causes_for(kp.subject)}

    rows = []
    if x is not None:
        rows = s.query(Mistake, Question).join(Question, Mistake.question_id == Question.id).filter(
            Mistake.id.in_(x.mistakes)).all()
    rows.sort(key=lambda r: r[0].last_wrong_at, reverse=True)
    rows.sort(key=lambda r: (OPEN_FIRST.get(r[0].status, 5), -r[0].wrong_count))
    refs: dict[str, dict] = {}
    mistakes = []
    for n, (m, q) in enumerate(rows[:MAX_MISTAKES], start=1):
        inst = s.get(QuestionInstance, m.first_instance_id) if m.first_instance_id else None
        ref = f"M{n}"
        refs[ref] = {"kind": "mistake", "id": m.id, "label": _mistake_label(s, m)}
        mistakes.append({
            "编号": ref, "出处": refs[ref]["label"], "题型": q.question_type, "题干": _clip(q.stem_md, 800), "选项": q.options,
            "小问": q.sub_questions, "正确答案": (q.answer or {}).get("final") or "（暂无）",
            "答案来源": SOURCE_NAMES.get(q.answer_source, "暂无"), "解析": _clip(q.solution_md, 600) or None,
            "孩子的作答": ((inst.student_answer or {}).get("text") if inst else None) or "（没有记录）",
            "错因": [causes.get(c, c) for c in (m.error_causes or [])], "错了几次": m.wrong_count,
            "现在的状态": mastery.STATUS_NAMES.get(m.status, m.status),
        })

    bank = []
    for info, q in knowledge.similar_bank(s, code, kp.subject):
        if len(bank) >= MAX_BANK:
            break
        if not (q.answer or {}).get("final"):
            continue
        ref = f"B{len(bank) + 1}"
        label = f"{info['paper_title']} · 第 {info['number_label']} 题"
        refs[ref] = {"kind": "bank", "id": info["id"], "paper_id": info["paper_id"], "label": label}
        bank.append({"编号": ref, "出处": label, "题干": _clip(q.stem_md, 800), "选项": q.options,
                     "小问": q.sub_questions, "官方答案": q.answer["final"],
                     "评分标准": _clip(q.solution_md, 600) or None})

    score = x.mastery if x else None
    top_causes = [causes.get(c, c) for c, _ in x.causes.most_common(3)] if x else []
    textbook = (student.textbooks or {}).get(kp.subject) if student else None
    kp_info = {"name": kp.name, "path": cur.path_name(code), "textbook": prompts.TEXTBOOK_NAMES.get(textbook, "人教版"),
               "中考权重": kp.bj_weight}
    situation = {
        "掌握度": round(score * 100) if score is not None else "暂无数据",
        "等级": LEVEL_NAMES[knowledge.level_of(score)],
        "错题": len(x.mistakes) if x else 0, "没学透": len(x.open) if x else 0,
        "顽固错题": len(x.stubborn) if x else 0, "反复错": len(x.repeat) if x else 0, "主要错因": top_causes,
    }
    basis = {"mistake_ids": sorted(x.mistakes) if x else [], "refs": refs}
    return [kp.subject, kp_info, situation, mistakes, bank], basis


def _normalize(out: object, refs: dict) -> dict:
    """模型输出只留约定的字段，引用只留材料里有的编号。"""
    out = out if isinstance(out, dict) else {}

    def text(v: object, n: int = 2000) -> str:
        return str(v).strip()[:n] if v not in (None, "") else ""

    def items(v: object) -> list:
        return v if isinstance(v, list) else []

    key_points = [{"title": text(k.get("title"), 40), "md": text(k.get("md"))}
                  for k in items(out.get("key_points")) if isinstance(k, dict) and text(k.get("md"))][:5]
    method = [text(m, 600) for m in items(out.get("method")) if text(m)][:6]
    pitfalls = [{"title": text(p.get("title"), 40), "md": text(p.get("md")),
                 "refs": [r for r in items(p.get("refs")) if r in refs]}
                for p in items(out.get("pitfalls")) if isinstance(p, dict) and text(p.get("md"))][:5]
    ex = out.get("example")
    example = None
    if isinstance(ex, dict) and text(ex.get("question_md")) and text(ex.get("steps_md")):
        example = {"ref": ex.get("ref") if ex.get("ref") in refs else None, "question_md": text(ex["question_md"]),
                   "steps_md": text(ex["steps_md"], 3000), "answer": text(ex.get("answer"), 300)}
    self_check = [text(c, 200) for c in items(out.get("self_check")) if text(c)][:4]
    if not key_points and not method:
        raise LLMError("AI 没有写出讲解内容，请重新生成")
    return {"one_line": text(out.get("one_line"), 200), "key_points": key_points, "method": method,
            "pitfalls": pitfalls, "example": example, "self_check": self_check}


def generate_job(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    sid, code = payload["student_id"], payload["code"]
    handle.progress("整理这个知识点的错题", 10)
    with ctx.db.session() as s:
        args, basis = gather(ctx, s, sid, code)
    handle.progress("AI 正在写讲解", 30)
    out = ctx.llm.chat_json("lesson", prompts.lesson_messages(*args), prompt_version=prompts.LESSON_VERSION,
                            temperature=0.3, fresh=bool(payload.get("fresh")))
    content = _normalize(out, basis["refs"])
    with ctx.db.session() as s:
        row = s.query(KpLesson).filter_by(student_id=sid, kp_code=code).first()
        if row is None:
            row = KpLesson(student_id=sid, kp_code=code, content=content)
            s.add(row)
        row.content, row.basis = content, basis
        row.model = "fake" if ctx.llm.fake is not None else ctx.llm.models.get("lesson", "")
        row.prompt_version, row.created_at = prompts.LESSON_VERSION, now_iso()
    return {"kp_code": code}


def running_job(s: "Session", student_id: str, code: str) -> Job | None:
    for j in s.query(Job).filter(Job.kind == "kp_lesson", Job.status.in_(("queued", "running"))):
        if j.payload.get("student_id") == student_id and j.payload.get("code") == code:
            return j
    return None


def start(ctx: "AppContext", student_id: str, code: str, fresh: bool = False) -> str:
    """开始生成（已经在生成的话返回那个任务）。"""
    with ctx.db.session() as s:
        j = running_job(s, student_id, code)
        if j is not None:
            return j.id
    return ctx.jobs.submit("kp_lesson", {"student_id": student_id, "code": code, "fresh": fresh})


def lesson_json(s: "Session", student_id: str, code: str) -> dict | None:
    row = s.query(KpLesson).filter_by(student_id=student_id, kp_code=code).first()
    if row is None:
        return None
    new = kp_mistake_ids(s, student_id, code) - set((row.basis or {}).get("mistake_ids") or [])
    return {**row.content, "id": row.id, "created_at": row.created_at, "model": row.model,
            "refs": (row.basis or {}).get("refs") or {}, "new_mistakes": len(new)}


def lesson_codes(s: "Session", student_id: str) -> set[str]:
    return {code for (code,) in s.query(KpLesson.kp_code).filter_by(student_id=student_id)}


def register(ctx: "AppContext") -> None:
    ctx.jobs.register("kp_lesson", generate_job)
