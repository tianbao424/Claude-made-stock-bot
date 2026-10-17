"""数据表（见 docs/04-data-model-and-api.md）。

每个模型用 ``__sync__`` 标明是否导出到 GitHub 数据仓库：
- ``"table"``：导出为 tables/<表名>.jsonl
- ``"monthly"``：按 created_at 的年月分文件（只追加的作答记录）
- ``None``：仅本地（派生数据、缓存、日志、密钥）
``__local_cols__`` 里的列即使所在的表要同步，也不导出。
"""

from typing import Any, ClassVar, Optional

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.ids import new_id, now_iso


class Base(DeclarativeBase):
    __sync__: ClassVar[Optional[str]] = None
    __local_cols__: ClassVar[frozenset[str]] = frozenset()


def _id() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=new_id)


def _created() -> Mapped[str]:
    return mapped_column(String(32), nullable=False, default=now_iso)


# ---------------------------------------------------------------- 孩子档案与设置


class Student(Base):
    __tablename__ = "students"
    __sync__ = "table"

    id: Mapped[str] = _id()
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    district: Mapped[Optional[str]] = mapped_column(String(30))
    textbooks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = _created()


class ExamEvent(Base):
    __tablename__ = "exam_events"
    __sync__ = "table"

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    exam_date: Mapped[str] = mapped_column(String(10), nullable=False)
    subjects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scope_kp_codes: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[str] = _created()


class AppSetting(Base):
    """仅本地：密码哈希、会话版本号等。非敏感设置在数据仓库的 settings.json。"""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)


# ---------------------------------------------------------------- 采集


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __sync__ = "table"

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(10), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    title: Mapped[Optional[str]] = mapped_column(String(100))
    exam_date: Mapped[Optional[str]] = mapped_column(String(10))
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="page")  # page|single
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = _created()


class SourcePage(Base):
    __tablename__ = "source_pages"
    __sync__ = "table"

    id: Mapped[str] = _id()
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    original_path: Mapped[str] = mapped_column(String(200), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transform: Mapped[Optional[list]] = mapped_column(JSON)  # 3x3 透视矩阵；None 表示未矫正
    erased_path: Mapped[Optional[str]] = mapped_column(String(200))
    erase_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    paper_size: Mapped[Optional[str]] = mapped_column(String(10))
    layout: Mapped[Optional[dict]] = mapped_column(JSON)
    quality: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[str] = _created()

    __table_args__ = (Index("ix_pages_doc", "document_id", "page_no", unique=True),)


class Question(Base):
    __tablename__ = "questions"
    __sync__ = "table"

    id: Mapped[str] = _id()
    subject: Mapped[str] = mapped_column(String(10), nullable=False)
    origin: Mapped[str] = mapped_column(String(10), nullable=False, default="captured")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stem_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    options: Mapped[Optional[list]] = mapped_column(JSON)
    sub_questions: Mapped[Optional[list]] = mapped_column(JSON)
    figures: Mapped[Optional[list]] = mapped_column(JSON)
    answer: Mapped[Optional[dict]] = mapped_column(JSON)
    solution_md: Mapped[Optional[str]] = mapped_column(Text)
    answer_source: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    verification: Mapped[Optional[dict]] = mapped_column(JSON)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, default="solve")
    difficulty: Mapped[Optional[int]] = mapped_column(Integer)
    bj_slot: Mapped[Optional[str]] = mapped_column(String(50))
    parent_question_id: Mapped[Optional[str]] = mapped_column(ForeignKey("questions.id"))
    variant_set_id: Mapped[Optional[str]] = mapped_column(String(36))
    variant_level: Mapped[Optional[int]] = mapped_column(Integer)
    gen_meta: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[str] = _created()
    # 录入的题在题库里找到了同一道题：{"question_id", "score", "status": auto|rejected, "prev_answer", "prev_source"}
    bank_match: Mapped[Optional[dict]] = mapped_column(JSON)


class QuestionKp(Base):
    __tablename__ = "question_kps"
    __sync__ = "table"

    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    kp_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)


class QuestionInstance(Base):
    __tablename__ = "question_instances"
    __sync__ = "table"

    id: Mapped[str] = _id()
    page_id: Mapped[str] = mapped_column(ForeignKey("source_pages.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)
    number_label: Mapped[Optional[str]] = mapped_column(String(20))
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)  # [x0, y0, x1, y1]，矫正图像素
    # 跨页的题：后半段在别的页上，[{"page_id": ..., "bbox": [...]}]；截图时竖着拼在 bbox 下面
    extra_regions: Mapped[Optional[list]] = mapped_column(JSON)
    answer_area_mm: Mapped[Optional[float]] = mapped_column(Float)
    student_answer: Mapped[Optional[dict]] = mapped_column(JSON)
    grading_marks: Mapped[Optional[dict]] = mapped_column(JSON)
    # 批量确认前是候选（candidate），确认后是 confirmed，未选中的是 discarded。
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="candidate")
    preselected: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = _created()


# ---------------------------------------------------------------- 题库（真题、各区一模二模、区统考）


class BankPaper(Base):
    """导入题库的一套卷子。原卷和答案文件存在数据仓库的 files/bank/<id>/ 下。"""

    __tablename__ = "bank_papers"
    __sync__ = "table"

    id: Mapped[str] = _id()
    subject: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    year: Mapped[Optional[int]] = mapped_column(Integer)
    region: Mapped[Optional[str]] = mapped_column(String(20))  # beijing（全市统考）或区的代码
    exam_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    # [{"role": "paper"|"answer", "kind": "pdf"|"image", "path": ..., "name": ...}]
    files: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{"n": 1, "file": 0, "index": 0, "role": ..., "kind": questions|answers|other, "transform": ...}]
    pages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="processing")
    error: Mapped[Optional[str]] = mapped_column(Text)
    stats: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[str] = _created()


class BankItem(Base):
    """题库里的一道题在原卷上的位置（题目内容在 questions 表，origin = "bank"）。"""

    __tablename__ = "bank_items"
    __sync__ = "table"

    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("bank_papers.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    number_label: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    # 跨页的题有多段：[{"page": 1, "bbox": [x0, y0, x1, y1]}]，坐标按页面 0–1000 归一化
    regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    points: Mapped[Optional[str]] = mapped_column(String(20))  # 卷面标注的分值
    # {"answer_in_crop": true}：截图里能看到答案（答案版卷子的填空题横线上已经填好了）
    flags: Mapped[Optional[dict]] = mapped_column(JSON)


# ---------------------------------------------------------------- 错题与学习


class Mistake(Base):
    __tablename__ = "mistakes"
    __sync__ = "table"
    __local_cols__ = frozenset({"priority"})

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)
    first_instance_id: Mapped[Optional[str]] = mapped_column(ForeignKey("question_instances.id"))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="TO_REDO")
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    gates: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_causes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    followups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    variant_passed_at: Mapped[Optional[str]] = mapped_column(String(10))
    next_review_at: Mapped[Optional[str]] = mapped_column(String(10))
    priority: Mapped[Optional[float]] = mapped_column(Float)
    mastered_at: Mapped[Optional[str]] = mapped_column(String(32))
    last_wrong_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    created_at: Mapped[str] = _created()

    __table_args__ = (
        Index("ix_mistakes_student_question", "student_id", "question_id", unique=True),
        Index("ix_mistakes_status", "student_id", "status"),
    )


class Attempt(Base):
    __tablename__ = "attempts"
    __sync__ = "monthly"

    id: Mapped[str] = _id()
    mistake_id: Mapped[str] = mapped_column(ForeignKey("mistakes.id"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[str] = mapped_column(String(12), nullable=False)
    variant_set_id: Mapped[Optional[str]] = mapped_column(String(36))
    print_job_id: Mapped[Optional[str]] = mapped_column(String(36))
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    graded_by: Mapped[str] = mapped_column(String(10), nullable=False)
    error_cause: Mapped[Optional[str]] = mapped_column(String(30))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = _created()


class VariantSet(Base):
    __tablename__ = "variant_sets"
    __sync__ = "table"

    id: Mapped[str] = _id()
    mistake_id: Mapped[str] = mapped_column(ForeignKey("mistakes.id"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    target_levels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    score: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[str] = _created()


class TutorSession(Base):
    __tablename__ = "tutor_sessions"
    __sync__ = "table"

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    mistake_id: Mapped[Optional[str]] = mapped_column(ForeignKey("mistakes.id"))
    question_id: Mapped[Optional[str]] = mapped_column(ForeignKey("questions.id"))
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[str] = _created()


class TutorMessage(Base):
    __tablename__ = "tutor_messages"
    __sync__ = "table"

    id: Mapped[str] = _id()
    session_id: Mapped[str] = mapped_column(ForeignKey("tutor_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    step: Mapped[Optional[int]] = mapped_column(Integer)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[str] = _created()


class KpMastery(Base):
    """仅本地：由作答记录算出的派生数据，重建索引时重算。"""

    __tablename__ = "kp_mastery"

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), primary_key=True)
    kp_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class KpLesson(Base):
    """知识点讲解：AI 按孩子在这个知识点上的错题写的（要点、方法、易错点、例题），每个孩子每个知识点一份。

    生成要花钱，所以同步到数据仓库；重新生成时覆盖。"""

    __tablename__ = "kp_lessons"
    __sync__ = "table"

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    kp_code: Mapped[str] = mapped_column(String(40), nullable=False)
    # {"one_line", "key_points": [{"title","md"}], "method": [md], "pitfalls": [{"title","md","refs"}],
    #  "example": {"ref","question_md","steps_md","answer"} | null, "self_check": [md]}
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 写讲解时用到的材料：{"mistake_ids": [...], "refs": {"M1": {"kind": "mistake", "id": ...}, "B1": {...}}}
    basis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    created_at: Mapped[str] = _created()

    __table_args__ = (Index("ix_kp_lessons_student_kp", "student_id", "kp_code", unique=True),)


# ---------------------------------------------------------------- 打印


class PrintJob(Base):
    __tablename__ = "print_jobs"
    __sync__ = "table"
    __local_cols__ = frozenset({"pdf_path", "key_pdf_path", "error"})

    id: Mapped[str] = _id()
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    template: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100))
    filters: Mapped[Optional[dict]] = mapped_column(JSON)
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="queued")
    pdf_path: Mapped[Optional[str]] = mapped_column(String(200))
    key_pdf_path: Mapped[Optional[str]] = mapped_column(String(200))
    manifest: Mapped[Optional[dict]] = mapped_column(JSON)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[str] = _created()


class PrintJobItem(Base):
    __tablename__ = "print_job_items"
    __sync__ = "table"

    print_job_id: Mapped[str] = mapped_column(ForeignKey("print_jobs.id"), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[Optional[str]] = mapped_column(ForeignKey("questions.id"))
    mistake_id: Mapped[Optional[str]] = mapped_column(ForeignKey("mistakes.id"))
    instance_id: Mapped[Optional[str]] = mapped_column(ForeignKey("question_instances.id"))
    page_id: Mapped[Optional[str]] = mapped_column(ForeignKey("source_pages.id"))  # 原卷还原时按页
    page_no: Mapped[Optional[int]] = mapped_column(Integer)
    answer_bbox_mm: Mapped[Optional[list]] = mapped_column(JSON)


# ---------------------------------------------------------------- 字典、任务与日志（仅本地）


class KnowledgePoint(Base):
    """启动时从 app/curriculum/*.yaml 加载。"""

    __tablename__ = "knowledge_points"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    subject: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(40))
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    bj_weight: Mapped[Optional[float]] = mapped_column(Float)
    textbook_refs: Mapped[Optional[dict]] = mapped_column(JSON)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = _id()
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="queued")
    progress: Mapped[Optional[dict]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = _created()
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)

    __table_args__ = (Index("ix_jobs_status", "status", "created_at"),)


class AiCall(Base):
    __tablename__ = "ai_calls"

    id: Mapped[str] = _id()
    task: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    cost_cny: Mapped[Optional[float]] = mapped_column(Float)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[str] = _created()


SYNCED_MODELS: list[type[Base]] = [
    m for m in Base.__subclasses__() if m.__sync__ is not None
]
