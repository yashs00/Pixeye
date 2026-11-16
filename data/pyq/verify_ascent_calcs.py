"""Independent re-check of the calculation questions in ascent_selected_100_questions.json.

Each question is written as equations with units and solved by the CQSE general checker; the result
is compared with the database's stored key (MCQ) or the value stated in its explanation (numericals,
whose key field is empty). Run:  python data/pyq/verify_ascent_calcs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sympy as sp  # noqa: E402

from cqse.generic.system import solve_system  # noqa: E402

K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731

CASES = [
    ("m6qvbchf", "Al deposited, 2 A for 30 min", "options", ("C", "0.336 g"),
     {"knowns": {"I": K("2", "A"), "t": K("30", "min"), "M": K("27", "g/mol"), "F": K("96500", "C/mol"),
                 "z": K("3")},
      "unknowns": {"m": U("g", "positive")}, "equations": ["m*z*F = I*t*M"], "target": "m",
      "model": ["Al3+ + 3e- -> Al; 100% current efficiency"]},
     {"A": "1.660", "B": "1.007", "C": "0.336", "D": "0.441"}),
    ("m6rmra42", "NaCl electrolysis current from pH 12", "nearest", "2",
     {"knowns": {"V": K("600", "mL"), "c": K("0.01", "mol/L"), "t": K("5", "min"), "F": K("96500", "C/mol")},
      "unknowns": {"I": U("A", "positive")}, "equations": ["I*t = c*V*F"], "target": "I",
      "model": ["pH 12 -> [OH-] = 0.01 M produced; 1 e- per OH-; initial pH 7 neglected"]}, None),
    ("m9e5j5ry", "molar conductivity of 0.2% NaOH (x 10^2 mS dm^2/mol)", "nearest", "23",
     {"knowns": {"w": K("0.2", "g"), "Vs": K("100", "mL"), "M": K("40", "g/mol"), "rho": K("870", "mohm*m"),
                 "u": K("100", "mS*dm^2/mol")},
      "unknowns": {"c": U("mol/m^3", "positive"), "L": U("S*m^2/mol", "positive"), "x": U("", "positive")},
      "equations": ["c*M*Vs = w", "L*rho*c = 1", "L = x*u"], "target": "x",
      "model": ["Lambda_m = kappa/c, kappa = 1/rho"]}, None),
    ("m6srmyb5", "E(FeO4 2-/Fe2+) from Latimer diagram", "options", ("D", "1.7 V"),
     {"knowns": {"E1": K("2.0", "V"), "E2": K("0.8", "V")}, "unknowns": {"E": U("V")},
      "equations": ["4*E = 3*E1 + 1*E2"], "target": "E",
      "model": ["dG additive: n4 E4 = n1 E1 + n2 E2 (n = 3 for FeO4 2-/Fe3+, 1 for Fe3+/Fe2+)"]},
     {"A": "1.2", "B": "2.1", "C": "1.4", "D": "1.7"}),
    ("m9dv7asx", "pH at which dichromate half-cell EMF is zero", "nearest", "10",
     {"knowns": {"E0": K("1.33", "V"), "s": K("0.059", "V"), "Q": K("10**-6")},
      "unknowns": {"pH": U("", "positive")},
      "equations": ["0 = E0 - (s/6)*(log(Q, 10) + 14*pH)"], "target": "pH",
      "model": ["Nernst: E = E0 - (0.059/6) log([Cr3+]^2/([Cr2O7 2-][H+]^14))"]}, None),
    ("m9e5jawj", "Cu/Ag cell EMF after electrolysis (mV)", "nearest", "400",
     {"knowns": {"E0": K("0.46", "V"), "s": K("0.06", "V"), "Cu": K("1.0"), "Ag": K("0.1"),
                 "mV": K("1", "mV")},
      "unknowns": {"E": U("V"), "x": U("")},
      "equations": ["E = E0 - (s/2)*log(Cu/Ag**2, 10)", "E = x*mV"], "target": "x",
      "model": ["ASSUMES inert electrodes: 1 F removes 0.5 mol Cu2+ (1.5 -> 1.0 M), 0.1 F removes 0.1 mol Ag+ "
                "(0.2 -> 0.1 M). With Cu/Ag electrodes the concentrations would NOT change -> stem ambiguity"]},
     None),
    ("m9ghxnwx", "DNA hydrogen bonds", "nearest", "33",
     {"knowns": {"gc": K("7"), "at": K("6")}, "unknowns": {"h": U("", "natural")},
      "equations": ["h = 3*gc + 2*at"], "target": "h",
      "model": ["sequence GGCAAATCGGCTA: G/C = 7, A/T = 6 (counted from the stem)", "G-C 3 H-bonds, A-T 2"]}, None),
    ("m9gxgbh6", "spin-only moment of Co2+ (BM)", "nearest", "4",
     {"knowns": {"n": K("3")}, "unknowns": {"mu": U("", "positive")},
      "equations": ["mu**2 = n*(n + 2)"], "target": "mu",
      "model": ["Co highest atomisation enthalpy (data in explanation table)", "Co2+ d7 high spin: 3 unpaired"]},
     None),
    ("m6qrgsyy", "molar mass of Fe2O3 (chromite fusion)", "nearest", "160",
     {"knowns": {"Fe": K("56", "g/mol"), "O": K("16", "g/mol")}, "unknowns": {"M": U("g/mol", "positive")},
      "equations": ["M = 2*Fe + 3*O"], "target": "M",
      "model": ["4FeCr2O4 + 8Na2CO3 + 7O2 -> 8Na2CrO4 + 2Fe2O3 + 8CO2; insoluble product Fe2O3",
                "atomic masses NOT given in the stem; 56/16 assumed"]}, None),
]


def main() -> None:
    print(f"{'id':<10} {'question':<48} {'engine':>12}  {'database':>10}  verdict")
    for qid, title, kind, ref, formal, opts in CASES:
        s = solve_system({"kind": "equation_system", **formal})
        hard = [r for r in s.records if r.hard and not r.is_affirmative() and r.check_id != "model.correspondence"]
        if s.value is None or hard:
            print(f"{qid:<10} {title:<48} {'BLOCKED':>12}  {str(ref):>10}  {[r.result for r in hard]}")
            continue
        v = float(sp.N(s.value, 15))
        if kind == "options":
            key, _ = ref
            close = [o for o, t in opts.items() if abs(float(t) - v) <= 0.01 * abs(v)]
            ok = close == [key]
            print(f"{qid:<10} {title:<48} {v:>12.5g}  {key:>10}  {'MATCH' if ok else 'MISMATCH ' + str(close)}")
        else:
            frac = v - int(v)
            boundary = abs(frac - 0.5) < 0.05
            r = round(v)
            verdict = "AMBIGUOUS ROUNDING" if boundary else ("MATCH" if str(r) == ref else f"MISMATCH ({r})")
            print(f"{qid:<10} {title:<48} {v:>12.5g}  {ref:>10}  {verdict}")
    print("\nAll matches still need a teacher to confirm the model (listed in each case's 'model').")


if __name__ == "__main__":
    main()
