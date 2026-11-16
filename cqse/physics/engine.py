"""Physics engine (blueprint 7, 37.2) - bounded pilot models.

kind = "projectile_level":
    {"kind": "projectile_level", "u": "20", "theta_deg": "30", "g": "10",
     "target": "range" | "max_height" | "time_of_flight"}
    Model: point mass, uniform g, no air resistance, launch and landing at the
    same height, ground frame, +y up.

kind = "incline_friction":
    {"kind": "incline_friction", "m": "2", "theta_deg": "30", "mu_s": "0.5",
     "mu_k": "0.4", "g": "10", "target": "acceleration" | "friction_force"}
    Model: block released from rest on a fixed rough incline, rigid, Coulomb
    friction, ground frame. Regime is decided (static vs kinetic) BEFORE any
    formula is applied. Exactly at threshold (tan(theta) == mu_s) is ambiguous
    and FAILS.

Physical inputs are SI magnitudes given as exact decimal/rational strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pint
import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.math.expr import parse, tri_equal

TOOL = f"sympy {sp.__version__}; pint {pint.__version__}"
_ureg = pint.UnitRegistry()

UNITS = {"range": "m", "max_height": "m", "time_of_flight": "s",
         "acceleration": "m/s^2", "friction_force": "N"}


def _num(s: str, name: str, positive: bool = True) -> sp.Rational:
    v = sp.nsimplify(parse(str(s)), rational=True)
    if not v.is_number or not v.is_real:
        raise ValueError(f"{name} must be a real number")
    if positive and not v.is_positive:
        raise ValueError(f"{name} must be > 0")
    return v


def _deg(s: str) -> sp.Expr:
    d = _num(s, "theta_deg")
    if not (0 < d < 90):
        raise ValueError("theta_deg must satisfy 0 < theta < 90 for this model")
    return d * sp.pi / 180


@dataclass
class PhysicsSolution:
    value: sp.Basic = sp.nan
    units: str = ""
    records: list[VerificationRecord] = field(default_factory=list)
    regime: str = ""


# ----------------------------------------------------------------- projectile
def _proj_eom(u, th, g, target):
    """Method A: integrate equations of motion symbolically and solve y(T)=0, T>0."""
    t = sp.Symbol("t", positive=True)
    x = u * sp.cos(th) * t
    y = u * sp.sin(th) * t - g * t**2 / 2
    T = [r for r in sp.solve(sp.Eq(y, 0), t) if r != 0]
    if len(T) != 1:
        raise RuntimeError(f"expected one positive landing time, got {T}")
    T = T[0]
    if target == "time_of_flight":
        return sp.simplify(T)
    if target == "range":
        return sp.simplify(x.subs(t, T))
    tp = sp.solve(sp.Eq(sp.diff(y, t), 0), t)  # vertical velocity zero
    return sp.simplify(y.subs(t, tp[0]))


def _proj_closed(u, th, g, target):
    """Method B: standard closed forms (independent of the EOM solve above)."""
    return sp.simplify({"time_of_flight": 2 * u * sp.sin(th) / g,
                        "range": u**2 * sp.sin(2 * th) / g,
                        "max_height": u**2 * sp.sin(th)**2 / (2 * g)}[target])


def _proj_dim(target: str) -> Callable:
    import math
    def f(u, th, g):
        return {"time_of_flight": 2 * u * math.sin(th) / g,
                "range": u**2 * math.sin(2 * th) / g,
                "max_height": u**2 * math.sin(th)**2 / (2 * g)}[target]
    return f


# ----------------------------------------------------------------- incline
def incline_regime(th, mu_s) -> Optional[str]:
    """'static', 'kinetic', or None at the exact threshold (ambiguous)."""
    d = sp.simplify(sp.tan(th) - mu_s)
    if d == 0:
        return None
    if d.is_positive:
        return "kinetic"
    if d.is_negative:
        return "static"
    v = sp.N(d, 50)
    if abs(v) < 1e-40:
        return None
    return "kinetic" if v > 0 else "static"


def _incline_formula(m, th, mu_s, mu_k, g, target, regime):
    """Method A: textbook regime formulas."""
    if regime == "static":
        return {"acceleration": sp.Integer(0), "friction_force": sp.simplify(m * g * sp.sin(th))}[target]
    return {"acceleration": sp.simplify(g * (sp.sin(th) - mu_k * sp.cos(th))),
            "friction_force": sp.simplify(mu_k * m * g * sp.cos(th))}[target]


def _incline_newton(m, th, mu_s, mu_k, g, target):
    """Method B: Newton's 2nd law along/normal to incline, assume static first,
    check |f| <= mu_s N, otherwise kinetic. Independent of the tan test."""
    N, f, a = sp.symbols("N f a", real=True)
    W = m * g
    # static attempt (a = 0): solve for N, f
    s = sp.solve([sp.Eq(N - W * sp.cos(th), 0), sp.Eq(W * sp.sin(th) - f, 0)], [N, f], dict=True)[0]
    margin = sp.simplify(mu_s * s[N] - s[f])
    if margin == 0:
        raise RuntimeError("exactly at limiting friction: ambiguous regime")
    holds = margin.is_positive if margin.is_positive is not None else sp.N(margin, 50) > 0
    if holds:
        return {"acceleration": sp.Integer(0), "friction_force": sp.simplify(s[f])}[target], "static"
    k = sp.solve([sp.Eq(N - W * sp.cos(th), 0), sp.Eq(W * sp.sin(th) - mu_k * N - m * a, 0)], [N, a],
                 dict=True)[0]
    return {"acceleration": sp.simplify(k[a]),
            "friction_force": sp.simplify(mu_k * k[N])}[target], "kinetic"


# ----------------------------------------------------------------- driver
def solve_and_verify(formal: dict) -> PhysicsSolution:
    kind = formal.get("kind")
    out = PhysicsSolution()
    st: dict = {}

    def _structure() -> VerificationRecord:
        tgt = formal.get("target")
        if kind == "projectile_level":
            if tgt not in ("range", "max_height", "time_of_flight"):
                raise ValueError(f"bad target {tgt}")
            st["args"] = (_num(formal["u"], "u"), _deg(formal["theta_deg"]), _num(formal["g"], "g"))
            assumptions = ["point mass", "uniform g", "no air resistance", "same launch/landing height",
                           "ground frame, +y up"]
        elif kind == "incline_friction":
            if tgt not in ("acceleration", "friction_force"):
                raise ValueError(f"bad target {tgt}")
            mu_s, mu_k = _num(formal["mu_s"], "mu_s"), _num(formal["mu_k"], "mu_k")
            if mu_k > mu_s:
                raise ValueError("mu_k > mu_s is physically inconsistent for this model")
            st["args"] = (_num(formal["m"], "m"), _deg(formal["theta_deg"]), mu_s, mu_k, _num(formal["g"], "g"))
            assumptions = ["block released from rest", "fixed rigid incline", "Coulomb friction",
                           "mu_k <= mu_s", "ground frame"]
        else:
            raise ValueError(f"unsupported physics kind {kind!r}")
        st["target"] = tgt
        return VerificationRecord(check_id="phys.model", status=CheckStatus.RULE_CHECKED,
                                  method="explicit physical model + input validation", tool=TOOL,
                                  assumptions=assumptions, result="model coherent; inputs in valid ranges")

    out.records.append(guarded("phys.model", _structure))
    if "args" not in st:
        return out
    tgt, args = st["target"], st["args"]
    out.units = UNITS[tgt]

    if kind == "projectile_level":
        def _a():
            st["A"] = _proj_eom(*args, tgt)
            return VerificationRecord(check_id="phys.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                      method="equations of motion, solve y(T)=0", tool=TOOL,
                                      result=f"{tgt} = {st['A']} {out.units}")

        def _b():
            B = _proj_closed(*args, tgt)
            r = tri_equal(st["A"], B)
            s = {True: CheckStatus.EXACT_CHECKED, False: CheckStatus.UNRESOLVED, None: CheckStatus.UNRESOLVED}[r]
            return VerificationRecord(check_id="phys.solve.independent", status=s,
                                      method="closed-form kinematic results", tool=TOOL,
                                      result=f"closed form {B}; agreement={r}")

        def _limits():
            u, g = sp.Symbol("u", positive=True), sp.Symbol("g", positive=True)
            th = sp.Symbol("theta", positive=True)
            expr = _proj_closed(u, th, g, tgt)
            at0 = sp.limit(expr, th, 0)
            ok = at0 == 0
            if tgt == "range":
                # R(90deg) = 0 and R(theta) = R(90deg - theta) (complementary angles)
                ok = ok and sp.simplify(expr.subs(th, sp.pi / 2)) == 0 and \
                    sp.simplify(expr - expr.subs(th, sp.pi / 2 - th)) == 0
            return VerificationRecord(check_id="phys.limiting_cases",
                                      status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                      method="theta->0 (and theta=90deg for range) limits", tool=TOOL,
                                      result="limits behave physically" if ok else "limit violated")

        dim_fn, dim_in = _proj_dim(tgt), ("m/s", "radian", "m/s^2")
    else:
        def _a():
            regime = incline_regime(args[1], args[2])
            if regime is None:
                return VerificationRecord(check_id="phys.solve.primary", status=CheckStatus.FAILED,
                                          method="regime test tan(theta) vs mu_s",
                                          result="tan(theta) == mu_s exactly: static/kinetic regime ambiguous")
            st["regime"] = regime
            st["A"] = _incline_formula(*args, tgt, regime)
            return VerificationRecord(check_id="phys.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                      method=f"regime test -> {regime} formulas", tool=TOOL,
                                      result=f"{tgt} = {st['A']} {out.units} ({regime})")

        def _b():
            B, reg = _incline_newton(*args, tgt)
            r = tri_equal(st["A"], B) if reg == st.get("regime") else False
            s = CheckStatus.EXACT_CHECKED if r is True else CheckStatus.UNRESOLVED
            return VerificationRecord(check_id="phys.solve.independent", status=s,
                                      method="Newton's 2nd law with static-first friction bound check", tool=TOOL,
                                      result=f"{B} ({reg}); agreement={r}")

        def _limits():
            m_, th = sp.Symbol("m", positive=True), sp.Symbol("theta", positive=True)
            g, mk = sp.Symbol("g", positive=True), sp.Symbol("mu_k", nonnegative=True)
            ok = sp.simplify(_incline_formula(m_, th, 0, 0, g, "acceleration", "kinetic").subs(th, sp.pi / 2) - g) == 0
            ok = ok and sp.simplify(_incline_formula(m_, th, 0, mk, g, "friction_force", "kinetic").subs(mk, 0)) == 0
            return VerificationRecord(check_id="phys.limiting_cases",
                                      status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                      method="frictionless vertical incline gives a=g; mu_k=0 gives f=0", tool=TOOL,
                                      result="limits behave physically" if ok else "limit violated")

        import math
        def dim_fn(m, th, mu_s, mu_k, g):
            if tgt == "acceleration":
                return g * (math.sin(th) - mu_k * math.cos(th))
            return mu_k * m * g * math.cos(th)
        dim_in = ("kg", "radian", "dimensionless", "dimensionless", "m/s^2")

    out.records.append(guarded("phys.solve.primary", _a))
    if "A" in st:
        out.records.append(guarded("phys.solve.independent", _b))
    out.records.append(guarded("phys.limiting_cases", _limits))
    out.records.append(guarded("phys.dimensions",
                               lambda: dimension_check(dim_fn, dim_in, out.units, tgt)))
    if "A" in st:
        out.value = st["A"]
        out.regime = st.get("regime", "")
    return out


def dimension_check(fn: Callable, in_units: tuple[str, ...], expected: str, label: str) -> VerificationRecord:
    """Evaluate the governing formula on pint quantities; incompatible terms raise."""
    import math
    qs = []
    for u in in_units:
        if u == "radian":
            qs.append(0.5)  # angle enters only through trig functions (dimensionless)
        elif u == "dimensionless":
            qs.append(0.3)
        else:
            qs.append(1.7 * _ureg(u))
    try:
        # math.sin on floats; pint quantities only on dimensional inputs
        res = fn(*qs)
    except pint.DimensionalityError as e:
        return VerificationRecord(check_id="phys.dimensions", status=CheckStatus.FAILED, method="pint evaluation",
                                  tool=TOOL, result=f"inconsistent dimensions: {e}")
    res_q = res if isinstance(res, pint.Quantity) else res * _ureg.dimensionless
    ok = res_q.dimensionality == _ureg(expected).dimensionality
    return VerificationRecord(
        check_id="phys.dimensions", status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
        method="pint evaluation of governing formula", tool=TOOL,
        limitations=["dimensional consistency does not prove the physical model"],
        result=f"{label}: {res_q.dimensionality} vs expected {expected}" + ("" if ok else " MISMATCH"))


# ----------------------------------------------------------------- misconceptions
def misconceptions(formal: dict) -> list[tuple[str, sp.Basic, list[str], str, str]]:
    """(id, value, trace, why_students, why_wrong). Caller verifies wrongness."""
    out = []
    kind, tgt = formal["kind"], formal["target"]
    if kind == "projectile_level":
        u, th, g = _num(formal["u"], "u"), _deg(formal["theta_deg"]), _num(formal["g"], "g")
        if tgt == "time_of_flight":
            out.append(("PHYS.KIN.HALF_FLIGHT", sp.simplify(u * sp.sin(th) / g),
                        ["Time to reach the top: u sin(theta)/g", "Report it as total flight time (error)"],
                        "Confuses time of ascent with total time of flight.",
                        "Flight time is twice the ascent time for level ground."))
            out.append(("PHYS.KIN.COS_FOR_SIN", sp.simplify(2 * u * sp.cos(th) / g),
                        ["Use horizontal component u cos(theta) for vertical motion (error)"],
                        "Mixes up velocity components.", "Vertical motion uses u sin(theta)."))
            out.append(("PHYS.KIN.NO_COMPONENT", sp.simplify(2 * u / g),
                        ["Use full speed u as the vertical speed: T = 2u/g (error)"],
                        "Does not resolve the velocity into components.", "Only u sin(theta) is vertical."))
        if tgt == "range":
            out.append(("PHYS.KIN.SIN_NOT_SIN2", sp.simplify(u**2 * sp.sin(th) / g),
                        ["Write R = u^2 sin(theta)/g (error: should be sin 2theta)"],
                        "Misremembers the range formula.", "R = u^2 sin(2 theta)/g."))
            out.append(("PHYS.KIN.HALF_RANGE", sp.simplify(u**2 * sp.sin(2 * th) / (2 * g)),
                        ["Use only time of ascent for horizontal travel (error)"],
                        "Uses ascent time instead of full flight time.", "Horizontal travel lasts the full flight."))
            out.append(("PHYS.KIN.NO_HORIZONTAL_COMPONENT", sp.simplify(2 * u**2 * sp.sin(th) / g),
                        ["T = 2u sin(theta)/g", "x = u * T, using u instead of u cos(theta) (error)"],
                        "Uses the full launch speed for horizontal motion.",
                        "Horizontal velocity is u cos(theta)."))
        if tgt == "max_height":
            out.append(("PHYS.KIN.MISSING_HALF", sp.simplify(u**2 * sp.sin(th)**2 / g),
                        ["v^2 = u^2 - 2gH rearranged without the factor 2 (error)"],
                        "Drops the factor of 2 in v^2 = u^2 - 2as.", "H = u^2 sin^2(theta)/(2g)."))
            out.append(("PHYS.KIN.NO_SIN", sp.simplify(u**2 / (2 * g)),
                        ["Use full speed u as vertical speed (error)"],
                        "Treats launch speed as vertical component.", "Only u sin(theta) is vertical."))
            out.append(("PHYS.KIN.COS_IN_HEIGHT", sp.simplify(u**2 * sp.cos(th)**2 / (2 * g)),
                        ["Use u cos(theta) as the vertical component (error)"],
                        "Mixes up velocity components.", "Vertical component is u sin(theta)."))
    else:
        m, th = _num(formal["m"], "m"), _deg(formal["theta_deg"])
        mu_s, mu_k, g = _num(formal["mu_s"], "mu_s"), _num(formal["mu_k"], "mu_k"), _num(formal["g"], "g")
        if tgt == "acceleration":
            out.append(("PHYS.FRICTION.ALWAYS_KINETIC", sp.simplify(g * (sp.sin(th) - mu_k * sp.cos(th))),
                        ["Apply a = g(sin - mu_k cos) without checking whether the block slides (error)"],
                        "Assumes kinetic friction acts whenever there is friction.",
                        "If tan(theta) <= mu_s the block stays at rest; a = 0."))
            out.append(("PHYS.FRICTION.IGNORE", sp.simplify(g * sp.sin(th)),
                        ["Ignore friction entirely (error)"], "Overlooks friction.", "Friction acts on a rough incline."))
            out.append(("PHYS.FRICTION.USE_MU_S", sp.simplify(g * (sp.sin(th) - mu_s * sp.cos(th))),
                        ["Use mu_s for a sliding block (error)"],
                        "Confuses static and kinetic coefficients.", "A sliding block experiences kinetic friction."))
            out.append(("PHYS.FRICTION.N_EQUALS_MG_ACC", sp.simplify(g * sp.sin(th) - mu_k * g),
                        ["Take N = mg, so a = g sin(theta) - mu_k g (error)"],
                        "Assumes normal force equals weight in every geometry.", "On an incline N = mg cos(theta)."))
            out.append(("PHYS.FRICTION.WRONG_DIRECTION", sp.simplify(g * (sp.sin(th) + mu_k * sp.cos(th))),
                        ["Friction taken down the slope, adding to gravity (error)"],
                        "Misjudges the direction of friction.", "Friction opposes the (impending) motion."))
        else:
            out.append(("PHYS.FRICTION.ALWAYS_LIMITING", sp.simplify(mu_s * m * g * sp.cos(th)),
                        ["Take friction = mu_s N always (error)"],
                        "Assumes friction is always at its limiting value.",
                        "Static friction only takes the value needed, up to mu_s N."))
            out.append(("PHYS.FRICTION.N_EQUALS_MG", sp.simplify(mu_k * m * g),
                        ["Take N = mg on an incline (error)"],
                        "Assumes normal force equals weight in every geometry.", "On an incline N = mg cos(theta)."))
            out.append(("PHYS.FRICTION.KINETIC_WHEN_STATIC", sp.simplify(mu_k * m * g * sp.cos(th)),
                        ["Use kinetic friction for a block at rest (error)"],
                        "Uses mu_k N without checking the regime.", "At rest, friction balances mg sin(theta)."))
            out.append(("PHYS.FRICTION.COS_COMPONENT", sp.simplify(m * g * sp.cos(th)),
                        ["Friction = mg cos(theta) (confuses normal and tangential components)"],
                        "Resolves weight onto the wrong axis.", "Tangential component of weight is mg sin(theta)."))
            out.append(("PHYS.FRICTION.MU_S_MG", sp.simplify(mu_s * m * g),
                        ["Friction = mu_s m g (limiting value with N = mg)"],
                        "Combines two errors: limiting friction and N = mg.",
                        "Static friction equals what is needed; N = mg cos(theta)."))
    return out
