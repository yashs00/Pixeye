"""Blind batch b1: written from blind/b1/questions.md only (keys and explanations sealed).

Contamination note: luxwdj8i's explanation ending was seen earlier while testing the explanation-value extractor,
so it is scored but excluded from the accuracy figure.
"""
K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
C = lambda t, n="": {"truth": t, "basis": "curated", "note": n}  # noqa: E731

FORMALS = {
    # plane through L2 = pencil 4ax-y+5z-7a + lam(2x-5y-z-3) = 0 (the plane 2x-5y-z-3=0 itself does not contain
    # L1's point (4,-1,0): 8+5-3 != 0); it must contain L1: point (4,-1,0) and direction (1,-2,1).
    "1l6jdxtys": {"formal": {
        "kind": "equation_system", "knowns": {},
        "unknowns": {"a": U(), "lam": U(), "t": U(), "S": U()},
        "equations": ["4*a*4 - (-1) + 0 - 7*a + lam*(2*4 - 5*(-1) - 0 - 3) = 0",
                      "4*a*1 - (-2) + 5*1 + lam*(2*1 - 5*(-2) - 1) = 0",
                      "4*a*(3 + 7*t) - (2 - t) + 5*(3 - 4*t) - 7*a + lam*(2*(3 + 7*t) - 5*(2 - t) - (3 - 4*t) - 3) = 0",
                      "S = (3 + 7*t) + (2 - t) + (3 - 4*t)"],
        "target": "S",
        "model": ["plane containing both lines taken from the pencil of planes through the second line",
                  "P = (3+7t, 2-t, 3-4t) on the first line lies on that plane"]}},
    "1ldydj6mi": {"formal": {
        "kind": "equation_system", "knowns": {"r": K("symbolic", "m"), "I": K("symbolic", "A")},
        "unknowns": {"k": U("", "positive")},
        "equations": ["k * (r**2/(r**2 + r**2)**(3/2)) = 1/r"], "target": "k",
        "model": ["B_centre = mu0 I/(2r); B_axis(x) = mu0 I r^2/(2 (r^2+x^2)^(3/2)) at x = r; k = B_centre/B_axis"]},
        "option_values": {"A": "3*sqrt(2)/2", "B": "1/(3*sqrt(2))", "C": "2*sqrt(2)", "D": "1/sqrt(2)"}},
    "m9fnuunk": {"formal": {
        "kind": "statement_set", "format": "select_combination",
        "statements": {
            "A": {"formal": {"kind": "equation_system", "knowns": {"Ha": K("-69.01", "kJ/mol"),
                                                                   "Hb": K("-72.79", "kJ/mol")},
                             "unknowns": {"Hd": U("kJ/mol")}, "equations": ["Hd = Hb - Ha"], "target": "Hd",
                             "model": ["dilution 10 -> 40 H2O: (b) - (a) by Hess's law"]},
                  "claim": "== 3.78", "subject": "CHEMISTRY"},
            "B": C(False, "both enthalpies of solution are negative: dissolution here is exothermic"),
            "C": C(True, "(a) and (b) differ only in the amount of water and have different dH"),
            "D": C(False, "(a)/(b) are enthalpies of solution of HCl(g), not formation from elements")}},
        "option_values": {"A": "{1}", "B": "{2}", "C": "{3}", "D": "{4}"},
        "note": "single correct statement; option k encoded as {k}"},
    "lv0vxcns": {"formal": {
        "kind": "equation_system", "knowns": {},
        "unknowns": {"t": U(), "S": U(), "S2": U(), "D": U("", "positive")},
        "equations": ["t**2*(4**2 + 2**2 + 4**2) = 81",
                      "S = (1 + 4*t)**2 + (-2 - 2*t)**2 + (3 + 4*t)**2",
                      "S2 = (1 - 4*t)**2 + (-2 + 2*t)**2 + (3 - 4*t)**2",
                      "D = S - S2"],
        "target": "S",
        "model": ["point = P + t (Q - P) with |t (Q-P)| = 9; S2 is the other candidate (P - t(Q-P));",
                  "'farther from the origin' imposed as S - S2 > 0"]},
        "option_values": {"A": "150", "B": "155", "C": "160", "D": "165"}},
    "1l5c43tt2": {"formal": {
        "kind": "equation_system",
        "knowns": {"bA": K("5.6", "MeV"), "bBC": K("6.4", "MeV"), "A": K("220"), "B": K("105"), "Cn": K("115")},
        "unknowns": {"Q": U("MeV")}, "equations": ["Q = (B + Cn)*bBC - A*bA"], "target": "Q",
        "model": ["Q = total binding energy of products - of reactant"]},
        "option_values": {"A": "0.8", "B": "275", "C": "220", "D": "176"}},
    "lsbn4uhh": {"formal": {
        "kind": "equation_system", "knowns": {"n": K("1")}, "unknowns": {"N": U("", "natural")},
        "equations": ["N = 2**n"], "target": "N",
        "model": ["2-chlorobutane CH3-CHCl-CH2-CH3: exactly one stereocentre (C2), no meso form -> 2^n"]}},
    "1ldswo1xf": {"formal": {
        "kind": "series_sum", "unknowns": {"m": "natural"},
        "sequences": {"f": {"term": "n/5", "index": "n"}},
        "conditions": ["Sum(f(r)/(r*(r + 1)*(r + 2)), r, 1, m) = 1/12"],
        "target": "m",
        "model": ["Cauchy additivity on N with f(1) = 1/5 gives f(n) = n f(1) = n/5"]}},
    "JYidkRMzBiSkcHPhByjgy2xukf256blz": {"formal": {
        "kind": "equation_system",
        "knowns": {"r": K("0.015", "cm"), "h": K("15", "cm"), "rho": K("900", "kg/m^3"), "g": K("10", "m/s^2")},
        "unknowns": {"T": U("mN/m", "positive")},
        "equations": ["2*T = r*h*rho*g"], "target": "T",
        "model": ["capillary rise h = 2 T cos(theta)/(r rho g), theta = 0"]}},
    "jaoe38c1lscs7q96": {"formal": {
        "kind": "equation_system", "knowns": {"s": K("0.059", "V"), "pH": K("3"), "u": K("10**-2", "V")},
        "unknowns": {"E": U("V"), "x": U()},
        "equations": ["E = -s*pH", "E = x*u"], "target": "x",
        "model": ["H+ + e- -> 1/2 H2 at 1 bar: E = 0 - 0.059 pH (reduction potential)"]}},
    "luxwdj8i": {"formal": {
        "kind": "series_sum", "unknowns": {"al": "natural"},
        "sequences": {"u": {"term": "1/(2*n*(2*n - 1))", "index": "n"}},
        "conditions": ["Sum(1/(al + r), r, 1, 1012) - Sum(u(r), r, 1, 1012) = 1/2024"],
        "target": "al",
        "model": ["alpha assumed a natural number (the answer is an integer-type numerical)"]},
        "note": "CONTAMINATED: explanation seen earlier"},
    "lvc5868j": {"formal": {
        "kind": "equation_system", "knowns": {"r": K("8.48", "angstrom"), "a0": K("0.529", "angstrom")},
        "unknowns": {"x": U("", "positive")},
        "equations": ["x*a0 = r"], "target": "x",
        "model": ["Bohr: r_n = n^2 a0 and E_n = E/n^2, so x = n^2 = r/a0 (16.03 -> nearest integer)"]}},
    "lv40vb6r": {"formal": {
        "kind": "equation_system",
        "knowns": {"n1": K("1", "mol"), "n2": K("9", "mol"), "M1": K("46", "g/mol"), "M2": K("18", "g/mol")},
        "unknowns": {"w": U("", "positive")},
        "equations": ["w*(n1*M1 + n2*M2) = 100*n1*M1"], "target": "w",
        "model": ["mass percent of ethanol"]}},
}
SKIPPED: dict = {}
