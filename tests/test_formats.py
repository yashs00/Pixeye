"""Option-format engine: option-text parsing, code derivation, and the full key check through ingest."""
import json
from pathlib import Path

import sympy as sp

from cqse.core.problem import Subject
from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record
from cqse.verification.formats import option_code, solve_and_verify

C = lambda t: {"truth": t, "basis": "curated", "note": "test"}  # noqa: E731


def test_option_text_parsing():
    assert option_code("select_combination", "A, D and E Only") == "{1, 4, 5}"
    assert option_code("select_combination", "<p>(B), (C) and (E) only</p>") == "{2, 3, 5}"
    assert option_code("statement_pair", "Statement I is true but Statement II is false") == "10"
    assert option_code("statement_pair", "Statement I is false but Statement II is true") == "1"
    assert option_code("statement_pair", "Both Statement I and Statement II are incorrect") == "0"
    assert option_code("statement_pair", "<b>Both Statement I and Statement II are correct</b>") == "11"
    assert option_code("match_list", "(A)-(III), (B)-(I), (C)-(IV), (D)-(II)") == "3142"
    assert option_code("match_list", "A-IV, B-III, C-II, D-I") == "4321"
    assert option_code("assertion_reason", "Both A and R are true but R is NOT the correct explanation of A") == "2"
    assert option_code("assertion_reason", "A is true but R is false") == "1"
    assert option_code("assertion_reason", "A is false but R is true") == "4"


def test_codes():
    r = solve_and_verify({"format": "select_combination",
                          "statements": {"A": C(True), "B": C(False), "C": C(True)}}, Subject.CHEMISTRY)
    assert r.value == sp.FiniteSet(1, 3)
    r = solve_and_verify({"format": "assertion_reason", "statements": {"A": C(True), "R": C(True)},
                          "explains": C(False)}, Subject.PHYSICS)
    assert r.value == 2
    r = solve_and_verify({"format": "ordering", "order": {"items": ["p", "q", "r"], "values": {"p": 3, "q": 1, "r": 2},
                                                          "direction": "increasing", "basis": "curated"}}, None)
    assert r.value == 231


def test_false_pairing_and_missing_truth_fail_closed():
    r = solve_and_verify({"format": "match_list", "pairs": {"A": ["I", C(False)], "B": ["II", C(True)]}}, None)
    assert r.value is None
    r = solve_and_verify({"format": "statement_pair", "statements": {"I": C(True), "II": {}}}, None)
    assert r.value is None


def _rec(key):
    return PYQRecord(**{
        "pyq_id": "T-1", "exam": "JEE_MAIN", "year": 2025, "subject": "CHEMISTRY",
        "question_format": "single_correct_mcq", "stem": "Two statements ...",
        "options": [{"id": i, "text": t, "value": option_code("statement_pair", t)} for i, t in
                    zip("ABCD", ["Both Statement I and Statement II are true",
                                 "Statement I is true but Statement II is false",
                                 "Statement I is false but Statement II is true",
                                 "Both Statement I and Statement II are false"])],
        "answer_key": key, "key_source": "provisional",
        "source": {"document": "t", "rights_status": "CLEARED", "permitted_uses": ["derive"], "rights_basis": "test"},
        "formal": {"kind": "statement_set", "format": "statement_pair", "statements": {"I": C(True), "II": C(False)}}})


def test_key_check_through_ingest():
    ok = ingest_record(_rec("B"))
    assert IngestStatus.PARENT_VERIFIED in ok.statuses and IngestStatus.NEEDS_EXPERT_REVIEW in ok.statuses
    bad = ingest_record(_rec("A"))
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in bad.statuses


def test_engine_computed_truth_is_rule_checked():
    K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
    sub = {"kind": "equation_system", "knowns": {"a": K("3")}, "unknowns": {"x": {"unit": "", "domain": "real"}},
           "equations": ["x = 2*a"], "target": "x"}
    r = solve_and_verify({"format": "statement_pair",
                          "statements": {"I": {"formal": sub, "claim": "== 6", "subject": "MATHEMATICS"},
                                         "II": {"formal": sub, "claim": "> 7", "subject": "MATHEMATICS"}}}, None)
    assert r.value == 10
    assert all(rec.status.value != "UNRESOLVED" for rec in r.records if rec.check_id == "statement.truth")


def test_sub_model_teacher_check_is_propagated():
    K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
    sub = {"kind": "equation_system", "knowns": {"a": K("3")}, "unknowns": {"x": {"unit": "", "domain": "real"}},
           "equations": ["x = 2*a"], "target": "x", "model": ["x is twice a"]}
    r = solve_and_verify({"format": "statement_pair",
                          "statements": {"I": {"formal": sub, "claim": "== 6"}, "II": C(False)}}, None)
    assert any(rec.check_id == "model.correspondence" for rec in r.records)
