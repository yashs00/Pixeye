"""Machine re-check of selected calculation items from the 300-question ascent set (chem/maths/phy).

Each item is written as equations with units and solved by the CQSE general checker (two methods, domain
checks, uniqueness). The result is compared with the database key (MCQ) or the value stated in the
explanation (numericals, whose key field is empty). Run:  python data/pyq/verify_ascent300_calcs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sympy as sp  # noqa: E402

from cqse.generic.system import solve_system  # noqa: E402

K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
MU0 = K("4*pi*10**-7", "T*m/A")

CASES = [
    # ---------------- PHYSICS ----------------
    ("m9ghxmzt", "ring vs sphere rolling: ratio = sqrt(x/5)", "nearest", "4",
     {"knowns": {"kr": K("1"), "ks": K("2/5")}, "unknowns": {"x": U("", "positive")},
      "equations": ["x/5 = (1 + ks)/(1 + kr)"], "target": "x",
      "model": ["v^2 = 2gh/(1+k^2/R^2); ratio v_ring/v_sphere"]}, None),
    ("m9fnut39", "wavelength, omega=628, v=300, pi=3.14", "options", ("C", "3 m"),
     {"knowns": {"w": K("628", "1/s"), "v": K("300", "m/s"), "p": K("3.14")},
      "unknowns": {"lam": U("m", "positive")}, "equations": ["lam*w = 2*p*v"], "target": "lam",
      "model": ["v = omega/k, k = 2pi/lambda"]}, {"A": "0.33", "B": "0.5", "C": "3", "D": "5"}),
    ("m6v42le1", "solenoid turns/m from electron period", "nearest", "250",
     {"knowns": {"m": K("9*10**-31", "kg"), "q": K("1.6*10**-19", "C"), "mu": MU0, "I": K("1.5", "A"),
                 "T": K("75", "ns")},
      "unknowns": {"n": U("1/m", "positive")},
      "equations": ["T*q*mu*n*I = 2*pi*m"],
      "target": "n", "model": ["T = 2 pi m/(qB), B = mu0 n I"]}, None),
    ("m6qjznvt", "capacitor plate gap from dV/dt (um)", "nearest", "1320",
     {"knowns": {"e0": K("9*10**-12", "F/m"), "p": K("22/7"), "r": K("10", "cm"), "I": K("0.15", "A"),
                 "dV": K("7*10**8", "V/s"), "um": K("1", "um")},
      "unknowns": {"d": U("m", "positive"), "x": U("", "positive")},
      "equations": ["I*d = e0*p*r**2*dV", "d = x*um"], "target": "x",
      "model": ["I = C dV/dt, C = e0 A/d"]}, None),
    ("m9fnutvk", "c / v in medium", "nearest", "6",
     {"knowns": {"mr": K("10/pi"), "er": K("1/0.0885")}, "unknowns": {"x": U("", "positive")},
      "equations": ["x**2 = mr*er"], "target": "x", "model": ["v = c/sqrt(mu_r eps_r)"]}, None),
    ("m9fnuree", "sphere pushed at top, a_cm", "options", ("B", "3.5"),
     {"knowns": {"F": K("49", "N"), "m": K("20", "kg")}, "unknowns": {"a": U("m/s^2", "positive")},
      "equations": ["a*(7*m/5) = 2*F"], "target": "a",
      "model": ["torque about contact: F*2R = (7/5) m R^2 alpha, a = R alpha"]},
     {"A": "2.5", "B": "3.5", "C": "0.25", "D": "0.35"}),
    ("m6rja0g8", "metre-rule balance mass (g)", "options", ("C", "190"),
     {"knowns": {"M": K("250", "g"), "m1": K("400", "g")}, "unknowns": {"m": U("g", "positive")},
      "equations": ["m1*30 = M*10 + m*50"], "target": "m",
      "model": ["torques about 40 cm pivot; rod weight at 50 cm"]},
     {"A": "290", "B": "200", "C": "190", "D": "300"}),
    ("m9gxgdp9", "block through rough region F=-kx", "options", ("C", "8 m/s"),
     {"knowns": {"m": K("1", "kg"), "vi": K("10", "m/s"), "k": K("10", "N/m"), "x1": K("0.1", "m"),
                 "x2": K("1.9", "m")},
      "unknowns": {"v": U("m/s", "positive")},
      "equations": ["m*v**2 = m*vi**2 - k*(x2**2 - x1**2)"], "target": "v",
      "model": ["work-energy; 'kr' in the stem read as kx"]}, {"A": "4", "B": "10", "C": "8", "D": "6"}),
    ("m6rp6kg1", "two antiparallel wires, field at P (x 10^-5 T)", "nearest", "1",
     {"knowns": {"mu": MU0, "I1": K("5", "A"), "I2": K("4", "A"), "r1": K("10", "cm"), "r2": K("4", "cm"),
                 "u": K("10**-5", "T")},
      "unknowns": {"B": U("T"), "x": U("")},
      "equations": ["2*pi*B = mu*(I2/r2 - I1/r1)", "B = x*u"], "target": "x",
      "model": ["P outside the pair, 4 cm from Y (from figure); explanation's 0.01 m is a typo"]}, None),
    ("m6qvbt5l", "electron between plates, v_y", "options", ("B", "16e6"),
     {"knowns": {"e": K("1.6*10**-19", "C"), "E": K("9.1", "V/cm"), "l": K("10", "cm"),
                 "m": K("9.1*10**-31", "kg"), "vx": K("10**6", "m/s")},
      "unknowns": {"vy": U("m/s", "positive")}, "equations": ["vy*m*vx = e*E*l"], "target": "vy",
      "model": ["a = eE/m for t = l/vx"]},
     {"A": "1*10**6", "B": "16*10**6", "C": "16*10**4", "D": "0"}),
    ("m9e5j2hj", "galvanometer voltage-sensitivity ratio", "nearest", "1",
     {"knowns": {"N1": K("15"), "A1": K("3.6*10**-3", "m^2"), "B1": K("0.25", "T"), "R1": K("5", "ohm"),
                 "N2": K("21"), "A2": K("1.8*10**-3", "m^2"), "B2": K("0.5", "T"), "R2": K("7", "ohm")},
      "unknowns": {"x": U("", "positive")},
      "equations": ["x*N2*A2*B2*R1 = N1*A1*B1*R2"], "target": "x", "model": ["S_V = NAB/(kR)"]}, None),
    # ---------------- CHEMISTRY ----------------
    ("m9dunp3y", "quinhydrone cell -> pKb of NH4X", "nearest", "6",
     {"knowns": {"Eag": K("0.8", "V"), "Eq": K("0.7", "V"), "s": K("0.06", "V"), "E": K("0.4", "V"),
                 "C": K("0.01")},
      "unknowns": {"pH": U("", "positive"), "pKb": U("", "positive")},
      "equations": ["E = Eag - (Eq - s*pH)", "pH = 7 - pKb/2 - log(C, 10)/2"], "target": "pKb",
      "model": ["E0(Q/QH2) = 0.70 V read from the IMAGE in the stem", "salt hydrolysis pH formula"]}, None),
    ("m9e5j4rt", "0.1 mol of azo dye from sulphanilic acid + 1-naphthylamine (g)", "options", ("B", "33"),
     {"knowns": {"C": K("12", "g/mol"), "H": K("1", "g/mol"), "N": K("14", "g/mol"), "O": K("16", "g/mol"),
                 "S": K("32", "g/mol"), "n": K("0.1", "mol")},
      "unknowns": {"m": U("g", "positive")},
      "equations": ["m = n*(16*C + 13*H + 3*N + 3*O + S)"], "target": "m",
      "model": ["product C16H13N3O3S (4-[(4-amino-1-naphthyl)azo]benzenesulfonic acid), M = 327"]},
     {"A": "330", "B": "33", "C": "343", "D": "66"}),
    # ---------------- MATHS ----------------
    ("m9fnuqsf", "line through (4,1,0) meeting L1, L2: determinant", "options", ("C", "8"),
     {"knowns": {}, "unknowns": {"l": U(), "u": U(), "D": U()},
      "equations": ["(3*l+1)*(4-u) - (4*l+3)*(u-1) = 0",
                    "(4*l+3)*(u+2) - (2*l-3)*(4-u) = 0",
                    "(2*l-3)*(u-1) - (3*l+1)*(u+2) = 0",
                    "D = ((2+3*l)*(4-u) - (3+4*l)*u) + ((1+2*l)*u - (2+3*l)*(6+u))"],
      "target": "D", "model": ["A on L1 at lambda, B on L2 at mu, PA x PB = 0 (collinear)"]},
     {"A": "16", "B": "6", "C": "8", "D": "12"}),
    ("m6t9xszy", "AP roots of 3x^2-px+q: q-2p", "nearest", "474",
     {"knowns": {"d": K("3/2")}, "unknowns": {"a": U(), "p": U(), "q": U(), "z": U()},
      "equations": ["11*(2*a + 10*d)/2 = 88", "p/3 = 2*a + 19*d", "q/3 = (a + 9*d)*(a + 10*d)", "z = q - 2*p"],
      "target": "z", "model": ["roots are T10, T11"]}, None),
    ("m6rj2ysd", "polygon angles in AP, largest 219 deg: n", "nearest", "20",
     {"knowns": {}, "unknowns": {"n": U("", "natural"), "a": U()},
      "equations": ["a + 6*(n - 1) = 219", "n*(2*a + 6*(n - 1))/2 = 180*(n - 2)"], "target": "n",
      "model": ["sum of interior angles (n-2)180"]}, None),
    ("m9fnusx5", "two APs with sum 36: p - q", "options", ("A", "540"),
     {"knowns": {}, "unknowns": {"d": U("", "positive"), "p": U(), "q": U(), "z": U()},
      "equations": ["p = 12*(144 - d**2)", "q = 12*(144 - (d + 3)**2)", "5*(p + q) = 19*(p - q)", "z = p - q"],
      "target": "z", "model": ["terms 12-d, 12, 12+d"]}, {"A": "540", "B": "450", "C": "600", "D": "630"}),
    ("m9e5j1on", "even-term AP: number of integer terms", "nearest", "4",
     {"knowns": {}, "unknowns": {"n": U("", "natural"), "a": U(), "d": U()},
      "equations": ["n*a + n*(n - 1)*d = 24", "n*a + n*n*d = 30", "(2*n - 1)*d = 21/2"], "target": "n",
      "model": ["2n terms; then terms a + k d listed and integers counted by hand: 3, 6, 9, 12"]}, None),
]


def main() -> None:
    print(f"{'id':<10} {'question':<52} {'engine':>12}  {'database':>8}  verdict")
    for qid, title, kind, ref, formal, opts in CASES:
        s = solve_system({"kind": "equation_system", **formal})
        hard = [r for r in s.records if r.hard and not r.is_affirmative() and r.check_id != "model.correspondence"]
        if s.value is None or hard:
            print(f"{qid:<10} {title:<52} {'BLOCKED':>12}  {str(ref):>8}  {[r.result for r in hard]}")
            continue
        v = float(sp.N(s.value, 15))
        if kind == "options":
            key, _ = ref
            close = [o for o, t in opts.items() if abs(float(sp.sympify(t)) - v) <= 0.02 * abs(v) + 1e-12]
            print(f"{qid:<10} {title:<52} {v:>12.6g}  {key:>8}  {'MATCH' if close == [key] else 'MISMATCH ' + str(close)}")
        else:
            frac = v - int(v)
            exact_int = abs(v - round(v)) < 1e-9
            if not exact_int and abs(abs(frac) - 0.5) < 0.05:
                verdict = "AMBIGUOUS ROUNDING (no nearest-integer rule?)"
            else:
                verdict = "MATCH" if str(round(v)) == ref else f"MISMATCH ({round(v)})"
                if not exact_int:
                    verdict += " (after rounding)"
            print(f"{qid:<10} {title:<52} {v:>12.6g}  {ref:>8}  {verdict}")


if __name__ == "__main__":
    main()
