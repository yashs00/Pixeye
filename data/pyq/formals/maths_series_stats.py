"""Formal states for the ascent maths chapters "Sequences And Series" (27) and "Statistics" (8).

Engine: cqse/math/series_stats.py (kinds "series_sum" / "statistics").  Every formal models the STEM only;
option values are transcribed from the option TEXT.  Conventions:
  * sequences: a(k) is the k-th term (first term a(1)); AP {"ap": [first, difference]}, GP {"gp": [first, ratio]}
  * Sum(body, r, lo, hi) is an ordinary finite / infinite sum; S_n is always written out as Sum(a(r), r, 1, n)
  * statistics: population variance (divide by n) - JEE convention, recorded by the engine
"""
from fractions import Fraction


def _rec_m6w9o8zv(n: int) -> str:
    """a_0 = 0, a_1 = 1/2, 2 a_{k+2} = 5 a_{k+1} - 3 a_k, iterated EXACTLY (no closed form) to turn the
    symbolic options 3a_100 +/- 100, 3a_99 +/- 100 into exact numbers."""
    a = [Fraction(0), Fraction(1, 2)]
    while len(a) <= n:
        a.append((5 * a[-1] - 3 * a[-2]) / 2)
    return f"{a[n].numerator}/{a[n].denominator}"


_A100, _A99 = _rec_m6w9o8zv(100), _rec_m6w9o8zv(99)

AP = lambda f, d: {"ap": [f, d]}  # noqa: E731
GP = lambda f, q: {"gp": [f, q]}  # noqa: E731
S = lambda n, lo="1", seq="a", v="r": f"Sum({seq}({v}), {v}, {lo}, {n})"  # noqa: E731

FORMALS = {
    # ------------------------------------------------------------------ Sequences And Series
    "m6srn27t": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": ["a(1) = 3", f"{S(4)} = {S(8, 5)}/5"],
                   "target": S(20), "model": ["A.P. a; S_4 = (1/5)(a_5 + ... + a_8)"]},
        "option_values": {"A": "-120", "B": "-1200", "C": "-1080", "D": "-1020"},
        "note": "'sum of the next four terms' = a_5 + a_6 + a_7 + a_8"},
    "m6qvaza3": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "positive", "q": "positive"},
                   "sequences": {"a": GP("A", "q")},
                   "conditions": ["a(1)*a(5) = 28", "a(2) + a(4) = 29"], "constraints": ["q > 1"],
                   "target": "a(6)", "model": ["increasing G.P. of positive terms: A > 0, q > 1"]},
        "option_values": {"A": "812", "B": "784", "C": "628", "D": "526"},
        "note": "increasing positive GP encoded as A > 0, ratio > 1"},
    "m6v42x9m": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": [f"{S(40)} = 1030", f"{S(12)} = 57"],
                   "target": f"{S(30)} - {S(10)}", "model": ["A.P."]},
        "option_values": {"A": "525", "B": "505", "C": "510", "D": "515"}},
    "m6ulvixl": {
        "formal": {"kind": "series_sum", "unknowns": {"p": "real"},
                   "sequences": {"s": {"term": "1/(n*(n+1))"}, "a": AP("-p", "p")},
                   "conditions": [f"{S(6)} = sqrt(2026*{S(2025, seq='s')})"],
                   "target": "Abs(a(20) - a(15))",
                   "model": ["1/2 + 1/6 + 1/12 + 1/20 + ... : n-th term 1/(n(n+1))", "A.P. first term -p, difference p"]},
        "option_values": {"A": "20", "B": "45", "C": "90", "D": "25"},
        "note": "explanation suspect (writes p = 3 then uses 5); key D believed correct"},
    "m6qi9jv4": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": ["a(1) + Sum(a(5*k), k, 1, 404) + a(2024) = 2233"],
                   "target": S(2024),
                   "model": ["a_5 + a_10 + ... + a_2020 = sum of a(5k), k = 1..404",
                             "A and d are not individually determined; the target must not depend on them"]},
        "explanation_value": "11132"},
    "m9dowfw9": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "n": "natural"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": [f"{S('n')} = 700", "a(6) = 7", f"{S(7)} = 7"],
                   "target": "a(n)", "model": ["A.P.; n is a number of terms (natural)"]},
        "option_values": {"A": "65", "B": "56", "C": "70", "D": "64"}},
    "m9fnusib": {
        "formal": {"kind": "series_sum", "sequences": {"s": {"term": "4*n/(4 + 3*n**2 + n**4)"}},
                   "target": f"Numer({S(20, seq='s')}) + Denom({S(20, seq='s')})",
                   "model": ["general term 4r/(4 + 3r^2 + r^4)", "m/n in lowest terms (sum is positive)"]},
        "option_values": {"A": "423", "B": "421", "C": "422", "D": "420"}},
    "m9dunoqg": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "n": "natural"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": ["Sum(a(2*k - 1), k, 1, 12) = -72*a(1)/5", f"{S('n')} = 0"],
                   "constraints": ["a(1) != 0"], "target": "n", "model": ["A.P.; n natural"]},
        "option_values": {"A": "18", "B": "17", "C": "11", "D": "10"}},
    "m6w9o103": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "m": "natural"},
                   "sequences": {"T": AP("A", "d")},
                   "conditions": ["T(m) = 1/25", "T(25) = 1/20", f"20*{S(25, seq='T')} = 13"],
                   "target": "5*m*Sum(T(r), r, m, 2*m)", "model": ["A.P. T; m a natural index"]},
        "option_values": {"A": "98", "B": "126", "C": "112", "D": "142"}},
    "m9gxgedv": {
        "formal": {"kind": "series_sum",
                   "sequences": {"s": {"term": "Sum(2*j - 1, j, 1, n)/factorial(n)"}},
                   "target": "Sum(s(r), r, 1, oo)",
                   "model": ["n-th term (1 + 3 + ... + (2n-1))/n!, first term 1 = 1/1!"]},
        "option_values": {"A": "3*E", "B": "2*E", "C": "4*E", "D": "6*E"}},
    "m9fnuqlo": {
        "formal": {"kind": "series_sum",
                   "sequences": {"s": {"fit": {"values": ["1", "3", "11", "25", "45", "71"], "degree": 2}}},
                   "target": S(20, seq="s"),
                   "model": ["the listed terms have constant second differences (2, 8, 14, 20, 26 -> 6); the "
                             "pattern is continued with constant second difference"]},
        "option_values": {"A": "7240", "B": "8124", "C": "7130", "D": "6982"},
        "note": "explanation suspect (its formula sign); key A believed correct"},
    "m9fnusx5": {
        "formal": {"kind": "series_sum",
                   "unknowns": {"A1": "real", "d": "positive", "B1": "real", "D": "real", "p": "real", "q": "real"},
                   "sequences": {"a": AP("A1", "d"), "b": AP("B1", "D")},
                   "conditions": ["a(1) + a(2) + a(3) = 36", "b(1) + b(2) + b(3) = 36",
                                  "p = a(1)*a(2)*a(3)", "q = b(1)*b(2)*b(3)", "D = d + 3",
                                  "5*(p + q) = 19*(p - q)"],
                   "constraints": ["p != q"], "target": "p - q",
                   "model": ["A = {a1, a2, a3}, B = {b1, b2, b3} three-term APs with differences d, D",
                             "(p+q)/(p-q) = 19/5 cross-multiplied with p != q"]},
        "option_values": {"A": "540", "B": "450", "C": "600", "D": "630"}},
    "m9ghxld2": {
        "formal": {"kind": "series_sum", "sequences": {"a": AP("1", "5"), "b": AP("9", "7")},
                   "target": "NUnion(a(r), b(r), r, 1, 2025)",
                   "model": ["A = first 2025 terms of 1, 6, 11, ...; B = first 2025 terms of 9, 16, 23, ..."]},
        "option_values": {"A": "3814", "B": "4003", "C": "4027", "D": "3761"}},
    "m9ghxljj": {
        "formal": {"kind": "series_sum",
                   "sequences": {"s": {"by_parity": {"odd": "(2*n - 1)**2", "even": "2*n - 1"}}},
                   "target": S(40, seq="s"),
                   "model": ["1, 3, 5^2, 7, 9^2, ...: n-th term is the n-th odd number, squared at odd positions "
                             "(1 = 1^2)"]},
        "option_values": {"A": "40870", "B": "41880", "C": "43890", "D": "33980"}},
    "m9dqr6zu": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "positive", "q": "positive"},
                   "sequences": {"a": GP("A", "q")},
                   "conditions": ["a(2) + a(4) + a(6) = 21", "a(8) + a(10) + a(12) = 15309"],
                   "target": S(9), "model": ["G.P. of positive terms: A > 0, q > 0"]},
        "option_values": {"A": "757", "B": "755", "C": "750", "D": "760"}},
    "m9d9bl5d": {
        "formal": {"kind": "series_sum", "unknowns": {"alpha": "real", "beta": "real"},
                   "conditions": ["alpha = Sum(1/(2*k - 1)**4, k, 1, oo)", "beta = Sum(1/(2*k)**4, k, 1, oo)"],
                   "target": "alpha/beta",
                   "model": ["alpha = sum over odd n of 1/n^4, beta = sum over even n of 1/n^4",
                             "the given value pi^4/90 of the full sum is not needed (closed forms are exact)"]},
        "option_values": {"A": "23", "B": "14", "C": "18", "D": "15"}},
    "m9e5j78z": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "q": "real"},
                   "sequences": {"x": GP("A", "q")},
                   "conditions": ["2*(x(2) - 7) = (x(1) - 2) + (x(3) - 9)",
                                  "2*(x(3) - 9) = (x(2) - 7) + (x(4) - 5)"],
                   "target": "x(1)*x(2)*x(3)*x(4)/24",
                   "model": ["x1..x4 in G.P.; x1-2, x2-7, x3-9, x4-5 in A.P. (middle term = mean of neighbours)"]},
        "option_values": {"A": "18", "B": "216", "C": "36", "D": "72"}},
    "m6v437u1": {
        "formal": {"kind": "series_sum", "unknowns": {"alpha": "real"},
                   "conditions": ["7 = Sum((5 + k*alpha)/7**k, k, 0, oo)"], "target": "alpha",
                   "model": ["k-th term (k >= 0) is (5 + k alpha)/7^k"]},
        "option_values": {"A": "1/7", "B": "1", "C": "6/7", "D": "6"}},
    "m6t9xszy": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "p": "real", "q": "real"},
                   "sequences": {"a": AP("A", "3/2")},
                   "conditions": [f"{S(11)} = 88", "p/3 = a(10) + a(11)", "q/3 = a(10)*a(11)"],
                   "target": "q - 2*p",
                   "model": ["roots of 3x^2 - px + q are a_10, a_11: Vieta sum p/3, product q/3"]},
        "explanation_value": "474"},
    "m9e5j28m": {
        "formal": {"kind": "series_sum", "sequences": {"s": {"term": "4*n/(1 + 4*n**4)"}},
                   "target": f"Numer({S(10, seq='s')}) + Denom({S(10, seq='s')})",
                   "model": ["general term 4r/(1 + 4r^4)", "m/n in lowest terms"]},
        "explanation_value": "441"},
    "m9e5j1on": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "n": "natural"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": ["Sum(a(2*k - 1), k, 1, n) = 24", "Sum(a(2*k), k, 1, n) = 30",
                                  "a(2*n) - a(1) = 21/2"],
                   "target": "CountInt(a(r), r, 1, 2*n)",
                   "model": ["2n terms; odd-positioned terms a_1, a_3, ..., even-positioned a_2, a_4, ...",
                             "'odd terms' read as odd-POSITIONED terms (standard reading)"]},
        "option_values": {"A": "6", "B": "4", "C": "8", "D": "10"},
        "note": "explanation suspect (writes a+(2n+1)d for the last term); key B believed correct"},
    "m6w9o8zv": {
        "formal": {"kind": "series_sum",
                   "sequences": {"a": {"recurrence": "2*a(n+2) = 5*a(n+1) - 3*a(n)",
                                       "initial": {"0": "0", "1": "1/2"}}},
                   "target": S(100), "model": ["a_0 = 0, a_1 = 1/2, 2a_{n+2} = 5a_{n+1} - 3a_n"]},
        "option_values": {"A": f"3*({_A100}) + 100", "B": f"3*({_A100}) - 100",
                          "C": f"3*({_A99}) - 100", "D": f"3*({_A99}) + 100"},
        "note": "options are symbolic in a_100 / a_99; encoded as exact numbers with a_100, a_99 obtained by "
                "exact Fraction iteration of the recurrence (independent of the engine's rsolve closed form)"},
    "m6rp5uwi": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "d": "real", "k": "natural"},
                   "sequences": {"a": AP("A", "d")}, "dummies": ["j", "r"],
                   "conditions": ["Sum(a(2*j - 1), j, 1, k) = 40", "Sum(a(2*j), j, 1, k) = 55",
                                  "a(2*k) - a(1) = 27"],
                   "target": "k", "model": ["2k terms; odd-/even-positioned terms"]},
        "option_values": {"A": "8", "B": "6", "C": "4", "D": "5"}},
    "m6qgq07h": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "natural", "d": "integer"},
                   "sequences": {"a": AP("A", "d")},
                   "conditions": [f"{S(3)} = 54"],
                   "constraints": [f"{S(20)} > 1600", f"{S(20)} < 1800", "d >= 0"],
                   "target": "a(11)",
                   "model": ["A.P. of positive integers: first term natural, difference an integer, d >= 0 "
                             "(an infinite AP with d < 0 eventually has negative terms)",
                             "'lies between' read as strict 1600 < S_20 < 1800"]},
        "option_values": {"A": "108", "B": "90", "C": "122", "D": "84"}},
    "m6rirljj": {
        "formal": {"kind": "series_sum", "sequences": {"a": {"term": "(n**2 + 5*n + 6)/4"}},
                   "target": "507*Sum(1/a(k), k, 1, 2025)", "model": ["4a_n = n^2 + 5n + 6"]},
        "option_values": {"A": "540", "B": "675", "C": "1350", "D": "135"}},
    "m6rj2ysd": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "real", "n": "natural"},
                   "sequences": {"a": AP("A", "6")},
                   "conditions": ["a(n) = 219", f"{S('n')} = 180*(n - 2)"],
                   "constraints": ["n >= 3", "a(1) > 0"],
                   "target": "n",
                   "model": ["interior angles (degrees) in increasing A.P. with difference 6, largest a_n = 219",
                             "angle sum of an n-gon = (n-2)180; polygon has n >= 3 and positive angles"]},
        "explanation_value": "20"},
    "m9fnuqki": {
        "formal": {"kind": "series_sum", "unknowns": {"A": "positive", "q": "positive"},
                   "sequences": {"a": GP("A", "q")},
                   "conditions": ["a(3)*a(5) = 729", "a(2) + a(4) = 111/4"], "constraints": ["q > 1"],
                   "target": "24*(a(1) + a(2) + a(3))",
                   "model": ["increasing G.P. of positive numbers: A > 0, q > 1"]},
        "option_values": {"A": "128", "B": "129", "C": "131", "D": "130"}},
    # ------------------------------------------------------------------ Statistics
    "m6qhsfy4": {
        "formal": {"kind": "statistics", "unknowns": {"S1": "real", "S2": "real", "beta": "real"},
                   "datasets": {"x": {"aggregate": {"n": "10", "sum": "S1", "sumsq": "S2"}},
                                "y": {"transform": {"of": "x", "map": "2*(t - 1) + 4*beta"}}},
                   "conditions": ["sumf(x, t - 2) = 30", "sumf(x, (t - beta)**2) = 98", "var(x) = 4/5"],
                   "constraints": ["beta > 2"],
                   "target": "beta*mean(y)/var(y)",
                   "model": ["ten observations known only through their sums", "y_i = 2(x_i - 1) + 4 beta"]},
        "option_values": {"A": "100", "B": "90", "C": "120", "D": "110"}},
    "m6srn6ee": {
        "formal": {"kind": "statistics", "unknowns": {"N": "natural"},
                   "datasets": {"g": {"grouped_median_class": {"lower": "12", "width": "6", "freq": "12",
                                                               "cf_before": "18", "total": "N"}}},
                   "conditions": ["median(g) = 14"], "target": "nobs(g)",
                   "model": ["grouped median l + (N/2 - cf) h / f with median class 12-18, f = 12, cf = 18"]},
        "option_values": {"A": "52", "B": "44", "C": "40", "D": "48"}},
    "m6t9xt0i": {
        "formal": {"kind": "statistics", "datasets": {"x": {"ap": {"first": "8", "diff": "13", "last": "320"}}},
                   "target": "var(x)", "model": ["8, 21, 34, ..., 320 (difference 13, 25 numbers)"]},
        "explanation_value": "8788"},
    "m9gxgcpa": {
        "formal": {"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
                   "datasets": {"x": {"values": ["1", "3", "a", "7", "b"]},
                                "y": {"transform": {"of": "x", "map": "t + i"}}},
                   "conditions": ["mean(x) = 5", "var(x) = 10"], "constraints": ["a > b"],
                   "target": "var(y)", "model": ["y_n = n + x_n"]},
        "option_values": {"A": "17", "B": "16", "C": "16.4", "D": "17.4"}},
    "m9e5j642": {
        "formal": {"kind": "statistics", "unknowns": {"S1": "real", "S2": "real"},
                   "datasets": {"w": {"aggregate": {"n": "100", "sum": "S1", "sumsq": "S2"}},
                                "c": {"replace": {"of": "w", "remove": ["50"], "add": ["40"]}}},
                   "conditions": ["mean(w) = 40", "sd(w) = 5.1"],
                   "target": "10*(mean(c) + sd(c))",
                   "model": ["w = the recorded (wrong) data; c = corrected data with 50 replaced by 40"]},
        "option_values": {"A": "447", "B": "445", "C": "449", "D": "451"}},
    "m9e5j0pj": {
        "formal": {"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
                   "datasets": {"x": {"values": ["6", "4", "a", "8", "b", "12", "10", "13"]}},
                   "conditions": ["mean(x) = 9", "var(x) = 9.25"], "target": "a + b + a*b"},
        "option_values": {"A": "103", "B": "106", "C": "100", "D": "105"}},
    "m6ulvphu": {
        "formal": {"kind": "statistics", "unknowns": {"S1": "real", "S2": "real"},
                   "datasets": {"w": {"aggregate": {"n": "10", "sum": "S1", "sumsq": "S2"}},
                                "c": {"replace": {"of": "w", "remove": ["4", "5"], "add": ["6", "8"]}}},
                   "conditions": ["mean(w) = 5.5", "sumf(w, t**2) = 371"], "target": "var(c)",
                   "model": ["w = data as noted (with 4 and 5); c = corrected data (6 and 8)"]},
        "option_values": {"A": "5", "B": "7", "C": "9", "D": "4"}},
    "m9fnusdf": {
        "formal": {"kind": "statistics", "unknowns": {"a": "real", "b": "real"},
                   "datasets": {"x": {"values": ["2", "3", "3", "4", "5", "7", "a", "b"]}},
                   "conditions": ["mean(x) = 4", "sd(x) = sqrt(2)"], "target": "md(x, mode(x))"},
        "option_values": {"A": "1/2", "B": "3/4", "C": "1", "D": "2"}},
}
