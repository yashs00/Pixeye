"""Rotational Motion families (original questions; patterns modelled on bank questions, never copied).

Every correct answer is a rigid_body / equation_system formal: moments of inertia are computed twice by the
engine (standard table + axis theorems vs direct integration), dynamics by exact solving. Every wrong option is
the engine-verified answer of a NAMED student mistake, written as its own formal (wrong table entry, missing or
doubled parallel-axis term, perpendicular-axis misuse, energy instead of momentum conservation, ...).
"""
from __future__ import annotations

import random
import re
from decimal import Decimal, getcontext

import sympy as sp

from cqse.core.problem import Subject
from cqse.generation.framework import Family, Mistake

CH, SUBJ = "Rotational Motion", Subject.PHYSICS
getcontext().prec = 40

K = lambda v, u="": {"value": str(v), "unit": u}  # noqa: E731
S = lambda u="": {"value": "symbolic", "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
G = {"g": K("10", "m/s^2")}


# ------------------------------------------------------------------ formal helpers
def body(shape, mass=None, center=("0", "0", "0"), axis=(0, 0, 1), u=None, sign=1, density=None, **dims):
    b = {"shape": shape, "dims": dims, "center": [str(c) for c in center], "axis": list(axis), "sign": sign}
    if mass is not None:
        b["mass"] = mass
    if density is not None:
        b["density"] = density
    if u is not None:
        b["u"] = list(u)
    return b


def ax(bodies, point=("0", "0", "0"), d=(0, 0, 1)):
    return {"bodies": list(bodies), "axis": {"point": [str(c) for c in point], "dir": list(d)}}


def rb(knowns, bodies, inertia, unknowns, equations, target, model=(), **extra):
    return {"kind": "rigid_body", "knowns": knowns, "bodies": bodies, "inertia": inertia, "unknowns": unknowns,
            "equations": equations, "target": target, "model": list(model), **extra}


# ------------------------------------------------------------------ display helpers
def fmt(v, sig: int = 4) -> str:
    """Exact terminating decimal when possible, else 4 significant figures (rational) or exact LaTeX (surd)."""
    v = sp.nsimplify(sp.sympify(v))
    if v.is_Rational:
        q = int(v.q)
        for f in (2, 5):
            while q % f == 0:
                q //= f
        if q == 1:
            return format((Decimal(int(v.p)) / Decimal(int(v.q))).normalize(), "f")
        s = f"{float(v):.{sig}g}"
        return format(Decimal(s), "f") if "e" in s else s
    return sp.latex(sp.radsimp(v))


def val(v, unit: str) -> str:
    return f"${fmt(v)}\\ \\mathrm{{{unit}}}$"


def coef(v, sym: str) -> str:
    v = sp.nsimplify(sp.sympify(v))
    if v == 1:
        return f"${sym}$"
    return f"${sp.latex(v)}\\,{sym}$"


def frac(v) -> str:
    return f"${sp.latex(sp.nsimplify(sp.sympify(v)))}$"


# ------------------------------------------------------------------ shared tables
NAME = {"disc": "thin uniform circular disc", "ring": "thin uniform circular ring",
        "solid_sphere": "uniform solid sphere", "spherical_shell": "thin hollow sphere (spherical shell)",
        "rod": "thin uniform rod", "rect_plate": "thin uniform square plate",
        "solid_cylinder": "uniform solid cylinder", "hollow_cylinder": "thin-walled hollow cylinder"}
ALT = {"disc": "ring", "ring": "disc", "solid_sphere": "spherical_shell", "spherical_shell": "solid_sphere",
       "solid_cylinder": "hollow_cylinder", "hollow_cylinder": "solid_cylinder"}
KCM = {"ring": 1, "disc": sp.Rational(1, 2), "solid_cylinder": sp.Rational(1, 2), "hollow_cylinder": 1,
       "solid_sphere": sp.Rational(2, 5), "spherical_shell": sp.Rational(2, 3)}
ROUND = list(KCM)


def round_body(shape, mass="M", R="R", **kw):
    """Round body of radius R with its symmetry axis along z (cylinders: length = R, irrelevant to I_z)."""
    if shape in ("solid_cylinder", "hollow_cylinder"):
        return body(shape, mass, R=R, L=R, **kw)
    return body(shape, mass, R=R, **kw)


def _ok_dec(x, places=2) -> bool:
    x = sp.nsimplify(x)
    return x.is_Rational and (x * 10 ** places).is_integer


def _s(x) -> str:
    """Exact rational -> short decimal string for stems/params."""
    return fmt(sp.nsimplify(x))


# ================================================================== 1. axis theorems: k in I = k M X^2
def _dims(shape):
    return {"rod": {"L": "L"}, "rect_plate": {"a": "a", "b": "a"}}.get(shape, {"R": "R"})


def _sym(shape):
    return {"rod": "L", "rect_plate": "a"}.get(shape, "R")


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
O3 = ("0", "0", "0")
# shape, axis text, point, dir, shift (|parallel-axis distance|), wrong point, swapped centroidal dir (lamina)
AXIS_CASES = [
    ("disc", "a tangent lying in the plane of the disc", ("R", 0, 0), Y, "R", ("2*R", 0, 0), Z),
    ("disc", "an axis perpendicular to its plane passing through a point on its rim", ("R", 0, 0), Z, "R",
     ("2*R", 0, 0), Y),
    ("disc", "one of its diameters", O3, X, None, None, Z),
    ("ring", "a tangent lying in the plane of the ring", ("R", 0, 0), Y, "R", ("2*R", 0, 0), Z),
    ("ring", "an axis perpendicular to its plane passing through a point on the ring", ("R", 0, 0), Z, "R",
     ("2*R", 0, 0), Y),
    ("ring", "one of its diameters", O3, X, None, None, Z),
    ("solid_sphere", "a tangent to its surface", ("R", 0, 0), Z, "R", ("2*R", 0, 0), None),
    ("spherical_shell", "a tangent to its surface", ("R", 0, 0), Z, "R", ("2*R", 0, 0), None),
    ("rod", "an axis perpendicular to the rod through one of its ends", ("L/2", 0, 0), Z, "L/2", ("L", 0, 0),
     None),
    ("rod", "an axis perpendicular to the rod through a point at distance $L/3$ from one end", ("L/6", 0, 0), Z,
     "L/6", ("L/3", 0, 0), None),
    ("rod", "an axis perpendicular to the rod through a point at distance $L/4$ from one end", ("L/4", 0, 0), Z,
     "L/4", ("3*L/4", 0, 0), None),
    ("rect_plate", "one of its edges", (0, "a/2", 0), X, "a/2", (0, "a", 0), Z),
    ("rect_plate", "an axis perpendicular to its plane through one of its corners", ("a/2", "a/2", 0), Z,
     "a/sqrt(2)", ("a", 0, 0), X),
]


def _kform(shape, pt, d, extra_eq=None, inertia_extra=None, dims=None):
    x = _sym(shape)
    kn = {"M": S("kg"), x: S("m")}
    bd = {"b": body(shape, "M", **(dims or _dims(shape)))}
    ine = {"I": ax(["b"], pt, d)}
    ine.update(inertia_extra or {})
    eqs = extra_eq or [f"I = k*M*{x}**2"]
    return rb(kn, bd, ine, {"k": U("", "positive")}, eqs, "k",
              ["uniform body; I = k M X^2 with X the stated length"])


def axis_theorems() -> Family:
    def sample(rng):
        return {"case": rng.randrange(len(AXIS_CASES))}

    def formal(p):
        sh, _, pt, d, *_ = AXIS_CASES[p["case"]]
        return _kform(sh, pt, d)

    def stem(p):
        sh, txt, *_ = AXIS_CASES[p["case"]]
        x = _sym(sh)
        size = {"rod": "length $L$", "rect_plate": "side $a$"}.get(sh, "radius $R$")
        return (f"<p>A {NAME[sh]} has mass $M$ and {size}. Its moment of inertia about {txt} is:</p>")

    def mistakes(p):
        sh, _, pt, d, shift, wpt, swap = AXIS_CASES[p["case"]]
        x = _sym(sh)
        out = []
        if sh in ALT:
            out.append(Mistake("WRONG_TABLE_ENTRY", _kform(ALT[sh], pt, d),
                               f"Students recall the standard result of a {NAME[ALT[sh]]} instead.",
                               f"A {NAME[sh]} has a different mass distribution, so a different centroidal MOI."))
        if shift:
            out.append(Mistake("PARALLEL_AXIS_TERM_FORGOTTEN", _kform(sh, O3, d),
                               "Students quote the centroidal result and forget the axis is shifted.",
                               f"The axis is at distance {shift} from the centre: add M·({shift})²."))
        if swap is not None:
            sh_eq = [f"k*M*{x}**2 = Ic + M*({shift})**2"] if shift else [f"k*M*{x}**2 = Ic"]
            out.append(Mistake("PERPENDICULAR_AXIS_MISUSE",
                               _kform(sh, pt, d, sh_eq, {"Ic": ax(["b"], O3, swap)}),
                               "Students start from the centroidal MOI about the wrong orientation (in-plane vs "
                               "perpendicular to the plane).",
                               "For a lamina the in-plane and normal centroidal axes differ by the "
                               "perpendicular-axis theorem; use the centroidal axis parallel to the asked axis."))
        if shift:
            out.append(Mistake("WRONG_SHIFT_DISTANCE", _kform(sh, wpt, d),
                               "Students take the full diameter/length (or the distance from the end) as the "
                               "parallel-axis shift.",
                               "The shift in I = I_cm + Md² is the distance of the axis from the centre of mass."))
            out.append(Mistake("PARALLEL_TERM_DOUBLED",
                               _kform(sh, pt, d, [f"k*M*{x}**2 = Ic + 2*M*({shift})**2"],
                                      {"Ic": ax(["b"], O3, d)}),
                               "Students add the Md² term twice (once for each side/tangent).",
                               "The parallel-axis theorem adds Md² exactly once."))
        else:
            out.append(Mistake("PERPENDICULAR_AXIS_INVERTED",
                               _kform(sh, pt, d, [f"k*M*{x}**2 = 2*Iz"], {"Iz": ax(["b"], O3, Z)}),
                               "Students write I_axis = I_x + I_y with the wrong roles, doubling I_z.",
                               "Perpendicular-axis theorem: I_z = I_x + I_y, so an in-plane axis gets I_z/2."))
            if sh != "rect_plate":
                out.append(Mistake("DIAMETER_USED_AS_RADIUS", _kform(sh, pt, d, dims={"R": "2*R"}),
                                   "Students put the diameter into the formula in place of the radius.",
                                   "The standard results are written in terms of the radius R."))
            out.append(Mistake("DIAMETER_TREATED_AS_ROD",
                               rb({"M": S("kg"), "R": S("m")}, {"b": body("rod", "M", u=Y, L="2*R")},
                                  {"I": ax(["b"], O3, X)}, {"k": U("", "positive")}, ["I = k*M*R**2"], "k",
                                  ["mass imagined spread along a rod of length 2R across the axis"]),
                               "Students picture the body as a rod of length 2R turning about its centre.",
                               "Mass at every distance up to R from the diameter is distributed over an area, "
                               "not along a line."))
        return out

    def explain(p, v):
        sh, txt, pt, d, shift, *_ = AXIS_CASES[p["case"]]
        x = _sym(sh)
        how = (f"Centroidal MOI about the parallel axis, plus $M({sp.latex(sp.sympify(shift))})^2$ "
               f"(parallel-axis theorem)." if shift else
               "Perpendicular-axis theorem: for a lamina $I_z = I_x + I_y$, and by symmetry the in-plane axes "
               "share $I_z$ equally.")
        return f"<p>{how}</p><p>$I = {sp.latex(v)}\\,M{x}^2$ (checked by direct integration).</p>"

    return Family(id="rot.axis_theorems", subject=SUBJ, chapter=CH, topic="Moment of Inertia",
                  difficulty="EASY", sample=sample, formal=formal, stem=stem, mistakes=mistakes,
                  display=lambda v, p: coef(v, "M" + _sym(AXIS_CASES[p["case"]][0]) + "^2"), explain=explain,
                  modelled_on=["1l568o323", "m9e5j2f6", "2p0E2TIZzrOYy5YhX67k9k2k5djt7ib"]).register()


# ================================================================== 2. disc with a circular hole
HOLE_AXES = {"perp_O": ("an axis through $O$ perpendicular to the plane of the disc", Z),
             "diam_OC": ("the diameter of the original disc that passes through $C$", X),
             "diam_perp": ("the diameter of the original disc perpendicular to $OC$", Y)}


def _hole_form(p, hole_mass=None, hole_center=None, own=True, sign=-1, skip_hole=False):
    n = p["n"]
    c = hole_center or (p["d"], "0", "0")
    bd = {"disc": body("disc", "M", R="R")}
    if not skip_hole:
        if own:
            hb = body("disc", hole_mass, center=c, sign=sign, R=f"R/{n}") if hole_mass else \
                body("disc", density="M/(pi*R**2)", center=c, sign=sign, R=f"R/{n}")
        else:
            hb = body("point", hole_mass or f"M/{n * n}", center=c, sign=sign)
        bd["hole"] = hb
    return rb({"M": S("kg"), "R": S("m")}, bd, {"I": ax(list(bd), O3, HOLE_AXES[p["axis"]][1])},
              {"k": U("", "positive")}, ["I = k*M*R**2"], "k",
              ["uniform lamina: removed mass = M x (area ratio)", "M = mass of the full disc before cutting"])


def removed_disc() -> Family:
    def sample(rng):
        n = rng.choice([2, 3, 4])
        d = rng.choice(["R/2", f"R - R/{n}"]) if n != 2 else "R/2"
        if n == 4 and rng.random() < 0.3:
            d = "R/4"
        return {"n": n, "d": d, "axis": rng.choice(list(HOLE_AXES))}

    def formal(p):
        return _hole_form(p)

    def stem(p):
        dtx = {"R/2": "R/2", "R/4": "R/4"}.get(p["d"], f"{p['n'] - 1}R/{p['n']}")
        touch = " (so the hole touches the rim)" if p["d"] == f"R - R/{p['n']}" else ""
        return (f"<p>A thin uniform circular disc of mass $M$ and radius $R$ has centre $O$. A circular hole of "
                f"radius $R/{p['n']}$ is cut from it, the centre $C$ of the hole being at distance ${dtx}$ from "
                f"$O${touch}. Here $M$ is the mass of the complete disc before the hole was cut. The moment of "
                f"inertia of the remaining part about {HOLE_AXES[p['axis']][0]} is:</p>")

    def mistakes(p):
        n = p["n"]
        return [
            Mistake("REMOVED_PART_OWN_MOI_FORGOTTEN", _hole_form(p, own=False),
                    "Students subtract only m·OC² for the hole, treating it as a particle at C.",
                    "The removed disc has its own centroidal MOI that must also be subtracted."),
            Mistake("REMOVED_PART_NOT_SHIFTED", _hole_form(p, hole_center=O3),
                    "Students subtract the hole's MOI about its own centre and forget the parallel-axis shift.",
                    "The hole's MOI must be taken about the given axis: I_C + m·(distance)²."),
            Mistake("MASS_PROPORTIONAL_TO_RADIUS", _hole_form(p, hole_mass=f"M/{n}"),
                    f"Students take the removed mass as M/{n} (ratio of radii).",
                    f"Mass of a uniform lamina scales with area: m = M/{n * n}."),
            Mistake("REMOVED_PART_ADDED", _hole_form(p, sign=1),
                    "Students add the MOI of the removed part instead of subtracting it.",
                    "The remaining body = full disc MINUS the removed disc."),
            Mistake("HOLE_IGNORED", _hole_form(p, skip_hole=True),
                    "Students quote the MOI of the complete disc.",
                    "The hole removes mass, so the MOI must decrease."),
        ]

    def explain(p, v):
        n = p["n"]
        return (f"<p>Removed mass $m = M/{n * n}$ (area ratio). $I = I_{{disc}} - I_{{hole}}$, where "
                f"$I_{{hole}}$ is the hole's centroidal MOI about the parallel axis plus $m\\cdot$(distance of "
                f"$C$ from the axis)$^2$.</p><p>$I = {sp.latex(v)}\\,MR^2$.</p>")

    return Family(id="rot.removed_disc", subject=SUBJ, chapter=CH, topic="Moment of Inertia",
                  difficulty="HARD", sample=sample, formal=formal, stem=stem, mistakes=mistakes,
                  display=lambda v, p: coef(v, "MR^2"), explain=explain,
                  modelled_on=["DTYVpqLOj6guqgSjz4IBq", "1jKxr2kiGFuwVxRZ"]).register()


# ================================================================== 3. rod + attached body
def _comp_form(p, shape=None, rod_pt="0", own=True, centre="L + rs"):
    shape = shape or p["shape"]
    kn = {"m1": K(p["m1"], "kg"), "m2": K(p["m2"], "kg"), "L": K(p["L"], "cm"), "rs": K(p["r"], "cm")}
    bd = {"rod": body("rod", "m1", center=("L/2", 0, 0), u=X, L="L")}
    bd["b"] = body(shape, "m2", center=(centre, 0, 0), R="rs") if own else body("point", "m2", center=(centre, 0, 0))
    pt = (rod_pt, 0, 0)
    return rb(kn, bd, {"I": ax(["rod", "b"], pt, Z)}, {"J": U("kg*m^2", "positive")}, ["J = I"], "J",
              ["rod along OA; attached body's centre on OA produced; axis through O perpendicular to the rod "
               "(and to the plane of a disc/ring)"])


def composite() -> Family:
    def sample(rng):
        return {"shape": rng.choice(["solid_sphere", "disc", "ring"]), "m1": rng.choice([1, 2, 3, 6]),
                "m2": rng.choice([1, 2, 4, 5]), "L": rng.choice([30, 40, 50, 60, 80, 90]),
                "r": rng.choice([5, 10, 15, 20])}

    def stem(p):
        what = {"solid_sphere": f"a uniform solid sphere of mass {p['m2']} kg and radius {p['r']} cm",
                "disc": f"a thin uniform disc of mass {p['m2']} kg and radius {p['r']} cm, lying in the plane of "
                        f"rotation,",
                "ring": f"a thin uniform ring of mass {p['m2']} kg and radius {p['r']} cm, lying in the plane of "
                        f"rotation,"}[p["shape"]]
        return (f"<p>A thin uniform rod $OA$ has mass {p['m1']} kg and length {p['L']} cm. {what[0].upper() + what[1:]} "
                f"is rigidly attached at the end $A$ so that its centre lies on the line $OA$ produced, at a distance "
                f"of {p['L'] + p['r']} cm from $O$. The moment of inertia of the system about an axis through $O$ "
                f"perpendicular to the rod (and to the plane of rotation) is:</p>")

    def mistakes(p):
        out = [Mistake("ATTACHED_BODY_OWN_MOI_FORGOTTEN", _comp_form(p, own=False),
                       "Students treat the attached body as a particle at its centre.",
                       "An extended body has its own centroidal MOI, added to m·d² by the parallel-axis theorem."),
               Mistake("BODY_CENTRE_TAKEN_AT_ROD_END", _comp_form(p, centre="L"),
                       "Students take the body's distance from O as the rod length L.",
                       "The body's centre is at L + r from O, not at the rod's end."),
               Mistake("ROD_MOI_ABOUT_CENTRE", _rod_centre_form(p),
                       "Students use ML²/12 for the rod even though the axis passes through its end.",
                       "About an end, a rod has I = ML²/3."),
               Mistake("WRONG_TABLE_ENTRY", _comp_form(p, shape=ALT.get(p["shape"], "spherical_shell")),
                       "Students recall the MOI of a different body (sphere vs shell, disc vs ring).",
                       "Use the standard result of the body actually attached.")]
        return out

    def explain(p, v):
        own = {"solid_sphere": "\\tfrac25 m_2 r^2", "disc": "\\tfrac12 m_2 r^2", "ring": "m_2 r^2"}[p["shape"]]
        return (f"<p>$I = \\tfrac13 m_1L^2 + {own} + m_2(L+r)^2$ with $L = {p['L'] / 100:g}$ m, "
                f"$r = {p['r'] / 100:g}$ m.</p><p>$I = {fmt(v)}$ kg m².</p>")

    return Family(id="rot.composite_rod_body", subject=SUBJ, chapter=CH, topic="Moment of Inertia",
                  difficulty="MEDIUM", sample=sample, formal=_comp_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: val(v, "kg\\,m^2"), explain=explain,
                  modelled_on=["1uFXUrAa9gukbiy84h4lE", "BE7hgZymN0E2d9uhFNjgy2xukf6jrqfg"]).register()


def _rod_centre_form(p):
    """Mistake: rod's MOI taken about its centre (ML^2/12), attached body done correctly about O."""
    kn = {"m1": K(p["m1"], "kg"), "m2": K(p["m2"], "kg"), "L": K(p["L"], "cm"), "rs": K(p["r"], "cm")}
    bd = {"rod": body("rod", "m1", u=X, L="L"), "b": body(p["shape"], "m2", center=("L + rs", 0, 0), R="rs")}
    return rb(kn, bd, {"Ir": ax(["rod"], O3, Z), "Ib": ax(["b"], O3, Z)}, {"J": U("kg*m^2", "positive")},
              ["J = Ir + Ib"], "J", ["rod MOI taken about its own centre (mistake)"])


# ================================================================== 4. radius of gyration of particle systems
SQ = {"A": ("0", "0"), "B": ("a", "0"), "C": ("a", "a"), "D": ("0", "a")}
TR = {"A": ("0", "0"), "B": ("a", "0"), "C": ("a/2", "sqrt(3)*a/2")}
GYR = {  # figure, axis text, point, dir
    "sq_perpA": ("square", "an axis through $A$ perpendicular to the plane of the square", ("0", "0", "0"), Z),
    "sq_AB": ("square", "the side $AB$", ("0", "0", "0"), X),
    "sq_BD": ("square", "the diagonal $BD$", ("a", "0", "0"), (-1, 1, 0)),
    "sq_perpO": ("square", "an axis through the centre of the square perpendicular to its plane",
                 ("a/2", "a/2", "0"), Z),
    "sq_mid": ("square", "the line joining the mid-points of $AB$ and $CD$", ("a/2", "0", "0"), Y),
    "tr_perpA": ("triangle", "an axis through $A$ perpendicular to the plane of the triangle", ("0", "0", "0"), Z),
    "tr_AB": ("triangle", "the side $AB$", ("0", "0", "0"), X),
    "tr_perpG": ("triangle", "an axis through the centroid perpendicular to the plane of the triangle",
                 ("a/2", "sqrt(3)*a/6", "0"), Z),
    "tr_median": ("triangle", "the median through $C$", ("a/2", "0", "0"), Y),
}
MASS_PAT = {"equal": ["m", "m", "m", "m"], "graded": ["m", "2*m", "3*m", "4*m"]}


def _gyr_geom(p):
    fig, _, pt, d = GYR[p["axis"]]
    pts = SQ if fig == "square" else TR
    masses = MASS_PAT[p["mass"]][:len(pts)]
    a = sp.Symbol("a", positive=True)
    P = sp.Matrix([sp.sympify(c, locals={"a": a}) for c in pt])
    dv = sp.Matrix(d) / sp.sqrt(sum(x * x for x in d))
    dist = {}
    for k, (x, y) in pts.items():
        r = sp.Matrix([sp.sympify(x, locals={"a": a}), sp.sympify(y, locals={"a": a}), 0]) - P
        dist[k] = sp.simplify(sp.sqrt((r - r.dot(dv) * dv).dot(r - r.dot(dv) * dv)))
    return pts, masses, dist


def _gyr_form(p, eq, extra_masses=None):
    pts, masses, _ = _gyr_geom(p)
    _, _, pt, d = GYR[p["axis"]]
    bd = {k: body("point", m, center=(x, y, "0")) for (k, (x, y)), m in zip(pts.items(), masses)}
    ms = {"Mt": list(bd)}
    ms.update(extra_masses or {})
    return rb({"m": S("kg"), "a": S("m")}, bd, {"I": ax(list(bd), pt, d)}, {"x": U("", "positive")}, [eq], "x",
              ["particles at the vertices; light rigid frame", "radius of gyration k = x a with I = M_total k^2"],
              masses=ms)


def gyration() -> Family:
    def sample(rng):
        return {"axis": rng.choice(list(GYR)), "mass": rng.choice(["equal", "equal", "graded"])}

    def formal(p):
        return _gyr_form(p, "I = Mt*(x*a)**2")

    def stem(p):
        fig, txt, *_ = GYR[p["axis"]]
        pts, masses, _ = _gyr_geom(p)
        shape = "a square $ABCD$" if fig == "square" else "an equilateral triangle $ABC$"
        if p["mass"] == "equal":
            ms = f"{'Four' if fig == 'square' else 'Three'} particles, each of mass $m$, are"
        else:
            ms = "Particles of masses " + ", ".join(f"${m.replace('*', '')}$" for m in masses) + \
                 f" are placed at " + ", ".join(f"${k}$" for k in pts) + " respectively, i.e."
        return (f"<p>{ms} placed at the vertices of {shape} of side $a$ (held by a light rigid frame). The radius "
                f"of gyration of the system about {txt} is:</p>")

    def mistakes(p):
        pts, masses, dist = _gyr_geom(p)
        on_axis = [k for k in pts if dist[k] == 0]
        off = [k for k in pts if dist[k] != 0]
        mean = " + ".join(f"({m})*({sp.sstr(dist[k])})" for k, m in zip(pts, masses) if dist[k] != 0)
        out = [Mistake("SQUARE_ROOT_FORGOTTEN", _gyr_form(p, "I = Mt*x*a**2"),
                       "Students write k = I/M instead of k = √(I/M).",
                       "Radius of gyration is defined by I = M k², so k = √(I/M).")]
        if on_axis:
            out.append(Mistake("AXIS_PARTICLES_DROPPED_FROM_MASS",
                               _gyr_form(p, "I = Moff*(x*a)**2", {"Moff": off}),
                               "Students drop particles lying on the axis from the total mass as well.",
                               "Particles on the axis add nothing to I but still count in the total mass M."))
        out.append(Mistake("MEAN_DISTANCE_USED", _gyr_form(p, f"x*a*Mt = {mean}"),
                           "Students take k as the (mass-weighted) average distance from the axis.",
                           "k is the root-mean-square distance, not the mean distance."))
        _, _, apt, _ = GYR[p["axis"]]
        a_ = sp.Symbol("a", positive=True)
        P0 = [sp.sympify(c, locals={"a": a_}) for c in apt]
        rad = []
        for (k, (x0, y0)), m in zip(pts.items(), masses):
            d2 = sp.simplify((sp.sympify(x0, locals={"a": a_}) - P0[0]) ** 2 +
                             (sp.sympify(y0, locals={"a": a_}) - P0[1]) ** 2)
            if d2 != 0:
                rad.append(f"({m})*({sp.sstr(d2)})")
        out.append(Mistake("DISTANCE_FROM_POINT_NOT_AXIS", _gyr_form(p, f"Mt*(x*a)**2 = {' + '.join(rad)}"),
                           "Students measure each particle's distance from a point on the axis instead of its "
                           "perpendicular distance from the axis line.",
                           "Moment of inertia uses the perpendicular distance from the axis."))
        out.append(Mistake("SINGLE_PARTICLE_MASS", _gyr_form(p, "I = m*(x*a)**2"),
                           "Students divide I by the mass of one particle instead of the total mass.",
                           "k² = I / (total mass of the system)."))
        return out

    def explain(p, v):
        pts, masses, dist = _gyr_geom(p)
        terms = " + ".join(f"{m.replace('*', '')}\\,({sp.latex(dist[k])})^2" for k, m in zip(pts, masses))
        return (f"<p>Perpendicular distances from the axis give $I = {terms}$. With $I = M_{{total}} k^2$: "
                f"$k = {sp.latex(v)}\\,a$.</p>")

    return Family(id="rot.gyration_particles", subject=SUBJ, chapter=CH, topic="Radius of Gyration",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes,
                  display=lambda v, p: coef(v, "a"), explain=explain,
                  modelled_on=["WH2jIqhtfbspNMF1", "aIqhqOdyMLkueyaCW7jgy2xukf3vyhuw"]).register()


# ================================================================== 5. rolling: speed at the bottom (numerical)
def _roll_v_form(p, shape=None, eq=None, h="h"):
    shape = shape or p["shape"]
    kn = {"M": K(p["M"], "kg"), "R": K(p["R"], "cm"), "h": K(p["h"], "m"), **G}
    return rb(kn, {"b": round_body(shape)}, {"I": ax(["b"])}, {"v": U("m/s", "positive")},
              [eq or f"M*g*{h} = M*v**2/2 + I*(v/R)**2/2"], "v",
              ["released from rest; rolls without slipping (static friction does no work)",
               "energy conservation from top to bottom"])


def rolling_speed() -> Family:
    def sample(rng):
        while True:
            sh, v = rng.choice(ROUND), rng.randint(2, 14)
            h = sp.Integer(v * v) * (1 + KCM[sh]) / 20
            if _ok_dec(h) and sp.Rational(1, 4) <= h <= 12:
                return {"shape": sh, "v": v, "h": _s(h), "M": rng.choice([1, 2, 3, 5]),
                        "R": rng.choice([5, 10, 15, 20])}

    def formal(p):
        return _roll_v_form(p)

    def stem(p):
        return (f"<p>A {NAME[p['shape']]} of mass {p['M']} kg and radius {p['R']} cm is released from rest at the "
                f"top of a rough inclined plane of inclination 30° and vertical height {p['h']} m. It rolls down "
                f"without slipping. Taking $g = 10\\ \\mathrm{{m\\,s^{{-2}}}}$, the speed (in m/s) of its centre "
                f"when it reaches the bottom is ______.</p>")

    def mistakes(p):
        return [Mistake("ROTATION_IGNORED", _roll_v_form(p, eq="M*g*h = M*v**2/2"),
                        "Students use v = √(2gh), as for a sliding block.", "Part of the energy goes into rotation."),
                Mistake("WRONG_TABLE_ENTRY", _roll_v_form(p, shape=ALT[p["shape"]]),
                        "Students use the MOI of a different body.", "Use this body's own I."),
                Mistake("SLANT_LENGTH_AS_HEIGHT", _roll_v_form(p, h="2*h"),
                        "Students use the length of the incline (2h at 30°) as the drop in height.",
                        "Potential energy depends on the vertical height h."),
                Mistake("ROTATIONAL_KE_ONLY", _roll_v_form(p, eq="M*g*h = I*(v/R)**2/2"),
                        "Students equate mgh to the rotational KE alone.",
                        "A rolling body has translational and rotational KE.")]

    def explain(p, v):
        return (f"<p>$Mgh = \\tfrac12 Mv^2(1 + I/MR^2)$ with $I/MR^2 = {sp.latex(KCM[p['shape']])}$, so "
                f"$v = \\sqrt{{2gh/(1+{sp.latex(KCM[p['shape']])})}} = {v}$ m/s.</p>")

    return Family(id="rot.rolling_speed", subject=SUBJ, chapter=CH, topic="Rolling Motion",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes,
                  display=lambda v, p: fmt(v), explain=explain, numerical=True,
                  modelled_on=["S9wqyyoVVI3UqM0yF51kmj42zit", "KQJHwKrZeCnzHTDE"]).register()


# ================================================================== 6. rolling: minimum friction coefficient
def _mu_form(p, shape=None, eqs=None):
    shape = shape or p["shape"]
    kn = {"M": S("kg"), "R": S("m"), "th": K(p["th"], "degree"), **G}
    return rb(kn, {"b": round_body(shape)}, {"I": ax(["b"])},
              {"a": U("m/s^2"), "f": U("N"), "mu": U("", "positive")},
              eqs or ["f = mu*M*g*cos(th)"], "mu",
              ["rolls without slipping; least mu: required static friction = mu N, N = M g cos(th)"],
              relations=[{"template": "rolling_incline", "a": "a", "f": "f", "M": "M", "I": "I", "R": "R",
                          "g": "g", "th": "th"}])


def _mu_plain(p, eqs):
    kn = {"M": S("kg"), "R": S("m"), "th": K(p["th"], "degree"), **G}
    unk = {"a": U("m/s^2"), "f": U("N"), "mu": U("", "positive")}
    unk = {k: v for k, v in unk.items() if any(re.search(rf"\b{k}\b", e) for e in eqs)}
    return rb(kn, {"b": round_body(p["shape"])}, {"I": ax(["b"])}, unk, eqs, "mu", ["mistaken model"])


def rolling_friction() -> Family:
    def sample(rng):
        return {"shape": rng.choice(ROUND), "th": rng.choice([30, 45, 60])}

    def stem(p):
        return (f"<p>A {NAME[p['shape']]} of mass $M$ and radius $R$ is placed on a rough inclined plane of "
                f"inclination {p['th']}° and released. The minimum coefficient of static friction for which it "
                f"rolls down without slipping is ($g = 10\\ \\mathrm{{m\\,s^{{-2}}}}$):</p>")

    def mistakes(p):
        return [Mistake("WRONG_TABLE_ENTRY", _mu_form(p, shape=ALT[p["shape"]]),
                        "Students use the MOI of a different body.", "Use this body's own I."),
                Mistake("SLIDING_BLOCK_CONDITION", _mu_plain(p, ["mu*M*g*cos(th) = M*g*sin(th)"]),
                        "Students use the no-sliding condition of a block, μ = tan θ.",
                        "A rolling body accelerates; friction only supplies the torque for α = a/R."),
                Mistake("FRICTION_TAKEN_AS_NET_FORCE",
                        _mu_form(p, eqs=["mu*M*g*cos(th) = M*a"]),
                        "Students set friction equal to M a (the net force).",
                        "The net force is Mg sinθ − f; friction equals I a/R²."),
                Mistake("SLIDING_ACCELERATION_IN_TORQUE",
                        _mu_plain(p, ["a = g*sin(th)", "f*R**2 = I*a", "f = mu*M*g*cos(th)"]),
                        "Students use a = g sinθ in the torque equation (rotation ignored in a).",
                        "With rolling, a = g sinθ/(1 + I/MR²)."),
                Mistake("SIN_COS_INTERCHANGED", _mu_form(p, eqs=["f = mu*M*g*sin(th)"]),
                        "Students take the normal reaction as Mg sinθ.", "N = Mg cosθ on an incline.")]

    def explain(p, v):
        k = KCM[p["shape"]]
        return (f"<p>$f = \\dfrac{{I/MR^2}}{{1 + I/MR^2}}\\,Mg\\sin\\theta$ and $f \\le \\mu Mg\\cos\\theta$ give "
                f"$\\mu_{{min}} = \\dfrac{{{sp.latex(k)}}}{{1+{sp.latex(k)}}}\\tan {p['th']}^\\circ = "
                f"{sp.latex(v)}$.</p>")

    return Family(id="rot.rolling_friction", subject=SUBJ, chapter=CH, topic="Rolling Motion",
                  difficulty="HARD", sample=sample, formal=_mu_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: frac(v), explain=explain,
                  modelled_on=["wQEYxGZIs3cHnLxTc61kmlw4y83", "KQJHwKrZeCnzHTDE"]).register()


# ================================================================== 7. rolling KE split
KE_ASK = {"rot_total": ("rotational kinetic energy to its total kinetic energy", "x = KEr/KE"),
          "trans_total": ("translational kinetic energy to its total kinetic energy", "x = KEt/KE"),
          "rot_trans": ("rotational kinetic energy to its translational kinetic energy", "x = KEr/KEt")}
KE_WRONG = {"rot_total": ["x = KEt/KE", "x = KEr/KEt"], "trans_total": ["x = KEr/KE", "x = KEt/KEr"],
            "rot_trans": ["x = KEt/KEr", "x = KEr/KE"]}


def _ke_form(p, shape=None, eq=None):
    shape = shape or p["shape"]
    return rb({"M": S("kg"), "R": S("m"), "v": S("m/s")}, {"b": round_body(shape)}, {"I": ax(["b"])},
              {"KE": U("J"), "KEt": U("J"), "KEr": U("J"), "x": U("", "positive")},
              [eq or KE_ASK[p["ask"]][1]], "x", ["rolling without slipping: omega = v/R"],
              relations=[{"template": "rolling_ke", "KE": "KE", "KEt": "KEt", "KEr": "KEr", "M": "M", "I": "I",
                          "R": "R", "v": "v"}])


def ke_split() -> Family:
    def sample(rng):
        return {"shape": rng.choice(ROUND), "ask": rng.choice(list(KE_ASK))}

    def stem(p):
        return (f"<p>A {NAME[p['shape']]} rolls without slipping on a horizontal floor. The ratio of its "
                f"{KE_ASK[p['ask']][0]} is:</p>")

    def mistakes(p):
        w1, w2 = KE_WRONG[p["ask"]]
        return [Mistake("WRONG_TABLE_ENTRY", _ke_form(p, shape=ALT[p["shape"]]),
                        "Students use the MOI of a different body.", "Use this body's own I."),
                Mistake("COMPLEMENT_OR_INVERSE", _ke_form(p, eq=w1),
                        "Students compute the other share (or the inverse ratio).",
                        "Read which energy is in the numerator."),
                Mistake("WRONG_REFERENCE_ENERGY", _ke_form(p, eq=w2),
                        "Students compare with the translational KE instead of the total (or vice versa).",
                        "Total KE = translational + rotational."),
                Mistake("CONTACT_AXIS_DOUBLE_COUNTED", _ke_form(p, eq={
                    "rot_total": "x = (KEr + KEt)/(KE + KEt)", "trans_total": "x = KEt/(KE + KEt)",
                    "rot_trans": "x = KE/KEt"}[p["ask"]]),
                        "Students take the rotational KE about the contact point, ½I_Pω², and still add the "
                        "translational KE.",
                        "½I_Pω² already is the total KE; about the centre, K_rot = ½I_cmω²."),
                Mistake("RING_FORMULA_FOR_ALL",
                        _ke_form(p, shape="ring" if p["shape"] != "ring" else "disc"),
                        "Students use I = MR² for every round body (or MR²/2 for a ring).",
                        "Each body has its own I/MR².")]

    def explain(p, v):
        k = KCM[p["shape"]]
        return (f"<p>$K_t = \\tfrac12 Mv^2$, $K_r = \\tfrac12 I\\omega^2 = {sp.latex(k)}\\cdot\\tfrac12 Mv^2$ "
                f"(with $\\omega = v/R$). Required ratio $= {sp.latex(v)}$.</p>")

    return Family(id="rot.ke_split", subject=SUBJ, chapter=CH, topic="Rolling Motion",
                  difficulty="EASY", sample=sample, formal=_ke_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: frac(v), explain=explain,
                  modelled_on=["1krqchuow", "9jCyQhEAs6eWjkTr4Q7k9k2k5hhldlt"]).register()


# ================================================================== 8. pulley with a hanging mass
PUL_ASK = {"a": ("the acceleration of the block", "m/s^2", "m\\,s^{-2}"),
           "T": ("the tension in the string", "N", "N"),
           "al": ("the angular acceleration of the pulley", "rad/s^2", "rad\\,s^{-2}")}
NEWTON = ["m*g - T = m*a", "T*R = I*al", "a = al*R"]


def _pul_form(p, shape=None, eqs=None, R="R", extra=None):
    shape = shape or p["shape"]
    kn = {"M": K(p["M"], "kg"), "m": K(p["m"], "kg"), "R": K(p["R"], "cm"), **G}
    unk = {"a": U("m/s^2"), "T": U("N"), "al": U("1/s^2"), **(extra or {})}
    return rb(kn, {"p": body(shape, "M", R=R)}, {"I": ax(["p"])}, unk, eqs or NEWTON, p["ask"],
              ["fixed frictionless horizontal axle; light inextensible string does not slip",
               "pulley = uniform disc / thin ring about its own axis"])


def pulley() -> Family:
    def sample(rng):
        return {"shape": rng.choice(["disc", "ring"]), "M": rng.choice([2, 4, 6, 8, 10]),
                "m": rng.choice([1, 2, 3, 4, 5]), "R": rng.choice([10, 20, 25, 40, 50]),
                "ask": rng.choice(list(PUL_ASK))}

    def stem(p):
        pul = "uniform disc" if p["shape"] == "disc" else "thin ring (spokes of negligible mass)"
        return (f"<p>A light string is wound round the rim of a pulley in the form of a {pul} of mass {p['M']} kg "
                f"and radius {p['R']} cm, free to rotate about a fixed horizontal frictionless axle through its "
                f"centre. A block of mass {p['m']} kg hangs from the free end of the string and the system is "
                f"released from rest. Taking $g = 10\\ \\mathrm{{m\\,s^{{-2}}}}$, {PUL_ASK[p['ask']][0]} is:</p>")

    def mistakes(p):
        return [Mistake("WRONG_TABLE_ENTRY", _pul_form(p, shape=ALT[p["shape"]]),
                        "Students use I = MR² for a disc pulley (or MR²/2 for a ring).", "Use the pulley's own I."),
                Mistake("TENSION_EQUALS_WEIGHT", _pul_form(p, eqs=["T = m*g", "T*R = I*al", "a = al*R"]),
                        "Students take the tension equal to the block's weight.",
                        "The block accelerates downward, so T < mg."),
                Mistake("PULLEY_MASS_AS_TRANSLATING",
                        _pul_form(p, eqs=["m*g = (m + M)*a", "T = M*a", "a = al*R"]),
                        "Students add the whole pulley mass as if it moved with the block.",
                        "The pulley rotates; its effective inertia is I/R², not M."),
                Mistake("DIAMETER_USED_AS_RADIUS", _pul_form(p, eqs=["m*g - T = m*a", "T*R = I*al", "a = 2*al*R"],
                                                             R="2*R"),
                        "Students use the diameter where the radius is needed.",
                        "Torque arm and a = αR use the radius."),
                Mistake("SIGN_OF_TENSION_REVERSED",
                        _pul_form(p, eqs=["T = m*(g + a0)", "a0 = m*g/(m + I/R**2)", "T*R = I*al", "a = al*R"],
                                  extra={"a0": U("m/s^2")}),
                        "Students write T − mg = ma for a block moving downward.",
                        "For downward acceleration mg − T = ma.")]

    def explain(p, v):
        kk = "\\tfrac12" if p["shape"] == "disc" else ""
        return (f"<p>Block: $mg - T = ma$; pulley: $TR = I\\alpha$ with $I = {kk}MR^2$; no slipping: "
                f"$a = \\alpha R$. Hence $a = \\dfrac{{mg}}{{m + I/R^2}}$, $T = (I/R^2)a$, "
                f"$\\alpha = a/R$.</p><p>Answer: {val(v, PUL_ASK[p['ask']][2])}.</p>")

    return Family(id="rot.pulley_hanging_mass", subject=SUBJ, chapter=CH, topic="Torque and Angular Acceleration",
                  difficulty="MEDIUM", sample=sample, formal=_pul_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: val(v, PUL_ASK[p["ask"]][2]), explain=explain,
                  modelled_on=["SkXe9OycfhSpUpyH", "shugQNB8jJKFVrgp4ot79"]).register()


# ================================================================== 9. person on a turntable
MOVES = {"rim_centre": ("R", "0", "from the rim to the centre"), "centre_rim": ("0", "R", "from the centre to the rim"),
         "rim_half": ("R", "R/2", "from the rim to a point midway between the rim and the centre"),
         "half_rim": ("R/2", "R", "from a point midway between the centre and the rim out to the rim")}


def _tt_form(p, shape="disc", eq="Ii*w1 = If*w2", r1=None, r2=None, person=True):
    r1 = r1 or MOVES[p["move"]][0]
    r2 = r2 or MOVES[p["move"]][1]
    kn = {"M": K(p["M"], "kg"), "m": K(p["m"], "kg"), "R": K(p["R"], "m"), "w1": K(p["w1"], "rpm")}
    bd = {"t": body(shape, "M", R="R"), "p1": body("point", "m", center=(r1, 0, 0)),
          "p2": body("point", "m", center=(r2, 0, 0))}
    ine = {"Ii": ax(["t", "p1"] if person else ["t"]), "If": ax(["t", "p2"] if person else ["t"])}
    return rb(kn, bd, ine, {"w2": U("rpm", "positive")}, [eq], "w2",
              ["no external torque about the vertical axis: angular momentum conserved",
               "platform = uniform disc; person = particle"])


def turntable() -> Family:
    def sample(rng):
        return {"M": rng.choice([100, 120, 150, 200, 240]), "m": rng.choice([40, 50, 60, 75, 80]),
                "R": rng.choice([1, 2, 3]), "w1": rng.choice([6, 8, 10, 12, 15, 20]),
                "move": rng.choice(list(MOVES))}

    def stem(p):
        return (f"<p>A horizontal circular platform (a uniform disc) of mass {p['M']} kg and radius {p['R']} m "
                f"rotates freely about a frictionless vertical axis through its centre at {p['w1']} rpm. A person "
                f"of mass {p['m']} kg standing on it walks radially {MOVES[p['move']][2]}. Treating the person as a "
                f"particle, the new angular speed of the platform is:</p>")

    def mistakes(p):
        return [Mistake("ENERGY_CONSERVED_INSTEAD", _tt_form(p, eq="Ii*w1**2 = If*w2**2"),
                        "Students conserve rotational kinetic energy.",
                        "The person does internal work; only angular momentum is conserved."),
                Mistake("PLATFORM_AS_RING", _tt_form(p, shape="ring"),
                        "Students take the platform's MOI as MR².", "A uniform disc has I = MR²/2."),
                Mistake("RATIO_INVERTED", _tt_form(p, eq="If*w1 = Ii*w2"),
                        "Students invert the ratio of moments of inertia.",
                        "Smaller I means larger ω: I₁ω₁ = I₂ω₂."),
                Mistake("PERSON_IGNORED", _tt_form(p, eq="Ii*w1 = If*w2", person=False),
                        "Students ignore the person's contribution, so ω is unchanged.",
                        "The person's m r² changes as they walk, changing ω.")]

    def explain(p, v):
        r1, r2, _ = MOVES[p["move"]]
        return (f"<p>$L$ conserved: $(\\tfrac12MR^2 + m r_1^2)\\omega_1 = (\\tfrac12MR^2 + m r_2^2)\\omega_2$ with "
                f"$r_1 = {r1}$, $r_2 = {r2}$.</p><p>$\\omega_2 = {fmt(v)}$ rpm.</p>")

    return Family(id="rot.turntable_person", subject=SUBJ, chapter=CH, topic="Conservation of Angular Momentum",
                  difficulty="MEDIUM", sample=sample, formal=_tt_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: val(v, "rpm"), explain=explain,
                  modelled_on=["bEtWbedAMiaQUiRiUYjgy2xukf258opx", "74sEsWoySBVGwUIk"]).register()


# ================================================================== 10. coupled discs: KE lost (numerical)
SENSE = {"same": "in the same sense as the first", "opposite": "in the opposite sense"}


def _cd_form(p, eqs=None, sense=None, target="dK"):
    s = sense or p["sense"]
    kn = {"M1": K(p["M1"], "kg"), "R1": K(p["R1"], "m"), "M2": K(p["M2"], "kg"), "R2": K(p["R2"], "m"),
          "w1": K(p["w1"], "1/s"), "w2": K(p["w2"], "1/s")}
    sg = "+" if s == "same" else "-"
    eqs = eqs or [f"I1*w1 {sg} I2*w2 = (I1 + I2)*w",
                  "dK = I1*w1**2/2 + I2*w2**2/2 - (I1 + I2)*w**2/2"]
    return rb(kn, {"d1": body("disc", "M1", R="R1"), "d2": body("disc", "M2", R="R2")},
              {"I1": ax(["d1"]), "I2": ax(["d2"])}, {"w": U("1/s"), "dK": U("J")}, eqs, target,
              ["coaxial discs; interaction is internal: angular momentum about the axis conserved",
               "common final angular velocity (sign = sense)"])


def coupled_discs() -> Family:
    def sample(rng):
        while True:
            M1, M2 = rng.randint(1, 10), rng.randint(1, 10)
            R1, R2 = rng.choice(["0.2", "0.4", "0.5", "1"]), rng.choice(["0.2", "0.4", "0.5", "1"])
            w1, w2 = rng.choice([4, 5, 6, 8, 10, 12, 15, 20, 30]), rng.choice([2, 3, 4, 5, 6, 10])
            sense = rng.choice(list(SENSE))
            I1 = M1 * sp.Rational(R1) ** 2 / 2
            I2 = M2 * sp.Rational(R2) ** 2 / 2
            dw = w1 - w2 if sense == "same" else w1 + w2
            dK = I1 * I2 * dw ** 2 / (2 * (I1 + I2))
            if dw != 0 and dK.is_integer and 2 <= dK <= 500 and w1 != w2:
                return {"M1": M1, "R1": R1, "M2": M2, "R2": R2, "w1": w1, "w2": w2, "sense": sense}

    def stem(p):
        return (f"<p>A uniform disc of mass {p['M1']} kg and radius {p['R1']} m spins about its axis with angular "
                f"speed {p['w1']} rad/s. A second uniform disc of mass {p['M2']} kg and radius {p['R2']} m, "
                f"spinning about the same axis at {p['w2']} rad/s {SENSE[p['sense']]}, is gently placed coaxially "
                f"on the first. Friction between them soon makes them rotate together. The loss of kinetic energy "
                f"(in J) is ______.</p>")

    def mistakes(p):
        other = "opposite" if p["sense"] == "same" else "same"
        return [Mistake("SENSE_IGNORED", _cd_form(p, sense=other),
                        "Students ignore the senses of rotation and add (or subtract) angular momenta wrongly.",
                        "Angular momentum is a vector; opposite spins subtract."),
                Mistake("FINAL_KE_REPORTED", _cd_form(p, target="Kf", eqs=[
                    f"I1*w1 {'+' if p['sense'] == 'same' else '-'} I2*w2 = (I1 + I2)*w",
                    "Kf = (I1 + I2)*w**2/2"]) | {"unknowns": {"w": U("1/s"), "Kf": U("J")}},
                    "Students report the final kinetic energy instead of the loss.",
                    "Loss = initial KE - final KE."),
                Mistake("DISC_AS_RING", _cd_form(p, eqs=[
                    f"2*I1*w1 {'+' if p['sense'] == 'same' else '-'} 2*I2*w2 = (2*I1 + 2*I2)*w",
                    "dK = I1*w1**2 + I2*w2**2 - (I1 + I2)*w**2"]),
                    "Students take I = MR² for each disc.", "A uniform disc has I = MR²/2."),
                Mistake("ENERGY_CONSERVED_NO_LOSS", _cd_form(p, eqs=[
                    "I1*w1**2 + I2*w2**2 = (I1 + I2)*w**2", "dK = I1*w1**2/2 + I2*w2**2/2 - (I1 + I2)*w**2/2"]),
                    "Students conserve KE to find the common ω.", "Coupling is inelastic: only L is conserved.")]

    def explain(p, v):
        sg = "+" if p["sense"] == "same" else "-"
        return (f"<p>$I = \\tfrac12MR^2$ for each disc. $I_1\\omega_1 {sg} I_2\\omega_2 = (I_1+I_2)\\omega$; "
                f"loss $= \\dfrac{{I_1I_2(\\omega_1 {'-' if sg == '+' else '+'} \\omega_2)^2}}{{2(I_1+I_2)}} = "
                f"{v}$ J.</p>")

    return Family(id="rot.coupled_discs_ke_loss", subject=SUBJ, chapter=CH, topic="Conservation of Angular Momentum",
                  difficulty="HARD", sample=sample, formal=_cd_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: fmt(v), explain=explain, numerical=True,
                  modelled_on=["1lsg70wif", "1ktfjwrjv"]).register()


# ================================================================== 11. rod released from horizontal
ROD_ASK = {"w": ("the angular speed of the rod as it passes through the vertical position", "rad/s", "rad\\,s^{-1}"),
           "vt": ("the linear speed of its free end as it passes through the vertical position", "m/s", "m\\,s^{-1}"),
           "vc": ("the speed of its centre of mass as it passes through the vertical position", "m/s",
                  "m\\,s^{-1}"),
           "al": ("its angular acceleration just after release", "rad/s^2", "rad\\,s^{-2}")}


def _rod_form(p, pivot="L/2", drop="L/2", arm="L/2", point_tip=False):
    kn = {"m": K(p["m"], "kg"), "L": K(p["L"], "m"), **G}
    bd = {"r": body("point", "m", center=("L", 0, 0)) if point_tip else body("rod", "m", center=(pivot, 0, 0),
                                                                             u=X, L="L")}
    unk = {"w": U("1/s", "positive"), "vt": U("m/s", "positive"), "vc": U("m/s", "positive"),
           "al": U("1/s^2", "positive")}
    eqs = [f"I*w**2/2 = m*g*{drop}", "vt = w*L", "vc = w*L/2", f"m*g*{arm} = I*al"]
    return rb(kn, bd, {"I": ax(["r"], O3, Y)}, unk, eqs, p["ask"],
              ["rod hinged at one end O, frictionless, released from rest horizontal",
               "energy: CM falls L/2 to the vertical; torque of weight about O at release"])


def rod_release() -> Family:
    def sample(rng):
        return {"L": rng.choice(["0.3", "0.6", "0.75", "0.9", "1.2", "1.5", "2.4", "2.7"]), "m": rng.randint(1, 5),
                "ask": rng.choice(list(ROD_ASK))}

    def stem(p):
        return (f"<p>A thin uniform rod of mass {p['m']} kg and length {p['L']} m is hinged at one end so that it can "
                f"rotate freely in a vertical plane. It is held horizontal and released from rest. Taking "
                f"$g = 10\\ \\mathrm{{m\\,s^{{-2}}}}$, {ROD_ASK[p['ask']][0]} is:</p>")

    def mistakes(p):
        return [Mistake("MOI_ABOUT_CENTRE", _rod_form(p, pivot="0"),
                        "Students use ML²/12 although the rod turns about its end.", "About an end, I = ML²/3."),
                Mistake("CM_DROP_TAKEN_AS_L", _rod_form(p, drop="L", arm="L"),
                        "Students take the fall of the centre of mass (and weight's arm) as the full length L.",
                        "The weight acts at the centre, L/2 from the hinge."),
                Mistake("ROD_AS_PARTICLE_AT_TIP", _rod_form(p, point_tip=True, drop="L", arm="L"),
                        "Students treat the rod as a particle at its free end.",
                        "Mass is spread along the rod: I = ML²/3 and the CM is at L/2."),
                Mistake("ROD_AS_PARTICLE_AT_CENTRE",
                        _rod_form(p, pivot="L/2") | {"bodies": {"r": body("point", "m", center=("L/2", 0, 0))}},
                        "Students replace the rod by a particle at its centre of mass.",
                        "Rotational inertia is not M·(L/2)²; a rod about its end has ML²/3.")]

    def explain(p, v):
        return (f"<p>$I_O = \\tfrac13 mL^2$. Energy: $\\tfrac12 I_O\\omega^2 = mg\\tfrac L2 \\Rightarrow "
                f"\\omega = \\sqrt{{3g/L}}$; $v_{{end}} = \\omega L$, $v_{{cm}} = \\omega L/2$. At release "
                f"$mg\\tfrac L2 = I_O\\alpha \\Rightarrow \\alpha = \\tfrac{{3g}}{{2L}}$.</p>"
                f"<p>Answer: {val(v, ROD_ASK[p['ask']][2])}.</p>")

    return Family(id="rot.rod_release", subject=SUBJ, chapter=CH, topic="Rotational Kinetic Energy",
                  difficulty="MEDIUM", sample=sample, formal=_rod_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: val(v, ROD_ASK[p["ask"]][2]), explain=explain,
                  modelled_on=["vJvFfvFSPmK8XIM4", "xifytadWvZeQkeLsnjmvY", "1ktmwpjl2"]).register()


# ================================================================== 12. constant torque: work / ω / power (numerical)
TW_ASK = {"W": ("the work done by the force in the first {t} s (in J)", "J"),
          "w": ("the angular speed of the wheel at the end of {t} s (in rad/s)", "rad/s"),
          "P": ("the instantaneous power delivered by the force at $t = {t}$ s (in W)", "W")}


def _tw_form(p, shape=None, eqs=None):
    shape = shape or p["shape"]
    kn = {"M": K(p["M"], "kg"), "R": K(p["R"], "m"), "F": K(p["F"], "N"), "t": K(p["t"], "s")}
    eqs = eqs or ["F*R = I*al", "w = al*t", "W = I*w**2/2", "P = F*R*w"]
    return rb(kn, {"b": round_body(shape)}, {"I": ax(["b"])},
              {"al": U("1/s^2"), "w": U("1/s"), "W": U("J"), "P": U("W")}, eqs, p["ask"],
              ["fixed frictionless axle; force tangential at the rim, constant in magnitude; starts from rest",
               "work-energy theorem: W = rotational KE gained"])


def torque_work() -> Family:
    def sample(rng):
        while True:
            sh = rng.choice(["disc", "ring", "solid_cylinder"])
            M, R = rng.choice([1, 2, 4, 5, 8, 10]), rng.choice(["0.1", "0.2", "0.25", "0.5", "1"])
            F, t, ask = rng.choice([1, 2, 4, 5, 10, 20]), rng.randint(1, 5), rng.choice(list(TW_ASK))
            I = KCM[sh] * M * sp.Rational(R) ** 2
            w = F * sp.Rational(R) * t / I
            v = {"W": I * w ** 2 / 2, "w": w, "P": F * sp.Rational(R) * w}[ask]
            if v.is_integer and 1 <= v <= 2000:
                return {"shape": sh, "M": M, "R": R, "F": F, "t": t, "ask": ask}

    def stem(p):
        return (f"<p>A {NAME[p['shape']]} of mass {p['M']} kg and radius {p['R']} m is mounted on a fixed, "
                f"frictionless horizontal axle through its centre (along its symmetry axis). Starting from rest, "
                f"a constant force of {p['F']} N is applied tangentially to its rim by a light string wound on it. "
                f"{TW_ASK[p['ask']][0].format(t=p['t'])[0].upper() + TW_ASK[p['ask']][0].format(t=p['t'])[1:]} "
                f"is ______.</p>")

    def mistakes(p):
        return [Mistake("WRONG_TABLE_ENTRY", _tw_form(p, shape=ALT[p["shape"]]),
                        "Students use I = MR² for a disc (or MR²/2 for a ring).", "Use this body's own I."),
                Mistake("DIAMETER_AS_ARM", _tw_form(p, eqs=["2*F*R = I*al", "w = al*t", "W = I*w**2/2",
                                                              "P = 2*F*R*w"]),
                        "Students take the diameter as the lever arm.", "Torque = F × radius."),
                Mistake("HALF_FORGOTTEN_IN_KE", _tw_form(p, eqs=["F*R = I*al", "w = al*t", "W = I*w**2",
                                                                  "P = 2*W/t"]),
                        "Students write rotational KE as Iω² (and the power from it).", "K_rot = ½Iω²."),
                Mistake("AVERAGE_FOR_INSTANTANEOUS", _tw_form(p, eqs=["F*R = I*al", "w = al*t/2",
                                                                       "W = I*w**2/2", "P = F*R*w"]),
                        "Students use the average angular speed (half the final value).",
                        "Starting from rest under constant α, ω(t) = αt at the instant t.")]

    def explain(p, v):
        return (f"<p>$I = {sp.latex(KCM[p['shape']])}MR^2$, $\\tau = FR = I\\alpha$, $\\omega = \\alpha t$, "
                f"$W = \\tfrac12 I\\omega^2$, $P = \\tau\\omega$.</p><p>Answer: {v} {TW_ASK[p['ask']][1]}.</p>")

    return Family(id="rot.torque_work_power", subject=SUBJ, chapter=CH, topic="Torque and Angular Acceleration",
                  difficulty="EASY", sample=sample, formal=_tw_form, stem=stem, mistakes=mistakes,
                  display=lambda v, p: fmt(v), explain=explain, numerical=True,
                  modelled_on=["xmtiN91wgRQTentL", "ANiozDvSSiYK3aYNBxrC5"]).register()


AXIS_THEOREMS = axis_theorems()
REMOVED_DISC = removed_disc()
COMPOSITE = composite()
GYRATION = gyration()
ROLLING_SPEED = rolling_speed()
ROLLING_FRICTION = rolling_friction()
KE_SPLIT = ke_split()
PULLEY = pulley()
TURNTABLE = turntable()
COUPLED_DISCS = coupled_discs()
ROD_RELEASE = rod_release()
TORQUE_WORK = torque_work()
