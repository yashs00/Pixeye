"""Regression tests from the JEE Main 2026-04-02 S1 reference paper."""
import json
from pathlib import Path

import pytest
import sympy as sp

from cqse.core.problem import Answer, Identity, Option, ProblemState, QuestionFormat, Subject
from cqse.generic.system import solve_system
from cqse.ingest.pyq import IngestStatus, ingest_file
from cqse.math.expr import parse, tri_equal
from cqse.verification.options import check_options_and_key

PAPER = Path(__file__).parent.parent / "data/pyq/jee_main_2026_04_02_s1.jsonl"
HAND = {"Q01": "2", "Q27": "B", "Q30": "B", "Q31": "C", "Q32": "B", "Q34": "D", "Q35": "D", "Q40": "B",
        "Q42": "B", "Q43": "A", "Q44": "C", "Q45": "B", "Q46": "36", "Q47": "120", "Q48": "171", "Q49": "3",
        "Q50": "387", "Q51": "D", "Q52": "C", "Q54": "D", "Q55": "D", "Q71": "33", "Q73": "17", "Q74": "41",
        "Q75": "727"}


def test_whole_reference_subset_verifies_and_matches_hand_solutions():
    res = {r.pyq_id[-3:]: r for r in ingest_file(PAPER)}
    assert set(res) == set(HAND)
    for q, r in res.items():
        assert IngestStatus.PARENT_VERIFIED in r.statuses, (q, r.notes)
        assert IngestStatus.NEEDS_OFFICIAL_KEY in r.statuses          # never treated as official
        assert IngestStatus.NEEDS_SOURCE in r.statuses                # rights not yet confirmed
        assert not any("disagree" in n.lower() for n in r.notes)


def test_printed_decimals_are_exact():
    assert parse("1.962*10**-17") == sp.Rational(981, 5 * 10**19)
    assert tri_equal(parse("0.1 + 0.2"), parse("0.3")) is True        # binary floats would fail this


def _mcq(values, key, formal):
    return ProblemState(identity=Identity(problem_id="T"), subject=Subject.PHYSICS,
                        exam_profile_id="JEE_MAIN-2027-v1", question_format=QuestionFormat.SINGLE_CORRECT_MCQ,
                        formal=formal, options=[Option(option_id=i, value=v) for i, v in zip("ABCD", values)],
                        answer=Answer(correct_option_ids=[key]))


def test_rounded_options_unique_match_and_ambiguity():
    f = {"kind": "x", "options_rounded": {"rel_tol": "0.02"}}
    exact = sp.Rational(-17, 45)                                       # -0.3778 (Bohr, Q44)
    ok = check_options_and_key(_mcq(["-1.51", "-0.85", "-0.38", "-0.28"], "C", f), exact)
    assert all(r.is_affirmative() for r in ok)
    amb = check_options_and_key(_mcq(["-0.38", "-0.37", "-0.85", "-0.28"], "A", f), exact)  # two options close
    assert any(r.status.value == "FAILED" for r in amb)
    wrong = check_options_and_key(_mcq(["-1.51", "-0.85", "-0.38", "-0.28"], "D", f), exact)
    assert any(r.check_id == "key.matches_derivation" and r.status.value == "FAILED" for r in wrong)


def test_nearest_integer_rule_and_boundary_guard():
    item = ProblemState(identity=Identity(problem_id="N"), subject=Subject.PHYSICS,
                        exam_profile_id="JEE_MAIN-2027-v1", question_format=QuestionFormat.NUMERICAL_INTEGER,
                        formal={"kind": "x"}, answer=Answer(exact_answer="36"))
    assert all(r.is_affirmative() for r in check_options_and_key(item, 2826 / (25 * sp.pi), "nearest_integer"))
    assert any(r.status.value == "FAILED" for r in check_options_and_key(item, 2826 / (25 * sp.pi)))  # no rule
    item.answer.exact_answer = "36"
    boundary = check_options_and_key(item, sp.Rational(7101, 200), "nearest_integer")             # 35.505
    assert any(r.check_id == "numerical.rounding" and r.status.value == "FAILED" for r in boundary)


def test_symbolic_knowns_must_cancel():
    K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
    f = {"kind": "equation_system", "knowns": {"M": K("symbolic", "kg"), "R": K("symbolic", "m"),
                                               "G": K("symbolic", "N*m^2/kg^2")},
         "unknowns": {"T": {"unit": "s", "domain": "positive"}},
         "equations": ["T**2*G*M = 4*pi**2*R**3"], "target": "T"}
    s = solve_system(f)                       # T depends on M and R: not a number -> must fail
    assert s.value is None
    assert any(r.status.value == "FAILED" and "depends on" in r.result for r in s.records)


def test_integer_domain_selects_the_integer_root():
    U = lambda d: {"unit": "", "domain": d}  # noqa: E731
    f = {"kind": "equation_system", "knowns": {}, "unknowns": {"n": U("natural")},
         "equations": ["2*n**2 - 13*n + 15 = 0"], "target": "n"}       # roots 5 and 3/2
    assert solve_system(f).value == 5
