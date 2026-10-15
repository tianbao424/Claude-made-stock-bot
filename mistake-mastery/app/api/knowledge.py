"""知识点整理：掌握度地图、掌握死角、单个知识点的详情。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.api.mistakes import _summary
from app.context import AppContext
from app.curriculum import SUBJECTS
from app.models import Mistake, Question
from app.services import knowledge, lessons

router = APIRouter(prefix="/api", dependencies=LOGIN)


def _leaf_codes(ctx: AppContext, subject: str) -> set[str]:
    kps = ctx.curriculum.for_subject(subject)
    parents = {k.parent_code for k in kps if k.parent_code}
    return {k.code for k in kps if k.code not in parents}


@router.get("/knowledge")
def overview(student_id: str, subject: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    if subject not in SUBJECTS:
        raise bad_request("不支持的学科")
    cur = ctx.curriculum
    with ctx.db.session() as s:
        stats = knowledge.compute(s, cur, student_id, subject)
        bank = knowledge.bank_rollup(cur, s, subject)
    leaf_codes = _leaf_codes(ctx, subject)
    leaves = [x for code, x in stats.items() if code in leaf_codes]
    levels = [knowledge.level_of(x.mastery) for x in leaves]
    roots = [x for code, x in stats.items() if cur.kps[code].parent_code is None]
    return {
        "subject": subject,
        "summary": {
            "points": len(leaves), "weak": levels.count("weak"), "medium": levels.count("medium"),
            "good": levels.count("good"),
            "open": len(set().union(*(x.open for x in roots))) if roots else 0,
            "mastered": len(set().union(*(x.mastered for x in roots))) if roots else 0,
        },
        "blind_spots": _mark_lessons(ctx, student_id, knowledge.blind_spots(cur, subject, stats, bank)),
        "untouched": knowledge.untouched(cur, subject, stats, bank),
        "tree": knowledge.tree(cur, subject, stats, bank),
    }


@router.get("/knowledge/blind-spots")
def top_blind_spots(student_id: str, limit: int = 3, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    """首页用：两科合在一起最该补的几个考点。"""
    out = []
    with ctx.db.session() as s:
        for subject in SUBJECTS:
            stats = knowledge.compute(s, ctx.curriculum, student_id, subject)
            bank = knowledge.bank_rollup(ctx.curriculum, s, subject)
            out += knowledge.blind_spots(ctx.curriculum, subject, stats, bank, limit=limit)
    out.sort(key=lambda b: -b["risk"])
    return _mark_lessons(ctx, student_id, out[:max(1, min(limit, 20))])


def _mark_lessons(ctx: AppContext, student_id: str, spots: list[dict]) -> list[dict]:
    with ctx.db.session() as s:
        have = lessons.lesson_codes(s, student_id)
    return [{**b, "lesson": b["code"] in have} for b in spots]


@router.get("/knowledge/{code}")
def detail(code: str, student_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    cur = ctx.curriculum
    kp = cur.kps.get(code)
    if kp is None:
        raise not_found("知识点")
    with ctx.db.session() as s:
        stats = knowledge.compute(s, cur, student_id, kp.subject)
        bank = knowledge.bank_rollup(cur, s, kp.subject)
        x = stats.get(code)
        names = {c["code"]: c["name"] for c in cur.causes_for(kp.subject)}

        mistakes = []
        if x is not None:
            for m in s.query(Mistake).filter(Mistake.id.in_(x.mistakes)):
                mistakes.append(_summary(s, ctx, m, s.get(Question, m.question_id)))
        open_first = {"STUBBORN": 0, "TO_REDO": 1, "TO_TUTOR": 1, "TO_VARIANT": 2, "TO_REVIEW": 3, "MASTERED": 4}
        mistakes.sort(key=lambda d: d["last_wrong_at"], reverse=True)
        mistakes.sort(key=lambda d: open_first.get(d["status"], 5))

        bank_questions = [b for b, _ in knowledge.similar_bank(s, code, kp.subject)]
        children = [knowledge.node_json(cur, c.code, stats.get(c.code), bank)
                    for c in cur.for_subject(kp.subject) if c.parent_code == code]
    return {
        **knowledge.node_json(cur, code, x, bank), "subject": kp.subject, "path": cur.path_name(code),
        "causes": [{"code": c, "name": names.get(c, c), "n": n} for c, n in (x.causes.most_common() if x else [])],
        "mistake_list": mistakes, "children": children, "bank_questions": bank_questions,
    }


# ---------------------------------------------------------------- 知识点讲解


class LessonBody(BaseModel):
    student_id: str
    fresh: bool = False  # 重新生成：不用上次的缓存


@router.get("/knowledge/{code}/lesson")
def get_lesson(code: str, student_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    if code not in ctx.curriculum.kps:
        raise not_found("知识点")
    with ctx.db.session() as s:
        job = lessons.running_job(s, student_id, code)
        return {"lesson": lessons.lesson_json(s, student_id, code),
                "job": {"id": job.id, "status": job.status} if job else None}


@router.post("/knowledge/{code}/lesson")
def make_lesson(code: str, body: LessonBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    if code not in ctx.curriculum.kps:
        raise not_found("知识点")
    return {"job_id": lessons.start(ctx, body.student_id, code, fresh=body.fresh)}
