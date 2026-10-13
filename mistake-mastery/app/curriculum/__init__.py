"""知识点树与字典：从本目录的 YAML 加载（通用资料，可以公开）。"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).parent
SUBJECTS = ("math", "physics")


@dataclass(frozen=True)
class KP:
    code: str
    subject: str
    name: str
    parent_code: str | None
    level: int
    bj_weight: float | None
    verified: bool = True


@dataclass
class Curriculum:
    kps: dict[str, KP] = field(default_factory=dict)
    error_causes: list[dict] = field(default_factory=list)
    question_types: list[dict] = field(default_factory=list)
    bj_slots: list[dict] = field(default_factory=list)
    source_kinds: list[dict] = field(default_factory=list)

    def for_subject(self, subject: str) -> list[KP]:
        return [k for k in self.kps.values() if k.subject == subject]

    def l1_of(self, code: str) -> KP | None:
        kp = self.kps.get(code)
        while kp and kp.parent_code:
            kp = self.kps.get(kp.parent_code)
        return kp

    def weight_of(self, code: str) -> float:
        l1 = self.l1_of(code)
        return (l1.bj_weight if l1 and l1.bj_weight is not None else 0.5)

    def path_name(self, code: str) -> str:
        names = []
        kp = self.kps.get(code)
        while kp:
            names.append(kp.name)
            kp = self.kps.get(kp.parent_code) if kp.parent_code else None
        return " › ".join(reversed(names))

    def causes_for(self, subject: str) -> list[dict]:
        return [c for c in self.error_causes if c["subject"] in ("all", subject)]

    def slots_for(self, subject: str) -> list[dict]:
        return [s for s in self.bj_slots if s["subject"] == subject]


def _walk(nodes: list[dict], subject: str, parent: str | None, level: int, inherited_w: float | None,
          out: dict[str, KP]) -> None:
    for n in nodes:
        w = n.get("bj_weight", inherited_w)
        code = n["code"]
        if code in out:
            raise ValueError(f"duplicate knowledge point code: {code}")
        out[code] = KP(code, subject, n["name"], parent, level, w, n.get("verified", True))
        _walk(n.get("children", []), subject, code, level + 1, w, out)


@lru_cache
def load() -> Curriculum:
    cur = Curriculum()
    for subject in SUBJECTS:
        data = yaml.safe_load((HERE / f"{subject}.yaml").read_text(encoding="utf-8"))
        assert data["subject"] == subject
        _walk(data["nodes"], subject, None, 1, None, cur.kps)
    d = yaml.safe_load((HERE / "dictionaries.yaml").read_text(encoding="utf-8"))
    cur.error_causes = d["error_causes"]
    cur.question_types = d["question_types"]
    cur.bj_slots = d["bj_slots"]
    cur.source_kinds = d["source_kinds"]
    return cur
