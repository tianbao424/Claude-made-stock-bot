"""打印任务：创建、查看、下载 PDF、按打印单回填结果。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.api.mistakes import AttemptBody, record_result
from app.context import AppContext
from app.models import Mistake, PrintJob, PrintJobItem, QuestionInstance
from app.services import mastery, printing

router = APIRouter(prefix="/api", dependencies=LOGIN)


class PrintBody(BaseModel):
    student_id: str
    template: str
    document_id: str | None = None
    mistake_ids: list[str] | None = None
    layout: dict | None = None


def _job_dict(j: PrintJob) -> dict:
    return {"id": j.id, "template": j.template, "template_name": printing.TEMPLATES.get(j.template, j.template),
            "title": j.title, "status": j.status, "page_count": j.page_count, "error": j.error,
            "layout": j.layout, "created_at": j.created_at, "has_pdf": bool(j.pdf_path)}


@router.post("/print-jobs")
def create(body: PrintBody, request: Request, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        job_id, task_id = printing.create_print_job(
            ctx, student_id=body.student_id, template=body.template, base_url=str(request.base_url),
            document_id=body.document_id, mistake_ids=body.mistake_ids, layout=body.layout)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return {"print_job_id": job_id, "job_id": task_id}


@router.get("/print-jobs")
def list_jobs(student_id: str, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        rows = s.query(PrintJob).filter_by(student_id=student_id).order_by(PrintJob.created_at.desc()).limit(50)
        return [_job_dict(j) for j in rows]


@router.get("/print-jobs/{job_id}")
def get_job(job_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        j = s.get(PrintJob, job_id)
        if j is None:
            raise not_found("打印任务")
        out = _job_dict(j)
        items = []
        for it in s.query(PrintJobItem).filter_by(print_job_id=job_id).order_by(PrintJobItem.seq):
            m = s.get(Mistake, it.mistake_id) if it.mistake_id else None
            inst = s.get(QuestionInstance, it.instance_id) if it.instance_id else None
            items.append({"seq": it.seq, "page_no": it.page_no, "mistake_id": it.mistake_id,
                          "instance_id": it.instance_id, "page_id": it.page_id,
                          "number_label": inst.number_label if inst else None,
                          "status": m.status if m else None,
                          "status_name": mastery.STATUS_NAMES.get(m.status) if m else None})
        out["items"] = items
        return out


@router.get("/print-jobs/{job_id}/pdf")
def get_pdf(job_id: str, ctx: AppContext = Depends(get_ctx)) -> FileResponse:
    with ctx.db.session() as s:
        j = s.get(PrintJob, job_id)
        if j is None or not j.pdf_path or not ctx.storage.exists(j.pdf_path):
            raise not_found("PDF")
        path, name = ctx.storage.abspath(j.pdf_path), f"{j.title or 'xuetou'}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=name, content_disposition_type="inline")


class ResultItem(BaseModel):
    seq: int
    result: str


class ResultsBody(BaseModel):
    results: list[ResultItem]


@router.post("/print-jobs/{job_id}/results")
def submit_results(job_id: str, body: ResultsBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    """孩子做完打印单后，家长按题号回填对错。"""
    with ctx.db.session() as s:
        j = s.get(PrintJob, job_id)
        if j is None:
            raise not_found("打印任务")
        items = {it.seq: it for it in s.query(PrintJobItem).filter_by(print_job_id=job_id)}
        n = 0
        for r in body.results:
            it = items.get(r.seq)
            if it is None or not it.mistake_id:
                continue
            m = s.get(Mistake, it.mistake_id)
            record_result(s, m, AttemptBody(result=r.result, context="redo", print_job_id=job_id))
            n += 1
    return {"recorded": n, **get_job(job_id, ctx)}
