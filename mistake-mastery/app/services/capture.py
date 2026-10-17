"""第 ① 步：拍照收集。上传 → 矫正 → 识别切题 → 擦除 → 分类 → 批量确认 → 后台解答。"""

import logging
from typing import TYPE_CHECKING

import cv2

from app.adapters import imaging
from app.adapters.eraser import EraseError
from app.adapters.llm import LLMError
from app.ids import now_iso
from app.jobs import JobHandle
from app.models import (Attempt, Mistake, Question, QuestionInstance, QuestionKp, SourceDocument, SourcePage,
                        Student)
from app.services import mastery, prompts
from app.services import bank
from app.services.questions import (VALID_TYPES, apply_classification, bbox_to_pixels, content_hash, corrected_image,
                                    instance_crop)

if TYPE_CHECKING:
    from app.context import AppContext

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- 上传


def create_document(ctx: "AppContext", *, student_id: str, subject: str, mode: str, source_kind: str,
                    title: str | None, exam_date: str | None, images: list[bytes]) -> tuple[str, str]:
    """保存原图（压缩到长边 2000px）并创建处理任务，返回 (document_id, job_id)。"""
    if subject not in prompts.SUBJECT_NAMES:
        raise ValueError(f"不支持的学科：{subject}")
    if not images:
        raise ValueError("至少上传一张照片")
    with ctx.db.session() as s:
        if s.get(Student, student_id) is None:
            raise ValueError("孩子档案不存在")
        doc = SourceDocument(student_id=student_id, subject=subject, mode=mode, source_kind=source_kind,
                             title=title or None, exam_date=exam_date or None, status="processing")
        s.add(doc)
        s.flush()
        for i, raw in enumerate(images, start=1):
            jpeg, w, h = imaging.normalize_upload(raw)
            page = SourcePage(document_id=doc.id, page_no=i, original_path="", width=w, height=h)
            s.add(page)
            s.flush()
            page.original_path = ctx.storage.write(f"{ctx.storage.page_dir(page.id)}/original.jpg", jpeg)
        doc_id = doc.id
    job_id = ctx.jobs.submit("capture", {"document_id": doc_id})
    return doc_id, job_id


# ---------------------------------------------------------------- 后台处理


def process_document(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    doc_id = payload["document_id"]
    with ctx.db.session() as s:
        doc = s.get(SourceDocument, doc_id)
        subject, mode = doc.subject, doc.mode
        page_ids = [p.id for p in s.query(SourcePage).filter_by(document_id=doc_id).order_by(SourcePage.page_no)]
    total = len(page_ids)
    created: list[str] = []
    errors: list[str] = []
    header_title = None
    prev_last: str | None = None  # 上一页最后一道题，这一页开头的"后半段"接到它上面
    for i, page_id in enumerate(page_ids):
        base = int(i / total * 80)
        step = 80 / total
        try:
            handle.progress(f"第 {i + 1}/{total} 页：矫正", base)
            img, transform = _correct(ctx, page_id, mode)
            handle.progress(f"第 {i + 1}/{total} 页：识别题目", base + int(step * 0.2))
            title, new_ids, prev_last = _recognize(ctx, page_id, _outbound(ctx, img, i + 1), subject, mode,
                                                   prev_last if mode == "page" else None)
            header_title = header_title or title
            created += new_ids
        except (LLMError, ValueError) as exc:
            errors.append(f"第 {i + 1} 页识别失败：{exc}")
            log.warning("recognize failed for page %s: %s", page_id, exc)
            continue
        handle.progress(f"第 {i + 1}/{total} 页：擦除手写", base + int(step * 0.6))
        err = erase_page(ctx, page_id)
        if err:
            errors.append(f"第 {i + 1} 页擦除失败：{err}")

    if created:
        handle.progress("分类知识点", 85)
        try:
            _classify(ctx, subject, created)
        except LLMError as exc:
            errors.append(f"分类失败：{exc}")

    with ctx.db.session() as s:
        doc = s.get(SourceDocument, doc_id)
        if header_title and not doc.title:
            doc.title = header_title
        doc.status = "ready" if created else "failed"
        doc.error = "\n".join(errors) or None
    if not created:
        raise RuntimeError("；".join(errors) or "没有识别出题目")
    return {"questions": len(created), "errors": errors}


def _outbound(ctx: "AppContext", img, page_no: int):  # noqa: ANN001
    """送给外部接口的图片：按设置把第 1 页的卷头涂白。"""
    ratio = ctx.settings.mask_header_ratio
    return imaging.mask_header(img, ratio) if page_no == 1 and ratio > 0 else img


def _correct(ctx: "AppContext", page_id: str, mode: str):
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        img = imaging.decode(ctx.storage.read(page.original_path))
        page.quality = imaging.quality_metrics(img)
        page.transform = imaging.detect_page_transform(img) if mode == "page" else None
        transform = page.transform
        corrected = corrected_image(ctx, page)
    return corrected, transform


def _recognize(ctx: "AppContext", page_id: str, img, subject: str, mode: str,
               prev_last: str | None = None) -> tuple[str | None, list[str], str | None]:
    """识别一页；返回（卷头、新建的题、这一页最后一道题的实例编号）。
    页面开头是上一页最后一道题的后半段（题干在上一页、图和选项在这一页）时，接到那道题上，不另算一道。"""
    url, _scale = imaging.data_url_jpeg(img)
    result = ctx.llm.chat_json("recognize", prompts.recognize_messages(subject, url, mode),
                               prompt_version=prompts.RECOGNIZE_VERSION)
    items = (result or {}).get("questions") or []
    if mode == "single" and not items:
        items = [{"bbox": [0, 0, 1000, 1000], "stem_md": "", "question_type": "solve"}]
    h, w = img.shape[:2]
    new_ids: list[str] = []
    last = prev_last
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        page.layout = {"recognized": len(items), "header": result.get("header") if result else None}
        if items and items[0].get("continued") and prev_last and s.get(QuestionInstance, prev_last) is not None:
            _continue(s, s.get(QuestionInstance, prev_last), items.pop(0), page_id, w, h)
        for item in items:
            qtype = item.get("question_type") if item.get("question_type") in VALID_TYPES else "solve"
            stem = item.get("stem_md") or ""
            options = item.get("options") or None
            bbox = [0.0, 0.0, float(w), float(h)] if mode == "single" else bbox_to_pixels(item.get("bbox"), w, h)
            chash = content_hash(subject, stem, options)
            existing = s.query(Question).filter_by(content_hash=chash, subject=subject, origin="captured").first() \
                if stem.strip() else None
            if existing is not None:
                question = existing
            else:
                teacher = (item.get("teacher_answer") or "").strip()
                question = Question(
                    subject=subject, origin="captured", content_hash=chash, stem_md=stem, options=options,
                    sub_questions=item.get("sub_questions") or None,
                    figures=[{"kind": "in_crop"}] if item.get("has_figure") else None,
                    answer={"final": teacher} if teacher else None,
                    answer_source="teacher" if teacher else "none",
                    question_type=qtype,
                )
                s.add(question)
                s.flush()
                if stem.strip():
                    bank.attach_match(ctx, s, question)  # 题库里有这道题：带上官方答案和出处
            grading = item.get("grading") if item.get("grading") in ("right", "wrong", "partial", "none") else "none"
            inst = QuestionInstance(
                page_id=page_id, question_id=question.id, number_label=str(item.get("number_label") or ""),
                bbox=bbox,
                student_answer={"text": item.get("student_answer")} if item.get("student_answer") else None,
                grading_marks={"mark": grading, "score": item.get("score_text")},
                status="candidate", preselected=grading in ("wrong", "partial"),
            )
            s.add(inst)
            s.flush()
            new_ids.append(inst.id)
            last = inst.id
    return (result or {}).get("header"), new_ids, last


def _continue(s, inst: QuestionInstance, item: dict, page_id: str, w: int, h: int) -> None:  # noqa: ANN001
    """把这一页开头的后半段接到上一页最后一道题上：位置多一段，文字、选项、小问合并，批改和作答补上。"""
    inst.extra_regions = list(inst.extra_regions or []) + [{"page_id": page_id, "bbox": bbox_to_pixels(item.get("bbox"), w, h)}]
    q = s.get(Question, inst.question_id)
    merged = {"stem_md": q.stem_md or "", "options": q.options, "sub_questions": q.sub_questions,
              "has_figure": bool(q.figures), "regions": [], "answer_shown": False}
    bank._extend(merged, item, None)
    q.stem_md, q.options, q.sub_questions = merged["stem_md"], merged["options"] or None, merged["sub_questions"] or None
    if merged["has_figure"] and not q.figures:
        q.figures = [{"kind": "in_crop"}]
    q.content_hash = content_hash(q.subject, q.stem_md, q.options)
    if not q.answer and (item.get("teacher_answer") or "").strip():
        q.answer, q.answer_source = {"final": item["teacher_answer"].strip()}, "teacher"
    text = (item.get("student_answer") or "").strip()
    if text:
        prev = (inst.student_answer or {}).get("text") or ""
        inst.student_answer = {"text": f"{prev}\n{text}".strip()}
    marks = dict(inst.grading_marks or {})
    grading = item.get("grading") if item.get("grading") in ("right", "wrong", "partial") else None
    rank = {"wrong": 3, "partial": 2, "right": 1}  # 两段里只要有一段判错，这道题就是错的
    if grading and rank[grading] > rank.get(marks.get("mark"), 0):
        marks["mark"] = grading
        inst.preselected = grading in ("wrong", "partial")
    if item.get("score_text") and not marks.get("score"):
        marks["score"] = item["score_text"]
    inst.grading_marks = marks


def erase_page(ctx: "AppContext", page_id: str) -> str | None:
    """整页去手写，结果存为 8 位灰度 PNG；返回错误信息（成功时为 None）。"""
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        img = corrected_image(ctx, page)
        page_dir = ctx.storage.page_dir(page.id)
        page_no = page.page_no
    error: str | None = None
    try:  # 调用外部接口时不占着数据库会话
        eraser = ctx.eraser()
        # 本地算法用无损 PNG；云接口有大小限制，用高质量 JPEG
        if eraser.name == "local_color":  # 本地算法用无损 PNG，不出本机
            data = imaging.encode_png(img)
        else:  # 云接口有大小限制，用高质量 JPEG；按设置涂白卷头
            data = imaging.encode_jpeg(_outbound(ctx, img, page_no), 92)
        out = imaging.decode(eraser.erase(data))
    except (EraseError, ValueError, OSError) as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 —— 网络等错误也只影响这一页
        error = f"{exc.__class__.__name__}: {exc}"
    with ctx.db.session() as s:
        page = s.get(SourcePage, page_id)
        if error:
            page.erase_status = "failed"
            return error
        h, w = img.shape[:2]
        if out.shape[:2] != (h, w):  # 有的接口返回的尺寸不同，对齐回矫正图，保证题目坐标不变
            out = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)
        page.erased_path = ctx.storage.write(f"{page_dir}/erased.png", imaging.encode_png_gray(out))
        page.erase_status = "done"
    return None


def _classify(ctx: "AppContext", subject: str, instance_ids: list[str]) -> None:
    with ctx.db.session() as s:
        rows = []
        for idx, iid in enumerate(instance_ids):
            inst = s.get(QuestionInstance, iid)
            q = s.get(Question, inst.question_id)
            rows.append({"id": idx, "number_label": inst.number_label, "type": q.question_type,
                         "stem": (q.stem_md or "")[:600], "options": q.options,
                         "student_answer": (inst.student_answer or {}).get("text"),
                         "grading": (inst.grading_marks or {}).get("mark")})
    if not rows:
        return
    result = ctx.llm.chat_json("classify", prompts.classify_messages(subject, ctx.curriculum, rows),
                               prompt_version=prompts.CLASSIFY_VERSION)
    valid_causes = {x["code"] for x in ctx.curriculum.causes_for(subject)}
    with ctx.db.session() as s:
        for item in (result or {}).get("items", []):
            try:
                iid = instance_ids[int(item.get("id"))]
            except (TypeError, ValueError, IndexError):
                continue
            inst = s.get(QuestionInstance, iid)
            q = s.get(Question, inst.question_id)
            apply_classification(ctx, s, q, item)
            causes = [c for c in item.get("error_causes") or [] if c in valid_causes][:2]
            marks = dict(inst.grading_marks or {})
            marks["cause_suggestions"] = causes
            inst.grading_marks = marks


# ---------------------------------------------------------------- 批量确认


def confirm(ctx: "AppContext", document_id: str, items: list[dict]) -> dict:
    """确认后的题成为错题（同一道题已经在错题本里时合并，错误次数 +1）。"""
    to_solve: list[str] = []
    created, merged = 0, 0
    today = mastery.today()
    cfg = mastery.MasteryConfig()
    with ctx.db.session() as s:
        doc = s.get(SourceDocument, document_id)
        if doc is None:
            raise ValueError("来源卷不存在")
        by_id = {i["instance_id"]: i for i in items}
        insts = (s.query(QuestionInstance).join(SourcePage, QuestionInstance.page_id == SourcePage.id)
                 .filter(SourcePage.document_id == document_id).all())
        for inst in insts:
            choice = by_id.get(inst.id)
            if choice is None:
                continue
            if not choice.get("selected"):
                inst.status = "discarded"
                continue
            inst.status = "confirmed"
            q = s.get(Question, inst.question_id)
            if choice.get("kp_codes") is not None:
                s.query(QuestionKp).filter_by(question_id=q.id).delete()
                for n, code in enumerate(dict.fromkeys(choice["kp_codes"])):
                    if code in ctx.curriculum.kps:
                        s.add(QuestionKp(question_id=q.id, kp_code=code, is_primary=int(n == 0)))
            answer = (choice.get("answer") or "").strip()
            if answer:
                q.answer = {"final": answer}
                q.answer_source = "manual"
            causes = choice.get("error_causes")
            if causes is None:
                causes = (inst.grading_marks or {}).get("cause_suggestions") or []
            mark = (inst.grading_marks or {}).get("mark")
            result = "partial" if mark == "partial" else "wrong"
            m = s.query(Mistake).filter_by(student_id=doc.student_id, question_id=q.id).first()
            if m is None:
                state = mastery.new_mistake_state()
                m = Mistake(student_id=doc.student_id, question_id=q.id, first_instance_id=inst.id,
                            error_causes=list(causes), last_wrong_at=now_iso())
                mastery.write_state(m, state)
                s.add(m)
                s.flush()
                created += 1
            else:
                state = mastery.apply(mastery.read_state(m), mastery.Event("CONFIRM"), cfg, today)
                mastery.write_state(m, state)
                m.last_wrong_at = now_iso()
                m.error_causes = list(dict.fromkeys(list(m.error_causes or []) + list(causes)))
                merged += 1
            s.add(Attempt(mistake_id=m.id, question_id=q.id, round=m.round, context="capture", result=result,
                          graded_by="teacher" if mark in ("wrong", "partial") else "guardian",
                          error_cause=(causes or [None])[0]))
            if q.answer_source == "none":
                to_solve.append(q.id)
        doc.status = "confirmed"
    for qid in dict.fromkeys(to_solve):
        ctx.jobs.submit("solve", {"question_id": qid})
    return {"created": created, "merged": merged, "solving": len(set(to_solve))}


# ---------------------------------------------------------------- 后台解答（v0.1 单模型，标"待核"）


def solve_question(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    qid = payload["question_id"]
    with ctx.db.session() as s:
        q = s.get(Question, qid)
        if q.answer_source != "none":
            return {"skipped": True}
        inst = s.query(QuestionInstance).filter_by(question_id=qid).first()
        page = s.get(SourcePage, inst.page_id) if inst else None
        image_url = None
        if inst and page:
            image_url, _ = imaging.data_url_jpeg(instance_crop(ctx, inst, page, "erased", s))
        qdata = {"type": q.question_type, "stem": q.stem_md, "options": q.options, "sub_questions": q.sub_questions}
        subject = q.subject
    handle.progress("AI 解答中", 30)
    out = ctx.llm.chat_json("solve", prompts.solve_messages(subject, qdata, image_url),
                            prompt_version=prompts.SOLVE_VERSION)
    with ctx.db.session() as s:
        q = s.get(Question, qid)
        if q.answer_source != "none":  # 期间家长已经手动填了答案
            return {"skipped": True}
        q.answer = {"final": str(out.get("final_answer") or "").strip()}
        q.solution_md = out.get("solution_md")
        q.answer_source = "ai_unverified"
        q.verification = {"solver": ctx.llm.models.get("solve"), "confidence": out.get("confidence"),
                          "at": now_iso()}
    return {"answered": True}


def register(ctx: "AppContext") -> None:
    ctx.jobs.register("capture", process_document)
    ctx.jobs.register("solve", solve_question)
