"""Blind chapter batch pnc (Permutations And Combinations): written from blind/pnc/questions.md ONLY
(stems + options; keys and explanations sealed and never opened).

Engine: cqse/math/combinatorics.py (kind "combinatorics"): every count = closed form (my derivation) AND an
independent enumeration of the objects (or literal evaluation of the stem's expression for algebraic items).
Option values are transcribed from the option TEXT (evaluated exactly here with Python integers).  When an
option is a statement/interval rather than a number, the formal carries "claims" (option text as predicates)
and the engine value is the bit-code sum 2^(i-1) of the true claims -> option values 1, 2, 4, 8.

Standard JEE readings used throughout (stated per item where it matters):
  * "words" = arrangements of letters, with or without meaning;  * an n-digit number has no leading zero;
  * "numbers formed using digits ..." without a stated length: every length allowed by the stem;
  * dictionary order = lexicographic order of the distinct arrangements.
"""
from fractions import Fraction as Fr
from math import comb, factorial as fa, perm

BITS = {"A": "1", "B": "2", "C": "4", "D": "8"}
MATH = "MATHEMATICS"


def _s(v) -> str:
    if isinstance(v, Fr):
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return str(v)


def ov(**kw) -> dict:
    return {k: _s(v) for k, v in kw.items()}


def Q(closed: str, uni: dict, where=None, agg=None) -> dict:
    e = {"universe": uni}
    if where is not None:
        e["where"] = where
    if agg is not None:
        e["agg"] = agg
    return {"closed": closed, "enum": e}


def F(quantities: dict, target: str = "N", model=(), **extra) -> dict:
    f = {"kind": "combinatorics", "quantities": quantities, "model": list(model)}
    if target is not None:
        f["target"] = target
    f.update(extra)
    return f


def RNG(lo, hi):
    return {"type": "range", "lo": lo, "hi": hi}


def PROD(alphabet, length):
    return {"type": "product", "alphabet": alphabet, "length": length}


def PRODS(*sets):
    return {"type": "product", "sets": list(sets)}


def ARR(items, length=None):
    u = {"type": "arrangements", "items": items}
    if length is not None:
        u["length"] = length
    return u


def SEL(items, size=None, sizes=None):
    u = {"type": "selections", "items": items}
    if size is not None:
        u["size"] = size
    if sizes is not None:
        u["sizes"] = sizes
    return u


def COMP(total, parts, lo=0, hi=None):
    u = {"type": "compositions", "total": total, "parts": parts, "lo": lo}
    if hi is not None:
        u["hi"] = hi
    return u


def SETP(items, blocks=None, max_blocks=None):
    u = {"type": "set_partitions", "items": items}
    if blocks is not None:
        u["blocks"] = blocks
    if max_blocks is not None:
        u["max_blocks"] = max_blocks
    return u


def IPART(total, max_parts):
    return {"type": "integer_partitions", "total": total, "max_parts": max_parts}


def CIRC(items):
    return {"type": "circular", "items": items}


def DIRECT(expr):
    return {"type": "direct", "value": expr}


def STMT(formal, claim):
    return {"formal": formal, "claim": claim, "subject": MATH}


def CUR(t, note):
    return {"truth": t, "basis": "curated", "note": note}


D10 = list(range(10))

FORMALS = {
    # ================================================================== chunk 1
    "TIV9ByukNGgS1zIC": {
        "formal": F({"N": Q("3*5**3 - 1", RNG(1001, 3999), "set(digits(x)) <= {0, 1, 2, 3, 4}")},
                    model=["4-digit numbers with leading digit 1-3 over {0..4}; 1000 itself excluded (not > 1000)"]),
        "option_values": ov(A=125, B=105, C=374, D=625)},
    "e1EyFwNJvi8vSFaE": {
        "formal": F({"N": Q("5*6*6*4", PROD([0, 1, 2, 3, 5, 7], 4), "x[0] != 0 and x[3] % 2 == 1")},
                    model=["4-digit (no leading zero), odd last digit, repetition allowed"]),
        "option_values": ov(A=216, B=375, C=400, D=720)},
    "38m7NMVKw7MZYgve": {
        "formal": F({"N": Q("2*50*51/2 + 5*20*21/2 - 10*10*11/2", RNG(1, 100), "x % 2 == 0 or x % 5 == 0",
                            {"sum": "x"})}, model=["inclusion-exclusion on sums of multiples"]),
        "option_values": ov(A=3000, B=3050, C=3600, D=3250)},
    "shaQfGQgffjfRATa": {
        "formal": F({"N": Q("fact(5) + 4*fact(4)", ARR([0, 1, 2, 3, 4, 5], 5), "x[0] != 0 and sum(x) % 3 == 0")},
                    model=["digit sum 15 - omitted digit must be 0 or 3; no leading zero"]),
        "option_values": ov(A=312, B=3125, C=120, D=216)},
    "Ya9LDYYS0XiNoh28": {
        "formal": F({"N": Q("C(5,4)*C(8,6) + C(5,5)*C(8,5)", SEL(list(range(13)), 10),
                            "sum(1 for q in x if q < 5) >= 4")}, model=["questions 0-4 are the first five"]),
        "option_values": ov(A=346, B=140, C=196, D=280)},
    "EkC57Q2rx3Nbk6Jx": {
        "formal": F({"N": Q("fact(m-1)*P(m, w)",
                            CIRC("[('m', i) for i in range(m)] + [('w', i) for i in range(w)]"),
                            "all(not (x[i][0] == 'w' and x[(i+1) % len(x)][0] == 'w') for i in range(len(x)))")},
                    let={"m": "6", "w": "5"}, scaled=[{"m": "4", "w": "3"}, {"m": "5", "w": "4"}, {"m": "6", "w": "4"},
                                                      {"m": "5", "w": "5"}],
                    model=["distinct people, round table: arrangements up to rotation; men first, women in gaps"]),
        "option_values": ov(A=fa(7) * fa(5), B=fa(6) * fa(5), C=fa(30), D=fa(5) * fa(4)),
        "note": "full instance 10! circular arrangements exceeds budget: closed form checked on scaled instances"},
    "txW7MxHrrC595ct0": {
        "formal": F({"G": Q("tuple(C(n+2, r+1) for n in range(1, 13) for r in range(1, n+1))",
                            DIRECT("tuple(C(n, r+1) + C(n, r-1) + 2*C(n, r) for n in range(1, 13) "
                                   "for r in range(1, n+1))"))},
                    target=None,
                    claims={"A": "G == tuple(C(n+1, r+1) for n in range(1, 13) for r in range(1, n+1))",
                            "B": "G == tuple(C(n+2, r) for n in range(1, 13) for r in range(1, n+1))",
                            "C": "G == tuple(C(n+2, r+1) for n in range(1, 13) for r in range(1, n+1))",
                            "D": "G == tuple(C(n+1, r) for n in range(1, 13) for r in range(1, n+1))"},
                    model=["identity: closed form by Pascal twice; literal LHS evaluated on the grid 1<=r<=n<=12"]),
        "option_values": BITS,
        "note": "identity checked exactly on a finite grid (not a symbolic proof); Pascal's rule derivation"},
    "n1oWTwJqCyxG22uT": {
        "formal": F({"N": Q("fact(6)/2", ARR(list("GARDEN")), "[t for t in x if t in 'AE'] == ['A', 'E']")},
                    model=["vowels A, E must appear in the order A before E"]),
        "option_values": ov(A=480, B=240, C=360, D=120)},
    "cxhMyG1Oo7EJnOxq": {
        "formal": F({"N": Q("C(7, 2)", COMP(8, 3, lo=1))}, model=["identical balls, distinct boxes, each >= 1"]),
        "option_values": ov(A=comb(8, 3), B=21, C=3 ** 8, D=5)},
    "MWbLRehjPiKaEgcg": {
        "formal": F({"N": Q("lexrank('SACHIN') - 1", ARR(list("SACHIN")), "x < tuple('SACHIN')")},
                    target="N + 1", model=["rank = 1 + number of arrangements before SACHIN"]),
        "option_values": ov(A=601, B=600, C=603, D=602)},
    "WAd9iWoQGJdqmxc0": {
        "formal": F({"N": Q("C(10,1) + C(10,2) + C(10,3) + C(10,4)", SEL(list(range(10)), sizes=[1, 2, 3, 4]))},
                    model=["a vote = a non-empty set of at most 4 of the 10 candidates"]),
        "option_values": ov(A=5040, B=6210, C=385, D=1110)},
    "wZ6fkRvOqG6GRUaw": {
        "formal": F({"N": Q("fact(12)/fact(4)**3", PROD(["A", "B", "C"], 12),
                            "count(x, 'A') == 4 and count(x, 'B') == 4")},
                    model=["the parts are the NAMED sets A, B, C (ordered): label each element A/B/C, 4 each"]),
        "option_values": ov(A=Fr(fa(12), fa(4) ** 3), B=Fr(fa(12), fa(4) ** 4), C=Fr(fa(12), 6 * fa(4) ** 3),
                            D=Fr(fa(12), 6 * fa(4) ** 4)),
        "note": "reading: A, B, C are named (labelled) sets; unordered reading would give option C"},
    "CtCfGCORzMr3qyUf": {
        "formal": F({"N": Q("mperm('MIIIIPP') * C(8, 4)", ARR(list("MISSISSIPPI")), "noadj(x, 'S')")},
                    model=["gap method: arrange the 7 non-S letters, place 4 S in 4 of the 8 gaps"]),
        "option_values": ov(A=8 * comb(6, 4) * comb(7, 4), B=6 * 7 * comb(8, 4), C=6 * 8 * comb(7, 4),
                            D=7 * comb(6, 4) * comb(8, 4))},
    "pW3FNSb5ohyzwnDR": {
        "formal": {"kind": "statement_set", "format": "assertion_reason", "statements": {
            "A": STMT(F({"N": Q("C(10, 4)", COMP(6, 5))}, model=["6 ice-creams of 5 types: multisets"]),
                      "== 252"),
            "R": STMT(F({"N": Q("C(10, 4)", COMP(6, 5)), "M": Q("C(10, 4)", ARR(list("AAAAAABBBB")))},
                        target="N - M", model=["ways to buy vs arrangements of 6 A and 4 B"]), "== 0")}},
        "option_values": {"A": "4", "B": "3", "C": "2", "D": "1"},
        "note": "Statement-1 / Statement-2 mapped to assertion_reason codes (A false R true = 4); "
                "10C5 = 252 is the claimed value in statement 1"},
    "KscQ5CpVa6h3aZAR": {
        "formal": F({"N": Q("C(6, 4)*3*fact(4)",
                            ARR("[('n', i) for i in range(6)] + [('d', i) for i in range(3)]", 5),
                            "x[2][0] == 'd' and sum(1 for t in x if t[0] == 'd') == 1")},
                    target=None,
                    claims={"A": "500 <= N < 750", "B": "750 <= N < 1000", "C": "N >= 1000", "D": "N < 500"},
                    model=["distinct novels and dictionaries; 5 books in a row, the single dictionary in slot 3"]),
        "option_values": BITS},
    "gu4xEM8HE3wz9OiX": {
        "formal": F({"N": Q("C(3, 2)*C(9, 2)",
                            SEL("[('r', i) for i in range(3)] + [('b', i) for i in range(9)]", 4),
                            "sum(1 for t in x if t[0] == 'r') == 2")},
                    model=["choose the 2 red to move and the 2 blue to move; transfer is then determined"]),
        "option_values": ov(A=36, B=66, C=108, D=3)},
    "hZ0WqGlvxb9cOBdE": {
        "formal": F({"N": Q("C(10, 3) - C(6, 3)", SEL(list(range(10)), 3), "not all(p < 6 for p in x)")},
                    target=None,
                    claims={"A": "N <= 100", "B": "100 < N <= 140", "C": "140 < N <= 190", "D": "N > 190"},
                    model=["points 0-5 collinear, no other three collinear"]),
        "option_values": BITS},
    "lWJFreINJxGWYGy2": {
        "formal": {"kind": "statement_set", "format": "assertion_reason", "statements": {
            "A": STMT(F({"N": Q("C(9, 3)", COMP(10, 4, lo=1))}, model=["identical balls, distinct boxes, >= 1"]),
                      "== 84"),
            "R": STMT(F({"N": Q("C(9, 3)", SEL(list(range(9)), 3))}, model=["3 of 9 places"]), "== 84")},
            "explains": CUR(True, "stars and bars: choosing 3 of the 9 gaps between 10 balls = 9C3")},
        "option_values": {"A": "2", "B": "1", "C": "4", "D": "3"},
        "note": "9C3 = 84; 'correct explanation' is a curated judgement (gap method), teacher to confirm"},
    "FrmiixXJ0JcQkToz": {
        "formal": F({"N": Q("11*10*8 - 1", SEL(["W"] * 10 + ["G"] * 9 + ["B"] * 7), "len(x) >= 1")},
                    model=["identical balls of each colour: a selection = (w, g, b) counts, not all zero"]),
        "option_values": ov(A=880, B=629, C=630, D=879)},
    "foj68NgT56Ij10bv": {
        "formal": F({"T1": Q("C(n, 3)", SEL("list(range(n))", 3)),
                     "T2": Q("C(n+1, 3)", SEL("list(range(n+1))", 3))},
                    target="n", params={"n": {"domain": "natural", "box": [3, 60]}},
                    equations=["T2 - T1 == 10"], constraints=["n >= 3"],
                    model=["triangles from vertices of a regular n-gon: any 3 vertices (no three collinear)"]),
        "option_values": ov(A=7, B=5, C=10, D=8)},
    "CMaU4ZiR4nN6vcs3UI1qpqahkk8g5fe1k": {
        "formal": F({"N": Q("2**8 - C(8,0) - C(8,1) - C(8,2)", SEL(list(range(8)), sizes=[3, 4, 5, 6, 7, 8]))},
                    model=["|A x B| = 8"]),
        "option_values": ov(A=219, B=211, C=256, D=220)},
    "cpWdidtToPeRE0b1": {
        "formal": F({"N4": Q("3*P(4, 3)", ARR([3, 5, 6, 7, 8], 4), "num(x) > 6000"),
                     "N5": Q("fact(5)", ARR([3, 5, 6, 7, 8], 5), "num(x) > 6000")},
                    target="N4 + N5", model=["4-digit numbers > 6000 plus all 5-digit numbers (no repetition)"]),
        "option_values": ov(A=120, B=72, C=216, D=192)},
    "pOakikkdQhU84tLNpvMvZ": {
        "formal": F({"N": Q("8*8 - 5", ARR(list("MEDITERRANEAN"), 4), "x[0] == 'R' and x[3] == 'E'")},
                    model=["letters available with multiplicity; after R, E fixed: 8 distinct letters remain, "
                           "of which E, A, N still have 2 copies"]),
        "option_values": ov(A=Fr(fa(11), 8), B=110, C=56, D=59)},
    "uKpYZD2xI25YxVqSvGYd0": {
        "formal": F({"S": Q("10*fact(11)", DIRECT("sum((r*r + 1)*fact(r) for r in range(1, 11))"))},
                    target="S", model=["(r^2+1) r! = r (r+1)! - (r-1) r!  telescopes to 10 * 11!"]),
        "option_values": ov(A=fa(11), B=10 * fa(11), C=101 * fa(10), D=11 * fa(11))},
    "IYJ08gkoyHdlZ5bWWXi8X": {
        "formal": F({"A6": Q("C(n+2, 6)", SEL("list(range(n+2))", 6)),
                     "B2": Q("P(n-2, 2)", ARR("list(range(n-2))", 2))},
                    target=None, params={"n": {"domain": "natural", "box": [1, 80]}},
                    equations=["A6 == 11*B2"], constraints=["n >= 4"],
                    claims={"A": "n*n + 3*n - 108 == 0", "B": "n*n + 5*n - 84 == 0", "C": "n*n + 2*n - 80 == 0",
                            "D": "n*n + n - 110 == 0"},
                    model=["nCr / nPr defined only for n-2 >= 2 and n+2 >= 6"]),
        "option_values": BITS},
    # ================================================================== chunk 2
    "IplDhMsmdCoRdapu": {
        "formal": F({"N": Q("lexrank('SMALL') - 1", ARR(list("SMALL")), "x < tuple('SMALL')")}, target="N + 1",
                    model=["dictionary rank among distinct arrangements of S, M, A, L, L"]),
        "option_values": ov(A=46, B=59, C=52, D=58)},
    "4sIda7kghDbn5SBTSeZMx": {
        "formal": F({"N": Q("lexrank('QUEEN') - 1", ARR(list("QUEEN")), "x < tuple('QUEEN')")}, target="N + 1",
                    model=["dictionary rank among distinct arrangements of Q, U, E, E, N"]),
        "option_values": ov(A=44, B=45, C=46, D=47)},
    "J7rxWs0HNWj60oLGyuAiC": {
        "formal": F({"N": Q("fact(7) - 2*fact(6)", CIRC(["B1", "B2", "B3", "B4", "B5", "G1", "G2", "G3"]),
                            "not cadj(x, 'B1', 'G1')")},
                    model=["8 distinct people round table (rotations identified); complement of B1G1 adjacent"]),
        "option_values": ov(A=5 * fa(6), B=6 * fa(6), C=fa(7), D=5 * fa(7))},
    "hPoq3OSkej5kavXb": {
        "formal": F({"N": Q("sum((C(4, i)*C(3, 3-i))**2 for i in range(4))",
                            SEL("[('XL', i) for i in range(4)] + [('XM', i) for i in range(3)] + "
                                "[('YL', i) for i in range(3)] + [('YM', i) for i in range(4)]", 6),
                            ["sum(1 for t in x if t[0][1] == 'L') == 3",
                             "sum(1 for t in x if t[0][0] == 'X') == 3"])},
                    model=["X: 4 ladies, 3 men; Y: 3 ladies, 4 men; 3 ladies + 3 men with 3 friends of each"]),
        "option_values": ov(A=468, B=469, C=484, D=485)},
    "xe5ZfgVxYCdbpMKEGIuOF": {
        "formal": F({"N": Q("P(5, 4) + 2*C(4, 2)*mperm(2, 1, 1) + mperm(2, 2)", ARR(list("BARRACK"), 4))},
                    model=["4-letter arrangements from the multiset B, A, A, R, R, C, K: all distinct / one pair / "
                           "two pairs"]),
        "option_values": ov(A=120, B=144, C=264, D=270)},
    "XLd4i0VsYtBkRaHaQmAcd": {
        "formal": F({"N": Q("3**n", PROD([2, 5, 7], "n")), "M": Q("3**(n-1)", PROD([2, 5, 7], "n-1"))},
                    target="n", params={"n": {"domain": "natural", "box": [1, 30]}},
                    constraints=["N >= 900", "M < 900"],
                    complete_box="3^(n-1) >= 900 for every n > 30 and 3^n < 900 for n < 7: the box covers all candidates",
                    model=["n-digit numbers using only digits 2, 5, 7 (repetition allowed): 3^n; smallest n with "
                           "3^n >= 900"]),
        "option_values": ov(A=6, B=7, C=8, D=9)},
    "dE3mDjQalcUd2nH6": {
        "formal": F({"N": Q("C(6, 4)*3*fact(4)",
                            ARR("[('n', i) for i in range(6)] + [('d', i) for i in range(3)]", 5),
                            "x[2][0] == 'd' and sum(1 for t in x if t[0] == 'd') == 1")},
                    target=None,
                    claims={"A": "750 <= N < 1000", "B": "N >= 1000", "C": "N < 500", "D": "500 <= N < 750"},
                    model=["distinct novels and dictionaries; 5 books in a row, the single dictionary in slot 3"]),
        "option_values": BITS},
    "vKUBJgogUkTqMHWSIq45x": {
        "formal": F({"N": Q("3*fact(3) + 2*fact(3)", ARR([0, 1, 2, 3, 4], 4),
                            "2000 < num(x) < 5000 and num(x) % 3 == 0")},
                    model=["4-digit numbers, distinct digits; digit sets {0,2,3,4} (lead 2,3,4) and {0,1,2,3} "
                           "(lead 2,3)"]),
        "option_values": ov(A=24, B=30, C=36, D=48)},
    "QpyXMtfVkQTUnuxoZ3qaz": {
        "formal": F({"N": Q("6**3 + 2*6**2 + 3*6 + 4", RNG(4322, 9999), "set(digits(x)) <= {0, 1, 2, 3, 4, 5}")},
                    model=["4-digit numbers > 4321 over digits 0-5 (repetition allowed)"]),
        "option_values": ov(A=306, B=288, C=310, D=360)},
    "iH5MBhbvLwnvCtEId43rsa0w2w9jxb03xdv": {
        "formal": F({"N": Q("C(5+n, 3) - C(5, 3) - C(n, 3)",
                            SEL("[('b', i) for i in range(5)] + [('g', i) for i in range(n)]", 3),
                            "0 < sum(1 for t in x if t[0] == 'b') < 3")},
                    target="n", params={"n": {"domain": "natural", "box": [1, 80]}}, equations=["N == 1750"],
                    model=["distinct students; teams with at least one boy and one girl"]),
        "option_values": ov(A=24, B=25, C=27, D=28)},
    "IiAhsoFZAqNRGsldWG3rsa0w2w9jx5e78h8": {
        "formal": F({"N": Q("2**20", SEL("['I']*10 + list(range(21))", 10))},
                    model=["j distinct objects (0<=j<=10) and 10-j identical ones: sum_{j<=10} 21Cj = 2^21/2"]),
        "option_values": ov(A=2 ** 20 - 1, B=2 ** 20, C=2 ** 20 + 1, D=2 ** 21)},
    "eOF6fmsz4KXubATcSH3rsa0w2w9jx2ay4se": {
        "formal": F({"N": Q("C(20, 2) - 20", SEL(list(range(20)), 2), "(x[1] - x[0]) % 20 not in (1, 19)")},
                    model=["pillars on a circle; a beam joins every non-adjacent pair"]),
        "option_values": ov(A=180, B=210, C=170, D=190)},
    "T7pubLMDX4L70jGUBQ3rsa0w2w9jwy0oxdn": {
        "formal": F({"N": Q("(fact(3) - fact(2))*fact(3) + fact(3)*fact(3)", ARR([0, 1, 2, 5, 7, 9], 6),
                            "x[0] != 0 and num(x) % 11 == 0")},
                    model=["all six digits used once; alternating sums 12/12 force {0,5,7} | {1,2,9}"]),
        "option_values": ov(A=36, B=60, C=72, D=48)},
    "ynFU9TI4bBJDhzTbt7TZv": {
        "formal": F({"m": Q("C(8,6)*C(5,5) + C(8,7)*C(5,4) + C(8,8)*C(5,3)",
                            SEL("[('M', i) for i in range(8)] + [('F', i) for i in range(5)]", 11),
                            "sum(1 for t in x if t[0] == 'M') >= 6"),
                     "n": Q("C(5,3)*C(8,8) + C(5,4)*C(8,7) + C(5,5)*C(8,6)",
                            SEL("[('M', i) for i in range(8)] + [('F', i) for i in range(5)]", 11),
                            "sum(1 for t in x if t[0] == 'F') >= 3")},
                    target=None,
                    claims={"A": "n == m - 8", "B": "m == n == 78", "C": "m + n == 68", "D": "m == n == 68"},
                    model=["distinct people"]),
        "option_values": BITS},
    "VyKFCxCKFLUFzxl6WeXIp": {
        "formal": F({"N": Q("C(4, 3)*mperm(2, 1)*mperm(4, 2)", ARR([1, 1, 2, 2, 2, 2, 3, 4, 4]),
                            "all(x[i] % 2 == 0 for i in (0, 2, 4, 6, 8))")},
                    model=["9 places, even places 2,4,6,8; odd digits 1,1,3 must sit in even places "
                           "(equivalently odd places hold only even digits)"]),
        "option_values": ov(A=175, B=162, C=160, D=180)},
    "wyrLSbxVQxkAIJHo7FrTT": {
        "formal": F({"GM": Q("2*C(m, 2)", SEL("list(range(m))", 2), agg={"sum": "2"}),
                     "GW": Q("2*2*m", PRODS("list(range(m))", [0, 1], [0, 1]))},
                    target="m", params={"m": {"domain": "natural", "box": [1, 80]}},
                    equations=["GM - GW == 84"], model=["every pair of participants plays 2 games"]),
        "option_values": ov(A=12, B=9, C=7, D=11)},
    "d9rYjwxlxiAXsKNTjN8AV": {
        "formal": F({"N": Q("C(10, 3)", PROD(list(range(1, 11)), 3), "x[0] < x[1] < x[2]")}),
        "option_values": ov(A=164, B=240, C=82, D=120)},
    "nopfCkMOXIUlIZhNggMvD": {
        "formal": F({"K": Q("2**25", DIRECT("sum(C(50, r)*C(50 - r, 25 - r) for r in range(26)) / C(50, 25)"))},
                    target="K", model=["50Cr * (50-r)C(25-r) = 50C25 * 25Cr"]),
        "option_values": ov(A=2 ** 24, B=2 ** 25 - 1, C=2 ** 25, D=625)},
    "va6hXgEJsJa8x7wVuocWG": {
        "formal": F({"N": Q("4 + 4*5 + 4*25 + 2*125", RNG(1, 6999), "set(digits(x)) <= {0, 1, 3, 7, 9}")},
                    model=["natural numbers (no leading zero) of 1-4 digits below 7000"]),
        "option_values": ov(A=374, B=372, C=375, D=250)},
    "UbyEKAsad53b322QnPdNK": {
        "formal": F({"N": Q("4*tau(100)", PRODS("list(range(-100, 101))", "list(range(-100, 101))"),
                            "abs(x[0]*x[1]) == 100")},
                    model=["vertices O, (a,0), (0,b) with nonzero integers a, b; area |ab|/2 = 50"]),
        "option_values": ov(A=9, B=18, C=36, D=32)},
    "CcpStCuUJqkQIn23GBxDt": {
        "formal": F({"N": Q("C(5, 2)*(C(7, 3) - C(5, 1))",
                            SEL("[('g', i) for i in range(5)] + [('b', i) for i in range(7)]", 5),
                            ["sum(1 for t in x if t[0] == 'g') == 2", "not (('b', 0) in x and ('b', 1) in x)"])},
                    model=["boys 0 and 1 are A and B"]),
        "option_values": ov(A=500, B=350, C=200, D=300)},
    "E0UshBABGmQdzdNVQPjgy2xukg4n2d68": {
        "formal": F({"N": Q("mperm('LETTER') - mperm('LTTR') * 5", ARR(list("LETTER")), "not together(x, 'E')")},
                    model=["vowels E, E never adjacent (never together); EE block: 5 units with T,T"]),
        "note": "EE block arrangements = 5!/2! = 60 = mperm('LTTR')*5"},
    "peQrKRXgQeisz7wOkTjgy2xukfuv9z75": {
        "formal": F({"N": Q("fact(3)*fact(a)*fact(b)*fact(c)",
                            ARR("[('F', i) for i in range(a)] + [('G', i) for i in range(b)] + "
                                "[('H', i) for i in range(c)]"),
                            ["together(x, [('F', i) for i in range(a)])", "together(x, [('G', i) for i in range(b)])",
                             "together(x, [('H', i) for i in range(c)])"])},
                    let={"a": "3", "b": "3", "c": "4"},
                    scaled=[{"a": "2", "b": "2", "c": "3"}, {"a": "3", "b": "2", "c": "3"}, {"a": "1", "b": "3", "c": "4"}],
                    model=["distinct people; each family a contiguous block: 3! block orders x internal orders"]),
        "option_values": ov(A=2 * 6 * 24, B=6 ** 3 * 24, C=6 * 24 ** 3, D=36 * 24)},
    "ogAhHOb39XAuEA27w1jgy2xukfqbzbjj": {
        "formal": F({"N": Q("3*C(5, 3)*5*5 + 3*C(5, 2)*C(5, 2)*5", SEL(list(range(15)), 5),
                            "set(q // 5 for q in x) == {0, 1, 2}")},
                    model=["questions 5s..5s+4 belong to section s"]),
        "option_values": ov(A=2250, B=2255, C=3000, D=1500)},
    "C8HGleU1NgkvV0IfgIjgy2xukfjjwd85": {
        "formal": F({"N": Q("2*C(5, 2)*mperm(2, 1, 1)", ARR(list("SYLLABUS"), 4),
                            "sorted(count(x, c) for c in set(x)) == [1, 1, 2]")},
                    model=["pattern: one repeated letter (S or L) + two other distinct letters"]),
    },
    # ================================================================== chunk 3
    "dGIKlgBoeVJkXafbxljgy2xukfjjsiul": {
        "formal": F({"N": Q("6**4*(1 - (2/3)**4 - 4*(1/3)*(2/3)**3)", PROD([1, 2, 3, 4, 5, 6], 4),
                            "sum(1 for d in x if d in (3, 5)) >= 2")},
                    target="27*N/6**4",
                    model=["expected count = 27 x P(at least two of four dice show 3 or 5); P(face in {3,5}) = 1/3"])},
    "FnMRlmZon3hFFMIfYv7k9k2k5ior0st": {
        "formal": F({"N": Q("8*P(8, 3)", ARR(D10, 5), "x[0] != 0 and x[3] == 2")}, target="N/336",
                    model=["five-digit numbers (no leading zero), distinct digits, tens digit 2"]),
        "option_values": ov(A=6, B=8, C=4, D=7)},
    "SLjj7ptO9uQcIkLlhTjgy2xukfakunkv": {
        "formal": F({"N": Q("C(6, 4)*3**2", PROD([0, 1, 2, 3], 6), "count(x, 0) == 4")},
                    model=["answer 0 is the correct alternative of each question; every question answered"])},
    "t2DoGkNqDTClpiz752jgy2xukf49ludb": {
        "formal": F({"N": Q("C(11, 2) - 1", RNG(100, 999), "sum(digits(x)) == 10")},
                    model=["a' = a-1 >= 0: a'+b+c = 9 (55 solutions) minus a' = 9 (a = 10)"])},
    "5PYzxgZ7ICeBa0uH9Ijgy2xukez5kjog": {
        "formal": F({"B": Q("n", SEL("list(range(n))", 2), "(x[1] - x[0]) % n in (1, n - 1)"),
                     "R": Q("C(n, 2) - n", SEL("list(range(n))", 2), "(x[1] - x[0]) % n not in (1, n - 1)")},
                    target="n", params={"n": {"domain": "natural", "box": [3, 220]}}, equations=["R == 99*B"],
                    constraints=["n > 3"],
                    model=["stations on a circle: n nearest-neighbour pairs (blue), all other pairs red"]),
        "option_values": ov(A=201, B=199, C=101, D=200)},
    "KcZ71werwgGvco0DDojgy2xukf0wa8ut": {
        "formal": F({"S": Q("1 + fact(52)",
                            DIRECT("sum((-1)**(k+1)*(k+1)*P(k, k-1) for k in range(1, 52)) + "
                                   "sum((-1)**(k+1)*fact(k) for k in range(1, 52))"))},
                    target="S", model=["k-th term of the first bracket (-1)^(k+1) (k+1) kP(k-1) = (-1)^(k+1) (k+1)!"]),
        "option_values": ov(A=1, B=1 + fa(51), C=1 - 51 * fa(51), D=1 + fa(52))},
    "lrAD8xOCEl2vEKUBAe7k9k2k5e2s565": {
        "formal": F({"N": Q("5*mperm(2, 1, 1, 1, 1)", PROD([1, 3, 5, 7, 9], 6), "set(x) == {1, 3, 5, 7, 9}")},
                    model=["one of the five digits repeated once"]),
        "option_values": ov(A=Fr(5 * fa(6), 2), B=fa(6), C=5 ** 6, D=Fr(fa(6), 2))},
    "mfec6lSyyVk6WkwqUq7k9k2k5fifl9j": {
        "formal": F({"N": Q("2*len([s for s in range(1, 10) if 4 <= s*s <= 9])",
                            PRODS("list(range(0, 36))", "list(range(-40, 41))"),
                            "6*C(35, x[0]) == (x[1]**2 - 3)*C(36, x[0] + 1)")},
                    model=["read as 6 . 35C_r = (k^2 - 3) . 36C_(r+1) (the '+1' is the subscript r+1 lost in "
                           "rendering); 36C(r+1) = 36/(r+1) 35Cr gives r+1 = 6(k^2-3), 0 <= r <= 35",
                           "enumeration over 0<=r<=35, |k|<=40 (k^2-3 <= 6 forces |k| <= 3)"]),
        "option_values": ov(A=6, B=3, C=2, D=4),
        "note": "subscript reading C_{r+1} (standard form of this item); literal 'C_r + 1' not used"},
    "Df2NYHYq0uAHcIQV3H7k9k2k5gjegt5": {
        "formal": F({"a": Q("C(19, 9)", DIRECT("max(C(19, p) for p in range(20))")),
                     "b": Q("C(20, 10)", DIRECT("max(C(20, q) for q in range(21))")),
                     "c": Q("C(21, 10)", DIRECT("max(C(21, r) for r in range(22))"))},
                    target=None,
                    claims={"A": "a/11 == b/22 == c/21", "B": "a/10 == b/22 == c/21", "C": "a/10 == b/11 == c/42",
                            "D": "a/11 == b/22 == c/42"},
                    model=["greatest binomial coefficient: middle term(s)"]),
        "option_values": BITS},
    "qbRvgJn6hv5comatCj7k9k2k5hketjb": {
        "formal": F({"N": Q("P(8, 4) + 3*C(7, 2)*mperm(2, 1, 1) + C(3, 2)*mperm(2, 2)", ARR(list("EXAMINATION"), 4))},
                    model=["multiset E X A A M I I N N T O: 8 distinct letters, A, I, N doubled"])},
    "k3m0N9G0xSwL4wln7Cjgy2xukewtoyf9": {
        "formal": F({"N": Q("lexrank('MOTHER') - 1", ARR(list("MOTHER")), "x < tuple('MOTHER')")}, target="N + 1",
                    model=["dictionary rank"])},
    "TgQzv9xzFjU3klQ0D27k9k2k5h0eczd": {
        "formal": F({"N": Q("C(12, 4) - C(5, 4)",
                            SEL("[('r', i) for i in range(5)] + [('b', i) for i in range(4)] + "
                                "[('w', i) for i in range(3)]", 4),
                            "sum(1 for t in x if t[0] == 'r') <= 3")},
                    model=["marbles distinguishable (standard counting of draws)"])},
    "kWZNAunq6lVQD0QwtP1klrg0wg0": {
        "formal": F({"N": Q("C(6,2)*C(8,4) + C(6,3)*C(8,6) + C(6,4)*C(8,8)",
                            SEL("[('I', i) for i in range(6)] + [('F', i) for i in range(8)]"),
                            ["sum(1 for t in x if t[0] == 'I') >= 2",
                             "sum(1 for t in x if t[0] == 'F') == 2*sum(1 for t in x if t[0] == 'I')"])},
                    model=["foreigners exactly twice the Indians, at least 2 Indians"]),
        "option_values": ov(A=1050, B=575, C=560, D=1625)},
    "xFuZjzUptaNFdoUgdM1klrmy2in": {
        "formal": F({"N": Q("sum(C(10, k)*(2**(10 - k) - 2) for k in range(1, 4))", PROD(["A", "B", "C"], 10),
                            ["set(x) == {'A', 'B', 'C'}", "count(x, 'C') <= 3"])},
                    model=["groups A, B, C are labelled; each student in exactly one group"])},
    "OtCzg7Sq3gsThouMtK1kls4fv1n": {
        "formal": F({"N": Q("C(5, 2)*C(3, 2)", PROD(list(range(1, 25)), 3), "x[0]*x[1]*x[2] == 24")},
                    model=["24 = 2^3 3: distribute exponents among x, y, z"]),
        "option_values": ov(A=36, B=24, C=45, D=30)},
    "IGIb0SRhLxdVea31gf1kls5ho0j": {
        "formal": F({"N": Q("4*3 + 4*fact(3) - 2*2", ARR([1, 2, 3, 4, 5], 3), "num(x) % 3 == 0 or num(x) % 5 == 0")},
                    model=["3-digit numbers, distinct digits from 1-5; div by 5: last digit 5; div by 3: digit sets "
                           "{1,2,3},{1,3,5},{2,3,4},{3,4,5}"])},
    "eNLKKMO5cYrCM8Jz6S1kluge0sz": {
        "formal": F({"N": Q("C(9, 6) - 7", PROD([1, 2, 3], 7), "sum(x) == 10")},
                    model=["y_i = x_i - 1 in {0,1,2} summing to 3: C(9,6) minus 7 with a part 3"]),
        "option_values": ov(A=35, B=42, C=82, D=77)},
    "OjrcXgele0CMwAVPCy1kluvyg3b": {
        "formal": F({"N": Q("(y + 1)*(z + 1)", RNG(1, "3**y*5**z"), "(3**y*5**z) % x == 0 and x % 2 == 1")},
                    target=None, params={"y": {"domain": "natural", "box": [1, 12]},
                                         "z": {"domain": "natural", "box": [1, 12]}},
                    equations=["y + z == 5", "6*(y + z) == 5*y*z"], constraints=["y > z"],
                    claims={"A": "N == 11", "B": "N == 6", "C": "N == 12",
                            "D": "all(N == 6*t for t in range(0, 10))"},
                    model=["odd divisors of 2^x 3^y 5^z = divisors of 3^y 5^z (independent of x)",
                           "option D '6x' read as the count being 6x for the unknown exponent x (false: the "
                           "count does not depend on x)"]),
        "option_values": BITS},
    "I5Ortna4ugLS6ar8gn1kmiwfm5s": {
        "formal": F({"al": Q("5*7*6 + 5*7*9 + 5*6*9 + 7*6*9",
                             SEL("[(s, i) for s, k in (('AB', 5), ('CD', 7), ('BC', 6), ('DA', 9)) "
                                 "for i in range(k)]", 3), "len(set(t[0] for t in x)) == 3"),
                     "be": Q("5*7*6*9",
                             SEL("[(s, i) for s, k in (('AB', 5), ('CD', 7), ('BC', 6), ('DA', 9)) "
                                 "for i in range(k)]", 4), "len(set(t[0] for t in x)) == 4")},
                    target="be - al", model=["one point from each of 3 (resp. 4) different sides"]),
        "option_values": ov(A=717, B=795, C=1890, D=1173)},
    "FlAz2HmdDhqlvaBRdA1kmjbf0bo": {
        "formal": F({"M": Q("7*4", PRODS(list(range(7)), list(range(4)))),
                     "G": Q("n*6", PRODS("list(range(n))", "list(range(6))"))},
                    target="n", params={"n": {"domain": "natural", "box": [1, 60]}}, equations=["M + G == 52"],
                    model=["a single match: one boy of A vs one boy of B, or one girl of A vs one girl of B"]),
        "option_values": ov(A=5, B=2, C=4, D=6)},
    "uTYPsLQsZvZrwoOMNL1kmkl4mb8": {
        "formal": F({"N": Q("C(14, 3) - C(3, 3) - C(5, 3) - C(6, 3)",
                            SEL("[(s, i) for s, k in (('AB', 3), ('BC', 5), ('CA', 6)) for i in range(k)]", 3),
                            "len(set(t[0] for t in x)) > 1")},
                    model=["interior points of the same side are collinear; vertices A, B, C not used"]),
        "option_values": ov(A=240, B=360, C=333, D=364)},
    "v0HhheYanRw9k3ecDT1kmlj6yhm": {
        "formal": F({"S": Q("(6*2 + 3*1 + 3*3)*1111", ARR([1, 2, 2, 3]), agg={"sum": "num(x)"})}, target="S",
                    model=["12 distinct numbers; each place: 2 six times, 1 and 3 three times"]),
        "option_values": ov(A=26664, B=122664, C=122234, D=22264)},
    "vTTgxkoqnfAoseQRCc1kmlj9jej": {
        "formal": F({"N": Q("3*10**2", RNG(1, 1000), agg={"sum": "count(digits(x), 3)"})},
                    model=["000-999: each of 3 places shows 3 in 100 numbers; 1000 has none"])},
    "IMSC1eZiT13CQApXI81kmm3wdw0": {
        "formal": F({"S": Q("sum(fact(r+3) - 9*fact(r+1) + 8*fact(r) for r in range(1, 11))",
                            DIRECT("sum(fact(r)*(r**3 + 6*r**2 + 2*r + 5) for r in range(1, 11))"))},
                    target="S/fact(11)",
                    model=["r^3+6r^2+2r+5 = (r+1)(r+2)(r+3) - 9r - 1; r.r! = (r+1)! - r!"])},
    "1krq1dvgf": {
        "formal": F({"N": Q("C(6,4)*C(7,5)*C(2,2) + C(6,4)*C(7,6)*C(2,1) + C(6,5)*C(7,5)*C(2,1)",
                            SEL("[('bo', i) for i in range(6)] + [('ba', i) for i in range(7)] + "
                                "[('wk', i) for i in range(2)]", 11),
                            ["sum(1 for t in x if t[0] == 'bo') >= 4", "sum(1 for t in x if t[0] == 'ba') >= 5",
                             "sum(1 for t in x if t[0] == 'wk') >= 1"])},
                    model=["distinct players"])},
    # ================================================================== chunk 4
    "1kruajm92": {
        "formal": F({"N": Q("4*fact(4)", ARR([0, 2, 4, 6, 8], 5), "x[0] != 0 and num(x) > 10000")},
                    model=["only 5-digit numbers (distinct digits, no leading zero) exceed 10000"])},
    "1krw30swu": {
        "formal": F({"N": Q("C(5,2)*C(6,2)*C(8,6) + C(5,2)*C(6,3)*C(8,5) + C(5,3)*C(6,2)*C(8,5)",
                            SEL("[(10, i) for i in range(5)] + [(11, i) for i in range(6)] + "
                                "[(12, i) for i in range(8)]", 10),
                            ["all(sum(1 for t in x if t[0] == c) >= 2 for c in (10, 11, 12))",
                             "sum(1 for t in x if t[0] in (10, 11)) <= 5"])},
                    target="N/100", model=["distinct students"])},
    "1krygm1ew": {
        "formal": F({"N": Q("11*6*14", PRODS("list(range(11))", "list(range(11))", "list(range(12))",
                                             "list(range(14))"),
                            "(2**x[0]*5**x[1]*11**x[2]*13**x[3]) % 4 == 1")},
                    model=["divisor 2^a 5^b 11^c 13^d; = 1 mod 4 needs a = 0 and c even (5, 13 = 1; 11 = 3 mod 4)"])},
    "1krzq59sa": {
        "formal": F({"PA": Q("P(n, r)", ARR("list(range(n))", "r")), "PB": Q("P(n, r+1)", ARR("list(range(n))", "r+1")),
                     "CA": Q("C(n, r)", SEL("list(range(n))", "r")), "CB": Q("C(n, r-1)", SEL("list(range(n))", "r-1"))},
                    target="r", params={"n": {"domain": "natural", "box": [1, 40]},
                                        "r": {"domain": "natural", "box": [1, 40]}},
                    equations=["PA == PB", "CA == CB"], constraints=["r + 1 <= n"],
                    model=["nPr, nP(r+1), nCr, nC(r-1) all defined: 1 <= r, r+1 <= n"]),
        "option_values": ov(A=1, B=4, C=2, D=3)},
    "1ktbicc13": {
        "formal": F({"S": Q("fact(16) - 1", DIRECT("sum(k*P(k, k) for k in range(1, 16))"))},
                    target="C(q + s, r - s)",
                    params={"q": {"domain": "natural", "box": [1, 30]}, "r": {"domain": "natural", "box": [1, 30]},
                            "s": {"domain": "nonnegative", "box": [0, 1]}},
                    equations=["S == P(q, r) - s"], constraints=["r == q"],
                    complete_box="with r = q the equation is q! - s = 16! - 1 (s in {0,1}); q! > 16! for q > 16",
                    model=["sum k.k! = 16! - 1 written as qPr - s with qPr = q! (r = q, the standard form "
                           "(n+1)! = (n+1)P(n+1)); without r = q, 16P15 = 16! would also fit"]),
        "note": "ambiguity: 16P15 = 16P16 = 16!; standard reading r = q used (gives 17C15); r = 15 would give 17C14"},
    "1ktbiwpdb": {
        "formal": F({"N": Q("5*4 + 2*4*4", ARR([0, 1, 3, 4, 6, 7], 3), "x[0] != 0 and x[2] % 2 == 0")},
                    model=["last digit 0: 5x4; last digit 4 or 6: 4 (non-zero first) x 4"])},
    "1kteplg92": {
        "formal": F({"N": Q("10*10", PRODS("list(range(1, 10))", D10, D10),
                            "num((x[0], x[1], x[2], x[2], x[1], x[0])) % 55 == 0")},
                    model=["palindrome abccba; last digit a must be 5; abccba = 11(9091a + 910b + 100c)"])},
    "1ktgp4gdp": {
        "formal": F({"N": Q("2**7 - 2**3*(1 + 2*2 + 1)", SEL([1, 2, 3, 4, 5, 6, 9]),
                            "len(x) > 0 and sum(x) % 3 != 0")},
                    model=["residues: {3,6,9} = 0, {1,4} = 1, {2,5} = 2; sum = 0 mod 3 needs #res1 = #res2 mod 3"])},
    "1ktisnbyi": {
        "formal": F({"N": Q("fact(6) - fact(3)*fact(4)", ARR(list("VOWELS")), "not together(x, 'VWLS')")},
                    model=["'never come together' = the four consonants are not all in one block"])},
    "1kto82i38": {
        "formal": F({"N": Q("C(15, 3) - npart(12 - 3, 3)", SEL(list(range(1, 16)), 3), "sum(x) != 15")},
                    model=["P_i distinct points; triples {i<j<k} with i+j+k = 15 <-> partitions of 12 into 3 parts"]),
        "option_values": ov(A=12, B=419, C=443, D=455)},
    "1ktobhmqv": {
        "formal": F({"N": Q("2*(mperm(1, 1, 1, 2) - fact(4)) + 1 + 1 + 2", ARR(list("FARMER")),
                            ["not adj(x, 'R', 'R')", "x < tuple('FARMER')"])},
                    target="N + 1",
                    model=["list = arrangements of FARMER without RR adjacent, in dictionary order; before FARMER: "
                           "A..., E... (36 each), FAE.., FAM.. (1 each), FARE.. (2)"])},
    "1l546nn3x": {
        "formal": F({"N": Q("2*(M - 2)*(M - 3) - (M - 3)", ARR("list(range(1, M + 1))", 4),
                            "(x[1] == x[0] + 1 and x[2] == x[1] + 1) or (x[2] == x[1] + 1 and x[3] == x[2] + 1)")},
                    let={"M": "100"}, scaled=[{"M": "6"}, {"M": "8"}, {"M": "10"}, {"M": "13"}],
                    model=["'consecutive integers' read in order: b2 = b1 + 1, b3 = b2 + 1 (increasing)",
                           "inclusion-exclusion: 98 x 97 twice minus 97 runs of four"]),
        "note": "100P4 too large to enumerate: closed form checked on scaled ranges 1..M"},
    "1l54udtan": {
        "formal": F({"N": Q("sum((9 // d)*(9 // d + 1)**2 for d in range(1, 10))", RNG(1000, 9999),
                            "x % 10 != 0 and all(t % (x % 10) == 0 for t in digits(x)[:3])")},
                    model=["last digit d >= 1; leading digit: multiples of d in 1..9; others: multiples in 0..9"])},
    "1l55h4ytt": {
        "formal": F({"N": Q("sum(31 - a - b for a in range(4, 8) for b in range(2, 7))",
                            COMP(30, 4, lo=[0, 4, 2, 0], hi=[None, 7, 6, None]))},
                    model=["identical candies; C1, C4 unrestricted (>= 0)"]),
        "option_values": ov(A=205, B=615, C=510, D=430)},
    "1l5668ose": {
        "formal": F({"N": Q("2*fact(4) + fact(4)", ARR([1, 2, 3, 5, 6, 7], 5), "num(x) % 6 == 0")},
                    model=["digit sum 24 minus omitted digit (3 or 6) divisible by 3; even last digit"]),
        "option_values": ov(A=36, B=48, C=60, D=72)},
    "1l56rx9ym": {
        "formal": F({"N": Q("C(6, 3) + C(8, 3) + C(10, 3) - 4*C(4, 3)", PROD([0, 1, 2, 3, 4, 5], 4),
                            "sum(x) in (3, 5, 7)")},
                    model=["p in {3, 5, 7}; stars and bars with entries <= 5"])},
    "1l57p1hn1": {
        "formal": F({"N": Q("C(3 + 5, 5)", ARR(["B"] * 11 + ["R"] * 5),
                            "all(b - a >= 3 for a, b in zip([i for i in range(16) if x[i] == 'R'], "
                            "[i for i in range(16) if x[i] == 'R'][1:]))")},
                    model=["cubes of one colour identical; 4 inner gaps get >= 2 blue: 3 spare blue over 6 gaps"])},
    "1l58afhi6": {
        "formal": F({"N": Q("(C(10, 3) - C(8, 1))*C(5, 3)",
                            SEL("[('B', i) for i in range(1, 11)] + [('G', i) for i in range(1, 6)]", 6),
                            ["sum(1 for t in x if t[0] == 'B') == 3", "not (('B', 1) in x and ('B', 2) in x)"])})},
    "1l58h031t": {
        "formal": F({"N": Q("225 - 75", RNG(100, 999), "gcd(x, 36) == 2")},
                    model=["x = 2 mod 4 (225 such) and not divisible by 3 (x = 6 mod 12: 75)"])},
    "1l59le9dg": {
        "formal": F({"N": Q("900 - 9*9*8 - 9", RNG(100, 999), "sorted(count(digits(x), d) for d in set(digits(x))) == [1, 2]")},
                    model=["exactly one digit appears exactly twice"])},
    "1l5ajmbj0": {
        "formal": F({"N": Q("sum((t if 1 <= t <= 9 else (19 - t if 10 <= t <= 18 else 0)) "
                            "for S in (7, 14, 21) for c in (1, 3, 5, 7, 9) for t in [S - c])",
                            RNG(100, 999), "x % 2 == 1 and sum(digits(x)) % 7 == 0")},
                    model=["#(a, b) with a in 1..9, b in 0..9, a + b = t is t (t <= 9) or 19 - t (10..18)"])},
    "1l5ajwu4h": {
        "formal": F({"N": Q("mperm(5, 4) + mperm(6, 1, 2) + mperm(7, 2)", PROD([-1, 0, 1], 9), "sum(x) == 5")},
                    model=["(#1, #-1) = (5,0), (6,1), (7,2)"])},
    "1l5bb1vut": {
        "formal": F({"N": Q("4*fact(4)*fact(3)", ARR([1, 2, 3, 4, 5, 7, 9]), "num(x) % 11 == 0")},
                    model=["odd places sum 21 & even 10 ({1,2,7},{1,4,5},{2,3,5}) or odd 10 ({1,2,3,4})"])},
    "1l5c20i6d": {
        "formal": F({"N": Q("C(5, 3)*C(2, 2)*2**2", PROD(["u", "c", "w1", "w2"], 5),
                            "3*count(x, 'c') - 2*(count(x, 'w1') + count(x, 'w2')) == 5")},
                    model=["per question: unattempted, the correct choice, or one of 2 wrong choices"])},
    "1l5w0pg9y": {
        "formal": F({"N": Q("3*fact(5)", ARR([1, 2, 3, 4, 5, 6, 7], 6), "num(x) % 15 == 0")},
                    model=["last digit 5; omitted digit d with 28 - d divisible by 3: d in {1, 4, 7}"])},
    # ================================================================== chunk 5
    "1l6dx41xx": {
        "formal": F({"N": Q("lexrank('MANKIND') - 1", ARR(list("MANKIND")), "x < tuple('MANKIND')")}, target="N + 1",
                    model=["dictionary rank among distinct arrangements"])},
    "1l6gjaknm": {
        "formal": F({"N": Q("mperm(1, 1, 3) + mperm(1, 2, 2) + mperm(2, 3) + mperm(1, 1, 1, 2) + mperm(1, 2, 2) "
                            "+ mperm(2, 2, 1)", PROD(list(range(1, 10)), 5), "x[0]*x[1]*x[2]*x[3]*x[4] == 36")},
                    model=["non-1 digit multisets: {9,4}, {9,2,2}, {6,6}, {6,3,2}, {4,3,3}, {3,3,2,2}, padded with 1s"])},
    "1l6hzoa3g": {
        "formal": F({"N": Q("6*3 + 4*3", ARR([1, 2, 3, 4, 5, 6], 4), "1000 < num(x) < 3000 and num(x) % 4 == 0")},
                    model=["lead 1: endings 24,32,36,52,56,64; lead 2: 16,36,56,64; 3 choices for the middle"])},
    "1l6m6g453": {
        "formal": F({"N6": Q("(a + d)**6 - a**6", PROD("list(range(a + d))", 6), "max(x) >= a"),
                     "N7": Q("(a + d)**7 - a**7", PROD("list(range(a + d))", 7), "max(x) >= a"),
                     "N8": Q("(a + d)**8 - a**8", PROD("list(range(a + d))", 8), "max(x) >= a")},
                    target="(N6 + N7 + N8)/5**6", let={"a": "5", "d": "5"},
                    scaled=[{"a": "1", "d": "1"}, {"a": "2", "d": "1"}, {"a": "1", "d": "2"}],
                    model=["characters 0..a-1 are letters, a..a+d-1 are digits; lengths 6, 7, 8; complement count"]),
        "note": "10^8 passwords too many to enumerate: closed form checked on scaled alphabets"},
    "1l6nox8pu": {
        "formal": F({"N": Q("C(b, 3)*C(g, 2)", SEL("[('b', i) for i in range(b)] + [('g', i) for i in range(g)]", 5),
                            "sum(1 for t in x if t[0] == 'b') == 3")},
                    target="b + 3*g", params={"b": {"domain": "natural", "box": [1, 60]},
                                              "g": {"domain": "natural", "box": [1, 60]}},
                    equations=["N == 168"],
                    complete_box="N = 168 needs C(b,3) >= 1 and C(g,2) >= 1; C(b,3) > 168 for b >= 13 and "
                                 "C(g,2) > 168 for g >= 20, so all solutions lie in the box",
                    model=["distinct boys and girls"])},
    "1l6p3l4h6": {
        "formal": F({"N": Q("C(9, 2) + C(9, 3) + C(9, 5) + C(9, 7)", PROD([0, 1], 9), "isprime(sum(x))")})},
    "1l6rflsnq": {
        "formal": F({"N4": Q("2*3", ARR([2, 3, 4, 5, 6], 4), "1012 < num(x) < 23421 and num(x) % 55 == 0"),
                     "N5": Q("0", ARR([2, 3, 4, 5, 6], 5), "1012 < num(x) < 23421 and num(x) % 55 == 0")},
                    target="N4 + N5",
                    model=["last digit 5; 4-digit abc5 needs a + c = b + 5 (b = 2, 3, 4: 2 orders each); 5-digit "
                           "candidates <= 23421 fail"])},
    "1ldo7e9ya": {
        "formal": F({"N": Q("C(13 + 2, 2)", COMP(21, 3, lo=[1, 3, 4]))}, model=["integer solutions with lower bounds"])},
    "1ldo7hjc5": {
        "formal": F({"N": Q("3**5/3", PROD([4, 5, 9], 6), "num(x) % 6 == 0")},
                    model=["last digit 4; residues 4,5,9 = 1,2,0 mod 3 are uniform, so 1/3 of the 3^5 prefixes work"])},
    "ldoaldz7": {
        "formal": F({"N": Q("C(6, 3) + (C(8, 3) - 4*C(3, 3)) + (C(10, 3) - 4*C(5, 3)) + (C(8, 3) - 4*C(3, 3))",
                            PROD([0, 1, 2, 3, 4], 4), "sum(x) in (3, 5, 7, 11)")},
                    model=["p in {3,5,7,11}; sum 11 count = sum 5 count by x -> 4 - x"])},
    "ldoan5f0": {
        "formal": F({"A": Q("P(2*n + 1, n - 1)", ARR("list(range(2*n + 1))", "n - 1")),
                     "B": Q("P(2*n - 1, n)", ARR("list(range(2*n - 1))", "n"))},
                    target="n*n + n + 15", params={"n": {"domain": "natural", "box": [1, 40]}},
                    equations=["21*A == 11*B"], constraints=["n >= 1"], model=["ratio of permutations"])},
    "1ldom13ou": {
        "formal": F({"S": Q("2**50/fact(51)", DIRECT("sum(1/(fact(k)*fact(51 - k)) for k in range(1, 52, 2))"))},
                    target="S", model=["sum over odd k of 51Ck = 2^50"]),
        "option_values": ov(A=Fr(2 ** 51, fa(50)), B=Fr(2 ** 51, fa(51)), C=Fr(2 ** 50, fa(50)), D=Fr(2 ** 50, fa(51)))},
    "1ldoo8du5": {
        "formal": F({"N": Q("(450 + 300 - 150) - ((999//14 - 99//14) + (999//21 - 99//21) - (999//42 - 99//42))",
                            RNG(100, 999), "(x % 2 == 0 or x % 3 == 0) and x % 7 != 0")})},
    "1ldoo9cl4": {
        "formal": F({"N": Q("mperm([c for c in W if c not in 'AEIOU'] + ['#'])*mperm([c for c in W if c in 'AEIOU'])",
                            ARR("list(W)"), "together(x, 'AEIOU')")},
                    let={"W": "'ASSASSINATION'"},
                    scaled=[{"W": "'SASINATO'"}, {"W": "'ASSASSINA'"}, {"W": "'ASSANATION'"}],
                    model=["vowels A,A,A,I,I,O as one block among the consonants S x4, N x2, T"]),
        "note": "13!/(3!4!2!2!) arrangements too many: closed form checked on scaled words"},
    "1ldpthzaf": {
        "formal": F({"N": Q("2*6**4 + 6**3 + 5*6**2 + 6 + 2", PRODS([2, 3, 4, 7, 9], *[[0, 2, 3, 4, 7, 9]] * 4),
                            "num(x) < 42923")}, target="N + 1",
                    model=["5-digit numbers (no leading 0) over the six digits, ascending"])},
    "1ldptkt5n": {
        "formal": F({"N": Q("(2800//3 - 999//3) + (2800//11 - 999//11) - (2800//33 - 999//33)", RNG(1000, 2800),
                            "x % 3 == 0 or x % 11 == 0")})},
    "ldqvb3cg": {
        "formal": F({"N": Q("12 + 35 + 42 + 19", PRODS("list(range(2, 101, 2))", "list(range(1, 100, 2))"),
                            "(x[0] + x[1]) % 23 == 2")},
                    model=["a + b odd, = 2 mod 23: 25, 71, 117, 163; count even a with b = s - a in 1..99"]),
        "option_values": ov(A=186, B=54, C=108, D=268)},
    "ldqzur7j": {
        "formal": F({"N": Q("mperm(3, 2, 1) + mperm(3, 1, 1, 1) + mperm(1, 3, 2)", ARR([1, 2, 2, 2, 3, 3, 5]),
                            "x[6] % 2 == 1")}, model=["last digit 1, 3 or 5"])},
    "1ldr7rs32": {
        "formal": F({"N": Q("5*1 + 6*1 + 5*2", PROD([1, 2, 3, 5], 4), "num(x) % 15 == 0")},
                    model=["last digit 5; first three digit residues (1+x+2x^2)^3: coefficient of x^1 mod x^3-1 = 21"])},
    "1ldseml3w": {
        "formal": F({"N": Q("lexrank('TOUGH') - 1", ARR(list("OUGHT")), "x < tuple('TOUGH')")}, target="N + 1"),
        "option_values": ov(A=79, B=84, C=89, D=86)},
    "1ldsetdwf": {
        "formal": F({"N": Q("300 + 225 - 75 - (999//48 - 99//48)", RNG(100, 999),
                            "(x % 3 == 0 or x % 4 == 0) and x % 48 != 0")}),
        "option_values": ov(A=400, B=472, C=507, D=432)},
    "1ldsg0itd": {
        "formal": F({"N": Q("4500 - 1500", RNG(1000, 9999), "gcd(x, 54) == 2")},
                    model=["gcd = 2 iff x even and 3 does not divide x"])},
    "1ldswvvgd": {
        "formal": F({"R": Q("C(8, 5) + C(6, 4) + 1", SEL([1, 2, 3, 4, 5, 6, 7, 8, 9], 6),
                            "x <= (2, 4, 5, 6, 7, 8)")},
                    target="2 + 4 + 5 + 6 + 7 + 8", require=["R == 72"],
                    model=["increasing-digit numbers <-> 6-subsets of 1..9 in lexicographic order; the 72nd is "
                           "245678 (56 start with 1, 15 start with 23)"])},
    "1ldswzrar": {
        "formal": F({"N": Q("2*5**4 + 5**3 + 2*5**2 + 2*5", PROD([1, 2, 3, 5, 7], 5), "num(x) > 35337")},
                    target="N + 1", model=["descending order: serial = 1 + count of larger numbers"])},
    "1ldu5hsr5": {
        "formal": F({"N": Q("3*P(4, 3)", ARR([1, 3, 5, 7, 9], 4), "5000 < num(x) < 10000")},
                    model=["only 4-digit numbers lie strictly between 5000 and 10000"]),
        "option_values": ov(A=120, B=6, C=72, D=12)},
    # ================================================================== chunk 6
    "1ldu5w6ww": {
        "formal": F({"S": Q("C(52, 4) - C(45, 4)", DIRECT("sum(C(51 - k, 3) for k in range(7))"))}, target="S",
                    model=["hockey stick: sum_{m=45}^{51} mC3 = 52C4 - 45C4"]),
        "option_values": ov(A=comb(51, 4) - comb(45, 4), B=comb(51, 3) - comb(45, 3), C=comb(52, 3) - comb(45, 3),
                            D=comb(52, 4) - comb(45, 4))},
    "1ldu601xz": {
        "formal": F({"N": Q("sum((59 - 3*a)//(4*a) for a in range(1, 20))",
                            PRODS("list(range(1, 20))", "list(range(1, 15))"),
                            "x[1] % x[0] == 0 and 3*x[0] + 4*x[1] < 60")},
                    model=["strictly inside: a > 0, b > 0, 3a + 4b < 60; 'b a multiple of a' = b = k a, k a "
                           "(positive) integer"])},
    "1ldu63yht": {
        "formal": F({"N": Q("C(8,2)*C(7,2)*C(5,1) + C(8,2)*C(7,1)*C(5,2) + C(8,3)*C(7,1)*C(5,1)",
                            SEL("[('r', i) for i in range(7)] + [('w', i) for i in range(5)] + "
                                "[('o', i) for i in range(8)]", 5),
                            ["sum(1 for t in x if t[0] == 'o') >= 2", "sum(1 for t in x if t[0] == 'r') >= 1",
                             "sum(1 for t in x if t[0] == 'w') >= 1"])},
                    model=["fruits treated as distinct (standard)"])},
    "1ldv2uyem": {
        "formal": F({"N": Q("2*(C(5, 2) + 5*5 + 5*5)", PROD("list(range(1, 26))", 2),
                            "x[0] != x[1] and (x[0] + x[1]) % 5 == 0")},
                    model=["(x, y) ordered (named variables); residue classes of size 5: (0,0), (1,4), (2,3)"]),
        "note": "ordered-pair reading of the named x, y; unordered would be 60"},
    "1ldww37nt": {
        "formal": F({"N4": Q("2*P(4, 3)", ARR([3, 5, 6, 7, 8], 4), "num(x) > 7000"),
                     "N5": Q("fact(5)", ARR([3, 5, 6, 7, 8], 5), "num(x) > 7000")}, target="N4 + N5"),
        "option_values": ov(A=48, B=120, C=168, D=220)},
    "1ldwwxq9r": {
        "formal": F({"N": Q("fact(5)", PROD([0, 1, 2, 3, 4], 5), "len(set(x)) == 5")},
                    model=["row sums 1: each row is a column index x[i]; column sums 1: indices distinct"]),
        "option_values": ov(A=125, B=150, C=225, D=120)},
    "1ldyc2w6e": {
        "formal": F({"N": Q("C(7, 5) + C(5, 1)*C(7, 4) + C(5, 2)*C(7, 3)",
                            SEL("[('L', i) for i in range(5)] + [('O', i) for i in range(7)]", 5),
                            "sum(1 for t in x if t[0] == 'L') <= 2")})},
    "1ldyc8xzj": {
        "formal": F({"N": Q("mperm(2, 2)*mperm(3, 2)", ARR([1, 2, 3, 4, 1, 2, 3, 4, 1]),
                            "all(x[i] % 2 == 0 for i in (1, 3, 5, 7))")},
                    model=["4 even digits fill the 4 even places exactly"])},
    "lgnwkhha": {
        "formal": F({"N": Q("5*1 + 6*2 + 5*1", PROD([1, 3, 5, 8], 3), "num(x) % 3 == 0")},
                    model=["residues 1,3,5,8 -> 1,0,2,2: constant term of (1 + x + 2x^2)^3 mod x^3 - 1"]),
        "option_values": ov(A=21, B=22, C=18, D=20)},
    "lgnys0w5": {
        "formal": F({"N": Q("8*(3 + 2 + 2 + 1 + 1)", ARR([0, 1, 2, 3, 4, 5, 6, 7], 4),
                            "max(x) == 7 and x[0] + x[1] == x[2] + x[3]")},
                    model=["digits 0-7 with 7 present, all different; 4-digit code may start with 0"])},
    "1lgow5dwx": {
        "formal": F({"N": Q("lexrank('MONDAY') - 1", ARR(list("MONDAY")), "x < tuple('MONDAY')")}, target="N + 1"),
        "option_values": ov(A=324, B=328, C=326, D=327)},
    "1lgoy7m2y": {
        "formal": F({"N": Q("8 + 8", PROD([1, 2, 3, 4, 5], 3), "num(x) % 6 == 0")},
                    model=["last digit 2 or 4; pair residues of the first two digits from (1 + 2x + 2x^2)^2"])},
    "1lgq0urew": {
        "formal": F({"N": Q("C(11, 6) - 7*C(7, 6)", PROD([1, 2, 3, 4], 7), "sum(x) == 12")},
                    model=["y = x - 1 in 0..3 summing to 5; remove a part >= 4"])},
    "1lgrefqkf": {
        "formal": F({"N": Q("3*P(4, 3) + 2*P(4, 3)", ARR([0, 1, 3, 5, 7, 9], 5),
                            "num(x) > 40000 and num(x) % 5 == 0")}),
        "option_values": ov(A=132, B=72, C=120, D=96)},
    "1lgrgicm5": {
        "formal": F({"N": Q("2*mperm(1, 2, 2, 2) - (2*mperm(1, 1, 1, 2) + fact(5) + 2*mperm(1, 1, 1, 2)) + "
                            "(8 + 2*2*fact(3) + 2*fact(3))",
                            ARR(list("aaabbbccc")),
                            "any(word(x[i:i+3]) in ('abc', 'cba') for i in range(7))")},
                    model=["a, b, c distinct digits with b the middle term: an A.P. triple is abc or cba",
                           "inclusion-exclusion over windows (clusters abc, abcba, abcbabc): 1260 - 360 + 44"]),
        "note": "reading: three consecutive digits 'in A.P.' = a b c or c b a in order (a, b, c distinct)"},
    "1lgsugvol": {
        "formal": F({"N": Q("lexrank('THAMS') - 1", ARR(list("MATHS")), "x < tuple('THAMS')")}, target="N + 1"),
        "option_values": ov(A=103, B=104, C=102, D=101)},
    "1lguw0e0f": {
        "formal": F({"N": Q("C(17, 2) - (3*8 - 3*1 + 1)", COMP(15, 3), "len(set(x)) == 3")},
                    model=["ordered triplets of distinct non-negative integers"]),
        "option_values": ov(A=136, B=80, C=92, D=114)},
    "1lguwuo8m": {
        "formal": F({"N": Q("derange(5)", ARR([0, 1, 2, 3, 4]), "all(x[i] != i for i in range(5))")})},
    "1lgvpequ0": {
        "formal": F({"N": Q("3*multinomial(8, 3, 3, 2)", PROD([0, 1, 2], 8), "max(count(x, c) for c in (0, 1, 2)) <= 3")},
                    model=["distinct persons, distinct cars; loads must be (3, 3, 2) in some order"]),
        "option_values": ov(A=560, B=1680, C=3360, D=1120)},
    "1lgvqlzes": {
        "formal": F({"S": Q("(6*2 + 3*1 + 3*3)*1111", ARR([2, 1, 2, 3]), agg={"sum": "num(x)"})}, target="S")},
    "1lgxwdlm3": {
        "formal": F({"N": Q("fact(7) - fact(5) - fact(4) + fact(2)", ARR([1, 2, 3, 4, 5, 6, 7]),
                            "'153' not in word(x) and '2467' not in word(x)")})},
    "1lgxwhg04": {
        "formal": F({"M": Q("2*C(n, 2)*C(n - 2, 2)", PRODS("list(range(n))", "list(range(n))", "list(range(n))",
                                                           "list(range(n))"),
                            "x[0] < x[1] and x[2] != x[3] and x[2] not in (x[0], x[1]) and x[3] not in (x[0], x[1])")},
                    target="2*n", params={"n": {"domain": "natural", "box": [2, 40]}}, equations=["M == 840"],
                    model=["couple i = man i + woman i; match = {man x0 + woman x2} vs {man x1 + woman x3}; no "
                           "husband and wife in the same match (partners or opponents)"])},
    "1lgylnv0d": {
        "formal": F({"N": Q("mperm(W) - 2*mperm([c for c in W if c not in 'CS'] + ['#'])", ARR("list(W)"),
                            "not adj(x, 'C', 'S')")},
                    target="N/fact(6)", let={"W": "'MATHEMATICS'"},
                    scaled=[{"W": "'MATHCS'"}, {"W": "'MATHEMCS'"}, {"W": "'MATHEMATCS'"}],
                    model=["complement: C and S adjacent (CS block in either order)"]),
        "option_values": ov(A=5670, B=1890, C=2835, D=945),
        "note": "11!/8 arrangements too many: closed form checked on scaled words"},
    "1lgzxfup5": {
        "formal": F({"N": Q("mperm([c for c in W if c not in 'AEIOU'] + ['#'])*mperm([c for c in W if c in 'AEIOU'])",
                            ARR("list(W)"), "together(x, 'AEIOU')")},
                    let={"W": "'INDEPENDENCE'"},
                    scaled=[{"W": "'INDEPEND'"}, {"W": "'INDEPENDEN'"}, {"W": "'NDEPENDENCE'"}],
                    model=["vowels I, E, E, E, E as one block"]),
        "option_values": ov(A=16800, B=14800, C=18000, D=33600)},
    "1lgzycfb1": {
        "formal": F({"N": Q("fact(m - 1)*P(m, w)",
                            CIRC("[('m', i) for i in range(m)] + [('w', i) for i in range(w)]"),
                            "all(not (x[i][0] == 'w' and x[(i+1) % len(x)][0] == 'w') for i in range(len(x)))")},
                    let={"m": "7", "w": "5"}, scaled=[{"m": "4", "w": "3"}, {"m": "5", "w": "4"}, {"m": "6", "w": "4"}],
                    model=["boys first round the table, girls in distinct gaps"]),
        "option_values": ov(A=720, B=7 * 360 ** 2, C=7 * 720 ** 2, D=126 * fa(5) ** 2)},
    # ================================================================== chunk 7
    "1lh245n1s": {
        "formal": F({"N": Q("3**n - 3*2**n + 3", PROD([0, 1, 2], "n"), "set(x) == {0, 1, 2}")},
                    let={"n": "20"}, scaled=[{"n": "3"}, {"n": "5"}, {"n": "7"}, {"n": "9"}],
                    model=["distinct oranges -> onto maps to 3 children; inclusion-exclusion"]),
        "note": "3^20 maps too many: closed form checked on n = 3, 5, 7, 9"},
    "1lh2xtxhh": {
        "formal": F({"N": Q("lexrank('PUBLIC') - 1", ARR(list("PUBLIC")), "x < tuple('PUBLIC')")}, target="N + 1"),
        "option_values": ov(A=578, B=576, C=580, D=582)},
    "1lh2yrfzn": {
        "formal": F({"N": Q("C(3, 2)*C(4, 2)*fact(4)", ARR(list("UNIVERSE"), 4),
                            ["len(set(x)) == 4", "sum(1 for t in x if t in 'AEIOU') == 2"])},
                    model=["'without repetition': the 4 letters are distinct (E not used twice); vowels U, I, E; "
                           "consonants N, V, R, S"]),
        "note": "reading: no letter repeated in a word (EE excluded)"},
    "lsaoelst": {
        "formal": F({"N": Q("stirling2(5, 1) + stirling2(5, 2) + stirling2(5, 3) + stirling2(5, 4)",
                            SETP([1, 2, 3, 4, 5], max_blocks=4))},
                    model=["indistinguishable offices: set partitions of the 5 employees into at most 4 blocks"]),
        "option_values": ov(A=47, B=53, C=51, D=43)},
    "lsapvsz6": {
        "formal": F({"N": Q("sum((42 - 3*z)//2 + 1 for z in range(15))", PRODS("list(range(15))", "list(range(22))"),
                            "42 - 3*x[0] - 2*x[1] >= 0")},
                    model=["for each (z, y) with 3z + 2y <= 42, x is determined"])},
    "jaoe38c1lscnqca5": {
        "formal": F({"a": Q("all(legendre(24, p) >= 6*vp(24, p) for p in (2, 3))", DIRECT("fact(24) % 24**6 == 0")),
                     "b": Q("all(legendre(120, p) >= 24*vp(120, p) for p in (2, 3, 5))",
                            DIRECT("fact(120) % 120**24 == 0"))},
                    target=None,
                    claims={"A": "a and b", "B": "a and not b", "C": "(not a) and b", "D": "(not a) and (not b)"},
                    model=["alpha = 24!/24^6, beta = 120!/120^24; integrality by Legendre valuations vs exact division"]),
        "option_values": BITS},
    "jaoe38c1lsd39r8j": {
        "formal": F({"N": Q("C(21 - 6 + 2, 2)", COMP(21, 3, lo=2))}),
        "option_values": ov(A=130, B=136, C=142, D=406)},
    "jaoe38c1lsd4qjvk": {
        "formal": F({"X": Q("C(8, m + 2)", DIRECT("C(6, m) + 2*C(6, m + 1) + C(6, m + 2)")),
                     "A": Q("P(n - 1, 3)", ARR("list(range(n - 1))", 3)),
                     "B": Q("P(n, 4)", ARR("list(range(n))", 4))},
                    target="P(n, m + 1) + C(n + 1, m)",
                    params={"m": {"domain": "nonnegative", "box": [0, 10]}, "n": {"domain": "natural", "box": [1, 40]}},
                    equations=["8*A == B"], constraints=["X > C(8, 3)", "n >= 4"],
                    complete_box="X = 8C(m+2) > 56 only for m = 2 (6Cm terms vanish beyond m = 6); 8(n-1)P3 = nP4 "
                                 "forces n = 8 for n >= 4",
                    model=["6Cm + 2.6C(m+1) + 6C(m+2) = 8C(m+2) (Pascal twice)"]),
        "option_values": ov(A=380, B=376, C=372, D=384)},
    "jaoe38c1lse5y7d4": {
        "formal": F({"N": Q("P(9, 4) + 2*C(8, 2)*mperm(2, 1, 1) + mperm(2, 2) + 8*mperm(3, 1)",
                            ARR(list("DISTRIBUTION"), 4))},
                    model=["9 distinct letters, I x3, T x2: all distinct / one pair / two pairs / III + one"])},
    "jaoe38c1lsf0oh50": {
        "formal": F({"N": Q("lexrank('GTWENTY') - 1", ARR(list("GTWENTY")), "x < tuple('GTWENTY')")},
                    target="N + 1")},
    "jaoe38c1lsfk9w8g": {
        "formal": F({"N": Q("npart(8, 4)", IPART(8, 4))},
                    model=["identical books, identical shelves: partitions of 8 into at most 4 parts"]),
        "option_values": ov(A=18, B=16, C=12, D=15)},
    "1lsg4z01p": {
        "formal": F({"N": Q("sum(C(8, 15 - b - c)*C(6, b)*C(6, c) for b in range(4, 7) for c in range(4, 7) "
                            "if 15 - b - c >= 4)",
                            SEL("[('A', i) for i in range(8)] + [('B', i) for i in range(6)] + "
                                "[('C', i) for i in range(6)]", 15),
                            "all(sum(1 for t in x if t[0] == s) >= 4 for s in 'ABC')")})},
    "luxweoza": {
        "formal": F({"N": Q("C(15, 2) - C(6, 2) - 2*C(5, 2)", RNG(101, 999), "sum(digits(x)) == 14")},
                    model=["3-digit numbers; a' = a - 1: a' + b + c = 13 with a' <= 8, b, c <= 9"])},
    "lv0vxc34": {
        "formal": F({"N": Q("C(18, 3) - C(5, 3) - C(6, 3) - C(7, 3)",
                            SEL("[(s, i) for s, k in (('AB', 5), ('BC', 6), ('CA', 7)) for i in range(k)]", 3),
                            "len(set(t[0] for t in x)) > 1")}),
        "option_values": ov(A=751, B=776, C=796, D=771)},
    "lv2er3yn": {
        "formal": F({"N": Q("sum((C(4, i)*C(5, 4 - i))**2 for i in range(5))",
                            SEL("[('A', 'm', i) for i in range(4)] + [('A', 'w', i) for i in range(5)] + "
                                "[('B', 'm', i) for i in range(5)] + [('B', 'w', i) for i in range(4)]", 8),
                            ["sum(1 for t in x if t[0] == 'A') == 4", "sum(1 for t in x if t[1] == 'm') == 4"])})},
    "lv3ve4dd": {
        "formal": F({"N": Q("C(8, 5) + 3*C(7, 3) + C(3, 2)*C(6, 1)", SEL(list("MATHEMATICS"), 5))},
                    model=["selections (not arrangements) of 5 letters from the multiset M2 A2 T2 H E I C S"]),
        "option_values": ov(A=179, B=177, C=175, D=181)},
    "lv5gs8ga": {
        "formal": F({"N": Q("P(5, 5)", PROD("R", "len(A)"), "len(set(x)) == len(A)")},
                    let={"A": "[p for p in range(2, 2311) if 2310 % p == 0 and isprime(p)]",
                         "R": "sorted(set(ilog2(p*p + p**3 // 5) for p in A))"},
                    model=["A = {2,3,5,7,11}; f values 2,3,5,6,8 by hand -> range has 5 elements; one-one maps "
                           "A -> range(f)"]),
        "option_values": ov(A=20, B=120, C=25, D=24)},
    "lv5gsk30": {
        "formal": F({"N": Q("P(5, 3) - 4*fact(3)", ARR([2, 3, 4, 5, 7], 3), "num(x) % 3 != 0")},
                    model=["digit sets with sum divisible by 3: {2,3,4}, {2,3,7}, {3,4,5}, {3,5,7}"])},
    "lv7v47sx": {
        "formal": F({"N": Q("C(15, 3) - 4*C(9, 3) + 6*C(3, 3)", PROD([1, 2, 3, 4, 5, 6], 4), "sum(x) == 16")},
                    model=["ordered outcomes of four throws"])},
    "lv9s208h": {
        "formal": F({"N": Q("fact(9)/fact(3)**3", PROD(["A", "B", "C"], 9),
                            "count(x, 'A') == 3 and count(x, 'B') == 3")},
                    model=["|S| = 9 (2^1..2^9); named sets A, B, C of 3 each (ordered partition)"]),
        "option_values": ov(A=1640, B=1520, C=1710, D=1680),
        "note": "labelled reading (A, B, C named); unordered would be 280 (not an option)"},
    "lv9s20f0": {
        "formal": F({"RA": Q("lexrank('OBBJH') - 1", ARR(list("BHBJO")), "x < tuple('OBBJH')"),
                     "RB": Q("lexrank('HBBJO') - 1", ARR(list("BHBJO")), "x < tuple('HBBJO')"),
                     "RC": Q("lexrank('OBBHJ') - 1", ARR(list("BHBJO")), "x < tuple('OBBHJ')"),
                     "RD": Q("lexrank('JBBOH') - 1", ARR(list("BHBJO")), "x < tuple('JBBOH')")},
                    target=None, claims={"A": "RA + 1 == 50", "B": "RB + 1 == 50", "C": "RC + 1 == 50",
                                         "D": "RD + 1 == 50"},
                    model=["option word is the 50th iff its dictionary rank is 50"]),
        "option_values": BITS},
    "lvb294sf": {
        "formal": F({"RA": Q("lexrank('NRAPUG') - 1", ARR(list("NAGPUR")), "x < tuple('NRAPUG')"),
                     "RB": Q("lexrank('NRAGUP') - 1", ARR(list("NAGPUR")), "x < tuple('NRAGUP')"),
                     "RC": Q("lexrank('NRAPGU') - 1", ARR(list("NAGPUR")), "x < tuple('NRAPGU')"),
                     "RD": Q("lexrank('NRAGPU') - 1", ARR(list("NAGPUR")), "x < tuple('NRAGPU')")},
                    target=None, claims={"A": "RA + 1 == 315", "B": "RB + 1 == 315", "C": "RC + 1 == 315",
                                         "D": "RD + 1 == 315"},
                    model=["option word is the 315th iff its dictionary rank is 315"]),
        "option_values": BITS},
    "lvb294ut": {
        "formal": F({"A": Q("C(n + 1, r + 1)", SEL("list(range(n + 1))", "r + 1")),
                     "B": Q("C(n, r)", SEL("list(range(n))", "r")),
                     "D": Q("C(n - 1, r - 1)", SEL("list(range(n - 1))", "r - 1"))},
                    target="2*n + 5*r", params={"n": {"domain": "natural", "box": [1, 40]},
                                                "r": {"domain": "nonnegative", "box": [0, 40]}},
                    equations=["35*A == 55*B", "21*B == 35*D"], constraints=["1 <= r <= n"],
                    model=["(n-1)C(r-1) defined needs r >= 1"]),
        "option_values": ov(A=62, B=60, C=55, D=50)},
    "lvc57pix": {
        "formal": F({"N": Q("8*(8 - 4)*(8 - 5)/6", SEL(list(range(8)), 3),
                            "all((b - a) % 8 not in (1, 7) for a in x for b in x if a != b)")},
                    model=["n(n-4)(n-5)/6 triangles with no side of the n-gon"]),
        "option_values": ov(A=56, B=16, C=24, D=48)},
    "m6qgods0": {
        "formal": F({"N": Q("C(10, 6) - 7*C(7, 6)", PROD([1, 2, 3], 7), "sum(x) == 11")},
                    model=["y = x - 1 in {0,1,2} summing to 4; remove a part >= 3"]),
        "option_values": ov(A=164, B=158, C=161, D=173)},
    # ================================================================== chunk 8
    "m6qhxk3l": {
        "formal": F({"RA": Q("lexrank('PRNAKU') - 1", ARR(list("KANPUR")), "x < tuple('PRNAKU')"),
                     "RB": Q("lexrank('PRKAUN') - 1", ARR(list("KANPUR")), "x < tuple('PRKAUN')"),
                     "RC": Q("lexrank('PRKANU') - 1", ARR(list("KANPUR")), "x < tuple('PRKANU')"),
                     "RD": Q("lexrank('PRNAUK') - 1", ARR(list("KANPUR")), "x < tuple('PRNAUK')")},
                    target=None, claims={"A": "RA + 1 == 440", "B": "RB + 1 == 440", "C": "RC + 1 == 440",
                                         "D": "RD + 1 == 440"},
                    model=["option word is the 440th iff its dictionary rank is 440"]),
        "option_values": BITS},
    "m6qiiiec": {
        "formal": F({"N": Q("C(5, 3)*mperm(2, 2, 2) + 5*4*mperm(2, 4) + C(5, 2)*mperm(3, 3) + 5",
                            PROD(list("MATHS"), 6), "all(count(x, c) >= 2 for c in set(x))")},
                    model=["letter-multiplicity patterns 2+2+2, 2+4, 3+3, 6 (letters may repeat)"])},
    "m6qvb110": {
        "formal": F({"N": Q("C(12, 2)*C(13, 2)", SEL(list(range(26)), 5), "x[2] == 12")},
                    model=["5 distinct letters in alphabetical order; M is the 13th letter (index 12)"]),
        "option_values": ov(A=6084, B=5148, C=14950, D=4356)},
    "m6rp5wrs": {
        "formal": F({"N": Q("2*fact(3)*(fact(4) - 2*fact(3))", ARR(["G1", "G2", "G3", "B1", "B2", "B3", "B4"]),
                            ["together(x, ['G1', 'G2', 'G3'])", "together(x, ['B1', 'B2', 'B3', 'B4'])",
                             "not adj(x, 'B1', 'B2')"])}),
        "option_values": ov(A=120, B=96, C=72, D=144)},
    "m6rj2yzu": {
        "formal": F({"N": Q("C(16, 2) - C(7, 2) - 2*C(6, 2) - 5", RNG(213, 998), "sum(digits(x)) == 15")},
                    model=["3-digit numbers with digit sum 15 (69) minus 159, 168, 177, 186, 195 (< 212)"])},
    "m6srmykg": {
        "formal": F({"N": Q("fact(8) - fact(6)*fact(3)", ARR(list("DAUGHTER")), "not together(x, 'AUE')")},
                    model=["'never come together' = the three vowels not all in one block"]),
        "option_values": ov(A=34000, B=37000, C=35000, D=36000)},
    "m6t9xszj": {
        "formal": F({"N": Q("fact(5)*fact(5) + fact(4)*P(5, 5)",
                            ARR("[('b', i) for i in range(5)] + [('g', i) for i in range(4)]"),
                            "together(x, [('b', i) for i in range(5)]) or "
                            "all(not (x[i][0] == 'b' and x[i+1][0] == 'b') for i in range(8))")},
                    model=["the two cases are disjoint"])},
    "m6ulvpt8": {
        "formal": F({"N": Q("(999//6 - 99//6) - (999//36 - 99//36)", RNG(100, 999),
                            "x % 6 == 0 and not (x % 4 == 0 and x % 9 == 0)")},
                    model=["parallel reading: 'divisible by 2 and 3' = by both; 'not divisible by 4 and 9' = not "
                           "divisible by both 4 and 9 (i.e. not by 36)"]),
        "note": "ambiguous: 'neither 4 nor 9' reading would give 50; parallel reading gives 125"},
    "m6v42xah": {
        "formal": F({"N": Q("sum(C(7, i)*C(3, 5 - i)*C(6, 4 - i)*C(5, i - 1) for i in range(2, 5))",
                            SEL("[('A', 'b', i) for i in range(7)] + [('A', 'g', i) for i in range(3)] + "
                                "[('B', 'b', i) for i in range(6)] + [('B', 'g', i) for i in range(5)]", 8),
                            ["sum(1 for t in x if t[0] == 'A') == 5", "sum(1 for t in x if t[1] == 'b') == 4"])}),
        "option_values": ov(A=8925, B=9100, C=8575, D=8750)},
    "m6v42h7g": {
        "formal": F({"N": Q("k*2**(n - k)", PROD([0, 1], "n"), "sum(x[:k]) == 1")},
                    let={"n": "100", "k": "98"}, scaled=[{"n": "5", "k": "3"}, {"n": "8", "k": "6"}, {"n": "12", "k": "10"}],
                    model=["exactly one of f(1..98) is 1; f(99), f(100) free"]),
        "note": "2^100 functions: closed form checked on scaled domains"},
    "m6w9o8r5": {
        "formal": F({"A": Q("C(n, r - 1)", SEL("list(range(n))", "r - 1")),
                     "B": Q("C(n, r)", SEL("list(range(n))", "r")),
                     "Cq": Q("C(n, r + 1)", SEL("list(range(n))", "r + 1")),
                     "al": Q("4**2 + 2**2", DIRECT("max(V) if len(V) == 1 else -1"))},
                    target="al", let={"V": "set((4*c + 2*s + 3*r - n - 1)**2 + (4*s - 2*c + r*r - n - 1)**2 "
                                           "for (c, s) in ((1, 0), (0, 1), (3/5, 4/5), (-4/5, 3/5), (-1, 0), (5/13, 12/13)))"},
                    params={"n": {"domain": "natural", "box": [1, 40]}, "r": {"domain": "natural", "box": [1, 40]}},
                    equations=["A == 28", "B == 56", "Cq == 70"], constraints=["2 <= r <= n - 1"],
                    require=["3*r - n - 1 == 0", "r*r - n - 1 == 0"],
                    complete_box="nC(r-1) = 28 with 1 <= r-1 <= n-1 forces n <= 28",
                    model=["centroid: 3x - 1 = 4cos t + 2 sin t + (3r - n - 1), 3y = 4 sin t - 2 cos t + (r^2 - n - 1)",
                           "with n = 8, r = 3 both offsets vanish: alpha = 4^2 + 2^2; enumeration evaluates the locus "
                           "at rational points (cos t, sin t) of the unit circle and requires a constant value"]),
        "option_values": ov(A=18, B=8, C=20, D=6)},
    "m6w9o90s": {
        "formal": F({"N": Q("(4 + 3 + 2)*8**3 - 1", RNG(50001, 99999), "set(digits(x)) <= {0, 1, 2, 3, 4, 5, 6, 7} "
                            "and digits(x)[0] + digits(x)[4] <= 8")},
                    model=["digits may repeat (no 'without repetition' in the stem); 50000 itself excluded"]),
        "option_values": ov(A=5720, B=5719, C=4608, D=4607)},
    "m9dmmc5r": {
        "formal": F({"N": Q("C(12, 3) - C(5, 3)", SEL(list(range(12)), 3), "not all(p < 5 for p in x)")}),
        "option_values": ov(A=230, B=210, C=200, D=220)},
    "m9dunp6b": {
        "formal": F({"N": Q("multinomial(10, 5, 3, 2)", PROD([0, 1, 2], 10), "count(x, 1) == 5 and count(x, 2) == 3")}),
        "option_values": ov(A=360, B=2520, C=1820, D=45)},
    "m9e5j5wn": {
        "formal": F({"N": Q("C(6, 3)*C(5, 5) + C(6, 4)*C(5, 4) + C(6, 5)*C(5, 3)",
                            SEL("[('bat', i) for i in range(7)] + [('bowl', i) for i in range(6)]", 10),
                            ["('bat', 0) in x and ('bowl', 0) in x", "sum(1 for t in x if t[0] == 'bat') >= 4",
                             "sum(1 for t in x if t[0] == 'bowl') >= 4"])},
                    model=["captain = batsman 0, vice-captain = bowler 0, both included"]),
        "option_values": ov(A=145, B=165, C=155, D=135)},
    "m9fnur1d": {
        "formal": F({"R": Q("lexrank('CDBEA') - 1", ARR(list("ABCDE")), "x < tuple('CDBEA')"),
                     "W": Q("fact(5)", ARR(list("ABCDE")))},
                    target="R + W",
                    model=["P(W_n) = 2^(n-1)/(2^120 - 1) (probabilities sum to 1); rank(CDBEA) = R + 1 so "
                           "alpha = R, beta = 120 (unique: odd parts force beta = 120)"])},
    "m9fnur3f": {
        "formal": F({"N": Q("9*10**(L - 1)/2", RNG("10**(L - 1)", "10**L - 1"), "sum(digits(x)) % 2 == 0")},
                    target="sum(m + n for m in range(1, 10) for n in range(1, 10) if N == m*n*10**n)",
                    require=["len([1 for m in range(1, 10) for n in range(1, 10) if N == m*n*10**n]) == 1"],
                    let={"L": "7"}, scaled=[{"L": "2"}, {"L": "3"}, {"L": "4"}, {"L": "5"}],
                    model=["exactly half of the L-digit numbers have even digit sum (last digit pairs)",
                           "4.5 x 10^6 = m n 10^n with m, n in 1..9 has the unique solution m = 9, n = 5"])},
    "m9fnut0z": {
        "formal": F({"N": Q("(2+2+4+2+6+4+6+4+10+4+12+6+8+8) - 14", PRODS("list(range(10, 100))",
                                                                         "list(range(10, 100))"),
                            "x[0] < x[1] and gcd(x[0], x[1]) == 6")},
                    model=["m = 6a, n = 6b, 2 <= a < b <= 16 coprime: sum_{b=3}^{16} (phi(b) - 1)"])},
    "m9gxgcsx": {
        "formal": F({"N": Q("C(22, 3) - C(13, 3) - C(10, 3)",
                            SEL("['O'] + [('P', i) for i in range(12)] + [('Q', i) for i in range(9)]", 3),
                            ["not all(t == 'O' or t[0] == 'P' for t in x)", "not all(t == 'O' or t[0] == 'Q' for t in x)"])},
                    model=["O, P_i collinear (13 points on L1); O, Q_j collinear (10 on L2)"]),
        "option_values": ov(A=1026, B=1188, C=1134, D=1080)},
}

SKIPPED: dict[str, str] = {}
