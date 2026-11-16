"""Blind chapter batch redox: written from blind/redox/questions.md only (keys and explanations sealed).

Conventions
  * "Which reaction/species ..." MCQs are computed per option with statement_set/select_combination: statement k is
    the claim made by option k, so option k has value "{k}" and exactly one option should come out true.
  * Tuple answers (x, y, z coefficients) use the redox engine's "code" return: sum c_i * 1000**(k-1-i).
  * Equations are transcribed from the stem; any correction of an obvious typo is stated in the note.
  * Descriptive facts the engine cannot compute are curated (statement.truth, teacher confirms); product identities
    a stem implies but does not state are premises (chem.reaction_feasibility, teacher confirms).
"""
K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="positive": {"unit": u, "domain": d}  # noqa: E731
C = lambda t, n="": {"truth": t, "basis": "curated", "note": n}  # noqa: E731
RX = lambda q, **k: {"kind": "redox", "query": q, **k}  # noqa: E731
Q = lambda q, **k: {"query": q, **k}  # noqa: E731  (redox sub-query)
SUB = lambda f, claim: {"formal": f, "claim": claim, "subject": "CHEMISTRY"}  # noqa: E731
OPT4 = {"A": "{1}", "B": "{2}", "C": "{3}", "D": "{4}"}
P = lambda s, n="": {"statement": s, "basis": "curated", "note": n}  # noqa: E731


def per_option(fn, items: dict) -> dict:
    """statement_set: option label -> computed truth fn(item)."""
    return {"kind": "statement_set", "format": "select_combination",
            "statements": {lab: fn(x) for lab, x in items.items()}}


def code(*c):
    return str(sum(v * 1000 ** (len(c) - 1 - i) for i, v in enumerate(c)))


def nf(eq, species, medium=None):
    return Q("n_factor", equation=eq, species=species, medium=medium)


def os_(species, el):
    return Q("oxidation_state", species=species, element=el)


def is_redox(eq):
    return SUB(RX("is_redox", equation=eq), "== 1")


def is_disp(eq):
    return SUB(RX("is_disproportionation", equation=eq), "== 1")


def all_os(triples):
    """statement: every (species, element, value) holds."""
    return SUB(RX("all", checks=[{**os_(s, e), "claim": f"== {v}"} for s, e, v in triples]), "== 1")


def all_types(pairs):
    return SUB(RX("all", checks=[{**Q("reaction_type", equation=eq), "claim": f"== {t}"} for eq, t in pairs]),
               "== 1")


FORMALS = {
    # ---------------------------------------------------------------- 1-22
    "bUz5bDaiqt75drYS": {"formal": per_option(is_redox, {
        "A": "NaCl + KNO3 -> NaNO3 + KCl", "B": "CaC2O4 + 2HCl -> CaCl2 + H2C2O4",
        "C": "Mg(OH)2 + 2NH4Cl -> MgCl2 + 2NH4OH", "D": "Zn + 2AgCN -> 2Ag + Zn(CN)2"}),
        "option_values": OPT4, "note": "option k true iff its reaction shows an ON change"},
    "vmryv46T98UL1Lk5": {"formal": per_option(lambda e: SUB(RX("role", equation=e, species="H2SO4"),
                                                            "== oxidant"), {
        "A": "NaCl + H2SO4 -> NaHSO4 + HCl", "B": "2PCl5 + H2SO4 -> 2POCl3 + 2HCl + SO2Cl2",
        "C": "2HI + H2SO4 -> I2 + SO2 + 2H2O", "D": "Ca(OH)2 + H2SO4 -> CaSO4 + 2H2O"}),
        "option_values": OPT4, "note": "oxidising behaviour = H2SO4 itself is reduced (S ON decreases)"},
    "Ee9Rx5oIInUG5CDx": {"formal": RX("balance", equation="MnO4^- + C2O4^2- + H^+ -> Mn^2+ + CO2 + H2O",
                                      **{"return": "code", "species": ["MnO4^-", "C2O4^2-", "H^+"]}),
                         "option_values": {"A": code(5, 2, 16), "B": code(2, 5, 8), "C": code(2, 5, 16),
                                           "D": code(5, 2, 8)},
                         "note": "(x, y, z) = coefficients of MnO4-, C2O4^2-, H+; stem's 2y CO2 and z/2 H2O are "
                                 "consistent with the smallest-integer balance (10 CO2, 8 H2O)"},
    "6gt8nqdfhZsoiXTH": {"formal": per_option(lambda e: SUB(RX("role", equation=e, species="H2O2"), "== reductant"), {
        "1": "H2O2 + 2H^+ + 2e^- -> 2H2O", "2": "H2O2 -> O2 + 2H^+ + 2e^-",
        "3": "H2O2 + 2e^- -> 2OH^-", "4": "H2O2 + 2OH^- -> O2 + 2H2O + 2e^-"}),
        "option_values": {"A": "{1, 2}", "B": "{3, 4}", "C": "{1, 3}", "D": "{2, 4}"},
        "note": "'X - 2e-' in the stem (electrons lost) written as electrons on the product side"},
    "xhb2zKJH6wZKhIy422O3J": {"formal": {
        "kind": "equation_system", "knowns": {"N": K("0.1", "mol/L"), "nOH": K("0.04", "mol")},
        "unknowns": {"V": U("mL")}, "equations": ["N*V = nOH"], "target": "V",
        "model": ["equivalents of acid = equivalents of OH- furnished by the base (0.04 eq)",
                  "normality 0.1 N = 0.1 eq/L; basicity of the acid is already inside the normality"]},
        "option_values": {"A": "200", "B": "400", "C": "600", "D": "800"}},
    "AZIQSjpVsC1nOZTE": {"formal": per_option(is_redox, {
        "A": "XeF6 + H2O -> XeOF4 + 2HF", "B": "XeF6 + 2H2O -> XeO2F2 + 4HF",
        "C": "XeF4 + O2F2 -> XeF6 + O2", "D": "XeF2 + PF5 -> XeF^+ + PF6^-"}),
        "option_values": OPT4, "note": "D's product [XeF]+[PF6]- written as its two ions"},
    "dJsK1dnG9eeuqU6h6B1v3": {"formal": RX("n_factor", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2",
                                           species="CO2", medium="acidic"),
                              "option_values": {"A": "10", "B": "2", "C": "1", "D": "5"},
                              "note": "electrons per CO2 molecule formed (C +3 -> +4)"},
    "Nc3KC2d3VAtJyLmgZhERW": {"formal": {
        "kind": "equation_system",
        "knowns": {"Mo": K("0.5", "mol/L"), "Vo": K("50", "mL"), "b": K("2"), "Vb": K("25", "mL"),
                   "V2": K("50", "mL"), "MM": K("40", "g/mol")},
        "unknowns": {"Mb": U("mol/L"), "m": U("g")},
        "equations": ["b*Mo*Vo = Mb*Vb", "m = Mb*V2*MM"], "target": "m",
        "model": ["oxalic acid is dibasic (n = 2) in neutralisation", "NaOH 40 g/mol (23 + 16 + 1)"]},
        "option_values": {"A": "20", "B": "4", "C": "80", "D": "10"}},
    "NEBjQdkhzIAtJZVzgZxw9": {"formal": {
        "kind": "equation_system",
        "knowns": {"c": K("10**-3", "mol/L"), "MC": K("100", "g/mol"), "rho": K("1", "kg/L")},
        "unknowns": {"w": U(), "H": U()}, "equations": ["w = c*MC/rho", "H = w*10**6"], "target": "H",
        "model": ["1 mol CaSO4 = 1 mol CaCO3 equivalent (both supply one Ca2+)", "CaCO3 = 100 g/mol",
                  "ppm by mass, dilute solution of density 1 kg/L"]},
        "option_values": {"A": "90", "B": "100", "C": "50", "D": "10"}},
    "KAjBwzLqopJziWrx0DCek": {"formal": RX(
        "equivalence",
        n_factors={"n1": nf("FeC2O4 -> Fe^3+ + CO2", "FeC2O4", "acidic"),
                   "n2": nf("Fe2(C2O4)3 -> Fe^3+ + CO2", "Fe2(C2O4)3", "acidic"),
                   "n3": nf("FeSO4 -> Fe^3+ + SO4^2-", "FeSO4", "acidic"),
                   "n4": nf("Fe2(SO4)3 -> Fe^3+ + SO4^2-", "Fe2(SO4)3", "acidic"),
                   "nK": nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic")},
        system={"knowns": {"m": K("1", "mol")}, "unknowns": {"x": U("mol")},
                "equations": ["x*nK = m*(n1 + n2 + n3 + n4)"], "target": "x",
                "model": ["equivalents of KMnO4 = total equivalents of the reductants (1 mol each)",
                          "Fe(II) -> Fe(III), oxalate -> CO2, MnO4- -> Mn2+ in acid"]},
        premises=[P("acidic KMnO4 is reduced to Mn2+; oxalate to CO2; Fe2+ to Fe3+", "NCERT XI 8 / XII 8")]),
        "option_values": {"A": "1.5", "B": "3", "C": "2", "D": "1"}},
    "ILZMXBbS6Wf9jXCoyj6rP": {"formal": {
        "kind": "statement_set", "format": "ordering",
        "order": {"items": ["NO", "N2O", "NO2", "N2O3"], "direction": "increasing",
                  "values": {s: {"formal": RX("oxidation_state", species=s, element="N")}
                             for s in ["NO", "N2O", "NO2", "N2O3"]},
                  "basis": "rule: oxidation numbers from the redox engine"}},
        "option_values": {"A": "3142", "B": "3412", "C": "2143", "D": "2413"},
        "note": "ordering code = positions in items [NO, N2O, NO2, N2O3], increasing ON"},
    "BsaVZ1wbbWcIJLZwfg3rsa0w2w9jx56tijx": {"formal": per_option(is_disp, {
        "A": "2NaBr + Cl2 -> 2NaCl + Br2", "B": "2KMnO4 -> K2MnO4 + MnO2 + O2", "C": "2CuBr -> CuBr2 + Cu",
        "D": "2MnO4^- + 10I^- + 16H^+ -> 2Mn^2+ + 5I2 + 8H2O"}),
        "option_values": OPT4,
        "note": "typos corrected: B printed '2KMnO4 -> 2KMnO4 + ...' read as K2MnO4 (as printed it is "
                "unbalanceable; in neither reading is one element both oxidised and reduced); D charges "
                "restored (MnO4^-, Mn^2+)"},
    "sUGLsiqlV2h6S2Ps2z7k9k2k5dyph0k": {"formal": per_option(all_os, {
        "A": [("K2O", "K", "1"), ("K2O2", "K", "2"), ("KO2", "K", "4")],
        "B": [("K2O", "K", "1"), ("K2O2", "K", "1"), ("KO2", "K", "1")],
        "C": [("K2O", "K", "2"), ("K2O2", "K", "1"), ("KO2", "K", "1/2")],
        "D": [("K2O", "K", "1"), ("K2O2", "K", "4"), ("KO2", "K", "2")]}),
        "option_values": OPT4, "note": "K2O2 peroxide and KO2 superoxide from the structure table"},
    "uOActAkQoaumecjQJo7k9k2k5epwqeu": {"formal": per_option(is_redox, {
        "A": "H2SO4 + 2NaOH -> Na2SO4 + 2H2O", "B": "3O2 -> 2O3", "C": "N2 + O2 -> 2NO",
        "D": "[Co(H2O)6]Cl3 + 3AgNO3 -> [Co(H2O)6](NO3)3 + 3AgCl"}),
        "option_values": OPT4,
        "note": "verbal options written as their standard equations (neutralisation, ozone formation, N2 + O2 "
                "at 2000 K, precipitation of the ionisable chloride)"},
    "vlhjHX6yKGZg6V7YU07k9k2k5idmyit": {"formal": per_option(
        lambda se: SUB(RX("capability", species=se[0], element=se[1]), "!= both"),
        {"A": ("H3PO4", "P"), "B": ("H2SO3", "S"), "C": ("H2O2", "O"), "D": ("HNO2", "N")}),
        "option_values": OPT4,
        "note": "redox behaviour judged at the central element (P, S, peroxide O, N): it can act both ways only "
                "from an intermediate oxidation state"},
    "fJgmdZRvqRLiiFd7mUjgy2xukevksjwi": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": C(False, "pipette (to deliver the HCl aliquot) and distilled water (rinsing) are required"),
            "B": C(False, "clamp (burette stand) and phenolphthalein (indicator) are required"),
            "C": C(False, "burette and white porcelain tile are required"),
            "D": C(True, "no heating is needed in an HCl-NaOH titration: Bunsen burner (and a measuring cylinder) "
                         "are not required")}},
        "option_values": OPT4, "note": "descriptive (laboratory practice) - curated"},
    "uNrZvCorxnp4BUjUHOjgy2xukeyh0ywx": {"formal": RX(
        "expr", terms={"x": os_("K2Cr2O7", "Cr"), "y": os_("KMnO4", "Mn"), "z": os_("K2FeO4", "Fe")},
        expr="x + y + z")},
    "DD98dZed5YgA5ZUouyjgy2xukfchmxk0": {"formal": {
        "kind": "equation_system",
        "knowns": {"N": K("0.1", "mol/L"), "V": K("100", "mL"), "m": K("1.43", "g"), "n": K("2"),
                   "MNa": K("23", "g/mol"), "MC": K("12", "g/mol"), "MO": K("16", "g/mol"), "MH": K("1", "g/mol")},
        "unknowns": {"Mm": U("g/mol"), "x": U()},
        "equations": ["N*V = n*m/Mm", "Mm = 2*MNa + MC + 3*MO + x*(2*MH + MO)"], "target": "x",
        "model": ["n-factor of Na2CO3 = 2 (complete neutralisation, CO3^2- + 2H+)",
                  "C 12, O 16, H 1 g/mol (standard); Na 23 stated"]}},
    "slYLNkJOzOyAXojifajgy2xukfq9pezo": {"formal": RX(
        "equivalence",
        n_factors={"nD": nf("Cr2O7^2- -> Cr^3+", "Cr2O7^2-", "acidic"),
                   "nF": nf("FeC2O4 -> Fe^3+ + CO2", "FeC2O4", "acidic")},
        system={"knowns": {"M": K("0.02", "mol/L"), "m": K("0.288", "g"), "MM": K("144", "g/mol")},
                "unknowns": {"V": U("mL")}, "equations": ["M*V*nD = nF*m/MM"], "target": "V",
                "model": ["FeC2O4 = 56 + 2*12 + 4*16 = 144 g/mol (Fe 56 stated)",
                          "equivalents of dichromate = equivalents of ferrous oxalate"]},
        premises=[P("acid dichromate -> Cr3+; ferrous oxalate -> Fe3+ + CO2", "NCERT XII 8")])},
    "jR6G1U3lIXmR5hprc61klsc56n9": {"formal": {
        "kind": "equation_system",
        "knowns": {"N": K("0.1", "mol/L"), "V1": K("17.5", "mL"), "V2": K("1.5", "mL"), "m": K("0.4", "g"),
                   "M2": K("106", "g/mol")},
        "unknowns": {"a": U("mol"), "b": U("mol"), "w": U()},
        "equations": ["N*V1 = a + b", "N*V2 = b", "w = 100*b*M2/m"], "target": "w",
        "model": ["phenolphthalein end point: NaOH + Na2CO3 -> NaHCO3 (one H+ each)",
                  "methyl orange end point: NaHCO3 -> CO2 (one H+ per original carbonate)",
                  "Na2CO3 = 106 g/mol; answer rounded to nearest integer (3.975 -> 4)"]}},
    "9KUPMuqvsxidkPpuBO1klue8sl2": {"formal": RX(
        "oxidation_state", species="CrO4^2-", element="Cr",
        premises=[P("Cr2O7^2- + 2OH^- -> 2CrO4^2- + H2O: the product in base is chromate", "NCERT XII 8.6")])},
    "91lPBnmet4BGfbFKjY1kmiunroc": {"formal": {
        "kind": "statement_set", "format": "statement_pair", "statements": {
            "I": SUB(RX("capability", species="NaH", element="H"), "!= reductant_only"),
            "II": C(True, "the sp2 lone pair on pyridine N is not part of the aromatic sextet and accepts H+")}},
        "option_values": {"A": "1", "B": "11", "C": "10", "D": "0"},
        "note": "I: NaH acts through hydride H(-1), already the lowest ON of H -> cannot be reduced -> not an "
                "oxidising agent"},
    # ---------------------------------------------------------------- 23-44
    "9qj8Tm9aeBraxksqGm1kmm1cgbf": {"formal": {
        "kind": "statement_set", "format": "ordering",
        "order": {"items": ["NO", "NO2", "N2O", "NO3^-"], "direction": "decreasing",
                  "values": {s: {"formal": RX("oxidation_state", species=s, element="N")}
                             for s in ["NO", "NO2", "N2O", "NO3^-"]},
                  "basis": "rule: oxidation numbers from the redox engine"}},
        "option_values": {"A": "3214", "B": "1234", "C": "2413", "D": "4213"},
        "note": "ordering code = positions in items [NO, NO2, N2O, NO3-], decreasing ON"},
    "1krxb954p": {"formal": per_option(
        lambda t: SUB(RX("on_change", **{"from": t[0], "to": t[1], "element": t[2]}), "== 5"),
        {"A": ("Cr2O7^2-", "Cr^3+", "Cr"), "B": ("MnO4^-", "Mn^2+", "Mn"), "C": ("CrO4^2-", "Cr^3+", "Cr"),
         "D": ("C2O4^2-", "CO2", "C")}),
        "option_values": OPT4,
        "note": "change in oxidation state of the element per atom (A 3, B 5, C 3, D 1); per formula unit A would "
                "be 6 and D 2 - still only B equals five"},
    "1krz034xm": {"formal": per_option(all_os, {
        "A": [("H4P2O7", "P", "7"), ("H4P2O5", "P", "5"), ("H4P2O6", "P", "6")],
        "B": [("H4P2O7", "P", "5"), ("H4P2O5", "P", "4"), ("H4P2O6", "P", "3")],
        "C": [("H4P2O7", "P", "5"), ("H4P2O5", "P", "3"), ("H4P2O6", "P", "4")],
        "D": [("H4P2O7", "P", "6"), ("H4P2O5", "P", "4"), ("H4P2O6", "P", "5")]}),
        "option_values": OPT4},
    "1ks1jhofn": {"formal": RX(
        "equivalence",
        n_factors={"nK": nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic"), "nO": nf("H2C2O4 -> CO2", "H2C2O4", "acidic")},
        system={"knowns": {"Mk": K("0.05", "mol/L"), "Vk": K("10.0", "mL"), "Vo": K("10.0", "mL"),
                           "MM": K("126", "g/mol"), "u": K("10**-2", "g/L")},
                "unknowns": {"Mo": U("mol/L"), "S": U("g/L"), "y": U()},
                "equations": ["Mk*nK*Vk = Mo*nO*Vo", "S = Mo*MM", "S = y*u"], "target": "y",
                "model": ["H2C2O4.2H2O = 126 g/mol (2 + 24 + 64 + 36)", "strength = molarity x molar mass",
                          "answer in units of 10^-2 g/L"]},
        premises=[P("acidic KMnO4 -> Mn2+, oxalic acid -> CO2", "NCERT XI 8 / XII 8")]),
        "note": "15.75 g/L = 1575 x 10^-2 g/L"},
    "1l55oahmw": {"formal": RX(
        "equivalence",
        n_factors={"nK": nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic"),
                   "nF": nf("FeSO4.(NH4)2SO4.6H2O -> Fe^3+ + SO4^2- + NH4^+", "FeSO4.(NH4)2SO4.6H2O", "acidic")},
        system={"knowns": {"Mk": K("0.01", "mol/L"), "Mf": K("0.05", "mol/L"), "Vf": K("20.0", "mL"),
                           "Vb": K("50", "mL")},
                "unknowns": {"V": U("mL"), "L": U("mL")},
                "equations": ["Mk*nK*V = Mf*nF*Vf", "L = Vb - V"], "target": "L",
                "model": ["Mohr's salt FeSO4.(NH4)2SO4.6H2O: only Fe2+ is oxidised", "burette starts at 0 of 50 mL"]},
        premises=[P("acidic KMnO4 -> Mn2+; Fe2+ -> Fe3+", "NCERT XII 8")])},
    "1l58jinm1": {"formal": per_option(is_disp, {
        "A": "3MnO4^2- + 4H^+ -> 2MnO4^- + MnO2 + 2H2O", "B": "MnO4^- + 4H^+ + 4e^- -> MnO2 + 2H2O",
        "C": "10I^- + 2MnO4^- + 16H^+ -> 2Mn^2+ + 8H2O + 5I2",
        "D": "8MnO4^- + 3S2O3^2- + H2O -> 8MnO2 + 6SO4^2- + 2OH^-"}),
        "option_values": OPT4,
        "note": "B as printed (4e-) is not charge balanced; the engine re-balances the skeleton (3e-) and finds "
                "a single reduction - not a disproportionation either way"},
    "1l59rrtym": {"formal": {
        "kind": "equation_system",
        "knowns": {"Va": K("10", "mL"), "Ma": K("0.1", "mol/L"), "Vb": K("30", "mL"), "Mb": K("0.05", "mol/L"),
                   "nb": K("2")},
        "unknowns": {"b": U()}, "equations": ["Va*Ma*b = Vb*Mb*nb"], "target": "b",
        "model": ["equivalents of acid = equivalents of base", "M(OH)2 is diacidic (2 OH- per formula)"]}},
    "1l6gqai21": {"formal": per_option(lambda e: SUB(RX("is_disproportionation", equation=e), "== 0"), {
        "A": "2H2O2 -> 2H2O + O2", "B": "2NO2 + H2O -> HNO3 + HNO2", "C": "MnO4^- + 4H^+ + 3e^- -> MnO2 + 2H2O",
        "D": "3MnO4^2- + 4H^+ -> 2MnO4^- + MnO2 + 2H2O"}),
        "option_values": OPT4, "note": "statement k: option k is NOT a disproportionation"},
    "1l6i5tubb": {"formal": {
        "kind": "statement_set", "format": "assertion_reason", "statements": {
            "A": C(True, "phenolphthalein is colourless in acid and pink in base (pH range ~8.3-10)"),
            "R": C(False, "phenolphthalein is a weak acid that DOES ionise in basic medium; the coloured "
                          "species is its anion")}},
        "option_values": {"A": "3", "B": "2", "C": "1", "D": "4"}, "note": "descriptive - curated"},
    "1l6i6eqso": {"formal": RX(
        "equivalence",
        n_factors={"nC": nf("2Cu^2+ + 4I^- -> Cu2I2 + I2", "Cu^2+"),
                   "nH": nf("I2 + 2S2O3^2- -> 2I^- + S4O6^2-", "S2O3^2-")},
        system={"knowns": {"Mh": K("0.02", "mol/L"), "Vh": K("20", "mL"), "Vc": K("10", "mL"),
                           "u": K("10**-2", "mol/L")},
                "unknowns": {"Mc": U("mol/L"), "y": U()},
                "equations": ["Mc*nC*Vc = Mh*nH*Vh", "Mc = y*u"], "target": "y",
                "model": ["iodine liberated by Cu2+ is titrated by hypo: equivalents of Cu2+ = equivalents of "
                          "thiosulphate", "answer in units of 10^-2 M"]})},
    "1l6ku767y": {"formal": {
        "kind": "equation_system",
        "knowns": {"Ma": K("0.1", "mol/L"), "Va": K("100", "mL"), "Mb": K("0.1", "mol/L"), "Vb": K("50", "mL"),
                   "na": K("2"), "u": K("10**-1", "mol/L")},
        "unknowns": {"N": U("mol/L"), "y": U()},
        "equations": ["N*(Va + Vb) = na*Ma*Va - Mb*Vb", "N = y*u"], "target": "y",
        "model": ["H2SO4 dibasic (n = 2); excess acid equivalents / total volume (volumes additive)",
                  "answer in units of 10^-1 N"]}},
    "1l6rl5zgs": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": C(False, "methyl orange changes colour at pH 3.1-4.4, below the CH3COONa equivalence point"),
            "B": C(False, "methyl red changes at pH 4.4-6.2, too acidic for a weak acid-strong base titration"),
            "C": C(True, "phenolphthalein, a weak acid ionised (pink) in base, changes at pH 8.3-10, around the "
                         "basic equivalence point of CH3COOH vs NaOH"),
            "D": C(False, "Eriochrome Black T is a metal-ion (complexometric) indicator")}},
        "option_values": OPT4, "note": "descriptive - curated"},
    "1ldolmvvn": {"formal": RX(
        "expr", terms={"a": os_("HBrO3", "Br"), "b": os_("HBrO4", "Br")}, expr="a + b",
        premises=[P("bromic acid = HBrO3, perbromic acid = HBrO4", "IUPAC/NCERT nomenclature")])},
    "1ldpq62ve": {"formal": RX(
        "oxidation_state", species="H4P2O6", element="P",
        premises=[P("hypophosphoric acid = H4P2O6", "NCERT XII 7 (oxoacids of phosphorus)")])},
    "1lduligif": {"formal": {
        "kind": "equation_system",
        "knowns": {"rho": K("1.21", "kg/L"), "M": K("24.2", "g/mol"), "Mb": K("0.24", "mol/L"),
                   "Vb": K("25", "mL"), "u": K("10**-2", "mL")},
        "unknowns": {"c": U("mol/L"), "V": U("mL"), "y": U()},
        "equations": ["c = rho/M", "c*V = Mb*Vb", "V = y*u"], "target": "y",
        "model": ["the 'solution' is the neat acid of the stated density: c = density / molar mass = 50 M",
                  "monobasic acid: 1 mol H+ per mol NaOH", "answer in units of 10^-2 mL"]}},
    "1lgp3h0ep": {"formal": RX(
        "balance", equation="Cr2O7^2- + H^+ + Fe^2+ -> Cr^3+ + Fe^3+ + H2O", scale_to={"Fe^2+": 6},
        **{"return": "expr", "map": {"X": "H^+", "Y": "Cr^3+", "Z": "H2O"}, "expr": "X + Y + Z"}),
        "note": "coefficients scaled so that Fe2+ = 6 as printed"},
    "1lgvv7bnc": {"formal": RX(
        "n_factor", equation="MnO4^- -> MnO2", species="MnO4^-", medium="basic",
        premises=[P("in (faintly) alkaline / neutral medium permanganate is reduced to MnO2",
                    "NCERT XII 8.6 - in strongly alkaline medium MnO4^2- (1 e-) is also cited")]),
        "note": "product identity is a curated premise"},
    "1lgys8ty2": {"formal": {
        "kind": "statement_set", "format": "statement_pair", "statements": {
            "I": C(False, "redox indicators respond to the change in electrode (oxidation) potential, not pH"),
            "II": C(False, "acid-base indicators respond to pH, not oxidation potential")}},
        "option_values": {"A": "0", "B": "10", "C": "1", "D": "11"}, "note": "descriptive - curated"},
    "1lgyt55ii": {"formal": RX(
        "expr", terms={"a": os_("Fe(CO)5", "Fe"), "b": os_("VO^2+", "V"), "c": os_("WO3", "W")}, expr="a + b + c")},
    "1lh031a7t": {"formal": RX(
        "balance", equation="IO3^- + I^- + H^+ -> I2 + H2O", scale_to={"IO3^-": 2},
        **{"return": "coefficient", "species": "I^-"}),
        "option_values": {"A": "10", "B": "2", "C": "12", "D": "6"},
        "note": "scaled to 2 IO3-; the balance then also gives 6 I2, 12 H+, 6 H2O as printed"},
    "1lh27pci2": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": is_redox("2[Au(CN)2]^- + Zn -> 2Au + [Zn(CN)4]^2-"),
            "B": SUB(RX("reaction_type", equation="2[Au(CN)2]^- + Zn -> 2Au + [Zn(CN)4]^2-"), "== displacement"),
            "C": SUB(RX("reaction_type", equation="2[Au(CN)2]^- + Zn -> 2Au + [Zn(CN)4]^2-"), "== decomposition"),
            "D": SUB(RX("reaction_type", equation="2[Au(CN)2]^- + Zn -> 2Au + [Zn(CN)4]^2-"), "== combination")}},
        "option_values": {"A": "{1, 2}", "B": "{3, 4}", "C": "{1}", "D": "{1, 4}"}},
    "1lh29uyl4": {"formal": RX(
        "oxidation_state", species="(NH4)3PO4.12MoO3", element="Mo",
        premises=[P("ammonium phosphomolybdate = (NH4)3PO4.12MoO3 (yellow ppt of the phosphate test)",
                    "NCERT XI/XII salt analysis")])},
    # ---------------------------------------------------------------- 45-66
    "lsblv392": {"formal": per_option(is_disp, {
        "A": "Cu^+ -> Cu^2+ + Cu", "B": "3MnO4^2- + 4H^+ -> 2MnO4^- + MnO2 + 2H2O",
        "C": "2KMnO4 -> K2MnO4 + MnO2 + O2", "D": "2MnO4^- + 3Mn^2+ + 2H2O -> 5MnO2 + 4H^+"}),
        "option_values": {"A": "{1, 2}", "B": "{1, 4}", "C": "{2, 3, 4}", "D": "{1, 2, 3}"},
        "note": "statement labels (A)-(D) of the stem; C is an intramolecular redox (Mn reduced, O oxidised), D is "
                "comproportionation"},
    "lsbmpghu": {"formal": per_option(lambda e: SUB(RX("verify_equation", equation=e), "== 1"), {
        "A": "Cr2O7^2- + 14H^+ + 7e^- -> 2Cr^3+ + 6H2O", "B": "Cr2O7^2- + 14H^+ + 6e^- -> 2Cr^3+ + 7H2O",
        "C": "Cr2O7^2- + 8H^+ + 4e^- -> 2Cr2O3 + 6H2O", "D": "Cr2O7^2- + 8H^+ + 6e^- -> 2Cr2O3 + 4H2O"}),
        "option_values": OPT4,
        "note": "each option's X, Y, Z, A substituted into the printed half-reaction; true iff atoms and charge "
                "balance (and equal the unique balancing)"},
    "jaoe38c1lscrqpvw": {"formal": per_option(
        lambda se: SUB(RX("capability", species=se[0], element=se[1]), "== reductant_only"),
        {"A": ("SO4^2-", "S"), "B": ("MnO4^-", "Mn"), "C": ("N^3-", "N"), "D": ("BrO3^-", "Br")}),
        "option_values": OPT4, "note": "cannot be an oxidant iff the element is already at its lowest ON"},
    "jaoe38c1lsda2rjf": {"formal": RX(
        "oxidation_state", species="CrO2Cl2", element="Cr",
        premises=[P("K2Cr2O7 + KCl + conc. H2SO4 gives chromyl chloride CrO2Cl2 (chromyl chloride test)",
                    "NCERT XI/XII salt analysis")])},
    "jaoe38c1lsda6dnv": {"formal": RX(
        "balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
        **{"return": "ratio", "species": ["H^+", "MnO4^-"]}),
        "note": "2MnO4- + 5C2O4^2- + 16H+ -> 2Mn2+ + 10CO2 + 8H2O: 16/2 per MnO4-"},
    "jaoe38c1lsfjgqcy": {"formal": RX(
        "balance", equation="Cl2 + OH^- -> ClO^- + Cl^- + H2O",
        **{"return": "code", "species": ["Cl2", "OH^-", "ClO^-", "Cl^-"]}),
        "option_values": {"A": code(3, 4, 4, 2), "B": code(1, 2, 1, 1), "C": code(2, 4, 1, 3), "D": code(2, 2, 1, 3)},
        "note": "(a, b, c, d) smallest-integer coefficients"},
    "jaoe38c1lsfjzybv": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": C(False, "I2 is the product in acidic medium"),
            "B": C(True, "NCERT XII 8.6: in neutral/faintly alkaline solution 2MnO4- + I- + H2O -> 2MnO2 + 2OH- + IO3-"),
            "C": C(False, "IO- is not the product"), "D": C(False, "IO4- is not the product")}},
        "option_values": OPT4, "note": "product identity is descriptive - curated (the IO3- equation itself balances: "
                                       "see redox balance of MnO4- + I- -> MnO2 + IO3- in base)"},
    "jaoe38c1lsfpnil4": {"formal": RX(
        "oxidation_state", species="[Fe(H2O)5(NO)]^2+", element="Fe",
        premises=[P("brown-ring compound = [Fe(H2O)5(NO)]SO4 with NO bound as NO+", "NCERT XII 7.4 / XI salt analysis")])},
    "1lsg8687o": {"formal": RX("count", checks=[
        {**Q("capability", species=sp_, element=el), "claim": "== both"} for sp_, el in
        [("H2O2", "O"), ("ClO3^-", "Cl"), ("P4", "P"), ("Cl2", "Cl"), ("Ag", "Ag"), ("Cu^+", "Cu"), ("F2", "F"),
         ("NO2", "N"), ("K^+", "K")]]),
        "note": "a species can disproportionate iff its element is in an intermediate oxidation state (NCERT XI 8.3)"},
    "1lsgz3rvm": {"formal": RX(
        "balance", equation="2MnO4^- + I^- + H2O -> I2 + MnO2 + OH^-", scale_to={"MnO4^-": 2},
        **{"return": "coefficient", "species": "OH^-"}),
        "note": "integer coefficients with 2 MnO4- as printed"},
    "lv0vyra5": {"formal": RX(
        "equivalence",
        n_factors={"nK": nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic"), "nO": nf("H2C2O4 -> CO2", "H2C2O4", "acidic")},
        system={"knowns": {"Vk": K("2", "mL"), "Vo": K("20", "mL"), "Mo": K("2", "mol/L")},
                "unknowns": {"Mk": U("mol/L")}, "equations": ["Mk*nK*Vk = Mo*nO*Vo"], "target": "Mk",
                "model": ["equivalents of KMnO4 = equivalents of oxalic acid"]},
        premises=[P("acidic KMnO4 -> Mn2+, oxalic acid -> CO2", "NCERT XII 8")])},
    "lv2ers4s": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": C(True, "greenish-yellow gas with MnO2/H2SO4 is Cl2, from a chloride: NH4Cl"),
            "B": C(False, "iodide gives violet I2 vapour"), "C": C(False, "nitrate gives no halogen"),
            "D": C(False, "bromide gives red-brown Br2")}},
        "option_values": OPT4, "note": "descriptive (salt analysis) - curated"},
    "lv5gt1sb": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": SUB(RX("all", checks=[
                {**Q("role", equation="S2O3^2- + Br2 + H2O -> SO4^2- + Br^- + H^+", species="S2O3^2-"),
                 "claim": "== reductant"},
                {**Q("role", equation="2S2O3^2- + I2 -> S4O6^2- + 2I^-", species="S2O3^2-"), "claim": "== oxidant"}]), "== 1"),
            "B": SUB(RX("expr", terms={"hi": os_("SO4^2-", "S"), "lo": os_("S4O6^2-", "S")}, expr="hi - lo"), "< 0"),
            "C": SUB(RX("expr", terms={"hi": os_("SO4^2-", "S"), "lo": os_("S4O6^2-", "S")}, expr="hi - lo"), "> 0"),
            "D": SUB(RX("all", checks=[
                {**Q("role", equation="S2O3^2- + Br2 + H2O -> SO4^2- + Br^- + H^+", species="Br2"),
                 "claim": "== reductant"},
                {**Q("role", equation="2S2O3^2- + I2 -> S4O6^2- + 2I^-", species="I2"), "claim": "== oxidant"}]), "== 1")}},
        "option_values": OPT4,
        "note": "roles from ON changes; B/C use the rule 'the stronger oxidant takes the same reductant to the "
                "higher ON' (S: +6 in SO4^2- with Br2 vs +5/2 in S4O6^2- with I2). The Br2 equation is used "
                "unbalanced (role needs only ON changes; the printed coefficients 5Br2/4Br- do not balance)"},
    "lvb29icb": {"formal": RX("count", checks=[
        {"curated": False, "note": "Sn4+ is the stable state of Sn (inert-pair effect weak): not an oxidant"},
        {"curated": False, "note": "Sn2+ is a reducing agent"},
        {"curated": False, "note": "Pb2+ is the stable state of Pb"},
        {"curated": True, "note": "Tl3+ is less stable than Tl+ (inert pair): oxidising"},
        {"curated": True, "note": "Pb4+ is less stable than Pb2+ (inert pair): oxidising"},
        {"curated": False, "note": "Tl+ is the stable state of Tl"}]),
        "option_values": {"A": "3", "B": "4", "C": "2", "D": "1"},
        "note": "inert-pair-effect stabilities are descriptive - curated per ion"},
    "lvb29nmy": {"formal": per_option(all_types, {
        "A": [("N2 + O2 -> 2NO", "combination"), ("2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "decomposition"),
              ("2Na + 2H2O -> 2NaOH + H2", "displacement"), ("2NO2 + 2OH^- -> NO2^- + NO3^- + H2O", "disproportionation")],
        "B": [("N2 + O2 -> 2NO", "decomposition"), ("2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "displacement"),
              ("2Na + 2H2O -> 2NaOH + H2", "disproportionation"), ("2NO2 + 2OH^- -> NO2^- + NO3^- + H2O", "combination")],
        "C": [("N2 + O2 -> 2NO", "displacement"), ("2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "disproportionation"),
              ("2Na + 2H2O -> 2NaOH + H2", "combination"), ("2NO2 + 2OH^- -> NO2^- + NO3^- + H2O", "decomposition")],
        "D": [("N2 + O2 -> 2NO", "disproportionation"), ("2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "displacement"),
              ("2Na + 2H2O -> 2NaOH + H2", "decomposition"), ("2NO2 + 2OH^- -> NO2^- + NO3^- + H2O", "combination")]}),
        "option_values": OPT4, "note": "option k true iff all four of its pairings match the engine's reaction type"},
    "m6qk9bth": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": SUB(RX("stoich", equation="5I^- + IO3^- + 6H^+ -> 3I2 + 3H2O", given={"I^-": "0.02"},
                        target="IO3^-"), "== 1/250"),
            "B": SUB(RX("expr", terms={"h": Q("stoich", equation="5I^- + IO3^- + 6H^+ -> 3I2 + 3H2O",
                                              given={"I^-": "0.02"}, target="H^+")}, expr="h/2"), "== 3/500"),
            "C": SUB(RX("stoich", equation="5I^- + IO3^- + 6H^+ -> 3I2 + 3H2O", given={"I^-": "0.05"},
                        target="I2"), "== 1/200"),
            "D": SUB(RX("n_factor", equation="5I^- + IO3^- + 6H^+ -> 3I2 + 3H2O", species="IO3^-"), "== 5")}},
        "option_values": {"A": "{3, 4}", "B": "{1, 2}", "C": "{2, 3}", "D": "{1, 4}"},
        "note": "200 mL of 0.1 M KI = 0.02 mol I-, 0.5 L = 0.05 mol; H2SO4 supplies 2 H+ (B: mol H2SO4 = H+/2); "
                "D: equivalent weight = M/n with n(IO3-) = 5 (I +5 -> 0)"},
    "m6qvb2if": {"formal": {
        "kind": "equation_system",
        "knowns": {"Mh": K("0.1", "mol/L"), "Vh": K("40", "mL"), "P": K("1", "atm"), "T": K("273", "K"),
                   "R": K("8.314", "J/(mol*K)")},
        "unknowns": {"nL": U("mol"), "n0": U("mol"), "nC": U("mol"), "x": U("cm^3")},
        "equations": ["Mh*Vh = 2*nL", "nL = n0/2", "nC = n0/2", "P*x = nC*R*T"], "target": "x",
        "model": ["Ca(OH)2 + 2HCl -> CaCl2 + 2H2O for the unreacted half", "CO2 + Ca(OH)2 -> CaCO3 + H2O (1:1)",
                  "ideal gas at 1 atm, 273 K; nearest integer (44.8 -> 45)"]}},
    "m6rp69zw": {"formal": per_option(
        lambda sp_: SUB(RX("capability", species=sp_, element="Cl"), "!= both"),
        {"A": "ClO4^-", "B": "ClO3^-", "C": "ClO^-", "D": "ClO2^-"}),
        "option_values": OPT4, "note": "no disproportionation from the highest oxidation state (Cl +7)"},
    "m6w9o93c": {"formal": {
        "kind": "statement_set", "format": "statement_pair", "statements": {
            "I": C(True, "oxalic acid-KMnO4 is slow at room temperature and is warmed to ~60 C; FAS titration is "
                         "done cold"),
            "II": C(True, "Mn2+ (MnSO4) formed initially autocatalyses the oxalate reaction; warming FAS lets air "
                          "oxidise Fe2+ to Fe3+, introducing error")}},
        "option_values": {"A": "1", "B": "10", "C": "11", "D": "0"}, "note": "descriptive (lab practice) - curated"},
    "m6w9o9wt": {"formal": per_option(all_types, {
        "A": [("CH4 + 2O2 -> CO2 + 2H2O", "decomposition"), ("2NaH -> 2Na + H2", "displacement"),
              ("V2O5 + 5Ca -> 2V + 5CaO", "disproportionation"), ("2H2O2 -> 2H2O + O2", "combination")],
        "B": [("CH4 + 2O2 -> CO2 + 2H2O", "displacement"), ("2NaH -> 2Na + H2", "disproportionation"),
              ("V2O5 + 5Ca -> 2V + 5CaO", "combination"), ("2H2O2 -> 2H2O + O2", "decomposition")],
        "C": [("CH4 + 2O2 -> CO2 + 2H2O", "combination"), ("2NaH -> 2Na + H2", "decomposition"),
              ("V2O5 + 5Ca -> 2V + 5CaO", "disproportionation"), ("2H2O2 -> 2H2O + O2", "displacement")],
        "D": [("CH4 + 2O2 -> CO2 + 2H2O", "combination"), ("2NaH -> 2Na + H2", "decomposition"),
              ("V2O5 + 5Ca -> 2V + 5CaO", "displacement"), ("2H2O2 -> 2H2O + O2", "disproportionation")]}),
        "option_values": OPT4,
        "note": "List II: I disproportionation, II combination, III decomposition, IV displacement. NCERT counts "
                "combustion in O2 as a combination redox reaction; H2O2 -> H2O + O2 is classed by its more specific "
                "type, disproportionation (engine precedence: disproportionation > displacement > decomposition > "
                "combination)"},
    "m6w9o9xm": {"formal": {
        "kind": "statement_set", "format": "select_combination", "statements": {
            "A": C(True, "both acidified dichromate and permanganate oxidise I- to I2"),
            "B": C(True, "both oxidise H2S/S2- to S"),
            "C": C(True, "both oxidise Fe2+ to Fe3+"),
            "D": C(False, "I- -> IO3- is the neutral/alkaline permanganate reaction, not acidic dichromate"),
            "E": C(False, "S2O3^2- -> SO4^2- is listed for neutral/alkaline permanganate, not acidic dichromate")}},
        "option_values": {"A": "{1, 2, 3}", "B": "{3, 4, 5}", "C": "{2, 3, 4}", "D": "{1, 4, 5}"},
        "note": "which oxidations each reagent performs is descriptive (NCERT XII 8.6 reaction lists) - curated; "
                "'Gamma^-' in A read as I-"},
    "m9ghxnw0": {"formal": RX(
        "expr", terms={
            "X": Q("on_change", **{"from": "MnO4^-", "to": "Mn^2+", "element": "Mn"}),
            "Y": {"formal": {"kind": "chem_property", "query": "value", "property": "subshell_electrons",
                             "species": "Fe^3+", "subshell": "3d"}, "subject": "CHEMISTRY"}},
        expr="X + Y",
        premises=[P("acidic KMnO4 is reduced to Mn2+", "NCERT XII 8.6"),
                  P("brown-red precipitate of the acetate test with neutral FeCl3 is basic iron(III) acetate "
                    "Fe(OH)2(CH3COO): iron is Fe3+", "NCERT XI/XII salt analysis")])},
}

SKIPPED: dict = {}
