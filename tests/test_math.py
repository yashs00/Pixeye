import random

import pytest
import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.math.engine import solve_and_verify
from cqse.math.expr import UnsupportedExpression, parse, tri_equal


def sols(lhs, rhs, domain="reals", target="solution_set"):
    s = solve_and_verify(dict(kind="equation", lhs=lhs, rhs=rhs, var="x", domain=domain, target=target))
    return s


@pytest.mark.parametrize("lhs,rhs,domain,expected", [
    ("(x**2-1)/(x-1)", "2", "reals", []),          # x=1 removed: denominator zero
    ("x/x + x", "1", "reals", []),                  # x/x would auto-simplify; x=0 must be rejected
    ("sqrt(x)+2", "x", "reals", [4]),               # x=1 extraneous from squaring
    ("sqrt(x+3)", "x-3", "reals", [6]),             # x=1 extraneous
    ("log(x-1)+log(x+1)", "log(3)", "reals", [2]),  # x=-2 makes log args negative
    ("x**2-2", "0", "positive_reals", [sp.sqrt(2)]),
    ("x**2-4", "0", "interval:[0,2)", []),          # open endpoint excludes 2
    ("x**2-4", "0", "interval:[0,2]", [2]),
    ("x**2-5*x+6", "0", "integers", [2, 3]),
])
def test_domain_aware_solutions(lhs, rhs, domain, expected):
    s = sols(lhs, rhs, domain)
    assert len(s.solutions) == len(expected)
    for a, b in zip(s.solutions, expected):
        assert tri_equal(a, sp.sympify(b)) is True
    assert all(r.is_affirmative() for r in s.records), [(r.check_id, r.status, r.result) for r in s.records]


def test_sum_of_empty_set_is_ill_posed():
    s = sols("x**2+1", "0", target="sum")
    assert any(r.status == CheckStatus.FAILED for r in s.records)


def test_infinite_solution_set_is_unresolved_not_passed():
    s = sols("x/x", "1")
    assert not all(r.is_affirmative() for r in s.records)


@pytest.mark.parametrize("bad", ["__import__('os')", "x; import os", "open('f')", "lambda: 1", "eval(x)"])
def test_parser_rejects_code(bad):
    with pytest.raises(UnsupportedExpression):
        parse(bad, {"x": sp.Symbol("x")})


def test_equivalence_detects_hidden_equal_forms():
    assert tri_equal(parse("1/2"), parse("0.5")) is True
    assert tri_equal(parse("sqrt(8)"), parse("2*sqrt(2)")) is True
    assert tri_equal(parse("sin(pi/6)"), parse("1/2")) is True
    assert tri_equal(parse("3"), parse("2")) is False


def test_property_random_quadratics():
    """Property test: (x-a)(x-b)=0 over a domain must give exactly the admissible a, b."""
    rng = random.Random(2026)
    for _ in range(25):
        a, b = rng.randint(-9, 9), rng.randint(-9, 9)
        dom = rng.choice(["reals", "positive_reals", "nonnegative_reals"])
        expected = sorted({r for r in (a, b) if dom == "reals" or (r > 0) or (dom == "nonnegative_reals" and r == 0)})
        s = sols(f"(x-({a}))*(x-({b}))", "0", dom, "count")
        assert int(s.target_value) == len(expected), (a, b, dom)
        assert [int(v) for v in s.solutions] == expected
