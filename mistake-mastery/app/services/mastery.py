"""错题状态机（见 docs/06-mastery-algorithm.md §2）。纯函数：输入旧状态和事件，输出新状态。

三道关：原题关（original）→ 变式关（variant）→ 时间关（spaced）。三关都过 = 已学透。
任何一关失败触发"回炉"：轮次 +1，三道关重置，回到待重做。
"""

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

TO_REDO = "TO_REDO"
TO_TUTOR = "TO_TUTOR"
TO_VARIANT = "TO_VARIANT"
TO_REVIEW = "TO_REVIEW"
MASTERED = "MASTERED"
STUBBORN = "STUBBORN"
STATUSES = (TO_REDO, TO_TUTOR, TO_VARIANT, TO_REVIEW, MASTERED, STUBBORN)

STATUS_NAMES = {
    TO_REDO: "待重做",
    TO_TUTOR: "待讲解",
    TO_VARIANT: "待变式",
    TO_REVIEW: "待复习",
    MASTERED: "已学透",
    STUBBORN: "顽固错题",
}


@dataclass(frozen=True)
class MasteryConfig:
    initial_pass: int = 4  # 首组 5 题至少做对几题（且综合题必须对）
    followup_pass: int = 2  # 追加 3 题至少做对几题（且层级最高的那题必须对）
    max_followups: int = 2  # 追加上限，超过转顽固错题
    min_interval_days: int = 7  # 时间关最小间隔
    min_interval_days_exam: int = 4  # 考前 14 天内压缩后的间隔


@dataclass(frozen=True)
class Gates:
    original: bool = False
    variant: bool = False
    spaced: bool = False


@dataclass(frozen=True)
class State:
    status: str = TO_REDO
    round: int = 1
    gates: Gates = field(default_factory=Gates)
    wrong_count: int = 1
    followups: int = 0
    variant_passed_at: str | None = None
    next_review_at: str | None = None
    mastered_at: str | None = None


@dataclass(frozen=True)
class Event:
    kind: str  # CONFIRM | REDO_RESULT | TUTOR_DONE | VARIANT_SET_SCORED | REVIEW_RESULT | RETRY
    result: str | None = None  # correct | wrong | partial
    set_kind: str | None = None  # initial | followup
    correct: int = 0
    key_ok: bool = False  # 首组：综合题做对；追加组：层级最高的那题做对
    exam_soon: bool = False  # 考前 14 天内（压缩时间关间隔）


def today() -> date:
    return date.today()


def new_mistake_state() -> State:
    return State()


def _reflow(s: State) -> State:
    """回炉：轮次 +1、错误次数 +1、三道关重置，回到待重做。"""
    return State(status=TO_REDO, round=s.round + 1, gates=Gates(), wrong_count=s.wrong_count + 1)


def apply(s: State, e: Event, cfg: MasteryConfig, on: date) -> State:
    if e.kind == "CONFIRM":  # 同一道题又录入了一次
        if s.status in (TO_REVIEW, MASTERED):
            return _reflow(s)
        return replace(s, wrong_count=s.wrong_count + 1)

    if e.kind == "REDO_RESULT":  # 重做原题
        if s.status in (TO_REVIEW, MASTERED):  # 已过变式关的题再做原题，等同于复习
            return apply(s, Event("REVIEW_RESULT", result=e.result, exam_soon=e.exam_soon), cfg, on)
        if e.result == "correct":
            if s.status in (TO_REDO, TO_TUTOR):
                return replace(s, status=TO_VARIANT, gates=replace(s.gates, original=True))
            return s  # 原题关已经过了，再做对不改变状态
        return replace(s, status=TO_TUTOR, gates=replace(s.gates, original=False), wrong_count=s.wrong_count + 1)

    if e.kind == "TUTOR_DONE":
        if s.status != TO_TUTOR:
            return s
        return replace(s, status=TO_VARIANT if s.gates.original else TO_REDO)

    if e.kind == "VARIANT_SET_SCORED":
        if s.status != TO_VARIANT:  # 只有处在变式关的题才有变式组成绩
            return s
        followups = s.followups + (1 if e.set_kind == "followup" else 0)
        need = cfg.initial_pass if e.set_kind == "initial" else cfg.followup_pass
        if e.correct >= need and e.key_ok:
            interval = cfg.min_interval_days_exam if e.exam_soon else cfg.min_interval_days
            return replace(s, status=TO_REVIEW, gates=replace(s.gates, variant=True), followups=followups,
                           variant_passed_at=on.isoformat(), next_review_at=(on + timedelta(days=interval)).isoformat())
        if followups >= cfg.max_followups:
            return replace(s, status=STUBBORN, followups=followups)
        return replace(s, status=TO_TUTOR, followups=followups)

    if e.kind == "REVIEW_RESULT":
        if e.result != "correct":
            return _reflow(s)
        if s.status == TO_REVIEW and s.variant_passed_at:
            interval = cfg.min_interval_days_exam if e.exam_soon else cfg.min_interval_days
            waited = (on - date.fromisoformat(s.variant_passed_at)).days
            if waited >= interval:
                return replace(s, status=MASTERED, gates=replace(s.gates, spaced=True), next_review_at=None,
                               mastered_at=on.isoformat())
        return s  # 间隔不够（比如提前打印了），只记录，不改状态

    if e.kind == "RETRY":  # 家长对顽固错题点"再试一次"
        if s.status == STUBBORN:
            return replace(s, status=TO_VARIANT, followups=0)
        return s

    raise ValueError(f"unknown event {e.kind}")


def apply_print_result(s: State, result: str, cfg: MasteryConfig, on: date, *, exam_soon: bool = False) -> State:
    """打印单（重做单、考前错题集、每日学透单）上原题的结果，按题目当前所处的关卡解释。"""
    return apply(s, Event("REDO_RESULT", result=result, exam_soon=exam_soon), cfg, on)


# ---------------------------------------------------------------- 与数据库模型互转


def read_state(m) -> State:  # noqa: ANN001 —— app.models.Mistake
    g = m.gates or {}
    return State(status=m.status, round=m.round,
                 gates=Gates(bool(g.get("original")), bool(g.get("variant")), bool(g.get("spaced"))),
                 wrong_count=m.wrong_count, followups=m.followups, variant_passed_at=m.variant_passed_at,
                 next_review_at=m.next_review_at, mastered_at=m.mastered_at)


def write_state(m, s: State) -> None:  # noqa: ANN001
    m.status = s.status
    m.round = s.round
    m.gates = {"original": s.gates.original, "variant": s.gates.variant, "spaced": s.gates.spaced}
    m.wrong_count = s.wrong_count
    m.followups = s.followups
    m.variant_passed_at = s.variant_passed_at
    m.next_review_at = s.next_review_at
    m.mastered_at = s.mastered_at
