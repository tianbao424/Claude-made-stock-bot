"""题库：导入卷子、查看和修改题目、录入时匹配的取消。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.api.capture import _image_response
from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.context import AppContext
from app.models import BankItem, BankPaper, Question, QuestionKp
from app.services import bank

router = APIRouter(prefix="/api", dependencies=LOGIN)


def _paper_dict(p: BankPaper) -> dict:
    return {"id": p.id, "subject": p.subject, "title": p.title, "year": p.year, "region": p.region,
            "exam_kind": p.exam_kind, "exam_kind_name": bank.EXAM_KINDS.get(p.exam_kind, p.exam_kind),
            "status": p.status, "error": p.error, "stats": p.stats or {}, "created_at": p.created_at,
            "files": [{"role": f["role"], "kind": f["kind"], "name": f.get("name"), "pages": f.get("pages")}
                      for f in p.files or []],
            "pages": [{"n": pg["n"], "role": pg["role"], "kind": pg.get("kind")} for pg in p.pages or []]}


def _question_dict(s, item: BankItem, q: Question) -> dict:  # noqa: ANN001
    kps = [k.kp_code for k in s.query(QuestionKp).filter_by(question_id=q.id)
           .order_by(QuestionKp.is_primary.desc(), QuestionKp.kp_code)]
    return {"id": q.id, "seq": item.seq, "number_label": item.number_label, "points": item.points,
            "pages": sorted({r["page"] for r in item.regions}), "type": q.question_type, "stem_md": q.stem_md,
            "options": q.options, "sub_questions": q.sub_questions, "answer": q.answer, "solution_md": q.solution_md,
            "answer_source": q.answer_source, "verification": q.verification, "needs_review": bank.needs_review(q),
            "kp_codes": kps, "bj_slot": q.bj_slot, "difficulty": q.difficulty}


@router.get("/bank/papers")
def list_papers(subject: str | None = None, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        qry = s.query(BankPaper)
        if subject:
            qry = qry.filter_by(subject=subject)
        return [_paper_dict(p) for p in qry.order_by(BankPaper.year.desc(), BankPaper.created_at.desc())]


@router.post("/bank/papers")
async def create_paper(
    subject: str = Form(...), title: str = Form(""), year: str = Form(""), region: str = Form(""),
    exam_kind: str = Form("other"), verify: bool = Form(True),
    paper_files: list[UploadFile] = File(...), answer_files: list[UploadFile] | None = File(None),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    papers = [(f.filename or "", await f.read()) for f in paper_files]
    answers = [(f.filename or "", await f.read()) for f in answer_files or [] if f.filename]
    try:
        paper_id, job_id = bank.create_paper(
            ctx, subject=subject, title=title, year=int(year) if year.strip().isdigit() else None,
            region=region.strip() or None, exam_kind=exam_kind, paper_files=papers, answer_files=answers,
            verify=verify)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return {"paper_id": paper_id, "job_id": job_id}


@router.get("/bank/papers/{paper_id}")
def get_paper(paper_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        p = s.get(BankPaper, paper_id)
        if p is None:
            raise not_found("卷子")
        rows = (s.query(BankItem, Question).join(Question, BankItem.question_id == Question.id)
                .filter(BankItem.paper_id == paper_id).order_by(BankItem.seq).all())
        return {**_paper_dict(p), "questions": [_question_dict(s, item, q) for item, q in rows]}


class PaperPatch(BaseModel):
    title: str | None = None
    year: int | None = None
    region: str | None = None
    exam_kind: str | None = None


@router.patch("/bank/papers/{paper_id}")
def patch_paper(paper_id: str, body: PaperPatch, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        p = s.get(BankPaper, paper_id)
        if p is None:
            raise not_found("卷子")
        if body.title is not None and body.title.strip():
            p.title = body.title.strip()[:100]
        if body.year is not None:
            p.year = body.year
        if body.region is not None:
            p.region = body.region or None
        if body.exam_kind in bank.EXAM_KINDS:
            p.exam_kind = body.exam_kind
        return _paper_dict(p)


@router.delete("/bank/papers/{paper_id}")
def delete_paper(paper_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        bank.delete_paper(ctx, paper_id)
    except ValueError as exc:
        raise not_found("卷子") from exc
    return {"ok": True}


@router.post("/bank/papers/{paper_id}/reimport")
def reimport(paper_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    """重新识别整套卷子（换了模型、或上次识别出错时用）。家长改过的答案会丢失。"""
    with ctx.db.session() as s:
        p = s.get(BankPaper, paper_id)
        if p is None:
            raise not_found("卷子")
        if p.status == "processing":
            raise bad_request("正在处理中")
        p.status = "processing"
    return {"job_id": ctx.jobs.submit("bank_import", {"paper_id": paper_id, "verify": True})}


@router.post("/bank/papers/{paper_id}/verify")
def verify(paper_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    """继续 AI 核对（上次因为每日费用上限暂停，或者导入时没勾选核对）。"""
    with ctx.db.session() as s:
        if s.get(BankPaper, paper_id) is None:
            raise not_found("卷子")
    return {"job_id": ctx.jobs.submit("bank_verify", {"paper_id": paper_id})}


class BankQuestionPatch(BaseModel):
    answer: str | None = None
    solution_md: str | None = None
    reviewed: bool | None = None
    kp_codes: list[str] | None = None


@router.patch("/bank/questions/{question_id}")
def patch_question(question_id: str, body: BankQuestionPatch, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        item = s.get(BankItem, question_id)
        q = s.get(Question, question_id)
        if item is None or q is None:
            raise not_found("题目")
        if body.answer is not None:
            q.answer = {"final": body.answer.strip()} if body.answer.strip() else None
            q.answer_source = "manual" if body.answer.strip() else "none"
        if body.solution_md is not None:
            q.solution_md = body.solution_md or None
        if body.reviewed is not None or body.answer is not None:
            v = dict(q.verification or {})
            v["reviewed"] = True if body.answer is not None else bool(body.reviewed)
            q.verification = v
        if body.kp_codes is not None:
            s.query(QuestionKp).filter_by(question_id=q.id).delete()
            for n, code in enumerate(dict.fromkeys(body.kp_codes)):
                if code in ctx.curriculum.kps:
                    s.add(QuestionKp(question_id=q.id, kp_code=code, is_primary=int(n == 0)))
        s.flush()
        bank.refresh_stats(s, s.get(BankPaper, item.paper_id))
        out = _question_dict(s, item, q)
    ctx.bank_index.invalidate()
    return out


@router.get("/bank/papers/{paper_id}/pages/{n}/image")
def page_img(paper_id: str, n: int, max_side: int = 1600, ctx: AppContext = Depends(get_ctx)):
    with ctx.db.session() as s:
        p = s.get(BankPaper, paper_id)
        pg = next((x for x in (p.pages if p else []) or [] if x["n"] == n), None)
        if p is None or pg is None:
            raise not_found("页面")
        img = bank.page_image(ctx, p.id, p.files, pg)
        return _image_response(img, f"bank:{paper_id}:{n}", min(max_side, 3000))


@router.get("/bank/questions/{question_id}/image")
def question_img(question_id: str, max_side: int = 1400, ctx: AppContext = Depends(get_ctx)):
    with ctx.db.session() as s:
        item = s.get(BankItem, question_id)
        if item is None:
            raise not_found("题目")
        p = s.get(BankPaper, item.paper_id)
        try:
            img = bank.question_image(ctx, p, item.regions)
        except ValueError as exc:
            raise not_found("题目截图") from exc
        return _image_response(img, f"bankq:{question_id}:{item.regions}", min(max_side, 3000))


class MatchAction(BaseModel):
    action: str  # reject


@router.post("/questions/{question_id}/bank-match")
def bank_match(question_id: str, body: MatchAction, ctx: AppContext = Depends(get_ctx)) -> dict:
    """录入时自动对上的题库题目不对：取消匹配。"""
    if body.action != "reject":
        raise bad_request("action 只能是 reject")
    try:
        return bank.reject_match(ctx, question_id)
    except ValueError as exc:
        raise not_found("题目") from exc
