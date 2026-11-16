"""Calculus engine: correctness, fail-closed behaviour, planted wrong key."""
import json
from pathlib import Path

import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record
from cqse.math.calculus import solve_and_verify

ROOT = Path(__file__).resolve().parents[1]


def _ok(r):
    return r.value is not None and all(x.is_affirmative() for x in r.records if x.hard)


def test_area_abs_and_sqrt():
    r = solve_and_verify({"kind": "area_region", "region": ["Abs(x-y) <= y <= 4*sqrt(x)"]})
    assert _ok(r) and r.value == sp.Rational(1024, 3)
    assert any(x.status == CheckStatus.NUMERICALLY_CHECKED and x.numeric_evidence_sufficient for x in r.records)


def test_area_max_curve_and_target():
    r = solve_and_verify({"kind": "area_region", "region": ["0 <= y <= Max(Abs(x), x*Abs(x-2))", "-2 <= x <= 4"],
                          "target": "3*A"})
    assert _ok(r) and r.value == 36


def test_area_template_match():
    r = solve_and_verify({"kind": "area_region", "region": ["x^2 + y^2 <= 25"], "split": "y >= Abs(x-1)",
                          "portion": "larger",
                          "match": {"template": "(b*pi + c)/4", "unknowns": {"b": "natural", "c": "natural"},
                                    "basis": ["pi"], "answer": "b + c"}})
    assert _ok(r) and r.value == 77


def test_area_parameter_solve():
    r = solve_and_verify({"kind": "area_region", "params": {"a": "a > 0"},
                          "region": ["-1 <= x <= 1", "0 <= y <= a + exp(Abs(x)) - exp(-x)"],
                          "equations": ["A = (E^2 + 8*E + 1)/E"], "param_sample": {"a": "1"}, "target": "a"})
    assert _ok(r) and r.value == 5


def test_unbounded_region_fails_closed():
    r = solve_and_verify({"kind": "area_region", "region": ["y >= x^2"]})
    assert r.value is None and r.records[0].status == CheckStatus.UNRESOLVED
    assert "unbounded" in r.records[0].result


def test_equal_portions_ambiguous():
    r = solve_and_verify({"kind": "area_region", "region": ["x^2 + y^2 <= 1"], "split": "y >= 0",
                          "portion": "larger"})
    assert r.value is None


def test_equality_is_not_a_region():
    assert solve_and_verify({"kind": "area_region", "region": ["y = x^2"]}).value is None


def test_extrema_counts_integral_defined():
    r = solve_and_verify({"kind": "extrema",
                          "defs": {"f": {"integral": "(t^2-8*t+15)/exp(t)", "t": "t", "lower": "0",
                                         "upper": "x^2"}},
                          "quantities": [{"name": "p", "op": "extrema", "fn": "f", "kind": "max", "return": "count"},
                                         {"name": "q", "op": "extrema", "fn": "f", "kind": "min", "return": "count"}],
                          "target": "10*p + q"})
    assert _ok(r) and r.value == 23


def test_extrema_corners():
    r = solve_and_verify({"kind": "extrema", "defs": {"f": "Abs(Abs(x+2) - 2*Abs(x))"},
                          "quantities": [{"name": "m", "op": "extrema", "fn": "f", "kind": "min",
                                          "return": "points"}], "target": "0"})
    assert _ok(r)


def test_constant_function_fails_closed():
    r = solve_and_verify({"kind": "extrema", "defs": {"f": "Abs(x) - Abs(x) + 3"},
                          "quantities": [{"name": "n", "op": "extrema", "fn": "f", "return": "count"}],
                          "target": "n"})
    assert r.value is None


def test_unattained_max_fails_closed():
    r = solve_and_verify({"kind": "calculus_value", "defs": {"f": "x"},
                          "quantities": [{"name": "M", "op": "abs_max", "fn": "f", "interval": ["0", "1"],
                                          "closed": [True, False]}], "target": "M"})
    assert r.value is None


def test_params_with_limit_condition():
    r = solve_and_verify({"kind": "calculus_value",
                          "params": {"c4": "c4 != 0", "c3": None, "c2": None, "c1": None, "c0": None},
                          "defs": {"f": "c4*x^4 + c3*x^3 + c2*x^2 + c1*x + c0"},
                          "equations": ["df(4) = 0", "df(5) = 0", {"limit": "f(x)/x^2", "at": "0", "equals": "5"}],
                          "target": "f(2)"})
    assert _ok(r) and r.value == 10


def test_no_admissible_parameter_fails_closed():
    r = solve_and_verify({"kind": "calculus_value", "params": {"a": "a > 0"}, "defs": {"f": "a*x^2"},
                          "equations": ["df(1) = -2"], "target": "a"})
    assert r.value is None


def test_planted_wrong_key_detected():
    from data.pyq.run_formals import attach, load_formals  # noqa: PLC0415
    formals = load_formals("maths_calculus")
    rec = next(json.loads(l) for l in (ROOT / "data/pyq/ascent_maths.jsonl").read_text().splitlines()
               if json.loads(l)["pyq_id"] == "ASCENT-m9gxgbr9")
    rec["answer_key"] = "A"  # true answer is D (1024/3)
    rec2, _ = attach(rec, formals["m9gxgbr9"])
    r = ingest_record(PYQRecord(**rec2))
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in r.statuses
