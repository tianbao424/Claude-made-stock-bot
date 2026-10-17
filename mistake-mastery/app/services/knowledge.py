"""知识点整理：从知识点的角度看错题，找出掌握死角。掌握度算法见 docs/06 §6。

- 掌握度：每次作答（录入时做错、重做、复习……）是一次观测，近期的、难题的、主知识点的观测权重更高；
  加一个"相当于 2 次半对"的先验，样本少时分数不会大起大落。没有任何观测的知识点不打分。
- 上级知识点（模块、主题）的掌握度由下面所有考点的观测汇总得到。
- 掌握死角：未学透、顽固、反复错的题多，掌握度低，中考又常考的考点排在前面，并说明原因。
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func

from app.models import Attempt, BankItem, BankPaper, Mistake, Question, QuestionKp
from app.services import mastery as m

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.curriculum import Curriculum

TAU_DAYS = 21.0  # 近期表现权重更高：21 天前的观测权重约为今天的 1/e
ALPHA = 2.0  # 先验：相当于 2 次"半对"
SECONDARY = 0.5  # 次知识点的权重
RESULT_SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
WEAK, GOOD = 0.4, 0.7  # < 0.4 薄弱；0.4–0.7 待加强；> 0.7 较好
OPEN = {m.TO_REDO, m.TO_TUTOR, m.TO_VARIANT, m.TO_REVIEW, m.STUBBORN}
FREQUENT = 0.6  # 模块的中考权重达到这个值算"常考"


@dataclass
class KpStat:
    code: str
    sw: float = 0.0  # Σ wᵢ
    swr: float = 0.0  # Σ wᵢ·rᵢ
    observations: int = 0
    mistakes: set = field(default_factory=set)
    open: set = field(default_factory=set)
    mastered: set = field(default_factory=set)
    stubborn: set = field(default_factory=set)
    repeat: set = field(default_factory=set)  # 错了不止一次或回炉过
    causes: Counter = field(default_factory=Counter)
    last_wrong_at: str | None = None

    @property
    def mastery(self) -> float | None:
        if not self.observations:
            return None
        return (self.swr + ALPHA * 0.5) / (self.sw + ALPHA)


def level_of(score: float | None) -> str:
    if score is None:
        return "none"
    return "weak" if score < WEAK else "medium" if score <= GOOD else "good"


def _ancestors(cur: "Curriculum", code: str) -> list[str]:
    out = []
    kp = cur.kps.get(code)
    while kp is not None:
        out.append(kp.code)
        kp = cur.kps.get(kp.parent_code) if kp.parent_code else None
    return out


def _age_days(iso: str, now: datetime) -> float:
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return 0.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return max(0.0, (now - t).total_seconds() / 86400)


def compute(s: "Session", cur: "Curriculum", student_id: str, subject: str,
            now: datetime | None = None) -> dict[str, KpStat]:
    """这个孩子在这一科每个知识点（含上级）的统计。只返回有数据的知识点。"""
    now = now or datetime.now(timezone.utc)
    stats: dict[str, KpStat] = {}

    def st(code: str) -> KpStat:
        return stats.setdefault(code, KpStat(code))

    rows = (s.query(Mistake, Question).join(Question, Mistake.question_id == Question.id)
            .filter(Mistake.student_id == student_id, Question.subject == subject).all())
    qids = {q.id for _, q in rows}
    qkps: dict[str, list[tuple[str, bool]]] = {}
    if qids:
        for k in s.query(QuestionKp).filter(QuestionKp.question_id.in_(qids)):
            if k.kp_code in cur.kps:
                qkps.setdefault(k.question_id, []).append((k.kp_code, bool(k.is_primary)))

    # 每道错题对它的每个知识点（及上级）只算一次；同一上级下有主、次两个知识点时取主
    node_weight: dict[str, dict[str, float]] = {}
    for mk, q in rows:
        weights: dict[str, float] = {}
        for code, primary in qkps.get(q.id, []):
            for node in _ancestors(cur, code):
                weights[node] = max(weights.get(node, 0.0), 1.0 if primary else SECONDARY)
        node_weight[mk.id] = weights
        for node in weights:
            x = st(node)
            x.mistakes.add(mk.id)
            if mk.status in OPEN:
                x.open.add(mk.id)
            if mk.status == m.MASTERED:
                x.mastered.add(mk.id)
            if mk.status == m.STUBBORN:
                x.stubborn.add(mk.id)
            if mk.wrong_count >= 2 or mk.round > 1:
                x.repeat.add(mk.id)
            x.causes.update(mk.error_causes or [])
            if x.last_wrong_at is None or mk.last_wrong_at > x.last_wrong_at:
                x.last_wrong_at = mk.last_wrong_at

    difficulty = {q.id: q.difficulty for _, q in rows}
    mistake_q = {mk.id: q.id for mk, q in rows}
    if node_weight:
        for a in s.query(Attempt).filter(Attempt.mistake_id.in_(list(node_weight))):
            r = RESULT_SCORE.get(a.result)
            if r is None:
                continue
            d = 0.8 + 0.1 * (difficulty.get(mistake_q.get(a.mistake_id)) or 3)  # 难题做对更能说明问题
            decay = math.exp(-_age_days(a.created_at, now) / TAU_DAYS)
            for node, c in node_weight[a.mistake_id].items():
                w = c * d * decay
                x = st(node)
                x.sw += w
                x.swr += w * r
                x.observations += 1
    return stats


def _bank_counts(s: "Session", subject: str) -> list[tuple[str, int]]:
    return (s.query(QuestionKp.kp_code, func.count(QuestionKp.question_id))
            .join(Question, QuestionKp.question_id == Question.id)
            .filter(Question.origin == "bank", Question.subject == subject, QuestionKp.is_primary == 1)
            .group_by(QuestionKp.kp_code).all())


def _cause_names(cur: "Curriculum", subject: str) -> dict[str, str]:
    return {c["code"]: c["name"] for c in cur.causes_for(subject)}


def blind_spots(cur: "Curriculum", subject: str, stats: dict[str, KpStat], bank: dict[str, int],
                limit: int = 8) -> list[dict]:
    """掌握死角：只看最细一级的考点。"""
    parents = {k.parent_code for k in cur.for_subject(subject) if k.parent_code}
    names = _cause_names(cur, subject)
    out = []
    for code, x in stats.items():
        kp = cur.kps.get(code)
        if kp is None or code in parents:
            continue
        score = x.mastery
        if not x.open and (score is None or score >= WEAK):
            continue  # 错题都学透了，掌握度也不低
        weight = kp.bj_weight if kp.bj_weight is not None else 0.5
        risk = (len(x.open) + 2 * len(x.stubborn) + len(x.repeat) + 3 * (1 - (score if score is not None else 0.5)))
        risk *= 0.6 + weight
        reasons = []
        if x.open:
            reasons.append(f"{len(x.open)} 道未学透")
        if x.stubborn:
            reasons.append(f"{len(x.stubborn)} 道顽固错题")
        if x.repeat:
            reasons.append(f"{len(x.repeat)} 道反复错")
        if score is not None and score < WEAK:
            reasons.append("最近做得不好")
        if weight >= FREQUENT:
            reasons.append("中考常考")
        top = [c for c, _ in x.causes.most_common(2) if c in names]
        if top:
            reasons.append("主要错因：" + "、".join(names[c] for c in top))
        out.append({**node_json(cur, code, x, bank), "subject": subject, "path": cur.path_name(code),
                    "risk": round(risk, 2), "reasons": reasons})
    out.sort(key=lambda b: (-b["risk"], b["code"]))
    return out[:limit]


def untouched(cur: "Curriculum", subject: str, stats: dict[str, KpStat], bank: dict[str, int],
              limit: int = 10) -> list[dict]:
    """中考常考、但还没有任何错题记录的考点。可能是掌握了，也可能是还没学到、没考到。"""
    parents = {k.parent_code for k in cur.for_subject(subject) if k.parent_code}
    out = [{"code": k.code, "name": k.name, "path": cur.path_name(k.code), "weight": k.bj_weight,
            "bank": bank.get(k.code, 0)}
           for k in cur.for_subject(subject)
           if k.code not in parents and k.code not in stats and (k.bj_weight or 0) >= FREQUENT]
    out.sort(key=lambda u: (-(u["weight"] or 0), -u["bank"], u["code"]))
    return out[:limit]


def node_json(cur: "Curriculum", code: str, x: KpStat | None, bank: dict[str, int]) -> dict:
    """一个知识点的统计。bank：题库里这个知识点有多少道题（提示"有同类真题可以练"）。"""
    kp = cur.kps[code]
    score = x.mastery if x else None
    return {
        "code": code, "name": kp.name, "level": kp.level, "weight": kp.bj_weight,
        "mastery": round(score, 3) if score is not None else None, "status": level_of(score),
        "observations": x.observations if x else 0, "mistakes": len(x.mistakes) if x else 0,
        "open": len(x.open) if x else 0, "mastered": len(x.mastered) if x else 0,
        "stubborn": len(x.stubborn) if x else 0, "repeat": len(x.repeat) if x else 0,
        "bank": bank.get(code, 0), "last_wrong_at": x.last_wrong_at if x else None,
    }


def tree(cur: "Curriculum", subject: str, stats: dict[str, KpStat], bank: dict[str, int]) -> list[dict]:
    """整棵知识点树，每个节点带统计（没有数据的节点也列出来，前端显示为灰色）。"""
    children: dict[str | None, list[str]] = {}
    for k in cur.for_subject(subject):
        children.setdefault(k.parent_code, []).append(k.code)

    def build(code: str) -> dict:
        node = node_json(cur, code, stats.get(code), bank)
        node["children"] = [build(c) for c in children.get(code, [])]
        return node

    return [build(c) for c in children.get(None, [])]


def similar_bank(s: "Session", code: str, subject: str, limit: int = 20) -> list[tuple[dict, Question]]:
    """题库里这个知识点（含下级）的题：以它为主知识点的、年份新的在前，孩子已经做错过的排在后面。"""
    done = {(q.bank_match or {}).get("question_id") for q in s.query(Question).filter(
        Question.origin == "captured", Question.subject == subject, Question.bank_match.isnot(None))}
    rows = (s.query(QuestionKp, BankItem, BankPaper, Question)
            .join(BankItem, BankItem.question_id == QuestionKp.question_id)
            .join(BankPaper, BankPaper.id == BankItem.paper_id)
            .join(Question, Question.id == BankItem.question_id)
            .filter((QuestionKp.kp_code == code) | QuestionKp.kp_code.like(f"{code}.%")).all())
    seen, out = set(), []
    for k, item, paper, q in sorted(rows, key=lambda r: (r[1].question_id in done, not r[0].is_primary,
                                                         -(r[2].year or 0), r[1].seq)):
        if item.question_id in seen:
            continue
        seen.add(item.question_id)
        out.append(({"id": item.question_id, "paper_id": paper.id, "paper_title": paper.title,
                     "number_label": item.number_label, "primary": bool(k.is_primary),
                     "done": item.question_id in done}, q))
    return out[:limit]


def bank_rollup(cur: "Curriculum", s: "Session", subject: str) -> dict[str, int]:
    """题库里每个知识点（含上级）有多少道题（按主知识点算）。"""
    out: Counter = Counter()
    for code, n in _bank_counts(s, subject):
        for node in _ancestors(cur, code):
            out[node] += n
    return dict(out)
