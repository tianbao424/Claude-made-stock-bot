"""状态机：逐条覆盖 docs/06 §2.3 的事件规则，再用随机事件序列检查不变式。"""

import random
from datetime import date, timedelta

import pytest

from app.services.mastery import (MASTERED, STATUSES, STUBBORN, TO_REDO, TO_REVIEW, TO_TUTOR, TO_VARIANT, Event,
                                  MasteryConfig, State, apply, apply_print_result, new_mistake_state)

CFG = MasteryConfig()
D0 = date(2026, 10, 13)


def run(events: list[Event], start: State | None = None, on: date = D0) -> State:
    s = start or new_mistake_state()
    for e in events:
        s = apply(s, e, CFG, on)
    return s


def redo(result: str) -> Event:
    return Event("REDO_RESULT", result=result)


def scored(set_kind: str, correct: int, key_ok: bool = True) -> Event:
    return Event("VARIANT_SET_SCORED", set_kind=set_kind, correct=correct, key_ok=key_ok)


def test_new_mistake_starts_at_redo():
    s = new_mistake_state()
    assert (s.status, s.round, s.wrong_count) == (TO_REDO, 1, 1)


def test_redo_correct_passes_original_gate():
    s = run([redo("correct")])
    assert s.status == TO_VARIANT and s.gates.original


@pytest.mark.parametrize("result", ["wrong", "partial"])
def test_redo_wrong_or_partial_goes_to_tutor(result):
    s = run([redo(result)])
    assert s.status == TO_TUTOR and s.wrong_count == 2 and not s.gates.original


def test_tutor_done_returns_to_redo_or_variant():
    assert run([redo("wrong"), Event("TUTOR_DONE")]).status == TO_REDO
    s = run([redo("correct"), scored("initial", 2), Event("TUTOR_DONE")])
    assert s.status == TO_VARIANT


def test_initial_set_needs_four_and_synthesis():
    base = [redo("correct")]
    assert run(base + [scored("initial", 4)]).status == TO_REVIEW
    assert run(base + [scored("initial", 5, key_ok=False)]).status == TO_TUTOR
    assert run(base + [scored("initial", 3)]).status == TO_TUTOR


def test_followups_capped_then_stubborn():
    s = run([redo("correct"), scored("initial", 2), Event("TUTOR_DONE"), scored("followup", 1),
             Event("TUTOR_DONE"), scored("followup", 1)])
    assert s.status == STUBBORN and s.followups == 2
    assert apply(s, Event("RETRY"), CFG, D0).status == TO_VARIANT


def test_followup_pass_needs_two_and_highest_level():
    s = run([redo("correct"), scored("initial", 2), Event("TUTOR_DONE")])
    assert apply(s, scored("followup", 2), CFG, D0).status == TO_REVIEW
    assert apply(s, scored("followup", 3, key_ok=False), CFG, D0).status == TO_TUTOR


def test_spaced_gate_requires_interval():
    s = run([redo("correct"), scored("initial", 5)])
    assert s.next_review_at == (D0 + timedelta(days=7)).isoformat()
    early = apply(s, Event("REVIEW_RESULT", result="correct"), CFG, D0 + timedelta(days=3))
    assert early.status == TO_REVIEW  # 间隔不够只记录
    done = apply(s, Event("REVIEW_RESULT", result="correct"), CFG, D0 + timedelta(days=7))
    assert done.status == MASTERED and done.gates.spaced and done.mastered_at


def test_exam_soon_compresses_interval():
    s = run([redo("correct"), Event("VARIANT_SET_SCORED", set_kind="initial", correct=5, key_ok=True,
                                    exam_soon=True)])
    assert s.next_review_at == (D0 + timedelta(days=4)).isoformat()


@pytest.mark.parametrize("result", ["wrong", "partial"])
def test_review_failure_reflows(result):
    s = run([redo("correct"), scored("initial", 5)])
    s2 = apply(s, Event("REVIEW_RESULT", result=result), CFG, D0 + timedelta(days=8))
    assert (s2.status, s2.round, s2.gates.original, s2.gates.variant) == (TO_REDO, 2, False, False)
    assert s2.wrong_count == s.wrong_count + 1


def test_confirm_again_reflows_only_after_variant_gate():
    assert run([Event("CONFIRM")]).status == TO_REDO
    assert run([Event("CONFIRM")]).wrong_count == 2
    s = run([redo("correct"), scored("initial", 5), Event("CONFIRM")])
    assert (s.status, s.round) == (TO_REDO, 2)


def test_print_result_maps_by_current_gate():
    s = new_mistake_state()
    assert apply_print_result(s, "correct", CFG, D0).status == TO_VARIANT
    v = run([redo("correct")])
    assert apply_print_result(v, "correct", CFG, D0) == v
    assert apply_print_result(v, "wrong", CFG, D0).status == TO_TUTOR
    m = apply(run([redo("correct"), scored("initial", 5)]), Event("REVIEW_RESULT", result="correct"), CFG,
              D0 + timedelta(days=8))
    assert apply_print_result(m, "wrong", CFG, D0 + timedelta(days=20)).round == 2


def test_random_sequences_keep_invariants():
    rng = random.Random(7)
    kinds = ["CONFIRM", "REDO_RESULT", "TUTOR_DONE", "VARIANT_SET_SCORED", "REVIEW_RESULT", "RETRY"]
    for _ in range(300):
        s, on, last_round = new_mistake_state(), D0, 1
        for _ in range(40):
            on += timedelta(days=rng.randint(0, 5))
            k = rng.choice(kinds)
            e = Event(k, result=rng.choice(["correct", "wrong", "partial"]),
                      set_kind=rng.choice(["initial", "followup"]), correct=rng.randint(0, 5),
                      key_ok=rng.random() < 0.6)
            s = apply(s, e, CFG, on)
            assert s.status in STATUSES
            assert s.round >= last_round
            last_round = s.round
            if s.status == MASTERED:
                assert s.gates.original and s.gates.variant and s.gates.spaced
            if s.status == TO_REVIEW:
                assert s.gates.variant and s.variant_passed_at
