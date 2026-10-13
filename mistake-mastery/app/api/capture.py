"""上传、来源卷、批量确认、题目截图。"""

import hashlib

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.adapters import imaging
from app.api.deps import LOGIN, bad_request, get_ctx, not_found
from app.context import AppContext
from app.models import Question, QuestionInstance, QuestionKp, SourceDocument, SourcePage
from app.services import capture
from app.services.questions import content_hash, corrected_image, instance_crop, page_image

router = APIRouter(prefix="/api", dependencies=LOGIN)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post("/captures")
async def create_capture(
    student_id: str = Form(...), subject: str = Form(...), mode: str = Form("page"),
    source_kind: str = Form("other"), title: str = Form(""), exam_date: str = Form(""),
    files: list[UploadFile] = File(...), ctx: AppContext = Depends(get_ctx),
) -> dict:
    if mode not in ("page", "single"):
        raise bad_request("mode 只能是 page 或 single")
    images = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise bad_request(f"{f.filename} 太大了（超过 25MB）")
        images.append(data)
    try:
        doc_id, job_id = capture.create_document(ctx, student_id=student_id, subject=subject, mode=mode,
                                                 source_kind=source_kind, title=title, exam_date=exam_date,
                                                 images=images)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return {"document_id": doc_id, "job_id": job_id}


def _doc_dict(d: SourceDocument, pages: list[SourcePage] | None = None) -> dict:
    out = {"id": d.id, "subject": d.subject, "source_kind": d.source_kind, "title": d.title, "exam_date": d.exam_date,
           "mode": d.mode, "status": d.status, "error": d.error, "created_at": d.created_at}
    if pages is not None:
        out["pages"] = [{"id": p.id, "page_no": p.page_no, "erase_status": p.erase_status, "quality": p.quality,
                         "width": p.width, "height": p.height,
                         # 矫正后的尺寸：题目坐标（bbox）都以它为准
                         "cw": (p.transform or {}).get("w") or p.width,
                         "ch": (p.transform or {}).get("h") or p.height} for p in pages]
    return out


@router.get("/documents")
def list_documents(student_id: str, ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    with ctx.db.session() as s:
        docs = s.query(SourceDocument).filter_by(student_id=student_id).order_by(SourceDocument.created_at.desc())
        return [_doc_dict(d) for d in docs.limit(100)]


@router.get("/documents/{document_id}")
def get_document(document_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        d = s.get(SourceDocument, document_id)
        if d is None:
            raise not_found("来源卷")
        pages = s.query(SourcePage).filter_by(document_id=document_id).order_by(SourcePage.page_no).all()
        return _doc_dict(d, pages)


@router.get("/documents/{document_id}/candidates")
def candidates(document_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        d = s.get(SourceDocument, document_id)
        if d is None:
            raise not_found("来源卷")
        rows = (s.query(QuestionInstance, SourcePage, Question)
                .join(SourcePage, QuestionInstance.page_id == SourcePage.id)
                .join(Question, QuestionInstance.question_id == Question.id)
                .filter(SourcePage.document_id == document_id)
                .order_by(SourcePage.page_no, QuestionInstance.created_at).all())
        items = []
        for inst, page, q in rows:
            kps = [k.kp_code for k in s.query(QuestionKp).filter_by(question_id=q.id)
                   .order_by(QuestionKp.is_primary.desc(), QuestionKp.kp_code)]
            marks = inst.grading_marks or {}
            items.append({
                "instance_id": inst.id, "page_no": page.page_no, "number_label": inst.number_label,
                "status": inst.status, "preselected": bool(inst.preselected), "bbox": inst.bbox,
                "question": {"id": q.id, "type": q.question_type, "stem_md": q.stem_md, "options": q.options,
                             "sub_questions": q.sub_questions, "answer": q.answer, "answer_source": q.answer_source,
                             "bj_slot": q.bj_slot, "difficulty": q.difficulty},
                "kp_codes": kps, "grading": marks.get("mark"), "score": marks.get("score"),
                "cause_suggestions": marks.get("cause_suggestions") or [],
                "student_answer": (inst.student_answer or {}).get("text"),
            })
        return {"document": _doc_dict(d), "items": items}


class ConfirmItem(BaseModel):
    instance_id: str
    selected: bool
    kp_codes: list[str] | None = None
    error_causes: list[str] | None = None
    answer: str | None = None


class ConfirmBody(BaseModel):
    items: list[ConfirmItem]


@router.post("/documents/{document_id}/confirm")
def confirm(document_id: str, body: ConfirmBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return capture.confirm(ctx, document_id, [i.model_dump() for i in body.items])
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


class RegionBody(BaseModel):
    bbox: list[float]  # 矫正图上的像素坐标


@router.post("/pages/{page_id}/regions")
def add_region(page_id: str, body: RegionBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    """手动框选一道题（自动切题漏掉或切错时用）。题干留空，打印时用截图。"""
    if len(body.bbox) != 4:
        raise bad_request("bbox 需要 4 个数")
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        if page is None:
            raise not_found("页面")
        doc = s.get(SourceDocument, page.document_id)
        q = Question(subject=doc.subject, origin="captured",
                     content_hash=content_hash(doc.subject, f"manual:{page_id}:{body.bbox}", None),
                     stem_md="", question_type="solve")
        s.add(q)
        s.flush()
        inst = QuestionInstance(page_id=page_id, question_id=q.id, number_label="", bbox=body.bbox,
                                grading_marks={"mark": "none"}, status="candidate", preselected=True)
        s.add(inst)
        s.flush()
        return {"instance_id": inst.id}


@router.patch("/instances/{instance_id}")
def update_instance(instance_id: str, body: RegionBody, ctx: AppContext = Depends(get_ctx)) -> dict:
    with ctx.db.session() as s:
        inst = s.get(QuestionInstance, instance_id)
        if inst is None:
            raise not_found("题目")
        inst.bbox = body.bbox
    return {"ok": True}


@router.post("/pages/{page_id}/erase")
def reerase(page_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    err = capture.erase_page(ctx, page_id)
    if err:
        raise bad_request(f"擦除失败：{err}")
    return {"ok": True}


# ---------------------------------------------------------------- 图片


def _image_response(img, cache_key: str, max_side: int) -> Response:  # noqa: ANN001
    small, _ = imaging.resize_max(img, max_side)
    data = imaging.encode_jpeg(small, 85)
    etag = hashlib.sha1(cache_key.encode()).hexdigest()
    return Response(data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=3600", "ETag": etag, "X-Robots-Tag": "noindex"})


@router.get("/pages/{page_id}/image")
def page_img(page_id: str, kind: str = "corrected", max_side: int = 1600, ctx: AppContext = Depends(get_ctx)):
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        if page is None:
            raise not_found("页面")
        if kind == "original":
            img = imaging.decode(ctx.storage.read(page.original_path))
        elif kind == "erased":
            img = page_image(ctx, page, "erased")
        else:
            img = corrected_image(ctx, page)
        return _image_response(img, f"{page_id}:{kind}:{page.erase_status}", min(max_side, 3000))


@router.get("/instances/{instance_id}/image")
def instance_img(instance_id: str, kind: str = "erased", max_side: int = 1400, ctx: AppContext = Depends(get_ctx)):
    with ctx.db.session() as s:
        inst = s.get(QuestionInstance, instance_id)
        if inst is None:
            raise not_found("题目")
        page = s.get(SourcePage, inst.page_id)
        img = instance_crop(ctx, inst, page, "erased" if kind == "erased" else "original")
        return _image_response(img, f"{instance_id}:{kind}:{inst.bbox}:{page.erase_status}", min(max_side, 3000))
