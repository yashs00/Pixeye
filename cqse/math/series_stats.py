"""Sequences / series and statistics engine (kinds "series_sum" and "statistics").

Both kinds share one fail-closed pipeline:

  1. PRIMARY (closed form).  Every condition is evaluated symbolically - sequence terms by their closed
     form (AP/GP formula, rsolve for recurrences, Lagrange interpolation for "fit" sequences), sums by
     sympy summation with SYMBOLIC limits (an antiderivative in the limits, then substituted - never
     sympy's term-by-term fallback), statistics by the SHORTCUT formulas (power sums:
     var = sum(x^2)/n - mean^2, linear-transform rules, corrected-sum updates).  The unknowns are solved
     exactly, filtered by their domains and by the stated selection rules, and the target must take
     exactly ONE admissible value (parametric families are accepted only if the target is provably
     independent of the free parameter).
  2. INDEPENDENT (brute force).  For every admissible solution the conditions and the target are
     re-evaluated by a different method: sequences by iteration (a_{k+1} = a_k + d, recurrence stepping,
     finite-difference table extension), finite sums by exact rational term-by-term addition, infinite
     sums by high-precision partial sums plus a CERTIFIED tail bound (ratio or integral test, proved by
     polynomial coefficient signs) in interval arithmetic, statistics by the DEFINITION formulas on an
     explicit data list (for aggregate-only data, on a constructed witness data set that realises the
     solved n / sum / sum of squares - its existence is itself checked).
  Any disagreement, timeout, divergence, unmodelled construct or non-unique answer -> value None.

series_sum formal:
{
  "kind": "series_sum",
  "unknowns":  {"A": "real", "d": "real", "n": "natural"},     # domains as in cqse.generic.system
  "sequences": {"a": {"ap": ["A", "d"]}},                       # a(1) = A, a(k) = A + (k-1) d
       # or {"gp": ["A", "q"]}                                  # a(k) = A q^(k-1)
       # or {"term": "1/(n*(n+1))", "index": "n"}                # explicit (may nest Sum, factorial)
       # or {"by_parity": {"odd": "(2*n-1)**2", "even": "2*n-1"}, "index": "n"}
       # or {"recurrence": "2*a(n+2) = 5*a(n+1) - 3*a(n)", "initial": {"0": "0", "1": "1/2"}, "index": "n"}
       # or {"fit": {"values": ["1", "3", "11"], "degree": 2, "start": 1}}  # k-th order differences constant
  "dummies": ["r", "k", "j"],                                   # bound summation variables (these 3 default)
  "conditions":  ["a(1) = 3", "Sum(a(r), r, 1, 4) = Sum(a(r), r, 5, 8)/5"],
  "constraints": ["d > 0", "a(1) != 0"],                        # selection rules: < <= > >= !=
  "target": "Sum(a(r), r, 1, 20)",
  "model": ["..."]
}
Expression helpers: a(k) term of sequence a; Sum(body, r, lo, hi) (hi may be a symbol or oo);
CountInt(expr, r, lo, hi) number of r in [lo, hi] with expr an integer (expr linear in r);
NUnion(e1, e2, r, lo, hi) / NInter(...) size of union / intersection of {e1(r)} and {e2(r)} (both linear in r);
Numer(x), Denom(x) numerator / denominator of a rational in lowest terms; factorial(x).

statistics formal:
{
  "kind": "statistics",
  "unknowns": {"a": "real", "b": "real"},
  "datasets": {"x": {"values": ["1", "3", "a", "7", "b"]},
               "w": {"ap": {"first": "8", "diff": "13", "last": "320"}},
               "g": {"aggregate": {"n": "100", "sum": "S1", "sumsq": "S2"}},
               "y": {"transform": {"of": "x", "map": "t + i"}},        # t = value, i = 1-based position
               "c": {"replace": {"of": "g", "remove": ["50"], "add": ["40"]}},
               "h": {"grouped_median_class": {"lower": "12", "width": "6", "freq": "12",
                                              "cf_before": "18", "total": "N"}}},
  "conditions": ["mean(x) = 5", "var(x) = 10"],
  "constraints": ["a > b"],
  "target": "var(y)",
  "variance": "population"                                           # the only supported convention
}
Statistics functions: nobs(X), mean(X), var(X), sd(X), median(X), mode(X), md(X, c) (mean deviation about
c), sumf(X, body-in-t).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Optional

import sympy as sp
from mpmath import iv
from sympy.core.function import AppliedUndef

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.core.result import EngineResult
from cqse.math.expr import is_exact_integer, parse, tri_equal

TOOL = f"cqse-series-stats 0.1; sympy {sp.__version__}"
DOMAINS = {"real", "positive", "nonnegative", "negative", "nonzero", "integer", "natural"}
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,15}$")
_RESERVED = {"pi", "oo", "E", "I", "sqrt", "log", "ln", "exp", "sin", "cos", "tan", "cot", "sec", "csc",
             "asin", "acos", "atan", "Abs", "Rational", "Integer", "Sum", "CountInt", "NUnion", "NInter",
             "Numer", "Denom", "factorial", "mean", "var", "sd", "median", "mode", "md", "nobs", "sumf"}

SUM, COUNTINT, NUNION, NINTER = (sp.Function(n) for n in ("SUM_", "COUNTINT_", "NUNION_", "NINTER_"))
NUMER, DENOM = sp.Function("NUMER_"), sp.Function("DENOM_")
MEAN, VAR, SD, MEDIAN, MODE, MD, NOBS, SUMF = (sp.Function(n.upper() + "_") for n in
                                               ("mean", "var", "sd", "median", "mode", "md", "nobs", "sumf"))
_SPECIAL = {"Sum": SUM, "CountInt": COUNTINT, "NUnion": NUNION, "NInter": NINTER, "Numer": NUMER,
            "Denom": DENOM, "factorial": sp.factorial}
_STATS = {"mean": MEAN, "var": VAR, "sd": SD, "median": MEDIAN, "mode": MODE, "md": MD, "nobs": NOBS,
          "sumf": SUMF}

PARTIAL_RATIO, PARTIAL_INTEGRAL = 80, 3000      # partial-sum lengths for the two tail tests
REL_WIDTH = sp.Rational(1, 10**9)               # interval must pin the value to 1e-9 relative


class Unsupported(ValueError):
    """Construct the engine does not model: the caller turns it into UNRESOLVED."""


class Divergent(ValueError):
    pass


class ModelError(ValueError):
    pass


# ======================================================================= interval helpers
class IvVal:
    """Rigorous enclosure [lo, hi] (mpmath interval) of a real number."""

    def __init__(self, x):
        self.x = x

    @staticmethod
    def of(v: sp.Basic) -> "IvVal":
        v = sp.sympify(v)
        if isinstance(v, IvVal):
            return v
        if v.is_Rational:
            return IvVal(iv.mpf(int(v.p)) / iv.mpf(int(v.q)))
        if not v.is_number or v.is_real is False:
            raise Unsupported(f"cannot enclose {v}")
        f = sp.N(v, 70)
        if f.is_real is False or not f.is_finite:
            raise Unsupported(f"cannot enclose {v}")
        s = sp.Float(f, 70)
        e = abs(s) * sp.Float("1e-55", 70) + sp.Float("1e-65", 70)
        return IvVal(iv.mpf([str(s - e), str(s + e)]))

    def width(self) -> float:
        return float(self.x.delta)

    def contains(self, v: sp.Basic) -> bool:
        w = IvVal.of(v).x
        return bool(self.x.a <= w.b and w.a <= self.x.b)


def _iv_combine(func, args):
    xs = [a.x if isinstance(a, IvVal) else IvVal.of(a).x for a in args]
    if func is sp.Add:
        out = xs[0]
        for x in xs[1:]:
            out = out + x
        return IvVal(out)
    if func is sp.Mul:
        out = xs[0]
        for x in xs[1:]:
            out = out * x
        return IvVal(out)
    if func is sp.Pow:
        ex = args[1]
        if isinstance(ex, IvVal):
            raise Unsupported("interval exponent")
        if ex.is_Integer:
            return IvVal(xs[0] ** int(ex))
        if ex == sp.Rational(1, 2):
            return IvVal(iv.sqrt(xs[0]))
        if ex == sp.Rational(-1, 2):
            return IvVal(1 / iv.sqrt(xs[0]))
    if func is sp.Abs:
        x = xs[0]
        if x.a >= 0:
            return IvVal(x)
        if x.b <= 0:
            return IvVal(-x)
    raise Unsupported(f"interval arithmetic for {func} not modelled")


def _close(a, b) -> Optional[bool]:
    """Exact equality, or interval containment of an exact value with a tight enclosure."""
    if isinstance(a, IvVal) or isinstance(b, IvVal):
        if isinstance(a, IvVal) and isinstance(b, IvVal):
            ok = bool(a.x.a <= b.x.b and b.x.a <= a.x.b)
            tight = max(a.width(), b.width())
            mag = max(1.0, abs(float(a.x.mid)))
            return ok and tight <= float(REL_WIDTH) * mag
        iv_, ex = (a, b) if isinstance(a, IvVal) else (b, a)
        mag = max(1.0, abs(float(iv_.x.mid)))
        if iv_.width() > float(REL_WIDTH) * mag:
            return None
        return iv_.contains(ex)
    return tri_equal(sp.sympify(a), sp.sympify(b))


# ======================================================================= small utilities
def _name_ok(n: str) -> None:
    if not _NAME.match(n) or n in _RESERVED:
        raise ModelError(f"bad name {n!r}")


def _norm_unknowns(spec: dict) -> dict[str, str]:
    out = {}
    for k, v in (spec or {}).items():
        dom = v.get("domain", "real") if isinstance(v, dict) else str(v)
        if dom not in DOMAINS:
            raise ModelError(f"unknown domain {dom!r} for {k}")
        _name_ok(k)
        out[k] = dom
    return out


def _split_eq(s: str) -> tuple[str, str]:
    if s.count("=") != 1 or any(op in s for op in ("<", ">", "!")):
        raise ModelError(f"condition must contain exactly one '=': {s!r}")
    a, b = s.split("=")
    return a, b


_OPS = [("<=", sp.Le), (">=", sp.Ge), ("!=", sp.Ne), ("<", sp.Lt), (">", sp.Gt)]


def _split_rel(s: str):
    for tok, fn in _OPS:
        if tok in s:
            a, b = s.split(tok, 1)
            if any(t in b for t, _ in _OPS):
                raise ModelError(f"one relation per constraint: {s!r}")
            return a, fn, b
    raise ModelError(f"constraint needs one of < <= > >= != : {s!r}")


def _truth(c) -> Optional[bool]:
    if c in (True, sp.true):
        return True
    if c in (False, sp.false):
        return False
    try:
        c2 = sp.simplify(c)
    except Exception:  # noqa: BLE001
        c2 = c
    if c2 in (True, sp.true):
        return True
    if c2 in (False, sp.false):
        return False
    if isinstance(c2, sp.core.relational.Relational):
        d = sp.simplify(c2.lhs - c2.rhs)
        if d.free_symbols or not d.is_number:
            return None
        if d.is_real is False:
            return False
        v = sp.N(d, 60)
        if abs(v) < sp.Float("1e-40"):
            if d.is_zero is not True:
                return None
            return bool(c2.func(0, 0))
        return bool(c2.func(v, 0))
    return None


def _dom_rels(v: sp.Expr, dom: str) -> list:
    return {"real": [], "integer": [], "positive": [v > 0], "nonnegative": [v >= 0],
            "negative": [v < 0], "nonzero": [sp.Ne(v, 0)], "natural": [v >= 1]}[dom]


def _is_real_number(v: sp.Expr) -> Optional[bool]:
    if v.is_real is not None:
        return bool(v.is_real)
    im = sp.N(sp.im(v), 60)
    if abs(im) > sp.Float("1e-40"):
        return False
    return None


def _coeff_signs(p: sp.Expr, m: sp.Symbol) -> Optional[int]:
    """+1 if polynomial p(m) has all coefficients >= 0 (and p != 0), -1 if all <= 0, else None.
    A +1 polynomial is >= 0 for every m >= 0 (> 0 when the constant term is > 0)."""
    try:
        cs = sp.Poly(sp.expand(p), m).all_coeffs()
    except sp.PolynomialError:
        return None
    if any(not c.is_Rational for c in cs):
        cs = [sp.nsimplify(c) for c in cs]
        if any(not c.is_Rational for c in cs):
            return None
    if all(c >= 0 for c in cs) and any(c != 0 for c in cs):
        return 1
    if all(c <= 0 for c in cs) and any(c != 0 for c in cs):
        return -1
    return None


def _strictly_pos_poly(p: sp.Expr, m: sp.Symbol) -> bool:
    s = _coeff_signs(p, m)
    return s == 1 and sp.expand(p).subs(m, 0) > 0


def _rat_pos(f: sp.Expr, m: sp.Symbol) -> Optional[int]:
    """Sign of a rational function of m on m >= 0 if certified by coefficient signs."""
    num, den = sp.fraction(sp.cancel(sp.together(f)))
    sn, sd = _coeff_signs(num, m), _coeff_signs(den, m)
    if sn is None or sd is None:
        return None
    if sp.expand(num).subs(m, 0) == 0 or sp.expand(den).subs(m, 0) == 0:
        return None
    return sn * sd


def tail_bound(f: sp.Expr, var: sp.Symbol, K: int) -> tuple[sp.Expr, sp.Expr, str]:
    """Certified enclosure [lo, hi] of sum_{k >= K} f(k).  Raises Unsupported if neither test applies."""
    m = sp.Symbol("m_", nonnegative=True)
    fK = sp.simplify(f.subs(var, K))
    if fK == 0:
        raise Unsupported("tail term vanishes; tail test not applicable")
    # ratio test: rho(k) = f(k+1)/f(k) in (0, q] for every k >= K
    try:
        rho = sp.simplify(sp.combsimp(sp.powsimp(f.subs(var, var + 1) / f, force=True)))
        rho_m = sp.cancel(sp.together(sp.expand_func(rho.subs(var, K + m))))
        num, den = sp.fraction(rho_m)
        if num.free_symbols <= {m} and den.free_symbols <= {m} and _rat_pos(rho_m, m) == 1:
            sd = _coeff_signs(den, m)
            if sd == -1:
                num, den = -num, -den
            for q in (sp.Rational(1, 2), sp.Rational(3, 4), sp.Rational(9, 10), sp.Rational(99, 100)):
                if _coeff_signs(q * den - num, m) == 1 or sp.expand(q * den - num) == 0:
                    t = fK / (1 - q)
                    return (sp.Integer(0), t, f"ratio test: 0 < f(k+1)/f(k) <= {q} for k >= {K}") if fK > 0 \
                        else (t, sp.Integer(0), f"ratio test: 0 < f(k+1)/f(k) <= {q} for k >= {K}")
    except Unsupported:
        raise
    except Exception:  # noqa: BLE001
        pass
    # integral test: f positive and decreasing on [K, oo)
    fm = sp.cancel(sp.together(f.subs(var, K + m)))
    if fm.free_symbols <= {m} and _rat_pos(fm, m) == 1:
        x = sp.Symbol("x_", positive=True)
        fx = f.subs(var, x)
        dm = sp.cancel(sp.together(-sp.diff(fx, x).subs(x, K + m)))
        if _rat_pos(dm, m) == 1:
            integral = sp.integrate(fx, (x, K, sp.oo))
            if integral.has(sp.oo, sp.zoo, sp.nan) or integral.has(sp.Integral):
                raise Divergent("integral test: tail integral diverges")
            return sp.Integer(0), fK + integral, f"integral test: f > 0 decreasing on [{K}, oo)"
    raise Unsupported("no certified tail bound (ratio / integral test not applicable)")


# ======================================================================= shared machinery
class _Model:
    prefix = "x"

    def __init__(self, formal: dict):
        self.formal = formal
        self.unknowns = _norm_unknowns(formal.get("unknowns", {}))
        self.syms: dict[str, sp.Symbol] = {u: sp.Symbol(u, real=True) for u in self.unknowns}
        self.domains = {self.syms[u]: d for u, d in self.unknowns.items()}
        self.ns: dict[str, Any] = {}
        self.conds: list[tuple[sp.Expr, sp.Expr, str]] = []
        self.cons: list[tuple[sp.Expr, Any, sp.Expr, str]] = []
        self.target = None
        self.extra: list[VerificationRecord] = []
        self.infinite = False

    def _parse_common(self):
        for c in self.formal.get("conditions", []):
            a, b = _split_eq(c)
            self.conds.append((parse(a, self.ns), parse(b, self.ns), c))
        for c in self.formal.get("constraints", []):
            a, fn, b = _split_rel(c)
            self.cons.append((parse(a, self.ns), fn, parse(b, self.ns), c))
        if not self.formal.get("target"):
            raise ModelError("no target")
        self.target = parse(self.formal["target"], self.ns)
        self.infinite = any(e.has(sp.oo) for e in [self.target] + [x for c in self.conds for x in c[:2]])

    # subclasses implement evC(expr, sol) and evB(expr, env)
    def reset_b(self):
        pass


def _apply(func, args):
    if any(isinstance(a, IvVal) for a in args):
        return _iv_combine(func, args)
    return func(*args)


def _candidates(model: _Model, sols: list[dict]) -> tuple[list[dict], list[str], bool]:
    """Admissible concrete solutions (free parameters enumerated or sampled).
    Returns (concrete solution list incl. samples, notes, undecided?)."""
    unk = list(model.syms.values())
    out, notes, undecided = [], [], False
    for s in sols:
        full = {u: sp.sympify(s.get(u, u)) for u in unk}
        free = set()
        for v in full.values():
            free |= v.free_symbols & set(unk)
        rels = []
        for u, dom in model.domains.items():
            rels += _dom_rels(full[u], dom)
        for a, fn, b, src in model.cons:
            rels.append(fn(model.evC(a, full), model.evC(b, full)))
        ints = [u for u, d in model.domains.items() if d in ("integer", "natural")]
        if not free:
            r = _check_concrete(model, full, rels)
            if r is True:
                out.append(full)
            elif r is None:
                undecided = True
                notes.append(f"admissibility undecidable for {full}")
            else:
                notes.append(f"rejected {_fmt(full)}")
            continue
        # parts that are already concrete decide immediately (e.g. n = 0 for a natural n)
        part = {u: v for u, v in full.items() if not v.free_symbols}
        sub_model = type("M", (), {"domains": {u: dm for u, dm in model.domains.items() if u in part}})
        if _check_concrete(sub_model, part, [rl for rl in rels if not getattr(rl, "free_symbols", set())]) \
                is False:
            notes.append(f"rejected {_fmt(full)}")
            continue
        free_l = sorted(free, key=str)
        if all(model.domains.get(f) in ("integer", "natural") for f in free_l):
            if len(free_l) != 1:
                undecided = True
                notes.append(f"{len(free_l)} free integer parameters: enumeration not modelled")
                continue
            x = free_l[0]
            rels_x = rels + _dom_rels(x, model.domains[x])
            dom_set = sp.S.Reals
            for rel in rels_x:
                if rel in (True, sp.true):
                    continue
                if rel in (False, sp.false):
                    dom_set = sp.S.EmptySet
                    break
                if not rel.free_symbols:
                    t = _truth(rel)
                    if t is False:
                        dom_set = sp.S.EmptySet
                        break
                    continue
                if rel.free_symbols != {x}:
                    raise Unsupported("constraint couples several free parameters")
                dom_set = dom_set.intersect(sp.solve_univariate_inequality(rel, x, relational=False))
            if dom_set == sp.S.EmptySet:
                notes.append(f"family {_fmt(full)} has no admissible member")
                continue
            lo, hi = dom_set.inf, dom_set.sup
            if not (lo.is_finite and hi.is_finite):
                undecided = True
                notes.append(f"free integer parameter {x} is unbounded in {dom_set}: infinitely many solutions")
                continue
            vals = [v for v in range(int(sp.ceiling(lo)), int(sp.floor(hi)) + 1)]
            if len(vals) > 5000:
                raise Unsupported("enumeration range too large")
            for v in vals:
                conc = {u: sp.simplify(full[u].subs(x, v)) for u in unk}
                rels_c = [rl.subs(x, v) if hasattr(rl, "subs") else rl for rl in rels]
                r = _check_concrete(model, conc, rels_c)
                if r is True:
                    out.append(conc)
                elif r is None:
                    undecided = True
            notes.append(f"enumerated integer {x} in [{lo}, {hi}]")
            continue
        if any(model.domains.get(f) in ("integer", "natural") for f in free_l):
            undecided = True
            notes.append("mixed integer/real free parameters: not modelled")
            continue
        # real free parameters: the target must not depend on them; sample admissible members
        tC = sp.simplify(model.evC(model.target, full))
        if tC.free_symbols & set(free_l):
            out.append({"__family__": True, "full": full, "target": tC, "free": free_l})
            continue
        pool = [sp.Rational(7, 3), sp.Rational(-5, 2), sp.Integer(3), sp.Rational(11, 7), sp.Integer(-4),
                sp.Rational(1, 9), sp.Integer(10), sp.Rational(-1, 3), sp.Rational(13, 2)]
        samples = []
        for i in range(len(pool)):
            sub = {f: pool[(i + 3 * j) % len(pool)] for j, f in enumerate(free_l)}
            conc = {u: sp.simplify(full[u].subs(sub)) for u in unk}
            rels_c = [rl.subs(sub) if hasattr(rl, "subs") else rl for rl in rels]
            if _check_concrete(model, conc, rels_c) is True:
                samples.append(conc)
            if len(samples) >= 2:
                break
        if len(samples) < 2:
            undecided = True
            notes.append(f"could not find admissible members of family {_fmt(full)}")
            continue
        notes.append(f"family {_fmt(full)} (free {free_l}); target independent of the free parameter; "
                     f"sampled {[_fmt({f: smp[f] for f in free_l}) for smp in samples]}")
        for smp in samples:
            smp["__sample_of__"] = tC
            out.append(smp)
    return out, notes, undecided


def _check_concrete(model, full, rels) -> Optional[bool]:
    for u, dom in model.domains.items():
        v = full[u]
        if v.free_symbols:
            return None
        rr = _is_real_number(v)
        if rr is not True:
            return rr
        if dom in ("integer", "natural"):
            ii = is_exact_integer(v)
            if ii is not True:
                return ii
    und = False
    for rel in rels:
        t = _truth(rel)
        if t is False:
            return False
        if t is None:
            und = True
    return None if und else True


def _solve_all(eqs: list, unk: list) -> list[dict]:
    """Union of sympy.solve and nonlinsolve (Groebner-based for polynomial systems).
    sympy.solve alone can silently drop solution branches (e.g. it misses A = -5d, n = 11 in
    {132A/5 + 132d = 0, n(2A + (n-1)d)/2 = 0}); a missed branch must never shrink the answer set."""
    out: list[dict] = []

    def add(dct):
        dct = {k: sp.simplify(v) for k, v in dct.items() if v != k}
        if not any(set(dct) == set(o) and all(sp.simplify(dct[k] - o[k]) == 0 for k in dct) for o in out):
            out.append(dct)

    try:
        for s_ in sp.solve(eqs, unk, dict=True):
            add(s_)
    except NotImplementedError:
        pass
    polynomial = all(sp.sympify(e).is_polynomial(*unk) or sp.fraction(sp.together(e))[0].is_polynomial(*unk)
                     for e in eqs)
    if polynomial:
        res = sp.nonlinsolve(eqs, unk)
        if not isinstance(res, sp.FiniteSet):
            raise Unsupported(f"nonlinsolve returned {type(res).__name__}")
        for tup in res:
            if any(not isinstance(v, sp.Expr) for v in tup):
                raise Unsupported(f"non-explicit solution {tup}")
            if any(v.has(sp.I) and _is_real_number(v) is False for v in tup if not v.free_symbols):
                continue
            add(dict(zip(unk, tup)))
    elif not out:
        raise Unsupported("non-polynomial system and sympy.solve found nothing")
    return out


def _fmt(d: dict) -> str:
    return "{" + ", ".join(f"{k}={v}" for k, v in d.items() if not str(k).startswith("__")) + "}"


def _pipeline(model: _Model, res: EngineResult) -> None:
    P = model.prefix
    st: dict = {}

    def _primary():
        eqs = []
        for a, b, src in model.conds:
            e = sp.simplify(model.evC(a, {}) - model.evC(b, {}))
            if e == 0:
                continue
            if not e.free_symbols:
                return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.FAILED,
                                          method="closed form", tool=TOOL,
                                          result=f"condition {src!r} reduces to {e} = 0: inconsistent")
            eqs.append(e)
        unk = list(model.syms.values())
        if eqs:
            sols = _solve_all(eqs, unk)
            if not sols:
                return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.UNRESOLVED,
                                          method="sympy.solve", tool=TOOL,
                                          result="no solution found for the conditions")
        else:
            sols = [{}]
        cands, notes, und = _candidates(model, sols)
        fams = [c for c in cands if c.get("__family__")]
        if fams:
            return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.FAILED,
                                      method="closed form + exact solve", tool=TOOL,
                                      result=f"target {fams[0]['target']} depends on free parameters "
                                             f"{fams[0]['free']}: the stem does not determine it")
        if und:
            return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.UNRESOLVED,
                                      method="closed form + exact solve", tool=TOOL, result="; ".join(notes))
        vals = []
        for c in cands:
            v = c.get("__sample_of__")
            if v is None:
                v = sp.simplify(model.evC(model.target, c))
            if v.free_symbols:
                return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.FAILED,
                                          method="closed form", tool=TOOL, result=f"target {v} not determined")
            if v.has(sp.oo, sp.zoo, sp.nan):
                raise Divergent(f"target evaluates to {v}")
            c["__tC__"] = v
            hit = False
            for w in vals:
                r = tri_equal(v, w)
                if r is True:
                    hit = True
                    break
                if r is None:
                    return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.UNRESOLVED,
                                              method="closed form", tool=TOOL,
                                              result=f"cannot decide whether {v} and {w} are equal")
            if not hit:
                vals.append(v)
        if not vals:
            return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.FAILED,
                                      method="closed form + exact solve + domain/selection filter", tool=TOOL,
                                      result="no admissible solution: " + "; ".join(notes))
        if len(vals) > 1:
            return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.FAILED,
                                      method="closed form + exact solve + domain/selection filter", tool=TOOL,
                                      result=f"{len(vals)} admissible target values {vals}: ambiguous")
        st["value"], st["cands"] = vals[0], cands
        sol_txt = [_fmt(c) for c in cands]
        return VerificationRecord(check_id=f"{P}.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                  method="closed-form terms/sums (symbolic limits) or shortcut statistics; "
                                         "exact solve; domain + selection filter; single-valued target",
                                  tool=TOOL, result=f"target = {vals[0]}; admissible solutions {sol_txt}",
                                  data={"notes": notes, "solutions": sol_txt})

    def _wrap(fn, cid, secs):
        def g():
            try:
                return fn()
            except Divergent as e:
                return VerificationRecord(check_id=cid, status=CheckStatus.FAILED, method="convergence",
                                          tool=TOOL, result=f"divergent: {e}")
            except ModelError as e:   # e.g. no real data set realises the aggregates
                return VerificationRecord(check_id=cid, status=CheckStatus.FAILED, method="model",
                                          tool=TOOL, result=f"inconsistent model: {e}")
            except Unsupported as e:
                return VerificationRecord(check_id=cid, status=CheckStatus.UNRESOLVED, method="model",
                                          tool=TOOL, result=f"not modelled: {e}")
        return guarded(cid, g, seconds=secs)

    rec = _wrap(_primary, f"{P}.solve.primary", 25)
    res.records.append(rec)
    if "value" not in st:
        return
    res.steps.append(f"Closed form: target = {st['value']}")

    def _independent():
        numeric = False
        for c in st["cands"]:
            env = {k: v for k, v in c.items() if not str(k).startswith("__")}
            model.reset_b()
            for a, b, src in model.conds:
                la, lb = model.evB(a, env), model.evB(b, env)
                numeric |= isinstance(la, IvVal) or isinstance(lb, IvVal)
                r = _close(la, lb)
                if r is not True:
                    return VerificationRecord(
                        check_id=f"{P}.solve.independent", status=CheckStatus.FAILED if r is False
                        else CheckStatus.UNRESOLVED, method="brute force / definition", tool=TOOL,
                        result=f"condition {src!r} at {_fmt(env)}: brute force gives {_show(la)} vs {_show(lb)}")
            for a, fn, b, src in model.cons:
                la, lb = model.evB(a, env), model.evB(b, env)
                if isinstance(la, IvVal) or isinstance(lb, IvVal):
                    raise Unsupported("interval-valued selection rule")
                if _truth(fn(la, lb)) is not True:
                    return VerificationRecord(check_id=f"{P}.solve.independent", status=CheckStatus.FAILED,
                                              method="brute force", tool=TOOL,
                                              result=f"selection rule {src!r} fails by brute force at {_fmt(env)}")
            tB = model.evB(model.target, env)
            numeric |= isinstance(tB, IvVal)
            r = _close(tB, c["__tC__"])
            if r is not True:
                return VerificationRecord(
                    check_id=f"{P}.solve.independent", status=CheckStatus.FAILED if r is False
                    else CheckStatus.UNRESOLVED, method="brute force / definition", tool=TOOL,
                    result=f"closed form {c['__tC__']} vs independent {_show(tB)} at {_fmt(env)}")
            st.setdefault("tB", []).append(_show(tB))
        if numeric:
            return VerificationRecord(
                check_id=f"{P}.solve.independent", status=CheckStatus.NUMERICALLY_CHECKED,
                numeric_evidence_sufficient=True, tool=TOOL,
                method="high-precision partial sums + certified tail bound (interval arithmetic) as a "
                       "cross-check of the exact closed form",
                result=f"every condition and the target agree; enclosures {st['tB']}")
        return VerificationRecord(check_id=f"{P}.solve.independent", status=CheckStatus.EXACT_CHECKED, tool=TOOL,
                                  method=model.b_method,
                                  result=f"all conditions hold exactly; target = {st['tB'][0]} for "
                                         f"{len(st['cands'])} admissible solution(s)/sample(s)")

    rec2 = _wrap(_independent, f"{P}.solve.independent", 25)
    res.records.append(rec2)
    if rec2.is_affirmative():
        res.value = st["value"]
        res.steps.append(f"Independent check: {rec2.result}")


def _show(v) -> str:
    if isinstance(v, IvVal):
        return str(v.x)
    return str(v)


# ======================================================================= series model
class _Seq:
    def __init__(self, name: str, spec: dict, model: "SeriesModel"):
        self.name, self.spec, self.m = name, spec, model
        self.f = model.fns[name]
        self.kind = next((k for k in ("ap", "gp", "term", "by_parity", "recurrence", "fit") if k in spec), None)
        if self.kind is None:
            raise ModelError(f"sequence {name}: unknown definition {list(spec)}")
        self.start = 1
        if self.kind in ("ap", "gp"):
            self.p = [parse(x, model.ns) for x in spec[self.kind]]
            if len(self.p) != 2:
                raise ModelError(f"{self.kind} needs [first, difference/ratio]")
        elif self.kind in ("term", "by_parity", "recurrence"):
            idx = spec.get("index", "n")
            _name_ok(idx)
            if idx in model.syms or idx in model.fns:
                raise ModelError(f"index {idx!r} clashes with an unknown/sequence; set 'index'")
            self.n = sp.Symbol(idx, integer=True)
            ns = {**model.ns, idx: self.n}
            if self.kind == "term":
                self.expr = parse(spec["term"], ns)
            elif self.kind == "by_parity":
                self.odd = parse(spec["by_parity"]["odd"], ns)
                self.even = parse(spec["by_parity"]["even"], ns)
            else:
                self._init_recurrence(ns)
        else:
            fit = spec["fit"]
            self.vals = [parse(v, model.ns) for v in fit["values"]]
            self.deg = int(fit["degree"])
            self.start = int(fit.get("start", 1))
            if any(v.free_symbols for v in self.vals):
                raise ModelError("fit values must be numbers")
            if len(self.vals) < self.deg + 2:
                raise ModelError("fit needs at least degree+2 given terms (one consistency check)")
            n = sp.Symbol("n", integer=True)
            self.n = n
            self.poly = sp.expand(sp.interpolate([(self.start + i, v) for i, v in enumerate(self.vals)], n))
            if sp.Poly(self.poly, n).degree() > self.deg:
                raise ModelError(f"given terms {fit['values']} do not have constant order-{self.deg} differences")

    def _init_recurrence(self, ns):
        lhs, rhs = _split_eq(self.spec["recurrence"])
        e = parse(lhs, ns) - parse(rhs, ns)
        apps = [a for a in e.atoms(AppliedUndef) if a.func == self.f]
        shifts = sorted({sp.simplify(a.args[0] - self.n) for a in apps})
        if not shifts or any(not s.is_Integer for s in shifts):
            raise ModelError("recurrence must relate a(n + const) terms")
        lo, hi = int(shifts[0]), int(shifts[-1])
        self.rel, self.lo, self.hi = e, lo, hi
        top = self.f(self.n + hi)
        sol = sp.solve(e, top)
        if len(sol) != 1:
            raise ModelError("recurrence is not uniquely solvable for its highest term")
        self.step = sol[0]
        init = {int(k): parse(v, self.m.ns) for k, v in self.spec["initial"].items()}
        ks = sorted(init)
        if len(ks) != hi - lo or ks != list(range(ks[0], ks[0] + hi - lo)):
            raise ModelError(f"recurrence of order {hi - lo} needs {hi - lo} consecutive initial values")
        self.init, self.start = init, ks[0]
        # closed form by rsolve (primary)
        cf = sp.rsolve(e.subs(self.n, self.n - lo), self.f(self.n), {self.f(k): v for k, v in init.items()})
        if cf is None:
            self.closed = None
            return
        self.closed = sp.simplify(cf)
        # certificate: closed form satisfies the recurrence identically and the initial values
        chk = sp.simplify(e.replace(lambda x: isinstance(x, AppliedUndef) and x.func == self.f,
                                    lambda x: self.closed.subs(self.n, x.args[0])))
        bad = chk != 0 or any(sp.simplify(self.closed.subs(self.n, k) - v) != 0 for k, v in init.items())
        self.m.extra.append(VerificationRecord(
            check_id=f"series.sequence.{self.name}", status=CheckStatus.FAILED if bad else CheckStatus.EXACT_CHECKED,
            method="rsolve closed form substituted back into the recurrence and initial values", tool=TOOL,
            result=f"{self.name}(n) = {self.closed}" + (" FAILS certificate" if bad else " (certified)")))

    # ---- closed form term
    def C(self, idx: sp.Expr, sol: dict) -> sp.Expr:
        if self.kind == "ap":
            a, d = (self.m.evC(x, sol) for x in self.p)
            return a + (idx - 1) * d
        if self.kind == "gp":
            a, q = (self.m.evC(x, sol) for x in self.p)
            return a * q ** (idx - 1)
        if self.kind == "term":
            return self.m.evC(self.expr.xreplace({self.n: idx}), sol)
        if self.kind == "by_parity":
            o = self.m.evC(self.odd.xreplace({self.n: idx}), sol)
            e = self.m.evC(self.even.xreplace({self.n: idx}), sol)
            return o * (1 - (-1) ** idx) / 2 + e * (1 + (-1) ** idx) / 2
        if self.kind == "recurrence":
            if self.closed is None:
                raise Unsupported(f"no closed form for recurrence {self.name}")
            return self.closed.subs(self.n, idx).xreplace(sol)
        return self.poly.subs(self.n, idx)

    # ---- brute-force term (iteration)
    def B(self, k, env: dict):
        k = sp.sympify(k)
        if not k.is_Integer:
            raise Unsupported(f"{self.name}({k}): brute force needs an integer index")
        k = int(k)
        cache = self.m.bcache.setdefault(self.name, {})
        if k in cache:
            return cache[k]
        if self.kind in ("ap", "gp"):
            if k < 1:
                raise Unsupported(f"{self.name}({k}) undefined (terms start at 1)")
            a, d = (self.m.evB(x, env) for x in self.p)
            if "last" not in cache:
                cache[1], cache["last"] = a, 1
            j = cache["last"]
            v = cache[j]
            while j < k:
                v = v + d if self.kind == "ap" else v * d
                j += 1
                cache[j] = v
            cache["last"] = max(cache["last"], j)
            return cache[k]
        if self.kind == "term":
            v = self.m.evB(self.expr, {**env, self.n: sp.Integer(k)})
        elif self.kind == "by_parity":
            v = self.m.evB(self.odd if k % 2 else self.even, {**env, self.n: sp.Integer(k)})
        elif self.kind == "recurrence":
            if k < self.start:
                raise Unsupported(f"{self.name}({k}) before the initial values")
            if k in self.init:
                v = self.m.evB(self.init[k], env)
            else:
                prev = {s: self.B(k - self.hi + s, env) for s in range(self.lo, self.hi)}
                expr = self.step.replace(lambda x: isinstance(x, AppliedUndef) and x.func == self.f,
                                         lambda x: prev[int(sp.simplify(x.args[0] - self.n))])
                v = sp.simplify(self.m.evB(expr.subs(self.n, k - self.hi), env))
        else:  # fit: extend the difference table
            i = k - self.start
            if i < 0:
                raise Unsupported("fit index before the first given term")
            if i < len(self.vals):
                v = self.vals[i]
            else:
                rows = [list(self.vals)]
                for _ in range(self.deg):
                    r = rows[-1]
                    rows.append([r[t + 1] - r[t] for t in range(len(r) - 1)])
                if len(set(rows[-1])) != 1:
                    raise ModelError("given terms do not have constant order-deg differences")
                lasts = [r[-1] for r in rows]
                for _ in range(i - len(self.vals) + 1):
                    for lvl in range(self.deg - 1, -1, -1):
                        lasts[lvl] = lasts[lvl] + lasts[lvl + 1]
                v = lasts[0]
        cache[k] = v
        return v


class SeriesModel(_Model):
    prefix = "series"
    b_method = ("brute force: terms by iteration (AP/GP stepping, recurrence stepping, difference table), "
                "exact rational term-by-term sums, enumeration for counts")

    def __init__(self, formal: dict):
        super().__init__(formal)
        seqs = formal.get("sequences", {})
        dummies = set(formal.get("dummies", [])) | ({"r", "k", "j"} - set(self.unknowns) - set(seqs))
        for n in list(seqs) + list(dummies):
            _name_ok(n)
        if set(seqs) & set(self.unknowns) or dummies & set(self.unknowns) or dummies & set(seqs):
            raise ModelError("names of unknowns, sequences and dummies must be distinct")
        self.fns = {s: sp.Function(s) for s in seqs}
        self.dums = {d: sp.Symbol(d, integer=True) for d in dummies}
        self.ns = {**self.syms, **self.dums, **self.fns, **_SPECIAL}
        self.seqs = {s: _Seq(s, spec, self) for s, spec in seqs.items()}
        self.bcache: dict = {}
        self._parse_common()

    def reset_b(self):
        self.bcache = {}

    # ------------------------------------------------ closed-form evaluation
    def evC(self, e, sol: dict):
        e = sp.sympify(e)
        if not e.atoms(AppliedUndef):
            return e.xreplace(sol) if sol else e
        if isinstance(e, AppliedUndef):
            name = e.func.__name__
            if name in self.seqs:
                return self.seqs[name].C(self.evC(e.args[0], sol), sol)
            if e.func == SUM:
                body, var, lo, hi = e.args
                lo, hi = self.evC(lo, sol), self.evC(hi, sol)
                bc = self.evC(body, sol)
                if hi == sp.oo:
                    s = sp.summation(bc, (var, lo, sp.oo))
                    if s.has(sp.Sum):
                        raise Unsupported(f"no closed form for {body} summed to oo")
                    if s.has(sp.oo, sp.zoo, sp.nan, -sp.oo):
                        raise Divergent(f"sum of {bc} from {lo} to oo = {s}")
                    return sp.simplify(s)
                L, U = sp.Symbol("L_", integer=True), sp.Symbol("U_", integer=True)
                F = sp.summation(bc, (var, L, U))
                if F.has(sp.Sum):
                    raise Unsupported(f"no closed-form antiderivative for sum of {bc}")
                return sp.expand(F.subs({L: lo, U: hi}))
            if e.func in (COUNTINT, NUNION, NINTER):
                return self._count_C(e, sol)
            if e.func in (NUMER, DENOM):
                v = sp.nsimplify(sp.simplify(self.evC(e.args[0], sol)))
                if not v.is_Rational:
                    raise Unsupported(f"Numer/Denom of non-rational {v}")
                return sp.Integer(v.p if e.func == NUMER else v.q)
            raise Unsupported(f"function {name} not modelled")
        return e.func(*[self.evC(a, sol) for a in e.args])

    def _count_C(self, e, sol):
        if e.func == COUNTINT:
            expr, var, lo, hi = e.args
            lo, hi = self.evC(lo, sol), self.evC(hi, sol)
            ex = sp.expand(self.evC(expr, sol))
            if not (lo.is_Integer and hi.is_Integer):
                raise Unsupported("CountInt needs integer limits")
            p = sp.Poly(ex, var)
            if p.degree() > 1 or any(not c.is_Rational for c in p.all_coeffs()):
                raise Unsupported("CountInt needs an expression linear in the index with rational coefficients")
            q, c0 = (p.all_coeffs() + [0])[:2] if p.degree() == 1 else (sp.Integer(0), p.all_coeffs()[0])
            Lc = sp.ilcm(sp.Rational(q).q, sp.Rational(c0).q)
            Q, P0 = int(q * Lc), int(c0 * Lc)
            return sp.Integer(_count_cong(Q, -P0, int(Lc), int(lo), int(hi)))
        e1, e2, var, lo, hi = e.args
        lo, hi = self.evC(lo, sol), self.evC(hi, sol)
        if not (lo.is_Integer and hi.is_Integer):
            raise Unsupported("NUnion/NInter need integer limits")
        lin = []
        for ex in (e1, e2):
            p = sp.Poly(sp.expand(self.evC(ex, sol)), var)
            if p.degree() != 1 or any(not c.is_Rational for c in p.all_coeffs()):
                raise Unsupported("NUnion/NInter need non-constant terms linear in the index")
            lin.append(p.all_coeffs())
        (q1, p1), (q2, p2) = lin
        Lc = sp.ilcm(*[sp.Rational(x).q for x in (q1, p1, q2, p2)])
        Q1, P1, Q2, P2 = (int(x * Lc) for x in (q1, p1, q2, p2))
        inter = _count_lin_inter(Q1, P1, Q2, P2, int(lo), int(hi))
        n = int(hi) - int(lo) + 1
        return sp.Integer(inter if e.func == NINTER else 2 * n - inter)

    # ------------------------------------------------ brute-force evaluation
    def evB(self, e, env: dict):
        e = sp.sympify(e)
        if isinstance(e, IvVal):
            return e
        if e.is_Symbol:
            if e in env:
                return env[e]
            raise Unsupported(f"brute force: {e} has no value")
        if e.is_Atom:
            return e
        if isinstance(e, AppliedUndef):
            name = e.func.__name__
            if name in self.seqs:
                return self.seqs[name].B(self.evB(e.args[0], env), env)
            if e.func == SUM:
                return self._sum_B(e, env)
            if e.func == COUNTINT:
                expr, var, lo, hi = e.args
                lo, hi = int(self.evB(lo, env)), int(self.evB(hi, env))
                cnt = 0
                for k in range(lo, hi + 1):
                    v = self.evB(expr, {**env, var: sp.Integer(k)})
                    if is_exact_integer(v):
                        cnt += 1
                return sp.Integer(cnt)
            if e.func in (NUNION, NINTER):
                e1, e2, var, lo, hi = e.args
                lo, hi = int(self.evB(lo, env)), int(self.evB(hi, env))
                s1 = {self.evB(e1, {**env, var: sp.Integer(k)}) for k in range(lo, hi + 1)}
                s2 = {self.evB(e2, {**env, var: sp.Integer(k)}) for k in range(lo, hi + 1)}
                if any(not v.is_Rational for v in s1 | s2):
                    raise Unsupported("set counting needs rational members")
                return sp.Integer(len(s1 | s2) if e.func == NUNION else len(s1 & s2))
            if e.func in (NUMER, DENOM):
                v = self.evB(e.args[0], env)
                if isinstance(v, IvVal) or not v.is_Rational:
                    raise Unsupported("Numer/Denom of non-rational")
                from fractions import Fraction
                fr = Fraction(int(v.p), int(v.q))     # independent reduction (Python gcd)
                return sp.Integer(fr.numerator if e.func == NUMER else fr.denominator)
            raise Unsupported(f"function {name} not modelled")
        return _apply(e.func, [self.evB(a, env) for a in e.args])

    def _sum_B(self, e, env):
        body, var, lo, hi = e.args
        lo, hi = self.evB(lo, env), self.evB(hi, env)
        if not lo.is_Integer:
            raise Unsupported("brute-force sum needs an integer lower limit")
        if hi == sp.oo:
            sol = {k: v for k, v in env.items() if k in set(self.syms.values())}
            outer = {k: v for k, v in env.items() if k not in sol}
            f = self.evC(body.xreplace(outer), sol)
            for N, label in ((PARTIAL_RATIO, "ratio"), (PARTIAL_INTEGRAL, "integral")):
                K = int(lo) + N
                try:
                    tlo, thi, how = tail_bound(f, var, K)
                except Unsupported:
                    continue
                if (label == "ratio" and not how.startswith("ratio")):
                    continue
                old = iv.dps
                iv.dps = 50
                try:
                    acc = iv.mpf(0)
                    for k in range(int(lo), K):
                        t = self.evB(body, {**env, var: sp.Integer(k)})
                        acc = acc + (t.x if isinstance(t, IvVal) else IvVal.of(t).x)
                    acc = acc + iv.mpf([str(sp.N(tlo, 60) - sp.Float("1e-58", 60)),
                                        str(sp.N(thi, 60) + sp.Float("1e-58", 60))])
                finally:
                    iv.dps = old
                return IvVal(acc)
            raise Unsupported(f"no certified tail bound for sum of {f}")
        if not hi.is_Integer:
            raise Unsupported("brute-force sum needs integer limits")
        terms = [self.evB(body, {**env, var: sp.Integer(k)}) for k in range(int(lo), int(hi) + 1)]
        if any(isinstance(t, IvVal) for t in terms):
            return _iv_combine(sp.Add, terms) if terms else sp.Integer(0)
        return sp.Add(*terms)


def _egcd(a: int, b: int):
    if b == 0:
        return a, 1, 0
    g, x, y = _egcd(b, a % b)
    return g, y, x - (a // b) * y


def _count_cong(Q: int, R: int, M: int, lo: int, hi: int) -> int:
    """#{v in [lo, hi] : Q v = R (mod M)}."""
    if hi < lo:
        return 0
    g = math.gcd(Q % M, M) if Q % M else M
    if R % g:
        return 0
    if Q % M == 0:
        return hi - lo + 1 if R % M == 0 else 0
    m2 = M // g
    _, inv, _ = _egcd((Q // g) % m2, m2)
    v0 = (R // g * inv) % m2 if m2 > 1 else 0
    first = lo + ((v0 - lo) % m2)
    return 0 if first > hi else (hi - first) // m2 + 1


def _count_lin_inter(Q1, P1, Q2, P2, lo, hi) -> int:
    """#{values P1 + Q1 i = P2 + Q2 j, i, j in [lo, hi]} (Q1, Q2 nonzero integers)."""
    # Q1 i - Q2 j = P2 - P1
    g, x, y = _egcd(abs(Q1), abs(Q2))
    rhs = P2 - P1
    if rhs % g:
        return 0
    x *= (1 if Q1 > 0 else -1)
    y *= (1 if Q2 > 0 else -1)
    i0, j0 = x * (rhs // g), -y * (rhs // g)       # Q1 i0 - Q2 j0 = rhs
    di, dj = Q2 // g, Q1 // g                      # i = i0 + di t, j = j0 + dj t
    lo_t, hi_t = -10**30, 10**30
    for base, step in ((i0, di), (j0, dj)):
        a, b = sp.Rational(lo - base, step), sp.Rational(hi - base, step)
        a, b = min(a, b), max(a, b)
        lo_t, hi_t = max(lo_t, int(sp.ceiling(a))), min(hi_t, int(sp.floor(b)))
    return max(0, hi_t - lo_t + 1)


# ======================================================================= statistics model
class StatsModel(_Model):
    prefix = "stats"
    b_method = ("definition formulas on an explicit data list (variance = sum (x - mean)^2 / n; frequency table "
                "for median/mode/mean deviation; ogive interpolation for grouped median; constructed witness "
                "data set for aggregate-only data)")

    def __init__(self, formal: dict):
        super().__init__(formal)
        conv = formal.get("variance", "population")
        if conv != "population":
            raise ModelError(f"variance convention {conv!r} not supported (JEE uses population, divide by n)")
        ds = formal.get("datasets", {})
        if not ds:
            raise ModelError("no datasets")
        for n in ds:
            _name_ok(n)
        if set(ds) & set(self.unknowns) or {"t", "i"} & (set(ds) | set(self.unknowns)):
            raise ModelError("dataset names, unknowns and the map variables t, i must be distinct")
        self.dsym = {n: sp.Symbol(n) for n in ds}
        self.t, self.i = sp.Symbol("t", real=True), sp.Symbol("i", integer=True, positive=True)
        self.ns = {**self.syms, **self.dsym, **_STATS, "t": self.t, "i": self.i, "factorial": sp.factorial}
        self.ds: dict[str, dict] = {}
        for n, spec in ds.items():
            self.ds[n] = self._parse_ds(n, spec)
        self._parse_common()
        for n, d in self.ds.items():
            if d["type"] == "grouped":
                N, cf, f = d["total"], d["cf"], d["freq"]
                self.cons.append((cf, sp.Le, N / 2, f"median class contains the N/2-th value ({n})"))
                self.cons.append((N / 2, sp.Le, cf + f, f"median class contains the N/2-th value ({n})"))
        self.extra.append(VerificationRecord(
            check_id="stats.convention", status=CheckStatus.RULE_CHECKED, hard=False, tool=TOOL,
            method="declared convention",
            result="population variance sigma^2 = (1/n) sum (x - mean)^2 (JEE convention); sd = sqrt(variance); "
                   "mean deviation about c = (1/n) sum |x - c|; grouped median = l + (N/2 - cf) h / f"))

    def _parse_ds(self, n, spec):
        P = lambda s: parse(str(s), self.ns)  # noqa: E731
        if "values" in spec:
            return {"type": "values", "vals": [P(v) for v in spec["values"]]}
        if "ap" in spec:
            a, d, last = (P(spec["ap"][k]) for k in ("first", "diff", "last"))
            cnt = sp.simplify((last - a) / d + 1)
            if not (cnt.is_Integer and cnt > 0):
                raise ModelError(f"{n}: last term is not in the progression")
            return {"type": "values", "vals": [a + k * d for k in range(int(cnt))]}
        if "aggregate" in spec:
            g = spec["aggregate"]
            return {"type": "aggregate", "n": P(g["n"]), "P1": P(g["sum"]), "P2": P(g["sumsq"])}
        if "transform" in spec:
            g = spec["transform"]
            if g["of"] not in spec and g["of"] not in self.dsym:
                raise ModelError(f"{n}: unknown source {g['of']}")
            return {"type": "transform", "of": g["of"], "map": P(g["map"])}
        if "replace" in spec:
            g = spec["replace"]
            return {"type": "replace", "of": g["of"], "remove": [P(v) for v in g.get("remove", [])],
                    "add": [P(v) for v in g.get("add", [])]}
        if "grouped_median_class" in spec:
            g = spec["grouped_median_class"]
            return {"type": "grouped", "lower": P(g["lower"]), "width": P(g["width"]), "freq": P(g["freq"]),
                    "cf": P(g["cf_before"]), "total": P(g["total"])}
        raise ModelError(f"{n}: unknown dataset definition {list(spec)}")

    # ------------------------------------------------ shortcut (aggregate) representation
    def _agg(self, name, sol) -> dict:
        d = self.ds[name]
        X = lambda e: sp.sympify(e).xreplace(sol)  # noqa: E731
        if d["type"] == "values":
            v = [X(x) for x in d["vals"]]
            return {"n": sp.Integer(len(v)), "P1": sp.Add(*v), "P2": sp.Add(*[x**2 for x in v]), "vals": v}
        if d["type"] == "aggregate":
            return {"n": X(d["n"]), "P1": X(d["P1"]), "P2": X(d["P2"]), "vals": None}
        if d["type"] == "transform":
            s = self._agg(d["of"], sol)
            mp = X(d["map"])
            if s["vals"] is not None:
                v = [mp.xreplace({self.t: x, self.i: k + 1}) for k, x in enumerate(s["vals"])]
                return {"n": s["n"], "P1": sp.Add(*v), "P2": sp.Add(*[x**2 for x in v]), "vals": v}
            if mp.has(self.i):
                raise Unsupported("position-dependent transform of aggregate-only data")
            p = sp.Poly(sp.expand(mp), self.t)
            if p.degree() > 1:
                raise Unsupported("non-linear transform of aggregate-only data")
            al, be = (p.all_coeffs() if p.degree() == 1 else [sp.Integer(0)] + p.all_coeffs())
            n = s["n"]
            return {"n": n, "P1": al * s["P1"] + n * be, "P2": al**2 * s["P2"] + 2 * al * be * s["P1"] + n * be**2,
                    "vals": None}
        if d["type"] == "replace":
            s = self._agg(d["of"], sol)
            rem, add = [X(x) for x in d["remove"]], [X(x) for x in d["add"]]
            if s["vals"] is not None:
                v = list(s["vals"])
                for r in rem:
                    hit = next((j for j, x in enumerate(v) if sp.simplify(x - r) == 0), None)
                    if hit is None:
                        raise ModelError(f"{name}: removed value {r} not in the data")
                    v.pop(hit)
                v += add
                return {"n": sp.Integer(len(v)), "P1": sp.Add(*v), "P2": sp.Add(*[x**2 for x in v]), "vals": v}
            return {"n": s["n"] - len(rem) + len(add), "P1": s["P1"] - sum(rem) + sum(add),
                    "P2": s["P2"] - sum(x**2 for x in rem) + sum(x**2 for x in add), "vals": None}
        return {"grouped": {k: X(v) for k, v in d.items() if k != "type"}}

    def evC(self, e, sol: dict):
        e = sp.sympify(e)
        if not e.atoms(AppliedUndef):
            return e.xreplace(sol) if sol else e
        if isinstance(e, AppliedUndef):
            X = e.args[0]
            if not (X.is_Symbol and str(X) in self.ds):
                raise ModelError(f"{e.func.__name__} needs a dataset name, got {X}")
            a = self._agg(str(X), sol)
            if "grouped" in a:
                g = a["grouped"]
                if e.func == MEDIAN:
                    return g["lower"] + (g["total"] / 2 - g["cf"]) * g["width"] / g["freq"]
                if e.func == NOBS:
                    return g["total"]
                raise Unsupported(f"{e.func.__name__} of a grouped median class")
            n, P1, P2, vals = a["n"], a["P1"], a["P2"], a["vals"]
            if e.func == NOBS:
                return n
            if e.func == MEAN:
                return P1 / n
            if e.func in (VAR, SD):
                v = P2 / n - (P1 / n) ** 2
                return v if e.func == VAR else sp.sqrt(v)
            if e.func == SUMF:
                body = self.evC(e.args[1], sol)
                if vals is not None:
                    return sp.Add(*[body.xreplace({self.t: x, self.i: k + 1}) for k, x in enumerate(vals)])
                if body.has(self.i):
                    raise Unsupported("position-dependent sum over aggregate-only data")
                p = sp.Poly(sp.expand(body), self.t)
                if p.degree() > 2:
                    raise Unsupported("sum of a degree > 2 function needs higher power sums")
                c = dict(zip(range(p.degree(), -1, -1), p.all_coeffs()))
                return c.get(0, 0) * n + c.get(1, 0) * P1 + c.get(2, 0) * P2
            # order statistics need the explicit, concrete data
            if vals is None or any(sp.sympify(x).free_symbols for x in vals):
                raise Unsupported(f"{e.func.__name__} needs explicit numeric data")
            srt = sorted(vals, key=lambda x: sp.N(x, 50))
            if e.func == MEDIAN:
                k = len(srt)
                return srt[k // 2] if k % 2 else (srt[k // 2 - 1] + srt[k // 2]) / 2
            if e.func == MODE:
                runs, cur = [], [srt[0]]
                for x in srt[1:]:
                    if sp.simplify(x - cur[-1]) == 0:
                        cur.append(x)
                    else:
                        runs.append(cur)
                        cur = [x]
                runs.append(cur)
                top = max(len(r) for r in runs)
                winners = [r for r in runs if len(r) == top]
                if len(winners) != 1:
                    raise Unsupported(f"data are multimodal ({[w[0] for w in winners]})")
                return winners[0][0]
            if e.func == MD:
                c = self.evC(e.args[1], sol)
                return sp.Add(*[sp.Abs(x - c) for x in srt]) / len(srt)
            raise Unsupported(f"{e.func.__name__} not modelled")
        return e.func(*[self.evC(a, sol) for a in e.args])

    # ------------------------------------------------ definition representation (explicit list)
    def _required(self, name, env) -> list:
        req = []
        for d in self.ds.values():
            if d["type"] == "replace" and d["of"] == name:
                req += [self.evB(x, env) for x in d["remove"]]
        return req

    def _list(self, name, env) -> list:
        d = self.ds[name]
        if d["type"] == "values":
            return [self.evB(x, env) for x in d["vals"]]
        if d["type"] == "aggregate":
            n, P1, P2 = (self.evB(d[k], env) for k in ("n", "P1", "P2"))
            if not (n.is_Integer and n > 0):
                raise Unsupported(f"{name}: number of observations {n} is not a positive integer")
            req = self._required(name, env)
            k = int(n) - len(req)
            s, q = P1 - sp.Add(*req), P2 - sp.Add(*[x**2 for x in req])
            if k < 0:
                raise ModelError(f"{name}: more removed values than observations")
            if k == 0:
                if sp.simplify(s) != 0 or sp.simplify(q) != 0:
                    raise ModelError(f"{name}: aggregates inconsistent with the listed values")
                return req
            m = s / k
            spread = sp.simplify(q - k * m**2)
            if _truth(spread >= 0) is not True:
                raise ModelError(f"{name}: no real data set has n={n}, sum={P1}, sum of squares={P2} "
                                 f"(containing {req}); spread {spread} < 0")
            if k == 1:
                if spread != 0:
                    raise ModelError(f"{name}: aggregates inconsistent")
                return req + [m]
            tt = sp.sqrt(spread / 2)
            return req + [m] * (k - 2) + [m - tt, m + tt]
        if d["type"] == "transform":
            src = self._list(d["of"], env)
            mp = d["map"].xreplace(env)
            return [sp.simplify(mp.xreplace({self.t: x, self.i: sp.Integer(k + 1)})) for k, x in enumerate(src)]
        if d["type"] == "replace":
            src = list(self._list(d["of"], env))
            for r in [self.evB(x, env) for x in d["remove"]]:
                hit = next((j for j, x in enumerate(src) if sp.simplify(x - r) == 0), None)
                if hit is None:
                    raise ModelError(f"{name}: removed value {r} not in the data")
                src.pop(hit)
            return src + [self.evB(x, env) for x in d["add"]]
        raise Unsupported("grouped class has no explicit list")

    def evB(self, e, env: dict):
        e = sp.sympify(e)
        if e.is_Symbol:
            if e in env:
                return env[e]
            raise Unsupported(f"definition check: {e} has no value")
        if e.is_Atom:
            return e
        if isinstance(e, AppliedUndef):
            name = str(e.args[0])
            d = self.ds[name]
            if d["type"] == "grouped":
                g = {k: self.evB(v, env) for k, v in d.items() if k != "type"}
                if e.func == NOBS:
                    return g["total"]
                if e.func == MEDIAN:   # ogive: cumulative frequency rises linearly across the class
                    x = sp.Symbol("x_")
                    sol = sp.solve(sp.Eq(g["cf"] + g["freq"] * (x - g["lower"]) / g["width"], g["total"] / 2), x)
                    if len(sol) != 1:
                        raise Unsupported("ogive interpolation not unique")
                    return sol[0]
                raise Unsupported(f"{e.func.__name__} of a grouped class")
            xs = self._list(name, env)
            n = len(xs)
            if e.func == NOBS:
                return sp.Integer(n)
            mean = sp.Add(*xs) / n
            if e.func == MEAN:
                return sp.simplify(mean)
            if e.func in (VAR, SD):
                v = sp.simplify(sp.expand(sp.Add(*[(x - mean) ** 2 for x in xs]) / n))
                return v if e.func == VAR else sp.sqrt(v)
            if e.func == SUMF:
                body = e.args[1].xreplace(env)
                return sp.simplify(sp.Add(*[body.xreplace({self.t: x, self.i: sp.Integer(k + 1)})
                                            for k, x in enumerate(xs)]))
            # frequency table (distinct value -> count), built by exact comparison
            table: list[list] = []
            for x in xs:
                for row in table:
                    if sp.simplify(row[0] - x) == 0:
                        row[1] += 1
                        break
                else:
                    table.append([x, 1])
            table.sort(key=lambda r: sp.N(r[0], 50))
            if e.func == MODE:
                fmax = max(r[1] for r in table)
                w = [r[0] for r in table if r[1] == fmax]
                if len(w) != 1:
                    raise Unsupported("multimodal")
                return w[0]
            if e.func == MEDIAN:
                def kth(k):
                    cum = 0
                    for val, f in table:
                        cum += f
                        if cum >= k:
                            return val
                return kth((n + 1) // 2) if n % 2 else (kth(n // 2) + kth(n // 2 + 1)) / 2
            if e.func == MD:
                c = self.evB(e.args[1], env)
                return sp.simplify(sp.Add(*[f * sp.Abs(val - c) for val, f in table]) / sum(f for _, f in table))
            raise Unsupported(f"{e.func.__name__} not modelled")
        return _apply(e.func, [self.evB(a, env) for a in e.args])


# ======================================================================= entry point
def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - registry signature
    res = EngineResult()
    kind = formal.get("kind")
    cls = {"series_sum": SeriesModel, "statistics": StatsModel}.get(kind)
    if cls is None:
        res.records.append(VerificationRecord(check_id="series_stats.kind", status=CheckStatus.UNRESOLVED,
                                              method="dispatch", result=f"kind {kind!r} not handled here"))
        return res
    st: dict = {}

    def _build():
        try:
            st["m"] = cls(formal)
        except (ModelError, Unsupported) as e:
            return VerificationRecord(check_id=f"{cls.prefix}.structure", status=CheckStatus.FAILED
                                      if isinstance(e, ModelError) else CheckStatus.UNRESOLVED,
                                      method="schema + whitelist parse", tool=TOOL, result=str(e))
        m = st["m"]
        return VerificationRecord(check_id=f"{cls.prefix}.structure", status=CheckStatus.EXACT_CHECKED,
                                  method="schema + whitelist parse", tool=TOOL,
                                  assumptions=list(formal.get("model", [])),
                                  result=f"{len(m.conds)} condition(s), {len(m.cons)} selection rule(s), "
                                         f"{len(m.syms)} unknown(s)")

    res.records.append(guarded(f"{cls.prefix}.structure", _build, seconds=20))
    if "m" not in st or not res.records[-1].is_affirmative():
        return res
    m = st["m"]
    res.records.extend(m.extra)
    _pipeline(m, res)
    if any(r.hard and not r.is_affirmative() for r in res.records):
        res.value = None
    res.records.append(VerificationRecord(
        check_id="model.correspondence", status=CheckStatus.UNRESOLVED,
        method="teacher confirms the formal state models the stem",
        result="sequence/statistics model must be confirmed by a subject teacher",
        data={"conditions": formal.get("conditions", []), "target": formal.get("target"),
              "model": formal.get("model", [])}))
    return res
