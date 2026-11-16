"""Executable mathematics misconceptions (blueprint 6.4, 11, 38).

Each operation re-solves the formal problem under ONE explicitly wrong
assumption and returns (value, trace). A distractor is accepted only if it is
provably different from the canonical answer and from every other option.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import sympy as sp

from cqse.math.engine import EquationModel, build_model
from cqse.math.expr import tri_equal


@dataclass
class ErrorResult:
    misconception_id: str
    value: sp.Basic
    trace: list[str]
    why_students: str
    why_wrong: str


def _apply_target(m: EquationModel, sols: list[sp.Expr]) -> Optional[sp.Basic]:
    if m.target == "solution_set":
        return sp.FiniteSet(*sols) if sols else sp.S.EmptySet
    if m.target == "count":
        return sp.Integer(len(sols))
    if not sols:
        return None
    return sp.simplify(sp.Add(*sols) if m.target == "sum" else sp.Mul(*sols))


def _numerator_poly(m: EquationModel) -> Optional[sp.Poly]:
    num, _ = sp.fraction(sp.together(sp.expand(m.lhs - m.rhs)))
    num = sp.expand(num)
    return sp.Poly(num, m.var) if num.is_polynomial(m.var) and num != 0 else None


def skip_definedness_check(m: EquationModel) -> Optional[ErrorResult]:
    p = _numerator_poly(m)
    if p is None or not m.conditions:
        return None
    roots = sorted(set(p.real_roots()), key=lambda r: float(r))
    roots = [r for r in roots if m.domain.contains(r) == sp.true]
    v = _apply_target(m, roots)
    if v is None:
        return None
    return ErrorResult(
        "MATH.DOMAIN.SKIP_DEFINEDNESS", v,
        ["Clear denominators / square / combine logs to get a polynomial",
         f"Solve the polynomial: real roots {roots}",
         "Do NOT substitute back into the original equation (error)",
         f"Report {m.target}: {v}"],
        "Students treat the cleared polynomial as equivalent to the original equation.",
        "Some roots make a denominator zero, an even-root radicand negative or a log argument non-positive; "
        "they are not solutions of the original equation.")


def include_nonreal_roots(m: EquationModel) -> Optional[ErrorResult]:
    p = _numerator_poly(m)
    if p is None or m.target not in ("count", "sum", "product"):
        return None
    allr = p.all_roots()
    if all(r.is_real for r in allr):
        return None
    v = _apply_target(m, list(allr))
    if v is None:
        return None
    return ErrorResult(
        "MATH.DOMAIN.COUNT_NONREAL", sp.simplify(v),
        [f"Polynomial of degree {p.degree()} -> take all {len(allr)} roots", "Ignore that only real values are asked",
         f"{m.target} = {sp.simplify(v)}"],
        "Students apply root-count / Vieta results without checking that the roots are real.",
        "The question asks only for real values; non-real roots must be excluded.")


def ignore_declared_domain(m: EquationModel) -> Optional[ErrorResult]:
    if m.domain == sp.S.Reals:
        return None
    sol = sp.solveset(sp.Eq(m.lhs, m.rhs), m.var, sp.S.Reals)
    if not isinstance(sol, sp.FiniteSet):
        return None
    from cqse.math.engine import admissible  # local import: avoid cycle at module load
    unrestricted = EquationModel(m.var, m.lhs_u, m.rhs_u, m.lhs, m.rhs, sp.S.Reals, m.target, m.conditions)
    kept = sorted([c for c in sol if admissible(unrestricted, c) is True], key=lambda r: float(r))
    v = _apply_target(m, kept)
    if v is None:
        return None
    return ErrorResult(
        "MATH.DOMAIN.IGNORE_RESTRICTION", v,
        [f"Solve over all reals: {kept}", f"Forget the restriction to {m.domain} (error)", f"{m.target} = {v}"],
        "Students solve correctly but do not re-read the domain restriction in the question.",
        f"Only values in {m.domain} are admissible.")


def vieta_sign_error(m: EquationModel) -> Optional[ErrorResult]:
    p = _numerator_poly(m)
    if p is None or p.degree() != 2 or m.target not in ("sum", "product"):
        return None
    a, b, c = p.all_coeffs()
    a, b, c = (sp.sympify(t) for t in (a, b, c))
    v = b / a if m.target == "sum" else -c / a
    return ErrorResult(
        "MATH.ALGEBRA.VIETA_SIGN", sp.simplify(v),
        [f"Quadratic {p.as_expr()} = 0 with a={a}, b={b}, c={c}",
         ("Use sum = b/a (sign error)" if m.target == "sum" else "Use product = -c/a (sign error)"),
         f"{m.target} = {sp.simplify(v)}"],
        "Students misremember the signs in Vieta's relations.",
        "Sum of roots is -b/a and product is c/a (and only real admissible roots count).")


def square_without_check(m: EquationModel) -> Optional[ErrorResult]:
    """sqrt(A) = B  ->  A = B^2, solved with no back-substitution."""
    lhs, rhs = m.lhs, m.rhs
    if not (isinstance(lhs, sp.Pow) and lhs.exp == sp.Rational(1, 2)):
        lhs, rhs = rhs, lhs
    if not (isinstance(lhs, sp.Pow) and lhs.exp == sp.Rational(1, 2)):
        return None
    sq = sp.expand(lhs.base - rhs**2)
    if not sq.is_polynomial(m.var) or sq == 0:
        return None
    roots = sorted(set(sp.Poly(sq, m.var).real_roots()), key=lambda r: float(r))
    roots = [r for r in roots if m.domain.contains(r) == sp.true]
    v = _apply_target(m, roots)
    if v is None:
        return None
    return ErrorResult(
        "MATH.ALGEBRA.SQUARE_NO_CHECK", v,
        [f"Square both sides: {lhs.base} = ({rhs})^2", f"Solve: {roots}",
         "Skip substituting back into the original radical equation (error)", f"{m.target} = {v}"],
        "Students forget that squaring can introduce extraneous roots.",
        "A root of the squared equation can make the right-hand side negative while the principal square root "
        "is non-negative.")


def keep_rejected_roots(m: EquationModel) -> Optional[ErrorResult]:
    """Keep the inadmissible roots and discard the valid ones (wrong root rejected)."""
    from cqse.math.engine import admissible
    p = _numerator_poly(m)
    if p is None:
        return None
    roots = sorted(set(p.real_roots()), key=lambda r: float(r))
    bad = [r for r in roots if admissible(m, r) is False]
    if not bad:
        return None
    v = _apply_target(m, bad)
    if v is None:
        return None
    return ErrorResult(
        "MATH.DOMAIN.REJECT_WRONG_ROOT", v,
        [f"Candidate roots {roots}", f"Discard the admissible root(s), keep {bad} (error in the check)",
         f"{m.target} = {v}"],
        "Students perform the domain check but apply the condition the wrong way round.",
        f"{bad} violate the domain or definedness conditions; the admissible roots are the solutions.")


def degree_as_count(m: EquationModel) -> Optional[ErrorResult]:
    if m.target != "count":
        return None
    degs = []
    for side in (m.lhs, m.rhs):
        num, _ = sp.fraction(side)
        if sp.expand(num).is_polynomial(m.var):
            degs.append(sp.Poly(sp.expand(num), m.var).degree())
    if not degs or max(degs) < 1:
        return None
    d = max(degs)
    return ErrorResult(
        "MATH.COUNT.DEGREE_AS_COUNT", sp.Integer(d),
        [f"Highest polynomial degree appearing is {d}", f"Conclude there are {d} solutions (error)"],
        "Students equate the degree of a polynomial with the number of real solutions.",
        "Degree bounds the number of complex roots; real, admissible solutions must be found and checked.")


OPERATIONS: list[Callable[[EquationModel], Optional[ErrorResult]]] = [
    skip_definedness_check, square_without_check, ignore_declared_domain, keep_rejected_roots,
    include_nonreal_roots, vieta_sign_error, degree_as_count,
]


def generate(formal: dict, canonical: sp.Basic) -> tuple[list[ErrorResult], list[str]]:
    """Run every misconception; keep only provably-wrong, mutually distinct results."""
    m = build_model(formal)
    kept: list[ErrorResult] = []
    log: list[str] = []
    for op in OPERATIONS:
        try:
            r = op(m)
        except Exception as e:  # noqa: BLE001
            log.append(f"{op.__name__}: error {e}")
            continue
        if r is None:
            log.append(f"{op.__name__}: not applicable")
            continue
        eq = tri_equal(r.value, canonical)
        if eq is not False:
            log.append(f"{op.__name__}: rejected (equals or may equal correct answer)")
            continue
        if any(tri_equal(r.value, k.value) is not False for k in kept):
            log.append(f"{op.__name__}: rejected (duplicates another distractor)")
            continue
        kept.append(r)
        log.append(f"{op.__name__}: accepted -> {r.value}")
    return kept, log
