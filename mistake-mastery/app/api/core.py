"""孩子档案、设置、知识点字典、任务进度、文件读取、同步状态、首页数据。"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func

from app.adapters.llm import default_models
from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.context import AppContext
from app.models import ExamEvent, Job, Mistake, PrintJob, SourceDocument, Student
from app.services.mastery import STATUS_NAMES

router = APIRouter(prefix="/api", dependencies=LOGIN)


# ---------------------------------------------------------------- 知识点与字典


def _tree(ctx: AppContext, subject: str) -> list[dict]:
    kps = ctx.curriculum.for_subject(subject)
    nodes = {k.code: {"code": k.code, "name": k.name, "level": k.level, "children": []} for k in kps}
    roots = []
    for k in kps:
        (nodes[k.parent_code]["children"] if k.parent_code else roots).append(nodes[k.code])
    return roots


@router.get("/curriculum/{subject}")
def curriculum(subject: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    if subject not in ("math", "physics"):
        raise not_found("学科")
    cur = ctx.curriculum
    return {
        "tree": _tree(ctx, subject),
        "names": {k.code: cur.path_name(k.code) for k in cur.for_subject(subject)},
        "error_causes": cur.causes_for(subject),
        "bj_slots": cur.slots_for(subject),
        "question_types": cur.question_types,
        "source_kinds": cur.source_kinds,
        "statuses": STATUS_NAMES,
    }


# ---------------------------------------------------------------- 孩子档案与考试日历


class StudentBody(BaseModel):
    name: str | None = None
    grade: int | None = None
    district: str | None = None
    textbooks: dict | None = None
    settings: dict | None = None


def _student_dict(st: Student) -> dict:
    return {"id": st.id, "name": st.name, "grade": st.grade, "district": st.district, "textbooks": st.textbooks,
            "settings": st.settings}


@router.get("/students")
def list_students(ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        return [_student_dict(st) for st in s.query(Student).order_by(Student.created_at)]


@router.post("/students")
def create_student(body: StudentBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    if not body.name:
        raise bad_request("请填写孩子的称呼")
    with ctx.db.session() as s:
        st = Student(name=body.name, grade=body.grade or 9, district=body.district,
                     textbooks=body.textbooks or {}, settings=body.settings or {})
        s.add(st)
        s.flush()
        return _student_dict(st)


@router.patch("/students/{student_id}")
def update_student(student_id: str, body: StudentBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        st = s.get(Student, student_id)
        if st is None:
            raise not_found("孩子档案")
        for k, v in body.model_dump(exclude_none=True).items():
            setattr(st, k, v)
        return _student_dict(st)


class ExamBody(BaseModel):
    name: str
    kind: str = "other"
    exam_date: str
    subjects: list[str] = ["math", "physics"]


@router.get("/students/{student_id}/exams")
def list_exams(student_id: str, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        rows = s.query(ExamEvent).filter_by(student_id=student_id).order_by(ExamEvent.exam_date)
        return [{"id": e.id, "name": e.name, "kind": e.kind, "exam_date": e.exam_date, "subjects": e.subjects}
                for e in rows]


@router.post("/students/{student_id}/exams")
def create_exam(student_id: str, body: ExamBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        e = ExamEvent(student_id=student_id, **body.model_dump())
        s.add(e)
        s.flush()
        return {"id": e.id}


@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        e = s.get(ExamEvent, exam_id)
        if e:
            s.delete(e)
    return {"ok": True}


# ---------------------------------------------------------------- 设置


class SettingsBody(BaseModel):
    models: dict[str, str] | None = None
    eraser: str | None = None


@router.get("/settings")
def get_settings(ctx: AppContext = Depends(get_ctx)) -> dict:
    return {
        "models": {**default_models(ctx.settings), **ctx.app_settings.get("models", {})},
        "eraser": ctx.app_settings.get("eraser") or ctx.settings.eraser,
        "erasers": ["local_color", "baidu", "youdao", "textin", "none"],
        "keys": {
            "qwen": bool(ctx.settings.dashscope_api_key), "doubao": bool(ctx.settings.ark_api_key),
            "deepseek": bool(ctx.settings.deepseek_api_key), "mimo": bool(ctx.settings.mimo_api_key),
            "baidu": bool(ctx.settings.baidu_api_key), "youdao": bool(ctx.settings.youdao_app_key),
            "textin": bool(ctx.settings.textin_app_id),
        },
        "spent_today": round(ctx.llm.spent_today(), 3),
        "daily_cap": ctx.settings.daily_cost_cap_cny,
    }


@router.patch("/settings")
def patch_settings(body: SettingsBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    patch = body.model_dump(exclude_none=True)
    if "models" in patch:
        patch["models"] = {**ctx.app_settings.get("models", {}), **patch["models"]}
    ctx.save_app_settings(patch)
    return get_settings(ctx)


# ---------------------------------------------------------------- 任务、文件、同步


@router.get("/jobs/{job_id}")
def get_job(job_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise not_found("任务")
        return {"id": j.id, "kind": j.kind, "status": j.status, "progress": j.progress, "result": j.result,
                "error": j.error}


@router.get("/files/{path:path}")
def get_file(path: str, ctx: AppContext = Depends(get_ctx)) -> FileResponse:
    try:
        if not ctx.storage.is_shareable(path) or not ctx.storage.exists(path):
            raise not_found("文件")
    except ValueError:
        raise not_found("文件") from None
    return FileResponse(ctx.storage.abspath(path), headers={"X-Robots-Tag": "noindex"})


@router.get("/sync/status")
def sync_status(ctx: AppContext = Depends(get_ctx)) -> dict:
    return ctx.sync.status()


@router.post("/sync")
def sync_now(ctx: AppContext = Depends(get_ctx)) -> dict:
    result = ctx.sync.sync_now()
    return {**result, "status": ctx.sync.status()}


# ---------------------------------------------------------------- 首页


@router.get("/today")
def today(student_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        counts = dict(s.query(Mistake.status, func.count()).filter_by(student_id=student_id).group_by(Mistake.status))
        pending_docs = [
            {"id": d.id, "title": d.title, "subject": d.subject, "status": d.status, "created_at": d.created_at}
            for d in s.query(SourceDocument).filter(SourceDocument.student_id == student_id,
                                                    SourceDocument.status.in_(("processing", "ready", "failed")))
            .order_by(SourceDocument.created_at.desc()).limit(10)
        ]
        recent_prints = [
            {"id": p.id, "title": p.title, "status": p.status, "created_at": p.created_at}
            for p in s.query(PrintJob).filter_by(student_id=student_id).order_by(PrintJob.created_at.desc()).limit(5)
        ]
        exams = [{"name": e.name, "exam_date": e.exam_date}
                 for e in s.query(ExamEvent).filter_by(student_id=student_id).order_by(ExamEvent.exam_date)]
    return {"counts": counts, "pending_documents": pending_docs, "recent_prints": recent_prints, "exams": exams,
            "status_names": STATUS_NAMES, "sync": ctx.sync.status()}
