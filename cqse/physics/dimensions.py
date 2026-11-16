"""Dimensional-consistency engine for "which combination is (not) meaningful" questions.

Example (formal state):
    {"kind": "dimension_meaningful",
     "quantities": ["A", "B", "C", "D"],
     "relation": "A*D = C*log(B*D)",
     "ask": "not_meaningful" | "meaningful"}
    Options are expressions in the quantities, e.g. "(A - C)/D".

Method (exact linear algebra, no numbers guessed):
  * Each quantity's dimension is an unknown vector (log-dimensions).
  * Walking an expression yields linear constraints:
        Add      -> all terms must have equal dimensions
        log/exp/sin/... -> argument must be dimensionless; result is dimensionless
        Mul/Pow  -> dimensions add / scale
  * The given relation's constraints are solved; remaining freedom is
    expressed with free symbols.
  * Stated facts ("none dimensionless", "all different") are FORBIDDEN forms:
        dim(Q) = 0  and  dim(Q_i) - dim(Q_j) = 0.
  * For an option with required-zero forms M:
        ALWAYS meaningful   iff every form in M is identically 0
        NEVER meaningful    iff span(M) contains a forbidden form
                            (making the option consistent would contradict the stated facts)
        CONTINGENT          otherwise (depends on unknown dimensions) -> an option like that
                            makes the question ambiguous and the item is FAILED.
"""
from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass, field
from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.math.expr import parse

TOOL = f"cqse-dimensions 0.1; sympy {sp.__version__}"
_TRANSCENDENTAL = (sp.log, sp.exp, sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.atan)


class DimensionError(ValueError):
    pass


@dataclass
class DimModel:
    names: list[str]
    dims: dict[str, sp.Expr]           # quantity -> linear form in free symbols
    free: list[sp.Symbol]
    forbidden: list[tuple[str, sp.Expr]] = field(default_factory=list)


def _walk(e: sp.Basic, dim_of: dict[sp.Symbol, sp.Expr], req: list[tuple[str, sp.Expr]]) -> sp.Expr:
    """Return the dimension form of e; append required-zero forms (reason, form) to req."""
    if e.is_Number or e in (sp.pi, sp.E):
        return sp.Integer(0)
    if isinstance(e, sp.Symbol):
        if e not in dim_of:
            raise DimensionError(f"unknown quantity {e}")
        return dim_of[e]
    if isinstance(e, sp.Mul):
        return sp.expand(sum((_walk(a, dim_of, req) for a in e.args), sp.Integer(0)))
    if isinstance(e, sp.Pow):
        base, ex = e.args
        ex = sp.sympify(ex).doit()
        if not ex.is_number:
            d_ex = _walk(ex, dim_of, req)
            req.append((f"exponent {ex} must be dimensionless", d_ex))
            d_b = _walk(base, dim_of, req)
            req.append((f"base {base} with variable exponent must be dimensionless", d_b))
            return sp.Integer(0)
        return sp.expand(ex * _walk(base, dim_of, req))
    if isinstance(e, sp.Add):
        terms = list(e.args)
        d0 = _walk(terms[0], dim_of, req)
        for t in terms[1:]:
            req.append((f"'{terms[0]}' and '{t}' are added, so must have equal dimensions",
                        sp.expand(_walk(t, dim_of, req) - d0)))
        return d0
    if isinstance(e, _TRANSCENDENTAL):
        d = _walk(e.args[0], dim_of, req)
        req.append((f"argument of {e.func.__name__}({e.args[0]}) must be dimensionless", d))
        return sp.Integer(0)
    if isinstance(e, sp.Abs):
        return _walk(e.args[0], dim_of, req)
    raise DimensionError(f"unsupported construct {e.func}")


def build_dim_model(formal: dict) -> DimModel:
    names = formal["quantities"]
    if len(set(names)) != len(names) or not all(re.fullmatch(r"[A-HJ-Z]", n) and n != "E" for n in names):
        raise DimensionError("quantities must be distinct single capital letters (not E or I: reserved constants)")
    syms = {n: sp.Symbol(n) for n in names}
    unknown = {syms[n]: sp.Symbol(f"d_{n}") for n in names}
    lhs_s, rhs_s = formal["relation"].split("=")
    req: list[tuple[str, sp.Expr]] = []
    dl = _walk(parse(lhs_s, syms, evaluate=False), unknown, req)
    dr = _walk(parse(rhs_s, syms, evaluate=False), unknown, req)
    eqs = [f for _, f in req] + [sp.expand(dl - dr)]
    sol = sp.linsolve(eqs, list(unknown.values()))
    if sol == sp.S.EmptySet:
        raise DimensionError("relation is dimensionally impossible")
    (vec,) = list(sol)
    free = sorted(set().union(*[v.free_symbols for v in vec]), key=str)
    dims = {n: sp.expand(v) for n, v in zip(names, vec)}
    forbidden: list[tuple[str, sp.Expr]] = []
    if formal.get("none_dimensionless", True):
        forbidden += [(f"{n} is not dimensionless", dims[n]) for n in names]
    if formal.get("all_different", True):
        forbidden += [(f"{a} and {b} have different dimensions", sp.expand(dims[a] - dims[b]))
                      for a, b in itertools.combinations(names, 2)]
    # The stated facts must themselves be consistent with the relation.
    for why, f in forbidden:
        if f == 0:
            raise DimensionError(f"relation contradicts the stated facts: {why}")
    return DimModel(names, dims, free, forbidden)


def _vec(form: sp.Expr, free: list[sp.Symbol]) -> sp.Matrix:
    p = sp.Poly(form, *free) if free else None
    return sp.Matrix([[p.coeff_monomial(s) if p is not None else 0 for s in free]])


def _in_span(f: sp.Expr, forms: list[sp.Expr], free: list[sp.Symbol]) -> bool:
    if not forms:
        return False
    M = sp.Matrix.vstack(*[_vec(g, free) for g in forms])
    return sp.Matrix.vstack(M, _vec(f, free)).rank() == M.rank()


@dataclass
class OptionVerdict:
    expression: str
    verdict: str  # ALWAYS | NEVER | CONTINGENT
    trace: list[str]
    reason: str


def classify(model: DimModel, expr: str) -> OptionVerdict:
    syms = {n: sp.Symbol(n) for n in model.names}
    req: list[tuple[str, sp.Expr]] = []
    d = _walk(parse(expr, syms, evaluate=False), {syms[n]: model.dims[n] for n in model.names}, req)
    show = lambda f: _pretty(f, model)  # noqa: E731
    trace = [f"[{n}] = {show(model.dims[n])}" for n in model.names]
    nonzero = [(w, f) for w, f in req if sp.expand(f) != 0]
    for w, f in req:
        trace.append(f"{w}: mismatch {show(f)}" if sp.expand(f) != 0 else f"{w}: OK")
    trace.append(f"overall dimension {show(d)}")
    if not nonzero:
        return OptionVerdict(expr, "ALWAYS", trace, "every sum and function argument is dimensionally consistent")
    forms = [f for _, f in nonzero]
    for why, f in model.forbidden:
        if _in_span(f, forms, model.free):
            return OptionVerdict(expr, "NEVER", trace,
                                 f"making it consistent would require violating: {why}")
    return OptionVerdict(expr, "CONTINGENT", trace,
                         "consistency depends on dimensions the question does not fix (ambiguous option)")


def _pretty(form: sp.Expr, model: DimModel) -> str:
    """Express a linear form back in terms of quantity dimensions where possible."""
    if form == 0:
        return "dimensionless"
    # choose base quantities whose dims equal single free symbols
    base = {}
    for n in model.names:
        f = model.dims[n]
        if f in model.free and f not in base:
            base[f] = n
    if all(s in base for s in model.free):
        p = sp.Poly(form, *model.free)
        parts = []
        for s in model.free:
            c = p.coeff_monomial(s)
            if c != 0:
                parts.append(f"[{base[s]}]" + ("" if c == 1 else f"^{c}"))
        return " ".join(parts)
    return str(form)


# --------------------------------------------------------------- verification
def verify_dimension_item(formal: dict, options: list[tuple[str, str]], declared_correct: list[str],
                          single_correct: bool = True) -> tuple[list[VerificationRecord], dict[str, OptionVerdict]]:
    recs: list[VerificationRecord] = []
    try:
        model = build_dim_model(formal)
    except Exception as e:  # noqa: BLE001
        return [VerificationRecord(check_id="dim.model", status=CheckStatus.FAILED, method="linear dimension solve",
                                   result=str(e))], {}
    recs.append(VerificationRecord(
        check_id="dim.model", status=CheckStatus.EXACT_CHECKED, method="linear solve of relation constraints",
        tool=TOOL, assumptions=["log/exp/trig arguments dimensionless", "only equal dimensions can be added",
                                "stated facts: none dimensionless, all different"],
        result="; ".join(f"[{n}]={_pretty(model.dims[n], model)}" for n in model.names)))
    verdicts: dict[str, OptionVerdict] = {}
    for oid, ex in options:
        try:
            verdicts[oid] = classify(model, ex)
        except Exception as e:  # noqa: BLE001
            recs.append(VerificationRecord(check_id="dim.options", status=CheckStatus.FAILED,
                                           method="classify", result=f"{oid}: {e}"))
            return recs, verdicts
    cont = [o for o, v in verdicts.items() if v.verdict == "CONTINGENT"]
    if cont:
        recs.append(VerificationRecord(check_id="dim.options", status=CheckStatus.FAILED, method="classify",
                                       tool=TOOL, result=f"options {cont} are neither always nor never meaningful "
                                                         f"-> question ambiguous"))
        return recs, verdicts
    want = "NEVER" if formal.get("ask", "not_meaningful") == "not_meaningful" else "ALWAYS"
    correct = sorted(o for o, v in verdicts.items() if v.verdict == want)
    recs.append(VerificationRecord(check_id="dim.options", status=CheckStatus.EXACT_CHECKED, method="classify",
                                   tool=TOOL, result=", ".join(f"{o}:{v.verdict}" for o, v in verdicts.items())))
    if single_correct and len(correct) != 1:
        recs.append(VerificationRecord(check_id="options.cardinality", status=CheckStatus.FAILED,
                                       method="per-option classification", tool=TOOL,
                                       result=f"{len(correct)} options satisfy the question: {correct}"))
    else:
        recs.append(VerificationRecord(check_id="options.cardinality", status=CheckStatus.EXACT_CHECKED,
                                       method="per-option classification", tool=TOOL, result=f"correct {correct}"))
    ok = sorted(declared_correct) == correct
    recs.append(VerificationRecord(check_id="key.matches_derivation",
                                   status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                   method="declared key vs derived key", tool=TOOL,
                                   result=f"declared {sorted(declared_correct)}; derived {correct}"))
    # distinctness: two options with identical structure are duplicates
    exprs = [sp.srepr(parse(ex, {n: sp.Symbol(n) for n in formal["quantities"]})) for _, ex in options]
    if len(set(exprs)) != len(exprs):
        recs.append(VerificationRecord(check_id="options.distinct", status=CheckStatus.FAILED,
                                       method="structural compare", result="two options are the same expression"))
    else:
        recs.append(VerificationRecord(check_id="options.distinct", status=CheckStatus.EXACT_CHECKED,
                                       method="structural compare", tool=TOOL, result="all distinct"))
    return recs, verdicts


# --------------------------------------------------------------- generation
# Every template must leave all four dimensions distinct and non-zero
# (enforced by tests/test_dimensions.py::test_templates_consistent).
RELATION_TEMPLATES = [
    "{a}*{d} = {c}*log({b}*{d})",
    "{a}/{d} = {c}*log({b}*{d})",
    "{a} = {c}*{d}*exp({b}*{d})",
    "{a}*{b} = {c}*sin({b}*{d})",
    "{a} = {b}*{c}*exp(-{d}*{c})",
]


def candidate_combinations(names: list[str]) -> list[str]:
    """Small exam-style combinations: X/Y - Z, (X - Y)/Z, X*Y - Z, X/(Y*Z) - W*Z^2/X ..."""
    out = []
    for x, y, z in itertools.permutations(names, 3):
        out += [f"{x}/{y} - {z}", f"({x} - {y})/{z}", f"{x}*{y} - {z}", f"{x}/{y} + {z}"]
    for x, y, z, w in itertools.permutations(names, 4):
        out += [f"{x}/({y}*{z}) - {w}*{z}**2/{x}", f"{x}*{z} - {y}"]
    return out


def generate_formal(seed: int, ask: str = "not_meaningful") -> dict:
    rng = random.Random(seed)
    letters = ["A", "B", "C", "D"]
    perm = letters[:]
    rng.shuffle(perm)
    tmpl = rng.choice(RELATION_TEMPLATES)
    rel = tmpl.format(a=perm[0], b=perm[1], c=perm[2], d=perm[3])
    return {"kind": "dimension_meaningful", "quantities": letters, "relation": rel, "ask": ask,
            "none_dimensionless": True, "all_different": True, "seed": seed}


def pick_options(formal: dict, n: int = 4, seed: int = 0) -> Optional[tuple[list[str], list[OptionVerdict]]]:
    """1 option with the asked property + (n-1) with the opposite; never CONTINGENT ones."""
    model = build_dim_model(formal)
    rng = random.Random(seed)
    pool = candidate_combinations(model.names)
    rng.shuffle(pool)
    want = "NEVER" if formal.get("ask", "not_meaningful") == "not_meaningful" else "ALWAYS"
    other = "ALWAYS" if want == "NEVER" else "NEVER"
    right, wrong = None, []
    seen: set[str] = set()
    syms = {n: sp.Symbol(n) for n in model.names}
    for ex in pool:
        key = sp.srepr(parse(ex, syms))  # canonical form: 'A*C - B' == 'C*A - B'
        if key in seen:
            continue
        seen.add(key)
        v = classify(model, ex)
        if v.verdict == want and right is None:
            right = v
        elif v.verdict == other and len(wrong) < n - 1:
            wrong.append(v)
        if right and len(wrong) == n - 1:
            return [right.expression] + [w.expression for w in wrong], [right] + wrong
    return None


def render_dimension_stem(formal: dict) -> str:
    q = ", ".join(formal["quantities"][:-1]) + " and " + formal["quantities"][-1]
    rel = formal["relation"].replace("**", "^").replace("log(", "ln(")
    rel = re.sub(r"\*(?=(ln|exp|sin|cos|tan)\()", " ", rel).replace("*", "")
    ask = "is not a meaningful quantity" if formal.get("ask", "not_meaningful") == "not_meaningful" \
        else "is a meaningful quantity"
    return (f"{q} are four different physical quantities having different dimensions. None of them is "
            f"dimensionless. It is known that the equation {rel} holds true. Which of the following "
            f"combinations {ask}?")
