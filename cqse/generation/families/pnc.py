"""Permutations & Combinations families (original questions; patterns modelled on bank questions)."""
from __future__ import annotations

import random
from collections import Counter

from cqse.core.problem import Subject
from cqse.generation.framework import Family, Mistake

CH, SUBJ = "Permutations And Combinations", Subject.MATHEMATICS
VOWELS = set("AEIOU")
# letter pools for made-up "words": 6-8 letters, some repeated, 2-4 vowels (arrangements, meaning not required)
WORDS = ["BANANAS", "PEPPERS", "ARRANGE", "BALLOON", "OCTAGON", "CORRECT", "SUCCESS", "LETTERS", "PALETTE",
         "ACADEMY", "TOMATO", "GARAGE", "AVENUE", "INSIDE", "PARADE", "EQUATION", "MEDIATOR", "VALIDATE"]


def _vowel_pred(k: int) -> str:
    # vowels occupy k consecutive positions
    return (f"max(i for i, c in enumerate(x) if c in 'AEIOU') - "
            f"min(i for i, c in enumerate(x) if c in 'AEIOU') == {k - 1}")


def _arr(word: str, where: str | None, closed: str, distinct: bool = False) -> dict:
    items = f"[(c, i) for i, c in enumerate('{word}')]" if distinct else f"list('{word}')"
    pred = where
    if distinct and where:
        pred = where.replace("c in 'AEIOU'", "c[0] in 'AEIOU'")
    q = {"closed": closed, "enum": {"universe": {"type": "arrangements", "items": items}}}
    if pred:
        q["enum"]["where"] = pred
    return {"kind": "combinatorics", "quantities": {"N": q}, "target": "N",
            "model": ["words = all distinct arrangements of the letters, with or without meaning"]}


def _counts(word):
    return Counter(word)


def _mperm(counts) -> str:
    return "mperm(" + ", ".join(str(v) for v in counts.values()) + ")"


def vowels_together() -> Family:
    def sample(rng: random.Random) -> dict:
        w = rng.choice(WORDS)
        return {"word": w, "mode": rng.choice(["together", "never"])}

    def formal(p):
        w = p["word"]
        c = _counts(w)
        vow = {k: v for k, v in c.items() if k in VOWELS}
        con = {k: v for k, v in c.items() if k not in VOWELS}
        k = sum(vow.values())
        block = f"{_mperm(con + Counter({'#': 1}) if False else {**con, '#': 1})} * {_mperm(vow)}"
        total = _mperm(c)
        closed = block if p["mode"] == "together" else f"{total} - {block}"
        pred = _vowel_pred(k) if p["mode"] == "together" else f"not ({_vowel_pred(k)})"
        return _arr(w, pred, closed)

    def stem(p):
        how = "all the vowels occur together" if p["mode"] == "together" else "no two... " if False else \
            "the vowels do not all occur together"
        return (f"<p>The number of distinct arrangements of all the letters of the word <b>{p['word']}</b> "
                f"in which {how} is:</p>")

    def mistakes(p):
        w = p["word"]
        c = _counts(w)
        vow = {k: v for k, v in c.items() if k in VOWELS}
        con = {k: v for k, v in c.items() if k not in VOWELS}
        k = sum(vow.values())
        n = len(w)
        together_pred = _vowel_pred(k)
        rep = [
            # 1. treat repeated letters as different (forget to divide by repetitions)
            Mistake("REPEATS_TREATED_DISTINCT",
                    _arr(w, together_pred if p["mode"] == "together" else f"not ({together_pred})",
                         f"fact({n - k + 1}) * fact({k})" if p["mode"] == "together"
                         else f"fact({n}) - fact({n - k + 1}) * fact({k})", distinct=True),
                    "Students apply n! directly and forget that identical letters give identical words.",
                    "Swapping two identical letters does not create a new word, so divide by the factorial of "
                    "each repetition."),
            # 2. block counted but vowels not arranged inside the block
            Mistake("BLOCK_NOT_ARRANGED",
                    {"kind": "combinatorics", "model": ["vowels glued in one fixed internal order"],
                     "quantities": {"N": {"closed": (f"{_mperm({**con, '#': 1})}" if p["mode"] == "together"
                                                     else f"{_mperm(c)} - {_mperm({**con, '#': 1})}"),
                                          "enum": {"universe": {"type": "arrangements",
                                                                "items": f"list('{''.join(ch * m for ch, m in con.items())}#')"}}
                                          if p["mode"] == "together" else
                                          {"universe": {"type": "direct",
                                                        "value": f"{_mperm(c)} - {_mperm({**con, '#': 1})}"}}}},
                     "target": "N"},
                    "Students treat the vowels as one unit but forget the vowels can be rearranged inside it.",
                    "The vowel block itself has its own arrangements, which multiply the count."),
            # 3. answer the opposite case (together vs not together)
            Mistake("COMPLEMENT_CASE",
                    _arr(w, f"not ({together_pred})" if p["mode"] == "together" else together_pred,
                         f"{_mperm(c)} - {_mperm({**con, '#': 1})} * {_mperm(vow)}" if p["mode"] == "together"
                         else f"{_mperm({**con, '#': 1})} * {_mperm(vow)}"),
                    "Students mix up the case asked with its complement.",
                    "The question asks for the other case; the two counts add up to the total."),
            # 4. ignore the condition: all arrangements
            Mistake("CONDITION_IGNORED", _arr(w, None, _mperm(c)),
                    "Students count all arrangements and forget the vowel condition.",
                    "Only arrangements meeting the vowel condition should be counted."),
        ]
        return rep

    def explain(p, v):
        w = p["word"]
        c = _counts(w)
        vow = "".join(ch * m for ch, m in c.items() if ch in VOWELS)
        con = "".join(ch * m for ch, m in c.items() if ch not in VOWELS)
        rep = ", ".join(f"{ch}×{m}" for ch, m in c.items() if m > 1) or "none"
        return (f"<p>Letters of {w}: vowels {vow}, consonants {con}; repeated letters: {rep}.</p>"
                f"<p>Glue the vowels into one block: arrange the block with the consonants, then the vowels "
                f"inside the block, dividing by repetitions each time."
                + ("" if p["mode"] == "together" else " Subtract this from all arrangements of the word.")
                + f"</p><p>Answer: <b>{v}</b>. (Checked by listing every distinct arrangement.)</p>")

    return Family(id="pnc.vowels_block", subject=SUBJ, chapter=CH, topic="Conditional Permutations",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes,
                  explain=explain,
                  modelled_on=["E0UshBABGmQdzdNVQPjgy2xukg4n2d68", "1lgzxfup5", "m6srmykg"]).register()


VOWELS_BLOCK = vowels_together()


# ============================================================================ shared helpers (new families)
from itertools import permutations as _permutations, product as _product  # noqa: E402
from math import comb as _comb, factorial as _fact, perm as _perm  # noqa: E402


def Q(closed: str, uni: dict, where=None, agg=None) -> dict:
    e = {"universe": uni}
    if where is not None:
        e["where"] = where
    if agg is not None:
        e["agg"] = agg
    return {"closed": closed, "enum": e}


def F(quantities: dict, target: str = "N", model=()) -> dict:
    return {"kind": "combinatorics", "quantities": quantities, "target": target, "model": list(model)}


def ARR(items, length=None):
    u = {"type": "arrangements", "items": items}
    if length is not None:
        u["length"] = length
    return u


def SEL(items, size=None):
    u = {"type": "selections", "items": items}
    if size is not None:
        u["size"] = size
    return u


def DIRECT(expr: str) -> dict:
    return {"type": "direct", "value": expr}


def direct(expr: str, model: str) -> dict:
    """A misreading that is a formula, not a set of objects: engine evaluates the student's expression literally."""
    return F({"N": Q(expr, DIRECT(expr))}, model=[model])


def _join(xs, last="and") -> str:
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + f" {last} " + xs[-1]


def _mp(word) -> int:
    r = _fact(len(word))
    for v in Counter(word).values():
        r //= _fact(v)
    return r


# ============================================================================ 1. dictionary rank
RANK_WORDS = ["BUTTER", "COFFEE", "RABBIT", "KITTEN", "BOTTLE", "PUZZLE", "DINNER", "TICKET", "VALLEY", "SUMMER",
              "WINTER", "PLANET", "CANDLE", "FOREST", "SILVER", "ROCKET", "JUNGLE", "PENCIL", "TEACHER", "FREEDOM",
              "BALANCE", "COMPASS", "GALLERY", "KITCHEN", "CABINET", "PATTERN", "LIBRARY", "PICNIC"]


def _rank_terms(w: str):
    """Per position: (letter, correct contribution, contributions under three wrong procedures)."""
    out = []
    for i, ch in enumerate(w):
        rem = Counter(w[i:])
        smaller = sorted(c for c in rem if c < ch)
        correct = sum(_mp("".join((rem - Counter(c)).elements())) for c in smaller)
        copies = sum(rem[c] for c in smaller)                       # copies counted separately
        out.append({"ch": ch, "smaller": smaller, "correct": correct,
                    "distinct_tags": copies * _fact(len(w) - 1 - i),
                    "no_div": len(smaller) * _fact(len(w) - 1 - i),
                    "all_letters": len({c for c in w if c < ch}) * _mp(w[i + 1:])})
    return out


def dictionary_rank() -> Family:
    def sample(rng):
        return {"word": rng.choice(RANK_WORDS)}

    def formal(p):
        w = p["word"]
        return F({"N": Q(f"lexrank('{w}') - 1", ARR(f"list('{w}')"), f"x < tuple('{w}')")}, target="N + 1",
                 model=["all distinct arrangements of the letters, listed in dictionary (lexicographic) order",
                        "rank = 1 + number of words strictly before it"])

    def stem(p):
        w = p["word"]
        return (f"<p>All the words (with or without meaning) that can be formed using every letter of the word "
                f"<b>{w}</b> exactly once are listed in alphabetical order, as in a dictionary. "
                f"The position (serial number) of the word <b>{w}</b> in this list is:</p>")

    def mistakes(p):
        w = p["word"]
        t = _rank_terms(w)
        n = len(w)
        tagged = f"[(c, i) for i, c in enumerate('{w}')]"
        return [
            Mistake("REPEATS_TREATED_DISTINCT",
                    F({"N": Q(" + ".join(str(x["distinct_tags"]) for x in t) or "0", ARR(tagged),
                              f"[x[j][0] < '{w}'[j] for j in range({n}) if x[j] != ('{w}'[j], j)][:1] == [True]")}, target="N + 1",
                      model=["identical letters treated as different (labelled copies); the given word = copies in "
                             "their original order; words before it in the labelled list"]),
                    "Students use (remaining)! for every smaller letter copy, as if repeated letters were different.",
                    "Identical letters give identical words: each block must be counted with the repeated letters "
                    "divided out, and each distinct smaller letter only once."),
            Mistake("NO_DIVISION_FOR_REPEATS",
                    direct(" + ".join(str(x["no_div"]) for x in t) + " + 1",
                           "distinct smaller letters x (remaining)! with no division by repeated letters"),
                    "Students pick the smaller letters correctly but multiply by (remaining)! without dividing "
                    "by the factorials of repeated letters.",
                    "The remaining letters contain repeats, so the number of words in each block is a "
                    "multiset permutation count, not a plain factorial."),
            Mistake("USED_LETTERS_COUNTED_AGAIN",
                    direct(" + ".join(str(x["all_letters"]) for x in t) + " + 1",
                           "letters smaller than the current one counted from the whole word, not the unused ones"),
                    "Students count all letters of the word smaller than the current letter, including letters "
                    "already fixed in earlier places.",
                    "Only letters still unused can be placed at the current position."),
            Mistake("COUNTED_FROM_END",
                    F({"N": Q(f"mperm('{w}') - lexrank('{w}') + 1", ARR(f"list('{w}')"), f"x >= tuple('{w}')")},
                      model=["position counted from the end of the list (reverse alphabetical order)"]),
                    "Students order the letters in reverse (Z to A) or count the word's position from the end.",
                    "Dictionary order starts from the alphabetically smallest word."),
            # last resort only (generate takes the first 3 distinct values): its value is adjacent to the key
            Mistake("FORGOT_PLUS_ONE",
                    F({"N": Q(f"lexrank('{w}') - 1", ARR(f"list('{w}')"), f"x < tuple('{w}')")},
                      model=["number of words before it, reported as its position"]),
                    "Students count the words that come before the given word and stop there.",
                    "If k words come before it, the word itself is at position k + 1."),
        ]

    def explain(p, v):
        w = p["word"]
        t = _rank_terms(w)
        letters = "".join(sorted(w))
        parts = [f"{x['correct']}" for x in t if x["correct"]]
        steps = "".join(f"<li>Position {i + 1} = {x['ch']}: words starting with a smaller unused letter "
                        f"({_join(x['smaller']) if x['smaller'] else 'none'}) here: {x['correct']}</li>"
                        for i, x in enumerate(t) if x["correct"] or i == 0)
        return (f"<p>Letters in alphabetical order: {letters}. Fix the letters of {w} one place at a time and count "
                f"the words that begin with a smaller unused letter at that place (dividing by repeated letters "
                f"among the rest).</p><ul>{steps}</ul>"
                f"<p>Words before {w}: {' + '.join(parts) or '0'} = {int(v) - 1}, so its position is "
                f"<b>{v}</b>. (Checked by listing all {_mp(w)} words.)</p>")

    return Family(id="pnc.dictionary_rank", subject=SUBJ, chapter=CH, topic="Dictionary Rank of a Word",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["MWbLRehjPiKaEgcg", "IplDhMsmdCoRdapu"]).register()


DICTIONARY_RANK = dictionary_rank()


# ============================================================================ 2. numbers from given digits
DIGIT_CONDS = {
    "even": ("even", "x[0] != 0 and num(x) % 2 == 0", 1, lambda s: int(s) % 2 == 0),
    "odd": ("odd", "x[0] != 0 and num(x) % 2 == 1", 1, lambda s: int(s) % 2 == 1),
    "div5": ("divisible by 5", "x[0] != 0 and num(x) % 5 == 0", 1, lambda s: int(s) % 5 == 0),
    "div4": ("divisible by 4", "x[0] != 0 and num(x) % 4 == 0", 2, lambda s: int(s) % 4 == 0),
}


def _digit_suffixes(digits, cond, rep=False):
    s = DIGIT_CONDS[cond][2]
    pool = list(_product(digits, repeat=s) if rep else _permutations(digits, s))
    ok = [t for t in pool if DIGIT_CONDS[cond][3]("".join(map(str, t)))]
    return ok


def digit_numbers() -> Family:
    def sample(rng):
        while True:
            nz = sorted(rng.sample(range(1, 10), rng.randint(4, 6)))
            cond = rng.choice(list(DIGIT_CONDS))
            k = rng.choice([3, 4])
            digits = [0] + nz
            with0 = [t for t in _digit_suffixes(digits, cond) if 0 in t]
            ok = _digit_suffixes(digits, cond)
            if len(ok) >= 2 and (cond == "odd" or with0) and len(ok) > len(with0):
                return {"digits": digits, "k": k, "cond": cond}

    def _closed(p, leading_zero_fix_always=False, allow_lead0=False):
        d, k, cond = p["digits"], p["k"], p["cond"]
        n, s = len(d), DIGIT_CONDS[cond][2]
        suf = _digit_suffixes(d, cond)
        a = sum(1 for t in suf if 0 in t)
        b = len(suf) - a
        m, t = n - s, k - s
        if allow_lead0:
            return f"{a + b}*P({m}, {t})"
        if leading_zero_fix_always:
            return f"{a + b}*(P({m}, {t}) - P({m - 1}, {t - 1}))"
        return f"{a}*P({m}, {t}) + {b}*(P({m}, {t}) - P({m - 1}, {t - 1}))"

    def formal(p):
        d, k, cond = p["digits"], p["k"], p["cond"]
        return F({"N": Q(_closed(p), ARR(str(d), k), DIGIT_CONDS[cond][1])},
                 model=[f"{k}-digit numbers: first digit non-zero; digits not repeated",
                        "case split on the last digit(s) fixed by the divisibility rule; leading-zero cases removed"])

    def stem(p):
        d, k, cond = p["digits"], p["k"], p["cond"]
        what = DIGIT_CONDS[cond][0]
        return (f"<p>How many {k}-digit numbers that are <b>{what}</b> can be formed using the digits "
                f"{_join(d)}, if no digit may be repeated in a number?</p>")

    def mistakes(p):
        d, k, cond = p["digits"], p["k"], p["cond"]
        n, s = len(d), DIGIT_CONDS[cond][2]
        rep = len(_digit_suffixes(d, cond, rep=True))
        pred = DIGIT_CONDS[cond][1]
        out = [
            Mistake("LEADING_ZERO_ALLOWED",
                    F({"N": Q(_closed(p, allow_lead0=True), ARR(str(d), k), pred.replace("x[0] != 0 and ", ""))},
                      model=["strings with 0 allowed in the first place counted as numbers"]),
                    "Students fill the remaining places with any unused digits, including 0 in the first place.",
                    f"A number starting with 0 is not a {k}-digit number; those cases must be excluded."),
            Mistake("ZERO_CASE_NOT_SEPARATED",
                    direct(_closed(p, leading_zero_fix_always=True),
                           "the leading-zero cases subtracted even when 0 is already used at the end"),
                    "Students remove the 'first digit 0' cases for every ending, without splitting the case "
                    "where 0 itself is the last digit.",
                    "When 0 is already used in the last place, the first place cannot be 0 anyway, so nothing "
                    "should be subtracted in that case."),
            Mistake("REPETITION_ALLOWED",
                    F({"N": Q(f"{rep}*{n - 1}*{n}**{k - s - 1}",
                              {"type": "product", "alphabet": str(d), "length": k}, pred)},
                      model=["digits allowed to repeat"]),
                    "Students overlook 'no digit may be repeated' and use n choices for every place.",
                    "Each digit can be used at most once, so the choices shrink from place to place."),
        ]
        if cond == "div4":
            out.insert(2, Mistake("LAST_DIGIT_EVEN_ONLY",
                                  F({"N": Q(_closed({**p, "cond": "even"}), ARR(str(d), k),
                                            DIGIT_CONDS["even"][1])},
                                    model=["divisibility by 4 replaced by divisibility by 2"]),
                                  "Students test divisibility by 4 using only the last digit (even).",
                                  "A number is divisible by 4 when the number formed by its last TWO digits is."))
        out.append(Mistake("CONDITION_IGNORED",
                           F({"N": Q(f"{n - 1}*P({n - 1}, {k - 1})", ARR(str(d), k), "x[0] != 0")},
                             model=["all numbers, divisibility condition dropped"]),
                           "Students count all numbers with distinct digits and forget the divisibility condition.",
                           "Only numbers meeting the stated condition are to be counted."))
        return out

    def explain(p, v):
        d, k, cond = p["digits"], p["k"], p["cond"]
        n, s = len(d), DIGIT_CONDS[cond][2]
        suf = _digit_suffixes(d, cond)
        a = [t for t in suf if 0 in t]
        b = [t for t in suf if 0 not in t]
        fmt = lambda ts: ", ".join("".join(map(str, t)) for t in ts)  # noqa: E731
        m, t = n - s, k - s
        txt = (f"<p>The last {'digit' if s == 1 else 'two digits'} must be one of: {fmt(suf)}.</p>")
        if a:
            txt += (f"<p>Endings containing 0 ({fmt(a)}): the other {t} places are filled from the remaining {m} "
                    f"digits in $^{{{m}}}P_{{{t}}} = {_perm(m, t)}$ ways each.</p>")
        txt += (f"<p>Endings without 0 ({fmt(b)}): $^{{{m}}}P_{{{t}}} - {{}}^{{{m - 1}}}P_{{{t - 1}}} = "
                f"{_perm(m, t) - _perm(m - 1, t - 1)}$ ways each (remove those starting with 0).</p>"
                f"<p>Total = {(str(len(a)) + '×' + str(_perm(m, t)) + ' + ') if a else ''}"
                f"{len(b)}×{_perm(m, t) - _perm(m - 1, t - 1)} = <b>{v}</b>.</p>")
        return txt

    return Family(id="pnc.digit_numbers", subject=SUBJ, chapter=CH, topic="Number Formation with Conditions",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["1ktbiwpdb", "shaQfGQgffjfRATa", "1l6hzoa3g"]).register()


DIGIT_NUMBERS = digit_numbers()


# ============================================================================ 3. committees: at least / at most
GROUPS = [("men", "women", "committee"), ("boys", "girls", "team"), ("teachers", "students", "panel"),
          ("seniors", "juniors", "delegation")]
SINGULAR = {"women": "woman", "girls": "girl", "students": "student", "juniors": "junior"}


def committee_atleast() -> Family:
    def sample(rng):
        while True:
            g = rng.randrange(len(GROUPS))
            m, w = rng.randint(5, 8), rng.randint(3, 6)
            r = rng.choice([4, 5])
            mode = rng.choice(["atleast", "atmost"])
            a = rng.randint(1, 3)
            if m + w > 13 or a >= w or a >= r or r - a > m:
                continue
            if mode == "atleast" and a < 2 and rng.random() < 0.6:
                continue                                          # prefer a >= 2 (richer at-least problems)
            return {"m": m, "w": w, "r": r, "a": a, "mode": mode, "g": g}

    def _items(p):
        return f"[('A', i) for i in range({p['m']})] + [('B', i) for i in range({p['w']})]"

    def _cnt():
        return "sum(1 for t in x if t[0] == 'B')"

    def _range(p, lo_op):
        m, w, r, a = p["m"], p["w"], p["r"], p["a"]
        js = [j for j in range(0, min(w, r) + 1) if r - j <= m and lo_op(j, a)]
        return js

    def _formal(p, ok, closed_js, note, agg=None, arranged=False):
        closed = " + ".join(f"C({p['w']}, {j})*C({p['m']}, {p['r'] - j})" for j in closed_js) or "0"
        if arranged:
            closed = f"fact({p['r']})*({closed})"
            uni = ARR(_items(p), p["r"])
        else:
            uni = SEL(_items(p), p["r"])
        return F({"N": Q(closed, uni, ok, agg)}, model=[note])

    def formal(p):
        a = p["a"]
        if p["mode"] == "atleast":
            js = _range(p, lambda j, a: j >= a)
            ok = f"{_cnt()} >= {a}"
        else:
            js = _range(p, lambda j, a: j <= a)
            ok = f"{_cnt()} <= {a}"
        return _formal(p, ok, js, "unordered selection of distinct people; case split on the number from group B")

    def stem(p):
        A, B, what = GROUPS[p["g"]]
        cond = "at least" if p["mode"] == "atleast" else "at most"
        return (f"<p>A {what} of {p['r']} is to be chosen from {p['m']} {A} and {p['w']} {B}. In how many ways "
                f"can this be done if the {what} must contain <b>{cond} {p['a']}</b> "
                f"{SINGULAR[B] if p['a'] == 1 else B}?</p>")

    def mistakes(p):
        m, w, r, a = p["m"], p["w"], p["r"], p["a"]
        atl = p["mode"] == "atleast"
        cnt = _cnt()
        if atl:
            dbl = F({"N": Q(f"C({w}, {a})*C({m + w - a}, {r - a})", SEL(_items(p), r), f"{cnt} >= {a}",
                            {"sum": f"C({cnt}, {a})"})},
                    model=[f"choose {a} from group B first, then the rest from everyone left (each committee "
                           f"counted once per choice of the 'first' {a})"])
        else:
            mc = f"sum(1 for t in x if t[0] == 'A')"
            dbl = F({"N": Q(f"C({m}, {r - a})*C({m + w - r + a}, {a})", SEL(_items(p), r), f"{mc} >= {r - a}",
                            {"sum": f"C({mc}, {r - a})"})},
                    model=[f"choose {r - a} from group A first, then the rest from everyone left (overcount)"])
        exact = _formal(p, f"{cnt} == {a}", [a], "exactly a from group B")
        if atl:
            strict = _formal(p, f"{cnt} > {a}", _range(p, lambda j, a: j > a), "'at least' read as 'more than'")
            opp = _formal(p, f"{cnt} <= {a}", _range(p, lambda j, a: j <= a), "'at least' read as 'at most'")
        else:
            strict = _formal(p, f"{cnt} < {a}", _range(p, lambda j, a: j < a), "'at most' read as 'fewer than'")
            opp = _formal(p, f"{cnt} >= {a}", _range(p, lambda j, a: j >= a), "'at most' read as 'at least'")
        js = _range(p, (lambda j, a: j >= a) if atl else (lambda j, a: j <= a))
        ordered = _formal(p, f"{cnt} {'>=' if atl else '<='} {a}", js, "members arranged (ordered) instead of chosen",
                          arranged=True)
        B = GROUPS[p["g"]][1]
        return [
            Mistake("DOUBLE_COUNTING", dbl,
                    f"Students first 'secure' the required {B} and then choose the rest from all remaining people.",
                    "A committee with more than the minimum is then counted several times (once for each choice "
                    "of which members were 'secured' first); split into disjoint cases instead."),
            Mistake("EXACTLY_INSTEAD", exact,
                    "Students count only the boundary case and miss the other cases.",
                    f"'{'At least' if atl else 'At most'}' includes every admissible number, not just {a}."),
            Mistake("STRICT_INEQUALITY", strict,
                    f"Students read '{'at least' if atl else 'at most'} {a}' as "
                    f"'{'more than' if atl else 'fewer than'} {a}'.",
                    f"The case with exactly {a} {B} is allowed."),
            Mistake("OPPOSITE_CONDITION", opp,
                    "Students mix up 'at least' and 'at most'.",
                    "The inequality runs the other way."),
            Mistake("ORDER_COUNTED", ordered,
                    "Students use permutations (nPr) for a selection.",
                    "A committee is a set of people: the order in which they are chosen does not matter."),
        ]

    def explain(p, v):
        A, B, what = GROUPS[p["g"]]
        atl = p["mode"] == "atleast"
        js = _range(p, (lambda j, a: j >= a) if atl else (lambda j, a: j <= a))
        terms = " + ".join(f"\\binom{{{p['w']}}}{{{j}}}\\binom{{{p['m']}}}{{{p['r'] - j}}}" for j in js)
        nums = " + ".join(str(_comb(p['w'], j) * _comb(p['m'], p['r'] - j)) for j in js)
        return (f"<p>Split by the number $j$ of {B} chosen ($j = {', '.join(map(str, js))}$); the cases are "
                f"disjoint, so add them:</p><p>${terms} = {nums} = {v}$.</p><p>Answer: <b>{v}</b>.</p>")

    return Family(id="pnc.committee_atleast", subject=SUBJ, chapter=CH, topic="Selections with Conditions",
                  difficulty="EASY", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["ynFU9TI4bBJDhzTbt7TZv", "Ya9LDYYS0XiNoh28"]).register()


COMMITTEE_ATLEAST = committee_atleast()


# ============================================================================ 4. circular arrangements
def circular_seating() -> Family:
    def sample(rng):
        if rng.random() < 0.55:
            n = rng.randint(4, 6)
            k = rng.randint(2, min(n, 8 - n))
            return {"mode": "no_two", "n": n, "k": k}
        return {"mode": "pair_apart", "n": rng.randint(6, 8)}

    def _people(p):
        if p["mode"] == "no_two":
            men = [f"M{i}" for i in range(1, p["n"] + 1)]
            wom = [f"W{i}" for i in range(1, p["k"] + 1)]
            return men + wom, wom
        return ["P", "Q"] + [f"X{i}" for i in range(1, p["n"] - 1)], ["P", "Q"]

    def formal(p):
        items, grp = _people(p)
        circ = {"type": "circular", "items": str(items)}
        if p["mode"] == "no_two":
            return F({"N": Q(f"fact({p['n'] - 1})*P({p['n']}, {p['k']})", circ, f"cnoadj(x, {grp})")},
                     model=["round table: arrangements differing by a rotation are the same",
                            "men seated first ((n-1)! ways), women in the n gaps between men"])
        n = p["n"]
        return F({"N": Q(f"fact({n - 1}) - 2*fact({n - 2})", circ, "not cadj(x, 'P', 'Q')")},
                 model=["round table: rotations identical", "total minus arrangements with P, Q adjacent"])

    def stem(p):
        if p["mode"] == "no_two":
            return (f"<p>In how many ways can {p['n']} men and {p['k']} women be seated around a circular table "
                    f"so that <b>no two women sit next to each other</b>? (Arrangements that differ only by a "
                    f"rotation are considered the same.)</p>")
        return (f"<p>{p['n']} persons, among them two friends P and Q, are to be seated around a round table. "
                f"In how many ways can they be seated if <b>P and Q must not sit next to each other</b>? "
                f"(Seatings that differ only by a rotation are the same.)</p>")

    def mistakes(p):
        items, grp = _people(p)
        circ = {"type": "circular", "items": str(items)}
        lin = ARR(str(items))
        if p["mode"] == "no_two":
            n, k = p["n"], p["k"]
            return [
                Mistake("ROTATIONS_NOT_IDENTIFIED",
                        F({"N": Q(f"{n + k}*fact({n - 1})*P({n}, {k})", lin, f"cnoadj(x, {grp})")},
                          model=["seats treated as labelled: rotations counted separately"]),
                        "Students arrange the men in n! ways around the table, as if the seats were numbered.",
                        "Around a round table only relative positions matter, so the men give (n−1)! arrangements."),
                Mistake("WOMEN_NOT_ARRANGED",
                        F({"N": Q(f"fact({n - 1})*C({n}, {k})", circ,
                                  f"cnoadj(x, {grp}) and [t for t in x if t in {grp}] == {sorted(grp)}")},
                          model=["only the gaps for the women chosen; women not permuted"]),
                        "Students choose the gaps for the women with nCk and stop.",
                        "The women are different people, so after choosing the gaps they can be permuted "
                        "in k! ways (nPk in all)."),
                Mistake("ROW_GAPS_USED",
                        direct(f"fact({n - 1})*P({n + 1}, {k})", "n+1 gaps between men, as in a row"),
                        "Students use n + 1 gaps between n men, as for a row.",
                        "In a circle n men create only n gaps (the two 'end' gaps are the same gap)."),
                Mistake("TREATED_AS_ROW",
                        F({"N": Q(f"fact({n})*P({n + 1}, {k})", lin, f"noadj(x, {grp})")},
                          model=["people seated in a straight row instead of a circle"]),
                        "Students apply the row (gap) method to a circular table.",
                        "In a circle the first and last seats are adjacent and rotations are identical."),
            ]
        n = p["n"]
        return [
            Mistake("ROTATIONS_NOT_IDENTIFIED",
                    F({"N": Q(f"{n}*(fact({n - 1}) - 2*fact({n - 2}))", lin, "not cadj(x, 'P', 'Q')")},
                      model=["seats labelled: rotations counted separately"]),
                    "Students take n! for the total around a table.",
                    "Seatings differing only by a rotation are the same, so the total is (n−1)!."),
            Mistake("PAIR_ORDER_IGNORED",
                    F({"N": Q(f"fact({n - 1}) - fact({n - 2})", {"type": "circular", "items": str(items)},
                              f"not any(x[i] == 'P' and x[(i + 1) % {n}] == 'Q' for i in range({n}))")},
                      model=["P, Q block subtracted in one internal order only"]),
                    "Students tie P and Q into one unit but forget the unit can be PQ or QP.",
                    "The block of P and Q has 2 internal orders, so 2·(n−2)! seatings have them together."),
            Mistake("COMPLEMENT_CASE",
                    F({"N": Q(f"2*fact({n - 2})", {"type": "circular", "items": str(items)}, "cadj(x, 'P', 'Q')")},
                      model=["counted seatings with P and Q together"]),
                    "Students compute the 'together' count and give that as the answer.",
                    "The question asks for P and Q apart: subtract the 'together' count from the total."),
            Mistake("TREATED_AS_ROW",
                    F({"N": Q(f"fact({n}) - 2*fact({n - 1})", lin, "not adj(x, 'P', 'Q')")},
                      model=["seated in a row"]),
                    "Students use the row formula n! − 2(n−1)!.",
                    "In a circle rotations are identical and the end seats are neighbours."),
        ]

    def explain(p, v):
        if p["mode"] == "no_two":
            n, k = p["n"], p["k"]
            return (f"<p>Seat the {n} men first: $({n}-1)! = {_fact(n - 1)}$ ways (rotations identical). They "
                    f"create {n} gaps around the table; place the {k} women in different gaps in "
                    f"$^{{{n}}}P_{{{k}}} = {_perm(n, k)}$ ways.</p><p>Total $= {_fact(n - 1)} \\times "
                    f"{_perm(n, k)} = $ <b>{v}</b>.</p>")
        n = p["n"]
        return (f"<p>All seatings: $({n}-1)! = {_fact(n - 1)}$. With P, Q together (one unit, 2 internal "
                f"orders): $2\\cdot({n}-2)! = {2 * _fact(n - 2)}$.</p><p>Apart: ${_fact(n - 1)} - "
                f"{2 * _fact(n - 2)} = $ <b>{v}</b>.</p>")

    return Family(id="pnc.circular_seating", subject=SUBJ, chapter=CH, topic="Circular Permutations",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["EkC57Q2rx3Nbk6Jx", "1lgzycfb1", "J7rxWs0HNWj60oLGyuAiC"]).register()


CIRCULAR_SEATING = circular_seating()


# ============================================================================ 5. identical objects into distinct boxes
BOX_THINGS = [("identical balls", "distinct boxes", "box"), ("identical chocolates", "children", "child"),
              ("identical coins", "different purses", "purse"), ("identical pencils", "students", "student")]


def identical_into_boxes() -> Family:
    def sample(rng):
        k = rng.choice([3, 4])
        b = rng.choice([1, 1, 2])
        hi = 9 if k == 4 else 11               # keeps k^n (distinct-objects distractor) enumerable
        if k * b + 2 > hi:
            b = 1
        n = rng.randint(k * b + 2, hi)
        return {"n": n, "k": k, "b": b, "t": rng.randrange(len(BOX_THINGS))}

    def formal(p):
        n, k, b = p["n"], p["k"], p["b"]
        return F({"N": Q(f"C({n - k * b} + {k - 1}, {k - 1})", {"type": "compositions", "total": n, "parts": k,
                                                               "lo": b})},
                 model=["identical objects, distinct recipients: a distribution = (x_1..x_k), sum n, x_i >= b",
                        "stars and bars after giving b to each"])

    def stem(p):
        obj, rec, one = BOX_THINGS[p["t"]]
        cond = "no " + one + " is left empty" if p["b"] == 1 and one == "box" else \
            f"every {one} gets at least {p['b']}" + ("" if p["b"] > 1 else "")
        if p["b"] == 1 and one != "box":
            cond = f"every {one} gets at least one"
        return f"<p>In how many ways can {p['n']} {obj} be distributed among {p['k']} {rec} so that {cond}?</p>"

    def mistakes(p):
        n, k, b = p["n"], p["k"], p["b"]
        m = n - k * b
        out = [
            Mistake("EMPTY_ALLOWED",
                    F({"N": Q(f"C({n + k - 1}, {k - 1})", {"type": "compositions", "total": n, "parts": k, "lo": 0})},
                      model=["lower bound ignored: zero allowed"]),
                    "Students apply the 'empty allowed' formula C(n+k−1, k−1) directly.",
                    f"Each recipient must get at least {b}; first give {b} to each and distribute only the rest."),
            Mistake("WRONG_BARS",
                    F({"N": Q(f"C({m + k - 1}, {k})", SEL(f"list(range({m + k - 1}))", k))},
                      model=["k bars chosen instead of k-1"]),
                    "Students choose k separators instead of k − 1.",
                    "k recipients need only k − 1 dividers between them."),
            Mistake("DISTINCT_OBJECTS",
                    F({"N": Q(f"fact({k})*stirling2({n}, {k})" if b == 1 else
                              f"sum(multinomial({n}, a, c, {n} - a - c) for a in range({b}, {n + 1}) "
                              f"for c in range({b}, {n + 1}) if {n} - a - c >= {b})" if k == 3 else
                              f"sum(multinomial({n}, a, c, d, {n} - a - c - d) for a in range({b}, {n + 1}) "
                              f"for c in range({b}, {n + 1}) for d in range({b}, {n + 1}) if {n} - a - c - d >= {b})",
                              {"type": "product", "alphabet": f"list(range({k}))", "length": n},
                              f"all(count(x, j) >= {b} for j in range({k}))")},
                      model=["objects treated as distinct (each object picks a recipient)"]),
                    "Students let each object choose its recipient, as if the objects were different.",
                    "The objects are identical: only how many each recipient gets matters."),
        ]
        if b > 1:
            out.insert(1, Mistake("LOWER_BOUND_ONE",
                                  F({"N": Q(f"C({n - 1}, {k - 1})", {"type": "compositions", "total": n, "parts": k,
                                                                    "lo": 1})},
                                    model=["'at least b' replaced by 'non-empty'"]),
                                  "Students use the non-empty formula C(n−1, k−1) whatever the lower bound.",
                                  f"Each must get at least {b}, not just at least 1: subtract {b}·{k} first."))
        out.append(Mistake("POWER_FORMULA",
                           F({"N": Q(f"{k}**{n}", {"type": "product", "alphabet": f"list(range({k}))", "length": n})},
                             model=["k^n: each object has k choices, no condition"]),
                           "Students use k^n for distributing n objects into k places.",
                           "k^n counts distributions of distinct objects with no restriction."))
        return out

    def explain(p, v):
        n, k, b = p["n"], p["k"], p["b"]
        m = n - k * b
        return (f"<p>First give {b} to each of the {k} recipients; {m} identical objects remain, to be shared "
                f"with no restriction. Number of non-negative solutions of $x_1+\\dots+x_{{{k}}} = {m}$ is "
                f"$\\binom{{{m}+{k}-1}}{{{k}-1}} = \\binom{{{m + k - 1}}}{{{k - 1}}}$ = <b>{v}</b>.</p>")

    return Family(id="pnc.identical_into_boxes", subject=SUBJ, chapter=CH, topic="Distribution of Identical Objects",
                  difficulty="EASY", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["cxhMyG1Oo7EJnOxq", "lWJFreINJxGWYGy2"]).register()


IDENTICAL_INTO_BOXES = identical_into_boxes()


# ============================================================================ 6. derangements (numerical)
DER_SETTINGS = 3   # 0 letters/envelopes, 1 students/seats, 2 guests/hats


def derangement() -> Family:
    def sample(rng):
        n = rng.randint(4, 7)
        r = rng.choice([0, 1, 2]) if n >= 5 else rng.choice([0, 1])
        return {"n": n, "r": r, "s": rng.randrange(DER_SETTINGS)}

    def _fixed():
        return "sum(1 for i in range(len(x)) if x[i] == i)"

    def formal(p):
        n, r = p["n"], p["r"]
        return F({"N": Q(f"C({n}, {r})*derange({n - r})", ARR(f"list(range({n}))"), f"{_fixed()} == {r}")},
                 model=["assignment = permutation of n; item i correct iff x[i] == i",
                        "choose the r correct ones, derange the rest"])

    def stem(p):
        n, r = p["n"], p["r"]
        if p["s"] == 0:
            intro = f"{n} letters are written to {n} different people and the {n} envelopes are addressed."
            act = "the letters be put into the envelopes, one letter per envelope,"
            one, many = "letter is put into its correct envelope", "letters are put into their correct envelopes"
        elif p["s"] == 1:
            intro = f"{n} students have {n} assigned seats in a row of {n} seats."
            act = "the students sit, one per seat,"
            one, many = "student sits in his or her own seat", "students sit in their own seats"
        else:
            intro = f"{n} guests leave their {n} distinct hats at a counter, and the hats are handed back at random."
            act = "the hats be returned, one per guest,"
            one, many = "guest gets back his or her own hat", "guests get back their own hats"
        cond = f"<b>no</b> {one}" if r == 0 else f"<b>exactly {r}</b> {one if r == 1 else many}"
        return f"<p>{intro} In how many ways can {act} so that {cond}?</p>"

    def mistakes(p):
        n, r = p["n"], p["r"]
        fx = _fixed()
        out = [
            Mistake("REST_NOT_DERANGED",
                    F({"N": Q(f"C({n}, {r})*fact({n - r})", ARR(f"list(range({n}))"), f"{fx} >= {r}",
                              {"sum": f"C({fx}, {r})"})},
                      model=["after fixing r correct ones, the rest arranged freely"]),
                    "Students fix the r correct items and arrange the rest in (n−r)! ways.",
                    "The remaining items must ALL be wrong, which is a derangement D(n−r), not (n−r)!."),
            Mistake("AT_LEAST_INSTEAD" if r > 0 else "NOT_ALL_CORRECT",
                    F({"N": Q(f"fact({n}) - " + " - ".join(f"C({n}, {j})*derange({n - j})" for j in range(r))
                              if r > 0 else f"fact({n}) - 1", ARR(f"list(range({n}))"),
                              f"{fx} >= {r}" if r > 0 else f"{fx} < {n}")},
                      model=["'at least r correct'" if r > 0 else "'not all correct' instead of 'none correct'"]),
                    "Students misread the condition.",
                    "The stem fixes the exact number of correct items."),
            Mistake("WRONG_DERANGEMENT_FORMULA",
                    direct(f"C({n}, {r})*(fact({n - r}) - {n - r})",
                           "derangements taken as (m)! minus the m arrangements with one item right"),
                    "Students subtract only the cases with a single item correct.",
                    "Use inclusion-exclusion: D(m) = m!(1 − 1/1! + 1/2! − … )."),
        ]
        if r > 0:
            out.append(Mistake("FORGOT_CHOICE_OF_CORRECT",
                               F({"N": Q(f"derange({n - r})", ARR(f"list(range({n - r}))"),
                                         "all(x[i] != i for i in range(len(x)))")},
                                 model=["which r are correct not chosen"]),
                               "Students only derange the remaining items.",
                               f"The {r} correct items can be any of the {n}: multiply by C({n}, {r})."))
        return out

    def explain(p, v):
        n, r = p["n"], p["r"]
        m = n - r
        return (f"<p>Choose the {r} item(s) that are correct in $\\binom{{{n}}}{{{r}}} = {_comb(n, r)}$ way(s); the "
                f"other {m} must all be wrong: $D_{{{m}}} = {m}!\\left(1-\\frac{{1}}{{1!}}+\\frac{{1}}{{2!}}-\\dots"
                f"\\right)$.</p><p>Answer $= {_comb(n, r)} \\times D_{{{m}}} = $ <b>{v}</b>.</p>"
                if r else
                f"<p>Number of derangements $D_{{{n}}} = {n}!\\sum_{{j=0}}^{{{n}}} \\frac{{(-1)^j}}{{j!}} = $ "
                f"<b>{v}</b>.</p>")

    return Family(id="pnc.derangement", subject=SUBJ, chapter=CH, topic="Derangements", difficulty="MEDIUM",
                  sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain, numerical=True,
                  modelled_on=["SLjj7ptO9uQcIkLlhTjgy2xukfakunkv"]).register()


DERANGEMENT = derangement()


# ============================================================================ 7. gap method: no two of a kind adjacent
GAP_CASES = [("BALLOON", "V"), ("TOMATO", "V"), ("COLLEGE", "V"), ("TEACHER", "V"), ("CALENDAR", "V"),
             ("PARABOLA", "V"), ("BANANAS", "V"), ("ANIMALS", "V"), ("SEASONS", "V"), ("PARALLEL", "L"),
             ("ADDRESSES", "S"), ("ASSESSOR", "S"), ("TENNESSEE", "E"), ("COMMITTEE", "E"), ("PARALLEL", "V")]


def gap_method() -> Family:
    def sample(rng):
        w, g = rng.choice(GAP_CASES)
        return {"word": w, "group": g}

    def _split(p):
        w, g = p["word"], p["group"]
        G = "AEIOU" if g == "V" else g
        grp = "".join(c for c in w if c in G)
        oth = "".join(c for c in w if c not in G)
        return w, G, grp, oth

    def formal(p):
        w, G, grp, oth = _split(p)
        m, k = len(oth), len(grp)
        return F({"N": Q(f"mperm('{oth}')*C({m + 1}, {k})*mperm('{grp}')", ARR(f"list('{w}')"), f"noadj(x, '{G}')")},
                 model=["distinct arrangements of all letters (with or without meaning)",
                        "gap method: arrange the other letters, choose gaps (incl. both ends), arrange the group"])

    def _what(p):
        return "two vowels are next to each other" if p["group"] == "V" else f"two {p['group']}'s are adjacent"

    def stem(p):
        return (f"<p>The number of distinct words (with or without meaning) that can be formed using all the "
                f"letters of the word <b>{p['word']}</b> such that <b>no {_what(p)}</b> is:</p>")

    def mistakes(p):
        w, G, grp, oth = _split(p)
        m, k = len(oth), len(grp)
        blk = dict(Counter(oth))
        blk["#"] = 1
        tag_grp = [f"{c}{i}" for i, c in enumerate(grp)]
        tag_oth = [f"{c}{i}" for i, c in enumerate(oth)]
        out = [
            Mistake("NOT_ALL_TOGETHER_INSTEAD",
                    F({"N": Q(f"mperm('{w}') - {_mperm(blk)}*mperm('{grp}')", ARR(f"list('{w}')"),
                              f"not together(x, '{G}')")},
                      model=["'no two together' read as 'not all together' (total minus block)"]),
                    "Students compute total − (all of them together).",
                    "'Not all together' still allows two of them to be adjacent; 'no two together' needs every "
                    "one of them separated (gap method)."),
            Mistake("END_GAPS_MISSED",
                    F({"N": Q(f"mperm('{oth}')*C({m - 1}, {k})*mperm('{grp}')", ARR(f"list('{w}')"),
                              f"noadj(x, '{G}') and x[0] not in '{G}' and x[-1] not in '{G}'")},
                      model=["only the m-1 gaps between letters used"]),
                    f"Students use only the {m - 1} gaps between the other letters.",
                    f"The two ends are also gaps: {m} letters leave {m + 1} places."),
            Mistake("GROUP_NOT_ARRANGED",
                    F({"N": Q(f"mperm('{oth}')*C({m + 1}, {k})", ARR(f"list('{w}')"),
                              f"noadj(x, '{G}') and [t for t in x if t in '{G}'] == {sorted(grp)}")},
                      model=["gaps chosen, letters in the gaps not permuted"]),
                    "Students choose the gaps but forget to arrange the letters placed in them.",
                    "Different letters placed in the chosen gaps can be permuted among themselves."),
            Mistake("GROUP_REPEATS_NOT_DIVIDED",
                    F({"N": Q(f"mperm('{oth}')*C({m + 1}, {k})*fact({k})", ARR(f"list('{oth}') + {tag_grp}"),
                              f"noadj(x, {tag_grp})")},
                      model=["identical letters in the group treated as different"]),
                    f"Students arrange the {k} separated letters in {k}! ways.",
                    "Identical letters among them must be divided out."),
            Mistake("OTHER_REPEATS_NOT_DIVIDED",
                    F({"N": Q(f"fact({m})*C({m + 1}, {k})*mperm('{grp}')", ARR(f"{tag_oth} + list('{grp}')"),
                              f"noadj(x, '{G}')")},
                      model=["remaining letters arranged in m! ways ignoring their repeats"]),
                    f"Students arrange the other {m} letters in {m}! ways.",
                    "Repeated letters among them give identical words and must be divided out."),
        ]
        if _comb(m - 1, k) == 0:          # the end-gap slip would give 0: an option nobody would pick
            out = [x for x in out if x.id != "END_GAPS_MISSED"]
        return out

    def explain(p, v):
        w, G, grp, oth = _split(p)
        m, k = len(oth), len(grp)
        return (f"<p>Separate the letters {grp} from the others {oth}. Arrange the {m} other letters: "
                f"{_mp(oth)} ways. They leave {m + 1} gaps (including both ends); choose {k} of them: "
                f"$\\binom{{{m + 1}}}{{{k}}} = {_comb(m + 1, k)}$. Arrange {grp} in the chosen gaps: {_mp(grp)} "
                f"way(s).</p><p>Total $= {_mp(oth)} \\times {_comb(m + 1, k)} \\times {_mp(grp)} = $ <b>{v}</b>.</p>")

    return Family(id="pnc.gap_method", subject=SUBJ, chapter=CH, topic="Arrangements with Restrictions (Gap Method)",
                  difficulty="HARD", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["CtCfGCORzMr3qyUf", "m6t9xszj"]).register()


GAP_METHOD = gap_method()


# ============================================================================ 8. counting divisors (numerical)
def divisors_count() -> Family:
    MODES = ["total", "even", "odd", "square", "multiple", "proper"]

    def sample(rng):
        while True:
            primes = sorted(rng.sample([2, 3, 5, 7], rng.choice([2, 3, 3])))
            if 2 not in primes and rng.random() < 0.7:
                continue
            ex = [rng.randint(1, 5) for _ in primes]
            N = 1
            for q, e in zip(primes, ex):
                N *= q ** e
            if not 300 <= N <= 50000:
                continue
            modes = [m for m in MODES if not (m in ("even", "odd") and 2 not in primes)]
            mode = rng.choice(modes)
            q = primes[0] * primes[1] if mode == "multiple" else 0
            return {"N": N, "mode": mode, "q": q}

    def _fac(N):
        out, p = {}, 2
        while N > 1:
            while N % p == 0:
                out[p] = out.get(p, 0) + 1
                N //= p
            p += 1
        return out

    def _closed(p):
        f = _fac(p["N"])
        e = lambda q: f.get(q, 0)  # noqa: E731
        mode = p["mode"]
        if mode == "total":
            return "*".join(f"({x} + 1)" for x in f.values())
        if mode == "proper":
            return "*".join(f"({x} + 1)" for x in f.values()) + " - 2"
        if mode == "even":
            return "*".join([str(e(2))] + [f"({x} + 1)" for q, x in f.items() if q != 2])
        if mode == "odd":
            return "*".join([f"({x} + 1)" for q, x in f.items() if q != 2])
        if mode == "square":
            return "*".join(f"({x} // 2 + 1)" for x in f.values())
        qf = _fac(p["q"])
        return "*".join(f"({x} - {qf.get(q, 0)} + 1)" for q, x in f.items())

    def _cond(p):
        return {"total": "True", "proper": f"1 < x < {p['N']}", "even": "x % 2 == 0", "odd": "x % 2 == 1",
                "square": "x in set(j*j for j in range(1, 250))", "multiple": f"x % {p['q']} == 0"}[p["mode"]]

    def formal(p):
        N = p["N"]
        return F({"N": Q(_closed(p), {"type": "range", "lo": 1, "hi": N}, f"{N} % x == 0 and ({_cond(p)})")},
                 model=["positive divisors; exponent counting from the prime factorisation"])

    def stem(p):
        N, mode = p["N"], p["mode"]
        ask = {"total": f"How many positive divisors does ${N}$ have?",
               "proper": f"How many divisors of ${N}$ are there other than $1$ and ${N}$ itself?",
               "even": f"How many positive divisors of ${N}$ are even?",
               "odd": f"How many positive divisors of ${N}$ are odd?",
               "square": f"How many positive divisors of ${N}$ are perfect squares (including $1$)?",
               "multiple": f"How many positive divisors of ${N}$ are multiples of ${p['q']}$?"}[mode]
        return f"<p>{ask}</p>"

    def mistakes(p):
        N = p["N"]
        f = _fac(N)
        tau = "*".join(f"({x} + 1)" for x in f.values())
        return [
            Mistake("CONDITION_IGNORED",
                    F({"N": Q(tau, {"type": "range", "lo": 1, "hi": N}, f"{N} % x == 0")},
                      model=["all divisors counted"]),
                    "Students count all divisors.", "Only divisors with the stated property count."),
            Mistake("COMPLEMENT_COUNTED",
                    F({"N": Q(f"{tau} - ({_closed(p)})", {"type": "range", "lo": 1, "hi": N},
                              f"{N} % x == 0 and not ({_cond(p)})")},
                      model=["the divisors WITHOUT the property counted"]),
                    "Students count the opposite class of divisors.", "The property asked is the other one."),
            Mistake("EXPONENTS_MULTIPLIED", direct("*".join(str(x) for x in f.values()), "product of exponents"),
                    "Students multiply the exponents instead of (exponent + 1).",
                    "Each prime can appear with exponent 0, 1, …, e: that is e + 1 choices."),
            Mistake("EXPONENTS_ADDED", direct("+".join(f"({x} + 1)" for x in f.values()), "sum of (e+1)"),
                    "Students add the numbers of choices for each prime.",
                    "Choices for different primes are independent, so they multiply."),
        ]

    def explain(p, v):
        f = _fac(p["N"])
        fac = " \\cdot ".join(f"{q}^{{{x}}}" for q, x in f.items())
        how = {"total": "each exponent $e$ gives $e+1$ choices", "proper": "all divisors minus 1 and the number",
               "even": "the power of 2 must be at least 1", "odd": "the power of 2 must be 0",
               "square": "every exponent must be even", "multiple": f"the divisor must contain ${p['q']}$"}[p["mode"]]
        return (f"<p>${p['N']} = {fac}$. A divisor is $\\prod q^{{a_q}}$ with $0 \\le a_q \\le e_q$; here {how}. "
                f"Count = ${_closed(p).replace('*', ' \\times ').replace('//', '/')}$ = <b>{v}</b>.</p>")

    return Family(id="pnc.divisors", subject=SUBJ, chapter=CH, topic="Number of Divisors", difficulty="EASY",
                  sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain, numerical=True,
                  modelled_on=["1krygm1ew", "OjrcXgele0CMwAVPCy1kluvyg3b"]).register()


DIVISORS = divisors_count()


# ============================================================================ 9. points, lines, triangles (numerical)
def points_triangles() -> Family:
    def sample(rng):
        mode = rng.choice(["tri_collinear", "lines_collinear", "tri_two_lines", "quad_two_lines", "polygon_no_side"])
        if mode in ("tri_collinear", "lines_collinear"):
            n = rng.randint(9, 16)
            return {"mode": mode, "n": n, "m": rng.randint(3, min(7, n - 3))}
        if mode == "polygon_no_side":
            return {"mode": mode, "n": rng.randint(8, 15)}
        return {"mode": mode, "p": rng.randint(3, 8), "q": rng.randint(4, 9)}

    def _pts(p):
        if p["mode"] in ("tri_collinear", "lines_collinear"):
            return f"[('L', i) for i in range({p['m']})] + [('F', i) for i in range({p['n'] - p['m']})]"
        return f"[('L', i) for i in range({p['p']})] + [('M', i) for i in range({p['q']})]"

    def _cl(t):
        return f"sum(1 for t in x if t[0] == '{t}')"

    def formal(p):
        mode = p["mode"]
        if mode == "tri_collinear":
            n, m = p["n"], p["m"]
            return F({"N": Q(f"C({n}, 3) - C({m}, 3)", SEL(_pts(p), 3), f"{_cl('L')} < 3")},
                     model=["only the m marked points are collinear; three collinear points give no triangle"])
        if mode == "lines_collinear":
            n, m = p["n"], p["m"]
            return F({"N": Q(f"C({n}, 2) - C({m}, 2) + 1", SEL(_pts(p), 2), None,
                             {"sum": f"1 if {_cl('L')} < 2 else 1 / C({m}, 2)"})},
                     model=["each pair determines a line; all pairs from the m collinear points give one line",
                            "enumeration: pairs weighted by 1/(pairs determining the same line)"])
        if mode == "tri_two_lines":
            return F({"N": Q(f"C({p['p']}, 2)*{p['q']} + {p['p']}*C({p['q']}, 2)", SEL(_pts(p), 3),
                             f"0 < {_cl('L')} < 3")},
                     model=["vertices from two parallel lines; a triangle needs points from both lines"])
        if mode == "quad_two_lines":
            return F({"N": Q(f"C({p['p']}, 2)*C({p['q']}, 2)", SEL(_pts(p), 4), f"{_cl('L')} == 2")},
                     model=["quadrilateral with vertices on two parallel lines: 2 on each line"])
        n = p["n"]
        return F({"N": Q(f"{n}*({n} - 4)*({n} - 5) / 6", SEL(f"list(range({n}))", 3),
                         f"all((a - b) % {n} not in (1, {n - 1}) for a in x for b in x)")},
                 model=["triangles from vertices of a convex n-gon with no side along a side of the polygon"])

    def stem(p):
        mode = p["mode"]
        if mode == "tri_collinear":
            return (f"<p>There are {p['n']} points in a plane, of which exactly {p['m']} lie on one straight line; "
                    f"apart from these, no three of the points are collinear. The number of triangles that can "
                    f"be formed with vertices at these points is ________.</p>")
        if mode == "lines_collinear":
            return (f"<p>There are {p['n']} points in a plane, of which exactly {p['m']} lie on one straight line; "
                    f"apart from these, no three of the points are collinear. The number of distinct straight lines "
                    f"obtained by joining pairs of these points is ________.</p>")
        if mode == "tri_two_lines":
            return (f"<p>{p['p']} distinct points are marked on a line $L_1$ and {p['q']} distinct points on a line "
                    f"$L_2$ parallel to $L_1$. The number of triangles whose vertices are three of these "
                    f"{p['p'] + p['q']} points is ________.</p>")
        if mode == "quad_two_lines":
            return (f"<p>{p['p']} distinct points are marked on a line $L_1$ and {p['q']} distinct points on a line "
                    f"$L_2$ parallel to $L_1$. The number of quadrilaterals whose four vertices are among these "
                    f"points is ________.</p>")
        return (f"<p>The number of triangles whose vertices are vertices of a convex polygon with {p['n']} sides, "
                f"and none of whose sides is a side of the polygon, is ________.</p>")

    def mistakes(p):
        mode = p["mode"]
        if mode in ("tri_collinear", "lines_collinear"):
            n, m = p["n"], p["m"]
            r = 3 if mode == "tri_collinear" else 2
            return [
                Mistake("COLLINEAR_IGNORED", F({"N": Q(f"C({n}, {r})", SEL(_pts(p), r))}, model=["no correction"]),
                        "Students use nCr directly.", "Collinear points do not give distinct figures."),
                Mistake("ONE_FIGURE_NOT_ADDED" if r == 2 else "COLLINEAR_SET_COUNTED_ONCE",
                        direct(f"C({n}, 2) - C({m}, 2)" if r == 2 else f"C({n}, 3) - C({m}, 3) + 1",
                               "subtract/add-back of the collinear figure done wrongly"),
                        "Students mix up the triangle and line corrections.",
                        "The m collinear points give exactly ONE line but NO triangle."),
                Mistake("COLLINEAR_POINTS_DROPPED",
                        F({"N": Q(f"C({n - m}, {r})", SEL(_pts(p), r), f"{_cl('L')} == 0")},
                          model=["collinear points excluded entirely"]),
                        "Students throw away the collinear points.",
                        "Those points can still be used together with other points."),
                Mistake("SUBTRACTED_M", direct(f"C({n}, {r}) - {m}", "subtracts m"),
                        "Students subtract the number of collinear points.",
                        f"The overcount is the number of {r}-subsets of the collinear points, C(m, {r})."),
            ]
        if mode in ("tri_two_lines", "quad_two_lines"):
            a, b = p["p"], p["q"]
            s = a + b
            r = 3 if mode == "tri_two_lines" else 4
            return [
                Mistake("ALL_SUBSETS", F({"N": Q(f"C({s}, {r})", SEL(_pts(p), r))}, model=["nCr"]),
                        "Students take every choice of points.", "Points on one line are collinear."),
                Mistake("ONE_CASE_ONLY" if r == 3 else "ADDED_NOT_MULTIPLIED",
                        direct(f"C({a}, 2)*{b}" if r == 3 else f"C({a}, 2) + C({b}, 2)",
                               "only the case 'two on L1' counted" if r == 3 else "choices on the lines added"),
                        "Students count only the case with two vertices on the first line." if r == 3 else
                        "Students add the choices for the two lines.",
                        "The case with two vertices on the second line is equally valid." if r == 3 else
                        "Both pairs are needed together: the choices multiply."),
                Mistake("ONE_FROM_EACH_THEN_ANY" if r == 3 else "ORDERED_PAIRS",
                        direct(f"{a}*{b}*({s} - 2)" if r == 3 else f"P({a}, 2)*P({b}, 2)",
                               "one point from each line then any third point (double count)" if r == 3
                               else "pairs chosen in order"),
                        "Students secure one point on each line, then pick any third point." if r == 3 else
                        "Students choose the pair on each line in order.",
                        "Each triangle is then counted twice (once for each of its two same-line vertices)." if r == 3
                        else "The two points of a pair are unordered; nP2 counts each pair twice."),
                Mistake("SUBTRACT_ONE_LINE", direct(f"C({s}, {r}) - C({a}, {r})", "only one line corrected"),
                        "Students correct for collinear points on one line only.", "Both lines need correcting."),
            ]
        n = p["n"]
        return [
            Mistake("ALL_TRIANGLES", F({"N": Q(f"C({n}, 3)", SEL(f"list(range({n}))", 3))}, model=["nC3"]),
                    "Students count all triangles.", "Triangles sharing a side with the polygon are excluded."),
            Mistake("ONE_SIDE_ONLY_REMOVED", direct(f"C({n}, 3) - {n}*({n} - 4)", "only one-side triangles removed"),
                    "Students remove triangles with exactly one polygon side only.",
                    "Triangles with two polygon sides must be removed too."),
            Mistake("OVERLAP_DOUBLE_SUB", direct(f"C({n}, 3) - {n}*({n} - 4) - 2*{n}", "two-side cases subtracted twice"),
                    "Students subtract two-side triangles twice.", "Each such triangle is removed once."),
            Mistake("SIDE_SUBTRACT", direct(f"C({n}, 3) - {n}*({n} - 2)", "n(n-2) triangles with a side"),
                    "Students take n(n−2) triangles with a side.", "That counts two-side triangles twice."),
        ]

    def explain(p, v):
        mode = p["mode"]
        if mode == "tri_collinear":
            return (f"<p>All triples: $\\binom{{{p['n']}}}{{3}}$; the $\\binom{{{p['m']}}}{{3}}$ triples from the "
                    f"collinear points give no triangle. Answer: <b>{v}</b>.</p>")
        if mode == "lines_collinear":
            return (f"<p>All pairs give $\\binom{{{p['n']}}}{{2}}$ lines, but the $\\binom{{{p['m']}}}{{2}}$ pairs "
                    f"from the collinear points all give the same single line: "
                    f"$\\binom{{{p['n']}}}{{2}} - \\binom{{{p['m']}}}{{2}} + 1 = $ <b>{v}</b>.</p>")
        if mode == "tri_two_lines":
            return (f"<p>Two vertices on one line and one on the other: $\\binom{{{p['p']}}}{{2}}\\cdot{p['q']} + "
                    f"{p['p']}\\cdot\\binom{{{p['q']}}}{{2}} = $ <b>{v}</b>.</p>")
        if mode == "quad_two_lines":
            return (f"<p>Two vertices on each line (no three collinear): $\\binom{{{p['p']}}}{{2}}"
                    f"\\binom{{{p['q']}}}{{2}} = $ <b>{v}</b>.</p>")
        n = p["n"]
        return (f"<p>All triangles $\\binom{{{n}}}{{3}}$; with exactly one polygon side: $n(n-4) = {n * (n - 4)}$; "
                f"with two polygon sides: $n = {n}$. Answer $= \\binom{{{n}}}{{3}} - {n * (n - 4)} - {n} = "
                f"\\frac{{n(n-4)(n-5)}}{{6}} = $ <b>{v}</b>.</p>")

    return Family(id="pnc.points_triangles", subject=SUBJ, chapter=CH, topic="Geometrical Applications",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  numerical=True, modelled_on=["hZ0WqGlvxb9cOBdE", "foj68NgT56Ij10bv"]).register()


POINTS_TRIANGLES = points_triangles()


# ============================================================================ 10. selecting / arranging letters with repeats
SEL_WORDS = ["COMMITTEE", "PROPORTION", "EXCELLENCE", "ASSISTANT", "REFERENCE", "BOOKKEEPER", "STATISTICS",
             "PARALLELOGRAM", "ACCOMMODATION", "PEPPERMINT", "SUCCESSFUL"]
PATTERNS = {3: [(1, 1, 1), (2, 1), (3,)], 4: [(1, 1, 1, 1), (2, 1, 1), (2, 2), (3, 1), (4,)]}


def _pattern_terms(word: str, r: int, arrange: bool):
    """[(pattern, choose-expression, number, arrangement factor)] — the case method for repeated letters."""
    cnt = Counter(word)
    A = lambda j: sum(1 for v in cnt.values() if v >= j)  # noqa: E731
    out = []
    for pat in PATTERNS[r]:
        groups = sorted(Counter(pat).items(), key=lambda t: -t[0])       # (part size, how many letters)
        used, exprs, num = 0, [], 1
        for size, g in groups:
            exprs.append(f"C({A(size) - used}, {g})")
            num *= _comb(A(size) - used, g)
            used += g
        fac = _fact(r)
        for part in pat:
            fac //= _fact(part)
        out.append((pat, "*".join(exprs), num, fac if arrange else 1))
    return out


def letter_selection() -> Family:
    def sample(rng):
        return {"word": rng.choice(SEL_WORDS), "r": rng.choice([3, 4]), "mode": rng.choice(["select", "arrange"])}

    def _closed(w, r, arrange, skip_big=False):
        ts = [t for t in _pattern_terms(w, r, arrange) if not (skip_big and max(t[0]) >= 3)]
        return " + ".join(f"{e}*{f}" for _, e, _, f in ts) or "0"

    def formal(p):
        w, r, arr = p["word"], p["r"], p["mode"] == "arrange"
        uni = ARR(f"list('{w}')", r) if arr else SEL(f"list('{w}')", r)
        return F({"N": Q(_closed(w, r, arr), uni)},
                 model=["identical letters are indistinguishable",
                        "case split by the repetition pattern of the chosen letters"
                        + ("; each case times its multiset arrangements" if arr else "")])

    def stem(p):
        w, r = p["word"], p["r"]
        if p["mode"] == "select":
            return (f"<p>The number of different selections of {r} letters that can be made from the letters of "
                    f"the word <b>{w}</b> is:</p><p>(Identical letters are not distinguished.)</p>")
        return (f"<p>The number of different {r}-letter words (with or without meaning) that can be formed using "
                f"the letters of the word <b>{w}</b> (each letter used at most as many times as it occurs in "
                f"{w}) is:</p>")

    def mistakes(p):
        w, r, arr = p["word"], p["r"], p["mode"] == "arrange"
        d, n = len(set(w)), len(w)
        tagged = f"[(c, i) for i, c in enumerate('{w}')]"
        uni = (lambda items: ARR(items, r)) if arr else (lambda items: SEL(items, r))
        out = [
            Mistake("ALL_LETTERS_DISTINCT",
                    F({"N": Q(f"P({n}, {r})" if arr else f"C({n}, {r})", uni(tagged))},
                      model=["repeated letters treated as different"]),
                    f"Students use {'nPr' if arr else 'nCr'} with n = {n}, the total number of letters.",
                    "Identical letters produce identical selections/words; work with the distinct letters and "
                    "their multiplicities."),
            Mistake("ONLY_DISTINCT_CASE",
                    F({"N": Q(f"P({d}, {r})" if arr else f"C({d}, {r})", uni(f"sorted(set('{w}'))"))},
                      model=["only the all-different case"]),
                    f"Students count only choices of {r} different letters.",
                    "Repeated letters can be chosen more than once (up to their multiplicity)."),
            Mistake("MISSED_TRIPLE_CASES",
                    F({"N": Q(_closed(w, r, arr, skip_big=True),
                              uni(f"list('{w}')"), "max(count(x, c) for c in x) < 3")},
                      model=["cases with a letter used 3 or more times forgotten"]),
                    "Students list the 'all different' and 'pairs' cases and forget a letter can occur 3 times.",
                    "Letters occurring 3 or more times in the word give further cases."),
        ]
        if arr:
            out.append(Mistake("SELECTIONS_GIVEN",
                               F({"N": Q(_closed(w, r, False), SEL(f"list('{w}')", r))},
                                 model=["selections instead of words"]),
                               "Students stop after choosing the letters.",
                               "Each selection of letters can be arranged into several different words."))
            out.append(Mistake("REPEATS_NOT_DIVIDED_IN_ARRANGING",
                               F({"N": Q(f"fact({r})*({_closed(w, r, False)})", SEL(f"list('{w}')", r), None,
                                         {"sum": f"fact({r})"})}, model=["every selection arranged in r! ways"]),
                               f"Students multiply every selection by {r}!.",
                               "A selection with repeated letters has fewer than r! distinct arrangements."))
        else:
            out.append(Mistake("ARRANGED_INSTEAD",
                               F({"N": Q(_closed(w, r, True), ARR(f"list('{w}')", r))},
                                 model=["words counted instead of selections"]),
                               "Students arrange the chosen letters.", "A selection ignores order."))
        gap = sum(num * f for pat, _, num, f in _pattern_terms(w, r, arr) if max(pat) >= 3)
        if gap <= 2:                      # option would sit right next to the key: use only as a last resort
            out.append(out.pop(2))
        return out

    def explain(p, v):
        w, r, arr = p["word"], p["r"], p["mode"] == "arrange"
        cnt = Counter(w)
        mult = ", ".join(f"{c}×{m}" for c, m in sorted(cnt.items(), key=lambda t: -t[1]))
        rows = "".join(f"<li>pattern {'+'.join(map(str, pat))}: ${e.replace('*', ' \\cdot ')}$ = {num}"
                       + (f" selections × {f} arrangements = {num * f}" if arr else "") + "</li>"
                       for pat, e, num, f in _pattern_terms(w, r, arr))
        return (f"<p>{w}: {len(cnt)} distinct letters ({mult}). Split by how the {r} letters repeat:</p>"
                f"<ul>{rows}</ul><p>Total = <b>{v}</b>.</p>")

    return Family(id="pnc.letter_selection", subject=SUBJ, chapter=CH, topic="Selections and Words from Repeated Letters",
                  difficulty="HARD", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  modelled_on=["xe5ZfgVxYCdbpMKEGIuOF", "C8HGleU1NgkvV0IfgIjgy2xukfjjwd85"]).register()


LETTER_SELECTION = letter_selection()
