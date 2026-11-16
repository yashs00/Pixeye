"""Sequences/series + statistics engine. Every expected value is hand-derived in the comment."""
import pytest
import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record
from cqse.math.series_stats import solve_and_verify, tail_bound


def run(formal):
    return solve_and_verify(formal, None)


def status(r, cid):
    return next(x.status for x in r.records if x.check_id == cid)


AP_SUM = {"kind": "series_sum", "unknowns": {"A": "real", "d": "real"}, "sequences": {"a": {"ap": ["A", "d"]}},
          "conditions": ["a(1) = 3", "Sum(a(r), r, 1, 4) = Sum(a(r), r, 5, 8)/5"],
          "target": "Sum(a(r), r, 1, 20)"}


@pytest.mark.parametrize("formal,expected", [
    # 12 + 6d = (12 + 22d)/5 -> d = -6; S20 = 10(6 - 114) = -1080
    (AP_SUM, -1080),
    # sum_{n>=1} n^2/n! = 2e (infinite: closed form + certified tail)
    ({"kind": "series_sum", "sequences": {"s": {"term": "Sum(2*j - 1, j, 1, n)/factorial(n)"}},
      "target": "Sum(s(r), r, 1, oo)"}, 2 * sp.E),
    # a_n = (3/2)^n - 1: sum_{1}^{10} = 3((3/2)^10 - 1) - 10
    ({"kind": "series_sum", "sequences": {"a": {"recurrence": "2*a(n+2) = 5*a(n+1) - 3*a(n)",
                                                "initial": {"0": "0", "1": "1/2"}}},
      "target": "Sum(a(r), r, 1, 10)"}, 3 * (sp.Rational(3, 2) ** 10 - 1) - 10),
    # A = 1+5(i-1), B = 9+7(j-1), 20 terms each: common values 16, 51, 86 -> |A u B| = 40 - 3
    ({"kind": "series_sum", "sequences": {"a": {"ap": ["1", "5"]}, "b": {"ap": ["9", "7"]}},
      "target": "NUnion(a(r), b(r), r, 1, 20)"}, 37),
    # 1/2, 1, 3/2, ..., 5: integers 1..5 -> 5
    ({"kind": "series_sum", "sequences": {"a": {"ap": ["1/2", "1/2"]}},
      "target": "CountInt(a(r), r, 1, 10)"}, 5),
    # 1/(1*2) + ... + 1/(10*11) = 10/11 -> m + n = 21
    ({"kind": "series_sum", "sequences": {"s": {"term": "1/(n*(n+1))"}},
      "target": "Numer(Sum(s(r), r, 1, 10)) + Denom(Sum(s(r), r, 1, 10))"}, 21),
    # 1, 3, 11, 25, 45, 71 (2nd differences 6): T = 3r^2 - 7r + 5, sum to 20 = 7240
    ({"kind": "series_sum", "sequences": {"s": {"fit": {"values": ["1", "3", "11", "25", "45", "71"],
                                                        "degree": 2}}},
      "target": "Sum(s(r), r, 1, 20)"}, 7240),
])
def test_series_values(formal, expected):
    r = run(formal)
    assert r.value is not None, [x.result for x in r.records]
    assert sp.simplify(r.value - expected) == 0
    assert status(r, "series.solve.primary") == CheckStatus.EXACT_CHECKED
    assert next(x for x in r.records if x.check_id == "series.solve.independent").is_affirmative()


def test_infinite_crosscheck_is_numeric_only_as_crosscheck():
    r = run({"kind": "series_sum", "target": "Sum(1/(2*k - 1)**4, k, 1, oo)"})   # pi^4/96, integral-test tail
    assert sp.simplify(r.value - sp.pi**4 / 96) == 0
    ind = next(x for x in r.records if x.check_id == "series.solve.independent")
    assert ind.status == CheckStatus.NUMERICALLY_CHECKED and ind.numeric_evidence_sufficient


@pytest.mark.parametrize("formal,expected", [
    # 8, 21, ..., 320: 25 terms of an AP, variance d^2 (n^2 - 1)/12 = 169*624/12 = 8788
    ({"kind": "statistics", "datasets": {"x": {"ap": {"first": "8", "diff": "13", "last": "320"}}},
      "target": "var(x)"}, 8788),
    # a + b = 14, a^2 + b^2 = 116, a > b -> (10, 4); n + x_n = 2, 5, 13, 11, 9 -> variance 16
    ({"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
      "datasets": {"x": {"values": ["1", "3", "a", "7", "b"]}, "y": {"transform": {"of": "x", "map": "t + i"}}},
      "conditions": ["mean(x) = 5", "var(x) = 10"], "constraints": ["a > b"], "target": "var(y)"}, 16),
    # sum 4000, sumsq 162601 -> corrected 3990, 161701: mean 39.9, var 25 -> 10(39.9 + 5) = 449
    ({"kind": "statistics", "unknowns": {"S1": "real", "S2": "real"},
      "datasets": {"w": {"aggregate": {"n": "100", "sum": "S1", "sumsq": "S2"}},
                   "c": {"replace": {"of": "w", "remove": ["50"], "add": ["40"]}}},
      "conditions": ["mean(w) = 40", "sd(w) = 5.1"], "target": "10*(mean(c) + sd(c))"}, 449),
    # 12 + (N/2 - 18) 6/12 = 14 -> N = 44
    ({"kind": "statistics", "unknowns": {"N": "natural"},
      "datasets": {"g": {"grouped_median_class": {"lower": "12", "width": "6", "freq": "12", "cf_before": "18",
                                                  "total": "N"}}},
      "conditions": ["median(g) = 14"], "target": "nobs(g)"}, 44),
    # a = b = 4 -> 2,3,3,4,4,4,5,7: mode 4, mean deviation about 4 = 8/8 = 1; median 4
    ({"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
      "datasets": {"x": {"values": ["2", "3", "3", "4", "5", "7", "a", "b"]}},
      "conditions": ["mean(x) = 4", "sd(x) = sqrt(2)"], "target": "md(x, mode(x)) + median(x)"}, 5),
])
def test_statistics_values(formal, expected):
    r = run(formal)
    assert r.value is not None, [x.result for x in r.records]
    assert sp.simplify(r.value - expected) == 0
    assert any(x.check_id == "stats.convention" and "population" in x.result for x in r.records)


# ----------------------------------------------------------------- fail closed
def test_divergent_series_blocks():
    r = run({"kind": "series_sum", "target": "Sum(1/k, k, 1, oo)"})
    assert r.value is None
    assert status(r, "series.solve.primary") == CheckStatus.FAILED


def test_divergence_detected_by_tail_test():
    k = sp.Symbol("k", integer=True)
    with pytest.raises(Exception):
        tail_bound(1 / k, k, 100)


def test_non_unique_unknowns_block():
    # without the selection rule a > b both (10, 4) and (4, 10) are admissible and a takes two values
    r = run({"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
             "datasets": {"x": {"values": ["1", "3", "a", "7", "b"]}},
             "conditions": ["mean(x) = 5", "var(x) = 10"], "target": "a"})
    assert r.value is None and status(r, "stats.solve.primary") == CheckStatus.FAILED
    # GP with a1 a5 = 28, a2 + a4 = 29 and no 'increasing' rule: ratio 2 sqrt 7 or 1/(2 sqrt 7)
    r = run({"kind": "series_sum", "unknowns": {"A": "positive", "q": "positive"},
             "sequences": {"a": {"gp": ["A", "q"]}}, "conditions": ["a(1)*a(5) = 28", "a(2) + a(4) = 29"],
             "target": "a(6)"})
    assert r.value is None


def test_symmetric_unknowns_with_single_valued_target_pass():
    # a + b = 19, ab = 84 in either order: a + b + ab = 103 is single-valued
    r = run({"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
             "datasets": {"x": {"values": ["6", "4", "a", "8", "b", "12", "10", "13"]}},
             "conditions": ["mean(x) = 9", "var(x) = 9.25"], "target": "a + b + a*b"})
    assert r.value == 103


def test_underdetermined_target_blocks():
    # one condition, two unknowns, target depends on the free parameter
    r = run({"kind": "series_sum", "unknowns": {"A": "real", "d": "real"}, "sequences": {"a": {"ap": ["A", "d"]}},
             "conditions": ["a(1) + a(3) = 10"], "target": "a(5)"})
    assert r.value is None and status(r, "series.solve.primary") == CheckStatus.FAILED
    # ... whereas a target that is independent of it passes (a1 + a3 = 2 a2 = 10 -> S3 = 15)
    r = run({"kind": "series_sum", "unknowns": {"A": "real", "d": "real"}, "sequences": {"a": {"ap": ["A", "d"]}},
             "conditions": ["a(1) + a(3) = 10"], "target": "Sum(a(r), r, 1, 3)"})
    assert r.value == 15


def test_missed_solution_branch_is_not_lost():
    # sympy.solve alone returns only {A: 0, d: 0}; the branch A = -5d, n = 11 must be found
    r = run({"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "n": "natural"},
             "sequences": {"a": {"ap": ["A", "d"]}},
             "conditions": ["Sum(a(2*k - 1), k, 1, 12) = -72*a(1)/5", "Sum(a(r), r, 1, n) = 0"],
             "constraints": ["a(1) != 0"], "target": "n"})
    assert r.value == 11


def test_inconsistent_fit_and_infeasible_aggregates_block():
    r = run({"kind": "series_sum", "sequences": {"s": {"fit": {"values": ["1", "3", "11", "26"], "degree": 2}}},
             "target": "Sum(s(r), r, 1, 5)"})
    assert r.value is None
    # 10 values with mean 5 need sum of squares >= 250; 200 is impossible
    r = run({"kind": "statistics", "datasets": {"w": {"aggregate": {"n": "10", "sum": "50", "sumsq": "200"}}},
             "target": "var(w)"})
    assert r.value is None


def test_multimodal_and_sample_variance_block():
    r = run({"kind": "statistics", "datasets": {"x": {"values": ["1", "1", "2", "2"]}}, "target": "mode(x)"})
    assert r.value is None
    r = run({"kind": "statistics", "variance": "sample", "datasets": {"x": {"values": ["1", "2"]}},
             "target": "var(x)"})
    assert r.value is None


def _rec(key):
    return PYQRecord(**{
        "pyq_id": "T-SS", "exam": "JEE_MAIN", "year": 2025, "subject": "MATHEMATICS",
        "question_format": "single_correct_mcq", "stem": "AP with first term 3 ...",
        "options": [{"id": i, "text": t, "value": t} for i, t in zip("ABCD", ["-120", "-1200", "-1080", "-1020"])],
        "answer_key": key, "key_source": "official",
        "source": {"document": "t", "rights_status": "CLEARED", "permitted_uses": ["derive"], "rights_basis": "test"},
        "formal": AP_SUM})


def test_planted_wrong_key_detected():
    assert IngestStatus.PARENT_VERIFIED in ingest_record(_rec("C")).statuses
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in ingest_record(_rec("B")).statuses
