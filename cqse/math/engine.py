"""Mathematics engine: formal 'equation' problems with two independent solvers.

Formal state (kind = "equation"):
    {
      "kind": "equation",
      "lhs": "(x**2 - 1)/(x - 1)", "rhs": "2",
      "var": "x",
      "domain": "reals" | "positive_reals" | "nonnegative_reals" | "integers"
                | "naturals" | "interval:[a,b)" ,
      "target": "solution_set" | "count" | "sum" | "product"
    }

Method A: sympy.solveset on the evaluated equation over the reals.
Method B (independent): clear denominators -> exact real roots of the numerator
           polynomial (Poly.real_roots); non-polynomial -> bracketed numeric scan.
Both candidate sets are then filtered by (1) the declared domain, (2) the
definedness conditions of the UNEVALUATED expression and (3) exact
back-substitution into the ORIGINAL equation. Disagreement -> UNRESOLVED.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.math.expr import UnsupportedExpression, definedness_conditions, parse, tri_equal

TOOL = f"sympy {sp.__version__}"
_INTERVAL = re.compile(r"^interval:([\[(])\s*([^,]+)\s*,\s*([^\])]+)\s*([\])])$")


def domain_set(spec: str) -> sp.Set:
    spec = spec.strip()
    if spec == "reals":
        return sp.S.Reals
    if spec == "positive_reals":
        return sp.Interval.open(0, sp.oo)
    if spec == "nonnegative_reals":
        return sp.Interval(0, sp.oo)
    if spec == "integers":
        return sp.S.Integers
    if spec == "naturals":
        return sp.S.Naturals  # {1, 2, 3, ...}
    m = _INTERVAL.match(spec)
    if m:
        lo, hi = parse(m.group(2)), parse(m.group(3))
        return sp.Interval(lo, hi, left_open=m.group(1) == "(", right_open=m.group(4) == ")")
    raise UnsupportedExpression(f"unknown domain {spec!r}")


@dataclass
class EquationModel:
    var: sp.Symbol
    lhs_u: sp.Basic          # unevaluated (keeps domain information)
    rhs_u: sp.Basic
    lhs: sp.Expr             # evaluated
    rhs: sp.Expr
    domain: sp.Set
    target: str
    conditions: list[sp.Basic] = field(default_factory=list)


def build_model(formal: dict) -> EquationModel:
    if formal.get("kind") != "equation":
        raise UnsupportedExpression("not an equation problem")
    name = formal.get("var", "x")
    if not re.fullmatch(r"[a-z]", name):
        raise UnsupportedExpression("variable must be a single lowercase letter")
    v = sp.Symbol(name, real=True)
    syms = {name: v}
    lhs_u, rhs_u = parse(formal["lhs"], syms, evaluate=False), parse(formal["rhs"], syms, evaluate=False)
    lhs, rhs = parse(formal["lhs"], syms), parse(formal["rhs"], syms)
    target = formal.get("target", "solution_set")
    if target not in {"solution_set", "count", "sum", "product"}:
        raise UnsupportedExpression(f"unknown target {target!r}")
    extra = set((lhs - rhs).free_symbols) - {v}
    if extra:
        raise UnsupportedExpression(f"unbound symbols {extra}")
    conds = definedness_conditions(lhs_u) + definedness_conditions(rhs_u)
    return EquationModel(v, lhs_u, rhs_u, lhs, rhs, domain_set(formal.get("domain", "reals")),
                         target, conds)


def admissible(m: EquationModel, c: sp.Expr) -> Optional[bool]:
    """Is candidate c a genuine solution of the ORIGINAL equation in the declared domain?"""
    c = sp.nsimplify(c) if isinstance(c, sp.Float) else c
    if c.is_real is False:
        return False
    in_dom = m.domain.contains(c)
    if in_dom not in (sp.true, sp.false):
        in_dom = sp.simplify(in_dom)
    if in_dom == sp.false:
        return False
    if in_dom != sp.true:
        return None
    for cond in m.conditions:
        val = cond.subs(m.var, c)
        val = sp.simplify(val) if val not in (sp.true, sp.false) else val
        if val == sp.false:
            return False
        if val != sp.true:
            return None
    lv, rv = m.lhs.subs(m.var, c), m.rhs.subs(m.var, c)
    if lv.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or rv.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return False
    if lv.is_real is False or rv.is_real is False:
        return False
    return tri_equal(lv, rv)


def _sort_key(e: sp.Expr) -> float:
    return float(sp.N(e, 30))


def method_a(m: EquationModel) -> tuple[list[sp.Expr], str]:
    sol = sp.solveset(sp.Eq(m.lhs, m.rhs), m.var, sp.S.Reals)
    if sol == sp.S.EmptySet:
        cands: list[sp.Expr] = []
    elif isinstance(sol, sp.FiniteSet):
        cands = list(sol)
    else:
        raise UnsupportedExpression(f"solveset returned non-finite set: {sol}")
    return cands, "solveset over reals"


def method_b(m: EquationModel) -> tuple[list[sp.Expr], str, bool]:
    """Returns (candidates, method description, exact?)."""
    num, _den = sp.fraction(sp.together(sp.expand(m.lhs - m.rhs)))
    num = sp.expand(num)
    if num.is_polynomial(m.var):
        if num == 0:
            raise UnsupportedExpression("equation is an identity after clearing denominators")
        p = sp.Poly(num, m.var)
        roots = [sp.nsimplify(r) if r.is_Float else r for r in p.real_roots()]
        uniq: list[sp.Expr] = []
        for r in roots:
            if not any(tri_equal(r, u) for u in uniq):
                uniq.append(r)
        # Express CRootOf exactly where radicals exist.
        uniq = [sp.simplify(sp.expand_func(r)) if isinstance(r, sp.CRootOf) else r for r in uniq]
        return uniq, "numerator polynomial real_roots (denominators cleared)", True
    return _numeric_scan(m), "bracketed numeric scan on bounded window", False


def _numeric_scan(m: EquationModel, lo: float = -200.0, hi: float = 200.0, n: int = 8001) -> list[sp.Expr]:
    dom = m.domain
    if dom.is_subset(sp.Interval(-sp.oo, sp.oo)) and isinstance(dom, sp.Interval):
        lo = max(lo, float(dom.inf)) if dom.inf.is_finite else lo
        hi = min(hi, float(dom.sup)) if dom.sup.is_finite else hi
    f = sp.lambdify(m.var, m.lhs - m.rhs, "mpmath")
    import mpmath as mp
    mp.mp.dps = 40
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    vals = []
    for x in xs:
        try:
            y = f(mp.mpf(x))
            vals.append(y if mp.im(y) == 0 and mp.isfinite(y) else None)
        except Exception:  # noqa: BLE001
            vals.append(None)
    roots: list[sp.Expr] = []
    for i in range(n - 1):
        a, b = vals[i], vals[i + 1]
        if a is None or b is None:
            continue
        if a == 0:
            roots.append(sp.Float(xs[i], 30))
        elif b != 0 and mp.sign(mp.re(a)) != mp.sign(mp.re(b)):
            try:
                r = mp.findroot(lambda t: mp.re(f(t)), (xs[i], xs[i + 1]), solver="anderson")
                roots.append(sp.Float(str(r), 30))
            except Exception:  # noqa: BLE001
                pass
    if vals and vals[-1] == 0:
        roots.append(sp.Float(xs[-1], 30))
    uniq: list[sp.Expr] = []
    for r in roots:
        if all(abs(float(r - u)) > 1e-12 for u in uniq):
            uniq.append(r)
    return uniq


def admissible_numeric(m: EquationModel, c: sp.Float, tol: float = 1e-18) -> Optional[bool]:
    """Numeric admissibility for approximate roots (evidence only, never proof)."""
    try:
        if m.domain.contains(c) == sp.false:
            return False
        for cond in m.conditions:
            if cond is sp.false:
                return False
            lhs_c, rhs_c = cond.lhs.subs(m.var, c), cond.rhs.subs(m.var, c)
            lv, rv = complex(sp.N(lhs_c, 40)), complex(sp.N(rhs_c, 40))
            if abs(lv.imag) > 1e-20 or abs(rv.imag) > 1e-20:
                return False
            d = lv.real - rv.real
            op = type(cond)
            if op is sp.Ne and abs(d) < 1e-12:
                return False
            if op is sp.StrictGreaterThan and d <= 1e-12:
                return False
            if op is sp.GreaterThan and d < -1e-12:
                return False
            if op is sp.StrictLessThan and d >= -1e-12:
                return False
            if op is sp.LessThan and d > 1e-12:
                return False
        v = complex(sp.N((m.lhs - m.rhs).subs(m.var, c), 40))
        return abs(v) < tol * max(1.0, abs(float(c)))
    except Exception:  # noqa: BLE001
        return None


@dataclass
class MathSolution:
    solutions: list[sp.Expr]
    target_value: sp.Basic
    rejected: list[tuple[sp.Expr, str]]
    records: list[VerificationRecord]


def solve_and_verify(formal: dict) -> MathSolution:
    records: list[VerificationRecord] = []
    state: dict = {}

    def _model() -> VerificationRecord:
        state["m"] = build_model(formal)
        m = state["m"]
        return VerificationRecord(
            check_id="math.structure", status=CheckStatus.EXACT_CHECKED, method="schema+whitelist parse",
            tool=TOOL, assumptions=[f"{m.var} real", f"domain {formal.get('domain', 'reals')}"],
            result=f"{len(m.conditions)} definedness condition(s) extracted",
            data={"conditions": [str(c) for c in m.conditions]})

    records.append(guarded("math.structure", _model))
    if "m" not in state:
        return MathSolution([], sp.nan, [], records)
    m: EquationModel = state["m"]

    def _filter(cands: list[sp.Expr], numeric: bool = False
                ) -> tuple[list[sp.Expr], list[tuple[sp.Expr, str]], bool]:
        kept, rej, undecided = [], [], False
        for c in cands:
            ok = admissible_numeric(m, c) if numeric else admissible(m, c)
            if ok is True:
                kept.append(c)
            elif ok is False:
                rej.append((c, "fails domain/definedness or back-substitution"))
            else:
                undecided = True
                rej.append((c, "admissibility undecidable"))
        return sorted(kept, key=_sort_key), rej, undecided

    def _a() -> VerificationRecord:
        cands, desc = method_a(m)
        kept, rej, und = _filter(cands)
        state["A"], state["rejA"] = kept, rej
        st = CheckStatus.UNRESOLVED if und else CheckStatus.EXACT_CHECKED
        return VerificationRecord(check_id="math.solve.primary", status=st, method=desc, tool=TOOL,
                                  domain_coverage="complete for declared real domain",
                                  result=f"solutions {kept}; rejected {[str(r[0]) for r in rej]}")

    records.append(guarded("math.solve.primary", _a, seconds=30))

    def _b() -> VerificationRecord:
        cands, desc, exact = method_b(m)
        kept, rej, und = _filter(cands, numeric=not exact)
        state["B"] = kept
        A = state.get("A")
        if A is None:
            return VerificationRecord(check_id="math.solve.independent", status=CheckStatus.UNRESOLVED,
                                      method=desc, result="primary method produced no result to compare")
        agree = _lists_agree(A, kept, exact)
        if und or agree is None:
            st, res = CheckStatus.UNRESOLVED, f"cannot decide agreement: A={A} B={kept}"
        elif not agree:
            st, res = CheckStatus.UNRESOLVED, f"SOLVER DISAGREEMENT A={A} B={kept} -> diagnose, do not average"
        else:
            st = CheckStatus.EXACT_CHECKED if exact else CheckStatus.NUMERICALLY_CHECKED
            res = f"independent method agrees ({len(kept)} solution(s))"
        lim = [] if exact else ["numeric scan on [-200,200]; tangential or out-of-window roots can be missed",
                                "item requires second expert review"]
        return VerificationRecord(check_id="math.solve.independent", status=st, method=desc, tool=TOOL,
                                  numeric_evidence_sufficient=not exact, result=res, limitations=lim,
                                  data={"exact": exact})

    records.append(guarded("math.solve.independent", _b, seconds=30))

    sols = state.get("A", [])
    target_value: sp.Basic = sp.nan

    def _target() -> VerificationRecord:
        nonlocal target_value
        if "A" not in state:
            raise RuntimeError("no verified solution set")
        if m.target == "solution_set":
            target_value = sp.FiniteSet(*sols) if sols else sp.S.EmptySet
        elif m.target == "count":
            target_value = sp.Integer(len(sols))
        elif m.target in ("sum", "product"):
            if not sols:
                return VerificationRecord(check_id="math.target", status=CheckStatus.FAILED,
                                          method="target evaluation",
                                          result=f"ill-posed: {m.target} of an empty solution set")
            target_value = sp.simplify(sp.Add(*sols) if m.target == "sum" else sp.Mul(*sols))
        return VerificationRecord(check_id="math.target", status=CheckStatus.EXACT_CHECKED,
                                  method="exact arithmetic on verified solutions", tool=TOOL,
                                  result=f"{m.target} = {target_value}")

    records.append(guarded("math.target", _target))
    return MathSolution(sols, target_value, state.get("rejA", []), records)


def _lists_agree(a: list[sp.Expr], b: list[sp.Expr], exact: bool) -> Optional[bool]:
    if len(a) != len(b):
        return False
    for x, y in zip(sorted(a, key=_sort_key), sorted(b, key=_sort_key)):
        if exact:
            r = tri_equal(x, y)
            if r is not True:
                return r
        elif abs(float(sp.N(x - y, 30))) > 1e-9:
            return False
    return True


def render_equation_stem(formal: dict) -> str:
    dom_txt = {
        "reals": "real", "positive_reals": "positive real", "nonnegative_reals": "non-negative real",
        "integers": "integer", "naturals": "natural-number",
    }.get(formal.get("domain", "reals"))
    if dom_txt is None:
        dom_txt = f"real (in the interval {formal['domain'].split(':', 1)[1]})"
    eq = f"{formal['lhs']} = {formal['rhs']}".replace("**", "^")
    v = formal.get("var", "x")
    t = formal.get("target", "solution_set")
    ask = {"solution_set": f"the set of all {dom_txt} values of {v} satisfying",
           "count": f"the number of {dom_txt} values of {v} satisfying",
           "sum": f"the sum of all {dom_txt} values of {v} satisfying",
           "product": f"the product of all {dom_txt} values of {v} satisfying"}[t]
    return f"Find {ask} the equation  {eq}."
