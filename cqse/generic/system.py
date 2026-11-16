"""General calculation checker: any PCM problem expressible as equations with units.

Formal state (kind = "equation_system"):
{
  "kind": "equation_system",
  "knowns":   {"m": {"value": "1", "unit": "kg"}, "h": {"value": "5", "unit": "m"},
               "g": {"value": "10", "unit": "m/s^2"}, "R": {"value": "2", "unit": "m"}},
  "unknowns": {"v": {"unit": "m/s", "domain": "positive"}, "N": {"unit": "N", "domain": "real"}},
  "equations": ["m*g*h = m*v**2/2",          # energy conservation, released from rest
                "N - m*g = m*v**2/R"],       # radial Newton's law at the bottom of the loop
  "target": "N",
  "model": ["frictionless track", "released from rest", "N measured at the lowest point"]
}

What is PROVED by software:
  * every equation is dimensionally consistent term by term (SI base dimensions);
  * function arguments (sin, log, exp ...) are dimensionless;
  * the system has exactly one admissible value of the target (domains applied);
  * the value satisfies every ORIGINAL equation exactly and is defined there;
  * an independent numeric solve from other starting points reaches the same value.
What is NOT proved and stays with a teacher (expert-resolvable):
  * "model.correspondence" - that these equations are the right physics/chemistry for the stem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pint
import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.math.expr import UnsupportedExpression, definedness_conditions, parse, tri_equal
from cqse.physics.dimensions import _walk

TOOL = f"cqse-generic 0.1; sympy {sp.__version__}; pint {pint.__version__}"
_ureg = pint.UnitRegistry()
BASE = ["[length]", "[mass]", "[time]", "[current]", "[temperature]", "[substance]", "[luminosity]"]
_BASE_SYMS = sp.symbols("L M T I Th N J")
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,15}$")
# "E" and "I" are allowed: declared symbols take priority over e / imaginary unit in the parser.
_RESERVED = {"pi", "oo", "sqrt", "log", "ln", "exp", "sin", "cos", "tan", "cot", "sec", "csc",
             "asin", "acos", "atan", "Abs", "Rational", "Integer"}
DOMAINS = {"real", "positive", "nonnegative", "negative", "nonzero", "integer", "natural"}


class ModelError(ValueError):
    pass


def unit_info(unit: str) -> tuple[sp.Expr, sp.Expr]:
    """(exact factor to SI base units, dimension as linear form over base symbols)."""
    unit = unit.strip()
    if unit in ("", "1", "dimensionless"):
        return sp.Integer(1), sp.Integer(0)
    if unit in ("degree", "deg"):
        return sp.pi / 180, sp.Integer(0)
    if unit in ("radian", "rad"):
        return sp.Integer(1), sp.Integer(0)
    q = (1 * _ureg(unit)).to_base_units()
    f = float(q.magnitude)
    cand = sp.nsimplify(f, rational=True, tolerance=abs(f) * 1e-13)
    if not (cand != 0 and sp.fraction(cand)[1] < 10**7):
        # SI prefixes give decimal factors (1e-5, 1e-21...): snap to the nearest power-of-ten rational
        e = sp.Integer(10) ** int(sp.floor(sp.log(abs(f), 10)) - 12)
        snapped = sp.Rational(round(f / float(e))) * e
        if snapped != 0 and abs(float(snapped) - f) <= abs(f) * 1e-13:
            cand = sp.nsimplify(snapped)
    def _good(c, scale=1.0):
        return c != 0 and sp.fraction(c)[1] < 10**7 and abs(float(c) * scale - f) <= abs(f) * 1e-13
    if _good(cand):
        exact = cand
    else:  # angular units (rpm, rev/s, degree-based) carry an exact factor of pi
        cpi = sp.nsimplify(f / float(sp.pi), rational=True, tolerance=abs(f) * 1e-13)
        exact = cpi * sp.pi if _good(cpi, float(sp.pi)) else sp.Rational(repr(f))
    dims = dict(q.dimensionality)
    unknown = set(dims) - set(BASE)
    if unknown:
        raise ModelError(f"unit {unit!r} has non-SI dimension {unknown}")
    form = sum((sp.Rational(str(dims.get(b, 0))) * s for b, s in zip(BASE, _BASE_SYMS)), sp.Integer(0))
    return exact, sp.expand(form)


def _pretty_dim(form: sp.Expr) -> str:
    if form == 0:
        return "dimensionless"
    names = ["m", "kg", "s", "A", "K", "mol", "cd"]
    p = sp.Poly(form, *_BASE_SYMS)
    return " ".join(f"{n}^{p.coeff_monomial(s)}" for n, s in zip(names, _BASE_SYMS) if p.coeff_monomial(s) != 0)


@dataclass
class SystemModel:
    syms: dict[str, sp.Symbol]
    known_vals: dict[sp.Symbol, sp.Expr]      # SI exact values
    params: set                               # symbolic knowns ("value": "symbolic"): positive, unspecified
    unknowns: dict[sp.Symbol, str]            # domain
    dims: dict[sp.Symbol, sp.Expr]
    target: sp.Symbol
    target_factor: sp.Expr                    # SI -> requested unit
    target_unit: str
    eqs_u: list[tuple[sp.Basic, sp.Basic]]    # unevaluated (lhs, rhs)
    eqs: list[sp.Expr]                        # evaluated lhs - rhs
    conversions: list[str] = field(default_factory=list)


def build_system(formal: dict) -> SystemModel:
    knowns, unknowns = formal.get("knowns", {}), formal.get("unknowns", {})
    names = list(knowns) + list(unknowns)
    if len(set(names)) != len(names):
        raise ModelError("a symbol is both known and unknown")
    for n in names:
        if not _NAME.match(n) or n in _RESERVED:
            raise ModelError(f"bad symbol name {n!r}")
    if not unknowns or formal.get("target") not in unknowns:
        raise ModelError("target must be one of the unknowns")
    syms = {n: sp.Symbol(n, real=True) for n in names}
    known_vals, dims, conv, params = {}, {}, [], set()
    for n, spec in knowns.items():
        f, d = unit_info(spec.get("unit", ""))
        if str(spec.get("value")).strip().lower() == "symbolic":
            syms[n] = sp.Symbol(n, positive=True)   # e.g. M, R in a ratio question
            params.add(syms[n])
            dims[syms[n]] = d
            continue
        v = sp.nsimplify(parse(str(spec["value"])), rational=True)
        if not (v.is_number and v.is_real):
            raise ModelError(f"known {n} must be a real number")
        known_vals[syms[n]] = sp.simplify(v * f)
        dims[syms[n]] = d
        if f != 1:
            conv.append(f"{n} = {spec['value']} {spec['unit']} = {sp.simplify(v * f)} (SI)")
    doms = {}
    for n, spec in unknowns.items():
        dom = spec.get("domain", "real")
        if dom not in DOMAINS:
            raise ModelError(f"unknown domain {dom!r}")
        _, d = unit_info(spec.get("unit", ""))
        dims[syms[n]] = d
        doms[syms[n]] = dom
    tf, _ = unit_info(unknowns[formal["target"]].get("unit", ""))
    eqs_u, eqs = [], []
    if not formal.get("equations"):
        raise ModelError("no equations")
    for e in formal["equations"]:
        if e.count("=") != 1:
            raise ModelError(f"equation must contain exactly one '=': {e!r}")
        l, r = e.split("=")
        lu, ru = parse(l, syms, evaluate=False), parse(r, syms, evaluate=False)
        eqs_u.append((lu, ru))
        eqs.append(parse(l, syms) - parse(r, syms))
    used = set().union(*[x.free_symbols for x in eqs])
    missing = set(doms) - used
    if missing:
        raise ModelError(f"unknowns {missing} appear in no equation")
    # equations must use the positive symbols for symbolic knowns
    eqs = [e.subs({sp.Symbol(str(p_), real=True): p_ for p_ in params}) for e in eqs]
    eqs_u = [(l_.subs({sp.Symbol(str(p_), real=True): p_ for p_ in params}),
              r_.subs({sp.Symbol(str(p_), real=True): p_ for p_ in params})) for l_, r_ in eqs_u]
    return SystemModel(syms, known_vals, params, doms, dims, syms[formal["target"]], 1 / tf,
                       unknowns[formal["target"]].get("unit", ""), eqs_u, eqs, conv)


def check_dimensions(m: SystemModel) -> VerificationRecord:
    problems = []
    for (lu, ru), src in zip(m.eqs_u, range(len(m.eqs_u))):
        req: list[tuple[str, sp.Expr]] = []
        dl, dr = _walk(lu, m.dims, req), _walk(ru, m.dims, req)
        # a literal 0 carries any dimension ("0 = u^2 + 2as")
        if sp.sympify(lu).doit() != 0 and sp.sympify(ru).doit() != 0:
            req.append(("left side vs right side", sp.expand(dl - dr)))
        for why, f in req:
            if sp.expand(f) != 0:
                problems.append(f"eq{src + 1}: {why} differ by {_pretty_dim(sp.expand(f))}")
    return VerificationRecord(
        check_id="system.dimensions", status=CheckStatus.FAILED if problems else CheckStatus.EXACT_CHECKED,
        method="term-by-term SI dimension algebra", tool=TOOL,
        result="; ".join(problems) if problems else f"all {len(m.eqs_u)} equations dimensionally consistent",
        limitations=["dimensional consistency does not prove the physical model"])


def _admissible(m: SystemModel, sol: dict) -> Optional[bool]:
    for s, dom in m.unknowns.items():
        v = sp.simplify(sol.get(s, s))
        if v.free_symbols - m.params:
            return None
        if v.is_real is False:
            return False
        if v.is_real is None:
            return None
        test = {"real": True, "positive": v.is_positive, "nonnegative": v.is_nonnegative,
                "negative": v.is_negative, "nonzero": v.is_nonzero, "integer": v.is_integer,
                "natural": (v.is_integer and v.is_positive) if v.is_integer is not None else None}[dom]
        if test is False:
            return False
        if test is None:
            return None
    full = {**m.known_vals, **sol}
    for lu, ru in m.eqs_u:
        for c in definedness_conditions(lu) + definedness_conditions(ru):
            val = c.subs(full)
            val = sp.simplify(val) if val not in (sp.true, sp.false) else val
            if val == sp.false:
                return False
            if val != sp.true:
                return None
    for e in m.eqs:
        r = tri_equal(sp.simplify(e.subs(full)), sp.Integer(0))
        if r is not True:
            return r
    return True


@dataclass
class SystemSolution:
    value: Optional[sp.Expr] = None      # in the target's requested unit
    unit: str = ""
    full: dict = field(default_factory=dict)
    records: list[VerificationRecord] = field(default_factory=list)


def solve_system(formal: dict, model_attested: bool = False) -> SystemSolution:
    out = SystemSolution()
    st: dict = {}

    def _build():
        st["m"] = build_system(formal)
        m = st["m"]
        return VerificationRecord(check_id="system.structure", status=CheckStatus.EXACT_CHECKED,
                                  method="schema + whitelist parse + exact unit conversion", tool=TOOL,
                                  assumptions=list(formal.get("model", [])),
                                  result=f"{len(m.eqs)} equation(s), {len(m.unknowns)} unknown(s)"
                                         + (f"; conversions: {m.conversions}" if m.conversions else ""))

    out.records.append(guarded("system.structure", _build))
    if "m" not in st:
        return out
    m: SystemModel = st["m"]
    out.records.append(guarded("system.dimensions", lambda: check_dimensions(m)))

    def _solve():
        eqs = [sp.simplify(e.subs(m.known_vals)) for e in m.eqs]
        sols = sp.solve(eqs, list(m.unknowns), dict=True)
        if not sols:
            return VerificationRecord(check_id="system.solve.primary", status=CheckStatus.UNRESOLVED,
                                      method="sympy.solve", result="no closed-form solution found")
        good, und = [], False
        for s in sols:
            a = _admissible(m, s)
            if a is True:
                good.append(s)
            elif a is None:
                und = True
        vals: list[sp.Expr] = []
        for s in good:
            v = sp.simplify(s[m.target])
            if not any(tri_equal(v, w) is True for w in vals):
                vals.append(v)
        if und:
            return VerificationRecord(check_id="system.solve.primary", status=CheckStatus.UNRESOLVED,
                                      method="sympy.solve", result=f"admissibility undecidable for some of {sols}")
        if len(vals) != 1:
            return VerificationRecord(check_id="system.solve.primary", status=CheckStatus.FAILED,
                                      method="sympy.solve + domain filter", tool=TOOL,
                                      result=f"{len(vals)} admissible target values {vals}: "
                                             "question is ambiguous or inconsistent")
        if vals[0].free_symbols:
            return VerificationRecord(check_id="system.solve.primary", status=CheckStatus.FAILED,
                                      method="sympy.solve", tool=TOOL,
                                      result=f"answer {vals[0]} still depends on {sorted(map(str, vals[0].free_symbols))}"
                                             ": the question does not determine a number")
        st["si"], st["full"] = vals[0], good[0]
        return VerificationRecord(check_id="system.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                  method="exact solve, domain filter, back-substitution into original equations",
                                  tool=TOOL, result=f"{m.target} = {vals[0]} (SI)")

    out.records.append(guarded("system.solve.primary", _solve, seconds=40))

    def _numeric():
        import mpmath as mp
        mp.mp.dps = 30
        unk = list(m.unknowns)
        sample = {p_: sp.Rational(17 + 6 * k, 10) for k, p_ in enumerate(sorted(m.params, key=str))}
        eqs = [sp.simplify(e.subs(m.known_vals).subs(sample)) for e in m.eqs]
        full_num = {u: sp.simplify(st["full"][u].subs(sample)) for u in unk}
        if len(eqs) != len(unk):
            return VerificationRecord(check_id="system.solve.independent", status=CheckStatus.NOT_APPLICABLE,
                                      hard=False, method="nsolve",
                                      result="non-square system; exact back-substitution is the only cross-check")
        target_idx = unk.index(m.target)
        exact = float(sp.N(st["si"], 30))
        hits, tries = 0, 0
        for k in range(8):
            if hits >= 3:      # three independent agreements are enough for a sanity check
                break
            start = [float(sp.N(full_num[u], 20)) * (1 + 0.15 * ((k % 5) - 2) / 2) + 0.01 * k for u in unk]
            try:
                r = sp.nsolve(eqs, unk, start, tol=1e-20, prec=30, maxsteps=40, verify=False)
                subs_ = dict(zip(unk, r))
                ok_res = True
                for e in eqs:   # each residual must be tiny relative to the size of its own terms
                    terms_ = [abs(complex(sp.N(t_.subs(subs_), 25))) for t_ in sp.Add.make_args(sp.expand(e))]
                    if abs(complex(sp.N(e.subs(subs_), 25))) > 1e-12 * max([1e-300] + terms_):
                        ok_res = False
                        break
                if not ok_res:
                    continue
            except Exception:  # noqa: BLE001
                continue
            tries += 1
            # numeric candidates: check domains numerically (exact back-substitution is the primary's job)
            ok_dom = True
            for i, u in enumerate(unk):
                x = complex(r[i])
                if abs(x.imag) > 1e-20:
                    ok_dom = False
                    break
                xr, dom = x.real, m.unknowns[u]
                if (dom == "positive" and xr <= 0) or (dom == "nonnegative" and xr < 0) or \
                        (dom == "negative" and xr >= 0) or (dom == "nonzero" and xr == 0):
                    ok_dom = False
                    break
            if not ok_dom:
                continue
            if abs(float(r[target_idx]) - exact) <= 1e-8 * max(1.0, abs(exact)):
                hits += 1
            else:
                return VerificationRecord(check_id="system.solve.independent", status=CheckStatus.UNRESOLVED,
                                          method="nsolve from perturbed starts", tool=TOOL,
                                          result=f"numeric solve reached a different admissible value "
                                                 f"{float(r[target_idx])} vs {exact}")
        if not hits:
            return VerificationRecord(check_id="system.solve.independent", status=CheckStatus.UNRESOLVED,
                                      method="nsolve", result="numeric method did not converge")
        return VerificationRecord(check_id="system.solve.independent", status=CheckStatus.NUMERICALLY_CHECKED,
                                  numeric_evidence_sufficient=True, method="nsolve from perturbed starts",
                                  tool=TOOL, result=f"{hits}/{tries} numeric runs agree")

    if "si" in st:
        out.records.append(guarded("system.solve.independent", _numeric, seconds=40))
        out.value = sp.simplify(st["si"] * m.target_factor)
        out.unit = m.target_unit
        out.full = st["full"]

    out.records.append(VerificationRecord(
        check_id="model.correspondence",
        status=CheckStatus.EXPERT_REVIEWED if model_attested else CheckStatus.UNRESOLVED,
        method="teacher confirms the equations model the stem",
        result="equations and assumptions must be confirmed by a subject teacher",
        data={"equations": formal.get("equations", []), "model": formal.get("model", [])}))
    return out


# ------------------------------------------------------------ generic misconceptions
def misconceptions(formal: dict) -> list[tuple[str, sp.Expr, list[str], str, str]]:
    """Mutate one term of one equation (drop it, flip its sign, halve/double it,
    swap sin<->cos), re-solve, and return the resulting target values.
    These are MECHANICAL error models: a teacher must confirm plausibility."""
    out = []
    base_m = build_system(formal)
    for i, eq in enumerate(formal["equations"]):
        l, r = eq.split("=")
        for side_name, side, other in (("left", l, r), ("right", r, l)):
            expr = parse(side, base_m.syms)
            terms = list(sp.Add.make_args(sp.expand(expr)))
            for t in terms:
                # A bare unknown (e.g. "N" or "-v") is never mis-scaled by real students.
                core = t.as_coeff_Mul()[1]
                if core in [base_m.syms[u] for u in formal["unknowns"]]:
                    continue
                muts = []
                if len(terms) > 1:
                    muts.append(("DROPPED_TERM", expr - t, f"omits the term {t}"))
                    muts.append(("SIGN_ERROR", expr - 2 * t, f"uses the wrong sign for {t}"))
                muts.append(("FACTOR_HALF", expr - t / 2, f"loses a factor of 2 in {t}"))
                muts.append(("FACTOR_DOUBLE", expr + t, f"doubles the term {t}"))
                if t.has(sp.sin) or t.has(sp.cos):
                    sw = t.subs({sp.sin: sp.cos, sp.cos: sp.sin}, simultaneous=True)
                    muts.append(("SIN_COS_SWAP", expr - t + sw, f"swaps sin and cos in {t}"))
                for mid, new_side, desc in muts:
                    new_eq = f"{sp.sstr(new_side)} = {other}" if side_name == "left" else f"{l} = {sp.sstr(new_side)}"
                    f2 = dict(formal)
                    f2["equations"] = formal["equations"][:i] + [new_eq] + formal["equations"][i + 1:]
                    try:
                        s = _solve_quiet(f2)
                    except Exception:  # noqa: BLE001
                        continue
                    if s is None:
                        continue
                    out.append((f"GENERIC.{mid}", s, [f"equation {i + 1}: {eq}", f"student {desc}",
                                                      f"-> {new_eq}"],
                                f"Student {desc} in equation {i + 1}.",
                                "The correct relation is: " + eq))
    # Most common real errors first: dropped term, lost 1/2, sign, sin/cos, doubled term.
    rank = {"GENERIC.DROPPED_TERM": 0, "GENERIC.FACTOR_HALF": 1, "GENERIC.SIGN_ERROR": 2,
            "GENERIC.SIN_COS_SWAP": 3, "GENERIC.FACTOR_DOUBLE": 4}
    out.sort(key=lambda m: (rank.get(m[0], 9), 0 if "1/2" in m[2][1] or "/2" in m[2][1] else 1))
    return [m for m in out if m[1] != 0]


def _solve_quiet(formal: dict) -> Optional[sp.Expr]:
    m = build_system(formal)
    eqs = [sp.simplify(e.subs(m.known_vals)) for e in m.eqs]
    vals = []
    for s in sp.solve(eqs, list(m.unknowns), dict=True):
        if _admissible(m, s) is True:
            v = sp.simplify(s[m.target] * m.target_factor)
            if not any(tri_equal(v, w) is True for w in vals):
                vals.append(v)
    return vals[0] if len(vals) == 1 else None
