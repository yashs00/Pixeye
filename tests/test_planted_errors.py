"""Verifier regression: known-good items pass; every planted defect is blocked.

Target (blueprint 41): ZERO false accepts on this suite. Passing it does not
prove that all possible defects are detectable.
"""
import pytest

from cqse.core.problem import Option, QuestionFormat
from cqse.verification.pipeline import software_blocking, verify_item


def passes(item):
    rep = verify_item(item)
    return not software_blocking(rep), rep


def test_known_good_items_pass(good_item):
    ok, rep = passes(good_item)
    assert ok, rep.summary()


def _wrong_ids(item):
    return [o.option_id for o in item.options if o.option_id not in item.answer.correct_option_ids]


# ---------------- mutation operators: each produces a defective copy
def m_wrong_key(it):
    it.answer.correct_option_ids = [_wrong_ids(it)[0]]


def m_two_keys(it):
    it.answer.correct_option_ids = it.answer.correct_option_ids + [_wrong_ids(it)[0]]


def m_distractor_becomes_correct(it):
    wid = _wrong_ids(it)[0]
    for o in it.options:
        if o.option_id == wid:
            o.value = it.answer.exact_answer  # hidden second correct answer


def m_equivalent_duplicate(it):
    # rewrite a distractor as an equivalent form of another distractor (e.g. 2 vs 4/2)
    a, b = _wrong_ids(it)[:2]
    va = next(o.value for o in it.options if o.option_id == a)
    for o in it.options:
        if o.option_id == b:
            o.value = f"2*({va})/2"


def m_edit_stem(it):
    it.stem = it.stem.replace("Find", "Find approximately", 1) + " "


def m_change_formal_number(it):
    f = it.formal
    if f["kind"] == "equation":
        f["rhs"] = "1" if f["rhs"] != "1" else "2"
    elif f["kind"] == "projectile_level":
        f["u"] = "25"
    elif f["kind"] == "incline_friction":
        f["m"] = "3"
    else:
        f["given"]["H2"]["mass_g"] = "2"


def m_drop_distractor_trace(it):
    it.distractors = it.distractors[1:]


def m_garbage_option(it):
    it.options[0].value = "__import__('os')"


def m_wrong_units(it):
    if it.answer.units:
        it.answer.units = "cm"
    else:
        it.answer.correct_option_ids = []


def m_unconfirmed_profile(it):
    it.exam_profile_id = "JEE_ADVANCED-2027-v0"


def m_unknown_profile(it):
    it.exam_profile_id = "JEE_MAIN-2031-v9"


def m_option_count(it):
    it.options.append(Option(option_id="E", value="999999", display="999999"))


def m_format_not_in_profile(it):
    it.question_format = QuestionFormat.MULTIPLE_CORRECT_MCQ


MUTATIONS = [m_wrong_key, m_two_keys, m_distractor_becomes_correct, m_equivalent_duplicate, m_edit_stem,
             m_change_formal_number, m_drop_distractor_trace, m_garbage_option, m_wrong_units,
             m_unconfirmed_profile, m_unknown_profile, m_option_count, m_format_not_in_profile]


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.__name__)
def test_planted_defect_is_blocked(good_item, mutation):
    bad = good_item.model_copy(deep=True)
    try:
        mutation(bad)
    except Exception:  # noqa: BLE001
        pytest.skip("mutation not applicable")
    # Re-validate structure the way a loader would; a structurally invalid item is also a block.
    try:
        bad = type(bad)(**bad.model_dump())
    except Exception:  # noqa: BLE001
        return
    ok, rep = passes(bad)
    assert not ok, f"FALSE ACCEPT for {mutation.__name__}:\n{rep.summary()}"


def test_numerical_non_integer_answer_blocked():
    from cqse.core.problem import Subject
    from cqse.verification.pipeline import build_item
    it = build_item("N1", Subject.PHYSICS, dict(kind="projectile_level", u="20", theta_deg="30", g="10",
                                                target="range"), "JEE_MAIN-2027-v1",
                    question_format=QuestionFormat.NUMERICAL_INTEGER)
    ok, rep = passes(it)  # 20*sqrt(3) is not an integer -> rounding ambiguity -> blocked
    assert not ok


def test_numerical_wrong_declared_answer_blocked():
    from cqse.core.problem import Subject
    from cqse.verification.pipeline import build_item
    it = build_item("N2", Subject.PHYSICS, dict(kind="projectile_level", u="20", theta_deg="30", g="10",
                                                target="max_height"), "JEE_MAIN-2027-v1",
                    question_format=QuestionFormat.NUMERICAL_INTEGER)
    assert passes(it)[0]
    it.answer.exact_answer = "6"
    assert not passes(it)[0]
