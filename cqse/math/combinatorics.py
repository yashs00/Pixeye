"""Counting engine (kind "combinatorics"): every count is established by TWO independent methods.

  1. CLOSED FORM.  A declarative counting expression written from the stem (factorials, nCr, nPr,
     multinomials, sums/products over cases, inclusion-exclusion, stars and bars, circular arrangements,
     derangements, Stirling numbers, divisor counting ...), evaluated with exact integer / rational arithmetic.
  2. ENUMERATION.  The objects themselves are generated (smart generators: distinct arrangements of a
     multiset, sub-multisets, bounded compositions, set partitions, rotation classes ...) over a declared
     universe, filtered by declared predicates, and counted (or summed).
  The two must agree.  When the true instance exceeds the enumeration budget, the SAME declarative model is
  enumerated on declared scaled-down instances and the closed form must match there; this weaker evidence is
  recorded as RULE_CHECKED with a limitation, never as EXACT_CHECKED.  Anything unproven -> value None.

Formal
------
{
  "kind": "combinatorics",
  "model":  ["reading of the stem, conventions (words = arrangements, no leading zero, ...)"],
  "let":    {"W": "'ASSASSINATION'", "k": "4"},          # instance constants (safe expressions, in order)
  "scaled": [{"W": "'ASSATION'"}, ...],                  # overrides of `let` for scaled-down enumeration
  "params": {"n": {"domain": "natural", "box": [1, 80]}},# unknowns solved from equations
  "equations":   ["N == 1750"],                          # safe expressions with a single ==
  "constraints": ["n >= 3"],                             # selection rules (safe boolean expressions)
  "complete_box": "reason the box is the whole domain",  # optional: box scan counts as a complete search
  "quantities": {                                        # evaluated in order; may use earlier quantities
     "N": {"closed": "C(5+n, 3) - C(5, 3) - C(n, 3)",
           "enum": {"universe": {"type": "selections", "items": "[('b', i) for i in range(5)] + "
                                                         "[('g', i) for i in range(n)]", "size": 3},
                    "where": "0 < sum(1 for t in x if t[0] == 'b') < 3",
                    "agg": "count"}}},                   # or {"sum": "num(x)"}; default count
  "target": "N",                                         # safe expression in params / lets / quantities
  "claims": {"A": "N <= 100", "B": "100 < N <= 140"}     # optional: option TEXT transcribed as predicates;
}                                                        #   then value = sum 2^(i-1) over true claims i
                                                         #   (option values 1, 2, 4, 8 ...)

Universes (`x` is the candidate inside predicates; string-valued fields are safe expressions):
  product        {"sets": [S1, S2, ...]} | {"alphabet": S, "length": k}       tuples (ordered, repetition)
  functions      {"domain": D, "codomain": S}                                 tuple of images, in D order
  arrangements   {"items": multiset, "length": k (default all)}              DISTINCT k-arrangements (tuples)
  selections     {"items": multiset, "size": k | "sizes": [..] (default any)} DISTINCT sub-multisets (sorted)
  compositions   {"total": n, "parts": k, "lo": a | [a_i], "hi": b | [b_i]}  integer k-tuples with sum n
  set_partitions {"items": S, "blocks": k | "max_blocks": k}                 unordered partitions (tuple of blocks)
  integer_partitions {"total": n, "max_parts": k}                             non-increasing positive tuples
  range          {"lo": a, "hi": b}                                           integers a..b (x is an int)
  circular       {"items": distinct S}                                        one representative per rotation
  direct         {"value": expr}                                              literal evaluation of the stem's
                                                                              expression (no objects); used for
                                                                              algebraic items - recorded as such
Safe expressions: Python expression syntax checked by an AST whitelist (no attributes, no lambdas, no
keywords, no dunder / underscore names, no floats; ``/`` is exact rational division; ``**`` is size-capped);
builtins limited to len sum set frozenset sorted abs min max all any range tuple list int str bool zip
enumerate reversed divmod; helpers: C P fact mperm multinomial derange stirling2 bell npart gcd lcm isprime
tau divisors vp legendre num digits word count adj noadj together cadj cnoadj ilog2 floor ceil lexrank.
Parameters: solved (a) symbolically by sympy (expand_func / gammasimp, all integer roots of the resulting
polynomial system, domain + constraints applied) and (b) by an exact integer scan of the declared box using
the closed forms; enumeration re-checks the closed forms at the solutions and further box points.  The two
solution sets must coincide and the target must be unique; a box-only search is RULE_CHECKED with a
limitation unless "complete_box" justifies it.
"""
from __future__ import annotations

import ast
import itertools
import math
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from typing import Any, Callable, Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded
from cqse.core.result import EngineResult

TOOL = f"cqse-combinatorics 1.0; sympy {sp.__version__}"
BUDGET = 2_500_000            # candidates per enumeration (runtime: whole chapter in < 3 min)
BOX_ENUM_BUDGET = 2_000_000   # total candidates for enumeration over a parameter box
EXTRA_POINTS = 8              # non-solution box points where closed forms are re-checked by enumeration
MAX_BOX = 200_000
MAX_EXPR = 3000
DOMAINS = {"natural", "nonnegative", "integer"}


class ModelError(ValueError):
    """Malformed or unsafe formal -> FAILED."""


class Unsupported(ValueError):
    """Construct not modelled -> UNRESOLVED."""


class TooLarge(Exception):
    pass


# ======================================================================= helpers (numeric)
def _int(v) -> int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, Fraction) and v.denominator == 1:
        return v.numerator
    if isinstance(v, sp.Basic) and v.is_Integer:
        return int(v)
    raise Unsupported(f"integer expected, got {v!r}")


def _is_sym(*a) -> bool:
    return any(isinstance(v, sp.Basic) and not v.is_number for v in a)


def C(n, k):
    if _is_sym(n, k):
        return sp.binomial(n, k)
    n, k = _int(n), _int(k)
    if k < 0 or n < 0 or k > n:
        return 0
    return math.comb(n, k)


def P(n, k):
    if _is_sym(n, k):
        return sp.ff(n, k)
    n, k = _int(n), _int(k)
    if k < 0 or n < 0 or k > n:
        return 0
    return math.perm(n, k)


def fact(n):
    if _is_sym(n):
        return sp.factorial(n)
    n = _int(n)
    if n < 0:
        raise Unsupported("factorial of a negative integer")
    if n > 5000:
        raise Unsupported("factorial argument too large")
    return math.factorial(n)


def mperm(*a):
    """Distinct arrangements of a multiset: mperm('MISSISSIPPI') or mperm(4, 4, 2, 1) (multiplicities)."""
    if len(a) == 1 and not isinstance(a[0], int):
        cnt = list(Counter(a[0]).values())
    else:
        cnt = [_int(v) for v in a]
    r = math.factorial(sum(cnt))
    for c in cnt:
        r //= math.factorial(c)
    return r


def multinomial(n, *ks):
    n = _int(n)
    ks = [_int(k) for k in ks]
    if sum(ks) != n or min(ks, default=0) < 0:
        return 0
    return mperm(*ks)


@lru_cache(maxsize=None)
def derange(n: int) -> int:
    n = _int(n)
    if n == 0:
        return 1
    if n == 1:
        return 0
    return (n - 1) * (derange(n - 1) + derange(n - 2))


@lru_cache(maxsize=None)
def stirling2(n: int, k: int) -> int:
    n, k = _int(n), _int(k)
    if n == k:
        return 1
    if k == 0 or k > n:
        return 0
    return k * stirling2(n - 1, k) + stirling2(n - 1, k - 1)


def bell(n):
    return sum(stirling2(n, k) for k in range(_int(n) + 1))


@lru_cache(maxsize=None)
def npart(n: int, k: int) -> int:
    """Partitions of n into at most k positive parts."""
    n, k = _int(n), _int(k)
    if n == 0:
        return 1
    if k == 0 or n < 0:
        return 0
    return npart(n, k - 1) + npart(n - k, k)


def isprime(n) -> bool:
    n = _int(n)
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def _factor(n: int) -> dict:
    n = _int(n)
    if n <= 0:
        raise Unsupported("factorisation of a non-positive integer")
    out, p = {}, 2
    while p * p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p += 1
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def tau(n) -> int:
    r = 1
    for e in _factor(n).values():
        r *= e + 1
    return r


def divisors(n) -> tuple:
    n = _int(n)
    if n > 10**7:
        raise Unsupported("divisors(): argument too large")
    return tuple(d for d in range(1, n + 1) if n % d == 0)


def vp(n, p) -> int:
    n, p = _int(n), _int(p)
    if n == 0:
        raise Unsupported("valuation of 0")
    k = 0
    while n % p == 0:
        n //= p
        k += 1
    return k


def legendre(n, p) -> int:
    """v_p(n!) by Legendre's formula."""
    n, p = _int(n), _int(p)
    s, q = 0, p
    while q <= n:
        s += n // q
        q *= p
    return s


def num(x) -> int:
    v = 0
    for d in x:
        v = 10 * v + _int(d)
    return v


def digits(n) -> tuple:
    return tuple(int(c) for c in str(_int(n)))


def word(x) -> str:
    return "".join(str(t) for t in x)


def count(x, v) -> int:
    return sum(1 for t in x if t == v)


def adj(x, a, b) -> bool:
    return any((x[i] == a and x[i + 1] == b) or (x[i] == b and x[i + 1] == a) for i in range(len(x) - 1))


def noadj(x, group) -> bool:
    g = set(group)
    return not any(x[i] in g and x[i + 1] in g for i in range(len(x) - 1))


def together(x, group) -> bool:
    g = set(group)
    pos = [i for i, t in enumerate(x) if t in g]
    return not pos or pos[-1] - pos[0] + 1 == len(pos)


def cadj(x, a, b) -> bool:
    n = len(x)
    return any((x[i] == a and x[(i + 1) % n] == b) or (x[i] == b and x[(i + 1) % n] == a) for i in range(n))


def cnoadj(x, group) -> bool:
    g, n = set(group), len(x)
    return not any(x[i] in g and x[(i + 1) % n] in g for i in range(n))


def ilog2(v) -> int:
    v = Fraction(v)
    if v <= 0:
        raise Unsupported("log of non-positive")
    k = v.numerator.bit_length() - v.denominator.bit_length()
    while Fraction(2) ** k > v:
        k -= 1
    while Fraction(2) ** (k + 1) <= v:
        k += 1
    return k


def floor(v):
    if _is_sym(v):
        return sp.floor(v)
    return math.floor(Fraction(v))


def ceil(v):
    if _is_sym(v):
        return sp.ceiling(v)
    return math.ceil(Fraction(v))


def lexrank(w) -> int:
    """1-based dictionary rank of w among the distinct arrangements of its own letters (closed formula:
    sum over positions of (#smaller unused letters) x multiset permutations of the rest)."""
    w = list(w)
    cnt = Counter(w)
    r = 0
    for ch in w:
        for c in sorted(cnt):
            if c >= ch:
                break
            if cnt[c] > 0:
                cnt[c] -= 1
                r += mperm(*[v for v in cnt.values() if v > 0]) if any(cnt.values()) else 1
                cnt[c] += 1
        cnt[ch] -= 1
    return r + 1


def _div(a, b):
    if _is_sym(a, b) or isinstance(a, sp.Basic) or isinstance(b, sp.Basic):
        return sp.sympify(a) / sp.sympify(b)
    if isinstance(a, (int, Fraction)) and isinstance(b, (int, Fraction)):
        if b == 0:
            raise ZeroDivisionError("division by zero")
        return Fraction(a) / Fraction(b)
    raise Unsupported(f"cannot divide {type(a).__name__} by {type(b).__name__}")


def _pow(a, b):
    if _is_sym(a, b):
        return sp.sympify(a) ** sp.sympify(b)
    if isinstance(b, Fraction) and b.denominator == 1:
        b = b.numerator
    if not isinstance(b, int):
        raise Unsupported("non-integer exponent")
    if abs(b) > 20000:
        raise Unsupported("exponent too large")
    if b < 0:
        return Fraction(1) / Fraction(a) ** (-b)
    return a ** b


SAFE_BUILTINS: dict[str, Any] = {
    "len": len, "sum": sum, "set": set, "frozenset": frozenset, "sorted": sorted, "abs": abs, "min": min,
    "max": max, "all": all, "any": any, "range": range, "tuple": tuple, "list": list, "int": int, "str": str,
    "bool": bool, "zip": zip, "enumerate": enumerate, "reversed": reversed, "divmod": divmod,
}
HELPERS: dict[str, Any] = {
    "C": C, "P": P, "fact": fact, "mperm": mperm, "multinomial": multinomial, "derange": derange,
    "stirling2": stirling2, "bell": bell, "npart": npart, "gcd": math.gcd, "lcm": math.lcm,
    "isprime": isprime, "tau": tau, "divisors": divisors, "vp": vp, "legendre": legendre, "num": num,
    "digits": digits, "word": word, "count": count, "adj": adj, "noadj": noadj, "together": together,
    "cadj": cadj, "cnoadj": cnoadj, "ilog2": ilog2, "floor": floor, "ceil": ceil, "lexrank": lexrank,
}
_INTERNAL = {"_div": _div, "_pow": _pow}
FUNCS = {**SAFE_BUILTINS, **HELPERS}

_OK_NODES = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
             ast.FloorDiv, ast.Mod, ast.Pow, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.Compare, ast.Eq,
             ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.IfExp, ast.Call, ast.Name,
             ast.Load, ast.Store, ast.Constant, ast.Tuple, ast.List, ast.Set, ast.Subscript, ast.Slice,
             ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.comprehension)


class _Rewrite(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, (ast.Div, ast.Pow)):
            fn = "_div" if isinstance(node.op, ast.Div) else "_pow"
            return ast.copy_location(ast.Call(func=ast.Name(id=fn, ctx=ast.Load()), args=[node.left, node.right],
                                              keywords=[]), node)
        return node


def check_safe(src: str, names: set[str]) -> ast.Expression:
    """Parse and whitelist-check a safe expression. `names` = variables visible to it."""
    if not isinstance(src, str) or not src.strip():
        raise ModelError("empty expression")
    if len(src) > MAX_EXPR:
        raise ModelError("expression too long")
    if "__" in src:
        raise ModelError(f"dunder in expression {src!r}")
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError as e:
        raise ModelError(f"syntax error in {src!r}: {e.msg}") from None
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
    for node in ast.walk(tree):
        if not isinstance(node, _OK_NODES):
            raise ModelError(f"construct {type(node).__name__} not allowed in {src!r}")
        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise ModelError(f"name {node.id!r} not allowed")
            if node.id not in names and node.id not in bound and node.id not in FUNCS:
                raise ModelError(f"unknown name {node.id!r} in {src!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
                raise ModelError(f"call of non-whitelisted function in {src!r}")
            if node.keywords:
                raise ModelError(f"keyword arguments not allowed in {src!r}")
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, float) or isinstance(v, complex) or v is None or v is Ellipsis or \
                    isinstance(v, bytes):
                raise ModelError(f"constant {v!r} not allowed (use exact integers / fractions)")
            if isinstance(v, str) and len(v) > 64:
                raise ModelError("string constant too long")
    return tree


def compile_expr(src: str, names: set[str], args: tuple[str, ...] = ()) -> Callable:
    """Validated expression -> Python callable f(env, *args)."""
    tree = check_safe(src, names | set(args))
    body = _Rewrite().visit(tree).body
    lam = ast.Expression(body=ast.Lambda(
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg=a) for a in args], vararg=None, kwonlyargs=[],
                           kw_defaults=[], kwarg=None, defaults=[]), body=body))
    ast.fix_missing_locations(lam)
    code = compile(lam, "<combinatorics>", "eval")

    def make(env: dict) -> Callable:
        g = {"__builtins__": {}}
        g.update(FUNCS)
        g.update(_INTERNAL)
        g.update(env)
        return eval(code, g)  # noqa: S307 - AST-whitelisted, no builtins

    return make


def safe_eval(src: str, env: dict) -> Any:
    return compile_expr(src, set(env))(env)()


# ======================================================================= generators
class Budget:
    def __init__(self, limit: int):
        self.limit, self.used = limit, 0

    def take(self, n: int = 1):
        self.used += n
        if self.used > self.limit:
            raise TooLarge(f"enumeration exceeds budget {self.limit}")


def _arrangements(items, k):
    if k < 0 or k > len(items):
        return
    cnt = Counter(items)
    keys = sorted(cnt, key=_sortkey)
    cur = []

    def rec(depth):
        if depth == k:
            yield tuple(cur)
            return
        for c in keys:
            if cnt[c]:
                cnt[c] -= 1
                cur.append(c)
                yield from rec(depth + 1)
                cur.pop()
                cnt[c] += 1
    yield from rec(0)


def _sortkey(v):
    return (type(v).__name__, v)


def _selections(items, sizes):
    cnt = Counter(items)
    keys = sorted(cnt, key=_sortkey)
    cur = []
    suffix = [0] * (len(keys) + 1)
    for i in range(len(keys) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + cnt[keys[i]]
    if sizes is not None and (not sizes or max(sizes) < 0):
        return

    def rec(i, left):
        if sizes is not None and len(cur) + suffix[i] < min(sizes):
            return
        if i == len(keys):
            if sizes is None or len(cur) in sizes:
                yield tuple(cur)
            return
        c = keys[i]
        for m in range(cnt[c] + 1):
            if sizes is not None and len(cur) + m > max(sizes):
                break
            cur.extend([c] * m)
            yield from rec(i + 1, left)
            del cur[len(cur) - m:]
    yield from rec(0, None)


def _compositions(total, parts, lo, hi):
    cur = []

    def rec(i, rem):
        if i == parts - 1:
            if lo[i] <= rem and (hi[i] is None or rem <= hi[i]):
                cur.append(rem)
                yield tuple(cur)
                cur.pop()
            return
        rest_lo = sum(lo[i + 1:])
        top = rem - rest_lo
        if hi[i] is not None:
            top = min(top, hi[i])
        for v in range(lo[i], top + 1):
            cur.append(v)
            yield from rec(i + 1, rem - v)
            cur.pop()
    if parts <= 0:
        return
    yield from rec(0, total)


def _set_partitions(items, blocks, max_blocks):
    items = list(items)
    n = len(items)
    cap = blocks if blocks is not None else (max_blocks if max_blocks is not None else n)
    assign = [0] * n

    def rec(i, used):
        if i == n:
            if blocks is None or used == blocks:
                yield tuple(tuple(items[j] for j in range(n) if assign[j] == b) for b in range(used))
            return
        if blocks is not None and used + (n - i) < blocks:
            return
        for b in range(min(used + 1, cap)):
            assign[i] = b
            yield from rec(i + 1, max(used, b + 1))
    if n == 0:
        if not blocks:
            yield ()
        return
    yield from rec(0, 0)


def _int_partitions(total, max_parts, max_part=None):
    if max_part is None:
        max_part = total
    if total == 0:
        yield ()
        return
    if max_parts == 0:
        return
    for first in range(min(total, max_part), 0, -1):
        for rest in _int_partitions(total - first, max_parts - 1, first):
            yield (first,) + rest


def _size_estimate(u: dict) -> Optional[int]:
    t = u["type"]
    if t == "product":
        r = 1
        for s in u["sets"]:
            r *= len(s)
        return r
    if t == "arrangements":
        items, k = u["items"], u["length"]
        if k == len(items):
            return mperm(items)
        return math.perm(len(items), k) if k <= len(items) else 0
    if t == "selections":
        poly = [1]                                   # coefficients of prod (1 + t + ... + t^m)
        for m_ in Counter(u["items"]).values():
            new = [0] * (len(poly) + m_)
            for i, c in enumerate(poly):
                for j in range(m_ + 1):
                    new[i + j] += c
            poly = new
        if u["sizes"] is None:
            return sum(poly)
        return sum(poly[s] for s in u["sizes"] if 0 <= s < len(poly))
    if t == "compositions":
        return math.comb(max(u["total"] - sum(u["lo"]), 0) + u["parts"] - 1, max(u["parts"] - 1, 0))
    if t == "set_partitions":
        n = len(u["items"])
        if u.get("blocks") is not None:
            return stirling2(n, u["blocks"])
        return bell(n)
    if t == "integer_partitions":
        return npart(u["total"], u["max_parts"])
    if t == "range":
        return max(0, u["hi"] - u["lo"] + 1)
    if t == "circular":
        return math.factorial(max(len(u["items"]) - 1, 0))
    return None


def _materialise(spec: dict, env: dict) -> dict:
    """Evaluate the string-valued fields of a universe spec."""
    out = {}
    for k, v in spec.items():
        if k == "type":
            out[k] = v
        elif k == "value":
            out[k] = v                      # evaluated lazily (direct)
        elif isinstance(v, str):
            out[k] = safe_eval(v, env)
        else:
            out[k] = v
    t = out.get("type")
    if t == "product":
        if "alphabet" in out:
            out["sets"] = [list(out["alphabet"])] * _int(out["length"])
        out["sets"] = [list(safe_eval(s, env) if isinstance(s, str) else s) for s in out["sets"]]
    elif t == "functions":
        out = {"type": "product", "sets": [list(out["codomain"])] * len(list(out["domain"]))}
    elif t == "arrangements":
        out["items"] = list(out["items"])
        out["length"] = _int(out.get("length", len(out["items"])))
    elif t == "selections":
        out["items"] = list(out["items"])
        if "size" in out:
            out["sizes"] = [_int(out["size"])]
        out["sizes"] = None if out.get("sizes") is None else [_int(s) for s in out["sizes"]]
    elif t == "compositions":
        p = _int(out["parts"])
        out["parts"], out["total"] = p, _int(out["total"])
        lo, hi = out.get("lo", 0), out.get("hi")
        out["lo"] = [_int(v) for v in lo] if isinstance(lo, (list, tuple)) else [_int(lo)] * p
        out["hi"] = [None if v is None else _int(v) for v in hi] if isinstance(hi, (list, tuple)) else \
            [None if hi is None else _int(hi)] * p
    elif t == "set_partitions":
        out["items"] = list(out["items"])
        for f in ("blocks", "max_blocks"):
            if out.get(f) is not None:
                out[f] = _int(out[f])
    elif t == "integer_partitions":
        out["total"] = _int(out["total"])
        out["max_parts"] = _int(out.get("max_parts", out["total"]))
    elif t == "range":
        out["lo"], out["hi"] = _int(out["lo"]), _int(out["hi"])
    elif t == "circular":
        out["items"] = list(out["items"])
        if len(set(out["items"])) != len(out["items"]):
            raise Unsupported("circular universe needs distinct items")
    elif t != "direct":
        raise ModelError(f"unknown universe type {t!r}")
    return out


def _generate(u: dict):
    t = u["type"]
    if t == "product":
        return itertools.product(*u["sets"])
    if t == "arrangements":
        return _arrangements(u["items"], u["length"])
    if t == "selections":
        return _selections(u["items"], u["sizes"])
    if t == "compositions":
        return _compositions(u["total"], u["parts"], u["lo"], u["hi"])
    if t == "set_partitions":
        return _set_partitions(u["items"], u.get("blocks"), u.get("max_blocks"))
    if t == "integer_partitions":
        return _int_partitions(u["total"], u["max_parts"])
    if t == "range":
        return iter(range(u["lo"], u["hi"] + 1))
    if t == "circular":
        it = u["items"]
        if not it:
            return iter([()])
        return ((it[0],) + p for p in itertools.permutations(it[1:]))
    raise ModelError(f"unknown universe type {t!r}")


def enumerate_quantity(spec: dict, env: dict, budget: Budget) -> tuple[Any, int]:
    """Returns (value, number of candidates examined)."""
    uni = spec.get("universe")
    if not isinstance(uni, dict) or "type" not in uni:
        raise ModelError("enum needs a universe with a type")
    u = _materialise(uni, env)
    if u["type"] == "direct":
        return safe_eval(u["value"], env), 0
    est = _size_estimate(u)
    if est is not None and est > budget.limit - budget.used:
        raise TooLarge(f"universe size ~{est} exceeds remaining budget {budget.limit - budget.used}")
    names = set(env)
    where = spec.get("where", [])
    if isinstance(where, str):
        where = [where]
    preds = [compile_expr(w, names, ("x",))(env) for w in where]
    agg = spec.get("agg", "count")
    if agg == "count":
        summand = None
    elif isinstance(agg, dict) and set(agg) == {"sum"}:
        summand = compile_expr(agg["sum"], names, ("x",))(env)
    else:
        raise ModelError(f"unknown aggregation {agg!r}")
    total, seen = 0, 0
    for x in _generate(u):
        seen += 1
        if seen & 1023 == 0:
            budget.take(1024)
        ok = True
        for p in preds:
            if not p(x):
                ok = False
                break
        if ok:
            total = total + (1 if summand is None else summand(x))
    budget.take(seen & 1023)
    return total, seen


# ======================================================================= model
def _norm(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, Fraction):
        return v.numerator if v.denominator == 1 else v
    if isinstance(v, sp.Basic) and v.is_Rational:
        return int(v) if v.is_Integer else Fraction(int(v.p), int(v.q))
    return v


def _to_sympy(v) -> sp.Basic:
    v = _norm(v)
    if isinstance(v, int):
        return sp.Integer(v)
    if isinstance(v, Fraction):
        return sp.Rational(v.numerator, v.denominator)
    if isinstance(v, sp.Basic):
        return v
    raise Unsupported(f"target value {v!r} is not a number")


class Model:
    def __init__(self, f: dict):
        self.f = f
        allowed = {"kind", "model", "let", "scaled", "params", "equations", "constraints", "complete_box",
                   "quantities", "target", "claims", "require", "note"}
        extra = set(f) - allowed
        if extra:
            raise ModelError(f"unknown fields {sorted(extra)}")
        self.params = dict(f.get("params", {}))
        for p, d in self.params.items():
            if not p.isidentifier() or p.startswith("_") or p in FUNCS:
                raise ModelError(f"bad parameter name {p!r}")
            if d.get("domain", "natural") not in DOMAINS:
                raise ModelError(f"bad domain for {p}")
            box = d.get("box")
            if not (isinstance(box, list) and len(box) == 2 and all(isinstance(b, int) for b in box)):
                raise ModelError(f"parameter {p} needs an integer box [lo, hi]")
        self.lets = dict(f.get("let", {}))
        self.scaled = list(f.get("scaled", []))
        self.quants = dict(f.get("quantities", {}))
        if not self.quants and "target" not in f and "claims" not in f:
            raise ModelError("nothing to compute")
        for q, spec in self.quants.items():
            if not q.isidentifier() or q.startswith("_") or q in FUNCS:
                raise ModelError(f"bad quantity name {q!r}")
            if "closed" not in spec or "enum" not in spec:
                raise ModelError(f"quantity {q} needs both a closed form and an enumeration")
        self.eqs = list(f.get("equations", []))
        self.cons = list(f.get("constraints", []))
        if self.params and not (self.eqs or self.cons):
            raise ModelError("parameters given but no equations / constraints")
        # static safety check of every expression with the full name set
        names = set(self.params) | set(self.lets) | set(self.quants)
        for src in list(self.lets.values()) + self.eqs + self.cons + [f.get("target", "0")] + \
                list(f.get("claims", {}).values()) + list(f.get("require", [])):
            check_safe(src, names)
        for s in self.scaled:
            if set(s) - set(self.lets):
                raise ModelError("scaled instance overrides an undeclared let")
            for v in s.values():
                check_safe(v, names)
        for q, spec in self.quants.items():
            check_safe(spec["closed"], names)
            e = spec["enum"]
            for k, v in (e.get("universe") or {}).items():
                if k != "type" and isinstance(v, str):
                    check_safe(v, names)
                if k == "sets" and isinstance(v, list):
                    for s_ in v:
                        if isinstance(s_, str):
                            check_safe(s_, names)
            w = e.get("where", [])
            for src in ([w] if isinstance(w, str) else w):
                check_safe(src, names | {"x"})
            agg = e.get("agg", "count")
            if isinstance(agg, dict):
                for src in agg.values():
                    check_safe(src, names | {"x"})
        for src in self.eqs:
            t = ast.parse(src, mode="eval").body
            if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)):
                raise ModelError(f"equation must be a single '==': {src!r}")

    # ------------------------------------------------------------- environments
    def base_env(self, point: dict, lets_override: Optional[dict] = None) -> dict:
        env = dict(point)
        lets = dict(self.lets)
        if lets_override:
            lets.update(lets_override)
        for k in self.lets:
            env[k] = safe_eval(lets[k], env)
        return env

    def closed_env(self, env: dict) -> dict:
        e = dict(env)
        for q, spec in self.quants.items():
            e[q] = _norm(safe_eval(spec["closed"], e))
        return e

    def enum_env(self, env: dict, budget: Budget) -> tuple[dict, int]:
        e, seen = dict(env), 0
        for q, spec in self.quants.items():
            v, s = enumerate_quantity(spec["enum"], e, budget)
            e[q] = _norm(v)
            seen += s
        return e, seen

    def holds(self, env: dict) -> bool:
        for src in self.cons + self.eqs:
            if not safe_eval(src, env):
                return False
        return True

    def domain_ok(self, point: dict) -> bool:
        for p, d in self.params.items():
            v = point[p]
            dom = d.get("domain", "natural")
            if dom == "natural" and v < 1 or dom == "nonnegative" and v < 0:
                return False
        return True


# ======================================================================= parameter solving
def _symbolic_solutions(m: Model) -> tuple[Optional[list[dict]], str]:
    syms = {p: sp.Symbol(p, integer=True) for p in m.params}
    if not m.eqs:
        return None, "no equations (constraints only)"
    if len(m.eqs) < len(m.params):
        return None, "fewer equations than parameters: no complete symbolic solve attempted"
    env = dict(syms)
    try:
        for k in m.lets:
            env[k] = safe_eval(m.lets[k], env)
        for q, spec in m.quants.items():
            env[q] = sp.sympify(safe_eval(spec["closed"], env))
        polys = []
        for src in m.eqs:
            t = ast.parse(src, mode="eval").body
            lhs = sp.sympify(safe_eval(ast.unparse(t.left), env))
            rhs = sp.sympify(safe_eval(ast.unparse(t.comparators[0]), env))
            d = sp.expand_func(lhs - rhs)
            d = sp.together(sp.expand(sp.gammasimp(d)))
            if d.has(sp.gamma, sp.factorial, sp.binomial, sp.ff, sp.RisingFactorial, sp.floor, sp.ceiling):
                if rhs != 0:
                    d = sp.together(sp.gammasimp(sp.combsimp(lhs / rhs)) - 1)
                if d.has(sp.gamma, sp.factorial, sp.binomial, sp.ff, sp.RisingFactorial, sp.floor, sp.ceiling):
                    return None, "closed form not reducible to a polynomial system"
            num_, _den = sp.fraction(sp.together(d))
            polys.append(sp.expand(num_))
        free = set().union(*[p.free_symbols for p in polys]) if polys else set()
        unknowns = [syms[p] for p in m.params]
        if free - set(unknowns):
            return None, "unexpected symbols"
        sols = sp.solve(polys, unknowns, dict=True)
    except Exception as e:  # noqa: BLE001 - symbolic route is optional; the box scan still runs
        return None, f"symbolic solve unavailable: {type(e).__name__}: {e}"
    out = []
    for s in sols:
        if any(v not in s for v in unknowns):
            return None, "underdetermined system (free parameter)"
        pt = {}
        for p, sy in syms.items():
            v = sp.nsimplify(s[sy])
            if v.free_symbols:
                return None, "parametric solution"
            if not (v.is_real and v.is_integer):
                pt = None
                break
            pt[p] = int(v)
        if pt is not None and pt not in out:
            out.append(pt)
    return out, f"sympy solve over the integers: {len(out)} integer root(s)"


def _admissible(m: Model, pt: dict) -> bool:
    if not m.domain_ok(pt):
        return False
    try:
        env = m.closed_env(m.base_env(pt))
        return m.holds(env)
    except (Unsupported, ZeroDivisionError, ValueError, TypeError):
        return False


# ======================================================================= pipeline
def _rec(cid, status, method, result, **kw) -> VerificationRecord:
    return VerificationRecord(check_id=cid, status=status, method=method, tool=TOOL, result=result, **kw)


def _values_equal(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    if isinstance(a, sp.Basic) or isinstance(b, sp.Basic):
        return sp.simplify(sp.sympify(a) - sp.sympify(b)) == 0
    return a == b


def _run(m: Model, res: EngineResult) -> None:
    f = m.f
    # ---------------- 1. parameters
    solutions = [{}]
    if m.params:
        names = list(m.params)
        ranges = [range(m.params[p]["box"][0], m.params[p]["box"][1] + 1) for p in names]
        size = math.prod(len(r) for r in ranges)
        if size > MAX_BOX:
            raise Unsupported(f"parameter box too large ({size})")
        box_sols = [dict(zip(names, vals)) for vals in itertools.product(*ranges)
                    if _admissible(m, dict(zip(names, vals)))]
        sym, how = _symbolic_solutions(m)
        if sym is not None:
            sym = [s for s in sym if _admissible(m, s)]
            outside = [s for s in sym if any(not (m.params[p]["box"][0] <= s[p] <= m.params[p]["box"][1])
                                            for p in names)]
            same = sorted(map(lambda d: tuple(sorted(d.items())), sym)) == \
                sorted(map(lambda d: tuple(sorted(d.items())), box_sols))
            if outside or not same:
                res.records.append(_rec("combinatorics.params", CheckStatus.FAILED, "sympy solve vs box scan",
                                        f"symbolic solutions {sym} vs box scan {box_sols} (outside box: {outside})"))
                return
            res.records.append(_rec("combinatorics.params", CheckStatus.EXACT_CHECKED,
                                    "sympy solve (complete) + exact box scan",
                                    f"{how}; admissible: {sym}; box scan agrees"))
        elif f.get("complete_box"):
            res.records.append(_rec("combinatorics.params", CheckStatus.EXACT_CHECKED, "exhaustive scan of the domain",
                                    f"admissible: {box_sols} ({how})", assumptions=[f["complete_box"]]))
        else:
            res.records.append(_rec("combinatorics.params", CheckStatus.RULE_CHECKED, "exact box scan",
                                    f"admissible in box: {box_sols} ({how})",
                                    limitations=["solutions searched only inside the declared box "
                                                 f"{dict((p, m.params[p]['box']) for p in names)}"]))
        if not box_sols:
            res.records.append(_rec("combinatorics.params", CheckStatus.FAILED, "box scan", "no admissible solution"))
            return
        solutions = box_sols
        # enumeration re-checks the closed forms (and the equations) at solutions and other box points
        if m.quants:
            budget = Budget(BOX_ENUM_BUDGET)
            pts = [dict(zip(names, vals)) for vals in itertools.product(*ranges)]
            others = [p for p in pts if p not in solutions and m.domain_ok(p)]
            step = max(1, len(others) // EXTRA_POINTS)
            ordered = solutions + others[::step][:EXTRA_POINTS]
            checked, mism, partial = 0, [], False
            for pt in ordered:
                if not m.domain_ok(pt):
                    continue
                try:
                    env = m.base_env(pt)
                    ce = m.closed_env(env)
                    ee, _ = m.enum_env(env, budget)
                except TooLarge:
                    partial = True
                    break
                except (Unsupported, ZeroDivisionError, ValueError, TypeError):
                    continue
                checked += 1
                for q in m.quants:
                    if not _values_equal(ce[q], ee[q]):
                        mism.append((pt, q, ce[q], ee[q]))
                if pt in solutions and not m.holds(ee):
                    mism.append((pt, "equations under enumeration", None, None))
            sol_checked = checked >= len(solutions) or not partial
            if mism:
                res.records.append(_rec("combinatorics.param_enum", CheckStatus.FAILED,
                                        "closed form vs enumeration over the box", f"mismatch {mism[:3]}"))
                return
            if checked == 0 or (partial and checked < len(solutions)):
                res.records.append(_rec("combinatorics.param_enum", CheckStatus.UNRESOLVED,
                                        "closed form vs enumeration over the box",
                                        "enumeration could not reach the solution point(s)"))
                return
            res.records.append(_rec("combinatorics.param_enum",
                                    CheckStatus.EXACT_CHECKED, "closed form vs enumeration over the box",
                                    f"closed forms agree with enumeration at {checked} box point(s)"
                                    + (" (budget reached; solutions included)" if partial else
                                       f" (solutions + {checked - len(solutions)} other box points)"),
                                    limitations=["enumeration stopped by budget"] if partial else []))
            _ = sol_checked
    # ---------------- 2. quantities, target, claims at every admissible solution
    finals, claim_sets = [], []
    for pt in solutions:
        env = m.base_env(pt)
        ce = m.closed_env(env)
        status, detail, limits = CheckStatus.EXACT_CHECKED, "", []
        if m.quants:
            try:
                ee, seen = m.enum_env(env, Budget(BUDGET))
                detail = f"full enumeration ({seen} candidates)"
            except TooLarge as e:
                if not m.scaled:
                    res.records.append(_rec("combinatorics.cross_check", CheckStatus.UNRESOLVED,
                                            "closed form vs enumeration", f"{e}; no scaled instances declared"))
                    return
                for inst in m.scaled:
                    senv = m.base_env(pt, inst)
                    sce = m.closed_env(senv)
                    see, _ = m.enum_env(senv, Budget(BUDGET))
                    for q in m.quants:
                        if not _values_equal(sce[q], see[q]):
                            res.records.append(_rec("combinatorics.cross_check", CheckStatus.FAILED,
                                                    "closed form vs enumeration (scaled instance)",
                                                    f"{q}: closed {sce[q]} != enumerated {see[q]} at {inst}"))
                            return
                ee = None
                status = CheckStatus.RULE_CHECKED
                detail = f"full instance too large ({e}); closed form matched enumeration on {len(m.scaled)} " \
                         f"scaled-down instance(s)"
                limits = ["full instance not enumerated: closed form validated on scaled-down instances only"]
            if ee is not None:
                bad = [(q, ce[q], ee[q]) for q in m.quants if not _values_equal(ce[q], ee[q])]
                if bad:
                    res.records.append(_rec("combinatorics.cross_check", CheckStatus.FAILED,
                                            "closed form vs enumeration", f"disagreement {bad}"))
                    return
            direct = [q for q, s in m.quants.items() if s["enum"]["universe"]["type"] == "direct"]
            if direct:
                detail += f"; {direct}: literal evaluation of the stem expression (no object enumeration)"
            res.records.append(_rec("combinatorics.cross_check", status, "closed form vs enumeration",
                                    f"{pt or ''} " + ", ".join(f"{q}={ce[q]}" for q in m.quants) + f"; {detail}",
                                    limitations=limits))
        else:
            ee = None
        tracks = [ce] + ([ee] if ee is not None else [])
        for src in f.get("require", []):
            if not all(bool(safe_eval(src, tr)) for tr in tracks):
                res.records.append(_rec("combinatorics.require", CheckStatus.FAILED, "required facts",
                                        f"required fact fails: {src}"))
                return
        if "claims" in f:
            truths = []
            for tr in tracks:
                truths.append({k: bool(safe_eval(v, tr)) for k, v in f["claims"].items()})
            if any(t != truths[0] for t in truths):
                res.records.append(_rec("combinatorics.claims", CheckStatus.FAILED, "claims under both tracks",
                                        f"claims differ between closed form and enumeration: {truths}"))
                return
            claim_sets.append(truths[0])
            from cqse.verification.formats import label_index
            finals.append(sum(2 ** (label_index(k) - 1) for k, v in truths[0].items() if v))
        else:
            vals = [safe_eval(f["target"], tr) for tr in tracks]
            if not all(_values_equal(vals[0], v) for v in vals[1:]):
                res.records.append(_rec("combinatorics.target", CheckStatus.FAILED, "target under both tracks",
                                        f"{vals}"))
                return
            finals.append(_norm(vals[0]))
    uniq = []
    for v in finals:
        if not any(_values_equal(v, u) for u in uniq):
            uniq.append(v)
    if len(uniq) != 1:
        res.records.append(_rec("combinatorics.unique", CheckStatus.FAILED, "target over admissible solutions",
                                f"target not unique: {uniq} over {solutions}"))
        return
    value = _to_sympy(uniq[0])
    if "claims" in f:
        res.records.append(_rec("combinatorics.claims", CheckStatus.EXACT_CHECKED, "option claims evaluated",
                                f"true claims {[k for k, v in claim_sets[0].items() if v]} -> code {value}"))
        res.steps.append(f"true claims: {[k for k, v in claim_sets[0].items() if v]}")
    res.value = value
    res.steps.insert(0, f"solutions {solutions}" if m.params else "no parameters")


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - registry signature
    res = EngineResult()
    st: dict = {}

    def _build():
        try:
            st["m"] = Model(formal)
        except ModelError as e:
            return _rec("combinatorics.structure", CheckStatus.FAILED, "schema + AST whitelist", str(e))
        except Unsupported as e:
            return _rec("combinatorics.structure", CheckStatus.UNRESOLVED, "schema + AST whitelist", str(e))
        return _rec("combinatorics.structure", CheckStatus.EXACT_CHECKED, "schema + AST whitelist",
                    f"{len(st['m'].quants)} quantity(ies), {len(st['m'].params)} parameter(s)",
                    assumptions=list(formal.get("model", [])))

    res.records.append(guarded("combinatorics.structure", _build, seconds=10))
    if "m" not in st or not res.records[-1].is_affirmative():
        return res
    m = st["m"]

    def _main():
        try:
            _run(m, res)
        except Unsupported as e:
            return _rec("combinatorics.run", CheckStatus.UNRESOLVED, "engine", f"unsupported: {e}")
        except TooLarge as e:
            return _rec("combinatorics.run", CheckStatus.UNRESOLVED, "engine", f"too large: {e}")
        except ModelError as e:
            return _rec("combinatorics.run", CheckStatus.FAILED, "engine", f"model error: {e}")
        return _rec("combinatorics.run", CheckStatus.EXACT_CHECKED, "engine", "completed")

    res.records.append(guarded("combinatorics.run", _main, seconds=90))
    if res.value is None and all(r.is_affirmative() for r in res.records if r.hard):
        res.records.append(_rec("combinatorics.value", CheckStatus.UNRESOLVED, "engine", "no value established"))
    if any(r.hard and not r.is_affirmative() for r in res.records):
        res.value = None
    res.records.append(VerificationRecord(
        check_id="model.correspondence", status=CheckStatus.UNRESOLVED,
        method="teacher confirms the formal state models the stem",
        result="counting model must be confirmed by a subject teacher",
        data={"model": formal.get("model", []), "target": formal.get("target"),
              "claims": formal.get("claims")}))
    return res
