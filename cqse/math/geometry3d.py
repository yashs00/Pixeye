"""Coordinate / vector geometry engine (kind = "geometry3d"): 3D lines, planes, triangles, 2D centres, conics.

A declarative construction language is evaluated TWICE, by two independent families of constructions,
and the admissible target values of both runs must coincide before anything is reported.

Formal state
------------
{
  "kind": "geometry3d",
  "params": {"p1": "real", "p2": "real", "A2": "positive", "b": "[0, pi/2]"},
        # unknown scalars.  domain: real | positive | negative | nonnegative | nonzero | interval "[a, b]",
        # "(a, b)", "[a, b)", "(a, b]"  (interval ends are expressions).
  "indeterminates": ["X", "Y"],          # optional: polynomial variables for "identity" conditions / poly(C, X, Y)
  "objects": {                           # evaluated IN ORDER; later objects may use earlier ones
      "P":  "(1, 2, 3)",                 # tuple literal = point / vector (2 or 3 components)
      "L1": {"symmetric": "(x+1)/3 = y/4 = z/5"},   # symmetric (Cartesian) form, any part may be "/0"
      "L2": "line((p1, 2, 1), (2, 3, 4))",           # point + direction  (also line2(P, Q): two points)
      "F":  "foot(P, L1)",               # any expression of the language (below)
      "s":  "dist2(P, F)"                # scalars are objects too
  },
  "conditions": [                        # equations that determine the params
      "sd2(L1, L2) = 1/6",               # lhs = rhs (scalars or vectors -> componentwise)
      "on(A, L1)",                       # a predicate
      {"identity": "poly(H, X, Y) = k*(3*X^2 - Y^2)", "in": ["X", "Y"]}   # polynomial identity -> coefficients
  ],
  "select": ["p1 < p2", "target > 0", "t != 0"],   # admissibility / selection rules ('target' = target value)
  "target": "expr"   |   {"which": "on(V, L)", "var": "V", "candidates": ["(7,15,13)", "(4,22,7)"]},
        # "which": value = 1-based index of the UNIQUE candidate satisfying the predicate
  "answer": "unique" (default) | "sum" | "set",
        # unique: every admissible solution must give the same target value;
        # sum:    sum of all DISTINCT admissible target values ("sum of all possible values");
        # set:    the finite set of admissible target values
  "model": ["free-text modelling notes"]
}

Expression language (parsed by cqse.math.expr.parse: whitelisted, decimals exact)
  arithmetic on scalars and vectors (+, -, scalar*vector), sqrt, Abs, sin, cos, ..., pi
  line(P, u)  line2(P, Q)  plane(P, n)  at(L, t) = P0 + t*u   dir(L)  pt(L)  normal(Pi)
  dot(u, v)  cross(u, v)  norm(u)  norm2(u)  cx(P) cy(P) cz(P)  det3(r1, r2, r3)
  dist(X, Y) / dist2(X, Y): point-point, point-line, point-plane, line-line (= shortest distance)
  sd(L1, L2) / sd2(L1, L2): shortest distance (squared) between skew/intersecting lines
  foot(P, L|Pi)  image(P, L|Pi)  meet(L1, L2|Pi) (intersection point)  common_perp(L1, L2) (line)
  area(P, Q, R)  area2(P, Q, R) (squared area, 2D or 3D)
  centroid(P, Q, R)  orthocentre(P, Q, R)  circumcentre(P, Q, R)  circumradius(P, Q, R)   (2D)
  ellipse(A2, B2): x^2/A2 + y^2/B2 = 1     hyperbola(A2, B2): x^2/A2 - y^2/B2 = 1
  hyperbola_foci(F1, F2, a): |PF1 - PF2| = 2a
  ecc(C)  latus_rectum(C)  focus(C, i)  directrix(C, i)  poly(C, X, Y)
        focus(C, 1) / directrix(C, 1) lie on the positive side of the focal axis; directrix(C, i) is the signed
        position of the directrix along the focal axis measured from the centre (x = a/e for x^2/a^2 - y^2/b^2 = 1)
  predicates (a condition, or 1/0 inside an expression):
  on(P, L|Pi|C)  perp(u|L, v|L)  parallel(u|L, v|L)  collinear(P, Q, R)  meets(L1, L2)  isosceles_right(A, B, C)
  iseq(a, b) (1 if a = b else 0)   numer(q), denom(q) (reduced numerator / positive denominator of a rational)

Two methods
  A: closed forms - projection formula for feet, triple-product formula for shortest distance, Cramer formula for
     intersections (with the coplanarity side-condition), cross-product areas, determinant expansion,
     textbook conic formulas, cross product for collinearity / incidence.
  B: defining conditions with auxiliary unknowns - foot by solving the perpendicularity condition, shortest
     distance by minimising |P(s) - Q(t)|^2 (stationarity equations), intersection by solving
     P1 + s d1 = P2 + t d2, image by solving (midpoint on line, PQ perpendicular), Heron's formula, triple product,
     Euler line H = A + B + C - 2O, focal-definition conic polynomial, chord-through-focus latus rectum.
  Each run solves its full system exactly (sympy), with radicals lifted to auxiliary non-negative unknowns,
  piecewise definitions split into cases, every candidate back-substituted exactly and checked against every
  domain / non-degeneracy / selection rule.  A further numeric multistart (Levenberg-Marquardt) solve of the
  method-B system must reach exactly the same set of admissible target values.

Fail-closed: parallel lines in sd/meet, degenerate lines or triangles, non-intersecting lines, a target that
varies over a continuum of solutions, several admissible values when one is expected, a method disagreement,
a timeout, or an undecidable comparison -> value None with a hard UNRESOLVED/FAILED record.
"""
from __future__ import annotations

import itertools
import math
import random
import re
from fractions import Fraction
from typing import Any, Callable, Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, CheckTimeout, VerificationRecord, time_limit
from cqse.core.result import EngineResult
from cqse.math.expr import parse, tri_equal

TOOL = f"cqse-geometry3d 0.1; sympy {sp.__version__}"
SOLVE_SECONDS = 12
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,15}$")


class GeometryError(ValueError):
    """Malformed formal or degenerate construction: always fails closed."""


# ------------------------------------------------------------------ boolean / rational placeholders
class IsZero(sp.Function):
    """1 if the argument is exactly 0, 0 if exactly nonzero; stays unevaluated while undecidable."""

    @classmethod
    def eval(cls, x):
        if isinstance(x, sp.Expr) and not x.free_symbols:
            r = tri_equal(x, sp.Integer(0))
            if r is True:
                return sp.Integer(1)
            if r is False:
                return sp.Integer(0)
        return None


class Numer(sp.Function):
    @classmethod
    def eval(cls, x):
        if isinstance(x, sp.Expr) and not x.free_symbols:
            v = sp.simplify(x)
            if v.is_Rational:
                return sp.Integer(v.p)
        return None


class Denom(sp.Function):
    @classmethod
    def eval(cls, x):
        if isinstance(x, sp.Expr) and not x.free_symbols:
            v = sp.simplify(x)
            if v.is_Rational:
                return sp.Integer(v.q)
        return None


def _num_iszero(x):
    return 1.0 if abs(x) < 1e-7 else 0.0


def _num_numer(x):
    f = Fraction(x).limit_denominator(10**6)
    if abs(float(f) - x) > 1e-9 * max(1.0, abs(x)):
        raise ValueError("not rational")
    return float(f.numerator)


def _num_denom(x):
    f = Fraction(x).limit_denominator(10**6)
    if abs(float(f) - x) > 1e-9 * max(1.0, abs(x)):
        raise ValueError("not rational")
    return float(f.denominator)


_NUM_MODULES = [{"IsZero": _num_iszero, "Numer": _num_numer, "Denom": _num_denom}, "math"]


# ------------------------------------------------------------------ geometric objects
class Line:
    def __init__(self, p: sp.Matrix, d: sp.Matrix):
        self.p, self.d = p, d


class Plane:
    def __init__(self, p: sp.Matrix, n: sp.Matrix):
        self.p, self.n = p, n


class Conic:
    """kind 'ellipse' (x'^2/a2 + y'^2/b2 = 1) or 'hyperbola' (x'^2/a2 - y'^2/b2 = 1), x' along unit vector u."""

    def __init__(self, kind: str, center: sp.Matrix, u: sp.Matrix, a2, b2, foci=None, a=None):
        self.kind, self.center, self.u, self.a2, self.b2 = kind, center, u, a2, b2
        self.foci, self.a = foci, a

    @property
    def v(self) -> sp.Matrix:
        return sp.Matrix([-self.u[1], self.u[0]])


class Pred:
    """A predicate: eqs() -> equations (may create auxiliary unknowns), truth -> 1/0 expression."""

    def __init__(self, eqs: Callable[[], list], truth: sp.Expr, name: str):
        self.eqs, self.truth, self.name = eqs, truth, name


def _is_vec(v) -> bool:
    return isinstance(v, sp.MatrixBase)


def _v3(v: sp.Matrix) -> sp.Matrix:
    if v.shape == (3, 1):
        return v
    if v.shape == (2, 1):
        return sp.Matrix([v[0], v[1], 0])
    raise GeometryError(f"not a 2D/3D vector: {v}")


def _dot(u, v):
    if u.shape != v.shape:
        raise GeometryError("dimension mismatch in dot product")
    return sum((a * b for a, b in zip(u, v)), sp.Integer(0))


def _cross_a(u, v):
    u, v = _v3(u), _v3(v)
    return u.cross(v)


def _cross_b(u, v):
    u, v = _v3(u), _v3(v)
    return sp.Matrix([sum(sp.LeviCivita(i, j, k) * u[j] * v[k] for j in range(3) for k in range(3))
                      for i in range(3)])


# ------------------------------------------------------------------ evaluation context (one per method)
class Ctx:
    def __init__(self, mode: str, formal: dict):
        if mode not in ("A", "B"):
            raise ValueError(mode)
        self.mode = mode
        self.formal = formal
        self.unknowns: list[sp.Symbol] = []
        self.params: dict[str, sp.Symbol] = {}
        self.domains: dict[sp.Symbol, sp.Set] = {}
        self.eqs: list[tuple[sp.Expr, str]] = []
        self.nonzero: list[tuple[sp.Expr, str]] = []
        self.rels: list[tuple[Any, str]] = []      # relational constraints (domains, construction validity)
        self.selects: list[tuple[Any, str]] = []   # selection rules (may involve the target)
        self.env: dict[str, Any] = {}
        self.indet: dict[str, sp.Symbol] = {}
        self._n = 0
        self._cond_ctx = False

    # -- bookkeeping
    def aux(self, hint: str) -> sp.Symbol:
        self._n += 1
        s = sp.Symbol(f"_{hint}{self._n}", real=True)
        self.unknowns.append(s)
        return s

    def eq(self, e, origin: str) -> None:
        if _is_vec(e):
            for c in e:
                self.eq(c, origin)
            return
        self.eqs.append((sp.sympify(e), origin))

    def nz(self, e, origin: str) -> None:
        self.nonzero.append((sp.sympify(e), origin))

    def pos(self, e, origin: str) -> None:
        self.rels.append((sp.StrictGreaterThan(sp.sympify(e), 0), origin))

    # -- parsing
    def symbols(self, extra: Optional[dict] = None) -> dict:
        syms: dict[str, Any] = {}
        for n in PRIMS:
            syms[n] = sp.Function(n)
        syms.update(self.params)
        syms.update(self.indet)
        for n in self.env:
            if n not in self.params:
                syms[n] = sp.Symbol(n)
        if extra:
            syms.update(extra)
        return syms

    def expr(self, s: str, extra: Optional[dict] = None, bind: Optional[dict] = None):
        if not isinstance(s, str):
            s = str(s)
        tree = parse(s, self.symbols(extra))
        return self.ev(tree, bind or {})

    def ev(self, node, bind: dict):
        if isinstance(node, tuple):
            node = sp.Tuple(*node)
        if isinstance(node, sp.Symbol):
            if node.name in bind:
                return bind[node.name]
            if node.name in self.params:
                return self.params[node.name]
            if node.name in self.indet:
                return self.indet[node.name]
            if node.name in self.env:
                return self.env[node.name]
            raise GeometryError(f"unknown name {node.name}")
        if isinstance(node, sp.Tuple):
            vals = [self.ev(a, bind) for a in node.args]
            if any(not isinstance(v, sp.Expr) for v in vals) or len(vals) not in (2, 3):
                raise GeometryError(f"tuple must hold 2 or 3 scalars: {node}")
            return sp.Matrix(vals)
        if isinstance(node, sp.core.function.AppliedUndef):
            name = node.func.__name__
            if name not in PRIMS:
                raise GeometryError(f"unknown function {name}")
            return PRIMS[name](self, *[self.ev(a, bind) for a in node.args])
        if isinstance(node, sp.Add):
            vals = [self.ev(a, bind) for a in node.args]
            vecs = [v for v in vals if _is_vec(v)]
            if vecs and len(vecs) != len(vals):
                raise GeometryError(f"cannot add scalar and vector in {node}")
            if any(isinstance(v, (Line, Plane, Conic, Pred)) for v in vals):
                raise GeometryError(f"arithmetic on non-numeric object in {node}")
            out = vals[0]
            for v in vals[1:]:
                out = out + v
            return out
        if isinstance(node, sp.Mul):
            vals = [self.ev(a, bind) for a in node.args]
            if any(isinstance(v, (Line, Plane, Conic)) for v in vals):
                raise GeometryError(f"arithmetic on non-numeric object in {node}")
            vals = [v.truth if isinstance(v, Pred) else v for v in vals]
            if sum(1 for v in vals if _is_vec(v)) > 1:
                raise GeometryError(f"product of two vectors in {node}: use dot/cross")
            out = sp.Integer(1)
            for v in vals:
                out = v * out if _is_vec(v) else out * v
            return out
        if isinstance(node, sp.Pow):
            b, e = self.ev(node.base, bind), self.ev(node.exp, bind)
            if not isinstance(b, sp.Expr) or not isinstance(e, sp.Expr):
                raise GeometryError(f"power of non-scalar in {node}")
            return b ** e
        if isinstance(node, sp.Function):
            args = [self.ev(a, bind) for a in node.args]
            if any(not isinstance(a, sp.Expr) for a in args):
                raise GeometryError(f"{node.func} needs scalar arguments")
            return node.func(*args)
        if isinstance(node, (sp.Number, sp.NumberSymbol)) or node in (sp.pi, sp.E):
            return node
        if isinstance(node, sp.Expr) and not node.free_symbols:
            return node
        raise GeometryError(f"unsupported expression node {node!r}")

    def scalar(self, s: str, **kw) -> sp.Expr:
        v = self.expr(s, **kw)
        if isinstance(v, Pred):
            return v.truth
        if not isinstance(v, sp.Expr):
            raise GeometryError(f"{s!r} is not a scalar")
        return v


# ------------------------------------------------------------------ primitives
def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise GeometryError(msg)


def _vec(x, what="vector"):
    _need(_is_vec(x), f"{what} expected, got {type(x).__name__}")
    return x


def _line(x):
    _need(isinstance(x, Line), f"line expected, got {type(x).__name__}")
    return x


def p_line(c: Ctx, P, u):
    _vec(P), _vec(u)
    _need(P.shape == u.shape, "line: point and direction dimensions differ")
    c.nz(_dot(u, u), "line direction is nonzero")
    return Line(P, u)


def p_line2(c: Ctx, P, Q):
    return p_line(c, _vec(P), _vec(Q) - P)


def p_plane(c: Ctx, P, n):
    _vec(P), _vec(n)
    c.nz(_dot(n, n), "plane normal is nonzero")
    return Plane(_v3(P), _v3(n))


def p_at(c: Ctx, L, t):
    L = _line(L)
    return L.p + t * L.d


def p_dir(c: Ctx, L):
    return _line(L).d


def p_pt(c: Ctx, L):
    return _line(L).p


def p_normal(c: Ctx, Pi):
    _need(isinstance(Pi, Plane), "plane expected")
    return Pi.n


def p_dot(c: Ctx, u, v):
    u, v = _vec(u), _vec(v)
    if c.mode == "A":
        return _dot(u, v)
    return (_dot(u + v, u + v) - _dot(u - v, u - v)) / 4  # polarisation identity


def p_cross(c: Ctx, u, v):
    return (_cross_a if c.mode == "A" else _cross_b)(_vec(u), _vec(v))


def p_norm2(c: Ctx, u):
    return _dot(_vec(u), u)


def p_norm(c: Ctx, u):
    return sp.sqrt(p_norm2(c, u))


def _comp(i):
    def f(c: Ctx, P):
        P = _vec(P)
        _need(P.shape[0] > i, "coordinate index out of range")
        return P[i]
    return f


def p_det3(c: Ctx, r1, r2, r3):
    r1, r2, r3 = _v3(_vec(r1)), _v3(_vec(r2)), _v3(_vec(r3))
    if c.mode == "A":
        return sp.Matrix([list(r1), list(r2), list(r3)]).det(method="bareiss")
    return _dot(r1, _cross_b(r2, r3))  # scalar triple product


def _foot_line(c: Ctx, P, L: Line):
    if c.mode == "A":
        return L.p + (_dot(P - L.p, L.d) / _dot(L.d, L.d)) * L.d
    t = c.aux("t")
    X = L.p + t * L.d
    c.eq(_dot(X - P, L.d), "foot: PX perpendicular to the line")
    return X


def _foot_plane(c: Ctx, P, Pi: Plane):
    P = _v3(P)
    if c.mode == "A":
        return P - (_dot(Pi.n, P - Pi.p) / _dot(Pi.n, Pi.n)) * Pi.n
    t = c.aux("t")
    X = P + t * Pi.n
    c.eq(_dot(Pi.n, X - Pi.p), "foot: X on the plane")
    return X


def p_foot(c: Ctx, P, M):
    P = _vec(P)
    if isinstance(M, Line):
        _need(P.shape == M.p.shape, "foot: dimension mismatch")
        return _foot_line(c, P, M)
    if isinstance(M, Plane):
        return _foot_plane(c, P, M)
    raise GeometryError("foot(P, line|plane)")


def p_image(c: Ctx, P, M):
    P = _vec(P)
    if c.mode == "A":
        return 2 * p_foot(c, P, M) - (P if not isinstance(M, Plane) else _v3(P))
    if isinstance(M, Line):
        Q = sp.Matrix([c.aux("q") for _ in range(P.shape[0])])
        mid = (P + Q) / 2
        c.eq(_cross_b(mid - M.p, M.d), "image: midpoint of PQ on the line")
        c.eq(_dot(Q - P, M.d), "image: PQ perpendicular to the line")
        return Q
    if isinstance(M, Plane):
        P = _v3(P)
        Q = sp.Matrix([c.aux("q") for _ in range(3)])
        c.eq(_dot(M.n, (P + Q) / 2 - M.p), "image: midpoint on the plane")
        c.eq(_cross_b(Q - P, M.n), "image: PQ along the normal")
        return Q
    raise GeometryError("image(P, line|plane)")


def _sd2(c: Ctx, L1: Line, L2: Line):
    _need(L1.p.shape == (3, 1) and L2.p.shape == (3, 1), "shortest distance needs 3D lines")
    if c.mode == "A":
        n = _cross_a(L1.d, L2.d)
        c.nz(_dot(n, n), "shortest distance: lines not parallel")
        return _dot(L2.p - L1.p, n) ** 2 / _dot(n, n)
    s, t = c.aux("s"), c.aux("t")
    w = (L2.p + t * L2.d) - (L1.p + s * L1.d)
    # stationarity of |w|^2 (a convex quadratic): the minimum
    c.eq(_dot(w, L1.d), "min |P(s)-Q(t)|^2: d/ds = 0")
    c.eq(_dot(w, L2.d), "min |P(s)-Q(t)|^2: d/dt = 0")
    return _dot(w, w)


def p_dist2(c: Ctx, X, Y):
    if isinstance(X, Line) and isinstance(Y, Line):
        return _sd2(c, X, Y)
    if isinstance(X, (Line, Plane)) and _is_vec(Y):
        X, Y = Y, X
    if _is_vec(X) and _is_vec(Y):
        _need(X.shape == Y.shape, "dist: dimension mismatch")
        return _dot(X - Y, X - Y)
    if _is_vec(X) and isinstance(Y, Line):
        if c.mode == "A":
            cr = _cross_a(X - Y.p, Y.d)
            return _dot(cr, cr) / _dot(Y.d, Y.d)
        F = _foot_line(c, X, Y)
        return _dot(X - F, X - F)
    if _is_vec(X) and isinstance(Y, Plane):
        X = _v3(X)
        if c.mode == "A":
            return _dot(Y.n, X - Y.p) ** 2 / _dot(Y.n, Y.n)
        F = _foot_plane(c, X, Y)
        return _dot(X - F, X - F)
    raise GeometryError("dist2: unsupported object pair")


def p_dist(c: Ctx, X, Y):
    return sp.sqrt(p_dist2(c, X, Y))


def p_sd2(c: Ctx, L1, L2):
    return _sd2(c, _line(L1), _line(L2))


def p_sd(c: Ctx, L1, L2):
    return sp.sqrt(p_sd2(c, L1, L2))


def p_meet(c: Ctx, L1, M):
    L1 = _line(L1)
    if isinstance(M, Line):
        _need(L1.p.shape == (3, 1) and M.p.shape == (3, 1), "meet: 3D lines")
        if c.mode == "A":
            w, n = M.p - L1.p, _cross_a(L1.d, M.d)
            c.nz(_dot(n, n), "meet: lines not parallel")
            c.eq(_dot(w, n), "meet: lines coplanar")
            s = _dot(_cross_a(w, M.d), n) / _dot(n, n)
            return L1.p + s * L1.d
        s, t = c.aux("s"), c.aux("t")
        c.eq(L1.p + s * L1.d - M.p - t * M.d, "meet: common point")
        c.nz(_dot(_cross_b(L1.d, M.d), _cross_b(L1.d, M.d)), "meet: lines not coincident/parallel")
        return L1.p + s * L1.d
    if isinstance(M, Plane):
        a, d = _v3(L1.p), _v3(L1.d)
        if c.mode == "A":
            c.nz(_dot(M.n, d), "meet: line not parallel to plane")
            return a + (_dot(M.n, M.p - a) / _dot(M.n, d)) * d
        t = c.aux("t")
        c.eq(_dot(M.n, a + t * d - M.p), "meet: point on plane")
        c.nz(_dot(M.n, d), "meet: line not parallel to plane")
        return a + t * d
    raise GeometryError("meet(line, line|plane)")


def p_common_perp(c: Ctx, L1, L2):
    L1, L2 = _line(L1), _line(L2)
    if c.mode == "A":
        w = L1.p - L2.p
        a, b, cc = _dot(L1.d, L1.d), _dot(L1.d, L2.d), _dot(L2.d, L2.d)
        d, e = _dot(L1.d, w), _dot(L2.d, w)
        den = a * cc - b ** 2
        c.nz(den, "common perpendicular: lines not parallel")
        s = (b * e - cc * d) / den
        return Line(L1.p + s * L1.d, _cross_a(L1.d, L2.d))
    s, t = c.aux("s"), c.aux("t")
    P, Q = L1.p + s * L1.d, L2.p + t * L2.d
    c.eq(_dot(Q - P, L1.d), "common perpendicular: PQ perpendicular to L1")
    c.eq(_dot(Q - P, L2.d), "common perpendicular: PQ perpendicular to L2")
    c.nz(_dot(Q - P, Q - P), "common perpendicular: lines do not intersect")
    return Line(P, Q - P)


def _sides2(P, Q, R):
    return _dot(Q - R, Q - R), _dot(R - P, R - P), _dot(P - Q, P - Q)


def p_area2(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    _need(P.shape == Q.shape == R.shape, "area: dimension mismatch")
    if c.mode == "A":
        cr = _cross_a(Q - P, R - P)
        return _dot(cr, cr) / 4
    x, y, z = _sides2(P, Q, R)
    return (2 * (x * y + y * z + z * x) - (x ** 2 + y ** 2 + z ** 2)) / 16  # Heron


def p_area(c: Ctx, P, Q, R):
    return sp.sqrt(p_area2(c, P, Q, R))


def _two(P, Q, R):
    _need(all(_is_vec(v) and v.shape == (2, 1) for v in (P, Q, R)), "triangle centres are 2D")


def _solve2(c: Ctx, M: list[list], rhs: list, what: str):
    det = M[0][0] * M[1][1] - M[0][1] * M[1][0]
    c.nz(det, f"{what}: non-degenerate triangle")
    x = (rhs[0] * M[1][1] - M[0][1] * rhs[1]) / det
    y = (M[0][0] * rhs[1] - rhs[0] * M[1][0]) / det
    return sp.Matrix([x, y])


def _circum_a(c: Ctx, P, Q, R):
    # |O-P|^2 = |O-Q|^2, |O-P|^2 = |O-R|^2 (linear in O), Cramer
    rows = [list(2 * (Q - P)), list(2 * (R - P))]
    return _solve2(c, rows, [_dot(Q, Q) - _dot(P, P), _dot(R, R) - _dot(P, P)], "circumcentre")


def _circum_b(c: Ctx, P, Q, R):
    (ax, ay), (bx, by), (cx, cy) = list(P), list(Q), list(R)
    D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    c.nz(D, "circumcentre: non-degenerate triangle")
    a2, b2, c2 = ax ** 2 + ay ** 2, bx ** 2 + by ** 2, cx ** 2 + cy ** 2
    return sp.Matrix([(a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / D,
                      (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / D])


def p_centroid(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    if c.mode == "A":
        return (P + Q + R) / 3
    _two(P, Q, R)
    # intersection of the medians from P and Q (Cramer on P + s(Mqr - P) = Q + t(Mpr - Q))
    m1, m2 = (Q + R) / 2 - P, (P + R) / 2 - Q
    st = _solve2(c, [[m1[0], -m2[0]], [m1[1], -m2[1]]], [Q[0] - P[0], Q[1] - P[1]], "centroid")
    return P + st[0] * m1


def p_orthocentre(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    _two(P, Q, R)
    if c.mode == "A":
        # (H-P).(Q-R) = 0, (H-Q).(P-R) = 0
        return _solve2(c, [list(Q - R), list(P - R)], [_dot(P, Q - R), _dot(Q, P - R)], "orthocentre")
    return P + Q + R - 2 * _circum_b(c, P, Q, R)  # Euler: H = 3G - 2O


def p_circumcentre(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    _two(P, Q, R)
    return (_circum_a if c.mode == "A" else _circum_b)(c, P, Q, R)


def p_circumradius(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    _two(P, Q, R)
    if c.mode == "A":
        x, y, z = _sides2(P, Q, R)
        cr = _cross_a(Q - P, R - P)
        c.nz(_dot(cr, cr), "circumradius: non-degenerate triangle")
        return sp.sqrt(x * y * z) / (2 * sp.sqrt(_dot(cr, cr)))  # abc / (4 * area)
    O = _circum_b(c, P, Q, R)
    return sp.sqrt(_dot(O - P, O - P))


# ---- conics (2D)
def p_ellipse(c: Ctx, A2, B2):
    c.pos(A2, "ellipse: a^2 > 0")
    c.pos(B2, "ellipse: b^2 > 0")
    return Conic("ellipse", sp.Matrix([0, 0]), sp.Matrix([1, 0]), A2, B2)


def p_hyperbola(c: Ctx, A2, B2):
    c.pos(A2, "hyperbola: a^2 > 0")
    c.pos(B2, "hyperbola: b^2 > 0")
    return Conic("hyperbola", sp.Matrix([0, 0]), sp.Matrix([1, 0]), A2, B2)


def p_hyperbola_foci(c: Ctx, F1, F2, a):
    F1, F2 = _vec(F1), _vec(F2)
    _need(F1.shape == (2, 1) and F2.shape == (2, 1), "hyperbola_foci: 2D foci")
    c.pos(a, "hyperbola: a > 0")
    c2 = _dot(F2 - F1, F2 - F1) / 4
    c.pos(c2 - a ** 2, "hyperbola: a < c")
    u = (F2 - F1) / sp.sqrt(4 * c2)
    return Conic("hyperbola", (F1 + F2) / 2, u, a ** 2, c2 - a ** 2, foci=(F2, F1), a=a)


def _conic(C):
    _need(isinstance(C, Conic), "conic expected")
    return C


def _major(C: Conic):
    """(cond 'major axis along u', ...) for an ellipse; hyperbola: transverse along u always."""
    return sp.GreaterThan(C.a2, C.b2)


def _pw(cond, a, b):
    return sp.Piecewise((a, cond), (b, True))


def _cdist(c: Ctx, C: Conic):
    """centre-to-focus distance along the focal axis."""
    if C.kind == "hyperbola":
        if c.mode == "A":
            return sp.sqrt(C.a2 + C.b2)
        return sp.sqrt(C.a2) * sp.sqrt(1 + C.b2 / C.a2)  # c = a e
    m = _major(C)
    if c.mode == "A":
        return _pw(m, sp.sqrt(C.a2 - C.b2), sp.sqrt(C.b2 - C.a2))
    return _pw(m, sp.sqrt(C.a2) * sp.sqrt(1 - C.b2 / C.a2), sp.sqrt(C.b2) * sp.sqrt(1 - C.a2 / C.b2))


def p_focus(c: Ctx, C, i):
    C = _conic(C)
    _need(i in (1, 2), "focus index must be 1 or 2")
    sgn = 1 if i == 1 else -1
    if C.foci is not None and c.mode == "B":
        return C.foci[i - 1]
    cd = _cdist(c, C)
    if C.kind == "hyperbola":
        return C.center + sgn * cd * C.u
    m = _major(C)
    return sp.Matrix([_pw(m, C.center[k] + sgn * cd * C.u[k], C.center[k] + sgn * cd * C.v[k]) for k in range(2)])


def p_ecc(c: Ctx, C):
    C = _conic(C)
    if C.kind == "hyperbola":
        if c.mode == "A":
            return sp.sqrt(1 + C.b2 / C.a2)
        F = p_focus(c, C, 1)
        return sp.sqrt(_dot(F - C.center, F - C.center)) / sp.sqrt(C.a2)  # e = c / a
    m = _major(C)
    if c.mode == "A":
        return _pw(m, sp.sqrt(1 - C.b2 / C.a2), sp.sqrt(1 - C.a2 / C.b2))
    return _pw(m, sp.sqrt(C.a2 - C.b2) / sp.sqrt(C.a2), sp.sqrt(C.b2 - C.a2) / sp.sqrt(C.b2))


def p_directrix(c: Ctx, C, i):
    C = _conic(C)
    _need(i in (1, 2), "directrix index must be 1 or 2")
    sgn = 1 if i == 1 else -1
    e = p_ecc(c, C)
    if C.kind == "hyperbola":
        a = sp.sqrt(C.a2)
        return sgn * (a / e if c.mode == "A" else a - (_cdist(c, C) - a) / e)  # B: vertex: |VF| = e |V D|
    m = _major(C)
    a = _pw(m, sp.sqrt(C.a2), sp.sqrt(C.b2))
    return sgn * (a / e if c.mode == "A" else a + (a - _cdist(c, C)) / e)


def p_latus_rectum(c: Ctx, C):
    C = _conic(C)
    if C.kind == "hyperbola":
        if c.mode == "A":
            return 2 * C.b2 / sp.sqrt(C.a2)
        cd = _cdist(c, C)
        h2 = C.b2 * (cd ** 2 / C.a2 - 1)       # (c, h) on x^2/a2 - y^2/b2 = 1
        return 2 * sp.sqrt(h2)
    m = _major(C)
    if c.mode == "A":
        return _pw(m, 2 * C.b2 / sp.sqrt(C.a2), 2 * C.a2 / sp.sqrt(C.b2))
    cd = _cdist(c, C)
    return _pw(m, 2 * sp.sqrt(C.b2 * (1 - cd ** 2 / C.a2)), 2 * sp.sqrt(C.a2 * (1 - cd ** 2 / C.b2)))


def _poly(c: Ctx, C: Conic, P):
    if c.mode == "A" or C.kind == "ellipse":
        x, y = _dot(P - C.center, C.u), _dot(P - C.center, C.v)
        if C.kind == "ellipse":
            return x ** 2 / C.a2 + y ** 2 / C.b2 - 1 if c.mode == "A" else \
                C.b2 * x ** 2 + C.a2 * y ** 2 - C.a2 * C.b2
        return x ** 2 / C.a2 - y ** 2 / C.b2 - 1
    # focal definition |d1 - d2| = 2a, squared twice (exact, quadratic in P)
    F1, F2 = (C.foci if C.foci is not None else (p_focus(c, C, 1), p_focus(c, C, 2)))
    a2 = C.a2
    d1, d2 = _dot(P - F1, P - F1), _dot(P - F2, P - F2)
    return (d1 - d2) ** 2 - 8 * a2 * (d1 + d2) + 16 * a2 ** 2


def p_poly(c: Ctx, C, X, Y):
    return sp.expand(_poly(c, _conic(C), sp.Matrix([X, Y])))


# ---- predicates
def _sumsq(v):
    return sum((e ** 2 for e in v), sp.Integer(0)) if _is_vec(v) else v ** 2


def _dirof(x):
    if isinstance(x, Line):
        return x.d
    return _vec(x)


def p_on(c: Ctx, P, M):
    P = _vec(P)
    if isinstance(M, Line):
        a, d = M.p, M.d
        cr = _cross_a(P - a, d)
        lag = _dot(P - a, P - a) * _dot(d, d) - _dot(P - a, d) ** 2  # Lagrange identity
        if c.mode == "A":
            return Pred(lambda: [(e, "on: (P - a) x d = 0") for e in cr], IsZero(_sumsq(cr)), "on")

        def eqs():
            t = c.aux("t")
            return [(e, "on: P = a + t d") for e in (P - a - t * d)]
        return Pred(eqs, IsZero(lag), "on")
    if isinstance(M, Plane):
        r = _dot(M.n, _v3(P) - M.p)
        return Pred(lambda: [(r, "on: plane equation")], IsZero(r), "on")
    if isinstance(M, Conic):
        r = _poly(c, M, P)
        return Pred(lambda: [(r, "on: conic equation")], IsZero(r), "on")
    raise GeometryError("on(P, line|plane|conic)")


def p_perp(c: Ctx, x, y):
    u, v = _dirof(x), _dirof(y)
    r = _dot(u, v) if c.mode == "A" else _dot(u + v, u + v) - _dot(u, u) - _dot(v, v)
    return Pred(lambda: [(r, "perpendicular")], IsZero(r), "perp")


def p_parallel(c: Ctx, x, y):
    u, v = _dirof(x), _dirof(y)
    c.nz(_dot(v, v), "parallel: nonzero vector")
    cr = _cross_a(u, v)
    if c.mode == "A":
        return Pred(lambda: [(e, "parallel: u x v = 0") for e in cr], IsZero(_sumsq(cr)), "parallel")

    def eqs():
        k = c.aux("k")
        return [(e, "parallel: u = k v") for e in (u - k * v)]
    lag = _dot(u, u) * _dot(v, v) - _dot(u, v) ** 2
    return Pred(eqs, IsZero(lag), "parallel")


def p_collinear(c: Ctx, P, Q, R):
    P, Q, R = _vec(P), _vec(Q), _vec(R)
    c.nz(_dot(Q - P, Q - P), "collinear: P != Q")
    cr = _cross_a(Q - P, R - P)
    if c.mode == "A":
        return Pred(lambda: [(e, "collinear: PQ x PR = 0") for e in cr], IsZero(_sumsq(cr)), "collinear")

    def eqs():
        k = c.aux("k")
        return [(e, "collinear: R = P + k (Q - P)") for e in (R - P - k * (Q - P))]
    u, v = Q - P, R - P
    return Pred(eqs, IsZero(_dot(u, u) * _dot(v, v) - _dot(u, v) ** 2), "collinear")


def p_meets(c: Ctx, L1, L2):
    L1, L2 = _line(L1), _line(L2)
    n = _cross_a(L1.d, L2.d)
    c.nz(_dot(n, n), "meets: lines not parallel")
    r = _dot(L2.p - L1.p, n)
    if c.mode == "A":
        return Pred(lambda: [(r, "meets: coplanar")], IsZero(r), "meets")

    def eqs():
        s, t = c.aux("s"), c.aux("t")
        return [(e, "meets: common point") for e in (L1.p + s * L1.d - L2.p - t * L2.d)]
    return Pred(eqs, IsZero(_dot(L2.p - L1.p, _cross_b(L1.d, L2.d))), "meets")


def p_isosceles_right(c: Ctx, A, B, C):
    A, B, C = _vec(A), _vec(B), _vec(C)
    if c.mode == "A":
        x, y, z = _sides2(A, B, C)  # |BC|^2, |CA|^2, |AB|^2
        res = ((y - z) ** 2 + (y + z - x) ** 2) * ((x - z) ** 2 + (x + z - y) ** 2) * \
              ((x - y) ** 2 + (x + y - z) ** 2)
    else:
        res = sp.Integer(1)
        for V, P, Q in ((A, B, C), (B, C, A), (C, A, B)):
            u, v = P - V, Q - V
            res *= (_dot(u, u) - _dot(v, v)) ** 2 + _dot(u, v) ** 2
    area = p_area2(c, A, B, C)
    truth = IsZero(res) * (1 - IsZero(area))
    return Pred(lambda: [(res, "isosceles right")], truth, "isosceles_right")


def p_iseq(c: Ctx, a, b):
    _need(isinstance(a, sp.Expr) and isinstance(b, sp.Expr), "iseq: scalars")
    return IsZero(a - b)


def p_numer(c: Ctx, q):
    return Numer(q)


def p_denom(c: Ctx, q):
    return Denom(q)


PRIMS: dict[str, Callable] = {
    "line": p_line, "line2": p_line2, "plane": p_plane, "at": p_at, "dir": p_dir, "pt": p_pt, "normal": p_normal,
    "dot": p_dot, "cross": p_cross, "norm": p_norm, "norm2": p_norm2, "cx": _comp(0), "cy": _comp(1),
    "cz": _comp(2), "det3": p_det3, "dist": p_dist, "dist2": p_dist2, "sd": p_sd, "sd2": p_sd2, "foot": p_foot,
    "image": p_image, "meet": p_meet, "common_perp": p_common_perp, "area": p_area, "area2": p_area2,
    "centroid": p_centroid, "orthocentre": p_orthocentre, "circumcentre": p_circumcentre,
    "circumradius": p_circumradius, "ellipse": p_ellipse, "hyperbola": p_hyperbola,
    "hyperbola_foci": p_hyperbola_foci, "ecc": p_ecc, "latus_rectum": p_latus_rectum, "focus": p_focus,
    "directrix": p_directrix, "poly": p_poly, "on": p_on, "perp": p_perp, "parallel": p_parallel,
    "collinear": p_collinear, "meets": p_meets, "isosceles_right": p_isosceles_right, "iseq": p_iseq,
    "numer": p_numer, "denom": p_denom,
}


# ------------------------------------------------------------------ formal -> system
def _split_top(s: str, seps: tuple[str, ...]) -> Optional[tuple[str, str, str]]:
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0:
            for sep in seps:
                if s.startswith(sep, i):
                    return s[:i], sep, s[i + len(sep):]
        i += 1
    return None


def _last_top_slash(s: str) -> Optional[int]:
    depth, pos = 0, None
    for i, ch in enumerate(s):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "/" and depth == 0:
            pos = i
    return pos


def _symmetric_line(c: Ctx, spec: str) -> Line:
    parts = [p.strip() for p in spec.split("=")]
    _need(len(parts) in (2, 3), f"symmetric form needs 2 or 3 parts: {spec!r}")
    coords = {n: sp.Symbol(n) for n in ("x", "y", "z")[:len(parts)]}
    pt, dr, used = {}, {}, set()
    for part in parts:
        k = _last_top_slash(part)
        num_s, den_s = (part, "1") if k is None else (part[:k], part[k + 1:])
        num = parse(num_s, {**c.params, **coords})
        den = c.ev(parse(den_s, dict(c.params)), {})
        _need(isinstance(den, sp.Expr) and not (den.free_symbols & set(coords.values())),
              f"bad denominator in {part!r}")
        vs = num.free_symbols & set(coords.values())
        _need(len(vs) == 1, f"each part must involve exactly one coordinate: {part!r}")
        v = vs.pop()
        _need(v.name not in used, f"coordinate {v} appears twice in {spec!r}")
        used.add(v.name)
        poly = sp.Poly(sp.expand(num), v)
        _need(poly.degree() == 1, f"part not linear in {v}: {part!r}")
        coef, k0 = poly.coeff_monomial(v), poly.coeff_monomial(1)
        c.nz(coef, "symmetric form: nonzero coefficient")
        pt[v.name], dr[v.name] = -k0 / coef, den / coef
    names = [n for n in ("x", "y", "z")[:len(parts)]]
    _need(set(pt) == set(names), f"symmetric form must use each of {names}")
    return p_line(c, sp.Matrix([pt[n] for n in names]), sp.Matrix([dr[n] for n in names]))


def _domain_set(dom: str, syms: dict) -> sp.Set:
    d = dom.strip()
    simple = {"real": sp.S.Reals, "positive": sp.Interval.open(0, sp.oo), "negative": sp.Interval.open(-sp.oo, 0),
              "nonnegative": sp.Interval(0, sp.oo), "nonzero": sp.Union(sp.Interval.open(-sp.oo, 0),
                                                                      sp.Interval.open(0, sp.oo))}
    if d in simple:
        return simple[d]
    m = re.match(r"^([\[(])(.+),(.+)([\])])$", d)
    if not m:
        raise GeometryError(f"unknown domain {dom!r}")
    lo, hi = parse(m.group(2), syms), parse(m.group(3), syms)
    _need(not lo.free_symbols and not hi.free_symbols, "interval ends must be constants")
    return sp.Interval(lo, hi, left_open=m.group(1) == "(", right_open=m.group(4) == ")")


_REL = {"<=": sp.LessThan, ">=": sp.GreaterThan, "!=": sp.Ne, "<": sp.StrictLessThan, ">": sp.StrictGreaterThan,
        "==": sp.Eq}


def build(formal: dict, mode: str) -> tuple[Ctx, sp.Expr, Optional[sp.Expr], list]:
    """Evaluate the formal under one method. Returns (ctx, target, which_count, ...)."""
    c = Ctx(mode, formal)
    for n, dom in (formal.get("params") or {}).items():
        _need(bool(_NAME.match(n)) and n not in PRIMS and n != "target", f"bad param name {n!r}")
        s = sp.Symbol(n, real=True)
        c.params[n] = s
        c.unknowns.append(s)
        ds = _domain_set(str(dom), {})
        c.domains[s] = ds
        if ds != sp.S.Reals:
            c.rels.append((ds.as_relational(s), f"domain of {n}: {dom}"))
    for n in formal.get("indeterminates") or []:
        _need(bool(_NAME.match(n)) and n not in PRIMS and n not in c.params, f"bad indeterminate {n!r}")
        c.indet[n] = sp.Symbol(n)
    for name, spec in (formal.get("objects") or {}).items():
        _need(bool(_NAME.match(name)) and name not in PRIMS and name not in c.params and name not in c.indet
              and name != "target", f"bad object name {name!r}")
        if isinstance(spec, dict) and "symmetric" in spec:
            c.env[name] = _symmetric_line(c, spec["symmetric"])
        elif isinstance(spec, str):
            c.env[name] = c.expr(spec)
        else:
            raise GeometryError(f"object {name}: unsupported spec {spec!r}")
    for cond in formal.get("conditions") or []:
        if isinstance(cond, dict) and "identity" in cond:
            sp_ = _split_top(cond["identity"], ("=",))
            _need(sp_ is not None, "identity needs '='")
            lhs, rhs = c.scalar(sp_[0]), c.scalar(sp_[2])
            vars_ = [c.indet[v] for v in cond["in"]]
            num = sp.numer(sp.together(sp.expand(lhs - rhs)))
            poly = sp.Poly(sp.expand(num), *vars_)
            for coeff in poly.coeffs():
                c.eq(coeff, f"identity in {cond['in']}")
            continue
        _need(isinstance(cond, str), f"condition must be a string: {cond!r}")
        sp_ = _split_top(cond, ("<=", ">=", "!=", "==", "="))
        if sp_ is not None and sp_[1] == "=":
            lhs, rhs = c.expr(sp_[0]), c.expr(sp_[2])
            if _is_vec(lhs) and _is_vec(rhs):
                _need(lhs.shape == rhs.shape, f"dimension mismatch in {cond!r}")
                c.eq(lhs - rhs, cond)
            elif isinstance(lhs, sp.Expr) and isinstance(rhs, sp.Expr):
                c.eq(lhs - rhs, cond)
            else:
                raise GeometryError(f"cannot equate {cond!r}")
            continue
        _need(sp_ is None, f"inequalities belong in 'select': {cond!r}")
        p = c.expr(cond)
        _need(isinstance(p, Pred), f"condition is not an equation or predicate: {cond!r}")
        for e, why in p.eqs():
            c.eq(e, f"{cond} [{why}]")
    tgt = formal.get("target")
    which_count = None
    if isinstance(tgt, dict) and "which" in tgt:
        total, count = sp.Integer(0), sp.Integer(0)
        for k, cand in enumerate(tgt["candidates"], 1):
            val = c.expr(cand)
            p = c.expr(tgt["which"], extra={tgt["var"]: sp.Symbol(tgt["var"])}, bind={tgt["var"]: val})
            tr = p.truth if isinstance(p, Pred) else p
            total += k * tr
            count += tr
        T, which_count = total, count
    elif isinstance(tgt, str):
        T = c.scalar(tgt)
    else:
        raise GeometryError("target missing")
    for sel in formal.get("select") or []:
        sp_ = _split_top(sel, ("<=", ">=", "!=", "==", "<", ">"))
        _need(sp_ is not None, f"select rule needs a relation: {sel!r}")
        tsym = sp.Symbol("target")
        lhs = c.scalar(sp_[0], extra={"target": tsym}, bind={"target": T})
        rhs = c.scalar(sp_[2], extra={"target": tsym}, bind={"target": T})
        c.selects.append((_REL[sp_[1]](lhs, rhs, evaluate=False), sel))
    return c, T, which_count


# ------------------------------------------------------------------ exact solving
class Unresolved(Exception):
    pass


def _decide(rel) -> Optional[bool]:
    """Exact truth of a relational / boolean between numbers; None if undecidable."""
    if rel in (sp.true, True):
        return True
    if rel in (sp.false, False):
        return False
    if isinstance(rel, (sp.And, sp.Or, sp.Not)):
        vals = [_decide(a) for a in rel.args]
        if isinstance(rel, sp.Not):
            return None if vals[0] is None else not vals[0]
        if isinstance(rel, sp.And):
            return False if False in vals else (None if None in vals else True)
        return True if True in vals else (None if None in vals else False)
    if isinstance(rel, sp.Rel):
        d = rel.lhs - rel.rhs
        if d.free_symbols:
            return None
        z = tri_equal(d, sp.Integer(0))
        if z is None:
            return None
        if isinstance(rel, sp.Eq):
            return z
        if isinstance(rel, sp.Ne):
            return not z
        if z:
            return isinstance(rel, (sp.GreaterThan, sp.LessThan))
        v = complex(sp.N(d, 50))
        if abs(v.imag) > 1e-40:
            return False
        pos = v.real > 0
        if isinstance(rel, (sp.GreaterThan, sp.StrictGreaterThan)):
            return pos
        return not pos
    return None


def _real(v: sp.Expr) -> Optional[bool]:
    if v.is_real:
        return True
    if not v.has(sp.I) and not v.free_symbols:
        n = complex(sp.N(v, 50))
        return True if abs(n.imag) < 1e-40 else None
    im = sp.simplify(sp.im(sp.expand_complex(v)))
    if im == 0:
        return True
    if im.is_number and im.is_zero is False:
        return False
    return None


def _split_piecewise(eqs: list[sp.Expr]):
    """Yield (eqs, branch_conditions) for every combination of piecewise branches."""
    pws = [p for e in eqs for p in e.atoms(sp.Piecewise)]
    if not pws:
        yield eqs, []
        return
    p = min(pws, key=sp.count_ops)
    prev = []
    for arg in p.args:
        cond = sp.And(arg.cond, *[sp.Not(q) for q in prev]) if prev else arg.cond
        prev.append(arg.cond)
        if cond is sp.false:
            continue
        rep = [e.xreplace({p: arg.expr}) for e in eqs]
        for sub, conds in _split_piecewise(rep):
            yield sub, [cond] + conds


def _lift(eqs: list[sp.Expr], unk: set) -> tuple[list[sp.Expr], list[sp.Symbol], list]:
    """Replace sqrt(E) / Abs(E) of unknowns by new unknowns r >= 0 with r^2 = E (resp. E^2)."""
    eqs = list(eqs)
    new, rels = [], []
    n = 0
    while True:
        allunk = unk | set(new)
        cands = []
        for e in eqs:
            for a in sp.preorder_traversal(e):
                if isinstance(a, sp.Pow) and a.exp.is_Rational and a.exp.q == 2 and a.base.free_symbols & allunk:
                    cands.append(a)
                elif isinstance(a, sp.Abs) and a.args[0].free_symbols & allunk:
                    cands.append(a)
        if not cands:
            return eqs, new, rels
        a = min(cands, key=sp.count_ops)
        n += 1
        r = sp.Symbol(f"_r{n}", real=True)
        new.append(r)
        rels.append(sp.GreaterThan(r, 0))
        if isinstance(a, sp.Abs):
            E = a.args[0]
            eqs = [e.xreplace({a: r}) for e in eqs] + [r ** 2 - E ** 2]
        else:
            base = a.base
            eqs = [e.replace(lambda x: isinstance(x, sp.Pow) and x.base == base and x.exp.is_Rational
                             and x.exp.q == 2, lambda x: r ** (x.exp * 2)) for e in eqs] + [r ** 2 - base]


def _numerators(eqs: list[sp.Expr], unk: set) -> tuple[list[sp.Expr], list[sp.Expr]]:
    out, dens = [], []
    for e in eqs:
        num, den = sp.fraction(sp.together(e))
        num = sp.expand(num)
        if den.free_symbols & unk:
            dens.append(den)
        if num == 0:
            continue
        out.append(num)
    return out, dens


def _exact_solve(eqs: list[sp.Expr], unk: list[sp.Symbol], domains: dict) -> list[dict]:
    if not eqs:
        return [{}]
    present = [u for u in unk if any(u in e.free_symbols for e in eqs)]
    for e in eqs:
        if not e.free_symbols & set(present):
            z = tri_equal(e, sp.Integer(0))
            if z is False:
                return []
            if z is None:
                raise Unresolved(f"cannot decide constant equation {e} = 0")
    eqs = [e for e in eqs if e.free_symbols & set(present)]
    if not eqs:
        return [{}]
    trig = any(e.has(sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.exp, sp.log) for e in eqs)
    if trig:
        if len(present) != 1:
            raise Unresolved("transcendental system in more than one unknown")
        x = present[0]
        dom = domains.get(x, sp.S.Reals)
        sols = dom
        for e in eqs:
            sols = sp.Intersection(sols, sp.solveset(e, x, domain=dom))
        if not isinstance(sols, sp.FiniteSet) and sols != sp.S.EmptySet:
            raise Unresolved(f"transcendental solution set not finite: {sols}")
        return [{x: v} for v in sols]
    sols = sp.solve(eqs, present, dict=True)
    if not isinstance(sols, list):
        raise Unresolved("solver returned an unexpected form")
    return sols


def solve_mode(formal: dict, mode: str) -> dict:
    """Exact admissible target values under one method."""
    c, T, which_count = build(formal, mode)
    unk = list(c.unknowns)
    raw = [e for e, _ in c.eqs]
    rels = [r for r, _ in c.rels]
    nonzero = [e for e, _ in c.nonzero]
    selects = [r for r, _ in c.selects]
    results: list[tuple[dict, sp.Expr]] = []
    rejected: list[str] = []
    for eqs_b, conds in _split_piecewise(raw):
        lifted, new, lrels = _lift(eqs_b, set(unk))
        nums, dens = _numerators(lifted, set(unk) | set(new))
        sols = _exact_solve(nums, unk + new, c.domains)
        for sol in sols:
            sol = {k: sp.simplify(v) for k, v in sol.items()}
            free = set().union(*[v.free_symbols for v in sol.values()]) if sol else set()
            free |= {u for u in unk if u not in sol and any(u in e.free_symbols for e in raw + [T])}
            free = {f for f in free if f in set(unk) | set(new)}
            if any(_real(v) is False for v in sol.values()):
                rejected.append(f"{sol}: complex")
                continue
            checks = [(sp.Ne(d, 0, evaluate=False), "denominator / non-degeneracy") for d in dens + nonzero] + \
                     [(r, "radical >= 0") for r in lrels] + [(r, "domain/validity") for r in rels] + \
                     [(r, "piecewise case") for r in conds]
            tsym = sp.Symbol("target")
            eq_checks = list(eqs_b) + list(raw)
            samples = [{}] if not free else _samples(free)
            ok_any, values, undecided = False, [], None
            for smp in samples:
                full = {k: v.subs(smp) for k, v in sol.items()}
                full.update(smp)
                if any(_real(v) is not True for v in full.values()):
                    continue
                # domain / non-degeneracy first: a candidate outside the domain is never back-substituted
                bad = False
                for r, why in checks:
                    d = _decide(r.subs(full) if not isinstance(r, bool) else r)
                    if d is None:
                        undecided = f"{why} undecidable: {r} at {full}"
                    if not d:
                        bad = True
                        break
                if bad:
                    continue
                for e in eq_checks:
                    ev_ = sp.sympify(e).subs(full)
                    if ev_.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                        bad = True
                        break
                    z = tri_equal(ev_, sp.Integer(0))
                    if z is False:
                        bad = True
                        break
                    if z is None:
                        undecided = f"back-substitution undecidable at {full}"
                        bad = True
                        break
                if bad:
                    continue
                tval = _canon(T.subs(full))
                sel_ok = True
                for r in selects:
                    d = _decide(r.subs(full).subs({tsym: tval}))
                    if d is None:
                        undecided = f"select undecidable: {r} at {full}"
                        sel_ok = False
                        break
                    if not d:
                        sel_ok = False
                        break
                if not sel_ok:
                    continue
                if which_count is not None:
                    wc = sp.simplify(which_count.subs(full))
                    if wc != 1:
                        raise Unresolved(f"'which' target: {wc} candidates satisfy the predicate (need exactly 1)")
                ok_any = True
                values.append(tval)
                if not free:
                    break
            if not ok_any:
                if undecided and not free:
                    raise Unresolved(undecided)
                rejected.append(f"{ {str(k): str(v) for k, v in sol.items()} }: inadmissible")
                continue
            for v in values:
                if v.free_symbols or v.has(IsZero, Numer, Denom):
                    raise Unresolved(f"target not determined: {v}")
            base = values[0]
            for v in values[1:]:
                if tri_equal(v, base) is not True:
                    raise Unresolved(f"target varies over a continuum of solutions ({base} vs {v})")
            results.append(({str(k): v for k, v in sol.items()}, base))
    vals: list[sp.Expr] = []
    for _, v in results:
        hit = None
        for w in vals:
            r = tri_equal(v, w)
            if r is None:
                raise Unresolved(f"cannot decide whether {v} = {w}")
            if r:
                hit = w
                break
        if hit is None:
            vals.append(v)
    return {"values": vals, "solutions": results, "rejected": rejected, "ctx": c, "target": T}


def _canon(v: sp.Expr) -> sp.Expr:
    """Exact canonical form: simplify, then denest radicals; keep the shortest exact form."""
    v = sp.simplify(v)
    best = v
    for f in (sp.radsimp, sp.sqrtdenest):
        try:
            w = sp.simplify(f(best))
        except Exception:  # noqa: BLE001
            continue
        if sp.count_ops(w) < sp.count_ops(best) and tri_equal(w, best) is True:
            best = w
    if best.is_number and not best.is_Rational:
        # an algebraic number that is numerically an integer/rational: confirm exactly via minimal polynomial
        n = sp.N(best, 60)
        if n.is_real:
            cand = sp.Rational(str(sp.N(n, 40))).limit_denominator(10**6)
            try:
                if sp.minimal_polynomial(best - cand, sp.Symbol("_m")) == sp.Symbol("_m"):
                    best = cand
            except Exception:  # noqa: BLE001
                pass
    return best


def _samples(free: set) -> list[dict]:
    rng = random.Random(4243)
    fl = sorted(free, key=str)
    out = []
    for _ in range(25):
        out.append({f: sp.Rational(rng.randint(-40, 40), rng.randint(1, 7)) for f in fl})
    return out


# ------------------------------------------------------------------ numeric cross-check
def _lm(fun, n: int, x0: list[float], iters: int = 120) -> Optional[list[float]]:
    x = list(x0)
    mu = 1e-3

    def F(z):
        return [float(v) for v in fun(*z)]
    try:
        f = F(x)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None
    cost = sum(v * v for v in f)
    for _ in range(iters):
        if cost < 1e-26:
            return x
        J = []
        try:
            for j in range(n):
                h = 1e-7 * (1 + abs(x[j]))
                xp = list(x)
                xp[j] += h
                fp = F(xp)
                J.append([(a - b) / h for a, b in zip(fp, f)])
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            return None
        m = len(f)
        A = [[sum(J[i][k] * J[j][k] for k in range(m)) for j in range(n)] for i in range(n)]
        g = [sum(J[i][k] * f[k] for k in range(m)) for i in range(n)]
        improved = False
        for _ in range(12):
            Am = [[A[i][j] + (mu * (A[i][i] + 1e-12) if i == j else 0.0) for j in range(n)] for i in range(n)]
            step = _gauss(Am, [-v for v in g])
            if step is None:
                mu *= 10
                continue
            xn = [a + b for a, b in zip(x, step)]
            try:
                fn = F(xn)
            except (ValueError, ZeroDivisionError, OverflowError, TypeError):
                mu *= 10
                continue
            cn = sum(v * v for v in fn)
            if cn < cost:
                x, f, cost = xn, fn, cn
                mu = max(mu / 10, 1e-15)
                improved = True
                break
            mu *= 10
        if not improved:
            break
    return x if cost < 1e-20 else None


def _gauss(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-300:
            return None
        M[col], M[piv] = M[piv], M[col]
        for r in range(n):
            if r != col:
                fct = M[r][col] / M[col][col]
                for k in range(col, n + 1):
                    M[r][k] -= fct * M[col][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def _num_rel_ok(rel, f) -> Optional[bool]:
    """Numeric truth of a relation with tolerance; strict relations near the boundary are False."""
    tol = 1e-5
    if isinstance(rel, (sp.And, sp.Or, sp.Not)):
        vals = [_num_rel_ok(a, f) for a in rel.args]
        if None in vals:
            return None
        if isinstance(rel, sp.Not):
            return not vals[0]
        return all(vals) if isinstance(rel, sp.And) else any(vals)
    if rel in (sp.true, True):
        return True
    if rel in (sp.false, False):
        return False
    d = f(rel.lhs - rel.rhs)
    if d is None:
        return None
    if isinstance(rel, sp.Eq):
        return abs(d) <= tol
    if isinstance(rel, sp.Ne):
        return abs(d) > tol
    if isinstance(rel, sp.GreaterThan):
        return d >= -tol
    if isinstance(rel, sp.LessThan):
        return d <= tol
    if isinstance(rel, sp.StrictGreaterThan):
        return d > tol
    if isinstance(rel, sp.StrictLessThan):
        return d < -tol
    return None


def numeric_values(formal: dict, mode: str = "B", starts: int = 160, seed: int = 7) -> list[float]:
    """Multistart Levenberg-Marquardt on the un-lifted system; admissible target values (clustered)."""
    c, T, which_count = build(formal, mode)
    unk = list(c.unknowns)
    eqs = [e for e, _ in c.eqs]
    if not unk:
        pts = [[]]
    else:
        fun = sp.lambdify(unk, eqs, modules=_NUM_MODULES) if eqs else None
        rng = random.Random(seed)
        pts = []
        for k in range(starts):
            scale = (3, 12, 40)[k % 3]
            x0 = []
            for u in unk:
                dom = c.domains.get(u, sp.S.Reals)
                if isinstance(dom, sp.Interval) and dom.inf.is_finite and dom.sup.is_finite:
                    lo, hi = float(dom.inf), float(dom.sup)
                    x0.append(rng.uniform(lo, hi))
                elif isinstance(dom, sp.Interval) and dom.inf == 0:
                    x0.append(rng.uniform(1e-3, scale))
                elif isinstance(dom, sp.Interval) and dom.sup == 0:
                    x0.append(-rng.uniform(1e-3, scale))
                else:
                    x0.append(rng.uniform(-scale, scale))
            if fun is None:
                pts.append(x0)
                continue
            r = _lm(fun, len(unk), x0)
            if r is not None:
                pts.append(r)
    cache: dict = {}

    def mkf(expr):
        key = sp.srepr(expr)
        if key not in cache:
            cache[key] = sp.lambdify(unk, expr, modules=_NUM_MODULES)
        g = cache[key]

        def f(_e=None):
            try:
                v = complex(g(*x))
            except (ValueError, ZeroDivisionError, OverflowError, TypeError):
                return None
            return v.real if abs(v.imag) < 1e-9 else None
        return f
    vals: list[float] = []
    for x in pts:
        ok = True
        for e, _ in c.nonzero:
            v = mkf(e)()
            if v is None or abs(v) < 1e-6:
                ok = False
                break
        if not ok:
            continue
        for r, _ in c.rels:
            if not _num_rel_ok(r, lambda ex: mkf(ex)()):
                ok = False
                break
        if not ok:
            continue
        tv = mkf(T)()
        if tv is None:
            continue
        for r, _ in c.selects:
            r2 = r.subs({sp.Symbol("target"): T}) if r.has(sp.Symbol("target")) else r
            if not _num_rel_ok(r2, lambda ex: mkf(ex)()):
                ok = False
                break
        if not ok:
            continue
        if which_count is not None:
            wc = mkf(which_count)()
            if wc is None or abs(wc - 1) > 1e-9:
                continue
        vals.append(tv)
    clusters: list[float] = []
    for v in vals:
        if not any(abs(v - w) <= 1e-5 * max(1.0, abs(w)) for w in clusters):
            clusters.append(v)
    return clusters


# ------------------------------------------------------------------ entry point
def _rec(cid: str, st: CheckStatus, method: str, result: str, **kw) -> VerificationRecord:
    return VerificationRecord(check_id=cid, status=st, method=method, tool=TOOL, result=result, **kw)


def _aggregate(vals: list[sp.Expr], how: str) -> tuple[Optional[sp.Basic], str]:
    if how == "unique":
        if len(vals) != 1:
            return None, f"{len(vals)} admissible target values {[str(v) for v in vals]} (one expected)"
        return vals[0], "single admissible value"
    if how == "sum":
        if not vals:
            return None, "no admissible value to sum"
        return sp.simplify(sp.Add(*vals)), f"sum of {len(vals)} distinct admissible values"
    if how == "set":
        return sp.FiniteSet(*vals), f"{len(vals)} admissible values"
    return None, f"unknown answer mode {how!r}"


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - subject unused
    out = EngineResult()
    how = formal.get("answer", "unique")
    res: dict[str, dict] = {}
    methods = {"A": "closed-form constructions (projection, triple product, Cramer, cross-product area, textbook "
                    "conic formulas) + exact solve",
               "B": "constructions by defining conditions (perpendicularity / stationarity of |P(s)-Q(t)|^2 / "
                    "common point / Heron / Euler line / focal definition) with auxiliary unknowns + exact solve"}
    for mode in ("A", "B"):
        cid = f"geometry3d.solve.{mode}"
        try:
            with time_limit(SOLVE_SECONDS):
                r = solve_mode(formal, mode)
        except CheckTimeout as e:
            out.records.append(_rec(cid, CheckStatus.UNRESOLVED, methods[mode], f"timeout: {e}"))
            return out
        except (GeometryError, Unresolved) as e:
            out.records.append(_rec(cid, CheckStatus.UNRESOLVED, methods[mode], f"{type(e).__name__}: {e}"))
            return out
        except Exception as e:  # noqa: BLE001 - any solver error blocks
            out.records.append(_rec(cid, CheckStatus.UNRESOLVED, methods[mode], f"{type(e).__name__}: {e}"))
            return out
        res[mode] = r
        out.records.append(_rec(
            cid, CheckStatus.EXACT_CHECKED, methods[mode],
            f"{len(r['solutions'])} admissible solution(s); target values {[str(v) for v in r['values']]}",
            data={"solutions": [{k: str(v) for k, v in s.items()} | {"target": str(t)} for s, t in r["solutions"]],
                  "rejected": r["rejected"][:20]}))
        if mode == "A":
            out.steps.append(f"Method A solutions: " + "; ".join(
                f"{ {k: str(v) for k, v in s.items() if not k.startswith('_')} } -> {t}" for s, t in r["solutions"]))
            if r["rejected"]:
                out.steps.append(f"Rejected candidates: {r['rejected'][:6]}")
    va, vb = res["A"]["values"], res["B"]["values"]
    from cqse.math.expr import _set_equal  # exact set comparison (value-wise)
    same = _set_equal(sp.FiniteSet(*va) if va else sp.S.EmptySet, sp.FiniteSet(*vb) if vb else sp.S.EmptySet) \
        if (va or vb) else True
    if same is not True:
        st = CheckStatus.FAILED if same is False else CheckStatus.UNRESOLVED
        out.records.append(_rec("geometry3d.methods_agree", st, "A vs B admissible target values",
                                f"method A {[str(v) for v in va]} vs method B {[str(v) for v in vb]}"))
        return out
    out.records.append(_rec("geometry3d.methods_agree", CheckStatus.EXACT_CHECKED, "A vs B admissible target values",
                            f"both methods give {[str(v) for v in va]}"))
    value, why = _aggregate(va, how)
    if value is None:
        out.records.append(_rec("geometry3d.target_determined", CheckStatus.FAILED, f"answer mode {how}", why))
        return out
    out.records.append(_rec("geometry3d.target_determined", CheckStatus.EXACT_CHECKED, f"answer mode {how}", why))

    def _numeric() -> VerificationRecord:
        nv = numeric_values(formal, "B")
        ex = [complex(sp.N(v, 30)) for v in va]
        if any(abs(e.imag) > 1e-12 for e in ex):
            return _rec("geometry3d.numeric_crosscheck", CheckStatus.UNRESOLVED, "multistart LM",
                        "non-real exact value")
        ex = [e.real for e in ex]
        close = lambda a, b: abs(a - b) <= 1e-5 * max(1.0, abs(b))  # noqa: E731
        extra = [v for v in nv if not any(close(v, e) for e in ex)]
        missing = [e for e in ex if not any(close(v, e) for v in nv)]
        if extra or missing:
            return _rec("geometry3d.numeric_crosscheck", CheckStatus.UNRESOLVED,
                        "multistart Levenberg-Marquardt on the method-B system",
                        f"numeric admissible values {nv}; exact {ex}; extra {extra}, missing {missing}")
        return _rec("geometry3d.numeric_crosscheck", CheckStatus.NUMERICALLY_CHECKED,
                    "multistart Levenberg-Marquardt on the method-B system", f"numeric values {nv} match exact",
                    numeric_evidence_sufficient=True)
    try:
        with time_limit(SOLVE_SECONDS):
            out.records.append(_numeric())
    except CheckTimeout as e:
        out.records.append(_rec("geometry3d.numeric_crosscheck", CheckStatus.UNRESOLVED, "multistart LM",
                                f"timeout: {e}"))
        return out
    except Exception as e:  # noqa: BLE001
        out.records.append(_rec("geometry3d.numeric_crosscheck", CheckStatus.UNRESOLVED, "multistart LM",
                                f"{type(e).__name__}: {e}"))
        return out
    out.records.append(VerificationRecord(
        check_id="model.correspondence", status=CheckStatus.UNRESOLVED, method="teacher confirms the construction "
        "models the stem", tool=TOOL, result="objects, conditions and selection rules must be confirmed by a teacher",
        data={"model": formal.get("model", []), "conditions": [str(x) for x in formal.get("conditions", [])]}))
    if not out.records[-2].is_affirmative():
        return out
    out.value = value
    out.steps.append(f"Target ({how}) = {value}")
    return out
