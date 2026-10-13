"""错题本：列表、详情、修改、回填作答结果。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.context import AppContext
from app.models import Attempt, Mistake, Question, QuestionInstance, QuestionKp, SourceDocument, SourcePage
from app.services import mastery

router = APIRouter(prefix="/api", dependencies=LOGIN)

RESULTS = ("correct", "wrong", "partial")


def _kps(s, question_id: str) -> list[str]:  # noqa: ANN001
    return [k.kp_code for k in s.query(QuestionKp).filter_by(question_id=question_id)
            .order_by(QuestionKp.is_primary.desc(), QuestionKp.kp_code)]


def _summary(s, ctx: AppContext, m: Mistake, q: Question) -> dict:  # noqa: ANN001
    inst = s.get(QuestionInstance, m.first_instance_id) if m.first_instance_id else None
    doc = None
    if inst:
        page = s.get(SourcePage, inst.page_id)
        doc = s.get(SourceDocument, page.document_id) if page else None
    kps = _kps(s, q.id)
    return {
        "id": m.id, "status": m.status, "status_name": mastery.STATUS_NAMES.get(m.status, m.status),
        "round": m.round, "wrong_count": m.wrong_count, "gates": m.gates, "error_causes": m.error_causes,
        "subject": q.subject, "question_type": q.question_type, "stem_md": q.stem_md,
        "answer_source": q.answer_source, "bj_slot": q.bj_slot, "difficulty": q.difficulty,
        "kp_codes": kps, "kp_names": [ctx.curriculum.path_name(c) for c in kps],
        "instance_id": inst.id if inst else None, "number_label": inst.number_label if inst else None,
        "document": {"id": doc.id, "title": doc.title, "source_kind": doc.source_kind,
                     "exam_date": doc.exam_date} if doc else None,
        "last_wrong_at": m.last_wrong_at, "created_at": m.created_at, "next_review_at": m.next_review_at,
    }


@router.get("/mistakes")
def list_mistakes(student_id: str, subject: str | None = None, status: str | None = None, kp: str | None = None,
                  source_kind: str | None = None, min_wrong: int = 0, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        qry = (s.query(Mistake, Question).join(Question, Mistake.question_id == Question.id)
               .filter(Mistake.student_id == student_id))
        if subject:
            qry = qry.filter(Question.subject == subject)
        if status:
            qry = qry.filter(Mistake.status.in_(status.split(",")))
        if min_wrong:
            qry = qry.filter(Mistake.wrong_count >= min_wrong)
        if kp:
            qry = qry.filter(Question.id.in_(
                s.query(QuestionKp.question_id).filter(QuestionKp.kp_code.like(f"{kp}%"))))
        out = [_summary(s, ctx, m, q) for m, q in qry.order_by(Mistake.last_wrong_at.desc()).limit(500)]
        if source_kind:
            out = [o for o in out if o["document"] and o["document"]["source_kind"] == source_kind]
        return out


@router.get("/mistakes/{mistake_id}")
def get_mistake(mistake_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        m = s.get(Mistake, mistake_id)
        if m is None:
            raise not_found("错题")
        q = s.get(Question, m.question_id)
        out = _summary(s, ctx, m, q)
        out["question"] = {"id": q.id, "stem_md": q.stem_md, "options": q.options, "sub_questions": q.sub_questions,
                           "answer": q.answer, "solution_md": q.solution_md, "answer_source": q.answer_source,
                           "verification": q.verification}
        out["instances"] = [
            {"id": i.id, "page_id": i.page_id, "number_label": i.number_label,
             "student_answer": (i.student_answer or {}).get("text"), "grading": (i.grading_marks or {}).get("mark"),
             "score": (i.grading_marks or {}).get("score")}
            for i in s.query(QuestionInstance).filter_by(question_id=q.id, status="confirmed")]
        out["attempts"] = [
            {"id": a.id, "round": a.round, "context": a.context, "result": a.result, "graded_by": a.graded_by,
             "error_cause": a.error_cause, "note": a.note, "created_at": a.created_at}
            for a in s.query(Attempt).filter_by(mistake_id=m.id).order_by(Attempt.created_at)]
        return out


class MistakePatch(BaseModel):
    kp_codes: list[str] | None = None
    error_causes: list[str] | None = None
    answer: str | None = None
    solution_md: str | None = None
    stem_md: str | None = None


@router.patch("/mistakes/{mistake_id}")
def patch_mistake(mistake_id: str, body: MistakePatch, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        m = s.get(Mistake, mistake_id)
        if m is None:
            raise not_found("错题")
        q = s.get(Question, m.question_id)
        if body.kp_codes is not None:
            s.query(QuestionKp).filter_by(question_id=q.id).delete()
            for n, code in enumerate(dict.fromkeys(body.kp_codes)):
                if code not in ctx.curriculum.kps:
                    raise bad_request(f"未知的知识点：{code}")
                s.add(QuestionKp(question_id=q.id, kp_code=code, is_primary=int(n == 0)))
        if body.error_causes is not None:
            m.error_causes = body.error_causes
        if body.answer is not None:
            q.answer = {"final": body.answer.strip()} if body.answer.strip() else None
            q.answer_source = "manual" if body.answer.strip() else "none"
        if body.solution_md is not None:
            q.solution_md = body.solution_md
        if body.stem_md is not None:
            q.stem_md = body.stem_md
    return get_mistake(mistake_id, ctx)


class AttemptBody(BaseModel):
    result: str
    context: str = "redo"
    error_cause: str | None = None
    note: str | None = None
    print_job_id: str | None = None


def record_result(s, m: Mistake, body: AttemptBody) -> None:  # noqa: ANN001
    """记一次作答，并按状态机更新错题。"""
    if body.result not in RESULTS:
        raise bad_request("result 只能是 correct / wrong / partial")
    state = mastery.apply_print_result(mastery.read_state(m), body.result, mastery.MasteryConfig(), mastery.today())
    s.add(Attempt(mistake_id=m.id, question_id=m.question_id, round=m.round, context=body.context,
                  print_job_id=body.print_job_id, result=body.result, graded_by="guardian",
                  error_cause=body.error_cause, note=body.note))
    mastery.write_state(m, state)


@router.post("/mistakes/{mistake_id}/attempts")
def add_attempt(mistake_id: str, body: AttemptBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        m = s.get(Mistake, mistake_id)
        if m is None:
            raise not_found("错题")
        record_result(s, m, body)
    return get_mistake(mistake_id, ctx)


@router.post("/mistakes/{mistake_id}/solve")
def resolve(mistake_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    """重新请 AI 解答（会覆盖之前的 AI 答案，不会覆盖老师或家长填的答案）。"""
    with ctx.db.session() as s:
        m = s.get(Mistake, mistake_id)
        if m is None:
            raise not_found("错题")
        q = s.get(Question, m.question_id)
        if q.answer_source in ("teacher", "manual", "answer_key"):
            raise bad_request("这道题已有老师或家长给的答案")
        q.answer_source = "none"
        qid = q.id
    return {"job_id": ctx.jobs.submit("solve", {"question_id": qid})}


@router.delete("/mistakes/{mistake_id}")
def delete_mistake(mistake_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    """录错了可以删除（作答记录一并删除；git 历史里仍能找回）。"""
    with ctx.db.session() as s:
        m = s.get(Mistake, mistake_id)
        if m is None:
            raise not_found("错题")
        s.query(Attempt).filter_by(mistake_id=m.id).delete()
        for inst in s.query(QuestionInstance).filter_by(question_id=m.question_id, status="confirmed"):
            inst.status = "discarded"
        s.delete(m)
    return {"ok": True}
