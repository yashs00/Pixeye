"""Typed legal-move catalogue (blueprint 2, 6.2, 7.2, 8.2).

Each operator declares: subject, applicable kinds, a precondition, the
transformation and what it is expected to change. Operators only PROPOSE a
child; a child is never trusted until it passes full verification itself.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterator

import sympy as sp

from cqse.core.problem import Subject
from cqse.math.engine import build_model
from cqse.math.expr import parse


@dataclass(frozen=True)
class Operator:
    op_id: str
    family: str  # parameter | domain | target | constraint | trap | regime
    subject: Subject
    kinds: tuple[str, ...]
    description: str
    propose: Callable[[dict], Iterator[tuple[str, dict]]]  # yields (variant label, child formal)


def _clone(f: dict) -> dict:
    return copy.deepcopy(f)


# ---------------------------------------------------------------- mathematics
def _m_shift(f: dict):
    v = sp.Symbol(f.get("var", "x"), real=True)
    for k in (1, -1, 2):
        c = _clone(f)
        for side in ("lhs", "rhs"):
            e = parse(f[side], {v.name: v}).subs(v, v - k)
            # expand polynomials; for rational forms combine over ONE denominator (never cancel factors)
            e = sp.expand(e) if e.is_polynomial(v) else sp.together(sp.expand(e))
            c[side] = sp.sstr(e)
        yield (f"{v.name}->{v.name}-{k}" if k > 0 else f"{v.name}->{v.name}+{-k}"), c


def _m_domain(f: dict):
    for d in ("reals", "positive_reals", "nonnegative_reals", "integers"):
        if f.get("domain", "reals") != d:
            c = _clone(f)
            c["domain"] = d
            yield d, c


def _m_target(f: dict):
    for t in ("count", "sum", "product", "solution_set"):
        if f.get("target", "solution_set") != t:
            c = _clone(f)
            c["target"] = t
            yield t, c


def _m_trap(f: dict):
    """P(x) = 0  ->  P(x)/(x - r) = 0 for a rational root r: removes r (extraneous-root trap)."""
    try:
        m = build_model(f)
    except Exception:  # noqa: BLE001
        return
    if m.rhs != 0 or m.conditions or not sp.expand(m.lhs).is_polynomial(m.var):
        return
    p = sp.Poly(sp.expand(m.lhs), m.var)
    for r in sorted({r for r in p.real_roots() if r.is_Rational}, key=float):
        c = _clone(f)
        den = sp.sstr(m.var - r)
        c["lhs"] = f"({f['lhs']})/({den})"
        yield f"divide by ({den})", c


def _m_radical(f: dict):
    """Quadratic P(x) = 0 -> sqrt(P(x) + (x-k)^2) = x - k.
    Squaring gives back P(x) = 0, but only roots with x >= k survive (planted extraneous root)."""
    try:
        m = build_model(f)
    except Exception:  # noqa: BLE001
        return
    if m.rhs != 0 or m.conditions or not sp.expand(m.lhs).is_polynomial(m.var):
        return
    p = sp.Poly(sp.expand(m.lhs), m.var)
    if p.degree() != 2:
        return
    x = m.var
    for k in (1, 2, 3):
        # P(x) = 0 rewritten as sqrt(P(x) + (x-k)^2) = x - k  (equivalent only where x >= k)
        inner = sp.expand(p.as_expr() + (x - k) ** 2)
        c = _clone(f)
        c["lhs"], c["rhs"] = f"sqrt({inner})", f"{x} - {k}"
        yield f"radical form, k={k}", c


# ---------------------------------------------------------------- physics
ANGLES = ("30", "45", "60")


def _p_angle(f: dict):
    for a in ANGLES:
        if f["theta_deg"] != a:
            c = _clone(f)
            c["theta_deg"] = a
            yield f"theta={a}", c


def _p_speed(f: dict):
    for u in ("10", "20", "30", "40"):
        if f.get("u") != u:
            c = _clone(f)
            c["u"] = u
            yield f"u={u}", c


def _p_target(f: dict):
    opts = ("range", "max_height", "time_of_flight") if f["kind"] == "projectile_level" \
        else ("acceleration", "friction_force")
    for t in opts:
        if f["target"] != t:
            c = _clone(f)
            c["target"] = t
            yield t, c


def _p_regime(f: dict):
    """Flip static <-> kinetic by choosing mu_s across tan(theta), never at it."""
    for mu_s, mu_k in (("0.2", "0.1"), ("0.4", "0.3"), ("0.8", "0.6"), ("1.2", "1")):
        if (f["mu_s"], f["mu_k"]) != (mu_s, mu_k):
            c = _clone(f)
            c["mu_s"], c["mu_k"] = mu_s, mu_k
            yield f"mu_s={mu_s},mu_k={mu_k}", c


# ---------------------------------------------------------------- chemistry
def _c_amounts(f: dict):
    for sp_name in f["given"]:
        for factor in (Fraction(1, 2), Fraction(2), Fraction(3)):
            c = _clone(f)
            q = c["given"][sp_name]
            key = "mass_g" if "mass_g" in q else "moles"
            q[key] = str(Fraction(q[key]) * factor)
            yield f"{sp_name} x{factor}", c


def _c_quantity(f: dict):
    c = _clone(f)
    c["target"]["quantity"] = "moles" if f["target"]["quantity"] == "mass_g" else "mass_g"
    yield c["target"]["quantity"], c


def _d_relation(f: dict):
    from cqse.physics.dimensions import generate_formal
    base = int(f.get("seed", 0))
    for k in range(1, 7):
        c = generate_formal(base * 31 + k, f.get("ask", "not_meaningful"))
        yield f"relation={c['relation']}", c


def _d_ask(f: dict):
    c = _clone(f)
    c["ask"] = "meaningful" if f.get("ask", "not_meaningful") == "not_meaningful" else "not_meaningful"
    yield c["ask"], c


def _c_values(f: dict):
    for i, c in enumerate(f["components"]):
        for k in ("2", "1/2", "3"):
            child = _clone(f)
            v = sp.nsimplify(parse(str(c["value"])), rational=True) * sp.Rational(k)
            child["components"][i]["value"] = sp.sstr(v)
            yield f"{c['id']} x{k}", child


def _c_target(f: dict):
    els = [c for c in f["components"] if c["type"] == "resistor"]
    for c in els:
        for q in ("current", "voltage", "power"):
            t = {"quantity": q, "element": c["id"]}
            if t != f["target"]:
                child = _clone(f)
                child["target"] = t
                yield f"{q} in {c['id']}", child


def _c_topology(f: dict):
    """Add a resistor in parallel with, or in series with, an existing resistor."""
    ids = {c["id"] for c in f["components"]}
    new_id = next(f"R{n}" for n in range(1, 99) if f"R{n}" not in ids)
    for c in f["components"]:
        if c["type"] != "resistor":
            continue
        child = _clone(f)
        child["components"].append({"id": new_id, "type": "resistor", "value": c["value"],
                                    "unit": c.get("unit", "ohm"), "nodes": list(c["nodes"])})
        yield f"{new_id} parallel to {c['id']}", child
        child = _clone(f)
        mid = f"N{len(ids)}"
        for x in child["components"]:
            if x["id"] == c["id"]:
                x["nodes"] = [c["nodes"][0], mid]
        child["components"].append({"id": new_id, "type": "resistor", "value": "2",
                                    "unit": c.get("unit", "ohm"), "nodes": [mid, c["nodes"][1]]})
        yield f"{new_id} in series with {c['id']}", child


CATALOGUE: list[Operator] = [
    Operator("CIR.VALUES", "parameter", Subject.PHYSICS, ("circuit_dc",), "rescale a component", _c_values),
    Operator("CIR.TARGET", "target", Subject.PHYSICS, ("circuit_dc",), "ask about another element", _c_target),
    Operator("CIR.TOPOLOGY", "constraint", Subject.PHYSICS, ("circuit_dc",), "add a parallel/series resistor",
             _c_topology),
    Operator("D.RELATION", "parameter", Subject.PHYSICS, ("dimension_meaningful",),
             "new governing relation / letter arrangement", _d_relation),
    Operator("D.ASK", "target", Subject.PHYSICS, ("dimension_meaningful",),
             "ask meaningful vs not meaningful", _d_ask),
    Operator("M.SHIFT", "parameter", Subject.MATHEMATICS, ("equation",), "translate variable", _m_shift),
    Operator("M.DOMAIN", "domain", Subject.MATHEMATICS, ("equation",), "restrict domain", _m_domain),
    Operator("M.TARGET", "target", Subject.MATHEMATICS, ("equation",), "change requested quantity", _m_target),
    Operator("M.TRAP.RATIONAL", "trap", Subject.MATHEMATICS, ("equation",),
             "rational form with removable root", _m_trap),
    Operator("M.TRAP.RADICAL", "trap", Subject.MATHEMATICS, ("equation",),
             "radical form with extraneous root", _m_radical),
    Operator("P.ANGLE", "parameter", Subject.PHYSICS, ("projectile_level", "incline_friction"),
             "change angle", _p_angle),
    Operator("P.SPEED", "parameter", Subject.PHYSICS, ("projectile_level",), "change launch speed", _p_speed),
    Operator("P.TARGET", "target", Subject.PHYSICS, ("projectile_level", "incline_friction"),
             "change requested observable", _p_target),
    Operator("P.REGIME", "regime", Subject.PHYSICS, ("incline_friction",), "flip friction regime", _p_regime),
    Operator("C.AMOUNTS", "parameter", Subject.CHEMISTRY, ("stoichiometry",),
             "rescale a reactant (may change limiting reagent)", _c_amounts),
    Operator("C.QUANTITY", "target", Subject.CHEMISTRY, ("stoichiometry",), "mass <-> moles", _c_quantity),
]


def legal_moves(subject: Subject, formal: dict) -> list[Operator]:
    return [o for o in CATALOGUE if o.subject == subject and formal.get("kind") in o.kinds]
