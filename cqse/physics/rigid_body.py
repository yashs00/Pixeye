"""Rigid-body engine: moments of inertia of composite bodies about arbitrary axes, by two independent methods,
bridged into the general equation checker for rotational dynamics.

Formal state (kind = "rigid_body") = an equation_system formal (cqse/generic/system.py) plus:
{
  "kind": "rigid_body",
  "knowns":   {"M": {"value": "symbolic", "unit": "kg"}, "R": {"value": "symbolic", "unit": "m"}},
  "bodies": {                                   # every number/expression may use the knowns' names
     "disc": {"shape": "disc", "mass": "M", "dims": {"R": "R"},
              "center": ["0", "0", "0"],         # REFERENCE point of the shape (see SHAPES below)
              "axis": [0, 0, 1],                 # symmetry axis / plane normal  (n)      [exact numbers]
              "u": [1, 0, 0]},                   # in-plane / long direction     (u ⟂ n) [exact numbers]
     "hole": {"shape": "disc", "density": "M/(pi*R**2)", "dims": {"R": "R/2"},   # mass = density * measure
              "center": ["R/2", "0", "0"], "sign": -1},                           # removed part
     "rod":  {"shape": "rod", "mass": "M", "dims": {"L": "L"},
              "density_profile": "1 + (s_ + L/2)/L"},  # variable density: local coords s_ (rod), r_ (radial)
  },
  "inertia": {"I": {"bodies": ["disc", "hole"],              # signed sum over parts
                    "axis": {"point": ["R", "0", "0"], "dir": [0, 0, 1]}}},
  "masses":  {"Mt": ["disc", "hole"]},                       # optional: signed total mass as a symbol
  "relations": [{"template": "rolling_incline", "a": "a", "f": "f", "M": "M", "I": "I", "R": "R",
                 "g": "g", "th": "th"}],                     # optional: engine-derived dynamics relations
                 # rolling_incline: outputs a, f (any subset); inputs M, I, R, g, th required
                 # rolling_ke: outputs KE, KEt, KEr; inputs M, I, R, v required
  "calculus": {"w": {"integral": "(c1*t - c2*t**2)*Rp/Ip", "var": "t", "lower": "0", "upper": "T"},
               "dI": {"derivative": "I", "var": "l", "subs": {"R": "sqrt(V/(pi*l))"}}},
                 # optional exact calculus on known/unknown symbols and inertia names (inertia names are replaced
                 # by their computed expressions first); each result becomes an equation "name = result".
                 # integral cross-check: d/d(upper) of the result == integrand at upper (and value 0 at lower);
                 # derivative cross-check: limit of the difference quotient.
  "unknowns": {...}, "equations": [...], "target": "...", "model": [...]   # as in equation_system
}
Each inertia name (and mass name) becomes an unknown with an exact defining equation, so the equations may use
it like any other quantity (rolling, angular-momentum conservation, torque = I alpha, work-energy ...).
If "equations" is omitted, the first inertia entry is the target.

Methods for every inertia entry (must agree EXACTLY, else FAILED):
  A. standard-results table about the centroid (perpendicular-axis theorem for laminae), tensor parallel-axis
     theorem to the requested axis, signed composition of parts; for variable density, continuous composition
     of tabulated thin elements (points along a rod, rings in a disc, shells in a sphere).
  B. direct exact symbolic integration of r_perp^2 dm over each body's own geometry.
Then the augmented system is solved by the equation_system checker (dimensions, uniqueness, two solvers).
"""
from __future__ import annotations

import copy
from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.core.result import EngineResult
from cqse.generic.system import ModelError, solve_system
from cqse.math.expr import parse

TOOL = f"cqse-rigid 1.0; sympy {sp.__version__}"
# Integration variables are Dummy symbols: they can never collide with names used in a formal (r, s, x, z...).
_r, _s = sp.Dummy("r_int", positive=True), sp.Dummy("s_int", positive=True)  # local radial / rod coordinate
_sr = sp.Dummy("s_rod", real=True)
_ph, _th, _z = sp.Dummy("phi_int", real=True), sp.Dummy("theta_int", real=True), sp.Dummy("z_int", real=True)
pi = sp.pi

# shape -> (dims required, reference point description)
SHAPES = {
    "point": ((), "the particle"),
    "rod": (("L",), "rod centre; rod along u"),
    "ring": (("R",), "centre; plane normal n"),
    "semi_ring": (("R",), "centre of the full circle; arc spans +v side (phi in [0, pi] from u)"),
    "disc": (("R",), "centre; plane normal n"),
    "annular_disc": (("R1", "R2"), "centre; plane normal n"),
    "semi_disc": (("R",), "centre of the full circle; half on +v side"),
    "solid_cylinder": (("R", "L"), "centre; axis n"),
    "hollow_cylinder": (("R", "L"), "centre; thin curved shell, axis n"),
    "thick_cylinder": (("R1", "R2", "L"), "centre; axis n"),
    "solid_sphere": (("R",), "centre"),
    "spherical_shell": (("R",), "centre; thin shell"),
    "thick_spherical_shell": (("R1", "R2"), "centre"),
    "solid_hemisphere": (("R",), "centre of the flat face; dome along +n"),
    "hemispherical_shell": (("R",), "centre of the rim circle; dome along +n"),
    "rect_plate": (("a", "b"), "centre; side a along u, side b along v, normal n"),
    "cuboid": (("a", "b", "c"), "centre; a along u, b along v, c along n"),
    "cube": (("a",), "centre"),
    "solid_cone": (("R", "H"), "centre of the base; apex at +H along n"),
}
VARIABLE_OK = {"rod": "s", "disc": "r", "annular_disc": "r", "solid_sphere": "r"}


class RigidError(ModelError):
    pass


# ------------------------------------------------------------------ parsing
def _syms(formal: dict) -> dict[str, sp.Symbol]:
    names = list(formal.get("knowns", {})) + list(formal.get("unknowns", {}))   # geometry may use unknowns
    for n in names:
        if n in ("r_", "s_"):
            raise RigidError("'r_' and 's_' are reserved for local density coordinates")
    return {n: sp.Symbol(n, positive=True) for n in names}


def _ex(v, syms: dict, extra: Optional[dict] = None) -> sp.Expr:
    if isinstance(v, (int, sp.Basic)):
        return sp.sympify(v)
    d = dict(syms)
    if extra:
        d.update(extra)
    return parse(str(v), d)


def _vec(v, syms) -> sp.Matrix:
    if v is None or len(v) != 3:
        raise RigidError(f"vector must have 3 components: {v!r}")
    return sp.Matrix([_ex(c, syms) for c in v])


def _unit(v: sp.Matrix) -> sp.Matrix:
    if any(c.free_symbols for c in v):
        raise RigidError("directions must be exact numbers")
    n = sp.sqrt(sp.nsimplify(v.dot(v)))
    if n == 0:
        raise RigidError("zero direction")
    return sp.simplify(v / n)


class Body:
    def __init__(self, name: str, spec: dict, syms: dict, numeric: dict):
        self.name = name
        self.shape = spec.get("shape")
        if self.shape not in SHAPES:
            raise RigidError(f"unknown body shape {self.shape!r} (known: {sorted(SHAPES)})")
        need = SHAPES[self.shape][0]
        dims = spec.get("dims", {})
        if set(dims) != set(need):
            raise RigidError(f"{name}: {self.shape} needs dims {need}, got {sorted(dims)}")
        self.d = {k: _ex(v, syms) for k, v in dims.items()}
        if self.shape == "cube":
            self.d = {"a": self.d["a"], "b": self.d["a"], "c": self.d["a"]}
        self.sign = int(spec.get("sign", 1))
        if self.sign not in (1, -1):
            raise RigidError("sign must be +1 or -1")
        self.c = _vec(spec.get("center", [0, 0, 0]), syms)
        self.n = _unit(_vec(spec.get("axis", [0, 0, 1]), syms))
        u0 = spec.get("u")
        if u0 is None:
            a = sp.Matrix([1, 0, 0]) if abs(float(self.n[0])) < 0.9 else sp.Matrix([0, 1, 0])
            u0 = a - a.dot(self.n) * self.n
            self.u = _unit(sp.Matrix([sp.nsimplify(x) for x in u0]))
        else:
            self.u = _unit(_vec(u0, syms))
        if sp.simplify(self.u.dot(self.n)) != 0:
            raise RigidError(f"{name}: u must be perpendicular to axis")
        self.v = sp.simplify(self.n.cross(self.u))
        prof = spec.get("density_profile")
        dens = spec.get("density")
        self.profile = None
        local = {"r_": _r, "s_": _sr}
        if prof is not None or (dens is not None and _ex(dens, syms, local).has(_r, _sr)):
            if self.shape not in VARIABLE_OK:
                raise RigidError(f"{name}: variable density only for {sorted(VARIABLE_OK)}")
            self.profile = _ex(prof if prof is not None else dens, syms, local)
        meas = self.measure()
        if "mass" in spec:
            self.M = _ex(spec["mass"], syms)
            if self.profile is not None and prof is None:
                raise RigidError(f"{name}: give either mass+density_profile or an absolute density")
        elif dens is not None:
            if self.profile is not None:
                self.M = None          # absolute variable density: mass = integral (computed by both methods)
            else:
                self.M = _ex(dens, syms) * meas
        else:
            raise RigidError(f"{name}: mass or density required")
        self.abs_density = self.profile is not None and prof is None

    # geometric measure (length / area / volume) of the uniform body
    def measure(self) -> sp.Expr:
        d, s = self.d, self.shape
        return {
            "point": lambda: sp.Integer(1), "rod": lambda: d["L"], "ring": lambda: 2 * pi * d["R"],
            "semi_ring": lambda: pi * d["R"], "disc": lambda: pi * d["R"] ** 2,
            "annular_disc": lambda: pi * (d["R2"] ** 2 - d["R1"] ** 2), "semi_disc": lambda: pi * d["R"] ** 2 / 2,
            "solid_cylinder": lambda: pi * d["R"] ** 2 * d["L"], "hollow_cylinder": lambda: 2 * pi * d["R"] * d["L"],
            "thick_cylinder": lambda: pi * (d["R2"] ** 2 - d["R1"] ** 2) * d["L"],
            "solid_sphere": lambda: 4 * pi * d["R"] ** 3 / 3, "spherical_shell": lambda: 4 * pi * d["R"] ** 2,
            "thick_spherical_shell": lambda: 4 * pi * (d["R2"] ** 3 - d["R1"] ** 3) / 3,
            "solid_hemisphere": lambda: 2 * pi * d["R"] ** 3 / 3, "hemispherical_shell": lambda: 2 * pi * d["R"] ** 2,
            "rect_plate": lambda: d["a"] * d["b"], "cuboid": lambda: d["a"] * d["b"] * d["c"],
            "cube": lambda: d["a"] ** 3, "solid_cone": lambda: pi * d["R"] ** 2 * d["H"] / 3,
        }[s]()

    def to_world(self, x, y, z) -> sp.Matrix:
        return self.c + x * self.u + y * self.v + z * self.n


# ------------------------------------------------------------------ method A: table + theorems
def _table(shape: str, M: sp.Expr, d: dict) -> tuple[tuple, tuple]:
    """(I about the REFERENCE point along body axes (u, v, n), centroid offset from the reference (u, v, n))."""
    R = d.get("R")
    z = (0, 0, 0)
    if shape == "point":
        return (0, 0, 0), z
    if shape == "rod":
        return (0, M * d["L"] ** 2 / 12, M * d["L"] ** 2 / 12), z
    if shape in ("ring", "disc", "annular_disc"):
        if shape == "ring":
            Iz = M * R ** 2
        elif shape == "disc":
            Iz = M * R ** 2 / 2
        else:
            Iz = M * (d["R1"] ** 2 + d["R2"] ** 2) / 2
        return (Iz / 2, Iz / 2, Iz), z                          # perpendicular-axis theorem + symmetry
    if shape == "semi_ring":
        return (M * R ** 2 / 2, M * R ** 2 / 2, M * R ** 2), (0, 2 * R / pi, 0)
    if shape == "semi_disc":
        return (M * R ** 2 / 4, M * R ** 2 / 4, M * R ** 2 / 2), (0, 4 * R / (3 * pi), 0)
    if shape == "solid_cylinder":
        t = M * R ** 2 / 4 + M * d["L"] ** 2 / 12
        return (t, t, M * R ** 2 / 2), z
    if shape == "hollow_cylinder":
        t = M * R ** 2 / 2 + M * d["L"] ** 2 / 12
        return (t, t, M * R ** 2), z
    if shape == "thick_cylinder":
        q = d["R1"] ** 2 + d["R2"] ** 2
        t = M * q / 4 + M * d["L"] ** 2 / 12
        return (t, t, M * q / 2), z
    if shape == "solid_sphere":
        t = sp.Rational(2, 5) * M * R ** 2
        return (t, t, t), z
    if shape == "spherical_shell":
        t = sp.Rational(2, 3) * M * R ** 2
        return (t, t, t), z
    if shape == "thick_spherical_shell":
        t = sp.Rational(2, 5) * M * (d["R2"] ** 5 - d["R1"] ** 5) / (d["R2"] ** 3 - d["R1"] ** 3)
        return (t, t, t), z
    if shape == "solid_hemisphere":
        t = sp.Rational(2, 5) * M * R ** 2
        return (t, t, t), (0, 0, sp.Rational(3, 8) * R)
    if shape == "hemispherical_shell":
        t = sp.Rational(2, 3) * M * R ** 2
        return (t, t, t), (0, 0, R / 2)
    if shape == "rect_plate":
        iu, iv = M * d["b"] ** 2 / 12, M * d["a"] ** 2 / 12
        return (iu, iv, iu + iv), z                              # perpendicular-axis theorem
    if shape in ("cuboid", "cube"):
        a, b, c = d["a"], d["b"], d["c"]
        return (M * (b ** 2 + c ** 2) / 12, M * (a ** 2 + c ** 2) / 12, M * (a ** 2 + b ** 2) / 12), z
    if shape == "solid_cone":
        t = M * (sp.Rational(3, 20) * R ** 2 + d["H"] ** 2 / 10)    # about a diameter of the base
        return (t, t, sp.Rational(3, 10) * M * R ** 2), (0, 0, d["H"] / 4)
    raise RigidError(f"no table entry for {shape}")


def _tensor_axis(b: Body, M, diag_ref, off, P: sp.Matrix, dvec: sp.Matrix, center=None) -> sp.Expr:
    """Parallel-axis theorem (tensor form): reference -> centroid -> requested axis."""
    c = b.c if center is None else center
    Rm = sp.Matrix.hstack(b.u, b.v, b.n)
    dd = sp.Matrix(off)
    Iref = sp.diag(*diag_ref)
    Ic_body = Iref - M * (dd.dot(dd) * sp.eye(3) - dd * dd.T)
    Ic = Rm * Ic_body * Rm.T
    cw = c + Rm * dd
    rr = cw - P
    return (dvec.T * Ic * dvec)[0] + M * (rr.dot(rr) - rr.dot(dvec) ** 2)


def method_table(b: Body, P, dvec) -> tuple[sp.Expr, sp.Expr]:
    """(signed I, signed mass) from standard results."""
    if b.profile is None:
        diag, off = _table(b.shape, b.M, b.d)
        return b.sign * _tensor_axis(b, b.M, diag, off, P, dvec), b.sign * b.M
    # continuous composition of tabulated thin elements
    if b.shape == "rod":
        lo, hi = -b.d["L"] / 2, b.d["L"] / 2
        dm = b.profile
        el = lambda var: _tensor_axis(b, 1, (0, 0, 0), (0, 0, 0), P, dvec, center=b.c + var * b.u)  # noqa: E731
        var = _sr
    elif b.shape in ("disc", "annular_disc"):
        lo, hi = (0, b.d["R"]) if b.shape == "disc" else (b.d["R1"], b.d["R2"])
        dm = b.profile * 2 * pi * _r
        el = lambda var: _tensor_axis(b, 1, (var ** 2 / 2, var ** 2 / 2, var ** 2), (0, 0, 0), P, dvec)  # noqa: E731
        var = _r
    else:  # solid_sphere: shells
        lo, hi = 0, b.d["R"]
        dm = b.profile * 4 * pi * _r ** 2
        t = sp.Rational(2, 3) * _r ** 2
        el = lambda var: _tensor_axis(b, 1, (t, t, t), (0, 0, 0), P, dvec)  # noqa: E731
        var = _r
    mass_raw = sp.integrate(sp.expand(dm), (var, lo, hi))
    I_raw = sp.integrate(sp.expand(dm * el(var)), (var, lo, hi))
    if b.abs_density:
        return b.sign * sp.simplify(I_raw), b.sign * sp.simplify(mass_raw)
    return b.sign * sp.simplify(b.M * I_raw / mass_raw), b.sign * b.M


# ------------------------------------------------------------------ method B: direct integration
def _param(b: Body):
    """(world position, jacobian, [(var, lo, hi), ...]) of the body's own geometry."""
    d, s = b.d, b.shape
    c, sn = sp.cos, sp.sin
    if s == "point":
        return b.c, sp.Integer(1), []
    if s == "rod":
        return b.to_world(_sr, 0, 0), sp.Integer(1), [(_sr, -d["L"] / 2, d["L"] / 2)]
    if s in ("ring", "semi_ring"):
        R = d["R"]
        return b.to_world(R * c(_ph), R * sn(_ph), 0), R, [(_ph, 0, 2 * pi if s == "ring" else pi)]
    if s in ("disc", "annular_disc", "semi_disc"):
        lo, hi = (d["R1"], d["R2"]) if s == "annular_disc" else (0, d["R"])
        return b.to_world(_r * c(_ph), _r * sn(_ph), 0), _r, [(_r, lo, hi), (_ph, 0, pi if s == "semi_disc" else 2 * pi)]
    if s in ("solid_cylinder", "thick_cylinder"):
        lo, hi = (d["R1"], d["R2"]) if s == "thick_cylinder" else (0, d["R"])
        return (b.to_world(_r * c(_ph), _r * sn(_ph), _z), _r,
                [(_r, lo, hi), (_ph, 0, 2 * pi), (_z, -d["L"] / 2, d["L"] / 2)])
    if s == "hollow_cylinder":
        R = d["R"]
        return b.to_world(R * c(_ph), R * sn(_ph), _z), R, [(_ph, 0, 2 * pi), (_z, -d["L"] / 2, d["L"] / 2)]
    if s in ("solid_sphere", "thick_spherical_shell", "solid_hemisphere"):
        lo, hi = (d["R1"], d["R2"]) if s == "thick_spherical_shell" else (0, d["R"])
        return (b.to_world(_r * sn(_th) * c(_ph), _r * sn(_th) * sn(_ph), _r * c(_th)), _r ** 2 * sn(_th),
                [(_r, lo, hi), (_th, 0, pi / 2 if s == "solid_hemisphere" else pi), (_ph, 0, 2 * pi)])
    if s in ("spherical_shell", "hemispherical_shell"):
        R = d["R"]
        return (b.to_world(R * sn(_th) * c(_ph), R * sn(_th) * sn(_ph), R * c(_th)), R ** 2 * sn(_th),
                [(_th, 0, pi / 2 if s == "hemispherical_shell" else pi), (_ph, 0, 2 * pi)])
    x, y = sp.Dummy("x_int", real=True), sp.Dummy("y_int", real=True)
    if s == "rect_plate":
        return b.to_world(x, y, 0), sp.Integer(1), [(x, -d["a"] / 2, d["a"] / 2), (y, -d["b"] / 2, d["b"] / 2)]
    if s in ("cuboid", "cube"):
        return (b.to_world(x, y, _z), sp.Integer(1),
                [(x, -d["a"] / 2, d["a"] / 2), (y, -d["b"] / 2, d["b"] / 2), (_z, -d["c"] / 2, d["c"] / 2)])
    if s == "solid_cone":
        R, H = d["R"], d["H"]
        return (b.to_world(_r * c(_ph), _r * sn(_ph), _z), _r,
                [(_r, 0, R * (1 - _z / H)), (_ph, 0, 2 * pi), (_z, 0, H)])
    raise RigidError(f"no parametrisation for {s}")


def _integrate(f: sp.Expr, lims) -> sp.Expr:
    for var, lo, hi in lims:          # innermost first
        f = sp.integrate(sp.expand(f), (var, lo, hi))
    return sp.simplify(f)


def method_integral(b: Body, P, dvec) -> tuple[sp.Expr, sp.Expr]:
    pos, jac, lims = _param(b)
    p = pos - P
    rperp2 = sp.expand(p.dot(p) - p.dot(dvec) ** 2)
    if not lims:
        return b.sign * b.M * rperp2, b.sign * b.M
    # the profile is written in the parametrisation's own coordinate (s_ for rods, radial r_ otherwise)
    w = b.profile if b.profile is not None else sp.Integer(1)
    mass_raw = _integrate(w * jac, lims)
    I_raw = _integrate(w * jac * rperp2, lims)
    if b.abs_density:
        return b.sign * I_raw, b.sign * mass_raw
    return b.sign * sp.simplify(b.M * I_raw / mass_raw), b.sign * b.M


# ------------------------------------------------------------------ dynamics templates (derived, not asserted)
def _template(rel: dict) -> list[str]:
    """Each template is DERIVED here from Newton's laws for a rigid body, then emitted as equations."""
    t = rel.get("template")
    a_, f_, M_, I_, R_, g_, th_ = (sp.Symbol(x) for x in ("a", "f", "M", "I", "R", "g", "th"))
    al = sp.Symbol("al")
    names = {k: rel[k] for k in rel if k != "template"}
    need = {"rolling_incline": ("M", "I", "R", "g", "th"), "rolling_ke": ("M", "I", "R", "v")}.get(t, ())
    if any(k not in names for k in need):
        raise RigidError(f"template {t} needs inputs {need}")

    def emit(eqs: dict) -> list[str]:
        sub = {sp.Symbol(k): sp.Symbol(v) for k, v in names.items()}
        return [f"{sp.sstr(sp.Symbol(k).subs(sub))} = {sp.sstr(v.subs(sub, simultaneous=True))}"
                for k, v in eqs.items() if k in names]

    if t == "rolling_incline":
        # M a = M g sin(th) - f ; I alpha = f R ; a = alpha R  (rolling without slipping, friction up the slope)
        sol = sp.solve([M_ * a_ - (M_ * g_ * sp.sin(th_) - f_), I_ * al - f_ * R_, a_ - al * R_], [a_, f_, al], dict=True)[0]
        return emit({"a": sp.simplify(sol[a_]), "f": sp.simplify(sol[f_])})
    if t == "rolling_ke":
        v_ = sp.Symbol("v")
        # KE = translational + rotational, omega = v/R
        return emit({"KEt": M_ * v_ ** 2 / 2, "KEr": I_ * (v_ / R_) ** 2 / 2,
                     "KE": M_ * v_ ** 2 / 2 + I_ * (v_ / R_) ** 2 / 2})
    raise RigidError(f"unknown template {t!r}")


# ------------------------------------------------------------------ main
def compute_inertia(formal: dict) -> tuple[dict, dict, list[VerificationRecord]]:
    """{name: I expr}, {mass name: expr}, records. Raises on structural errors."""
    syms = _syms(formal)
    numeric = {}
    bodies = {n: Body(n, s, syms, numeric) for n, s in formal.get("bodies", {}).items()}
    recs, out, masses = [], {}, {}
    for name, spec in formal.get("inertia", {}).items():
        ax = spec["axis"]
        P = _vec(ax.get("point", [0, 0, 0]), syms)
        dvec = _unit(_vec(ax["dir"], syms))
        parts = spec["bodies"]
        unknown = [p for p in parts if p not in bodies]
        if unknown:
            raise RigidError(f"inertia {name}: unknown bodies {unknown}")
        A = sum((method_table(bodies[p], P, dvec)[0] for p in parts), sp.Integer(0))
        B = sum((method_integral(bodies[p], P, dvec)[0] for p in parts), sp.Integer(0))
        A, B = sp.simplify(A), sp.simplify(B)
        agree = sp.simplify(A - B) == 0
        recs.append(VerificationRecord(
            check_id=f"rigid.inertia.{name}", status=CheckStatus.EXACT_CHECKED if agree else CheckStatus.FAILED,
            method="standard table + parallel/perpendicular-axis theorems vs direct symbolic integration of r_perp^2 dm",
            tool=TOOL, result=(f"{name} = {A} (both methods)" if agree else f"{name}: table {A} != integral {B}"),
            data={"table": str(A), "integral": str(B), "parts": parts}))
        out[name] = A
    for name, parts in formal.get("masses", {}).items():
        out_m = sp.Integer(0)
        for p in parts:
            b = bodies[p]
            m = b.sign * b.M if b.M is not None else method_integral(b, sp.zeros(3, 1), sp.Matrix([0, 0, 1]))[1]
            out_m += m
        masses[name] = sp.simplify(out_m)
    return out, masses, recs


def compute_calculus(formal: dict, inertia: dict) -> tuple[dict, list[VerificationRecord]]:
    names = list(formal.get("knowns", {})) + list(formal.get("unknowns", {})) + list(inertia)
    out, recs = {}, []
    for name, spec in formal.get("calculus", {}).items():
        var = spec["var"]
        syms = {n: sp.Symbol(n, real=True) for n in names + [var] + list(out)}
        x = syms[var]
        f = parse(spec["integral"] if "integral" in spec else spec["derivative"], syms)
        f = f.subs({syms[k]: v for k, v in out.items()})
        f = f.subs({syms[k]: v.subs({z: sp.Symbol(str(z), real=True) for z in v.free_symbols})
                    for k, v in inertia.items()})
        for k, v in spec.get("subs", {}).items():
            f = f.subs(syms[k], parse(v, syms))
        if "integral" in spec:
            lo, hi = parse(str(spec["lower"]), syms), parse(str(spec["upper"]), syms)
            res = sp.simplify(sp.integrate(sp.expand(f), (x, lo, hi)))
            u = sp.Dummy("u", real=True)
            g = sp.integrate(sp.expand(f), (x, lo, u))
            ok = sp.simplify(sp.diff(g, u) - f.subs(x, u)) == 0 and sp.simplify(g.subs(u, lo)) == 0 \
                and sp.simplify(g.subs(u, hi) - res) == 0
            how = "exact antiderivative; check d/du of F(u) = integrand(u), F(lower) = 0"
        else:
            res = sp.simplify(sp.diff(f, x))
            h = sp.Dummy("h", positive=True)
            dq = sp.limit(sp.simplify((f.subs(x, x + h) - f) / h), h, 0)
            ok = sp.simplify(dq - res) == 0
            how = "symbolic derivative vs limit of the difference quotient"
        recs.append(VerificationRecord(check_id=f"rigid.calculus.{name}",
                                       status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                       method=how, tool=TOOL, result=f"{name} = {res}" + ("" if ok else " (cross-check failed)")))
        out[name] = res
    return out, recs


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001
    out = EngineResult()
    st: dict = {}

    def _run():
        st["I"], st["m"], st["recs"] = compute_inertia(formal)
        return VerificationRecord(check_id="rigid.structure", status=CheckStatus.EXACT_CHECKED,
                                  method="body schema + exact geometry", tool=TOOL,
                                  result=f"{len(formal.get('bodies', {}))} bodies, {len(st['I'])} inertia value(s)")

    def _calc(st_):
        st_["C"], st_["crecs"] = compute_calculus(formal, st_["I"])
        return VerificationRecord(check_id="rigid.calculus", status=CheckStatus.EXACT_CHECKED, method="sympy",
                                  tool=TOOL, result=f"{len(st_['C'])} calculus definition(s)")

    out.records.append(guarded("rigid.structure", _run, seconds=60))
    if "I" not in st:
        return out
    out.records += st["recs"]
    if any(r.status != CheckStatus.EXACT_CHECKED for r in st["recs"]):
        return out
    if formal.get("calculus"):
        out.records.append(guarded("rigid.calculus", lambda: _calc(st), seconds=60))
        out.records += st.get("crecs", [])
        if "C" not in st or any(r.status != CheckStatus.EXACT_CHECKED for r in st["crecs"]):
            return out
    else:
        st["C"] = {}
    sysf = {k: copy.deepcopy(v) for k, v in formal.items()
            if k not in ("bodies", "inertia", "masses", "relations", "kind")}
    sysf["kind"] = "equation_system"
    sysf.setdefault("unknowns", {})
    eqs = list(sysf.get("equations", []))
    for name, expr in st["I"].items():
        sysf["unknowns"].setdefault(name, {"unit": "kg*m^2", "domain": "real"})
        eqs.append(f"{name} = {sp.sstr(expr)}")
    for name, expr in st["m"].items():
        sysf["unknowns"].setdefault(name, {"unit": "kg", "domain": "real"})
        eqs.append(f"{name} = {sp.sstr(expr)}")
    for name, expr in st["C"].items():
        if name not in sysf["unknowns"]:
            raise RigidError(f"calculus result {name} must be declared as an unknown (with its unit)")
        eqs.append(f"{name} = {sp.sstr(expr)}")
    for rel in formal.get("relations", []):
        eqs += _template(rel)
    sysf["equations"] = eqs
    if "target" not in sysf:
        sysf["target"] = next(iter(st["I"]))
    s = solve_system(sysf)
    out.records += s.records
    out.value, out.unit = s.value, s.unit
    out.steps = ([f"{r.result}" for r in st["recs"]] + [f"Equation {i + 1}: {e}" for i, e in enumerate(eqs)]
                 + [f"{sysf['target']} = {s.value} {s.unit}"])
    return out
