"""单题讲解：AI 看着题目截图、针对孩子的作答讲这一道题（读题、思路、分步、错在哪、提醒），见 docs/06 §2.3。

存在 tutor_sessions（mode = explain）+ tutor_messages 里，每道错题保留最新一份；重新生成时覆盖。
"做错 → 待讲解"的题看完讲解点"讲完了"，状态机收到 TUTOR_DONE 回到待重做（过了原题关的回待变式）。
"""

from typing import TYPE_CHECKING

from app.adapters import imaging
from app.adapters.llm import LLMError
from app.ids import now_iso
from app.jobs import JobHandle
from app.models import Job, Mistake, Question, QuestionInstance, QuestionKp, SourcePage, TutorMessage, TutorSession
from app.services import mastery, prompts
from app.services.lessons import SOURCE_NAMES, _clip
from app.services.questions import instance_crop

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.context import AppContext

MODE = "explain"


def gather(ctx: "AppContext", s: "Session", m: Mistake) -> tuple[list, str | None]:
    """写讲解用的材料（tutor_messages 的参数）。不带孩子的名字。"""
    q = s.get(Question, m.question_id)
    cur = ctx.curriculum
    kps = [cur.path_name(k.kp_code) for k in s.query(QuestionKp).filter_by(question_id=q.id)
           .order_by(QuestionKp.is_primary.desc())]
    causes = {c["code"]: c["name"] for c in cur.causes_for(q.subject)}
    insts = s.query(QuestionInstance).filter_by(question_id=q.id, status="confirmed").all()
    answers = [t for t in ((i.student_answer or {}).get("text") for i in insts) if t]
    image_url = None
    inst = s.get(QuestionInstance, m.first_instance_id) if m.first_instance_id else (insts[0] if insts else None)
    page = s.get(SourcePage, inst.page_id) if inst else None
    if inst and page:
        try:
            image_url, _ = imaging.data_url_jpeg(instance_crop(ctx, inst, page, "erased", s))
        except (ValueError, OSError):
            image_url = None
    question = {"题型": q.question_type, "题干": _clip(q.stem_md, 1500), "选项": q.options, "小问": q.sub_questions,
                "知识点": kps, "有截图": image_url is not None}
    student = {"孩子的作答": answers or "（没有识别出作答）", "错因": [causes.get(c, c) for c in m.error_causes or []],
               "错了几次": m.wrong_count, "第几轮": m.round,
               "状态": mastery.STATUS_NAMES.get(m.status, m.status)}
    answer = {"答案": (q.answer or {}).get("final") or "（暂无）", "来源": SOURCE_NAMES.get(q.answer_source, q.answer_source),
              "解析": _clip(q.solution_md, 2000) or None}
    return [q.subject, question, image_url, student, answer], image_url


def _normalize(out: object) -> dict:
    out = out if isinstance(out, dict) else {}

    def text(v: object, n: int = 1500) -> str:
        return str(v).strip()[:n] if v not in (None, "") else ""

    def items(v: object) -> list:
        return v if isinstance(v, list) else []

    content = {"read": text(out.get("read"), 600), "idea": text(out.get("idea")),
               "steps": [text(x, 800) for x in items(out.get("steps")) if text(x)][:8],
               "where_wrong": text(out.get("where_wrong")),
               "pitfalls": [text(x, 300) for x in items(out.get("pitfalls")) if text(x)][:4],
               "answer": text(out.get("answer"), 400)}
    if not content["idea"] and not content["steps"]:
        raise LLMError("AI 没有写出讲解内容，请重新生成")
    return content


def _markdown(c: dict) -> str:
    parts = []
    if c["read"]:
        parts.append(f"**读题**　{c['read']}")
    if c["idea"]:
        parts.append(f"**思路**　{c['idea']}")
    if c["steps"]:
        parts.append("**分步**\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(c["steps"], start=1)))
    if c["where_wrong"]:
        parts.append(f"**错在哪**　{c['where_wrong']}")
    if c["pitfalls"]:
        parts.append("**下次提醒自己**\n" + "\n".join(f"- {x}" for x in c["pitfalls"]))
    if c["answer"]:
        parts.append(f"**答案**　{c['answer']}")
    return "\n\n".join(parts)


def generate_job(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    mid = payload["mistake_id"]
    handle.progress("整理题目和作答", 10)
    with ctx.db.session() as s:
        m = s.get(Mistake, mid)
        if m is None:
            return {"skipped": True}
        args, _ = gather(ctx, s, m)
        sid, qid = m.student_id, m.question_id
    handle.progress("AI 正在讲解", 30)
    out = ctx.llm.chat_json("tutor", prompts.tutor_messages(*args), prompt_version=prompts.TUTOR_VERSION,
                            temperature=0.3, fresh=bool(payload.get("fresh")))
    content = _normalize(out)
    with ctx.db.session() as s:
        sess = s.query(TutorSession).filter_by(mistake_id=mid, mode=MODE).first()
        if sess is None:
            sess = TutorSession(student_id=sid, mistake_id=mid, question_id=qid, mode=MODE, status="done")
            s.add(sess)
            s.flush()
        sess.status, sess.created_at = "done", now_iso()
        s.query(TutorMessage).filter_by(session_id=sess.id).delete()
        s.add(TutorMessage(session_id=sess.id, role="assistant", content_md=_markdown(content), attachments={
            "sections": content, "model": "fake" if ctx.llm.fake is not None else ctx.llm.models.get("tutor", ""),
            "prompt_version": prompts.TUTOR_VERSION}))
    return {"mistake_id": mid}


def running_job(s: "Session", mistake_id: str) -> Job | None:
    for j in s.query(Job).filter(Job.kind == "tutor_explain", Job.status.in_(("queued", "running"))):
        if j.payload.get("mistake_id") == mistake_id:
            return j
    return None


def start(ctx: "AppContext", mistake_id: str, fresh: bool = False) -> str:
    with ctx.db.session() as s:
        j = running_job(s, mistake_id)
        if j is not None:
            return j.id
    return ctx.jobs.submit("tutor_explain", {"mistake_id": mistake_id, "fresh": fresh})


def explain_json(s: "Session", mistake_id: str) -> dict | None:
    sess = s.query(TutorSession).filter_by(mistake_id=mistake_id, mode=MODE).first()
    if sess is None:
        return None
    msg = s.query(TutorMessage).filter_by(session_id=sess.id, role="assistant").order_by(TutorMessage.created_at.desc()).first()
    if msg is None:
        return None
    att = msg.attachments or {}
    return {**(att.get("sections") or {}), "md": msg.content_md, "created_at": msg.created_at, "model": att.get("model", "")}


def tutor_done(s: "Session", m: Mistake) -> None:
    """看完讲解：回到待重做（已过原题关的回待变式）。"""
    state = mastery.apply(mastery.read_state(m), mastery.Event("TUTOR_DONE"), mastery.MasteryConfig(), mastery.today())
    mastery.write_state(m, state)


def register(ctx: "AppContext") -> None:
    ctx.jobs.register("tutor_explain", generate_job)
