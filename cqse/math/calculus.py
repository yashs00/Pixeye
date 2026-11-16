"""Calculus engine: areas of plane regions, extrema / monotonicity, and derivative/integral conditions.

Kinds served (see cqse/engines.py): ``area_region``, ``extrema``, ``calculus_value``.  All three share one small
interpreter; the kind only documents the intent.  Every answer is established by an EXACT symbolic computation
and confirmed by an INDEPENDENT numeric method; any disagreement, timeout, unbounded region, unattained extremum,
undecidable comparison or unmodelled construct returns ``value=None`` with a hard UNRESOLVED record (fail closed).

Formal schema (all strings are parsed with ``cqse.math.expr.parse``; ``Max``/``Min``/``sign`` are added here)
--------------------------------------------------------------------------------------------------------------
Common keys::

    "var":     "x"                          # independent variable of the function defs (default "x")
    "params":  {"a": "a > 0", "b": null}    # unknowns, each with an optional assumption ("a>0", "a != 0", ...)
    "locals":  ["t"]                        # extra free symbols used inside ops (e.g. a family parameter)
    "defs":    {name: spec}                 # functions of `var`; usable as f(3), df(3) (f'), d2f(3) (f'')
        spec = "expr"                                                  # ordinary expression
             | {"piecewise": [["expr", "cond"], ...]}                    # cond like "x < -1" / "-1 <= x <= 2"
             | {"integral": "g(t)", "t": "t", "lower": "0", "upper": "x^2"}   # f'(x) by Leibniz' rule
             | {"volterra": {"forcing": "1-2*x", "kernel": "exp(x-t)", "t": "t"}}
                  # f(x) = forcing + int_0^x kernel(x-t) f(t) dt, solved by Laplace transform and
                  # substituted back exactly (uniqueness: Volterra equation of the 2nd kind, continuous kernel)
    "equations": ["df(4) = 0", {"limit": "f(x)/x^2", "at": "0", "equals": "5"}, "A = (E^2+8*E+1)/E"]
                  # determine the params (solved exactly; every solution is then re-verified concretely)
    "param_sample": {"a": "1"}              # only when an equation uses the area A with a symbolic parameter
    "param_scan":   {"a": ["0", "20", 8]}   # optional: residual sign scan to back uniqueness of that root
    "quantities": [ {"name": "M" | ["b", "c"], "op": ..., ...}, ... ]   # evaluated in order
    "checks":     ["M > 1", {"op": ..., "equals": [...]} ]               # stem facts; a False check rejects
                                                                         # a parameter candidate
    "target":   "100*(a+b-c)"               # expression in params / quantity names / defs (e.g. "f(2)")
    "approximations": {"log(2)": "7/10"}    # stem-given numeric substitutions applied to the exact target
    "match": {"template": "(b*pi+c)/4", "unknowns": {"b": "natural", "c": "natural"},
              "basis": ["pi"], "answer": "b+c"}
              # write the target value exactly as the template (basis assumed Q-linearly independent with 1)

Quantity / check ops::

    {"op": "area", "region": [...], ...}            see area_region below (the area_region kind binds "A")
    {"op": "extrema", "fn": "f", "kind": "max"|"min", "return": "points"|"values"|"count"|"sum",
     "interval": ["lo", "hi"]}                     # local extrema at interior points (strict, by sign of f'
                                                   # and one-sided limits at corners/jumps)
    {"op": "monotone", "fn": "f", "mode": "increasing"|"decreasing", "return": "endpoints"|"intervals"}
    {"op": "abs_max"|"abs_min", "fn": "f", "interval": ["lo", "hi"], "closed": [true, true],
     "return": "value"|"point"}                    # fails if the sup/inf is not attained
    {"op": "critical_points", "fn": "f"}            # zeros of f' and points of non-differentiability in domain
    {"op": "roots", "expr": "...", "interval": ["0", "oo"]}           # real roots in the open interval
    {"op": "root_count_set", "poly": "5*x^3-15*x-a", "param": "a", "count": 3, "return": "endpoints"}
                                                   # set of the (local) parameter for which the polynomial
                                                   # equation has exactly `count` distinct real roots
    {"op": "expr", "expr": "..."}
  A check dict carries "equals": "v" | ["v1", ...] (exact list equality) or "contains": [...].

area_region kind (binds the area to the name "A")::

    "region": ["Abs(x-y) <= y <= 4*sqrt(x)", {"any": [...]}, {"not": "..."}]   # conjunction of inequalities
    "split": "y >= Abs(x-1)", "portion": "larger"|"smaller"   # optional: piece of region cut by `split`
    "bounded_part": true                                       # area of the bounded component(s) only

Exact area: every inequality boundary (Abs/Max/Min expanded into all cases) is solved for y; all special x
(intersections, domain ends, x-only boundaries) partition the line; on each strip the candidate curves are
ordered and each y-cell is classified by evaluating the ORIGINAL predicate at an interior point; the in-region
cells are integrated exactly.  Unbounded in-region cells -> fail (unless bounded_part).  Numeric check: an
independent slice length L(x) = |{y : predicate}| obtained by scanning + bisection of the predicate itself,
compared pointwise with the exact slices and integrated by tanh-sinh quadrature.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import mpmath
import sympy as sp

from cqse.core.evidence import CheckStatus, CheckTimeout, VerificationRecord, time_limit
from cqse.core.result import EngineResult
from cqse.math.expr import parse

TOOL = f"sympy {sp.__version__} / mpmath {mpmath.__version__}"
X = sp.Symbol("x", real=True)
Y = sp.Symbol("y", real=True)
_YP = sp.Symbol("yy")  # plain symbol used when solving boundaries for y
_EXTRA_FUNCS = {"Max": sp.Max, "Min": sp.Min, "sign": sp.sign}
_REL = re.compile(r"(<=|>=|!=|==|=|<|>)")
_RTOL = 1e-7


class CalcError(Exception):
    """A fail-closed condition: the engine cannot establish the answer."""


# ----------------------------------------------------------------------------------------------- exact helpers
def _N(v, prec: int = 40):
    """Complex mpmath value of a closed-form number (None if not a finite number)."""
    try:
        z = sp.N(sp.sympify(v), prec)
        c = complex(z)
    except (TypeError, ValueError, AttributeError, ZeroDivisionError, OverflowError):
        return None
    if not (math.isfinite(c.real) and math.isfinite(c.imag)):
        return None
    return c


def _real(v, prec: int = 40) -> Optional[float]:
    c = _N(v, prec)
    if c is None or abs(c.imag) > 1e-25 * max(1.0, abs(c.real)):
        return None
    return c.real


def _mpreal(v, dps: int = 40):
    try:
        with mpmath.workdps(dps):
            z = sp.N(sp.sympify(v), dps)
            if not z.is_number or z.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                return None
            re_, im_ = z.as_real_imag()
            r, i = mpmath.mpf(str(re_)), mpmath.mpf(str(im_))
            if abs(i) > mpmath.mpf(10) ** (-dps + 10) * max(1, abs(r)):
                return None
            return r
    except (TypeError, ValueError, AttributeError):
        return None


def is_zero(d) -> Optional[bool]:
    """Exact zero test for a closed-form number: True / False / None (undecided)."""
    d = sp.sympify(d)
    if d == 0:
        return True
    if not d.is_number:
        s = sp.simplify(d)
        return True if s == 0 else None
    c = _N(d, 60)
    if c is None:
        return None
    if abs(c) > 1e-40:
        return False
    for f in (sp.simplify, lambda e: sp.radsimp(sp.expand(e)), lambda e: sp.nsimplify(sp.simplify(e)),
              lambda e: sp.simplify(e.rewrite(sp.atan))):
        try:
            if f(d) == 0:
                return True
        except Exception:  # noqa: BLE001
            pass
    z = sp.Dummy("z")
    try:
        if not d.has(sp.pi, sp.E, sp.exp, sp.log, sp.asin, sp.acos, sp.atan, sp.sin, sp.cos):
            if sp.minimal_polynomial(d, z) == z:
                return True
    except Exception:  # noqa: BLE001
        pass
    # inverse-trig identities: sin(d) == 0 exactly and |d| < pi  =>  d == 0
    try:
        s = sp.simplify(sp.expand_trig(sp.sin(d)))
        if abs(c) < 1 and (s == 0 or (not s.has(sp.pi, sp.sin, sp.cos, sp.asin, sp.acos, sp.atan, sp.log, sp.exp)
                                      and sp.minimal_polynomial(s, z) == z)):
            return True
    except Exception:  # noqa: BLE001
        pass
    return None


def cmp_exact(a, b) -> int:
    """Sign of a-b for closed-form reals; CalcError if undecidable."""
    d = sp.sympify(a) - sp.sympify(b)
    c = _N(d, 60)
    if c is None:
        raise CalcError(f"cannot compare {a} and {b}")
    if abs(c.imag) > 1e-30:
        raise CalcError(f"non-real comparison {a} vs {b}")
    if abs(c.real) > 1e-40:
        return 1 if c.real > 0 else -1
    z = is_zero(d)
    if z is True:
        return 0
    raise CalcError(f"comparison of {a} and {b} undecidable (numerically equal, not proven)")


def _simplest(e):
    e = sp.sympify(e)
    cands = [e]
    for f in (sp.simplify, sp.nsimplify, lambda t: sp.radsimp(sp.simplify(t))):
        try:
            cands.append(f(e))
        except Exception:  # noqa: BLE001
            pass
    good = [c for c in cands if is_zero(c - e) is True or c is e]
    return min(good, key=sp.count_ops)


def _basis_atoms(v) -> list:
    out = set()
    for a in sp.preorder_traversal(v):
        if isinstance(a, sp.Pow) and a.exp.is_Rational and not a.exp.is_Integer and a.base.is_Integer:
            out.add(sp.root(a.base, a.exp.q))
        elif isinstance(a, sp.log) and a.args[0].is_Rational:
            out.add(sp.log(a.args[0]))
        elif a == sp.E or isinstance(a, sp.exp):
            out.update({sp.E, 1 / sp.E})
        elif a == sp.pi or isinstance(a, (sp.asin, sp.acos, sp.atan)):
            out.add(sp.pi)
    return sorted(out, key=sp.default_sort_key)


def identify(v, basis: Optional[list] = None) -> Optional[list]:
    """Rational coefficients q with v = q0 + sum q_i basis_i, PROVEN exactly; None if not found/proven."""
    basis = list(basis if basis is not None else _basis_atoms(v))
    with mpmath.workdps(60):
        vals = [_mpreal(v, 60), mpmath.mpf(1)] + [_mpreal(b, 60) for b in basis]
        if any(x is None for x in vals):
            return None
        rel = mpmath.pslq(vals, maxcoeff=10 ** 7, maxsteps=10 ** 5)
    if not rel or rel[0] == 0:
        return None
    q = [sp.Rational(-r, rel[0]) for r in rel[1:]]
    cand = q[0] + sum(qi * b for qi, b in zip(q[1:], basis))
    if is_zero(sp.sympify(v) - cand) is True:
        return q
    return None


def canonical(v):
    """Present a proven-equal simpler closed form when the raw exact result is messy."""
    v = sp.sympify(v)
    s = _simplest(v)
    if s.has(sp.asin, sp.acos, sp.atan, sp.CRootOf) or sp.count_ops(s) > 25:
        basis = _basis_atoms(s)
        q = identify(s, basis)
        if q is not None:
            return q[0] + sum(qi * b for qi, b in zip(q[1:], basis))
    return s


# ----------------------------------------------------------------------------------------------- parsing env
def _split_rel(s: str) -> list[tuple[str, str, str]]:
    parts = _REL.split(s)
    if len(parts) < 3:
        raise CalcError(f"not a relation: {s!r}")
    exprs, ops = parts[0::2], parts[1::2]
    ops = ["=" if o == "==" else o for o in ops]
    return [(exprs[i], ops[i], exprs[i + 1]) for i in range(len(ops))]


def _rel_true(lhs, op, rhs) -> bool:
    c = cmp_exact(lhs, rhs)
    return {"<": c < 0, "<=": c <= 0, ">": c > 0, ">=": c >= 0, "=": c == 0, "!=": c != 0}[op]


@dataclass
class FnDef:
    name: str
    var: sp.Symbol
    expr: sp.Expr                       # exact closed form (may contain Abs/Max/Piecewise)
    deriv: Optional[sp.Expr] = None     # explicit derivative (Leibniz); else diff(expr)
    kind: str = "expr"
    integrand: Optional[tuple] = None   # (g, t, lower, upper) for integral defs
    domain: Optional[tuple] = None      # closed (lo, hi)
    notes: list = field(default_factory=list)


class Env:
    def __init__(self, formal: dict, subs: Optional[dict] = None):
        self.formal = formal
        self.var = sp.Symbol(formal.get("var", "x"), real=True)
        self.params = {p: sp.Symbol(p, real=True) for p in (formal.get("params") or {})}
        self.locals = {n: sp.Symbol(n, real=True) for n in formal.get("locals", [])}
        self.subs = subs or {}
        self.qsyms: dict[str, sp.Symbol] = {}
        self.defs: dict[str, FnDef] = {}
        self._funcs: dict[str, sp.Function] = {}
        for name in formal.get("defs") or {}:
            for pre in ("", "d", "d2"):
                self._funcs[pre + name] = sp.Function(pre + name)
        for name, spec in (formal.get("defs") or {}).items():
            self.defs[name] = self._build_def(name, spec)

    # symbols visible to the parser
    def symbols(self) -> dict:
        d = {"x": X, "y": Y, self.var.name: self.var}
        d.update(_EXTRA_FUNCS)
        d.update(self.params)
        d.update(self.locals)
        d.update(self._funcs)
        d.update(self.qsyms)
        return d

    def parse(self, s: str, expand: bool = True) -> sp.Expr:
        if not isinstance(s, str):
            s = str(s)
        e = parse(s.replace("**", "^"), self.symbols())
        if expand:
            e = self.expand(e)
        return e.subs(self.subs) if self.subs else e

    def expand(self, e):
        """Replace applied def functions f(u), df(u), d2f(u) by their closed forms."""
        def repl(app):
            nm = app.func.__name__
            for pre in ("d2", "d", ""):
                base = nm[len(pre):] if nm.startswith(pre) else None
                if base is not None and base in self.defs and (pre + base) == nm:
                    fd = self.defs[base]
                    body = fd.expr if pre == "" else (self.deriv(base) if pre == "d"
                                                      else sp.diff(self.deriv(base), fd.var))
                    return body.subs(fd.var, app.args[0])
            raise CalcError(f"unknown function {nm}")
        return e.replace(lambda a: isinstance(a, sp.core.function.AppliedUndef), repl)

    def deriv(self, name: str) -> sp.Expr:
        fd = self.defs[name]
        return fd.deriv if fd.deriv is not None else sp.diff(fd.expr, fd.var)

    def _build_def(self, name: str, spec) -> FnDef:
        v = self.var
        if isinstance(spec, dict) and "var" in spec:
            v = sp.Symbol(spec["var"], real=True)
        dom = None
        if isinstance(spec, dict) and "domain" in spec:
            dom = tuple(self.parse(s) for s in spec["domain"])
        if isinstance(spec, str) or (isinstance(spec, dict) and "expr" in spec):
            s = spec if isinstance(spec, str) else spec["expr"]
            return FnDef(name, v, self.parse(s), domain=dom)
        if "piecewise" in spec:
            pairs = []
            for ex, cond in spec["piecewise"]:
                c = sp.And(*[_mk_rel(self.parse(a), op, self.parse(b)) for a, op, b in _split_rel(cond)])
                pairs.append((self.parse(ex), c))
            return FnDef(name, v, sp.Piecewise(*pairs), kind="piecewise", domain=dom)
        if "integral" in spec:
            t = sp.Symbol(spec.get("t", "t"), real=True)
            self.locals.setdefault(t.name, t)
            g = self.parse(spec["integral"])
            g = g.subs(self.locals[t.name], t)
            lo, hi = self.parse(spec["lower"]), self.parse(spec["upper"])
            der = g.subs(t, hi) * sp.diff(hi, v) - g.subs(t, lo) * sp.diff(lo, v)
            try:
                with_closed = sp.integrate(g, (t, lo, hi))
                closed = None if with_closed.has(sp.Integral) else with_closed
            except Exception:  # noqa: BLE001
                closed = None
            fd = FnDef(name, v, closed if closed is not None else sp.Integral(g, (t, lo, hi)), deriv=der,
                       kind="integral", integrand=(g, t, lo, hi), domain=dom)
            fd.notes.append("f' by Leibniz rule: g(upper)*upper' - g(lower)*lower'")
            return fd
        if "volterra" in spec:
            return self._volterra(name, v, spec["volterra"], dom)
        raise CalcError(f"unsupported def for {name}: {spec}")

    def _volterra(self, name, v, sp_, dom) -> FnDef:
        t = sp.Symbol(sp_.get("t", "t"), real=True)
        self.locals.setdefault(t.name, t)
        forcing = self.parse(sp_["forcing"])
        kernel = self.parse(sp_["kernel"]).subs(self.locals[t.name], t)
        u, c = sp.Dummy("u", positive=True), sp.Dummy("c", real=True)
        if sp.simplify(kernel.subs({v: v + c, t: t + c}, simultaneous=True) - kernel) != 0:
            raise CalcError("volterra kernel is not of convolution type k(x-t)")
        k = sp.simplify(kernel.subs({v: u, t: 0}, simultaneous=True))
        s = sp.Symbol("s", positive=True)
        xp = sp.Symbol("xp", positive=True)
        K = sp.laplace_transform(k.subs(u, xp), xp, s, noconds=True)
        G = sp.laplace_transform(forcing.subs(v, xp), xp, s, noconds=True)
        F = sp.simplify(G / (1 - K))
        f = sp.inverse_laplace_transform(F, s, xp).replace(sp.Heaviside, lambda *a: sp.Integer(1))
        f = sp.simplify(f.subs(xp, v))
        if f.has(sp.InverseLaplaceTransform, sp.LaplaceTransform):
            raise CalcError("volterra: Laplace inversion failed")
        # exact back-substitution: forcing + int_0^x k(x-t) f(t) dt - f == 0
        resid = sp.simplify(forcing + sp.integrate(kernel * f.subs(v, t), (t, 0, v)) - f)
        if resid != 0:
            raise CalcError(f"volterra solution does not satisfy the equation (residual {resid})")
        fd = FnDef(name, v, f, kind="volterra", domain=dom)
        fd.notes.append(f"Volterra equation solved by Laplace transform: {name}({v}) = {f}; substituted back "
                        "exactly (2nd-kind Volterra equation with continuous kernel has a unique solution)")
        fd.integrand = (forcing, kernel, t)
        return fd


def _mk_rel(a, op, b):
    return {"<": sp.Lt, "<=": sp.Le, ">": sp.Gt, ">=": sp.Ge, "=": sp.Eq, "!=": sp.Ne}[op](a, b)


# ----------------------------------------------------------------------------------------------- numeric fns
def _mp_fn(env: Env, fd: FnDef) -> Callable:
    """Independent-ish numeric evaluator of a def (mpmath)."""
    if fd.kind == "integral":
        g, t, lo, hi = fd.integrand
        gl = sp.lambdify(t, g, "mpmath")
        lof, hif = sp.lambdify(fd.var, lo, "mpmath"), sp.lambdify(fd.var, hi, "mpmath")
        return lambda xv: mpmath.quad(gl, [lof(xv), hif(xv)])
    return sp.lambdify(fd.var, fd.expr, ["mpmath", {"Max": max, "Min": min}])


def _gl_nodes(n: int = 48) -> list[tuple[float, float]]:
    nodes = []
    for i in range(1, n + 1):
        z = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, z
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * z * p1 - (k - 1) * p0) / k
            dp = n * (z * p1 - p0) / (z * z - 1)
            dz = p1 / dp
            z -= dz
            if abs(dz) < 1e-16:
                break
        nodes.append((z, 2 / ((1 - z * z) * dp * dp)))
    return nodes


_GL = _gl_nodes(48)


def _float_fn(fd: FnDef) -> Callable[[float], float]:
    """Fast float evaluator; nan where undefined.  Integral defs use Gauss-Legendre on the integrand
    (independent of the Leibniz derivative used by the exact analysis)."""
    if fd.kind == "integral":
        g, t, lo, hi = fd.integrand
        gf = _safe_float(sp.lambdify(t, g, ["math", {"Max": max, "Min": min}]))
        lof = _safe_float(sp.lambdify(fd.var, lo, "math"))
        hif = _safe_float(sp.lambdify(fd.var, hi, "math"))

        def f(xv):
            a, b = lof(xv), hif(xv)
            if not (math.isfinite(a) and math.isfinite(b)):
                return math.nan
            m, h = (a + b) / 2, (b - a) / 2
            return h * sum(w * gf(m + h * z) for z, w in _GL)
        return f
    return _safe_float(sp.lambdify(fd.var, fd.expr, ["math", {"Max": max, "Min": min}]))


def _safe_float(fn):
    def f(*a):
        try:
            v = fn(*a)
            if isinstance(v, complex):
                if abs(v.imag) > 1e-12 * max(1.0, abs(v.real)):
                    return math.nan
                v = v.real
            v = float(v)
            return v
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            return math.nan
    return f


# ----------------------------------------------------------------------------------------------- roots / kinks
def _kink_exprs(e, var) -> list:
    """Univariate expressions whose real zeros are special points of e (kinks, domain ends, poles)."""
    out = []
    for a in sp.preorder_traversal(e):
        if isinstance(a, sp.Abs) or isinstance(a, sp.sign):
            out.append(a.args[0])
        elif isinstance(a, (sp.Max, sp.Min)):
            args = a.args
            out += [args[i] - args[j] for i in range(len(args)) for j in range(i + 1, len(args))]
        elif isinstance(a, sp.Piecewise):
            for _, c in a.args:
                for r in (c.atoms(sp.core.relational.Relational) if not isinstance(c, sp.core.relational.Relational)
                          else {c}):
                    out.append(r.lhs - r.rhs)
        elif isinstance(a, sp.Pow):
            if a.exp.is_number and (a.exp.is_negative or not a.exp.is_integer):
                out.append(a.base)
        elif isinstance(a, sp.log):
            out.append(a.args[0])
        elif isinstance(a, (sp.tan, sp.sec)):
            out.append(sp.cos(a.args[0]))
        elif isinstance(a, (sp.cot, sp.csc)):
            out.append(sp.sin(a.args[0]))
        elif isinstance(a, (sp.asin, sp.acos)):
            out += [a.args[0] - 1, a.args[0] + 1]
    return [k for k in out if k.has(var)]


def real_roots(e, var, sample: Optional[dict] = None) -> list:
    """All real zeros of a univariate expression (exact).  CalcError when completeness cannot be ensured."""
    e = sp.sympify(e)
    if not e.has(var):
        return []
    sample = sample or {}
    num = sp.numer(sp.together(e))
    if not num.has(var):
        return []
    others = num.free_symbols - {var}
    if num.is_polynomial(var) and not others:
        P = sp.Poly(num, var)
        if P.domain.is_ZZ or P.domain.is_QQ:
            rr = sorted(set(P.real_roots()), key=lambda r: float(sp.N(r, 30)))
        else:
            rd = sp.roots(P)
            if sum(rd.values()) != P.degree():
                raise CalcError(f"cannot find all roots of {num} exactly")
            rr = sorted([r for r in rd if _real(r) is not None], key=lambda r: _real(r))
        out = []
        try:
            rad = [r for r in sp.solve(num, var) if _real(r) is not None]
        except Exception:  # noqa: BLE001
            rad = []
        for r in rr:
            nice = [q for q in rad if abs(_real(q) - float(sp.N(r, 30))) < 1e-12 and is_zero(q - r)]
            out.append(min(nice, key=sp.count_ops) if nice else r)
        return out
    if others:
        # symbolic parameter (structure phase only): sympy.solve, real at the sample value
        sols = sp.solve(num, var)
        return [r for r in sols if _real(r.subs(sample)) is not None]
    res = sp.solveset(num, var, sp.S.Reals)
    if isinstance(res, sp.FiniteSet):
        out = [r for r in res if _real(r) is not None]
    elif res == sp.S.EmptySet:
        out = []
    else:
        # try plain solve, then insist numerically that nothing is missed in a window (caller cross-checks)
        try:
            sols = sp.solve(num, var)
        except Exception as ex:  # noqa: BLE001
            raise CalcError(f"cannot solve {num} = 0 exactly: {res}") from ex
        out = [r for r in sols if _real(r) is not None]
        if not out and res != sp.S.EmptySet:
            raise CalcError(f"cannot solve {num} = 0 exactly: {res}")
    return sorted(out, key=lambda r: _real(r))


def _dedupe_points(pts: list, sample: Optional[dict] = None) -> list:
    sample = sample or {}
    items = []
    for p in pts:
        v = _real(sp.sympify(p).subs(sample))
        if v is None:
            continue
        items.append((v, p))
    items.sort(key=lambda t: t[0])
    out: list = []
    for v, p in items:
        if out and abs(out[-1][0] - v) <= 1e-12 * max(1.0, abs(v)):
            if sample or is_zero(sp.sympify(out[-1][1]) - p) is not False:
                if sp.count_ops(p) < sp.count_ops(out[-1][1]):
                    out[-1] = (v, p)
                continue
            raise CalcError(f"special points {out[-1][1]} and {p} too close to separate")
        out.append((v, p))
    return [p for _, p in out]


def _sample_between(a, b, sample=None):
    sample = sample or {}
    if a == -sp.oo and b == sp.oo:
        return sp.Integer(0)
    if a == -sp.oo:
        return sp.floor(sp.N(sp.sympify(b).subs(sample), 30)) - 1
    if b == sp.oo:
        return sp.ceiling(sp.N(sp.sympify(a).subs(sample), 30)) + 1
    va, vb = _mpreal(sp.sympify(a).subs(sample)), _mpreal(sp.sympify(b).subs(sample))
    m = (va + vb) / 2
    return sp.Rational(str(mpmath.nstr(m, 35)))


def _resolve(e, var, x0, sample=None):
    """Smooth form of e on a neighbourhood of x0 (Abs/Max/Min/sign/Piecewise resolved by evaluation)."""
    sample = sample or {}
    pt = {var: x0, **sample}

    def val(u):
        c = _N(u.subs(pt), 40)
        if c is None or abs(c.imag) > 1e-25:
            raise CalcError(f"cannot resolve {u} at {x0}")
        return c.real

    def rec(a):
        if a.is_Atom:
            return a
        if isinstance(a, sp.Piecewise):
            for ex, c in a.args:
                cv = c.subs(pt) if c not in (sp.true, sp.false) else c
                if cv in (sp.true, sp.false):
                    if cv == sp.true:
                        return rec(ex)
                    continue
                raise CalcError(f"piecewise condition {c} undecided at {x0}")
            raise CalcError(f"no piecewise branch at {x0}")
        args = [rec(t) for t in a.args]
        if isinstance(a, sp.Abs):
            v = val(args[0])
            if abs(v) < 1e-30:
                if sp.simplify(args[0]) == 0:
                    return sp.Integer(0)
                raise CalcError(f"Abs argument vanishes at sample {x0}")
            return args[0] if v > 0 else -args[0]
        if isinstance(a, sp.sign):
            v = val(args[0])
            return sp.Integer(1 if v > 0 else -1)
        if isinstance(a, (sp.Max, sp.Min)):
            vals = [val(t) for t in args]
            best = max(vals) if isinstance(a, sp.Max) else min(vals)
            hits = [t for t, v in zip(args, vals) if abs(v - best) < 1e-25]
            if len({sp.simplify(h) for h in hits}) > 1:
                raise CalcError(f"{a} switches at sample {x0}")
            return hits[0]
        return a.func(*args)
    return rec(sp.sympify(e))


def zeros_on(e, var, lo, hi, sample=None) -> list:
    """Exact zeros of e (may contain Abs/Max/Piecewise) strictly inside (lo, hi)."""
    sample = sample or {}
    kinks = []
    for k in _kink_exprs(e, var):
        kinks += real_roots(k, var, sample)
    pts = [p for p in _dedupe_points(kinks, sample) if _inside(p, lo, hi, sample)]
    bounds = [lo] + pts + [hi]
    out = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        x0 = _sample_between(a, b, sample)
        try:
            es = _resolve(e, var, x0, sample)
        except CalcError:
            continue
        if _real(es.subs({var: x0, **sample})) is None:
            continue  # undefined on this piece
        if is_zero(sp.simplify(es)) is True:
            raise CalcError(f"{e} vanishes identically on ({a}, {b})")
        out += [r for r in real_roots(es, var, sample) if _inside(r, a, b, sample)]
    # kink points themselves can be zeros
    for p in pts:
        try:
            v = e.subs(var, p).subs(sample)
            if is_zero(v) is True:
                out.append(p)
        except Exception:  # noqa: BLE001
            pass
    return _dedupe_points(out, sample)


def _inside(p, lo, hi, sample=None) -> bool:
    sample = sample or {}
    v = _real(sp.sympify(p).subs(sample))
    if v is None:
        return False
    lo_ok = lo == -sp.oo or v > _real(sp.sympify(lo).subs(sample)) + 1e-14 * max(1, abs(v))
    hi_ok = hi == sp.oo or v < _real(sp.sympify(hi).subs(sample)) - 1e-14 * max(1, abs(v))
    return lo_ok and hi_ok


# ----------------------------------------------------------------------------------------------- function analysis
@dataclass
class Sub:
    lo: Any
    hi: Any
    sign: int
    fs: sp.Expr        # smooth form of f on the piece
    defined: bool = True


@dataclass
class Analysis:
    subs: list            # list[Sub] covering the domain (undefined pieces dropped)
    points: list          # partition points (exact)
    info: dict            # point -> dict(defined, fc, L, R, sL, sR)
    maxima: list
    minima: list


def analyze(env: Env, name: str, lo=-sp.oo, hi=sp.oo) -> Analysis:
    fd = env.defs[name]
    var, f = fd.var, fd.expr
    if fd.domain is not None:
        lo = fd.domain[0] if cmp_exact_safe(fd.domain[0], lo) > 0 else lo
        hi = fd.domain[1] if cmp_exact_safe(fd.domain[1], hi) < 0 else hi
    der = env.deriv(name)
    kinks = []
    for k in _kink_exprs(f if fd.kind != "integral" else der, var) + _kink_exprs(der, var):
        kinks += real_roots(k, var)
    pts = [p for p in _dedupe_points(kinks) if _inside(p, lo, hi)]
    coarse = [lo] + pts + [hi]
    subs: list[Sub] = []
    for a, b in zip(coarse[:-1], coarse[1:]):
        x0 = _sample_between(a, b)
        f0 = _float_fn(fd)(float(x0))
        if not math.isfinite(f0):
            continue
        fs = _resolve(f, var, x0) if fd.kind != "integral" else f
        ds = sp.diff(fs, var) if fd.kind != "integral" else _resolve(der, var, x0)
        ds = sp.simplify(ds)
        if ds == 0:
            raise CalcError(f"{name} is constant on ({a}, {b}): extrema/monotonicity ill-posed")
        zs = [r for r in real_roots(ds, var) if _inside(r, a, b)]
        bounds = [a] + zs + [b]
        for c, d in zip(bounds[:-1], bounds[1:]):
            xm = _sample_between(c, d)
            v = _real(ds.subs(var, xm))
            if v is None or abs(v) < 1e-30:
                raise CalcError(f"sign of {name}' undecided at {xm}")
            subs.append(Sub(c, d, 1 if v > 0 else -1, fs))
    points = _dedupe_points([s.lo for s in subs if s.lo != -sp.oo] + [s.hi for s in subs if s.hi != sp.oo])
    info = {}
    maxima, minima = [], []
    for c in points:
        left = next((s for s in subs if s.hi == c or (s.hi != sp.oo and is_zero(s.hi - c) is True)), None)
        right = next((s for s in subs if s.lo == c or (s.lo != -sp.oo and is_zero(s.lo - c) is True)), None)
        fc = _value_at(fd, c)
        d = {"defined": fc is not None, "fc": fc, "left": left, "right": right}
        if fc is not None and left is not None and right is not None:
            if fd.kind == "integral":
                L = R = fc
            else:
                L = _side_limit(left.fs, var, c, "-")
                R = _side_limit(right.fs, var, c, "+")
            d.update(L=L, R=R)
            sl, sr = left.sign, right.sign
            cl, cr = _cmp_lim(fc, L), _cmp_lim(fc, R)
            lmax = (sl > 0 and cl >= 0) or (sl < 0 and cl > 0)
            rmax = (sr < 0 and cr >= 0) or (sr > 0 and cr > 0)
            lmin = (sl < 0 and cl <= 0) or (sl > 0 and cl < 0)
            rmin = (sr > 0 and cr <= 0) or (sr < 0 and cr < 0)
            if lmax and rmax:
                maxima.append(c)
            if lmin and rmin:
                minima.append(c)
        info[c] = d
    return Analysis(subs, points, info, maxima, minima)


def cmp_exact_safe(a, b) -> int:
    if a == b:
        return 0
    if a in (sp.oo, -sp.oo) or b in (sp.oo, -sp.oo):
        av = math.inf if a == sp.oo else (-math.inf if a == -sp.oo else _real(a))
        bv = math.inf if b == sp.oo else (-math.inf if b == -sp.oo else _real(b))
        return (av > bv) - (av < bv)
    return cmp_exact(a, b)


def _cmp_lim(fc, L) -> int:
    if L in (sp.oo, -sp.oo):
        return -1 if L == sp.oo else 1
    return cmp_exact(fc, L)


def _value_at(fd: FnDef, c):
    if fd.kind == "integral":
        g, t, lo, hi = fd.integrand
        try:
            v = sp.integrate(g, (t, lo.subs(fd.var, c), hi.subs(fd.var, c)))
        except Exception:  # noqa: BLE001
            return None
        return None if v.has(sp.Integral) or _real(v) is None else sp.simplify(v)
    if fd.domain is not None and (cmp_exact(c, fd.domain[0]) < 0 or cmp_exact(c, fd.domain[1]) > 0):
        return None
    try:
        v = fd.expr.subs(fd.var, c)
    except Exception:  # noqa: BLE001
        return None
    if v.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.Piecewise) or _real(v) is None:
        return None
    return v


def _side_limit(fs, var, c, d):
    v = fs.subs(var, c)
    if not v.has(sp.zoo, sp.nan, sp.oo, -sp.oo) and _real(v) is not None:
        return v
    v = sp.limit(fs, var, c, d)
    if v in (sp.oo, -sp.oo):
        return v
    if _real(v) is None:
        raise CalcError(f"one-sided limit at {c} undetermined")
    return v


def components(an: Analysis, mode: int, fd: FnDef) -> list[tuple]:
    """Maximal open intervals where f is strictly increasing (mode=+1) / decreasing (-1)."""
    comps: list[list] = []
    for s in an.subs:
        if s.sign != mode:
            continue
        if comps and (comps[-1][1] == s.lo or (s.lo != -sp.oo and comps[-1][1] != sp.oo
                                               and is_zero(comps[-1][1] - s.lo) is True)):
            c = s.lo
            inf = an.info.get(c) or next((v for k, v in an.info.items() if is_zero(k - c) is True), None)
            if inf and inf["defined"] and "L" in inf:
                L, R, fc = inf["L"], inf["R"], inf["fc"]
                ok = (_cmp_lim(fc, L) * mode >= 0) and (_cmp_lim(fc, R) * mode <= 0) if fd.kind != "integral" \
                    else True
                if ok:
                    comps[-1][1] = s.hi
                    continue
        comps.append([s.lo, s.hi])
    return [tuple(c) for c in comps]


# numeric cross-checks for the analysis ------------------------------------------------------------------------
def _window(points, lo, hi) -> tuple[float, float]:
    vals = [_real(p) for p in points if p not in (sp.oo, -sp.oo)]
    vals = [v for v in vals if v is not None]
    if lo not in (-sp.oo, sp.oo):
        vals.append(_real(lo))
    if hi not in (-sp.oo, sp.oo):
        vals.append(_real(hi))
    if not vals:
        vals = [0.0]
    a, b = min(vals), max(vals)
    m = max(1.0, 0.25 * (b - a))
    wa = _real(lo) if lo != -sp.oo else a - m
    wb = _real(hi) if hi != sp.oo else b + m
    return wa, wb


def _grid(wa, wb, n, extra=()):
    h = (wb - wa) / n
    ex = [e for e in extra if e is not None and wa <= e <= wb]
    pts = [p for p in (wa + h * i for i in range(n + 1)) if all(abs(p - e) > 0.01 * h for e in ex)]
    pts += ex
    return sorted(set(pts))


def numeric_extrema(fd: FnDef, an: Analysis, lo, hi, n: int = 3000) -> tuple[list, list]:
    f = _float_fn(fd)
    wa, wb = _window(an.points, lo, hi)
    xs = _grid(wa, wb, n, [_real(p) for p in an.points])
    ys = [f(x) for x in xs]
    finite = [abs(y) for y in ys if math.isfinite(y)]
    tol = 1e-11 * (max(finite) if finite else 1.0)
    mx, mn = [], []
    for i in range(1, len(xs) - 1):
        a, b, c = ys[i - 1], ys[i], ys[i + 1]
        if not all(map(math.isfinite, (a, b, c))):
            continue
        if b > a + tol and b > c + tol:
            mx.append(xs[i])
        elif b < a - tol and b < c - tol:
            mn.append(xs[i])
    return mx, mn


def _match_points(exact: list, numeric: list, h: float) -> bool:
    ev = sorted(_real(p) for p in exact)
    if len(ev) != len(numeric):
        return False
    return all(abs(a - b) <= 3 * h for a, b in zip(ev, sorted(numeric)))


# ----------------------------------------------------------------------------------------------- area engine
def _pred_tree(item, env: Env):
    if isinstance(item, str):
        atoms = []
        for a, op, b in _split_rel(item):
            if op in ("=", "!="):
                raise CalcError(f"equality '{item}' does not define an area")
            atoms.append(("atom", env.parse(a) - env.parse(b), op))
        return ("and", atoms)
    if isinstance(item, list):
        return ("and", [_pred_tree(i, env) for i in item])
    if isinstance(item, dict):
        if "any" in item:
            return ("or", [_pred_tree(i, env) for i in item["any"]])
        if "all" in item:
            return ("and", [_pred_tree(i, env) for i in item["all"]])
        if "not" in item:
            return ("not", _pred_tree(item["not"], env))
    raise CalcError(f"bad region item {item!r}")


def _atoms(tree) -> list:
    if tree[0] == "atom":
        return [tree]
    if tree[0] == "not":
        return _atoms(tree[1])
    return [a for t in tree[1] for a in _atoms(t)]


def _eval_tree(tree, atomval) -> bool:
    k = tree[0]
    if k == "atom":
        return atomval(tree)
    if k == "not":
        return not _eval_tree(tree[1], atomval)
    vals = [_eval_tree(t, atomval) for t in tree[1]]
    return all(vals) if k == "and" else any(vals)


def _cmp_op(v, op) -> bool:
    return {"<": v < 0, "<=": v <= 0, ">": v > 0, ">=": v >= 0}[op]


def _exact_pred(tree, x0, y0, sample) -> bool:
    pt = {X: x0, Y: y0, **sample}

    def atom(a):
        c = _N(a[1].subs(pt), 40)
        if c is None or abs(c.imag) > 1e-25:
            return False
        if abs(c.real) < 1e-28:
            raise CalcError(f"sample point ({x0}, {y0}) lies on a boundary")
        return _cmp_op(c.real, a[2])
    return _eval_tree(tree, atom)


def _float_pred(tree, sample):
    fns = {}
    for a in _atoms(tree):
        fns[id(a)] = _safe_float(sp.lambdify((X, Y), a[1].subs(sample), ["math", {"Max": max, "Min": min}]))

    def P(xv, yv):
        def atom(a):
            v = fns[id(a)](xv, yv)
            return math.isfinite(v) and _cmp_op(v, a[2])
        return _eval_tree(tree, atom)
    return P


def _variants(e, cap: int = 256) -> list:
    """All smooth case-expressions of e: Abs(u) -> +/-u, Max/Min -> each argument."""
    nodes = [a for a in sp.preorder_traversal(e) if isinstance(a, (sp.Abs, sp.Max, sp.Min))]
    if not nodes:
        return [e]
    node = nodes[0]
    choices = [node.args[0], -node.args[0]] if isinstance(node, sp.Abs) else list(node.args)
    out = []
    for ch in choices:
        out += _variants(e.xreplace({node: ch}), cap)
        if len(out) > cap:
            raise CalcError("too many boundary cases")
    return out


@dataclass
class Run:
    k: int            # strip index
    a: Any            # strip ends
    b: Any
    lo: Optional[sp.Expr]   # None = -oo
    hi: Optional[sp.Expr]   # None = +oo


def _area_structure(tree, sample: dict, steps: list):
    """Cylindrical decomposition of the region; returns (strips, runs)."""
    curves, xcrit = [], []
    for at in _atoms(tree):
        g = at[1]
        for h in _variants(g):
            parts = [h] + [k for k in _kink_exprs(h, Y)]
            for hh in parts:
                if hh.has(Y):
                    try:
                        sols = sp.solve(hh.subs(Y, _YP), _YP)
                    except Exception as ex:  # noqa: BLE001
                        raise CalcError(f"cannot solve boundary {hh} = 0 for y") from ex
                    for s in sols:
                        s = sp.sympify(s)
                        if s.has(_YP) or s.has(Y):
                            raise CalcError(f"boundary {hh} not explicit in y")
                        curves.append(s)
                else:
                    xcrit += real_roots(hh, X, sample)
    # dedupe curves
    uniq: list = []
    for c in curves:
        if any(sp.simplify(c - u) == 0 for u in uniq):
            continue
        uniq.append(c)
    curves = uniq
    for c in curves:
        for k in _kink_exprs(c, X):
            xcrit += real_roots(k, X, sample)
    for i in range(len(curves)):
        for j in range(i + 1, len(curves)):
            d = curves[i] - curves[j]
            for r in real_roots(d, X, sample):
                vi, vj = _real(curves[i].subs(X, r).subs(sample)), _real(curves[j].subs(X, r).subs(sample))
                if vi is not None and vj is not None and abs(vi - vj) < 1e-15 * max(1, abs(vi)):
                    xcrit.append(r)
    pts = _dedupe_points(xcrit, sample)
    steps.append(f"boundary curves y = {curves}; special x = {pts}")
    bounds = [-sp.oo] + pts + [sp.oo]
    strips = []
    runs: list[Run] = []
    for k, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        x0 = _sample_between(a, b, sample)
        vals = []
        for c in curves:
            v = _mpreal(c.subs(X, x0).subs(sample), 40)
            if v is not None:
                vals.append((v, c))
        vals.sort(key=lambda t: t[0])
        ordered: list = []
        for v, c in vals:
            if ordered and abs(ordered[-1][0] - v) < mpmath.mpf(10) ** -28 * max(1, abs(v)):
                if is_zero(sp.simplify((c - ordered[-1][1]).subs(sample))) is not True:
                    raise CalcError(f"curves {c} and {ordered[-1][1]} meet at non-special x={x0}")
                continue
            ordered.append((v, c))
        strips.append((a, b, [c for _, c in ordered]))
        cells = []
        n = len(ordered)
        for i in range(n + 1):
            if n == 0:
                y0 = sp.Integer(0)
            elif i == 0:
                y0 = sp.floor(sp.Float(ordered[0][0], 30)) - 1
            elif i == n:
                y0 = sp.ceiling(sp.Float(ordered[-1][0], 30)) + 1
            else:
                y0 = sp.Rational(mpmath.nstr((ordered[i - 1][0] + ordered[i][0]) / 2, 35))
            cells.append(_exact_pred(tree, x0, y0, sample))
        i = 0
        while i <= n:
            if not cells[i]:
                i += 1
                continue
            j = i
            while j + 1 <= n and cells[j + 1]:
                j += 1
            runs.append(Run(k, a, b, None if i == 0 else ordered[i - 1][1], None if j == n else ordered[j][1]))
            i = j + 1
    return strips, runs


def _run_unbounded(r: Run) -> bool:
    return r.a == -sp.oo or r.b == sp.oo or r.lo is None or r.hi is None


def _components(runs: list[Run], sample) -> list[list[Run]]:
    parent = list(range(len(runs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def at(c, curve, x, side):
        if curve is None:
            return -math.inf if side == "lo" else math.inf
        v = _real(curve.subs(X, x).subs(sample))
        if v is None:
            v = _real(sp.limit(curve.subs(sample), X, x))
        return v if v is not None else (-math.inf if side == "lo" else math.inf)

    for i, r in enumerate(runs):
        for j, s in enumerate(runs):
            if s.k != r.k + 1:
                continue
            c = r.b
            lo1, hi1 = at(None, r.lo, c, "lo"), at(None, r.hi, c, "hi")
            lo2, hi2 = at(None, s.lo, c, "lo"), at(None, s.hi, c, "hi")
            if min(hi1, hi2) - max(lo1, lo2) > 1e-12:
                parent[find(i)] = find(j)
    groups: dict[int, list] = {}
    for i, r in enumerate(runs):
        groups.setdefault(find(i), []).append(r)
    return list(groups.values())


def _integrate_runs(runs: list[Run], sample: dict):
    total = sp.Integer(0)
    for r in runs:
        integrand = r.hi - r.lo
        v = sp.integrate(integrand, (X, r.a, r.b))
        if v.has(sp.Integral) or (not v.free_symbols and _real(v.subs(sample)) is None):
            raise CalcError(f"could not integrate {integrand} on [{r.a}, {r.b}] exactly")
        total += v
    return total


def _tanh_sinh(a: float, b: float, h: float = 1 / 8):
    out = []
    k = 0
    while True:
        t = k * h
        u = math.pi / 2 * math.sinh(t)
        th = math.tanh(u)
        w = h * (math.pi / 2) * math.cosh(t) / math.cosh(u) ** 2
        if w < 1e-18 or 1 - th < 1e-16:
            break
        for s in ((1,) if k == 0 else (1, -1)):
            out.append(((a + b) / 2 + (b - a) / 2 * th * s, (b - a) / 2 * w))
        k += 1
    return out


def _numeric_area(tree, runs: list[Run], strips, sample, bounded_only: bool) -> tuple[float, str]:
    P = _float_pred(tree, sample)
    fsub = {s: float(sp.N(v, 30)) for s, v in sample.items()}
    curves_f = {}

    def cf(c):
        if id(c) not in curves_f:
            curves_f[id(c)] = _safe_float(sp.lambdify(X, c.subs(sample), "math"))
        return curves_f[id(c)]

    xa = min(_real(r.a.subs(sample)) for r in runs)
    xb = max(_real(r.b.subs(sample)) for r in runs)
    ylo, yhi = math.inf, -math.inf
    for r in runs:
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = _real(r.a.subs(sample)) * (1 - t) + _real(r.b.subs(sample)) * t
            for c in (r.lo, r.hi):
                v = cf(c)(x)
                if math.isfinite(v):
                    ylo, yhi = min(ylo, v), max(yhi, v)
    pad = 0.5 * (yhi - ylo) + 1.0
    Ylo, Yhi = ylo - pad, yhi + pad
    all_curves = {id(c): c for _, _, cs in strips for c in cs}

    def slice_len(x, band=None):
        lo_, hi_ = band if band else (Ylo, Yhi)
        if not hi_ > lo_:
            return 0.0
        ys = [lo_ + (hi_ - lo_) * i / 400 for i in range(401)]
        for c in all_curves.values():
            v = cf(c)(x)
            if math.isfinite(v) and lo_ < v < hi_:
                e = 1e-9 * max(1.0, abs(v))
                ys += [v - e, v + e]
        ys = sorted(set(ys))
        vals = [P(x, y) for y in ys]
        total, start = 0.0, (lo_ if vals[0] else None)
        for i in range(1, len(ys)):
            if vals[i] != vals[i - 1]:
                a, b = ys[i - 1], ys[i]
                for _ in range(60):
                    m = (a + b) / 2
                    if P(x, m) == vals[i - 1]:
                        a = m
                    else:
                        b = m
                edge = (a + b) / 2
                if vals[i]:
                    start = edge
                else:
                    total += edge - start
                    start = None
        if start is not None:
            total += hi_ - start
        return total

    # strips restricted to the counted runs' x-range
    exact_total, num_total, worst = 0.0, 0.0, 0.0
    by_strip: dict[int, list[Run]] = {}
    for r in runs:
        by_strip.setdefault(r.k, []).append(r)
    for k, rs in by_strip.items():
        a, b = _real(rs[0].a.subs(sample)), _real(rs[0].b.subs(sample))
        for x, w in _tanh_sinh(a, b):
            ex = sum(cf(r.hi)(x) - cf(r.lo)(x) for r in rs)
            if bounded_only:
                nm = sum(slice_len(x, (cf(r.lo)(x), cf(r.hi)(x))) for r in rs)
            else:
                nm = slice_len(x)
            if not math.isfinite(ex):
                continue
            worst = max(worst, abs(ex - nm))
            exact_total += w * ex
            num_total += w * nm
    if not bounded_only:
        # region must be empty outside the counted strips (sample the uncounted strips and the far field)
        span = xb - xa
        probes = [xa - span * t for t in (0.01, 0.1, 0.5, 1, 3)] + [xb + span * t for t in (0.01, 0.1, 0.5, 1, 3)]
        for (a, b, _) in strips:
            if any(r.a == a and r.b == b for r in runs):
                continue
            av = _real(a.subs(sample)) if a != -sp.oo else None
            bv = _real(b.subs(sample)) if b != sp.oo else None
            if av is not None and bv is not None:
                probes += [av + (bv - av) * t for t in (0.13, 0.5, 0.87)]
        for x in probes:
            if slice_len(x) > 1e-9:
                raise CalcError(f"numeric slice at x={x:.6g} finds region points outside the exact cells")
    return num_total, f"pointwise slice mismatch <= {worst:.2e}; exact-slice quadrature {exact_total:.12g}"


def area_value(env: Env, spec: dict, steps: list, sample: Optional[dict] = None,
               numeric: bool = True) -> tuple[sp.Expr, Optional[float]]:
    sample = sample or {}
    base = _pred_tree(spec["region"], env)
    trees = [("main", base)]
    if spec.get("split"):
        sp_tree = _pred_tree(spec["split"], env)
        trees = [("in", ("and", [base, sp_tree])), ("out", ("and", [base, ("not", sp_tree)]))]
    results = []
    for label, tree in trees:
        strips, runs = _area_structure(tree, sample, steps)
        if not runs:
            raise CalcError(f"region ({label}) is empty")
        if spec.get("bounded_part"):
            comps = _components(runs, sample)
            keep = [r for c in comps if not any(_run_unbounded(r) for r in c) for r in c]
            if not keep:
                raise CalcError("no bounded component")
            if len(keep) < len(runs):
                steps.append(f"bounded part: {len(comps)} components, unbounded ones discarded")
            runs = keep
        elif any(_run_unbounded(r) for r in runs):
            raise CalcError(f"region ({label}) is unbounded")
        A = _integrate_runs(runs, sample)
        A = sp.simplify(A)
        steps.append(f"area[{label}] = sum of {len(runs)} exact strip integrals = {A}")
        nv = None
        if numeric:
            nv, msg = _numeric_area(tree, runs, strips, sample, bool(spec.get("bounded_part")))
            ev = _real(A.subs(sample))
            if ev is None or abs(nv - ev) > _RTOL * max(1.0, abs(ev)):
                raise CalcError(f"numeric slice integration {nv!r} disagrees with exact area {A} = {ev!r}")
            steps.append(f"numeric check [{label}]: independent slice-length quadrature {nv:.12g} ({msg})")
        results.append((A, nv))
    if len(results) == 1:
        return results[0]
    (A1, n1), (A2, n2) = results
    c = cmp_exact(A1.subs(sample), A2.subs(sample)) if not A1.free_symbols else \
        (1 if _real(A1.subs(sample)) > _real(A2.subs(sample)) else -1)
    if c == 0:
        raise CalcError("both portions have equal area: 'larger/smaller' ambiguous")
    want = spec.get("portion", "larger")
    pick = (A1, n1) if (c > 0) == (want == "larger") else (A2, n2)
    steps.append(f"portions: {A1} and {A2}; {want} = {pick[0]}")
    return pick


# ----------------------------------------------------------------------------------------------- ops
@dataclass
class QV:
    exact: Any
    numeric: Any


def _interval(env: Env, op: dict):
    iv = op.get("interval")
    if not iv:
        return -sp.oo, sp.oo
    st = getattr(env, "store", {})
    return _qsubs(env, env.parse(str(iv[0])), st), _qsubs(env, env.parse(str(iv[1])), st)


def run_op(env: Env, op: dict, steps: list) -> QV:
    kind = op["op"]
    if kind == "area":
        A, nv = area_value(env, op, steps, numeric=True)
        return QV(A, nv)
    if kind == "expr":
        e = env.parse(op["expr"])
        return QV(e, _num_expr(env, op["expr"]))
    if kind in ("extrema", "monotone", "critical_points"):
        fd = env.defs[op["fn"]]
        lo, hi = _interval(env, op)
        an = analyze(env, op["fn"], lo, hi)
        if kind == "extrema":
            return _op_extrema(env, fd, an, op, lo, hi, steps)
        if kind == "monotone":
            return _op_monotone(fd, an, op, lo, hi, steps)
        return _op_critical(env, fd, an, op, lo, hi, steps)
    if kind in ("abs_max", "abs_min"):
        return _op_absext(env, op, steps)
    if kind == "roots":
        e = env.parse(op["expr"]) if "expr" in op else env.defs[op["fn"]].expr
        var = env.var
        lo, hi = _interval(env, op)
        rs = zeros_on(e, var, lo, hi)
        f = _safe_float(sp.lambdify(var, e, ["math", {"Max": max, "Min": min}]))
        wa, wb = _window(rs, lo, hi)
        xs = _grid(wa, wb, 4000)
        sc = [0.5 * (xs[i] + xs[i + 1]) for i in range(len(xs) - 1)
              if math.isfinite(f(xs[i])) and math.isfinite(f(xs[i + 1])) and f(xs[i]) * f(xs[i + 1]) < 0]
        for r in rs:
            if abs(f(_real(r))) > 1e-9:
                raise CalcError(f"root {r} does not vanish numerically")
        for s in sc:
            if not any(abs(s - _real(r)) <= (wb - wa) / 4000 * 2 for r in rs):
                raise CalcError(f"numeric sign change near {s} has no exact root")
        steps.append(f"roots of {e} in ({lo}, {hi}): {rs}")
        return QV(rs, [_real(r) for r in rs])
    if kind == "root_count_set":
        return _op_rootset(env, op, steps)
    raise CalcError(f"unknown op {kind}")


def _op_extrema(env, fd, an, op, lo, hi, steps) -> QV:
    which = op.get("kind", "max")
    pts = {"max": an.maxima, "min": an.minima, "any": sorted(an.maxima + an.minima, key=_real)}[which]
    nmx, nmn = numeric_extrema(fd, an, lo, hi)
    wa, wb = _window(an.points, lo, hi)
    h = (wb - wa) / 3000
    if not (_match_points(an.maxima, nmx, h) and _match_points(an.minima, nmn, h)):
        raise CalcError(f"numeric sampling extrema (max {nmx}, min {nmn}) disagree with exact "
                        f"(max {an.maxima}, min {an.minima})")
    steps.append(f"{op['fn']}: local maxima at {an.maxima}, local minima at {an.minima} "
                 f"(sign of {op['fn']}' and one-sided limits); dense sampling agrees")
    ret = op.get("return", "points")
    f = _float_fn(fd)
    if ret == "points":
        return QV(list(pts), [_real(p) for p in pts])
    if ret == "count":
        nnum = {"max": len(nmx), "min": len(nmn), "any": len(nmx) + len(nmn)}[which]
        return QV(sp.Integer(len(pts)), nnum)
    vals = [an.info[p]["fc"] for p in pts]
    if any(v is None for v in vals):
        raise CalcError("extremum value not available in closed form")
    nvals = [f(_real(p)) for p in pts]
    if ret == "values":
        return QV(vals, nvals)
    if ret == "sum":
        return QV(sp.simplify(sum(vals)), sum(nvals))
    raise CalcError(f"bad return {ret}")


def _op_monotone(fd, an, op, lo, hi, steps) -> QV:
    mode = 1 if op.get("mode", "increasing").startswith("inc") else -1
    comps = components(an, mode, fd)
    f = _float_fn(fd)
    wa, wb = _window(an.points, lo, hi)
    # numeric: every grid cell inside a component moves in `mode`; every cell outside (defined) does not
    n = 4000
    xs = _grid(wa, wb, n)
    ys = [f(x) for x in xs]
    h = (wb - wa) / n

    def inside(a, b):
        for c, d in comps:
            cv = -math.inf if c == -sp.oo else _real(c)
            dv = math.inf if d == sp.oo else _real(d)
            if a >= cv - 1e-15 and b <= dv + 1e-15:
                return True
        return False

    def near_end(a, b):
        ends = [_real(c) for cd in comps for c in cd if c not in (sp.oo, -sp.oo)] + \
               [_real(p) for p in an.points]
        return any(a - 2 * h <= e <= b + 2 * h for e in ends)
    for i in range(n):
        a, b = xs[i], xs[i + 1]
        ya, yb = ys[i], ys[i + 1]
        if not (math.isfinite(ya) and math.isfinite(yb)) or near_end(a, b):
            continue
        moves = (yb - ya) * mode > 0
        if inside(a, b) != moves and abs(yb - ya) > 1e-12 * max(1.0, abs(ya)):
            raise CalcError(f"numeric monotonicity on [{a:.6g}, {b:.6g}] contradicts exact intervals {comps}")
    steps.append(f"{op['fn']} strictly {'increasing' if mode > 0 else 'decreasing'} on {comps}")
    if op.get("return", "endpoints") == "intervals":
        return QV(comps, comps)
    ends = _dedupe_points([c for cd in comps for c in cd if c not in (sp.oo, -sp.oo)])
    return QV(ends, [_real(e) for e in ends])


def _op_critical(env, fd, an, op, lo, hi, steps) -> QV:
    der = env.deriv(op["fn"])
    out = []
    for c in an.points:
        if not an.info[c]["defined"] or an.info[c]["left"] is None or an.info[c]["right"] is None:
            continue
        L, R = an.info[c]["left"], an.info[c]["right"]
        dl = _side_limit(sp.diff(L.fs, fd.var), fd.var, c, "-")
        dr = _side_limit(sp.diff(R.fs, fd.var), fd.var, c, "+")
        if dl in (sp.oo, -sp.oo) or dr in (sp.oo, -sp.oo) or cmp_exact(dl, dr) != 0 or is_zero(dl) is True:
            out.append(c)
    fm = _mp_fn(env, fd)
    for c in out:
        try:
            with mpmath.workdps(30):
                dl = mpmath.diff(fm, _mpreal(c), direction=-1)
                dr = mpmath.diff(fm, _mpreal(c), direction=1)
        except Exception:  # noqa: BLE001
            continue
        if abs(dl) > 1e-8 and abs(dr) > 1e-8 and abs(dl - dr) < 1e-8:
            raise CalcError(f"numeric derivative at {c} is nonzero and smooth: not critical")
    steps.append(f"critical points of {op['fn']}: {out} (f'=0 or f' undefined)")
    _ = der
    return QV(out, [_real(c) for c in out])


def _op_absext(env, op, steps) -> QV:
    fd = env.defs[op["fn"]]
    lo, hi = _interval(env, op)
    closed = op.get("closed", [True, True])
    an = analyze(env, op["fn"], lo, hi)
    att, sup = [], []
    ends = [e for e in (lo, hi) if e not in (sp.oo, -sp.oo)]
    for c in an.points:
        inf = an.info[c]
        if any(is_zero(sp.sympify(c) - e) is True for e in ends):
            continue  # interval ends handled below (attained only when closed)
        if inf["defined"]:
            att.append((c, inf["fc"]))
        if inf.get("left") is not None:
            sup.append(_side_limit(inf["left"].fs, fd.var, c, "-"))
        if inf.get("right") is not None:
            sup.append(_side_limit(inf["right"].fs, fd.var, c, "+"))
    for end, cl, d in ((lo, closed[0], "+"), (hi, closed[1], "-")):
        if end in (sp.oo, -sp.oo):
            s = next((s for s in an.subs if (s.lo == end or s.hi == end)), None)
            if s is not None:
                sup.append(sp.limit(s.fs, fd.var, end))
        else:
            s_in = next((s for s in an.subs if (d == "+" and s.lo == end) or (d == "-" and s.hi == end)), None)
            if s_in is not None:
                sup.append(_side_limit(s_in.fs, fd.var, end, d))
            v = _value_at(fd, end) if cl else None
            if v is not None:
                att.append((end, v))
    if not att:
        raise CalcError("no attained values")
    best = att[0]
    sgn = 1 if op["op"] == "abs_max" else -1
    for c, v in att[1:]:
        if cmp_exact(v, best[1]) * sgn > 0:
            best = (c, v)
    for s in sup:
        if s in (sp.oo, -sp.oo):
            if (s == sp.oo) == (sgn > 0):
                raise CalcError(f"{op['op']} not attained (unbounded)")
            continue
        if cmp_exact(s, best[1]) * sgn > 0:
            raise CalcError(f"{op['op']} not attained: limit {s} beyond attained {best[1]}")
    # numeric: dense grid never beats the exact extremum; f(argext) agrees
    f = _float_fn(fd)
    wa, wb = _window(an.points, lo, hi)
    xs = _grid(wa, wb, 6000)
    ev = _real(best[1])
    for x in xs:
        y = f(x)
        if math.isfinite(y) and (y - ev) * sgn > 1e-9 * max(1.0, abs(ev)):
            raise CalcError(f"numeric sample f({x:.6g})={y:.10g} beats exact {op['op']} {ev:.10g}")
    fv = f(_real(best[0]))
    if not math.isfinite(fv) or abs(fv - ev) > 1e-9 * max(1.0, abs(ev)):
        raise CalcError("numeric value at the extremum point disagrees")
    steps.append(f"{op['op']} of {op['fn']} on [{lo}, {hi}] = {best[1]} at x = {best[0]}")
    if op.get("return", "value") == "point":
        return QV(best[0], _real(best[0]))
    return QV(sp.simplify(best[1]), fv)


def _op_rootset(env, op, steps) -> QV:
    var = env.var
    a = env.locals.get(op["param"]) or env.params.get(op["param"])
    P = sp.Poly(env.parse(op["poly"]), var)
    k = int(op["count"])
    disc = sp.discriminant(P.as_expr(), var)
    lc = P.LC()
    crit = []
    for e in (disc, lc):
        crit += real_roots(e, a)
    crit = _dedupe_points(crit)

    def count(av):
        p = sp.Poly(P.as_expr().subs(a, av), var)
        if p.degree() <= 0:
            return None
        return len(set(p.real_roots()))
    bounds = [-sp.oo] + crit + [sp.oo]
    pieces = []
    for lo_, hi_ in zip(bounds[:-1], bounds[1:]):
        if count(_sample_between(lo_, hi_)) == k:
            pieces.append(sp.Interval.open(lo_, hi_))
    for c in crit:
        if count(c) == k:
            pieces.append(sp.FiniteSet(c))
    S = sp.Union(*pieces) if pieces else sp.S.EmptySet
    # numeric: random-ish probes, root count by sign changes on a dense grid
    import random
    rng = random.Random(7)
    for _ in range(12):
        lo_f = (_real(crit[0]) if crit else 0) - 5
        hi_f = (_real(crit[-1]) if crit else 0) + 5
        av = sp.Rational(rng.randint(int(lo_f * 1000), int(hi_f * 1000)), 1000)
        inS = S.contains(av) == sp.true
        roots = [complex(r) for r in sp.Poly(P.as_expr().subs(a, av), var).nroots()]
        nreal = len({round(r.real, 8) for r in roots if abs(r.imag) < 1e-9})
        if (nreal == k) != inS:
            raise CalcError(f"numeric root count at {op['param']}={av} disagrees with exact set {S}")
    steps.append(f"{{{op['param']} : {op['poly']} = 0 has exactly {k} distinct real roots}} = {S}")
    if op.get("return", "endpoints") == "set":
        return QV(S, None)
    if not isinstance(S, (sp.Interval, sp.Union)):
        raise CalcError(f"set {S} is not a union of intervals")
    ends = _dedupe_points([e for e in S.boundary if e not in (sp.oo, -sp.oo)])
    return QV(ends, [_real(e) for e in ends])


# ----------------------------------------------------------------------------------------------- numeric exprs
def _num_env(env: Env) -> dict:
    mods = {}
    for name, fd in env.defs.items():
        fm = _mp_fn(env, fd)
        mods[name] = fm
        mods["d" + name] = (lambda g: (lambda t: mpmath.diff(g, t)))(fm)
        mods["d2" + name] = (lambda g: (lambda t: mpmath.diff(g, t, 2)))(fm)
    mods.update({"Max": max, "Min": min})
    return mods


def _num_expr(env: Env, s: str, qnum: Optional[dict] = None):
    e = parse(s.replace("**", "^"), env.symbols())
    if env.subs:
        e = e.subs(env.subs)
    qnum = qnum or {}
    e = e.subs({env.qsyms[k]: sp.Symbol(f"_q_{k}") for k in qnum if k in env.qsyms})
    syms = sorted(e.free_symbols, key=str)
    vals = []
    for s_ in syms:
        k = s_.name[3:] if s_.name.startswith("_q_") else None
        if k is None or k not in qnum:
            raise CalcError(f"numeric evaluation: free symbol {s_}")
        vals.append(mpmath.mpf(qnum[k]) if not isinstance(qnum[k], (list, tuple)) else None)
    fn = sp.lambdify(syms, e, ["mpmath", _num_env(env)])
    with mpmath.workdps(30):
        v = fn(*vals)
    return v


# ----------------------------------------------------------------------------------------------- interpreter
def _bind(env: Env, names, qv: QV, store: dict, nstore: dict):
    if isinstance(names, str):
        names = [names] if isinstance(qv.exact, list) and len(qv.exact) == 1 and False else names
    if isinstance(names, list):
        ex = qv.exact if isinstance(qv.exact, list) else [qv.exact]
        nu = qv.numeric if isinstance(qv.numeric, list) else [qv.numeric]
        if len(ex) != len(names):
            raise CalcError(f"expected {len(names)} values for {names}, got {len(ex)}: {ex}")
        for n_, e_, v_ in zip(names, ex, nu):
            env.qsyms[n_] = sp.Symbol(n_)
            store[n_], nstore[n_] = e_, v_
    else:
        env.qsyms[names] = sp.Symbol(names)
        store[names], nstore[names] = qv.exact, qv.numeric


def _qsubs(env: Env, e, store: dict):
    return e.subs({env.qsyms[k]: v for k, v in store.items() if k in env.qsyms and not isinstance(v, list)})


def _check(env: Env, chk, store: dict, nstore: dict, steps: list) -> bool:
    if isinstance(chk, str):
        for a, op, b in _split_rel(chk):
            av = _qsubs(env, env.parse(a), store)
            bv = _qsubs(env, env.parse(b), store)
            if not _rel_true(av, op, bv):
                steps.append(f"check {chk!r} is FALSE")
                return False
        steps.append(f"check {chk!r} holds")
        return True
    qv = run_op(env, chk, steps)
    got = qv.exact if isinstance(qv.exact, list) else [qv.exact]
    if "equals" in chk:
        want = chk["equals"] if isinstance(chk["equals"], list) else [chk["equals"]]
        wv = [_qsubs(env, env.parse(str(w)), store) for w in want]
        ok = len(wv) == len(got) and all(cmp_exact_safe(sp.sympify(g), w) == 0
                                         for g, w in zip(sorted(got, key=_sortkey), sorted(wv, key=_sortkey)))
    elif "contains" in chk:
        wv = [_qsubs(env, env.parse(str(w)), store) for w in chk["contains"]]
        ok = all(any(cmp_exact_safe(sp.sympify(g), w) == 0 for g in got) for w in wv)
    else:
        raise CalcError("check op needs 'equals' or 'contains'")
    steps.append(f"check {chk.get('op')} {chk.get('equals', chk.get('contains'))}: got {got} -> {ok}")
    return ok


def _sortkey(v):
    v = sp.sympify(v)
    if v == sp.oo:
        return math.inf
    if v == -sp.oo:
        return -math.inf
    r = _real(v)
    return r if r is not None else 0.0


def _eq_list(env: Env, formal: dict, store: dict, sample: Optional[dict]) -> list:
    """Exact equations (expressions == 0) for the params."""
    eqs = []
    for e in formal.get("equations", []):
        if isinstance(e, str):
            (a, op, b), = _split_rel(e)
            if op != "=":
                raise CalcError(f"equation expected: {e}")
            eqs.append(_qsubs(env, env.parse(a), store) - _qsubs(env, env.parse(b), store))
        elif "limit" in e:
            eqs += _limit_eqs(env, e)
        else:
            raise CalcError(f"bad equation {e}")
    return eqs


def _limit_eqs(env: Env, e: dict) -> list:
    var = env.var
    expr = env.parse(e["limit"])
    at = env.parse(str(e["at"]))
    L = env.parse(str(e["equals"]))
    h = sp.Symbol("h", positive=True)
    ex = expr.subs(var, 1 / h) if at == sp.oo else expr.subs(var, at + h)
    s = sp.series(ex, h, 0, 1).removeO()
    out = []
    const = sp.Integer(0)
    for term in sp.Add.make_args(sp.expand(s)):
        c, p = term.as_coeff_exponent(h)
        if c.has(h):
            raise CalcError(f"limit series has non-power term {term}")
        if p < 0:
            out.append(c)
        elif p == 0:
            const += c
    out.append(const - L)
    return out


def _verify_eqs_numeric(env: Env, formal: dict, nstore: dict) -> float:
    worst = 0.0
    for e in formal.get("equations", []):
        if isinstance(e, str):
            (a, _, b), = _split_rel(e)
            v = _num_expr(env, a, nstore) - _num_expr(env, b, nstore)
        else:
            fn = sp.lambdify(env.var, env.parse(e["limit"]), ["mpmath", _num_env(env)])
            with mpmath.workdps(60):
                at = env.parse(str(e["at"]))
                pt = mpmath.mpf(10) ** 20 if at == sp.oo else _mpreal(at, 60) + mpmath.mpf(10) ** -20
                v = fn(pt) - _mpreal(env.parse(str(e["equals"])), 60)
        scale = 1.0
        worst = max(worst, float(abs(v)) / scale)
    return worst


def _evaluate(formal: dict, subs: dict, steps: list) -> tuple[Optional[Any], Any, dict, bool]:
    """Concrete pass: returns (target_exact, target_numeric, store, checks_ok)."""
    env = Env(formal, subs)
    for fd in env.defs.values():
        steps += fd.notes
    store, nstore = {}, {}
    env.store = store
    if formal.get("kind") == "area_region":
        A, nv = area_value(env, formal, steps, numeric=True)
        _bind(env, "A", QV(A, nv), store, nstore)
    for q in formal.get("quantities", []):
        qv = run_op(env, q, steps)
        _bind(env, q["name"], qv, store, nstore)
    for chk in formal.get("checks", []):
        if not _check(env, chk, store, nstore, steps):
            return None, None, store, False
    # the parameter equations must hold for the concrete candidate, exactly and numerically
    if subs:
        for e in _eq_list(env, formal, store, None):
            if is_zero(sp.simplify(e)) is not True:
                raise CalcError(f"equation residual {e} not proven zero for {subs}")
        w = _verify_eqs_numeric(env, formal, nstore)
        if w > 1e-6:
            raise CalcError(f"numeric equation residual {w:.3g} for {subs}")
        steps.append(f"parameters {subs}: equations re-verified exactly and numerically (residual {w:.1e})")
    tgt = formal.get("target", "A")
    te = _qsubs(env, env.parse(tgt), store)
    if te.free_symbols:
        raise CalcError(f"target has free symbols {te.free_symbols}")
    tn = _num_expr(env, tgt, nstore)
    return te, tn, store, True


def _solve_params(formal: dict, steps: list) -> list[dict]:
    env = Env(formal)
    params = list(env.params.values())
    sample = {env.params[k]: env.parse(str(v)) for k, v in (formal.get("param_sample") or {}).items()}
    store = {}
    if formal.get("kind") == "area_region" and any("A" in str(e) for e in formal.get("equations", [])):
        if not sample:
            raise CalcError("area with a symbolic parameter needs param_sample")
        A, _ = area_value(env, formal, steps, sample=sample, numeric=False)
        env.qsyms["A"] = sp.Symbol("A")
        store["A"] = A
        steps.append(f"A({', '.join(map(str, params))}) = {A} (structure valid near {sample})")
    eqs = [sp.simplify(e) for e in _eq_list(env, formal, store, sample)]
    eqs = [e for e in eqs if e != 0]
    if not eqs:
        raise CalcError("no equations to determine the parameters")
    sols = sp.solve(eqs, params, dict=True)
    if not isinstance(sols, list):
        raise CalcError(f"unexpected solve output {sols}")
    out = []
    for s in sols:
        if set(s) != set(params) or any(v.free_symbols for v in s.values()):
            raise CalcError(f"parameters not determined: {s}")
        if any(_real(v) is None for v in s.values()):
            continue
        ok = True
        for name, assum in (formal.get("params") or {}).items():
            if not assum:
                continue
            for a, op, b in _split_rel(assum):
                if not _rel_true(env.parse(a).subs(s), op, env.parse(b).subs(s)):
                    ok = False
        if ok:
            out.append({k: sp.simplify(v) for k, v in s.items()})
    steps.append(f"parameter candidates from the equations: {out}")
    return out


def _param_scan(formal: dict, roots: list[dict], steps: list):
    scan = formal.get("param_scan")
    if not scan:
        return
    (pname, (lo, hi, n)), = scan.items()
    env = Env(formal)
    p = env.params[pname]
    lo, hi, n = env.parse(str(lo)), env.parse(str(hi)), int(n)
    signs = []
    for i in range(n + 1):
        pv = lo + (hi - lo) * sp.Rational(2 * i + 1, 2 * n + 2)
        ev = Env(formal, {p: pv})
        store = {}
        if formal.get("kind") == "area_region":
            A, _ = area_value(ev, formal, [], numeric=False)
            ev.qsyms["A"] = sp.Symbol("A")
            store["A"] = A
        res = _eq_list(ev, formal, store, None)
        if len(res) != 1:
            raise CalcError("param_scan supports a single equation")
        r = _real(res[0])
        if r is None:
            raise CalcError("scan residual not real")
        signs.append(1 if r > 0 else (-1 if r < 0 else 0))
    changes = sum(1 for a, b in zip(signs[:-1], signs[1:]) if a * b < 0) + signs.count(0)
    inside = [r for r in roots if _inside(r[p], lo, hi)]
    if changes != len(inside):
        raise CalcError(f"scan of {pname} in ({lo}, {hi}) shows {changes} sign changes but "
                        f"{len(inside)} verified roots")
    steps.append(f"scan of the residual over {pname} in ({lo}, {hi}) ({n + 1} exact points): "
                 f"{changes} sign change(s) = verified root count")


def _apply_approx(formal: dict, v, env: Env):
    ap = formal.get("approximations")
    if not ap:
        return v
    v = sp.expand_log(sp.expand(v), force=True)
    for k, val in ap.items():
        ke = sp.expand_log(env.parse(k), force=True)
        v = v.subs(ke, env.parse(str(val)))
        if v.has(ke):
            raise CalcError(f"approximation {k} could not be applied")
    if v.has(sp.log) or v.has(sp.pi) and "pi" in ap:
        raise CalcError(f"approximated value still contains transcendental parts: {v}")
    return sp.nsimplify(v) if v.is_number else v


def _match(formal: dict, v, steps: list):
    m = formal["match"]
    env = Env(formal)
    unk = {n: sp.Symbol(n) for n in m["unknowns"]}
    syms = {**env.symbols(), **unk}
    basis = [parse(b, syms) for b in m.get("basis", [])]
    q = identify(v, basis)
    if q is None:
        raise CalcError(f"value {v} not expressible as a rational combination of 1, {basis} (proof failed)")
    steps.append(f"value = {q[0]} + " + " + ".join(f"({qi})*{b}" for qi, b in zip(q[1:], basis))
                 + " (exact, PSLQ candidate proven)")
    tmpl = sp.expand(parse(m["template"], syms))
    ph = [sp.Dummy(f"b{i}") for i in range(len(basis))]
    t2 = tmpl
    for b, d in zip(basis, ph):
        t2 = sp.expand(t2.subs(b, d))
    poly_part = sp.Poly(t2, *ph) if ph else None
    eqs = []
    if ph:
        for mon, coeff in poly_part.terms():
            if sum(mon) > 1:
                raise CalcError("template not linear in the basis")
        const = t2.subs({d: 0 for d in ph})
        eqs.append(const - q[0])
        for d, qi in zip(ph, q[1:]):
            eqs.append(sp.diff(t2, d) - qi)
    else:
        eqs.append(t2 - q[0])
    sols = sp.solve(eqs, list(unk.values()), dict=True)
    good = []
    for s in sols:
        if set(s) != set(unk.values()) or any(val.free_symbols for val in s.values()):
            continue
        ok = True
        for n, typ in m["unknowns"].items():
            val = s[unk[n]]
            if typ in ("natural", "integer") and not val.is_integer:
                ok = False
            if typ == "natural" and not (val.is_integer and val > 0):
                ok = False
        if ok:
            good.append(s)
    if len(good) != 1:
        raise CalcError(f"template {m['template']} matches {len(good)} admissible solutions: {good}")
    s = good[0]
    steps.append(f"template {m['template']}: {s}")
    ans = parse(m["answer"], syms).subs(s)
    return sp.simplify(ans), {str(k): v_ for k, v_ in s.items()}


def _fail(msg: str, steps: list, check_id: str = "calculus.solve") -> EngineResult:
    return EngineResult(None, "", [VerificationRecord(check_id=check_id, status=CheckStatus.UNRESOLVED,
                                                      method="calculus engine (fail closed)", tool=TOOL,
                                                      result=msg[:500])], steps)


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - registry signature
    steps: list[str] = []
    try:
        with time_limit(int(formal.get("timeout", 90))):
            return _solve(formal, steps)
    except CheckTimeout as e:
        return _fail(f"timeout: {e}", steps)
    except CalcError as e:
        return _fail(str(e), steps)
    except Exception as e:  # noqa: BLE001 - any solver failure blocks
        return _fail(f"{type(e).__name__}: {e}", steps)


def _solve(formal: dict, steps: list) -> EngineResult:
    if formal.get("kind") not in ("area_region", "extrema", "calculus_value"):
        raise CalcError(f"kind {formal.get('kind')} not handled")
    records: list[VerificationRecord] = []
    if formal.get("params"):
        cands = _solve_params(formal, steps)
        env0 = Env(formal)
        _param_scan(formal, [{env0.params[k]: v for k, v in c.items()} if False else c for c in cands], steps)
    else:
        cands = [{}]
    results = []
    for c in cands:
        sub_steps: list[str] = []
        te, tn, store, ok = _evaluate(formal, c, sub_steps)
        steps += sub_steps
        if ok:
            results.append((c, te, tn))
        else:
            steps.append(f"candidate {c} rejected by the stem's conditions")
    if not results:
        raise CalcError("no parameter candidate satisfies the stem's conditions")
    vals = [r[1] for r in results]
    for v in vals[1:]:
        if cmp_exact(v, vals[0]) != 0:
            raise CalcError(f"several admissible candidates give different answers: {results}")
    c, te, tn = results[0]
    env = Env(formal, c)
    if not te.is_number:
        raise CalcError(f"target {te} not a number")
    ten = _real(te)
    if tn is None or ten is None or abs(float(tn) - ten) > _RTOL * max(1.0, abs(ten)):
        raise CalcError(f"exact target {te} = {ten} and independent numeric {tn} disagree")
    records.append(VerificationRecord(
        check_id="calculus.exact", status=CheckStatus.EXACT_CHECKED, method=f"exact symbolic ({formal['kind']})",
        tool=TOOL, result=f"target = {te}", assumptions=[s for s in steps if "unique" in s or "Volterra" in s][:3],
        data={"params": {str(k): str(v) for k, v in c.items()}, "candidates": len(cands)}))
    records.append(VerificationRecord(
        check_id="calculus.numeric_crosscheck", status=CheckStatus.NUMERICALLY_CHECKED,
        numeric_evidence_sufficient=True, method="independent numeric method (slice scanning / dense sampling / "
                                                 "mpmath quadrature & differentiation)",
        tool=TOOL, result=f"numeric {float(tn):.12g} vs exact {ten:.12g}"))
    value = te
    if formal.get("match"):
        value, sol = _match(formal, canonical(te), steps)
        records.append(VerificationRecord(check_id="calculus.template_match", status=CheckStatus.EXACT_CHECKED,
                                          method="PSLQ candidate + exact proof + unique admissible solution",
                                          tool=TOOL, result=f"{sol} -> {value}",
                                          assumptions=["basis elements are linearly independent over Q with 1"]))
    if formal.get("approximations"):
        value = _apply_approx(formal, value, env)
        steps.append(f"stem approximations {formal['approximations']} applied: {value}")
    value = canonical(value)
    steps.append(f"answer = {value}")
    return EngineResult(value, formal.get("unit", ""), records, steps)
