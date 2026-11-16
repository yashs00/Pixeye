"""Chemistry engine (blueprint 8, 37.3) - quantitative pilot: stoichiometry.

IMPORTANT LIMIT: atom/charge balance is necessary, NOT sufficient. It never
proves that a reaction occurs or that a product is major. Every reaction-based
item therefore carries a hard 'chem.reaction_feasibility' check that stays
UNRESOLVED until a source-backed rule or a qualified chemist confirms it.

kind = "stoichiometry":
    {"kind": "stoichiometry",
     "reaction": "2 H2 + O2 -> 2 H2O",          # coefficients optional; verified
     "given": {"H2": {"mass_g": "4"}, "O2": {"mass_g": "48"}},
     "atomic_masses": {"H": "1", "O": "16"},     # values STATED IN THE STEM
     "target": {"species": "H2O", "quantity": "mass_g" | "moles"},
     "reaction_source": "NCERT Class 11 Ch.1 ..." (optional rule reference)}
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord, guarded

TOOL = f"cqse-chem 0.1; sympy {sp.__version__}"

ELEMENTS = set("""H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se
Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu
Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu""".split())

_TOKEN = re.compile(r"([A-Z][a-z]?)|(\d+)|([()\[\]])|(\S)")


class FormulaError(ValueError):
    pass


@dataclass
class Species:
    text: str
    atoms: dict[str, int]
    charge: int


def parse_formula(text: str) -> Species:
    """Parse e.g. 'H2O', 'Ca(OH)2', 'CuSO4.5H2O', 'SO4^2-', 'Fe^3+', 'e^-'."""
    t = text.strip()
    charge = 0
    m = re.fullmatch(r"(.+?)\^(\d*)([+-])", t)
    if m:
        t, mag, sign = m.group(1), m.group(2), m.group(3)
        charge = (int(mag) if mag else 1) * (1 if sign == "+" else -1)
    if t == "e":
        return Species(text, {}, charge if m else -1)
    total: dict[str, int] = {}
    for part_i, part in enumerate(re.split(r"[.·*]", t)):
        mult = 1
        mm = re.match(r"^(\d+)(.*)$", part)
        if mm and part_i > 0:
            mult, part = int(mm.group(1)), mm.group(2)
        for el, n in _parse_group(part).items():
            total[el] = total.get(el, 0) + n * mult
    if not total:
        raise FormulaError(f"empty formula {text!r}")
    return Species(text, total, charge)


def _parse_group(s: str) -> dict[str, int]:
    stack: list[dict[str, int]] = [{}]
    toks = [m for m in _TOKEN.finditer(s)]
    i = 0
    while i < len(toks):
        el, num, br, bad = toks[i].groups()
        if bad:
            raise FormulaError(f"unexpected character {bad!r} in {s!r}")
        if el:
            if el not in ELEMENTS:
                raise FormulaError(f"unknown element {el!r}")
            n = 1
            if i + 1 < len(toks) and toks[i + 1].group(2):
                n = int(toks[i + 1].group(2))
                i += 1
            stack[-1][el] = stack[-1].get(el, 0) + n
        elif br in "([":
            stack.append({})
        elif br in ")]":
            if len(stack) == 1:
                raise FormulaError(f"unbalanced brackets in {s!r}")
            grp = stack.pop()
            n = 1
            if i + 1 < len(toks) and toks[i + 1].group(2):
                n = int(toks[i + 1].group(2))
                i += 1
            for k, v in grp.items():
                stack[-1][k] = stack[-1].get(k, 0) + v * n
        elif num:
            raise FormulaError(f"stray number in {s!r}")
        i += 1
    if len(stack) != 1:
        raise FormulaError(f"unbalanced brackets in {s!r}")
    return stack[0]


@dataclass
class Reaction:
    reactants: list[tuple[Optional[int], Species]]
    products: list[tuple[Optional[int], Species]]

    @property
    def species(self) -> list[Species]:
        return [s for _, s in self.reactants + self.products]


def parse_reaction(text: str) -> Reaction:
    if "->" not in text:
        raise FormulaError("reaction must contain '->'")
    lhs, rhs = text.split("->", 1)

    def side(s: str):
        out = []
        for term in [p.strip() for p in re.split(r"\s\+\s", f" {s.strip()} ") if p.strip()]:
            m = re.match(r"^(\d+)\s+(.+)$", term) or re.match(r"^(\d+)([A-Z(\[].*)$", term)
            coef, f = (int(m.group(1)), m.group(2)) if m else (None, term)
            if coef == 0:
                raise FormulaError("zero coefficient")
            out.append((coef, parse_formula(f)))
        if not out:
            raise FormulaError("empty side")
        return out

    return Reaction(side(lhs), side(rhs))


def balance(rx: Reaction) -> list[int]:
    """Exact balancing via nullspace. Raises if the balancing is not unique (up to scale)."""
    sp_list = rx.species
    elements = sorted({e for s in sp_list for e in s.atoms})
    rows = []
    nr = len(rx.reactants)
    for e in elements:
        rows.append([s.atoms.get(e, 0) * (1 if i < nr else -1) for i, s in enumerate(sp_list)])
    rows.append([s.charge * (1 if i < nr else -1) for i, s in enumerate(sp_list)])
    ns = sp.Matrix(rows).nullspace()
    if len(ns) != 1:
        raise FormulaError(f"balancing not unique ({len(ns)} independent solutions) - ambiguous reaction")
    v = ns[0]
    lcm = sp.ilcm(*[sp.fraction(x)[1] for x in v])
    v = [int(x * lcm) for x in v]
    if all(x < 0 for x in v):
        v = [-x for x in v]
    if any(x <= 0 for x in v):
        raise FormulaError(f"no all-positive balancing: {v}")
    g = 0
    for x in v:
        g = sp.igcd(g, x)
    return [x // g for x in v]


def balance_report(rx: Reaction, coeffs: list[int]) -> tuple[bool, list[str]]:
    nr = len(rx.reactants)
    problems = []
    elements = sorted({e for s in rx.species for e in s.atoms})
    for e in elements:
        l = sum(c * s.atoms.get(e, 0) for c, s in zip(coeffs[:nr], rx.species[:nr]))
        r = sum(c * s.atoms.get(e, 0) for c, s in zip(coeffs[nr:], rx.species[nr:]))
        if l != r:
            problems.append(f"{e}: {l} vs {r}")
    lc = sum(c * s.charge for c, s in zip(coeffs[:nr], rx.species[:nr]))
    rc = sum(c * s.charge for c, s in zip(coeffs[nr:], rx.species[nr:]))
    if lc != rc:
        problems.append(f"charge: {lc} vs {rc}")
    return not problems, problems


def molar_mass(sp_: Species, masses: dict[str, Fraction]) -> Fraction:
    missing = [e for e in sp_.atoms if e not in masses]
    if missing:
        raise FormulaError(f"atomic mass not stated for {missing} - refusing to assume a value")
    return sum((masses[e] * n for e, n in sp_.atoms.items()), Fraction(0))


def _frac(s: str) -> Fraction:
    f = Fraction(str(s))
    if f <= 0:
        raise FormulaError(f"non-positive quantity {s}")
    return f


@dataclass
class ChemSolution:
    value: Optional[Fraction] = None
    units: str = ""
    coeffs: list[int] = field(default_factory=list)
    limiting: Optional[str] = None
    records: list[VerificationRecord] = field(default_factory=list)


def solve_and_verify(formal: dict) -> ChemSolution:
    out = ChemSolution()
    st: dict = {}
    if formal.get("kind") != "stoichiometry":
        out.records.append(VerificationRecord(check_id="chem.structure", status=CheckStatus.UNRESOLVED,
                                              method="schema", result=f"unsupported kind {formal.get('kind')!r}"))
        return out

    def _parse():
        rx = parse_reaction(formal["reaction"])
        st["rx"] = rx
        st["masses"] = {k: _frac(v) for k, v in formal.get("atomic_masses", {}).items()}
        names = [s.text for s in rx.species]
        if len(set(names)) != len(names):
            raise FormulaError("species repeated in reaction")
        for k in formal.get("given", {}):
            if k not in names[:len(rx.reactants)]:
                raise FormulaError(f"given species {k} is not a reactant")
        if formal["target"]["species"] not in names:
            raise FormulaError("target species not in reaction")
        return VerificationRecord(check_id="chem.structure", status=CheckStatus.EXACT_CHECKED,
                                  method="formula/reaction parse", tool=TOOL, result=f"{len(names)} species")

    out.records.append(guarded("chem.structure", _parse))
    if "rx" not in st:
        return out
    rx: Reaction = st["rx"]

    def _balance():
        derived = balance(rx)
        given = [c for c, _ in rx.reactants + rx.products]
        st["coeffs"] = derived
        if any(c is not None for c in given):
            # Once any coefficient is written, an omitted one means 1 (as printed to students).
            given = [1 if c is None else c for c in given]
            ok, probs = balance_report(rx, given)
            if not ok:
                return VerificationRecord(check_id="chem.balance", status=CheckStatus.FAILED,
                                          method="atom + charge conservation", tool=TOOL,
                                          result=f"stated equation unbalanced: {probs}; balanced form {derived}")
            g = 0
            for c in given:
                g = sp.igcd(g, c)
            if [c // g for c in given] != derived:
                return VerificationRecord(check_id="chem.balance", status=CheckStatus.FAILED,
                                          method="atom + charge conservation", result="inconsistent coefficients")
            st["coeffs"] = given
        ok, probs = balance_report(rx, st["coeffs"])
        return VerificationRecord(check_id="chem.balance",
                                  status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                  method="unique nullspace balance + atom/charge recount", tool=TOOL,
                                  result=f"coefficients {st['coeffs']}" + ("" if ok else f" {probs}"))

    out.records.append(guarded("chem.balance", _balance))

    src = formal.get("reaction_source")
    out.records.append(VerificationRecord(
        check_id="chem.reaction_feasibility",
        status=CheckStatus.UNRESOLVED,
        method="source-backed rule / expert confirmation required",
        result=(f"cites '{src}' - awaiting expert confirmation" if src
                else "no source cited; balance does not prove the reaction occurs"),
        limitations=["atom balance is necessary, not sufficient"]))

    if "coeffs" not in st or out.records[-2].status != CheckStatus.EXACT_CHECKED:
        return out
    coeffs, masses = st["coeffs"], st["masses"]
    names = [s.text for s in rx.species]
    by_name = dict(zip(names, rx.species))
    coef = dict(zip(names, coeffs))
    tgt = formal["target"]

    def _moles(name: str, spec: dict) -> Fraction:
        if "moles" in spec:
            return _frac(spec["moles"])
        if "mass_g" in spec:
            return _frac(spec["mass_g"]) / molar_mass(by_name[name], masses)
        raise FormulaError(f"no quantity for {name}")

    def _method_a():
        """Extent-of-reaction: xi = min(n_i / nu_i); limiting = argmin (ties reported)."""
        given = formal["given"]
        ratios = {k: _moles(k, v) / coef[k] for k, v in given.items()}
        xi = min(ratios.values())
        lim = sorted(k for k, r in ratios.items() if r == xi)
        n_t = xi * coef[tgt["species"]]
        if tgt["species"] in given:  # asking leftover of a reactant
            n_t = _moles(tgt["species"], given[tgt["species"]]) - xi * coef[tgt["species"]]
        val = n_t if tgt["quantity"] == "moles" else n_t * molar_mass(by_name[tgt["species"]], masses)
        st["A"], st["lim"] = val, lim
        return VerificationRecord(check_id="chem.solve.primary", status=CheckStatus.EXACT_CHECKED,
                                  method="extent of reaction (exact rationals)", tool=TOOL,
                                  result=f"limiting {lim}; {tgt['species']} {tgt['quantity']} = {val}")

    def _method_b():
        """Independent: try each reactant as limiting, keep the scenario that
        never consumes more of any reactant than available."""
        given = formal["given"]
        avail = {k: _moles(k, v) for k, v in given.items()}
        feasible = []
        for cand in given:
            xi = avail[cand] / coef[cand]
            if all(xi * coef[k] <= avail[k] for k in given):
                feasible.append((cand, xi))
        xis = {xi for _, xi in feasible}
        if len(xis) != 1:
            raise RuntimeError(f"no unique feasible extent: {feasible}")
        xi = xis.pop()
        s = tgt["species"]
        n_t = avail[s] - xi * coef[s] if s in given else xi * coef[s]
        val = n_t if tgt["quantity"] == "moles" else n_t * molar_mass(by_name[s], masses)
        ok = val == st.get("A")
        return VerificationRecord(check_id="chem.solve.independent",
                                  status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.UNRESOLVED,
                                  method="enumerate limiting-reagent scenarios with feasibility test", tool=TOOL,
                                  result=f"value {val}; agreement={ok}")

    def _mass_conservation():
        """Mass of reactants consumed equals mass of products formed at extent xi."""
        given = formal["given"]
        xi = min(_moles(k, v) / coef[k] for k, v in given.items())
        nr = len(rx.reactants)
        mr = sum(xi * coef[n] * molar_mass(by_name[n], masses) for n in names[:nr])
        mp = sum(xi * coef[n] * molar_mass(by_name[n], masses) for n in names[nr:])
        return VerificationRecord(check_id="chem.mass_conservation",
                                  status=CheckStatus.EXACT_CHECKED if mr == mp else CheckStatus.FAILED,
                                  method="mass consumed vs mass formed", tool=TOOL, result=f"{mr} g vs {mp} g")

    out.records.append(guarded("chem.solve.primary", _method_a))
    if "A" in st:
        out.records.append(guarded("chem.solve.independent", _method_b))
        out.records.append(guarded("chem.mass_conservation", _mass_conservation))
        out.value, out.limiting = st["A"], ",".join(st["lim"])
        out.units = "g" if tgt["quantity"] == "mass_g" else "mol"
    out.coeffs = coeffs
    return out


def misconceptions(formal: dict) -> list[tuple[str, Fraction, list[str], str, str]]:
    rx = parse_reaction(formal["reaction"])
    coeffs = balance(rx)
    names = [s.text for s in rx.species]
    by_name, coef = dict(zip(names, rx.species)), dict(zip(names, coeffs))
    masses = {k: Fraction(str(v)) for k, v in formal["atomic_masses"].items()}
    given, tgt = formal["given"], formal["target"]
    s = tgt["species"]
    if s in given:
        return []
    M = {n: molar_mass(by_name[n], masses) for n in names}

    def mol(k, v):
        return Fraction(str(v["moles"])) if "moles" in v else Fraction(str(v["mass_g"])) / M[k]

    def finish(n):
        return n if tgt["quantity"] == "moles" else n * M[s]

    out = []
    avail = {k: mol(k, v) for k, v in given.items()}
    # 1. limiting = smallest number of moles, ignoring coefficients
    lim_wrong = min(avail, key=lambda k: avail[k])
    out.append(("CHEM.STOICH.LIMITING_BY_MOLES", finish(avail[lim_wrong] / coef[lim_wrong] * coef[s]),
                [f"Pick {lim_wrong} as limiting because it has the fewest moles (ignores coefficients)"],
                "Compares raw moles instead of moles/coefficient.",
                "Limiting reagent is the smallest n/nu, not the smallest n."))
    # 2. ignore stoichiometric coefficients (1:1 assumed)
    xi = min(avail.values())
    out.append(("CHEM.STOICH.IGNORE_COEFFICIENTS", finish(xi),
                ["Assume all species react 1:1 (ignores coefficients)"],
                "Uses an unbalanced or 1:1 mole ratio.", "Mole ratios come from the balanced equation."))
    # 3. limiting reagent chosen by smallest given mass
    if all("mass_g" in v for v in given.values()):
        lm = min(given, key=lambda k: Fraction(str(given[k]["mass_g"])))
        out.append(("CHEM.STOICH.LIMITING_BY_MASS", finish(avail[lm] / coef[lm] * coef[s]),
                    [f"Pick {lm} as limiting because its mass is smallest"],
                    "Uses mass instead of moles to find limiting reagent.",
                    "Reacting amounts are compared in moles (scaled by coefficients)."))
    # 4. use the excess reagent
    ratios = {k: avail[k] / coef[k] for k in avail}
    ex = max(ratios, key=lambda k: ratios[k])
    out.append(("CHEM.STOICH.USE_EXCESS", finish(ratios[ex] * coef[s]),
                [f"Base the calculation on {ex} (the excess reagent)"],
                "Uses the reagent in excess.", "Product is limited by the limiting reagent."))
    # 5. all reactant mass becomes the target product
    if tgt["quantity"] == "mass_g" and all("mass_g" in v for v in given.values()):
        total = sum(Fraction(str(v["mass_g"])) for v in given.values())
        out.append(("CHEM.MASS.TOTAL_REACTANT_MASS", total,
                    ["Add the masses of all reactants", "Assume all of it becomes the product (error)"],
                    "Misapplies conservation of mass, ignoring the excess reagent left over.",
                    "Only the reacting amounts (set by the limiting reagent) are converted."))
    # 6. reports moles where grams are asked
    if tgt["quantity"] == "mass_g":
        n_correct = min(ratios.values()) * coef[s]
        out.append(("CHEM.UNITS.MOLES_AS_GRAMS", n_correct,
                    ["Find moles of product correctly", "Report the mole number as the mass (error)"],
                    "Stops after finding moles; forgets to multiply by molar mass.",
                    "Mass = moles x molar mass."))
    return out
