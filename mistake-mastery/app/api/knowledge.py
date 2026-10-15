"""知识点整理：掌握度地图、掌握死角、单个知识点的详情。"""

from fastapi import APIRouter, Depends

from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.api.mistakes import _summary
from app.context import AppContext
from app.curriculum import SUBJECTS
from app.models import BankItem, BankPaper, Mistake, Question, QuestionKp
from app.services import knowledge

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
        "blind_spots": knowledge.blind_spots(cur, subject, stats, bank),
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
    return out[:max(1, min(limit, 20))]


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

        # 题库里这个知识点（含下级）的题；孩子已经做错过的排在后面
        done = {(q.bank_match or {}).get("question_id") for q in s.query(Question).filter(
            Question.origin == "captured", Question.subject == kp.subject, Question.bank_match.isnot(None))}
        bank_rows = (s.query(QuestionKp, BankItem, BankPaper)
                     .join(BankItem, BankItem.question_id == QuestionKp.question_id)
                     .join(BankPaper, BankPaper.id == BankItem.paper_id)
                     .filter((QuestionKp.kp_code == code) | QuestionKp.kp_code.like(f"{code}.%")).all())
        seen, bank_questions = set(), []
        for k, item, paper in sorted(bank_rows, key=lambda r: (r[1].question_id in done, not r[0].is_primary,
                                                              -(r[2].year or 0), r[1].seq)):
            if item.question_id in seen:
                continue
            seen.add(item.question_id)
            bank_questions.append({"id": item.question_id, "paper_id": paper.id, "paper_title": paper.title,
                                   "number_label": item.number_label, "primary": bool(k.is_primary),
                                   "done": item.question_id in done})

        children = [knowledge.node_json(cur, c.code, stats.get(c.code), bank)
                    for c in cur.for_subject(kp.subject) if c.parent_code == code]
    return {
        **knowledge.node_json(cur, code, x, bank), "subject": kp.subject, "path": cur.path_name(code),
        "causes": [{"code": c, "name": names.get(c, c), "n": n} for c, n in (x.causes.most_common() if x else [])],
        "mistake_list": mistakes, "children": children, "bank_questions": bank_questions[:20],
    }
