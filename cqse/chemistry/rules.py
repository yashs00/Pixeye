"""Chemistry rule engine (kind = "chem_property"): versioned, table-driven, fail-closed.

Every value is derived from the versioned rule set RULESET (NCERT XI/XII conventions) and, wherever two
methods exist, by two independent computations that must agree:

  * electron configuration    Madelung (n+l) filling  AND  period/block construction; exceptions are an
                              explicit table (Cr Cu Nb Mo Ru Rh Pd Ag La Ce Gd Pt Au), never Aufbau alone
  * unpaired electrons        closed formula per subshell  AND  explicit Hund's-rule box filling
  * VSEPR steric number       formula count  1/2(V + M - T - q)  AND  explicit Lewis-structure electron count
  * dipole zero / non-zero    symmetry-class table  AND  vector sum of symbolic bond/lone-pair dipoles over
                              every distinct ligand placement on the idealised VSEPR geometry
  * linear yes/no             shape table  AND  collinearity of the bond vectors
  * MO unpaired electrons     closed formula per level  AND  Hund box filling; heteronuclear diatomics
                              must give the same answer under BOTH level orderings (else UNRESOLVED)
  * LCAO symmetry match       symmetry-label table  AND  azimuthal integral of the angular product
  * molar mass                cqse.chemistry.engine.parse_formula  AND  an independent formula parser
  * half-reaction n           given n  AND  oxidation-state change (when computable)

Anything outside the rule tables (unknown species, transition-metal centres in VSEPR, organic species,
ambiguous central atom, Z > 86 ...) is UNRESOLVED - never guessed.

Formal schema
-------------
{"kind": "chem_property", "query": <query>, ..., "premises": [PREMISE, ...]}   # premises optional

PREMISE = {"statement": "C is Na2Cr2O7 (dichromate)", "basis": "curated", "note": "..."}
    -> a hard UNRESOLVED, expert-resolvable record "chem.reaction_feasibility" (teacher confirms the
       descriptive identification that the stem requires); the computed part stays RULE_CHECKED.

Queries (a "sub-query" is any of these dicts without "kind"):
  value    {"query": "value", "property": P, "species": S, [params...], ["round_to": "0.1"]}
  approx   {"query": "approx", "property": P, "species": S, "target": "2.84", "tol": "0.02"} -> 1 / 0
  count    {"query": "count", "property": P, "species": [S, ...], "claim": "== linear"} -> Integer
  select   {"query": "select", "property": P, "species": {"A": S, ...}, "claim": "== 4"}
                                            -> FiniteSet of label indices (A/I/1 -> 1 ...)
  all      {"query": "all", "checks": [SUBQ + {"claim": ...} | {"curated": bool, "note": ...}]} -> 1 / 0
  all_equal {"query": "all_equal", "property": P, "species": [S, ...]} -> 1 / 0
  expr     {"query": "expr", "terms": {"x": SUBQ, "y": SUBQ}, "expr": "x + y"}
  pick     {"query": "pick", "species": [S...], "where": [{"property": P, "claim": C}],
            "maximize" | "minimize": P, "then": {"property": P2, "species_template": "{X}^2+"},
            ["return": "label"]}   -> value of P2 for the UNIQUE optimum (ties -> UNRESOLVED)
  extremum {"query": "extremum", "select": "max"|"min", "values": {"A": SUBQ | "1.15", ...}} -> {label}
  redox_extremum {"query": "redox_extremum", "role": "oxidising"|"reducing",
            "couples": [{"ox": "Cr^3+", "red": "Cr", "E": "-0.74"}, ...], "candidates": {"A": "Cr", ...}}
            -> {label}: strongest oxidant = ox form of the couple with highest E; strongest reductant =
               red form of the couple with lowest E; a candidate that is never in the needed role is excluded
  combine_potentials {"query": "combine_potentials",
            "couples": [{"ox": "Fe^3+", "red": "Fe", "n": 3, "E": "z"}, ...],   # E may be symbolic
            "target": {"ox": .., "red": ..} | "cell": {"cathode": {"ox","red"}, "anode": {"ox","red"}}}
            -> E of the target couple (dG additivity, -nFE) or E_cell = E_cathode - E_anode
  cell     {"query": "cell", "cathode": {"ox","red","E"}, "anode": {"ox","red","E"},
            "return": "E" | "n" | "deltaG_over_F"}
  nernst   {"query": "nernst", "cathode": {"ox","red"}, "anode": {"ox","red"},
            "symbols": {"Mg^2+": "Mg", "Ag^+": "Ag"}}  -> E - E0 = -(R*T/(n*F)) * ln Q (expanded logs)

Properties P (species S as text, e.g. "Fe^3+", "XeOF4", "N3^-", "O2^-"):
  atoms/ions   electron_configuration (string, steps only) | subshell_electrons (param "subshell": "4d")
               | unpaired_electrons | spin_only_moment (BM, exact sqrt(n(n+2))) | paramagnetic (1/0)
               | oct_config_ligand_independent (1/0: high-spin == low-spin d^n in Oh)
               | aq_colour (Symbol; NCERT XII table of aquated 3d ions)
               | enthalpy_atomisation (kJ/mol; NCERT XII Table 8.2, 3d metals)
  VSEPR        steric_number | bond_pairs (sigma) | lone_pairs | lone_pairs_equatorial (SN 5 only)
               | shape (Symbol: linear bent trigonal_planar tetrahedral trigonal_pyramidal
                 trigonal_bipyramidal see_saw T_shaped octahedral square_pyramidal square_planar
                 pentagonal_bipyramidal pentagonal_pyramidal) | hybridization (Symbol sp sp2 sp3 sp3d sp3d2 sp3d3)
               | dipole_nonzero (1/0) | is_linear (1/0) | bond_sites_inequivalent (1/0)
  Lewis        bond_pairs_total (sigma + pi; period>=3 centres use the formal-charge-minimised, expanded
                 octet structure - NCERT convention, recorded as an assumption)
               | lewis_nonbonded_electrons (whole species; period-2 centre or no pi bonds only)
               | octet_class (Symbol: obeys incomplete odd expanded) | valence_electrons_total
  MO           bond_order | mo_unpaired_electrons | paramagnetic
  other        molar_mass (g/mol; param "atomic_masses" = values stated in the stem, else IUPAC table)
               | oxidation_state (param "element") | dna_duplex_hbonds (species = one strand "GGCAT...")
               | lcao_symmetry_match (species "2pz|2px" -> 1/0) | terminal_oxygens | bridging_oxygens
"""
from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from functools import reduce
from typing import Any, Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.core.result import EngineResult

RULESET = "cqse-chem-rules 1.0 (NCERT XI/XII conventions)"
TOOL = f"cqse.chemistry.rules 1.0; {RULESET}; sympy {sp.__version__}"


class RuleError(ValueError):
    """Outside the rule tables or methods disagree -> UNRESOLVED (never guessed)."""


# =============================================================================== periodic data
SYMBOLS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
           "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm "
           "Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn").split()
assert len(SYMBOLS) == 86
Z_OF = {s: i + 1 for i, s in enumerate(SYMBOLS)}
L_LETTER = "spdf"

# Ground-state exceptions to (n+l) filling, Z <= 86 (NCERT XI Ch.2 / XII Ch.8 tables). Only the listed
# subshells are overridden; the total is re-checked against Z.
CONFIG_EXCEPTIONS: dict[str, dict[str, int]] = {
    "Cr": {"3d": 5, "4s": 1}, "Cu": {"3d": 10, "4s": 1},
    "Nb": {"4d": 4, "5s": 1}, "Mo": {"4d": 5, "5s": 1}, "Ru": {"4d": 7, "5s": 1}, "Rh": {"4d": 8, "5s": 1},
    "Pd": {"4d": 10, "5s": 0}, "Ag": {"4d": 10, "5s": 1},
    "La": {"4f": 0, "5d": 1}, "Ce": {"4f": 1, "5d": 1}, "Gd": {"4f": 7, "5d": 1},
    "Pt": {"5d": 9, "6s": 1}, "Au": {"5d": 10, "6s": 1},
}

PAULING_EN = {"H": 2.20, "Li": 0.98, "Be": 1.57, "B": 2.04, "C": 2.55, "N": 3.04, "O": 3.44, "F": 3.98,
              "Na": 0.93, "Mg": 1.31, "Al": 1.61, "Si": 1.90, "P": 2.19, "S": 2.58, "Cl": 3.16, "Ar": None,
              "Ga": 1.81, "Ge": 2.01, "As": 2.18, "Se": 2.55, "Br": 2.96, "Kr": 3.00, "In": 1.78, "Sn": 1.96,
              "Sb": 2.05, "Te": 2.10, "I": 2.66, "Xe": 2.60, "Tl": 1.62, "Pb": 2.33, "Bi": 2.02}

# IUPAC abridged standard atomic weights (2021), g/mol.
ATOMIC_MASS = {"H": "1.008", "He": "4.0026", "Li": "6.94", "Be": "9.0122", "B": "10.81", "C": "12.011",
               "N": "14.007", "O": "15.999", "F": "18.998", "Ne": "20.180", "Na": "22.990", "Mg": "24.305",
               "Al": "26.982", "Si": "28.085", "P": "30.974", "S": "32.06", "Cl": "35.45", "Ar": "39.95",
               "K": "39.098", "Ca": "40.078", "Sc": "44.956", "Ti": "47.867", "V": "50.942", "Cr": "51.996",
               "Mn": "54.938", "Fe": "55.845", "Co": "58.933", "Ni": "58.693", "Cu": "63.546", "Zn": "65.38",
               "Br": "79.904", "Ag": "107.87", "Sn": "118.71", "I": "126.90", "Ba": "137.33", "Pb": "207.2",
               "Hg": "200.59", "Au": "196.97", "Pt": "195.08", "Xe": "131.29", "Kr": "83.798"}

# NCERT XII Ch.8 Table 8.2: enthalpy of atomisation (kJ/mol), 3d series.
ENTHALPY_ATOMISATION_3D = {"Sc": 326, "Ti": 473, "V": 515, "Cr": 397, "Mn": 281, "Fe": 416, "Co": 425,
                           "Ni": 430, "Cu": 339, "Zn": 126}

# NCERT XII Ch.8 table "Colours of some of the first row (aquated) transition metal ions".
AQ_COLOUR = {"Sc^3+": "colourless", "Ti^4+": "colourless", "Ti^3+": "purple", "V^4+": "blue", "V^3+": "green",
             "V^2+": "violet", "Cr^3+": "violet", "Mn^3+": "violet", "Cr^2+": "blue", "Mn^2+": "pink",
             "Fe^3+": "yellow", "Fe^2+": "green", "Co^3+": "blue", "Co^2+": "pink", "Ni^2+": "green",
             "Cu^2+": "blue", "Zn^2+": "colourless"}

# Oxoanion connectivity: number of MO4 tetrahedra sharing corners in a chain (pyro-anions share one O).
OXO_TETRAHEDRA = {"CrO4^2-": ("Cr", 1), "Cr2O7^2-": ("Cr", 2), "SO4^2-": ("S", 1), "S2O7^2-": ("S", 2),
                  "MnO4^-": ("Mn", 1), "MnO4^2-": ("Mn", 1), "PO4^3-": ("P", 1), "P2O7^4-": ("P", 2)}

# Explicit structures for species whose connectivity is not "central atom + terminal atoms".
STRUCTURES = {"H2SO4": ("S", ["O", "O", "OH", "OH"]), "H2SO3": ("S", ["O", "OH", "OH"]),
              "HNO3": ("N", ["O", "O", "OH"]), "H3PO4": ("P", ["O", "OH", "OH", "OH"]),
              "HClO4": ("Cl", ["O", "O", "O", "OH"])}

POLYATOMIC = [({"S": 1, "O": 4}, -2), ({"N": 1, "O": 3}, -1), ({"C": 1, "O": 3}, -2), ({"P": 1, "O": 4}, -3),
              ({"O": 1, "H": 1}, -1), ({"N": 1, "H": 4}, 1)]


def _species(text: str):
    from cqse.chemistry.engine import FormulaError, parse_formula
    try:
        s = parse_formula(text)
    except FormulaError as e:
        raise RuleError(f"cannot parse species {text!r}: {e}")
    for el in s.atoms:
        if el not in Z_OF:
            raise RuleError(f"element {el} (Z > 86) outside rule tables")
    return s


def _sub(n: int, l: int) -> str:
    return f"{n}{L_LETTER[l]}"


def _parse_sub(t: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d)([spdf])", t.strip())
    if not m:
        raise RuleError(f"bad subshell {t!r}")
    return int(m.group(1)), L_LETTER.index(m.group(2))


# =============================================================================== electron configurations
def _madelung(Z: int) -> dict[tuple[int, int], int]:
    order = sorted(((n, l) for n in range(1, 8) for l in range(0, min(n, 4))), key=lambda t: (t[0] + t[1], t[0]))
    conf, left = {}, Z
    for n, l in order:
        if left <= 0:
            break
        k = min(left, 2 * (2 * l + 1))
        conf[(n, l)] = k
        left -= k
    return conf


def _block_construction(Z: int) -> dict[tuple[int, int], int]:
    """Independent construction: period by period, ns -> (n-2)f -> (n-1)d -> np."""
    conf, left = {}, Z
    for p in range(1, 8):
        seq = [(p, 0)]
        if p >= 6:
            seq.append((p - 2, 3))
        if p >= 4:
            seq.append((p - 1, 2))
        if p >= 2:
            seq.append((p, 1))
        for n, l in seq:
            if left <= 0:
                return conf
            k = min(left, 2 * (2 * l + 1))
            conf[(n, l)] = k
            left -= k
    return conf


def _apply_exceptions(sym: str, conf: dict) -> dict:
    conf = dict(conf)
    for t, k in CONFIG_EXCEPTIONS.get(sym, {}).items():
        conf[_parse_sub(t)] = k
    return {k: v for k, v in conf.items() if v > 0}


def atom_config(sym: str, ctx: "Ctx") -> dict[tuple[int, int], int]:
    if sym not in Z_OF:
        raise RuleError(f"{sym}: outside Z = 1..86")
    Z = Z_OF[sym]
    a = _apply_exceptions(sym, _madelung(Z))
    b = _apply_exceptions(sym, _block_construction(Z))
    if a != b or sum(a.values()) != Z:
        raise RuleError(f"{sym}: configuration methods disagree ({fmt_config(a)} vs {fmt_config(b)})")
    ctx.cross(f"config {sym}: Madelung == block construction"
              + (" (tabulated exception applied)" if sym in CONFIG_EXCEPTIONS else ""))
    return a


def _removal_key(nl: tuple[int, int]) -> tuple[float, int]:
    n, l = nl
    eff = n + {0: 0.0, 1: 0.0, 2: 0.6, 3: 1.5}[l]   # ns,np > (n-1)d > (n-2)f > core
    return (eff, l)


def ion_config(text: str, ctx: "Ctx") -> tuple[str, int, dict]:
    s = _species(text)
    if len(s.atoms) != 1 or list(s.atoms.values())[0] != 1:
        raise RuleError(f"{text}: not a single atom/monatomic ion")
    sym = next(iter(s.atoms))
    conf = atom_config(sym, ctx)
    q = s.charge
    if q > 0:
        for _ in range(q):
            occ = [k for k, v in conf.items() if v > 0]
            if not occ:
                raise RuleError(f"{text}: removes more electrons than present")
            top = max(occ, key=_removal_key)
            conf[top] -= 1
        ctx.step(f"{text}: electrons removed from outermost ns/np first, then (n-1)d, then (n-2)f")
    elif q < 0:
        if any(l >= 2 and v < 2 * (2 * l + 1) for (n, l), v in conf.items()):
            raise RuleError(f"{text}: anion of an open d/f-shell element outside rule tables")
        conf = _madelung(Z_OF[sym] - q)
        ctx.step(f"{text}: added electrons follow (n+l) filling")
    conf = {k: v for k, v in conf.items() if v > 0}
    return sym, q, conf


NOBLE = [(2, "He"), (10, "Ne"), (18, "Ar"), (36, "Kr"), (54, "Xe"), (86, "Rn")]


def fmt_config(conf: dict) -> str:
    return " ".join(f"{_sub(n, l)}{v}" for (n, l), v in sorted(conf.items()) if v)


def unpaired(conf: dict, ctx: "Ctx", label: str) -> int:
    m1 = 0
    for (n, l), e in conf.items():
        k = 2 * l + 1
        m1 += e if e <= k else 2 * k - e
    m2 = 0
    for (n, l), e in conf.items():
        boxes = [0] * (2 * l + 1)
        for i in range(e):                 # Hund: singly fill every box (parallel spins), then pair
            boxes[i % len(boxes)] += 1
        m2 += sum(1 for b in boxes if b == 1)
    if m1 != m2:
        raise RuleError(f"{label}: unpaired-electron methods disagree ({m1} vs {m2})")
    ctx.cross(f"unpaired e- of {label}: subshell formula == Hund box filling == {m1}")
    return m1


# =============================================================================== VSEPR / Lewis
NEED = {"H": 1, "F": 1, "Cl": 1, "Br": 1, "I": 1, "OH": 1, "O": 2, "S": 2, "Se": 2, "N": 3, "P": 3}
PI_CAP = {"O": 1, "S": 1, "Se": 1, "N": 2, "P": 2}
LIG_VALENCE = {"H": 1, "F": 7, "Cl": 7, "Br": 7, "I": 7, "OH": 7, "O": 6, "S": 6, "Se": 6, "N": 5, "P": 5}
LIG_NB_SINGLE = {"H": 0, "OH": 4}          # non-bonded electrons on a terminal joined by one single bond


def valence_main_group(sym: str, ctx: "Ctx") -> int:
    conf = atom_config(sym, ctx)
    nmax = max(n for (n, l) in conf)
    last = sorted(((n, l) for n in range(1, 8) for l in range(0, min(n, 4))), key=lambda t: (t[0] + t[1], t[0]))
    filled = [nl for nl in last if nl in conf]
    lastfilled = filled[-1]
    if lastfilled[1] >= 2 and sym not in ("He",):
        raise RuleError(f"{sym} is not a main-group element: VSEPR central atom outside rule tables")
    v = sum(e for (n, l), e in conf.items() if n == nmax and l <= 1)
    return v


def period(sym: str) -> int:
    Z = Z_OF[sym]
    return 1 + sum(1 for z, _ in NOBLE if Z > z)


@dataclass
class Vsepr:
    text: str
    central: str
    ligands: list[str]
    charge: int
    sn: int
    lp: int
    single: int            # odd electron on the central atom (0/1)
    nb_central: int        # non-bonded electrons on the central atom
    total_valence: int
    pi: int = 0
    pi_assumption: str = ""
    shape: str = ""
    sites: list = field(default_factory=list)       # [(vector, label, occupant)]


SN_HYB = {2: "sp", 3: "sp2", 4: "sp3", 5: "sp3d", 6: "sp3d2", 7: "sp3d3"}
SHAPES = {(2, 0): "linear", (3, 0): "trigonal_planar", (3, 1): "bent", (4, 0): "tetrahedral",
          (4, 1): "trigonal_pyramidal", (4, 2): "bent", (5, 0): "trigonal_bipyramidal", (5, 1): "see_saw",
          (5, 2): "T_shaped", (5, 3): "linear", (6, 0): "octahedral", (6, 1): "square_pyramidal",
          (6, 2): "square_planar", (7, 0): "pentagonal_bipyramidal", (7, 1): "pentagonal_pyramidal"}
NONPOLAR_SYMMETRIC = {"linear", "trigonal_planar", "tetrahedral", "trigonal_bipyramidal", "octahedral",
                      "square_planar", "pentagonal_bipyramidal"}
SUBSTITUTION_POLAR = {"linear", "trigonal_planar", "tetrahedral"}   # any mixed ligand set is polar


def _geometry(sn: int):
    r3 = sp.sqrt(3)
    tri = [(sp.Integer(1), 0, 0), (-sp.Rational(1, 2), r3 / 2, 0), (-sp.Rational(1, 2), -r3 / 2, 0)]
    if sn == 2:
        return [((0, 0, 1), "ax"), ((0, 0, -1), "ax")], [0, 1]
    if sn == 3:
        return [(v, "eq") for v in tri], [0, 1, 2]
    if sn == 4:
        return [(v, "td") for v in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]], [0, 1, 2, 3]
    if sn == 5:
        return [(v, "eq") for v in tri] + [((0, 0, 1), "ax"), ((0, 0, -1), "ax")], [0, 1, 2, 3, 4]
    if sn == 6:
        return [((0, 0, 1), "ax"), ((0, 0, -1), "ax"), ((1, 0, 0), "eq"), ((-1, 0, 0), "eq"),
                ((0, 1, 0), "eq"), ((0, -1, 0), "eq")], [0, 1, 2, 3, 4, 5]
    if sn == 7:
        pent = [(sp.cos(2 * sp.pi * k / 5), sp.sin(2 * sp.pi * k / 5), 0) for k in range(5)]
        return [((0, 0, 1), "ax"), ((0, 0, -1), "ax")] + [(v, "eq") for v in pent], list(range(7))
    raise RuleError(f"steric number {sn} outside rule tables")


def _central_and_ligands(text: str, ctx: "Ctx"):
    s = _species(text)
    base = re.sub(r"\^.*$", "", text.strip())
    if base in STRUCTURES:
        c, ligs = STRUCTURES[base]
        ctx.step(f"{text}: connectivity from structure table (central {c}, ligands {ligs})")
        return c, list(ligs), s.charge
    atoms = dict(s.atoms)
    total = sum(atoms.values())
    if total < 2:
        raise RuleError(f"{text}: not a molecule")
    if len(atoms) == 1:
        el = next(iter(atoms))
        if total == 2:
            return el, [el], s.charge
        if total != 3:
            raise RuleError(f"{text}: homoatomic species other than A2/A3 outside rule tables")
        return el, [el, el], s.charge
    cands = [e for e, n in atoms.items() if e != "H" and n == 1]
    if not cands:
        raise RuleError(f"{text}: no unique central atom")
    for e in cands:
        if PAULING_EN.get(e) is None:
            raise RuleError(f"{text}: electronegativity of {e} not tabulated")
    cands.sort(key=lambda e: PAULING_EN[e])
    if len(cands) > 1 and PAULING_EN[cands[0]] == PAULING_EN[cands[1]]:
        raise RuleError(f"{text}: central atom ambiguous")
    c = cands[0]
    ligs = []
    for e, n in atoms.items():
        if e == c:
            continue
        ligs += [e] * n
    if "H" in ligs and any(NEED.get(x, 0) >= 2 for x in ligs if x != "H"):
        raise RuleError(f"{text}: H attachment ambiguous (H with polyvalent ligands) - needs a structure entry")
    return c, ligs, s.charge


def vsepr(text: str, ctx: "Ctx") -> Vsepr:
    c, ligs, q = _central_and_ligands(text, ctx)
    for x in ligs:
        if x not in NEED:
            raise RuleError(f"{text}: terminal atom {x} outside rule tables")
    V = valence_main_group(c, ctx)
    n = len(ligs)
    # --- method A: formula electron count H = 1/2 (V + M - T - q)
    M = sum(1 for x in ligs if NEED[x] == 1)
    T = sum(1 for x in ligs if NEED[x] == 3)
    twice = V + M - T - q
    sn_a = (twice + 1) // 2           # odd electron counts as a domain
    single_a = twice % 2
    # --- method B: explicit Lewis structure count (single bonds, complete terminal octets, rest on centre)
    tv = V + sum(LIG_VALENCE[x] for x in ligs) - q
    used = 2 * n + sum(LIG_NB_SINGLE.get(x, 6) for x in ligs) + sum(2 for x in ligs if x == "OH")
    R = tv - used
    if R < 0:
        raise RuleError(f"{text}: not enough electrons for a single-bonded Lewis structure")
    lp_b, single_b = R // 2, R % 2
    sn_b = n + lp_b + single_b
    if (sn_a, single_a) != (sn_b, single_b) and n > 1:
        raise RuleError(f"{text}: steric number methods disagree (formula {sn_a}, Lewis {sn_b})")
    ctx.cross(f"{text}: steric number formula 1/2({V}+{M}-{T}-({q})) == Lewis count ({n} bonds + {lp_b} lp"
              f"{' + 1 odd e-' if single_b else ''}) == {sn_b}")
    v = Vsepr(text, c, ligs, q, sn_b, lp_b, single_b, R, tv)
    # --- pi bonds (Lewis structure completion)
    caps = [PI_CAP.get(x, 0) for x in ligs]
    pis = [0] * n
    if period(c) == 2:
        while 2 * (n + sum(pis)) + R + 2 <= 8:
            avail = [i for i in range(n) if pis[i] < caps[i]]
            if not avail:
                break
            i = min(avail, key=lambda j: (pis[j], j))
            pis[i] += 1
        v.pi_assumption = "period-2 centre: pi bonds added only until the octet is complete"
    else:
        def fc_c():
            return V - R - (n + sum(pis))
        while fc_c() > 0:
            avail = [i for i in range(n) if pis[i] < caps[i]]
            if not avail:
                break
            i = min(avail, key=lambda j: (pis[j], j))
            pis[i] += 1
        if sum(pis):
            v.pi_assumption = ("period>=3 centre: formal-charge-minimised (expanded octet) Lewis structure, "
                               "NCERT convention")
    v.pi = sum(pis)
    if n > 1:
        key = (v.sn, v.lp + v.single)
        if key not in SHAPES:
            raise RuleError(f"{text}: (SN {v.sn}, lone domains {v.lp + v.single}) outside shape table")
        v.shape = SHAPES[key]
        geo, _ = _geometry(v.sn)
        lone = v.lp + v.single
        if v.sn == 5:
            lp_sites = [0, 1, 2][:lone] if lone <= 3 else None
        elif v.sn == 6:
            lp_sites = [0, 1][:lone]
        elif v.sn == 7:
            lp_sites = [0][:lone]
        else:
            lp_sites = list(range(lone))
        v.sites = [(vec, lab, "LP" if i in lp_sites else None) for i, (vec, lab) in enumerate(geo)]
    else:
        v.shape = "linear"
    return v


def _bond_sites(v: Vsepr):
    return [(vec, lab) for vec, lab, occ in v.sites if occ != "LP"]


def dipole_nonzero(v: Vsepr, ctx: "Ctx") -> int:
    ligset = set(v.ligands)
    if len(v.ligands) == 1:
        res1 = 1 if v.ligands[0] != v.central else 0
        ctx.cross(f"{v.text}: diatomic, {'heteronuclear' if res1 else 'homonuclear'}")
        return res1
    # method 1: symmetry table
    if v.shape in NONPOLAR_SYMMETRIC and v.lp + v.single in (0, 2, 3) and \
            not (v.shape == "linear" and v.sn == 2 and v.lp) and \
            ((v.lp + v.single == 0) or v.shape in ("square_planar", "linear")):
        if len(ligset) == 1:
            m1: Optional[int] = 0
        elif v.shape in SUBSTITUTION_POLAR:
            m1 = 1
        else:
            m1 = None
    else:
        m1 = 1
    # method 2: symbolic vector sum over all distinct ligand placements
    bsites = _bond_sites(v)
    wl = {x: sp.Symbol(f"w_{x}", positive=True) for x in ligset}
    wlp = sp.Symbol("w_lp", positive=True)
    lone_vecs = [vec for vec, lab, occ in v.sites if occ == "LP"]
    outcomes = set()
    for perm in set(itertools.permutations(v.ligands)):
        tot = [sp.Integer(0)] * 3
        for (vec, _), x in zip(bsites, perm):
            for k in range(3):
                tot[k] += wl[x] * sp.sympify(vec[k])
        for vec in lone_vecs:
            for k in range(3):
                tot[k] += wlp * sp.sympify(vec[k])
        zero = True
        for comp in tot:
            comp = sp.expand(comp)
            for sym in list(wl.values()) + [wlp]:
                coeff = comp.coeff(sym)
                if abs(complex(sp.N(coeff, 40))) > 1e-25:
                    zero = False
        outcomes.add(0 if zero else 1)
    m2 = outcomes.pop() if len(outcomes) == 1 else None
    if m1 is None or m2 is None:
        raise RuleError(f"{v.text}: dipole depends on the isomer (mixed ligands) - outside rule tables")
    if m1 != m2:
        raise RuleError(f"{v.text}: dipole methods disagree (symmetry {m1}, vector sum {m2})")
    ctx.cross(f"{v.text}: dipole {'non-zero' if m1 else 'zero'} by symmetry table and by bond/lone-pair vector sum")
    return m1


def is_linear(v: Vsepr, ctx: "Ctx") -> int:
    if len(v.ligands) == 1:
        ctx.cross(f"{v.text}: diatomic is linear")
        return 1
    m1 = 1 if v.shape == "linear" else 0
    vecs = [sp.Matrix(vec) for vec, _ in _bond_sites(v)]
    m2 = 1
    for a, b in itertools.combinations(vecs, 2):
        if any(abs(complex(sp.N(c, 30))) > 1e-20 for c in a.cross(b)):
            m2 = 0
    if m1 != m2:
        raise RuleError(f"{v.text}: linearity methods disagree")
    ctx.cross(f"{v.text}: linear={m1} from shape table and from bond-vector collinearity")
    return m1


def octet_class(v: Vsepr) -> str:
    if v.total_valence % 2:
        return "odd"
    e = 2 * (len(v.ligands) + v.pi) + v.nb_central
    return "obeys" if e == 8 else ("incomplete" if e < 8 else "expanded")


# =============================================================================== MO theory (diatomics)
ORDER_MIX = [("sigma2s", 1, +1), ("sigma*2s", 1, -1), ("pi2p", 2, +1), ("sigma2p", 1, +1), ("pi*2p", 2, -1),
             ("sigma*2p", 1, -1)]
ORDER_NOMIX = [("sigma2s", 1, +1), ("sigma*2s", 1, -1), ("sigma2p", 1, +1), ("pi2p", 2, +1), ("pi*2p", 2, -1),
               ("sigma*2p", 1, -1)]
ORDER_1S = [("sigma1s", 1, +1), ("sigma*1s", 1, -1)]


def _fill_mo(order, ne, label, ctx):
    if ne > sum(2 * g for _, g, _ in order) or ne < 0:
        raise RuleError(f"{label}: electron count outside MO table")
    left, nb, na, u1, u2, occ = ne, 0, 0, 0, 0, []
    for name, g, kind in order:
        e = min(left, 2 * g)
        left -= e
        if e:
            occ.append(f"({name}){e}")
        nb += e if kind > 0 else 0
        na += e if kind < 0 else 0
        u1 += e if e <= g else 2 * g - e
        boxes = [0] * g
        for i in range(e):
            boxes[i % g] += 1
        u2 += sum(1 for b in boxes if b == 1)
    if u1 != u2:
        raise RuleError(f"{label}: MO unpaired-electron methods disagree")
    return sp.Rational(nb - na, 2), u1, " ".join(occ)


def mo_diatomic(text: str, ctx: "Ctx"):
    s = _species(text)
    if sum(s.atoms.values()) != 2:
        raise RuleError(f"{text}: not a diatomic")
    els = list(s.atoms)
    for e in els:
        if Z_OF[e] > 18:
            raise RuleError(f"{text}: MO tables cover Z <= 18 only")
    if all(Z_OF[e] <= 2 for e in els):
        ne = sum(Z_OF[e] * n for e, n in s.atoms.items()) - s.charge
        res = [_fill_mo(ORDER_1S, ne, text, ctx)]
    else:
        if any(Z_OF[e] <= 2 for e in els):
            raise RuleError(f"{text}: mixed 1s/2p diatomic outside MO tables")
        ne = 0
        for e, n in s.atoms.items():
            ne += n * valence_main_group(e, ctx)
        ne -= s.charge
        mixing = [Z_OF[e] in (3, 4, 5, 6, 7, 11, 12, 13, 14, 15) for e in els]
        if len(els) == 1:
            order = ORDER_MIX if mixing[0] else ORDER_NOMIX
            res = [_fill_mo(order, ne, text, ctx)]
            ctx.step(f"{text}: {'s-p mixing (sigma2p above pi2p)' if mixing[0] else 'no s-p mixing'} "
                     f"level ordering ({'group 1-2/13-15' if mixing[0] else 'group 16-18'} convention)")
        else:
            res = [_fill_mo(ORDER_MIX, ne, text, ctx), _fill_mo(ORDER_NOMIX, ne, text, ctx)]
            if (res[0][0], res[0][1]) != (res[1][0], res[1][1]):
                raise RuleError(f"{text}: heteronuclear result depends on level ordering - UNRESOLVED")
            ctx.cross(f"{text}: both MO level orderings give bond order {res[0][0]}, {res[0][1]} unpaired")
    bo, u, occ = res[0]
    ctx.step(f"{text}: {ne} electrons in MOs: {occ}; bond order {bo}; unpaired {u}")
    ctx.cross(f"{text}: MO unpaired e- by formula == Hund box filling == {u}")
    return bo, u


# =============================================================================== oxidation states
FIXED_OS = {"F": -1, "Li": 1, "Na": 1, "K": 1, "Rb": 1, "Cs": 1, "Be": 2, "Mg": 2, "Ca": 2, "Sr": 2, "Ba": 2,
            "Al": 3}


def _os_range(el: str, ctx) -> tuple[int, int]:
    """Plausible oxidation-state window: [-(8 - valence) for p-block non-metals, 0 otherwise] ..
    [ns + np + unfilled (n-1)d electrons]; Cu/Ag/Au capped at +3."""
    conf = atom_config(el, ctx)
    nmax = max(n for (n, l) in conf)
    vs = sum(e for (n, l), e in conf.items() if n == nmax and l <= 1)
    d = sum(e for (n, l), e in conf.items() if n == nmax - 1 and l == 2 and e < 10)
    if el in ("Cu", "Ag", "Au"):
        return 0, 3
    lo = -(8 - vs) if (vs >= 4 or el == "H") else 0
    if el == "H":
        lo = -1
    return lo, vs + d


def oxidation_state(text: str, element: str, ctx: "Ctx") -> sp.Rational:
    s = _species(text)
    atoms = dict(s.atoms)
    if element not in atoms:
        raise RuleError(f"{element} not in {text}")
    if len(atoms) == 1:
        val = sp.Rational(s.charge, atoms[element])
        ctx.step(f"oxidation state of {element} in {text} = {val} (homoatomic)")
        return val
    known: dict[str, int] = {}
    metals_only_h = "H" in atoms and all(e in FIXED_OS for e in atoms if e != "H")
    for e in atoms:
        if e in FIXED_OS:
            known[e] = FIXED_OS[e]
        elif e == "H":
            known[e] = -1 if metals_only_h else 1
        elif e == "O" and "F" not in atoms:
            known[e] = -2
        elif e in ("Cl", "Br", "I") and not ({"O", "F"} & set(atoms)):
            known[e] = -1
    unknown = [e for e in atoms if e not in known]
    charge = s.charge
    if len(unknown) > 1:
        for grp, gq in POLYATOMIC:
            k = None
            for e, n in grp.items():
                if e not in atoms or atoms[e] % n:
                    k = None
                    break
                kk = atoms[e] // n
                k = kk if k is None else min(k, kk)
            if not k:
                continue
            rest = {e: atoms[e] - k * grp.get(e, 0) for e in atoms}
            rest = {e: n for e, n in rest.items() if n}
            if len([e for e in rest if e not in known or e == element]) == 1 and element in rest:
                ctx.step(f"{text}: recognised {k} x polyatomic group {grp} (charge {gq})")
                atoms, charge, unknown = rest, s.charge - k * gq, [element]
                for e in list(known):
                    if e not in atoms:
                        known.pop(e)
                break
    if unknown != [element]:
        raise RuleError(f"{text}: oxidation state of {element} not fixed by rules (unknowns {unknown})")
    total_known = sum(known[e] * n for e, n in atoms.items() if e in known and e != element)
    val = sp.Rational(charge - total_known, atoms[element])
    lo, hi = _os_range(element, ctx)
    if not (lo <= val <= hi):
        raise RuleError(f"{text}: computed oxidation state {val} of {element} outside [{lo}, {hi}] "
                        "(peroxide/superoxide or unusual bonding?) - UNRESOLVED")
    ctx.step(f"oxidation state of {element} in {text} = {val} (O -2, H +1, F -1, group 1/2 fixed)")
    return val


# =============================================================================== misc properties
def _parse_formula_independent(text: str) -> dict[str, int]:
    t = re.sub(r"\^.*$", "", text.strip())

    def parse(i: int) -> tuple[dict, int]:
        out: dict[str, int] = {}
        while i < len(t):
            ch = t[i]
            if ch == "(":
                sub, i = parse(i + 1)
                m = re.match(r"\d+", t[i:])
                k = int(m.group()) if m else 1
                i += len(m.group()) if m else 0
                for e, n in sub.items():
                    out[e] = out.get(e, 0) + n * k
            elif ch == ")":
                return out, i + 1
            else:
                m = re.match(r"([A-Z][a-z]?)(\d*)", t[i:])
                if not m:
                    raise RuleError(f"independent parser cannot read {text!r}")
                out[m.group(1)] = out.get(m.group(1), 0) + (int(m.group(2)) if m.group(2) else 1)
                i += len(m.group())
        return out, i

    res, _ = parse(0)
    return res


def molar_mass(text: str, masses: Optional[dict], ctx: "Ctx") -> sp.Rational:
    a = _species(text).atoms
    b = _parse_formula_independent(text)
    if a != b:
        raise RuleError(f"{text}: formula parsers disagree {a} vs {b}")
    if masses:
        missing = [e for e in a if e not in masses]
        if missing:
            raise RuleError(f"{text}: atomic masses for {missing} not stated")
        table, src = masses, "atomic masses stated in the stem"
    else:
        missing = [e for e in a if e not in ATOMIC_MASS]
        if missing:
            raise RuleError(f"{text}: {missing} not in atomic-mass table")
        table, src = ATOMIC_MASS, "IUPAC 2021 abridged standard atomic weights (stem gives none)"
        ctx.assume(src)
    m = sum(sp.Rational(str(table[e])) * n for e, n in a.items())
    ctx.cross(f"{text}: formula parsed identically by two parsers; M = {m} g/mol ({src})")
    return m


def dna_hbonds(seq: str, ctx: "Ctx") -> int:
    s = re.sub(r"[^A-Za-z]", "", seq.replace("5'", "").replace("3'", "")).upper()
    if not s or set(s) - set("ATGC"):
        raise RuleError(f"DNA sequence {seq!r} must contain only A, T, G, C")
    m1 = 3 * (s.count("G") + s.count("C")) + 2 * (s.count("A") + s.count("T"))
    comp = {"A": "T", "T": "A", "G": "C", "C": "G"}
    pair_h = {frozenset("AT"): 2, frozenset("GC"): 3}
    m2 = sum(pair_h[frozenset((b, comp[b]))] for b in s)
    if m1 != m2:
        raise RuleError("DNA H-bond methods disagree")
    ctx.cross(f"DNA {s}: G-C 3 H-bonds, A-T 2 (Watson-Crick); count formula == explicit pairing == {m1}")
    return m1


AO_POLY = {"s": "1", "px": "x", "py": "y", "pz": "z", "dz2": "2*z**2 - x**2 - y**2", "dxz": "x*z", "dyz": "y*z",
           "dxy": "x*y", "dx2-y2": "x**2 - y**2", "dx2y2": "x**2 - y**2"}
AO_LABEL = {"s": "sigma", "pz": "sigma", "dz2": "sigma", "px": "pi_x", "dxz": "pi_x", "py": "pi_y", "dyz": "pi_y",
            "dxy": "delta_xy", "dx2-y2": "delta_x2y2", "dx2y2": "delta_x2y2"}


def lcao_match(pair: str, ctx: "Ctx") -> int:
    parts = [p.strip().replace("_", "").replace("{", "").replace("}", "").replace("^", "") for p in pair.split("|")]
    if len(parts) != 2:
        raise RuleError("lcao pair must be 'AO1|AO2'")
    keys = []
    for p in parts:
        m = re.fullmatch(r"\d([spd].*)", p)
        if not m or m.group(1) not in AO_POLY:
            raise RuleError(f"atomic orbital {p!r} outside table")
        keys.append(m.group(1))
    m1 = 1 if AO_LABEL[keys[0]] == AO_LABEL[keys[1]] else 0
    x, y, z, rho, phi = sp.symbols("x y z rho phi", real=True)
    loc = {"x": x, "y": y, "z": z}
    prod = sp.sympify(AO_POLY[keys[0]], locals=loc) * sp.sympify(AO_POLY[keys[1]], locals=loc)
    integ = sp.integrate(sp.expand(prod.subs({x: rho * sp.cos(phi), y: rho * sp.sin(phi)})), (phi, 0, 2 * sp.pi))
    m2 = 0 if sp.simplify(integ) == 0 else 1
    if m1 != m2:
        raise RuleError(f"{pair}: LCAO symmetry methods disagree")
    ctx.cross(f"{pair} (axis z): symmetry labels {AO_LABEL[keys[0]]}/{AO_LABEL[keys[1]]}; azimuthal overlap "
              f"integral {'non-zero' if m2 else 'zero'}")
    return m1


def oxo_counts(text: str, ctx: "Ctx") -> tuple[int, int]:
    key = text.strip()
    if key not in OXO_TETRAHEDRA:
        raise RuleError(f"{text}: oxoanion structure not tabulated")
    el, k = OXO_TETRAHEDRA[key]
    bridging = k - 1
    terminal = 4 * k - 2 * bridging
    o = _species(text).atoms.get("O", 0)
    if terminal + bridging != o:
        raise RuleError(f"{text}: O count {o} inconsistent with {k} corner-sharing tetrahedra")
    ctx.cross(f"{text}: {k} corner-sharing {el}O4 tetrahedra -> {terminal} terminal + {bridging} bridging O "
              f"(= {o} O in formula)")
    return terminal, bridging


# =============================================================================== redox helpers
def _redox_element(ox: str, red: str):
    a, b = _species(ox), _species(red)
    common = [e for e in a.atoms if e in b.atoms and e not in ("O", "H")]
    if len(common) != 1:
        return None
    return common[0], a.atoms[common[0]], b.atoms[common[0]]


def couple_n(c: dict, ctx: "Ctx") -> int:
    info = _redox_element(c["ox"], c["red"])
    n_calc = None
    if info:
        el, na, nb = info
        try:
            s_ox, s_red = oxidation_state(c["ox"], el, ctx), oxidation_state(c["red"], el, ctx)
            n_calc = (s_ox - s_red) * na
            if n_calc <= 0 or not n_calc.is_integer:
                raise RuleError(f"{c['ox']}/{c['red']}: not a reduction couple")
            n_calc = int(n_calc)
        except RuleError:
            if "n" not in c:
                raise
            n_calc = None
    if "n" in c:
        n = int(c["n"])
        if n_calc is not None and n != n_calc:
            raise RuleError(f"{c['ox']}/{c['red']}: stated n={n} but oxidation states give {n_calc}")
        if n_calc is None:
            ctx.assume(f"{c['ox']}/{c['red']}: n = {n} as stated (oxidation-state check not applicable)")
        else:
            ctx.cross(f"{c['ox']}/{c['red']}: n = {n} stated == oxidation-state change")
        return n
    if n_calc is None:
        raise RuleError(f"{c['ox']}/{c['red']}: n not determinable")
    ctx.step(f"{c['ox']}/{c['red']}: n = {n_calc} from oxidation-state change")
    return n_calc


def _couple_vector(c: dict, n: int) -> dict[str, sp.Rational]:
    info = _redox_element(c["ox"], c["red"])
    r = sp.Rational(info[1], info[2]) if info else sp.Integer(1)
    return {c["ox"]: sp.Integer(-1), c["red"]: r, "e-": sp.Integer(-n)}


def _expr(s: Any) -> sp.Expr:
    from cqse.math.expr import parse
    t = str(s)
    names = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", t)) - {"sqrt", "log", "ln", "exp", "pi", "Abs"}
    return parse(t, {n: sp.Symbol(n) for n in names})


def combine_potentials(q: dict, ctx: "Ctx") -> sp.Expr:
    couples = q["couples"]
    ns = [couple_n(c, ctx) for c in couples]
    vecs = [_couple_vector(c, n) for c, n in zip(couples, ns)]
    Es = [_expr(c["E"]) for c in couples]

    def solve_target(t: dict) -> sp.Expr:
        key = (t["ox"], t["red"])
        for c, E in zip(couples, Es):
            if (c["ox"], c["red"]) == key:
                return E
        nt = couple_n(t, ctx)
        vt = _couple_vector(t, nt)
        keys = sorted(set().union(*[set(v) for v in vecs], set(vt)))
        cs = sp.symbols(f"c0:{len(vecs)}")
        eqs = [sum(cs[i] * vecs[i].get(k, 0) for i in range(len(vecs))) - vt.get(k, 0) for k in keys]
        sol = sp.linsolve(eqs, cs)
        if len(sol) != 1:
            raise RuleError("target half-reaction is not a unique combination of the given couples")
        coeffs = list(sol)[0]
        if any(cc.free_symbols for cc in coeffs):
            raise RuleError("target half-reaction combination not unique")
        # independent re-check: recombine the vectors
        for k in keys:
            if sum(coeffs[i] * vecs[i].get(k, 0) for i in range(len(vecs))) != vt.get(k, 0):
                raise RuleError("recombination check failed")
        Et = sp.expand(sum(coeffs[i] * ns[i] * Es[i] for i in range(len(vecs))) / nt)
        ctx.cross(f"E({t['ox']}/{t['red']}): half-reactions combined with coefficients {list(coeffs)}; "
                  f"dG additivity n_t E_t = sum c_i n_i E_i; recombination re-checked")
        ctx.step(f"E({t['ox']}/{t['red']}) = {Et}")
        return Et

    if "cell" in q:
        Ec = solve_target(q["cell"]["cathode"])
        Ea = solve_target(q["cell"]["anode"])
        E = sp.expand(Ec - Ea)
        ctx.step(f"E_cell = E_cathode - E_anode = {E}")
        return E
    return solve_target(q["target"])


def cell(q: dict, ctx: "Ctx"):
    c, a = q["cathode"], q["anode"]
    nc, na = couple_n(c, ctx), couple_n(a, ctx)
    n = nc * na // math.gcd(nc, na)
    E = _expr(c["E"]) - _expr(a["E"])
    ctx.step(f"cell {a['red']}|{a['ox']}||{c['ox']}|{c['red']}: E0 = {c['E']} - ({a['E']}) = {E}; n = {n}")
    ret = q.get("return", "E")
    if ret == "E":
        return E, "V"
    if ret == "n":
        return sp.Integer(n), ""
    if ret == "deltaG_over_F":
        return sp.nsimplify(-n * E), "V"
    raise RuleError(f"unknown cell return {ret!r}")


def nernst(q: dict, ctx: "Ctx") -> sp.Expr:
    c, a = q["cathode"], q["anode"]
    nc, na = couple_n(c, ctx), couple_n(a, ctx)
    n = nc * na // math.gcd(nc, na)
    # overall: (n/nc) [ox_c + nc e -> red_c]  +  (n/na) [red_a -> ox_a + na e]
    vc, va = _couple_vector(c, nc), _couple_vector(a, na)
    tot: dict[str, sp.Rational] = {}
    for k, v in vc.items():
        tot[k] = tot.get(k, 0) + v * n / nc
    for k, v in va.items():
        tot[k] = tot.get(k, 0) - v * n / na
    if tot.get("e-", 0) != 0:
        raise RuleError("electrons do not cancel")
    syms = q.get("symbols", {})
    R, T, F = sp.symbols("R T F")
    lnQ = sp.Integer(0)
    for sp_name, nu in tot.items():
        if sp_name == "e-" or nu == 0:
            continue
        s = _species(sp_name)
        if s.charge == 0 and len(s.atoms) == 1:
            ctx.step(f"{sp_name}: pure solid, activity 1 (excluded from Q)")
            continue
        if sp_name not in syms:
            raise RuleError(f"no concentration symbol for {sp_name}")
        lnQ += nu * sp.log(sp.Symbol(syms[sp_name]))   # tot: products > 0, reactants < 0 -> ln Q = sum nu ln c
    expr = sp.expand(-(R * T / (n * F)) * lnQ)
    ctx.step(f"overall reaction coefficients {dict((k, str(v)) for k, v in tot.items() if k != 'e-')}; n = {n}; "
             f"E - E0 = {expr}")
    ctx.cross(f"Nernst: n = lcm({nc}, {na}) = {n}; electrons cancel in the overall reaction")
    return expr


# =============================================================================== evaluation context
@dataclass
class Ctx:
    steps: list[str] = field(default_factory=list)
    crosses: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    curated: list[tuple[bool, str]] = field(default_factory=list)

    def step(self, s):
        if s not in self.steps:
            self.steps.append(s)

    def cross(self, s):
        if s not in self.crosses:
            self.crosses.append(s)

    def assume(self, s):
        if s not in self.assumptions:
            self.assumptions.append(s)


def _label_index(label: str) -> int:
    from cqse.verification.formats import label_index
    return label_index(label)


def prop(p: str, species: str, params: dict, ctx: Ctx) -> tuple[sp.Basic, str]:
    if p == "electron_configuration":
        sym, q, conf = ion_config(species, ctx)
        ctx.step(f"{species}: {fmt_config(conf)}")
        return sp.Symbol(fmt_config(conf).replace(" ", "_")), ""
    if p == "subshell_electrons":
        sym, q, conf = ion_config(species, ctx)
        ctx.step(f"{species}: {fmt_config(conf)}")
        return sp.Integer(conf.get(_parse_sub(params["subshell"]), 0)), ""
    if p == "unpaired_electrons":
        sym, q, conf = ion_config(species, ctx)
        ctx.step(f"{species}: {fmt_config(conf)} (free ion, high spin)")
        return sp.Integer(unpaired(conf, ctx, species)), ""
    if p == "spin_only_moment":
        sym, q, conf = ion_config(species, ctx)
        n = unpaired(conf, ctx, species)
        ctx.step(f"{species}: {fmt_config(conf)}; n = {n}; mu = sqrt(n(n+2)) = sqrt({n * (n + 2)}) BM")
        return sp.sqrt(n * (n + 2)), "BM"
    if p == "paramagnetic":
        s = _species(species)
        if sum(s.atoms.values()) == 1:
            sym, q, conf = ion_config(species, ctx)
            return sp.Integer(1 if unpaired(conf, ctx, species) else 0), ""
        bo, u = mo_diatomic(species, ctx)
        return sp.Integer(1 if u else 0), ""
    if p in ("bond_order", "mo_unpaired_electrons"):
        bo, u = mo_diatomic(species, ctx)
        return (bo if p == "bond_order" else sp.Integer(u)), ""
    if p == "oct_config_ligand_independent":
        sym, q, conf = ion_config(species, ctx)
        ds = [(n, l) for (n, l) in conf if l == 2]
        if not ds and q <= 0:
            raise RuleError(f"{species}: not a d-block ion")
        nd = conf.get(max(ds), 0) if ds else 0
        m1 = 1 if nd in (0, 1, 2, 3, 8, 9, 10) else 0
        hs = _cf_fill(nd, high_spin=True)
        ls = _cf_fill(nd, high_spin=False)
        m2 = 1 if hs == ls else 0
        if m1 != m2:
            raise RuleError(f"{species}: crystal-field methods disagree")
        ctx.cross(f"{species}: d{nd}; Oh high-spin t2g{hs[0]}eg{hs[1]} vs low-spin t2g{ls[0]}eg{ls[1]} -> "
                  f"{'same' if m2 else 'different'} (d-count rule agrees)")
        return sp.Integer(m1), ""
    if p == "aq_colour":
        key = species.strip()
        if key not in AQ_COLOUR:
            raise RuleError(f"{species}: colour not in NCERT table")
        col = AQ_COLOUR[key]
        sym, q, conf = ion_config(species, ctx)
        ds = [(n, l) for (n, l) in conf if l == 2]
        nd = conf.get(max(ds), 0) if ds else 0
        if (col == "colourless") != (nd in (0, 10)):
            raise RuleError(f"{species}: colour table inconsistent with d{nd} (colourless iff d0/d10)")
        ctx.cross(f"{species}: {col} (NCERT table); consistent with d{nd}")
        return sp.Symbol(col), ""
    if p == "enthalpy_atomisation":
        if species not in ENTHALPY_ATOMISATION_3D:
            raise RuleError(f"{species}: not in NCERT Table 8.2")
        ctx.step(f"{species}: enthalpy of atomisation {ENTHALPY_ATOMISATION_3D[species]} kJ/mol (NCERT XII T8.2)")
        return sp.Integer(ENTHALPY_ATOMISATION_3D[species]), "kJ/mol"
    if p == "molar_mass":
        return molar_mass(species, params.get("atomic_masses"), ctx), "g/mol"
    if p == "oxidation_state":
        return oxidation_state(species, params["element"], ctx), ""
    if p == "dna_duplex_hbonds":
        return sp.Integer(dna_hbonds(species, ctx)), ""
    if p == "lcao_symmetry_match":
        return sp.Integer(lcao_match(species, ctx)), ""
    if p in ("terminal_oxygens", "bridging_oxygens"):
        t, b = oxo_counts(species, ctx)
        return sp.Integer(t if p == "terminal_oxygens" else b), ""
    # ---- VSEPR / Lewis
    v = vsepr(species, ctx)
    nlig = len(v.ligands)
    ctx.step(f"{species}: central {v.central}, {nlig} sigma bonds, {v.lp} lone pair(s)"
             f"{', 1 odd electron' if v.single else ''}; SN {v.sn}; {v.shape}")
    if p == "steric_number":
        return sp.Integer(v.sn), ""
    if p == "bond_pairs":
        return sp.Integer(nlig), ""
    if p == "lone_pairs":
        return sp.Integer(v.lp), ""
    if p == "lone_pairs_equatorial":
        if v.sn != 5:
            raise RuleError(f"{species}: 'equatorial' defined here only for SN 5 (trigonal bipyramid)")
        eq = sum(1 for vec, lab, occ in v.sites if occ == "LP" and lab == "eq")
        ctx.step(f"{species}: lone pairs occupy equatorial sites of the trigonal bipyramid ({eq})")
        return sp.Integer(eq), ""
    if p == "shape":
        return sp.Symbol(v.shape), ""
    if p == "hybridization":
        if nlig < 2:
            raise RuleError(f"{species}: hybridization not defined for a diatomic in this rule set")
        return sp.Symbol(SN_HYB[v.sn]), ""
    if p == "dipole_nonzero":
        return sp.Integer(dipole_nonzero(v, ctx)), ""
    if p == "is_linear":
        return sp.Integer(is_linear(v, ctx)), ""
    if p == "bond_sites_inequivalent":
        labs = {lab for vec, lab in _bond_sites(v)}
        if v.sn == 6 and v.lp + v.single == 0:
            labs = {"oct"}
        res = 1 if (len(labs) > 1 or len(set(v.ligands)) > 1) else 0
        ctx.step(f"{species}: bond sites {sorted(labs)}; ligands {sorted(set(v.ligands))} -> "
                 f"{'inequivalent (different bond lengths)' if res else 'all equivalent'}")
        return sp.Integer(res), ""
    if p == "valence_electrons_total":
        return sp.Integer(v.total_valence), ""
    if p == "bond_pairs_total":
        if v.pi_assumption:
            ctx.assume(v.pi_assumption)
        ctx.step(f"{species}: {nlig} sigma + {v.pi} pi bond pairs")
        return sp.Integer(nlig + v.pi), ""
    if p == "lewis_nonbonded_electrons":
        if period(v.central) > 2 and v.pi:
            raise RuleError(f"{species}: non-bonded count depends on the octet/expanded-octet convention")
        nb = v.total_valence - 2 * (nlig + v.pi) - 2 * sum(1 for x in v.ligands if x == "OH")
        ctx.step(f"{species}: {v.total_valence} valence e-; {nlig + v.pi} bonds -> {nb} non-bonded electrons")
        return sp.Integer(nb), ""
    if p == "octet_class":
        if v.pi_assumption:
            ctx.assume(v.pi_assumption)
        oc = octet_class(v)
        ctx.step(f"{species}: central {v.central} has {2 * (nlig + v.pi) + v.nb_central} e- -> {oc}")
        return sp.Symbol(oc), ""
    raise RuleError(f"unknown property {p!r}")


def _cf_fill(nd: int, high_spin: bool) -> tuple[int, int]:
    """Explicit box filling of t2g (3) / eg (2) in an octahedral field: high spin = Hund across all five
    boxes before pairing; low spin = fill t2g completely before eg."""
    t2g, eg = [0] * 3, [0] * 2
    for _ in range(nd):
        if high_spin:
            cand = [(t2g, j) for j in range(3) if t2g[j] == 0] + [(eg, j) for j in range(2) if eg[j] == 0] \
                or [(t2g, j) for j in range(3) if t2g[j] == 1] + [(eg, j) for j in range(2) if eg[j] == 1]
        else:
            cand = [(t2g, j) for j in range(3) if t2g[j] == 0] or [(t2g, j) for j in range(3) if t2g[j] == 1] \
                or [(eg, j) for j in range(2) if eg[j] == 0] or [(eg, j) for j in range(2) if eg[j] == 1]
        arr, j = cand[0]
        arr[j] += 1
    return sum(t2g), sum(eg)


# =============================================================================== query evaluation
def _claim_ok(val: sp.Basic, claim: str) -> bool:
    m = re.match(r"\s*(==|!=|<=|>=|<|>)\s*(.+)$", str(claim))
    if not m:
        raise RuleError(f"bad claim {claim!r}")
    op, rhs = m.groups()
    r = sp.sympify(rhs.strip())
    if op in ("==", "!="):
        eq = sp.simplify(val - r) == 0 if not isinstance(val, sp.Set) else val == r
        return eq if op == "==" else not eq
    return bool({"<": val < r, ">": val > r, "<=": val <= r, ">=": val >= r}[op])


def _round(val: sp.Expr, step: str) -> sp.Rational:
    st = sp.Rational(step)
    x = sp.N(val / st, 50)
    lo = sp.floor(x)
    if abs(float(x - lo) - 0.5) < 1e-9:
        raise RuleError(f"{val} lies on a rounding boundary")
    return sp.Rational(int(sp.floor(x + sp.Rational(1, 2)))) * st


def evaluate(q: dict, ctx: Ctx) -> tuple[sp.Basic, str]:
    kind = q.get("query", "value")
    if kind == "value":
        v, u = prop(q["property"], q["species"], q, ctx)
        if "round_to" in q:
            v = _round(v, q["round_to"])
            ctx.step(f"rounded to {q['round_to']}: {v}")
        return v, u
    if kind == "approx":
        v, u = prop(q["property"], q["species"], q, ctx)
        t, tol = sp.Rational(str(q["target"])), sp.Rational(str(q["tol"]))
        ok = abs(float(sp.N(v - t, 30))) <= float(tol)
        ctx.step(f"{q['species']}: {q['property']} = {v} ~ {float(sp.N(v)):.4f} vs printed {t} "
                 f"(tolerance {tol}): {'match' if ok else 'no match'}")
        return sp.Integer(1 if ok else 0), ""
    if kind == "count":
        n = 0
        for s in q["species"]:
            v, _ = prop(q["property"], s, q, ctx)
            ok = _claim_ok(v, q["claim"])
            ctx.step(f"  {s}: {q['property']} = {v} -> {'counted' if ok else 'not counted'}")
            n += ok
        return sp.Integer(n), ""
    if kind == "select":
        chosen = []
        for lab, s in q["species"].items():
            v, _ = prop(q["property"], s, q, ctx)
            ok = _claim_ok(v, q["claim"])
            ctx.step(f"  ({lab}) {s}: {q['property']} = {v} -> {ok}")
            if ok:
                chosen.append(_label_index(lab))
        return (sp.FiniteSet(*sorted(chosen)) if chosen else sp.S.EmptySet), ""
    if kind == "all":
        res = True
        for chk in q["checks"]:
            if "curated" in chk:
                ctx.curated.append((bool(chk["curated"]), chk.get("note", "")))
                res = res and bool(chk["curated"])
                continue
            v, _ = evaluate(chk, ctx)
            ok = _claim_ok(v, chk["claim"])
            ctx.step(f"  check {chk.get('species', '')} {chk.get('property', chk.get('query'))} = {v} "
                     f"{chk['claim']}: {ok}")
            res = res and ok
        return sp.Integer(1 if res else 0), ""
    if kind == "all_equal":
        vals = [(s, prop(q["property"], s, q, ctx)[0]) for s in q["species"]]
        ok = all(v == vals[0][1] for _, v in vals)
        ctx.step(f"{q['property']}: {[(s, str(v)) for s, v in vals]} -> {'all equal' if ok else 'not all equal'}")
        return sp.Integer(1 if ok else 0), ""
    if kind == "expr":
        vals = {}
        unit = ""
        for name, sub in q["terms"].items():
            vals[name], unit = evaluate(sub, ctx)
        from cqse.math.expr import parse
        e = parse(q["expr"], {n: sp.Symbol(n) for n in vals})
        out = sp.nsimplify(e.subs({sp.Symbol(n): v for n, v in vals.items()}))
        ctx.step(f"{q['expr']} with {dict((k, str(v)) for k, v in vals.items())} = {out}")
        return out, q.get("unit", unit if len(vals) == 1 else "")
    if kind == "pick":
        cands = []
        for s in q["species"]:
            if all(_claim_ok(prop(w["property"], s, w, ctx)[0], w["claim"]) for w in q.get("where", [])):
                cands.append(s)
        ctx.step(f"species satisfying {q.get('where', [])}: {cands}")
        if not cands:
            raise RuleError("no species satisfies the conditions")
        key = q.get("maximize") or q.get("minimize")
        scored = [(prop(key, s, q, ctx)[0], s) for s in cands]
        best = (max if "maximize" in q else min)(v for v, _ in scored)
        winners = [s for v, s in scored if sp.simplify(v - best) == 0]
        ctx.step(f"{'max' if 'maximize' in q else 'min'} {key}: {[(s, str(v)) for v, s in scored]} -> {winners}")
        if len(winners) != 1:
            raise RuleError(f"optimum not unique: {winners}")
        w = winners[0]
        th = q.get("then")
        if not th:
            return sp.Symbol(w), ""
        target = th.get("species_template", "{X}").replace("{X}", w)
        return prop(th["property"], target, th, ctx)
    if kind == "extremum":
        scored = []
        for lab, sub in q["values"].items():
            v = evaluate(sub, ctx)[0] if isinstance(sub, dict) else sp.Rational(str(sub))
            scored.append((v, lab))
        best = (max if q["select"] == "max" else min)(v for v, _ in scored)
        winners = [lab for v, lab in scored if sp.simplify(v - best) == 0]
        ctx.step(f"{q['select']} over {[(lab, str(v)) for v, lab in scored]} -> {winners}")
        if len(winners) != 1:
            raise RuleError("extremum not unique")
        if q.get("rule"):
            ctx.step(f"rule: {q['rule']}")
        return sp.FiniteSet(_label_index(winners[0])), ""
    if kind == "redox_extremum":
        role = q["role"]
        scored = []
        for lab, s in q["candidates"].items():
            key = "ox" if role == "oxidising" else "red"
            Es = [sp.Rational(str(c["E"])) for c in q["couples"] if c[key] == s]
            other = [c for c in q["couples"] if c["ox" if key == "red" else "red"] == s]
            if not Es and not other:
                raise RuleError(f"{s}: not in any given couple - no data")
            if not Es:
                ctx.step(f"({lab}) {s}: only appears as the {'reduced' if key == 'ox' else 'oxidised'} form - "
                         f"cannot act as {role} agent in the given couples")
                continue
            if len(Es) > 1:
                raise RuleError(f"{s}: appears in several couples in the same role")
            strength = Es[0] if role == "oxidising" else -Es[0]
            scored.append((strength, lab, Es[0]))
            ctx.step(f"({lab}) {s}: E0 = {Es[0]} V")
        if not scored:
            raise RuleError("no candidate can act in the requested role")
        best = max(v for v, _, _ in scored)
        winners = [lab for v, lab, _ in scored if v == best]
        if len(winners) != 1:
            raise RuleError("tie")
        ctx.step(f"strongest {role} agent: {'highest' if role == 'oxidising' else 'lowest'} E0(reduction) "
                 f"-> ({winners[0]})")
        ctx.cross(f"rule: E0(red) higher => oxidised form stronger oxidant; lower => reduced form stronger reductant")
        return sp.FiniteSet(_label_index(winners[0])), ""
    if kind == "combine_potentials":
        return combine_potentials(q, ctx), "V"
    if kind == "cell":
        return cell(q, ctx)
    if kind == "nernst":
        return nernst(q, ctx), "V"
    raise RuleError(f"unknown query {kind!r}")


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - registry signature
    out = EngineResult()
    ctx = Ctx()
    try:
        val, unit = evaluate(formal, ctx)
    except RuleError as e:
        out.records.append(VerificationRecord(
            check_id="chem.rules", status=CheckStatus.UNRESOLVED, method=f"versioned rule set: {RULESET}",
            tool=TOOL, result=f"outside rule tables / methods disagree: {e}", assumptions=ctx.assumptions))
        out.steps = ctx.steps
        return out
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as e:
        out.records.append(VerificationRecord(
            check_id="chem.rules", status=CheckStatus.UNRESOLVED, method=f"versioned rule set: {RULESET}",
            tool=TOOL, result=f"malformed formal or unsupported input: {type(e).__name__}: {e}"))
        return out
    out.value, out.unit, out.steps = val, unit, list(ctx.steps)
    out.records.append(VerificationRecord(
        check_id="chem.rule_value", status=CheckStatus.RULE_CHECKED, method=f"versioned rule set: {RULESET}",
        tool=TOOL, tool_version="1.0", result=f"value {val}{' ' + unit if unit else ''}",
        assumptions=list(ctx.assumptions), domain_coverage="Z = 1..86; main-group VSEPR; diatomic MO (Z <= 18)",
        data={"steps": ctx.steps}))
    if ctx.crosses:
        out.records.append(VerificationRecord(
            check_id="chem.rule_cross_check", status=CheckStatus.RULE_CHECKED,
            method="two independent rule computations agree", tool=TOOL, result="; ".join(ctx.crosses)[:2000]))
    for truth, note in ctx.curated:
        out.records.append(VerificationRecord(
            check_id="statement.truth", status=CheckStatus.UNRESOLVED, method="curated sub-check",
            result=f"curated as {truth} - teacher must confirm: {note}", assumptions=[note]))
    for p in formal.get("premises", []):
        out.records.append(VerificationRecord(
            check_id="chem.reaction_feasibility", status=CheckStatus.UNRESOLVED, method="curated premise",
            result=f"premise needs chemist confirmation: {p.get('statement', '')}",
            assumptions=[p.get("note", ""), f"basis: {p.get('basis', 'curated')}"]))
    return out
