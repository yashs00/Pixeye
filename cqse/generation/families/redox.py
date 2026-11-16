"""Redox Reactions families (original questions; patterns modelled on bank questions, never their numbers/wording).

Every correct answer is a "redox" (or statement_set over "redox") formal solved by the redox engine with two
independent methods. Every wrong option is the engine value of a named student mistake:
  * charge-balance misreadings are written as `expr` formals over engine oxidation numbers of reference ions
    (O^2- for "oxide oxygen", H2O2 for "peroxide oxygen", H^+, K^+ ...), so the wrong reading is executed,
    not typed in;
  * n-factor / titration misreadings swap in the engine n-factor (or per-atom ON change) of the wrong process;
  * "which of the following" items are statement_set/select_combination formals (option k -> "{k}"); each wrong
    option is the unique option satisfying a named wrong criterion (e.g. "is a comproportionation").
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

import sympy as sp

from cqse.core.problem import Subject
from cqse.generation.framework import Family, Mistake

CH, SUBJ = "Redox Reactions", Subject.CHEMISTRY


# =============================================================================== formal helpers
def RX(q, **k):
    return {"kind": "redox", "query": q, **k}


def Q(q, **k):
    return {"query": q, **k}


def SUB(f, claim):
    return {"formal": f, "claim": claim, "subject": "CHEMISTRY"}


def on(species, el, which="average"):
    d = Q("oxidation_state", species=species, element=el)
    if which != "average":
        d["which"] = which
    return d


def nf(eq, species, medium=None):
    return Q("n_factor", equation=eq, species=species, medium=medium)


def per_option(fn, items: list) -> dict:
    """statement_set: statement k (1-based) = fn(items[k-1]); the value is the set of true statements."""
    return {"kind": "statement_set", "format": "select_combination",
            "statements": {str(i + 1): fn(x) for i, x in enumerate(items)}}


# Reference ions whose engine oxidation number is the "textbook default" a student plugs in.
REF = {"O": "O^2-", "H": "H^+", "K": "K^+", "Na": "Na^+", "Ba": "Ba^2+", "Ca": "Ca^2+", "F": "F^-",
       "Li": "Li^+", "Mg": "Mg^2+"}
PEROXO_O = ("H2O2", "O")        # O at -1
OXIDE_O = ("O^2-", "O")         # O at -2


def charge_balance(charge, n_target, parts) -> dict:
    """x = (charge - sum count*ON(ref)) / n_target, every ON taken from the engine.
    parts: [(count, ref_species, element)]."""
    terms = {f"t{i}": on(ref, el) for i, (_, ref, el) in enumerate(parts)}
    s = " + ".join(f"({c})*t{i}" for i, (c, _, _) in enumerate(parts)) or "0"
    return RX("expr", terms=terms, expr=f"(({charge}) - ({s}))/({n_target})")


def _atoms(species):
    from cqse.chemistry.engine import parse_formula
    f = parse_formula(species)
    return dict(f.atoms), f.charge


def default_parts(species, target, omit=()):
    atoms, _ = _atoms(species)
    return [(n, REF[e], e) for e, n in atoms.items() if e != target and e not in omit]


# =============================================================================== display helpers
def sp_html(s: str) -> str:
    """'Cr2O7^2-' -> Cr<sub>2</sub>O<sub>7</sub><sup>2−</sup>; 'FeSO4.7H2O' -> FeSO<sub>4</sub>·7H<sub>2</sub>O."""
    base, _, ch = s.partition("^")
    out = re.sub(r"(?<=[A-Za-z\)\]])(\d+)", r"<sub>\1</sub>", base).replace(".", "·")
    if ch:
        out += f"<sup>{ch.replace('-', '−')}</sup>"
    return out


def eq_html(eq: str) -> str:
    def side(t):
        terms = []
        for term in t.split(" + "):
            m = re.match(r"^(\d+)(?=[A-Z(\[])(.*)$", term.strip())
            terms.append((m.group(1) if m else "") + sp_html(m.group(2) if m else term.strip()))
        return " + ".join(terms)
    left, right = eq.split(" -> ")
    return f"{side(left)} → {side(right)}"


def on_disp(v, p=None) -> str:
    v = sp.nsimplify(v)
    if v == 0:
        return "$0$"
    sign = "+" if v > 0 else "-"
    a = abs(v)
    if a.is_integer:
        return f"${sign}{a}$"
    return f"${sign}\\frac{{{a.p}}}{{{a.q}}}$"


def int_disp(v, p=None) -> str:
    v = sp.nsimplify(v)
    return str(v) if v.is_integer else f"$\\frac{{{v.p}}}{{{v.q}}}$"


def num_str(v) -> str:
    """Exact decimal when terminating, else a fraction."""
    v = sp.nsimplify(v)
    if v.is_integer:
        return str(v)
    q = int(v.q)
    while q % 2 == 0:
        q //= 2
    while q % 5 == 0:
        q //= 5
    if q == 1:
        return f"{float(v):g}"
    return f"$\\frac{{{v.p}}}{{{v.q}}}$"


def set_disp_factory(key):
    """statement_set value {k} -> the k-th listed item's HTML."""
    def disp(v, p):
        return p[key][set_val(v) - 1]["html"] if len(v) == 1 else str(v)
    return disp


def set_val(v) -> int:
    return int(list(v)[0])


# =============================================================================== 1. ON of a common species (EASY)
COMMON = [("K2Cr2O7", "Cr"), ("CrO4^2-", "Cr"), ("KMnO4", "Mn"), ("MnO4^2-", "Mn"), ("ClO4^-", "Cl"),
          ("ClO3^-", "Cl"), ("ClO2^-", "Cl"), ("BrO3^-", "Br"), ("IO4^-", "I"), ("H5IO6", "I"), ("H3PO2", "P"),
          ("H3PO3", "P"), ("H4P2O7", "P"), ("H4P2O6", "P"), ("P2O7^4-", "P"), ("Na2S2O3", "S"), ("H2S2O7", "S"),
          ("SO3^2-", "S"), ("NO2^-", "N"), ("NH4^+", "N"), ("N2H4", "N"), ("NH2OH", "N"), ("VO4^3-", "V"),
          ("VO^2+", "V"), ("K2FeO4", "Fe"), ("Na2B4O7", "B"), ("XeO4", "Xe"), ("XeF4", "Xe"), ("HCO3^-", "C"),
          ("Na2MoO4", "Mo"), ("Cr2O7^2-", "Cr"), ("N2O5", "N"), ("KIO3", "I"), ("Cl2O7", "Cl")]


def on_common() -> Family:
    def sample(rng):
        s, e = rng.choice(COMMON)
        return {"species": s, "element": e}

    def formal(p):
        return RX("oxidation_state", species=p["species"], element=p["element"])

    def stem(p):
        return (f"<p>The oxidation number of {p['element']} in {sp_html(p['species'])} is:</p>")

    def mistakes(p):
        s, e = p["species"], p["element"]
        atoms, q = _atoms(s)
        n = atoms[e]
        parts = default_parts(s, e)
        out = []
        if q:
            out.append(Mistake("IGNORED_IONIC_CHARGE", charge_balance(0, n, parts),
                               "Students set the sum of oxidation numbers to zero out of habit, even for an ion.",
                               f"For an ion the oxidation numbers must add up to the ionic charge ({q:+d})."))
        if n > 1:
            out.append(Mistake("TOTAL_NOT_PER_ATOM", charge_balance(q, 1, parts),
                               f"Students stop at the total for all {n} {e} atoms and forget to divide.",
                               f"The question asks for one {e} atom: divide the total by {n}."))
        cations = [x for x in atoms if x in ("K", "Na", "H", "Ba", "Ca")]
        if cations:
            out.append(Mistake("FORGOT_" + "_".join(cations) + "_ATOMS",
                               charge_balance(q, n, default_parts(s, e, omit=cations)),
                               f"Students balance only the {e}–O part and forget the "
                               f"{'/'.join(cations)} atoms.",
                               "Every atom in the formula contributes to the charge balance."))
        if q:
            out.append(Mistake("CHARGE_SIGN_REVERSED", charge_balance(-q, n, parts),
                               "Students put the ionic charge on the wrong side of the balance (sign slip).",
                               f"Sum of oxidation numbers = {q:+d}, not {-q:+d}."))
        if atoms.get("O", 0) > 1:
            out.append(Mistake("O_SUBSCRIPT_IGNORED",
                               charge_balance(q, n, [(c if el != "O" else 1, r, el) for c, r, el in parts]),
                               "Students count oxygen's −2 only once instead of once per O atom.",
                               f"There are {atoms['O']} O atoms, each −2."))
        out.append(Mistake("SIGN_SLIP_IN_BALANCE", RX("expr", terms={"x": on(s, e)}, expr="-x"),
                           "Students move the known contributions across the equation without changing sign.",
                           "x + (sum of the others) = charge, so x = charge − (sum of the others)."))
        return out

    def explain(p, v):
        s, e = p["species"], p["element"]
        return (f"<p>Use O = −2, H = +1, alkali metals +1 and let the oxidation number of {e} be x; the sum of all "
                f"oxidation numbers equals the charge on {sp_html(s)}.</p><p>Solving gives x = {on_disp(v)}.</p>")

    return Family(id="redox.on_common", subject=SUBJ, chapter=CH, topic="Oxidation Number", difficulty="EASY",
                  sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain, display=on_disp,
                  modelled_on=["1ldpq62ve", "1krz034xm", "uNrZvCorxnp4BUjUHOjgy2xukeyh0ywx"]).register()


# =============================================================================== 2. tricky ON (structure) (HARD)
def _oxide_split(charge, n, others, n_peroxo, n_oxide):
    parts = list(others)
    if n_peroxo:
        parts.append((n_peroxo, *PEROXO_O))
    if n_oxide:
        parts.append((n_oxide, *OXIDE_O))
    return charge_balance(charge, n, parts)


def _peroxo_mistakes(species, el, n, charge, others, n_o, true_peroxo):
    alt = 4 if true_peroxo == 2 else 2
    out = [Mistake("PEROXIDE_O_TAKEN_AS_MINUS_2", _oxide_split(charge, n, others, 0, n_o),
                   "Students apply 'O is −2' blindly and miss the O–O (peroxo) linkage.",
                   f"{sp_html(species)} has {true_peroxo} peroxide O atoms at −1; an O–O bond adds nothing to "
                   "the oxidation number."),
           Mistake("WRONG_NUMBER_OF_PEROXO_O", _oxide_split(charge, n, others, alt, n_o - alt),
                   f"Students miscount the peroxo bridges ({alt // 2} instead of {true_peroxo // 2}).",
                   f"The structure has exactly {true_peroxo} peroxide O atoms."),
           Mistake("ALL_O_TAKEN_AS_PEROXIDE", _oxide_split(charge, n, others, n_o, 0),
                   "Students who remember 'peroxide' assign −1 to every oxygen.",
                   "Only the O atoms in O–O bridges are −1; the others stay −2.")]
    return out


def _mixed_mistakes(species, el, which):
    avg, mx, mn = on(species, el), on(species, el, "max"), on(species, el, "min")
    m = [("FORMULA_AVERAGE", RX("expr", terms={"x": avg}, expr="x"),
          "Students compute the formula average and report it as the value of a particular atom.",
          "The atoms are not equivalent; the average is not the oxidation number of any single atom."),
         ("HIGHEST_ATOM_VALUE", RX("expr", terms={"x": mx}, expr="x"),
          "Students quote the oxidation number of the most oxidised atom.",
          "That is only one kind of atom in the structure."),
         ("LOWEST_ATOM_VALUE", RX("expr", terms={"x": mn}, expr="x"),
          "Students quote the oxidation number of the least oxidised atom.",
          "That is only one kind of atom in the structure."),
         ("TOTAL_NOT_PER_ATOM", RX("expr", terms={"x": avg}, expr=f"{_atoms(species)[0][el]}*x"),
          "Students report the total for all atoms of the element instead of the value per atom.",
          "Divide the total by the number of atoms.")]
    skip = {"average": "FORMULA_AVERAGE", "max": "HIGHEST_ATOM_VALUE", "min": "LOWEST_ATOM_VALUE"}[which]
    if which != "average":
        skip = {skip, "TOTAL_NOT_PER_ATOM"}
    out = [Mistake(i, f, a, b) for i, f, a, b in m if i not in (skip if isinstance(skip, set) else {skip})]
    if species == "S4O6^2-" and which == "min":
        out.append(Mistake("BRIDGING_S_AS_SULPHIDE", RX("expr", terms={"x": on("H2S", "S")}, expr="x"),
                           "Students give the S–S bridging atoms the sulphide value −2.",
                           "S bonded only to S (and S) has no electronegativity difference: oxidation number 0."))
    if species == "S4O6^2-" and which == "max":
        out.append(Mistake("TERMINAL_S_AS_SULPHATE", RX("expr", terms={"x": on("SO4^2-", "S")}, expr="x"),
                           "Students treat each SO3 end like a sulphate sulphur (+6).",
                           "Each terminal S has three O and one S–S bond: +5, not +6."))
    return out


TRICKY = [
    # (species, element, which, kind, extra)
    ("CrO5", "Cr", "average", "peroxo", dict(charge=0, n=1, others=[], n_o=5, peroxo=4)),
    ("H2SO5", "S", "average", "peroxo", dict(charge=0, n=1, others=[(2, "H^+", "H")], n_o=5, peroxo=2)),
    ("H2S2O8", "S", "average", "peroxo", dict(charge=0, n=2, others=[(2, "H^+", "H")], n_o=8, peroxo=2)),
    ("S2O8^2-", "S", "average", "peroxo", dict(charge=-2, n=2, others=[], n_o=8, peroxo=2)),
    ("S4O6^2-", "S", "average", "mixed", {}),
    ("S4O6^2-", "S", "min", "mixed", {}),
    ("S4O6^2-", "S", "max", "mixed", {}),
    ("Fe3O4", "Fe", "average", "mixed", {}),
    ("Pb3O4", "Pb", "average", "mixed", {}),
    ("Mn3O4", "Mn", "average", "mixed", {}),
    ("C3O2", "C", "average", "mixed", {}),
    ("NaN3", "N", "average", "mixed", {}),
    ("KO2", "O", "average", "superoxide", {}),
    ("[Fe(H2O)5(NO)]^2+", "Fe", "average", "nitrosyl", {}),
]
TRICKY_NAMES = {"CrO5": "chromium pentoxide (blue 'chromium peroxide')", "H2SO5": "peroxomonosulphuric acid "
                "(Caro's acid)", "H2S2O8": "peroxodisulphuric acid (Marshall's acid)",
                "S2O8^2-": "the peroxodisulphate ion", "S4O6^2-": "the tetrathionate ion",
                "Fe3O4": "magnetite", "Pb3O4": "red lead", "Mn3O4": "hausmannite", "C3O2": "carbon suboxide",
                "NaN3": "sodium azide", "KO2": "potassium superoxide",
                "[Fe(H2O)5(NO)]^2+": "the brown-ring complex ion"}


def on_tricky() -> Family:
    def sample(rng):
        i = rng.randrange(len(TRICKY))
        return {"i": i, "species": TRICKY[i][0], "element": TRICKY[i][1], "which": TRICKY[i][2]}

    def formal(p):
        return RX("oxidation_state", species=p["species"], element=p["element"], which=p["which"])

    def stem(p):
        s, e, w = p["species"], p["element"], p["which"]
        what = {"average": f"the (average) oxidation number of {e}",
                "max": f"the highest oxidation number shown by any {e} atom",
                "min": f"the lowest oxidation number shown by any {e} atom"}[w]
        return f"<p>In {sp_html(s)}, {TRICKY_NAMES[s]}, {what} is:</p>"

    def mistakes(p):
        s, e, w, kind, x = TRICKY[p["i"]]
        if kind == "peroxo":
            return _peroxo_mistakes(s, e, x["n"], x["charge"], x["others"], x["n_o"], x["peroxo"])
        if kind == "mixed":
            out = _mixed_mistakes(s, e, w)
            if s == "S4O6^2-" and w == "average":
                out.append(Mistake("IGNORED_IONIC_CHARGE", charge_balance(0, 4, [(6, *OXIDE_O)]),
                                   "Students set the sum to zero for the ion.", "The sum must equal −2."))
            if s == "NaN3":
                out.insert(0, Mistake("TREATED_AS_NITRIDE", RX("expr", terms={"x": on("N^3-", "N")}, expr="x"),
                                      "Students take N at its common negative state −3, as in nitrides.",
                                      "Azide N3⁻ carries only −1 shared over three N atoms."))
            return out
        if kind == "superoxide":
            return [Mistake("TREATED_AS_PEROXIDE", RX("expr", terms={"x": on(*PEROXO_O)}, expr="x"),
                            "Students recognise 'not an oxide' but take KO2 as a peroxide.",
                            "KO2 contains O2^− (superoxide): −1 shared by two O atoms."),
                    Mistake("TREATED_AS_OXIDE", RX("expr", terms={"x": on(*OXIDE_O)}, expr="x"),
                            "Students apply 'O is −2'.", "Then K would have to be +4, impossible for group 1."),
                    Mistake("CHARGE_SIGN_REVERSED", charge_balance(0, 2, [(-1, "K^+", "K")]),
                            "Students move K's +1 across without changing sign.",
                            "2x + (+1) = 0 gives x = −1/2."),
                    Mistake("K_TAKEN_AS_PLUS_2", charge_balance(0, 2, [(1, "Ba^2+", "Ba")]),
                            "Students treat K like an alkaline-earth metal (+2).", "K is always +1.")]
        if kind == "nitrosyl":
            h2o = [(5, "H2O", "O"), (10, "H^+", "H")]
            return [Mistake("NO_TAKEN_AS_NEUTRAL", charge_balance(2, 1, h2o + [(1, "NO", "N"), (1, "NO", "O")]),
                            "Students treat NO as a neutral ligand like H2O.",
                            "In the brown-ring complex NO is bound as nitrosonium NO⁺."),
                    Mistake("NO_TAKEN_AS_NITROSYL_ANION",
                            charge_balance(2, 1, h2o + [(1, "NO^-", "N"), (1, "NO^-", "O")]),
                            "Students treat NO as an anionic ligand NO⁻.",
                            "Electron transfer goes from NO to iron, giving NO⁺ and Fe(I)."),
                    Mistake("IGNORED_COMPLEX_CHARGE",
                            charge_balance(0, 1, h2o + [(1, "NO^+", "N"), (1, "NO^+", "O")]),
                            "Students set the total to zero, forgetting the 2+ charge of the complex.",
                            "The oxidation numbers must add up to +2."),
                    Mistake("FE_FROM_FESO4", RX("expr", terms={"x": on("FeSO4", "Fe")}, expr="x"),
                            "Students quote iron's value in the FeSO4 used for the test.",
                            "Iron is reduced to +1 when NO⁺ forms in the complex.")]
        return []

    def explain(p, v):
        s, e, w, kind, x = TRICKY[p["i"]]
        why = {"peroxo": "Draw the structure: O atoms in O–O (peroxo) bridges are −1, the others −2.",
               "mixed": "The atoms of this element are in different environments (from the structure); "
                        "per-atom values differ from the formula average.",
                        "superoxide": "KO2 is K⁺O2⁻; the −1 charge is shared by two O atoms.",
               "nitrosyl": "The complex is [Fe(H2O)5(NO⁺)]²⁺; H2O is neutral, NO⁺ is +1."}[kind]
        return f"<p>{why}</p><p>Required value: <b>{on_disp(v)}</b> (checked by rules and by the Lewis/fragment " \
               "structure).</p>"

    return Family(id="redox.on_tricky", subject=SUBJ, chapter=CH, topic="Oxidation Number", difficulty="HARD",
                  sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain, display=on_disp,
                  modelled_on=["sUGLsiqlV2h6S2Ps2z7k9k2k5dyph0k", "jaoe38c1lsfpnil4", "lv5gt1sb"]).register()


# =============================================================================== 3. sum of ONs (numerical)
SUM_POOLS = {
    "S": {"H2S": -2, "SO2": 4, "H2SO4": 6, "H2SO5": 6, "Na2S2O3": 2, "SCl2": 2, "H2S2O7": 6, "S2O8^2-": 6,
          "SO3^2-": 4, "SF6": 6},
    "N": {"NH3": -3, "N2H4": -2, "NH2OH": -1, "N2O": 1, "NO": 2, "HNO2": 3, "NO2": 4, "HNO3": 5, "N2O5": 5,
          "N2O3": 3},
    "Cl": {"HCl": -1, "HOCl": 1, "HClO2": 3, "ClO2": 4, "KClO3": 5, "HClO4": 7, "Cl2O7": 7},
    "P": {"PH3": -3, "H3PO2": 1, "H3PO3": 3, "H3PO4": 5, "H4P2O6": 4, "H4P2O7": 5},
    "Mn": {"KMnO4": 7, "K2MnO4": 6, "MnO2": 4, "Mn2O3": 3, "MnSO4": 2},
    "Cr": {"K2Cr2O7": 6, "CrO5": 6, "Cr2O3": 3, "CrO2Cl2": 6, "CrCl3": 3},
}


def on_sum() -> Family:
    def sample(rng):
        while True:
            el = rng.choice(list(SUM_POOLS))
            sps = sorted(rng.sample(list(SUM_POOLS[el]), 3))
            if sum(SUM_POOLS[el][s] for s in sps) > 0:
                return {"element": el, "species": sps}

    def formal(p):
        return RX("expr", terms={f"x{i}": on(s, p["element"]) for i, s in enumerate(p["species"])},
                  expr="x0 + x1 + x2")

    def stem(p):
        a, b, c = (sp_html(s) for s in p["species"])
        return (f"<p>The oxidation numbers of {p['element']} in {a}, {b} and {c} are x, y and z respectively. "
                f"The value of x + y + z is ________.</p>")

    def mistakes(p):   # numerical: recorded for teachers, not shown as options
        el = p["element"]
        return [Mistake("TOTAL_NOT_PER_ATOM",
                        RX("expr", terms={f"x{i}": on(s, el) for i, s in enumerate(p["species"])},
                           expr=" + ".join(f"{_atoms(s)[0][el]}*x{i}" for i, s in enumerate(p["species"]))),
                        "Students add the totals for all atoms of the element.", "Per-atom values are asked."),
                Mistake("MAGNITUDES_ADDED",
                        RX("expr", terms={f"x{i}": on(s, el) for i, s in enumerate(p["species"])},
                           expr="Abs(x0) + Abs(x1) + Abs(x2)"),
                        "Students drop the minus sign of negative oxidation numbers.",
                        "Negative oxidation numbers must be added with their sign.")]

    def explain(p, v):
        rows = ", ".join(f"{sp_html(s)}: {on_disp(SUM_POOLS[p['element']][s])}" for s in p["species"])
        return f"<p>{rows}.</p><p>x + y + z = <b>{v}</b>.</p>"

    return Family(id="redox.on_sum", subject=SUBJ, chapter=CH, topic="Oxidation Number", difficulty="MEDIUM",
                  sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain, numerical=True,
                  modelled_on=["1ldolmvvn", "uNrZvCorxnp4BUjUHOjgy2xukeyh0ywx", "1lgyt55ii"]).register()


# =============================================================================== equations (balancing / electrons)
# (oxidant, its product, reductant, its product(s), medium); equation = ox + red -> products
EQS = [
    ("MnO4^-", "Mn^2+", "C2O4^2-", "CO2", "acidic"), ("Cr2O7^2-", "Cr^3+", "Fe^2+", "Fe^3+", "acidic"),
    ("Cr2O7^2-", "Cr^3+", "I^-", "I2", "acidic"), ("MnO4^-", "Mn^2+", "SO3^2-", "SO4^2-", "acidic"),
    ("Cr2O7^2-", "Cr^3+", "H2S", "S", "acidic"), ("MnO4^-", "Mn^2+", "NO2^-", "NO3^-", "acidic"),
    ("NO3^-", "NO", "Cu", "Cu^2+", "acidic"), ("NO3^-", "NH4^+", "Zn", "Zn^2+", "acidic"),
    ("Cr2O7^2-", "Cr^3+", "SO2", "SO4^2-", "acidic"), ("MnO4^-", "Mn^2+", "Fe^2+", "Fe^3+", "acidic"),
    ("ClO3^-", "Cl^-", "Fe^2+", "Fe^3+", "acidic"), ("Cr2O7^2-", "Cr^3+", "C2O4^2-", "CO2", "acidic"),
    ("MnO4^-", "Mn^2+", "H2S", "S", "acidic"), ("Cr2O7^2-", "Cr^3+", "NO2^-", "NO3^-", "acidic"),
    ("MnO4^-", "Mn^2+", "Cl^-", "Cl2", "acidic"), ("Cr2O7^2-", "Cr^3+", "Sn^2+", "Sn^4+", "acidic"),
    ("MnO4^-", "MnO2", "I^-", "IO3^-", "basic"), ("MnO4^-", "MnO2", "SO3^2-", "SO4^2-", "basic"),
    ("IO3^-", "I^-", "Cr(OH)3", "CrO4^2-", "basic"), ("MnO4^-", "MnO2", "Br^-", "BrO3^-", "basic"),
    ("NO3^-", "NH3", "Al", "Al(OH)4^-", "basic"), ("CrO4^2-", "Cr(OH)3", "Fe(OH)2", "Fe(OH)3", "basic"),
    ("MnO4^-", "MnO2", "C2O4^2-", "CO3^2-", "basic"), ("NO3^-", "NH3", "Zn", "ZnO2^2-", "basic"),
]


def _full(e):
    ox, oxp, red, redp, _ = e
    return f"{ox} + {red} -> {oxp} + {redp}"


def _ox_half(e):
    return f"{e[0]} -> {e[1]}"


def _red_half(e):
    return f"{e[2]} -> {e[3]}"


def _scaled_half(e, half, s):
    """coefficient of s in a half-reaction after scaling it to the electrons of the full equation (uncancelled)."""
    med = e[4]
    return RX("expr", terms={"c": Q("balance", equation=half, medium=med, half=True, species=s),
                             "h": Q("balance", equation=half, medium=med, half=True, **{"return": "electrons"}),
                             "E": Q("balance", equation=_full(e), medium=med, **{"return": "electrons"})},
              expr="c*E/h")


def balance_coeff() -> Family:
    def sample(rng):
        i = rng.randrange(len(EQS))
        med = EQS[i][4]
        return {"i": i, "species": rng.choice(["H^+", "H2O"] if med == "acidic" else ["OH^-", "H2O"])}

    def formal(p):
        e = EQS[p["i"]]
        return RX("balance", equation=_full(e), medium=e[4], species=p["species"])

    def stem(p):
        e = EQS[p["i"]]
        return (f"<p>The skeletal equation</p><p style='text-align:center'>{eq_html(_full(e))}</p>"
                f"<p>is balanced in <b>{e[4]}</b> medium by the ion-electron method using the smallest whole-number "
                f"coefficients. The number of {sp_html(p['species'])} {'ions' if '^' in p['species'] else 'molecules'}"
                f" in the balanced equation is:</p>")

    def mistakes(p):
        return [m for m in _balance_mistakes(p) if _nonzero(m.formal)]

    def _nonzero(f):
        from cqse.generation.framework import _solve
        v, _ = _solve(SUBJ, f)
        return v is None or v != 0      # a "0" option (species absent) is not a credible distractor

    def _balance_mistakes(p):
        e, s = EQS[p["i"]], p["species"]
        med, other = e[4], ("basic" if e[4] == "acidic" else "acidic")
        swap_s = s if s == "H2O" else ("H^+" if s == "OH^-" else "OH^-")
        return [
            Mistake("WRONG_MEDIUM", RX("balance", equation=_full(e), medium=other,
                                       species=s if s == "H2O" else ("H^+" if other == "acidic" else "OH^-")),
                    f"Students balance with H⁺/H₂O (or OH⁻/H₂O) out of habit, ignoring that the medium is {med}.",
                    f"In {med} medium the equation must be balanced with "
                    f"{'H⁺' if med == 'acidic' else 'OH⁻'} and H₂O; the water count changes on conversion."),
            Mistake("REDUCTION_HALF_ONLY", RX("balance", equation=_ox_half(e), medium=med, species=s, half=True),
                    "Students read the coefficient off the balanced reduction half-reaction alone.",
                    "The two half-reactions must be scaled to equal electrons and added; H⁺/OH⁻/H₂O partly "
                    "cancel."),
            Mistake("OXIDATION_HALF_ONLY", RX("balance", equation=_red_half(e), medium=med, species=s, half=True),
                    "Students read the coefficient off the balanced oxidation half-reaction alone.",
                    "Both halves contribute; the electrons must cancel first."),
            Mistake("SCALED_REDUCTION_HALF_NOT_CANCELLED", _scaled_half(e, _ox_half(e), s),
                    "Students multiply the reduction half correctly but read the coefficient before cancelling "
                    f"the {sp_html(s)} that also appears on the other side.",
                    "After adding the halves, species on both sides must be cancelled."),
            Mistake("SCALED_OXIDATION_HALF_NOT_CANCELLED", _scaled_half(e, _red_half(e), s),
                    "Students take the coefficient from the scaled oxidation half and forget the other half.",
                    "Both scaled halves are added and common species cancelled."),
            Mistake("OTHER_MEDIUM_SPECIES", RX("balance", equation=_full(e), medium=med,
                                               species="H2O" if s != "H2O" else ("H^+" if med == "acidic"
                                                                                 else "OH^-")),
                    "Students mix up the coefficients of H₂O and H⁺/OH⁻ in the final equation.",
                    "Each species has its own coefficient; read the one asked for."),
            Mistake("CROSS_MULTIPLIED_NOT_LCM",
                    RX("expr", terms={"c": Q("balance", equation=_full(e), medium=med, species=s),
                                      "a": Q("balance", equation=_ox_half(e), medium=med, half=True,
                                             **{"return": "electrons"}),
                                      "b": Q("balance", equation=_red_half(e), medium=med, half=True,
                                             **{"return": "electrons"}),
                                      "E": Q("balance", equation=_full(e), medium=med, **{"return": "electrons"})},
                       expr="c*a*b/E"),
                    "Students multiply the halves by each other's electron count (cross-multiplication) and do "
                    "not reduce the result.", "Coefficients must be the smallest whole numbers."),
        ]

    def explain(p, v):
        e = EQS[p["i"]]
        return (f"<p>Reduction: {eq_html(_ox_half(e))}; oxidation: {eq_html(_red_half(e))}. Balance each half "
                f"(atoms, O with H₂O, H with {'H⁺' if e[4] == 'acidic' else 'H₂O/OH⁻'}, charge with e⁻), equalise "
                f"electrons and add.</p><p>Coefficient of {sp_html(p['species'])}: <b>{v}</b> (confirmed by the "
                "unique nullspace balancing).</p>")

    return Family(id="redox.balance_coeff", subject=SUBJ, chapter=CH, topic="Balancing Redox Reactions",
                  difficulty="HARD", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=int_disp,
                  modelled_on=["Ee9Rx5oIInUG5CDx", "jaoe38c1lsda6dnv", "1lsgz3rvm"]).register()


def electrons() -> Family:
    def sample(rng):
        return {"i": rng.randrange(len(EQS))}

    def formal(p):
        e = EQS[p["i"]]
        return RX("balance", equation=_full(e), medium=e[4], **{"return": "electrons"})

    def stem(p):
        e = EQS[p["i"]]
        return (f"<p>When the reaction</p><p style='text-align:center'>{eq_html(_full(e))}</p><p>is balanced in "
                f"{e[4]} medium with the smallest whole-number coefficients, the total number of electrons "
                f"transferred from the reducing agent to the oxidising agent is:</p>")

    def mistakes(p):
        e = EQS[p["i"]]
        full = _full(e)
        n_ox, n_red = nf(full, e[0], e[4]), nf(full, e[2], e[4])
        return [
            Mistake("OXIDANT_HALF_ONLY", RX("expr", terms={"a": n_ox}, expr="a"),
                    "Students count the electrons gained by one formula unit of the oxidant only.",
                    "The oxidant half must be multiplied up until the electrons match the reductant's."),
            Mistake("REDUCTANT_HALF_ONLY", RX("expr", terms={"b": n_red}, expr="b"),
                    "Students count the electrons lost by one formula unit of the reductant only.",
                    "The reductant half must be multiplied up until the electrons match the oxidant's."),
            Mistake("N_FACTORS_ADDED", RX("expr", terms={"a": n_ox, "b": n_red}, expr="a + b"),
                    "Students add the electrons of the two half-reactions.",
                    "Electrons lost = electrons gained; the common number is the lcm, not the sum."),
            Mistake("CROSS_MULTIPLIED", RX("expr", terms={"a": n_ox, "b": n_red}, expr="a*b"),
                    "Students cross-multiply the half-reactions and do not reduce.",
                    "Smallest whole numbers: use the lcm of the two electron counts."),
            Mistake("ELECTRONS_COUNTED_TWICE", RX("expr", terms={"c": formal(p)}, expr="2*c"),
                    "Students add the electrons lost and the electrons gained.",
                    "They are the same electrons; count them once."),
        ]

    def explain(p, v):
        e = EQS[p["i"]]
        return (f"<p>Electrons per formula unit: {sp_html(e[0])} → {sp_html(e[1])} and {sp_html(e[2])} → "
                f"{sp_html(e[3])}. Multiply each half so that electrons lost = electrons gained (lcm).</p>"
                f"<p>Electrons transferred: <b>{v}</b>.</p>")

    return Family(id="redox.electrons", subject=SUBJ, chapter=CH, topic="Balancing Redox Reactions",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=int_disp, modelled_on=["1lgvv7bnc", "dJsK1dnG9eeuqU6h6B1v3"]).register()


# =============================================================================== 6. equivalent weight
MN_PRODUCT = {"acidic": ("Mn^2+", "acidic", "acidic medium (dil. H<sub>2</sub>SO<sub>4</sub>)"),
              "neutral": ("MnO2", "basic", "neutral or faintly alkaline medium"),
              "strong": ("MnO4^2-", "basic", "strongly alkaline medium")}
EQW = [
    # id, compound (stem), species in eq, half eq, medium, mistakes [(id, formal, why_s, why_w)]
    "kmno4_acidic", "kmno4_neutral", "kmno4_strong", "k2cr2o7", "fec2o4", "oxalic", "hypo",
    "arsenious", "sulphite",
]


def _eqw_case(c):
    def mn(k):
        prod, med, _ = MN_PRODUCT[k]
        return nf(f"MnO4^- -> {prod}", "MnO4^-", med)
    if c.startswith("kmno4"):
        k = c.split("_")[1]
        others = [x for x in MN_PRODUCT if x != k]
        prod, med, words = MN_PRODUCT[k]
        ms = [(f"PRODUCT_OF_{o.upper()}_MEDIUM", RX("expr", terms={"n": mn(o)}, expr="n"),
               f"Students use the permanganate product of {MN_PRODUCT[o][2].replace('<sub>', '').replace('</sub>', '')}"
               " (memorised one-size-fits-all n-factor).",
               f"In {words.replace('<sub>', '').replace('</sub>', '')} MnO₄⁻ goes to {MN_PRODUCT[k][0]}.")
              for o in others]
        ms.append(("PRODUCT_ON_AS_N", RX("expr", terms={"n": on(prod, "Mn")}, expr="n"),
                   "Students take the oxidation number of Mn in the product as the n-factor.",
                   "n = change in oxidation number per formula unit (+7 → product), not the final value."))
        ms.append(("INITIAL_ON_AS_N", RX("expr", terms={"n": on("MnO4^-", "Mn")}, expr="n"),
                   "Students take the oxidation number of Mn in KMnO₄ (+7) as the n-factor.",
                   "Only the change in oxidation number counts."))
        return dict(name="KMnO<sub>4</sub>", what=f"acts as an oxidising agent in {words}",
                    eq=f"MnO4^- -> {prod}", sp="MnO4^-", med=med, mist=ms)
    if c == "k2cr2o7":
        return dict(name="K<sub>2</sub>Cr<sub>2</sub>O<sub>7</sub>",
                    what="oxidises Fe<sup>2+</sup> in acidic medium (Cr<sub>2</sub>O<sub>7</sub><sup>2−</sup> → "
                         "Cr<sup>3+</sup>)", eq="Cr2O7^2- -> Cr^3+", sp="Cr2O7^2-", med="acidic",
                    mist=[("FORGOT_2_CR", RX("on_change", **{"from": "Cr2O7^2-", "to": "Cr^3+", "element": "Cr"}),
                           "Students take the change per Cr atom (+6 → +3 = 3).",
                           "Each dichromate has 2 Cr atoms: n = 2 × 3 = 6."),
                          ("PARTNER_N_FACTOR", nf("Fe^2+ -> Fe^3+", "Fe^2+"),
                           "Students use the n-factor of the partner (Fe²⁺, 1).", "Use the dichromate's own change."),
                          ("TOTAL_ON_AS_N", RX("expr", terms={"x": on("Cr2O7^2-", "Cr")}, expr="2*x"),
                           "Students take the total oxidation number of Cr (2 × 6) as n.",
                           "Only the change (2 × 3) counts.")])
    if c == "fec2o4":
        return dict(name="FeC<sub>2</sub>O<sub>4</sub> (ferrous oxalate)",
                    what="is completely oxidised by acidified KMnO<sub>4</sub> (Fe<sup>2+</sup> → Fe<sup>3+</sup>, "
                         "C<sub>2</sub>O<sub>4</sub><sup>2−</sup> → CO<sub>2</sub>)",
                    eq="FeC2O4 -> Fe^3+ + CO2", sp="FeC2O4", med="acidic",
                    mist=[("ONLY_FE_OXIDISED", nf("Fe^2+ -> Fe^3+", "Fe^2+"),
                           "Students oxidise only Fe²⁺ and forget the oxalate.", "Both Fe²⁺ and C₂O₄²⁻ are oxidised."),
                          ("ONLY_OXALATE_OXIDISED", nf("C2O4^2- -> CO2", "C2O4^2-", "acidic"),
                           "Students oxidise only the oxalate.", "Fe²⁺ → Fe³⁺ also releases one electron."),
                          ("PARTNER_N_FACTOR", nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic"),
                           "Students use the n-factor of KMnO₄ (5).", "Use the electrons lost by FeC₂O₄."),
                          ("PER_C_ATOM", RX("on_change", **{"from": "C2O4^2-", "to": "CO2", "element": "C"}),
                           "Students take the change per C atom only.", "Two C and one Fe change: 1 + 2 = 3.")])
    if c == "oxalic":
        return dict(name="H<sub>2</sub>C<sub>2</sub>O<sub>4</sub>·2H<sub>2</sub>O",
                    what="is oxidised to CO<sub>2</sub> by acidified KMnO<sub>4</sub>",
                    eq="H2C2O4.2H2O -> CO2", sp="H2C2O4.2H2O", med="acidic",
                    mist=[("PER_C_ATOM", RX("on_change", **{"from": "C2O4^2-", "to": "CO2", "element": "C"}),
                           "Students take the change per C atom (+3 → +4).", "There are two C atoms: n = 2."),
                          ("PARTNER_N_FACTOR", nf("MnO4^- -> Mn^2+", "MnO4^-", "acidic"),
                           "Students use the n-factor of KMnO₄.", "Use the electrons lost by oxalic acid."),
                          ("TOTAL_ELECTRONS_IN_EQUATION",
                           RX("balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
                              **{"return": "electrons"}),
                           "Students use all electrons in the balanced equation (10).",
                           "n-factor is per formula unit of oxalic acid."),
                          ("FINAL_ON_AS_N", RX("expr", terms={"x": on("CO2", "C")}, expr="x"),
                           "Students take the ON of C in CO₂ (+4) as n.", "Only the change counts.")])
    if c == "hypo":
        return dict(name="Na<sub>2</sub>S<sub>2</sub>O<sub>3</sub>",
                    what="reacts with I<sub>2</sub> to give S<sub>4</sub>O<sub>6</sub><sup>2−</sup>",
                    eq="S2O3^2- -> S4O6^2-", sp="S2O3^2-", med=None,
                    mist=[("PER_S_ATOM", RX("on_change", **{"from": "S2O3^2-", "to": "S4O6^2-", "element": "S"}),
                           "Students take the average change per S atom (+2 → +5/2 = 1/2).",
                           "Two S atoms per thiosulphate: n = 2 × 1/2 = 1."),
                          ("PRODUCT_WITH_CL2", nf("S2O3^2- -> SO4^2-", "S2O3^2-", "basic"),
                           "Students use the product formed with Cl₂/Br₂ (sulphate).",
                           "Iodine (a milder oxidant) stops at tetrathionate."),
                          ("PARTNER_N_FACTOR", nf("I2 -> I^-", "I2"),
                           "Students use the n-factor of iodine (2).", "Use the electrons lost by thiosulphate."),
                          ("FINAL_ON_AS_N", RX("expr", terms={"x": on("S4O6^2-", "S")}, expr="x"),
                           "Students take the average ON of S in tetrathionate as n.", "Only the change counts.")])
    if c == "arsenious":
        return dict(name="As<sub>2</sub>O<sub>3</sub>",
                    what="is oxidised to H<sub>3</sub>AsO<sub>4</sub> in acidic medium",
                    eq="As2O3 -> H3AsO4", sp="As2O3", med="acidic",
                    mist=[("PER_AS_ATOM", RX("on_change", **{"from": "As2O3", "to": "H3AsO4", "element": "As"}),
                           "Students take the change per As atom (+3 → +5).", "Two As atoms: n = 4."),
                          ("FINAL_ON_AS_N", RX("expr", terms={"x": on("H3AsO4", "As")}, expr="x"),
                           "Students take the final ON (+5) as n.", "Only the change counts."),
                          ("INITIAL_ON_AS_N", RX("expr", terms={"x": on("As2O3", "As")}, expr="x"),
                           "Students take the initial ON (+3) as n.", "Only the change counts."),
                          ("TOTAL_ON_AS_N", RX("expr", terms={"x": on("H3AsO4", "As")}, expr="2*x"),
                           "Students take 2 × final ON.", "n = 2 × (5 − 3) = 4.")])
    if c == "sulphite":
        return dict(name="Na<sub>2</sub>SO<sub>3</sub>",
                    what="is oxidised to sulphate by acidified K<sub>2</sub>Cr<sub>2</sub>O<sub>7</sub>",
                    eq="SO3^2- -> SO4^2-", sp="SO3^2-", med="acidic",
                    mist=[("PARTNER_N_FACTOR", nf("Cr2O7^2- -> Cr^3+", "Cr2O7^2-", "acidic"),
                           "Students use the n-factor of dichromate (6).", "Use the electrons lost by sulphite."),
                          ("FINAL_ON_AS_N", RX("expr", terms={"x": on("SO4^2-", "S")}, expr="x"),
                           "Students take the ON of S in sulphate (+6) as n.", "Only the change (4 → 6) counts."),
                          ("INITIAL_ON_AS_N", RX("expr", terms={"x": on("SO3^2-", "S")}, expr="x"),
                           "Students take the ON of S in sulphite (+4) as n.", "Only the change counts."),
                          ("PARTNER_PER_CR", RX("on_change", **{"from": "Cr2O7^2-", "to": "Cr^3+", "element": "Cr"}),
                           "Students use dichromate's per-Cr change (3).", "Use sulphite's own change, 2.")])
    raise KeyError(c)


def eq_weight() -> Family:
    def sample(rng):
        return {"case": rng.choice(EQW)}

    def formal(p):
        c = _eqw_case(p["case"])
        return RX("n_factor", equation=c["eq"], species=c["sp"], medium=c["med"])

    def stem(p):
        c = _eqw_case(p["case"])
        return (f"<p>{c['name']} {c['what']}. If M is the molar mass of {c['name']}, its equivalent weight in "
                f"this reaction is:</p>")

    def mistakes(p):
        return [Mistake(i, f if "kind" in f else {"kind": "redox", **f}, a, b)
                for i, f, a, b in _eqw_case(p["case"])["mist"]]

    def display(v, p):
        v = sp.nsimplify(v)
        if v == 1:
            return "$M$"
        if v.is_integer:
            return f"$\\frac{{M}}{{{v}}}$"
        r = 1 / v
        return f"${r}M$" if r.is_integer else f"$\\frac{{{v.q}M}}{{{v.p}}}$"

    def explain(p, v):
        c = _eqw_case(p["case"])
        return (f"<p>n-factor = electrons exchanged per formula unit = {int_disp(v)} (balanced half-reaction "
                f"{eq_html(c['eq'])}, checked against the total change in oxidation number).</p>"
                f"<p>Equivalent weight = M / n = {display(v, p)}.</p>")

    return Family(id="redox.eq_weight", subject=SUBJ, chapter=CH, topic="n-Factor And Equivalent Weight",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=display, modelled_on=["dJsK1dnG9eeuqU6h6B1v3", "1krxb954p", "m9ghxnw0"]).register()


# =============================================================================== titrations
OXIDANTS = {"KMnO4": dict(html="KMnO<sub>4</sub>", eq="MnO4^- -> Mn^2+", sp="MnO4^-", n=5,
                          note="MnO<sub>4</sub><sup>−</sup> → Mn<sup>2+</sup>"),
            "K2Cr2O7": dict(html="K<sub>2</sub>Cr<sub>2</sub>O<sub>7</sub>", eq="Cr2O7^2- -> Cr^3+",
                            sp="Cr2O7^2-", n=6, note="Cr<sub>2</sub>O<sub>7</sub><sup>2−</sup> → Cr<sup>3+</sup>")}
REDUCTANTS = {
    "FeSO4": dict(html="FeSO<sub>4</sub>", eq="FeSO4 -> Fe^3+ + SO4^2-", sp="FeSO4", n=1,
                  note="Fe<sup>2+</sup> → Fe<sup>3+</sup>", M=152),
    "Mohr": dict(html="Mohr's salt, FeSO<sub>4</sub>·(NH<sub>4</sub>)<sub>2</sub>SO<sub>4</sub>·6H<sub>2</sub>O",
                 eq="FeSO4.(NH4)2SO4.6H2O -> Fe^3+ + SO4^2- + NH4^+", sp="FeSO4.(NH4)2SO4.6H2O", n=1,
                 note="Fe<sup>2+</sup> → Fe<sup>3+</sup>", M=392),
    "Na2C2O4": dict(html="sodium oxalate", eq="C2O4^2- -> CO2", sp="C2O4^2-", n=2,
                    note="C<sub>2</sub>O<sub>4</sub><sup>2−</sup> → CO<sub>2</sub>", M=134),
    "H2C2O4": dict(html="oxalic acid, H<sub>2</sub>C<sub>2</sub>O<sub>4</sub>·2H<sub>2</sub>O",
                   eq="H2C2O4.2H2O -> CO2", sp="H2C2O4.2H2O", n=2,
                   note="C<sub>2</sub>O<sub>4</sub><sup>2−</sup> → CO<sub>2</sub>", M=126),
    "FeC2O4": dict(html="ferrous oxalate, FeC<sub>2</sub>O<sub>4</sub>", eq="FeC2O4 -> Fe^3+ + CO2", sp="FeC2O4",
                   n=3, note="Fe<sup>2+</sup> → Fe<sup>3+</sup> and C<sub>2</sub>O<sub>4</sub><sup>2−</sup> → "
                             "CO<sub>2</sub>", M=144),
    "Na2SO3": dict(html="sodium sulphite", eq="SO3^2- -> SO4^2-", sp="SO3^2-", n=2,
                   note="SO<sub>3</sub><sup>2−</sup> → SO<sub>4</sub><sup>2−</sup>", M=126),
    "SnCl2": dict(html="stannous chloride", eq="Sn^2+ -> Sn^4+", sp="Sn^2+", n=2,
                  note="Sn<sup>2+</sup> → Sn<sup>4+</sup>", M=190),
}
CONC_OX = ["1/100", "1/50", "1/25", "1/20", "1/10"]
CONC_RED = ["1/20", "1/10", "1/5", "1/4", "1/2"]
VOLS = [10, 20, 25, 30, 40, 50]


def _dec(s):
    f = Fraction(s)
    return f"{float(f):g}"


def _vol_formal(p, n_ox=None, n_red=None, expr=None):
    o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
    t = {"nO": n_ox or nf(o["eq"], o["sp"], "acidic"), "nR": n_red or nf(r["eq"], r["sp"], "acidic")}
    return RX("expr", terms=t, expr=expr or f"({p['cR']})*({p['VR']})*nR/(({p['cO']})*nO)")


def titration_volume() -> Family:
    def sample(rng):
        while True:
            p = {"ox": rng.choice(list(OXIDANTS)), "red": rng.choice(list(REDUCTANTS)), "cO": rng.choice(CONC_OX),
                 "cR": rng.choice(CONC_RED), "VR": rng.choice(VOLS)}
            v = Fraction(p["cR"]) * p["VR"] * REDUCTANTS[p["red"]]["n"] / (Fraction(p["cO"]) *
                                                                           OXIDANTS[p["ox"]]["n"])
            if v.denominator == 1 and 5 <= v <= 100:
                return p

    def formal(p):
        return _vol_formal(p)

    def stem(p):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        return (f"<p>{p['VR']} mL of a {_dec(p['cR'])} M solution of {r['html']} is titrated against "
                f"{_dec(p['cO'])} M {o['html']} solution in the presence of dilute H<sub>2</sub>SO<sub>4</sub> "
                f"({o['note']}; {r['note']}). The volume of {o['html']} solution (in mL) required to reach the end "
                f"point is ________.</p>")

    def mistakes(p):
        o = OXIDANTS[p["ox"]]
        return [Mistake("N_FACTORS_SWAPPED", _vol_formal(p, expr=f"({p['cR']})*({p['VR']})*nO/(({p['cO']})*nR)"),
                        "Students put each n-factor on the wrong side of the equivalence.",
                        "n × M × V of the oxidant = n × M × V of the reductant."),
                Mistake("MOLARITY_EQUATION", _vol_formal(p, expr=f"({p['cR']})*({p['VR']})/({p['cO']})"),
                        "Students use M₁V₁ = M₂V₂ without n-factors.", "Redox titrations equate equivalents.")]

    def explain(p, v):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        return (f"<p>Equivalents of {o['html']} = equivalents of {r['html']}: n<sub>O</sub>M<sub>O</sub>V<sub>O</sub>"
                f" = n<sub>R</sub>M<sub>R</sub>V<sub>R</sub> with n<sub>O</sub> = {o['n']}, n<sub>R</sub> = "
                f"{r['n']}.</p><p>V = {_dec(p['cR'])} × {p['VR']} × {r['n']} / ({_dec(p['cO'])} × {o['n']}) = "
                f"<b>{v} mL</b>.</p>")

    return Family(id="redox.titration_volume", subject=SUBJ, chapter=CH, topic="Redox Titrations",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  numerical=True, modelled_on=["lv0vyra5", "1l55oahmw", "1ks1jhofn"]).register()


def titration_mass() -> Family:
    """Mass of a solid reductant given -> volume of oxidant (MCQ with named n-factor slips)."""
    REDS = ["FeC2O4", "H2C2O4", "Mohr", "FeSO4", "Na2C2O4"]

    def sample(rng):
        while True:
            p = {"ox": rng.choice(list(OXIDANTS)), "red": rng.choice(REDS), "cO": rng.choice(CONC_OX),
                 "mmol": rng.choice([1, 2, 3, 4, 5, 6])}
            r, o = REDUCTANTS[p["red"]], OXIDANTS[p["ox"]]
            v = Fraction(p["mmol"]) * r["n"] / (Fraction(p["cO"]) * o["n"])
            if 4 <= v <= 120 and (v * 10).denominator == 1:
                return p

    def _f(p, nO=None, nR=None, expr=None):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        m = Fraction(p["mmol"] * r["M"], 1000)
        t = {"nO": nO or nf(o["eq"], o["sp"], "acidic"), "nR": nR or nf(r["eq"], r["sp"], "acidic")}
        return RX("expr", terms=t, expr=expr or f"1000*({m})/({r['M']})*nR/(({p['cO']})*nO)")

    def formal(p):
        return _f(p)

    def mass(p):
        return f"{float(Fraction(p['mmol'] * REDUCTANTS[p['red']]['M'], 1000)):g}"

    def stem(p):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        return (f"<p>{mass(p)} g of {r['html']} (molar mass {r['M']} g mol<sup>−1</sup>) is dissolved in dilute "
                f"H<sub>2</sub>SO<sub>4</sub> and titrated with {_dec(p['cO'])} M {o['html']} "
                f"({o['note']}; {r['note']}). The volume of {o['html']} solution needed for complete oxidation "
                f"is:</p>")

    def mistakes(p):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        m = Fraction(p["mmol"] * r["M"], 1000)
        out = []
        if p["ox"] == "K2Cr2O7":
            out.append(Mistake("FORGOT_2_CR", _f(p, nO=Q("on_change", **{"from": "Cr2O7^2-", "to": "Cr^3+",
                                                                          "element": "Cr"})),
                               "Students take dichromate's n-factor as 3 (change per Cr atom).",
                               "Cr₂O₇²⁻ has two Cr atoms: n = 6."))
        else:
            out.append(Mistake("MNO2_PRODUCT", _f(p, nO=nf("MnO4^- -> MnO2", "MnO4^-", "basic")),
                               "Students use n = 3 for KMnO₄ (product MnO₂).",
                               "In acidic medium MnO₄⁻ → Mn²⁺, n = 5."))
        if p["red"] == "FeC2O4":
            out += [Mistake("ONLY_FE_OXIDISED", _f(p, nR=nf("Fe^2+ -> Fe^3+", "Fe^2+")),
                            "Students oxidise only Fe²⁺ and forget the oxalate.", "Both ions are oxidised: n = 3."),
                    Mistake("ONLY_OXALATE_OXIDISED", _f(p, nR=nf("C2O4^2- -> CO2", "C2O4^2-", "acidic")),
                            "Students oxidise only the oxalate.", "Fe²⁺ also loses an electron: n = 3.")]
        if p["red"] in ("H2C2O4", "Na2C2O4"):
            out.append(Mistake("PER_C_ATOM", _f(p, nR=Q("on_change", **{"from": "C2O4^2-", "to": "CO2",
                                                                         "element": "C"})),
                               "Students take oxalate's n-factor as 1 (per C atom).", "Two C atoms: n = 2."))
        out += [Mistake("N_FACTORS_SWAPPED", _f(p, expr=f"1000*({m})/({r['M']})*nO/(({p['cO']})*nR)"),
                        "Students put the n-factors on the wrong sides.",
                        "n × moles of oxidant = n × moles of reductant."),
                Mistake("MOLE_RATIO_1_TO_1", _f(p, expr=f"1000*({m})/({r['M']})/({p['cO']})"),
                        "Students assume 1 mol oxidant per mol reductant.",
                        "Electrons, not moles, must balance.")]
        return out

    def explain(p, v):
        o, r = OXIDANTS[p["ox"]], REDUCTANTS[p["red"]]
        return (f"<p>Moles of {r['html']} = {mass(p)}/{r['M']} = {p['mmol']}×10<sup>−3</sup> mol; "
                f"n<sub>R</sub> = {r['n']}, n<sub>O</sub> = {o['n']}.</p><p>V = "
                f"{p['mmol']}×10<sup>−3</sup> × {r['n']} / ({_dec(p['cO'])} × {o['n']}) L = <b>{num_str(v)} mL</b>."
                "</p>")

    return Family(id="redox.titration_mass", subject=SUBJ, chapter=CH, topic="Redox Titrations",
                  difficulty="HARD", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=lambda v, p: f"{num_str(v)} mL",
                  modelled_on=["slYLNkJOzOyAXojifajgy2xukfq9pezo", "KAjBwzLqopJziWrx0DCek"]).register()


# =============================================================================== 9. reaction type (statement_set)
DISPRO = ["2H2O2 -> 2H2O + O2", "3HNO2 -> HNO3 + 2NO + H2O", "Cl2 + 2OH^- -> Cl^- + ClO^- + H2O",
          "2Cu^+ -> Cu^2+ + Cu", "3MnO4^2- + 4H^+ -> 2MnO4^- + MnO2 + 2H2O", "P4 + 3OH^- + 3H2O -> PH3 + 3H2PO2^-",
          "4KClO3 -> 3KClO4 + KCl", "2NO2 + H2O -> HNO3 + HNO2", "3Br2 + 6OH^- -> 5Br^- + BrO3^- + 3H2O",
          "2CuCl -> CuCl2 + Cu", "4H3PO3 -> 3H3PO4 + PH3", "Cl2 + H2O -> HCl + HOCl",
          "2ClO2 + 2OH^- -> ClO2^- + ClO3^- + H2O", "Hg2Cl2 -> HgCl2 + Hg"]
COMPRO = ["5Br^- + BrO3^- + 6H^+ -> 3Br2 + 3H2O", "2H2S + SO2 -> 3S + 2H2O", "IO3^- + 5I^- + 6H^+ -> 3I2 + 3H2O",
          "Fe + 2Fe^3+ -> 3Fe^2+", "Hg + Hg^2+ -> Hg2^2+", "NaH + H2O -> NaOH + H2", "CaH2 + 2H2O -> Ca(OH)2 + 2H2",
          "5Cl^- + ClO3^- + 6H^+ -> 3Cl2 + 3H2O", "NH4NO2 -> N2 + 2H2O", "NH4NO3 -> N2O + 2H2O"]
DECOMP = ["2KClO3 -> 2KCl + 3O2", "2HgO -> 2Hg + O2", "2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "2KNO3 -> 2KNO2 + O2",
          "2Ag2O -> 4Ag + O2", "(NH4)2Cr2O7 -> N2 + Cr2O3 + 4H2O", "PCl5 -> PCl3 + Cl2", "2HI -> H2 + I2"]
NONREDOX = ["CaCO3 -> CaO + CO2", "2NaHCO3 -> Na2CO3 + CO2 + H2O", "NH4Cl -> NH3 + HCl",
            "Cr2O7^2- + 2OH^- -> 2CrO4^2- + H2O", "2CrO4^2- + 2H^+ -> Cr2O7^2- + H2O", "XeF6 + 3H2O -> XeO3 + 6HF",
            "SO3 + H2O -> H2SO4"]
COMBO = ["H2 + Cl2 -> 2HCl", "2Mg + O2 -> 2MgO", "2SO2 + O2 -> 2SO3", "Ca + H2 -> CaH2", "N2 + O2 -> 2NO",
         "2Fe + 3Cl2 -> 2FeCl3", "2NO + O2 -> 2NO2"]

RT_MISTAKES = {
    "comproportionation": ("COMPROPORTIONATION_CONFUSED",
                           "Students see the same element on both sides in different states and call it "
                           "disproportionation.",
                           "Here two different oxidation states of the element meet at one intermediate state "
                           "(comproportionation) — the reverse process."),
    "disproportionation": ("DISPROPORTIONATION_CONFUSED",
                           "Students mix up the two terms because both involve one element in several states.",
                           "Here one oxidation state splits into a higher and a lower one (disproportionation)."),
    "decomposition": ("DECOMPOSITION_CONFUSED",
                      "One reactant giving two products looks like 'splitting' into two states.",
                      "The element oxidised and the element reduced are different elements."),
    "non_redox": ("NO_ON_CHANGE",
                  "The same element appears in two species, so students assume a change of oxidation state.",
                  "No element changes its oxidation number: this is not a redox reaction at all."),
    "combination": ("COMBINATION_CONFUSED",
                    "Two reactants forming one product looks like 'two states meeting'.",
                    "The atoms combining belong to different elements (or start at the same 0 state)."),
}


def reaction_type() -> Family:
    def sample(rng):
        ask = rng.choice(["disproportionation", "comproportionation"])
        if ask == "disproportionation":
            items = [("disproportionation", rng.choice(DISPRO)), ("comproportionation", rng.choice(COMPRO)),
                     ("decomposition", rng.choice(DECOMP)), ("non_redox", rng.choice(NONREDOX))]
        else:
            items = [("comproportionation", rng.choice(COMPRO)), ("disproportionation", rng.choice(DISPRO)),
                     ("combination", rng.choice(COMBO)), ("non_redox", rng.choice(NONREDOX))]
        rng.shuffle(items)
        return {"ask": ask, "items": [{"type": t, "eq": e, "html": eq_html(e)} for t, e in items]}

    def _by_type(p, t):
        return per_option(lambda it: SUB(RX("reaction_type", equation=it["eq"]), f"== {t}"), p["items"])

    def formal(p):
        return _by_type(p, p["ask"])

    def stem(p):
        return (f"<p>Which of the following is an example of a <b>{p['ask']}</b> reaction?</p>")

    def mistakes(p):
        return [Mistake(RT_MISTAKES[it["type"]][0], _by_type(p, it["type"]), *RT_MISTAKES[it["type"]][1:])
                for it in p["items"] if it["type"] != p["ask"]]

    def explain(p, v):
        it = p["items"][set_val(v) - 1]
        d = ("one element in a single oxidation state is simultaneously oxidised and reduced"
             if p["ask"] == "disproportionation" else
             "the same element in two different oxidation states forms a single intermediate state")
        return (f"<p>In a {p['ask']} reaction {d}. Assign oxidation numbers in every option:</p>"
                + "".join(f"<p>{x['html']}: {x['type'].replace('_', '-')}</p>" for x in p["items"])
                + f"<p>Answer: {it['html']}.</p>")

    return Family(id="redox.reaction_type", subject=SUBJ, chapter=CH, topic="Types Of Redox Reactions",
                  difficulty="MEDIUM", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=set_disp_factory("items"),
                  modelled_on=["BsaVZ1wbbWcIJLZwfg3rsa0w2w9jx56tijx", "1l58jinm1", "lvb29nmy"]).register()


# =============================================================================== 10. capability (statement_set)
OX_ONLY = [("KMnO4", "Mn"), ("K2Cr2O7", "Cr"), ("HNO3", "N"), ("H2SO4", "S"), ("F2", "F"), ("HClO4", "Cl"),
           ("PbO2", "Pb"), ("SO3", "S"), ("N2O5", "N"), ("CrO3", "Cr"), ("Sn^4+", "Sn")]
RED_ONLY = [("H2S", "S"), ("NH3", "N"), ("KI", "I"), ("HCl", "Cl"), ("Na", "Na"), ("Zn", "Zn"), ("NaH", "H"),
            ("PH3", "P"), ("CH4", "C"), ("Br^-", "Br")]
BOTH_HIGH = [("SO2", "S"), ("HNO2", "N"), ("NO2", "N"), ("ClO3^-", "Cl"), ("MnO4^2-", "Mn"), ("MnO2", "Mn"),
             ("H3PO3", "P"), ("ClO2", "Cl")]
BOTH_LOW = [("H2O2", "O"), ("Cl2", "Cl"), ("Br2", "Br"), ("I2", "I"), ("O3", "O"), ("S", "S")]
BOTH_NEG = [("N2H4", "N"), ("NH2OH", "N"), ("H2O2", "O")]
BOTH_POS = [("Fe^2+", "Fe"), ("Sn^2+", "Sn"), ("Cu^+", "Cu"), ("Na2SO3", "S"), ("NO", "N"), ("H2SO3", "S"),
            ("CO", "C")]
ZERO_OX = [("F2", "F")]
OX_POS = [x for x in OX_ONLY if x not in ZERO_OX]          # distractor pools must satisfy the ON claim
RED_NEG = [x for x in RED_ONLY if x not in (("Na", "Na"), ("Zn", "Zn"))]
ZERO_RED = [("Na", "Na"), ("Zn", "Zn")]


def _cap(it, cap, on_claim=None):
    checks = [{**Q("capability", species=it["species"], element=it["element"]), "claim": f"== {cap}"}]
    if on_claim:
        checks.append({**on(it["species"], it["element"]), "claim": on_claim})
    return SUB(RX("all", checks=checks), "== 1")


CAP_ROLES = {
    # role: (pool, capability, ON claim, mistake id, why students, why wrong)
    "ox_any": (OX_ONLY, "oxidant_only", None, "-", "-", "-"),
    "ox_only": (OX_POS, "oxidant_only", "> 0", "HIGHEST_STATE_ONLY_OXIDANT",
                "Students pick a familiar strong oxidant.", "Its element is at its highest state: it can only be "
                "reduced, never oxidised."),
    "red_only": (RED_NEG, "reductant_only", "< 0", "LOWEST_STATE_ONLY_REDUCTANT",
                 "Students reverse the roles of the highest and lowest oxidation states.",
                 "At its lowest state the element can only lose electrons (only a reducing agent)."),
    "both_high": (BOTH_HIGH, "both", ">= 3", "HIGH_ON_BUT_NOT_MAXIMUM",
                  "Students think any high positive oxidation number means 'only oxidant'.",
                  "The element is below its maximum state, so it can still be oxidised further."),
    "both_low": (BOTH_LOW, "both", "<= 0", "FAMOUS_OXIDANT_INTERMEDIATE_STATE",
                 "Students remember it as a well-known oxidising agent.",
                 "Its element is in an intermediate state, so it can also be oxidised (it acts both ways)."),
    "both_neg": (BOTH_NEG, "both", "< 0", "NEGATIVE_ON_BUT_NOT_MINIMUM",
                 "Students think any negative oxidation number means 'only reductant'.",
                 "The element is above its minimum state, so it can still be reduced."),
    "both_pos": (BOTH_POS, "both", "> 0", "FAMOUS_REDUCTANT_INTERMEDIATE_STATE",
                 "Students remember it as a well-known reducing agent.",
                 "Its element is in an intermediate state, so it can also be reduced (it acts both ways)."),
    "zero_ox": (ZERO_OX, "oxidant_only", "== 0", "ZERO_STATE_ASSUMED_INTERMEDIATE",
                "Students assume an element in the free (0) state can always go both ways.",
                "Fluorine has no positive oxidation states, so F2 can only be reduced."),
    "zero_red": (ZERO_RED, "reductant_only", "== 0", "ZERO_STATE_ASSUMED_INTERMEDIATE",
                 "Students assume an element in the free (0) state can always go both ways.",
                 "Metals have no negative oxidation states, so the free metal can only be oxidised."),
    "red_any": (RED_ONLY, "reductant_only", None, "-", "-", "-"),
    "red_neg": (RED_NEG, "reductant_only", "< 0", "LOWEST_STATE_ONLY_REDUCTANT",
                "Students pick a familiar reducing agent.", "At its lowest state it can only be oxidised."),
}
CAP_ASK = {"oxidant_only": ("only as an oxidising agent", ["ox_any", "red_only", "both_high", "both_low"]),
           "reductant_only": ("only as a reducing agent", ["red_any", "ox_only", "both_neg", "both_pos"]),
           "both": ("both as an oxidising and as a reducing agent", ["both_any", "ox_only", "red_neg", "zero"])}


def capability() -> Family:
    def sample(rng):
        ask = rng.choice(list(CAP_ASK))
        roles = list(CAP_ASK[ask][1])
        if "both_any" in roles:
            roles[0] = rng.choice(["both_high", "both_low", "both_pos", "both_neg"])
            roles[3] = rng.choice(["zero_ox", "zero_red"])
        while True:
            items = [dict(zip(("species", "element"), rng.choice(CAP_ROLES[r][0])), role=r) for r in roles]
            if len({i["species"] for i in items}) == 4:
                break
        rng.shuffle(items)
        for it in items:
            it["html"] = f"{sp_html(it['species'])} (for {it['element']})"
        return {"ask": ask, "items": items}

    def _by_role(p, role):
        _, cap, claim, *_ = CAP_ROLES[role]
        return per_option(lambda it: _cap(it, cap, claim), p["items"])

    def formal(p):
        return per_option(lambda it: SUB(RX("capability", species=it["species"], element=it["element"]),
                                         f"== {p['ask']}"), p["items"])

    def stem(p):
        return (f"<p>Considering only the oxidation state of the element given in brackets, which of the following "
                f"can act <b>{CAP_ASK[p['ask']][0]}</b>?</p>")

    def mistakes(p):
        out = []
        for it in p["items"]:
            if CAP_ROLES[it["role"]][1] == p["ask"]:
                continue
            _, _, _, mid, ws, ww = CAP_ROLES[it["role"]]
            out.append(Mistake(mid, _by_role(p, it["role"]), ws, ww))
        return out

    def explain(p, v):
        it = p["items"][set_val(v) - 1]
        return ("<p>An element at its highest oxidation state can only be reduced (only oxidant); at its lowest "
                "state it can only be oxidised (only reductant); in between it can do both.</p>"
                f"<p>Answer: {it['html']}.</p>")

    return Family(id="redox.capability", subject=SUBJ, chapter=CH, topic="Oxidising And Reducing Agents",
                  difficulty="EASY", sample=sample, formal=formal, stem=stem, mistakes=mistakes, explain=explain,
                  display=set_disp_factory("items"),
                  modelled_on=["vlhjHX6yKGZg6V7YU07k9k2k5idmyit", "jaoe38c1lscrqpvw", "lvb29icb"]).register()


ON_COMMON = on_common()
ON_TRICKY = on_tricky()
ON_SUM = on_sum()
BALANCE_COEFF = balance_coeff()
ELECTRONS = electrons()
EQ_WEIGHT = eq_weight()
TITRATION_VOLUME = titration_volume()
TITRATION_MASS = titration_mass()
REACTION_TYPE = reaction_type()
CAPABILITY = capability()
