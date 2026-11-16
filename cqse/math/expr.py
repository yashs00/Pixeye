"""Safe expression parsing, domain extraction and exact equivalence.

Key rule (blueprint 6.1 / 37.1): an algebraic transformation is valid only
under its assumptions. We therefore keep the UNEVALUATED expression tree to
recover every definedness condition (denominators, even roots, logs, inverse
trig ranges) that automatic simplification would silently discard
(e.g. x/x -> 1 loses x != 0).
"""
from __future__ import annotations

import re
from typing import Optional

import sympy as sp
from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations

_TRANSFORMS = standard_transformations + (convert_xor,)

_ALLOWED_FUNCS = {
    "sqrt": sp.sqrt, "log": sp.log, "ln": sp.log, "exp": sp.exp, "Abs": sp.Abs,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "pi": sp.pi, "E": sp.E, "I": sp.I, "oo": sp.oo,
    "Rational": sp.Rational, "Integer": sp.Integer,
}
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_DECIMAL = re.compile(r"(?<![A-Za-z_0-9.])(\d+\.\d*|\.\d+)(?![0-9.])")
_SAFE_CHARS = re.compile(r"^[0-9A-Za-z_+\-*/^().,{}\[\]\s]*$")


class UnsupportedExpression(ValueError):
    pass


def parse(s: str, symbols: dict[str, sp.Symbol] | None = None, evaluate: bool = True) -> sp.Expr:
    """Parse a math string with a strict whitelist (parse_expr uses eval internally)."""
    if not isinstance(s, str) or not s.strip():
        raise UnsupportedExpression("empty expression")
    if "__" in s or not _SAFE_CHARS.match(s):
        raise UnsupportedExpression(f"illegal characters in {s!r}")
    symbols = symbols or {}
    for tok in _TOKEN.findall(s):
        if tok not in _ALLOWED_FUNCS and tok not in symbols:
            raise UnsupportedExpression(f"unknown identifier {tok!r} in {s!r}")
    local = dict(_ALLOWED_FUNCS)
    local.update(symbols)
    # Printed decimals are exact: 1.962 -> Rational('1.962'), never a binary float.
    s = _DECIMAL.sub(lambda m: f"Rational('{m.group(0)}')", s)
    return parse_expr(s, local_dict=local, global_dict={"__builtins__": {}, **_base_globals()},
                      transformations=_TRANSFORMS, evaluate=evaluate)


def _base_globals() -> dict:
    # parse_expr needs these constructors available in its eval namespace.
    return {"Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float,
            "Rational": sp.Rational, "Function": sp.Function,
            "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow}


def parse_value(s: str, symbols: dict[str, sp.Symbol] | None = None) -> sp.Basic:
    """Parse an option/answer: expression, or finite set literal '{a, b}', or '{}'."""
    t = s.strip()
    if t.startswith("{") and t.endswith("}"):
        inner = t[1:-1].strip()
        if not inner:
            return sp.S.EmptySet
        return sp.FiniteSet(*[parse(p, symbols) for p in _split_top(inner)])
    return parse(t, symbols)


def _split_top(s: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def definedness_conditions(expr_uneval: sp.Basic) -> list[sp.Basic]:
    """Real-domain conditions under which an UNEVALUATED expression is defined.

    Raises UnsupportedExpression for constructs whose real domain we do not model
    (fail closed instead of guessing).
    """
    conds: list[sp.Basic] = []

    def walk(e: sp.Basic) -> None:
        if e.is_Atom:
            return
        if isinstance(e, sp.Pow):
            base, ex = e.args
            ex_v = sp.sympify(ex).doit()
            b = sp.sympify(base).doit()
            if ex_v.is_number:
                if ex_v.is_negative:
                    conds.append(sp.Ne(b, 0))
                if ex_v.is_Rational and not ex_v.is_Integer:
                    if ex_v.q % 2 == 0:
                        conds.append(b >= 0 if not ex_v.is_negative else b > 0)
                elif not ex_v.is_Rational:
                    conds.append(b > 0)  # irrational real power
            else:
                conds.append(b > 0)  # symbolic exponent: real power needs positive base
        elif isinstance(e, sp.log):
            conds.append(sp.sympify(e.args[0]).doit() > 0)
        elif isinstance(e, (sp.tan, sp.sec)):
            conds.append(sp.Ne(sp.cos(sp.sympify(e.args[0]).doit()), 0))
        elif isinstance(e, (sp.cot, sp.csc)):
            conds.append(sp.Ne(sp.sin(sp.sympify(e.args[0]).doit()), 0))
        elif isinstance(e, (sp.asin, sp.acos)):
            a = sp.sympify(e.args[0]).doit()
            conds.extend([a >= -1, a <= 1])
        elif isinstance(e, (sp.Add, sp.Mul, sp.exp, sp.Abs, sp.sin, sp.cos, sp.atan,
                            sp.Equality, sp.Rational, sp.Integer)):
            pass
        elif isinstance(e, sp.Function):
            raise UnsupportedExpression(f"domain of {e.func} not modelled")
        for a in e.args:
            walk(a)

    walk(expr_uneval)
    # Constant conditions: True is dropped; False is kept (expression never defined).
    return [c for c in conds if c is not sp.true]


def tri_equal(a: sp.Basic, b: sp.Basic, sym_list: Optional[list[sp.Symbol]] = None) -> Optional[bool]:
    """Exact equality: True / False / None (undecidable -> caller must treat as UNRESOLVED)."""
    if isinstance(a, sp.Set) or isinstance(b, sp.Set):
        return _set_equal(a, b)
    d = sp.simplify(a - b)
    if d == 0:
        return True
    if d.is_number:
        if d.is_zero is False:
            return False
        v = sp.N(d, 60)
        if v.is_real is not None and abs(complex(v)) > 1e-45:
            return False
        return None  # numerically zero but not proven
    # symbolic: a single nonzero sample disproves equality; zeros never prove it.
    free = sorted(d.free_symbols, key=str)
    import random
    rng = random.Random(1729)
    for _ in range(12):
        sub = {s: sp.Rational(rng.randint(-97, 97), rng.randint(1, 13)) for s in free}
        try:
            v = sp.N(d.subs(sub), 40)
        except Exception:  # noqa: BLE001
            continue
        if v.is_number and v.is_finite and abs(complex(v)) > 1e-25:
            return False
    return None


def _set_equal(a: sp.Basic, b: sp.Basic) -> Optional[bool]:
    if not (isinstance(a, sp.FiniteSet) or a == sp.S.EmptySet) or \
       not (isinstance(b, sp.FiniteSet) or b == sp.S.EmptySet):
        return None if isinstance(a, sp.Set) and isinstance(b, sp.Set) else False
    # FiniteSet de-duplicates only structurally identical members, so match by value.
    la, lb = list(a), list(b)
    used = [False] * len(lb)
    undecided = False
    for x in la:
        hit = False
        for j, y in enumerate(lb):
            if used[j]:
                continue
            r = tri_equal(x, y)
            if r is True:
                used[j] = hit = True
                break
            if r is None:
                undecided = True
        if not hit:
            return None if undecided else False
    if not all(used):
        return None if undecided else False
    return True


def is_exact_integer(v: sp.Basic) -> Optional[bool]:
    v = sp.simplify(v)
    if v.is_Integer:
        return True
    if v.is_number:
        if v.is_integer is False:
            return False
        if v.is_integer:
            return True
    return None
