"""Redox engine (kind = "redox"): oxidation numbers, ion-electron balancing, n-factors, reaction types.

Every answer is established by two independent methods that must agree, or by a versioned rule table;
otherwise the engine fails closed (value None + hard UNRESOLVED record).

  * oxidation number (average)   (a) sequential NCERT rule assignment from the formula (F -1; group 1/2, Al fixed;
                                     H +1 / -1 in metal hydrides; O -2; polyatomic groups; most-electronegative
                                     unknown takes its group valence; last unknown by charge balance), or the
                                     curated per-atom value for a STRUCTURE-table species
                                 (b) an independent route: cqse.chemistry.rules.oxidation_state (directly, or by
                                     charge balance over its values for the other elements), ionic / ligand
                                     fragment decomposition, or per-atom ONs computed from a Lewis bond list
                                     (ON = formal charge + sum over bonds of +order (partner more electronegative)
                                     / -order (partner less electronegative)); per-atom values must sum to the
                                     charge and match the curated table
  * balanced redox equation       (a) ion-electron (half-reaction) method run as an algorithm: partition species
                                     into oxidation / reduction halves by ON change, balance each half (redox
                                     atoms, O with H2O, H with H+, charge with e-), scale by lcm of electrons,
                                     add, convert to basic medium with OH- if asked, reduce to smallest integers
                                 (b) cqse.chemistry.engine.balance (unique nullspace) on the full equation with
                                     H+/H2O (or OH-/H2O) tried on every side / omitted; exactly one balancing
                                     must exist and it must equal (a)
  * n-factor                     (a) electrons in the balanced half-reaction per formula unit (ion-electron)
                                 (b) sum over atoms of |ON change| from the ON tables alone (no coefficients)
  * redox / disproportionation   (a) coefficient-free comparison of the (element, ON) states on both sides
                                 (b) multiset of atom states using the nullspace-balanced coefficients
  * reaction type                (a) species-pattern rule (elements vs compounds; NCERT XI 8.3)
                                 (b) ON-pattern rule (free element oxidised/reduced, element liberated ...)
  * redox capability of an ON    (a) group extremes table (max = valence electrons, min = valence - 8 ...)
                                 (b) curated list of known oxidation states; classifications must agree

Formal schema:  {"kind": "redox", "query": Q, ..., "premises": [{"statement": ..., "note": ...}]}

Queries (a "sub-query" is any of these dicts without "kind"):
  oxidation_state  {"species": "H2SO5", "element": "S", "which": "average"|"max"|"min"|"count_distinct"}
  on_change        {"from": "MnO4^-", "to": "Mn^2+", "element": "Mn"}     -> |ON(to) - ON(from)| per atom
  balance          {"equation": "MnO4^- + C2O4^2- -> Mn^2+ + CO2", "medium": "acidic"|"basic"|None,
                    "half": false (true: add e- as a free species), "scale_to": {"MnO4^-": 2},
                    "return": "coefficient" (+"species") | "code" (+"species": [..], base 1000)
                              | "expr" (+"map": {"X": "H^+"}, "expr": "X+Y") | "electrons"
                              | "ratio" (+"species": [A, B])}
  verify_equation  {"equation": "<with explicit coefficients>"} -> 1 if atoms + charge balance and the
                    coefficients equal (a multiple of) the unique balancing, else 0
  n_factor         {"equation": ..., "species": S, "medium": ...}       (skeleton half-reactions allowed)
  equivalent_weight {... n_factor fields ..., "atomic_masses": {...}}  -> M / n
  stoich           {"equation": ..., "given": {"I^-": "0.02"}, "target": "IO3^-"} -> mol of target
  role             {"equation": ..., "species": S} -> Symbol oxidant | reductant | both | neither
  is_redox | is_disproportionation | is_comproportionation  {"equation": ...} -> 1 / 0
  reaction_type    {"equation": ...} -> Symbol disproportionation | comproportionation | displacement |
                    decomposition | combination | other_redox | non_redox  (precedence in that order)
  capability       {"species": S, "element": X} -> Symbol both | oxidant_only | reductant_only | neither
  all / count      {"checks": [SUBQ + {"claim": "== 5"} | {"curated": bool, "note": ...}]} -> 1/0 | Integer
  expr             {"terms": {"x": SUBQ | {"formal": OTHER_KIND_FORMAL, "subject": ...}}, "expr": "x + y"}
  equivalence      {"n_factors": {"nA": SUBQ, ...}, "system": EQUATION_SYSTEM_FORMAL}
                    -> the n-factors are computed here and injected as dimensionless knowns of the system
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.core.result import EngineResult

RULESET = "cqse-redox 1.0 (NCERT XI Ch.8 conventions; structure table v1)"
TOOL = f"cqse.chemistry.redox 1.0; {RULESET}; sympy {sp.__version__}"
R = sp.Rational


class RedoxError(ValueError):
    """Outside the rule tables, methods disagree, or ill-posed input -> UNRESOLVED (never guessed)."""


# =============================================================================== element data
G1 = {"Li", "Na", "K", "Rb", "Cs"}
G2 = {"Be", "Mg", "Ca", "Sr", "Ba"}
NONMETALS = {"H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "As", "Se", "Br", "Te", "I", "Xe", "Kr"}
# Pauling electronegativities (for the Lewis method and the "most electronegative unknown" rule).
EN = {"H": 2.20, "Li": 0.98, "Be": 1.57, "B": 2.04, "C": 2.55, "N": 3.04, "O": 3.44, "F": 3.98, "Na": 0.93,
      "Mg": 1.31, "Al": 1.61, "Si": 1.90, "P": 2.19, "S": 2.58, "Cl": 3.16, "K": 0.82, "Ca": 1.00, "Ti": 1.54,
      "V": 1.63, "Cr": 1.66, "Mn": 1.55, "Fe": 1.83, "Co": 1.88, "Ni": 1.91, "Cu": 1.90, "Zn": 1.65,
      "As": 2.18, "Se": 2.55, "Br": 2.96, "Ag": 1.93, "Sn": 1.96, "Sb": 2.05, "Te": 2.10, "I": 2.66,
      "Xe": 2.60, "Ba": 0.89, "W": 2.36, "Pt": 2.28, "Au": 2.54, "Hg": 2.00, "Pb": 2.33, "Mo": 2.16,
      "Tl": 1.62, "Bi": 2.02, "Sr": 0.95, "Cs": 0.79, "Rb": 0.82}
NEG_VALENCE = {"F": -1, "Cl": -1, "Br": -1, "I": -1, "O": -2, "S": -2, "Se": -2, "Te": -2, "N": -3, "P": -3,
               "As": -3, "C": -4, "Si": -4, "H": -1}

# Method (a) of the capability rule: extreme oxidation states. Main group: max = valence (s+p) electrons
# (O +2, F 0 exceptions), min = valence - 8 for non-metals, 0 for metals. d-block: explicit (NCERT XII 8).
_VALENCE = {"H": 1, "Li": 1, "Na": 1, "K": 1, "Rb": 1, "Cs": 1, "Be": 2, "Mg": 2, "Ca": 2, "Sr": 2, "Ba": 2,
            "B": 3, "Al": 3, "Tl": 3, "C": 4, "Si": 4, "Sn": 4, "Pb": 4, "N": 5, "P": 5, "As": 5, "Sb": 5,
            "Bi": 5, "O": 6, "S": 6, "Se": 6, "Te": 6, "F": 7, "Cl": 7, "Br": 7, "I": 7, "Xe": 8}
D_MAX = {"Sc": 3, "Ti": 4, "V": 5, "Cr": 6, "Mn": 7, "Fe": 6, "Co": 4, "Ni": 4, "Cu": 2, "Zn": 2, "Mo": 6,
         "W": 6, "Ag": 1, "Au": 3, "Hg": 2, "Pt": 6, "Cd": 2}


def limits(el: str) -> tuple[int, int]:
    if el in D_MAX:
        return 0, D_MAX[el]
    if el not in _VALENCE:
        raise RedoxError(f"no oxidation-state limits tabulated for {el}")
    v = _VALENCE[el]
    if el == "H":
        return -1, 1
    if el == "O":
        return -2, 2
    if el == "F":
        return -1, 0
    if el == "Xe":
        return 0, 8
    lo = v - 8 if el in NONMETALS else 0
    return lo, v


# Method (b): curated list of known oxidation states (NCERT XI Ch.8 / XII Ch.7-8; versioned).
KNOWN_STATES = {
    "H": [-1, 0, 1], "Li": [0, 1], "Na": [0, 1], "K": [0, 1], "Rb": [0, 1], "Cs": [0, 1],
    "Be": [0, 2], "Mg": [0, 2], "Ca": [0, 2], "Sr": [0, 2], "Ba": [0, 2], "B": [-3, 0, 3], "Al": [0, 3],
    "Tl": [0, 1, 3], "C": [-4, -3, -2, -1, 0, 1, 2, 3, 4], "Si": [-4, 0, 4], "Sn": [0, 2, 4], "Pb": [0, 2, 4],
    "N": [-3, -2, -1, 0, 1, 2, 3, 4, 5], "P": [-3, 0, 1, 3, 4, 5], "As": [-3, 0, 3, 5], "Sb": [-3, 0, 3, 5],
    "Bi": [-3, 0, 3, 5], "O": [-2, -1, R(-1, 2), 0, 1, 2], "S": [-2, -1, 0, 2, 4, 6], "Se": [-2, 0, 4, 6],
    "Te": [-2, 0, 4, 6], "F": [-1, 0], "Cl": [-1, 0, 1, 3, 4, 5, 6, 7], "Br": [-1, 0, 1, 3, 5, 7],
    "I": [-1, 0, 1, 3, 5, 7], "Xe": [0, 2, 4, 6, 8], "Ti": [0, 2, 3, 4], "V": [0, 2, 3, 4, 5],
    "Cr": [0, 2, 3, 6], "Mn": [0, 2, 3, 4, 6, 7], "Fe": [0, 2, 3, 6], "Co": [0, 2, 3, 4], "Ni": [0, 2, 4],
    "Cu": [0, 1, 2], "Zn": [0, 2], "Ag": [0, 1], "Au": [0, 1, 3], "Hg": [0, 1, 2], "Mo": [0, 6],
    "W": [0, 6], "Pt": [0, 2, 4, 6], "Sc": [0, 3], "Cd": [0, 2]}

# Polyatomic groups used when more than one element is still unknown (method a).
GROUPS = [("CN", {"C": 1, "N": 1}, -1, {"C": 2, "N": -3}),
          ("NH4", {"N": 1, "H": 4}, 1, {"N": -3}),
          ("NO3", {"N": 1, "O": 3}, -1, {"N": 5}),
          ("SO4", {"S": 1, "O": 4}, -2, {"S": 6}),
          ("PO4", {"P": 1, "O": 4}, -3, {"P": 5}),
          ("C2O4", {"C": 2, "O": 4}, -2, {"C": 3}),
          ("CO3", {"C": 1, "O": 3}, -2, {"C": 4}),
          ("ClO4", {"Cl": 1, "O": 4}, -1, {"Cl": 7})]

# =============================================================================== structure table (v1)
# Species whose individual atoms differ from the formula average, or that the formula rules cannot fix.
# "per_atom": curated textbook values; "lewis": (atoms [(el, formal_charge)], bonds [(i, j, order)]);
# "fragments": [(species, count)] + optional ("remainder", element, count) -> remainder by charge balance.
STRUCTURES: dict[str, dict] = {
    "H2O2": {"per_atom": {"H": [1, 1], "O": [-1, -1]},
             "lewis": ([("H", 0), ("O", 0), ("O", 0), ("H", 0)], [(0, 1, 1), (1, 2, 1), (2, 3, 1)]),
             "note": "peroxide H-O-O-H"},
    "Na2O2": {"per_atom": {"Na": [1, 1], "O": [-1, -1]}, "fragments": [("Na^+", 2), ("O2^2-", 1)],
              "note": "sodium peroxide"},
    "K2O2": {"per_atom": {"K": [1, 1], "O": [-1, -1]}, "fragments": [("K^+", 2), ("O2^2-", 1)],
             "note": "potassium peroxide"},
    "BaO2": {"per_atom": {"Ba": [2], "O": [-1, -1]}, "fragments": [("Ba^2+", 1), ("O2^2-", 1)],
             "note": "barium peroxide"},
    "KO2": {"per_atom": {"K": [1], "O": [R(-1, 2), R(-1, 2)]}, "fragments": [("K^+", 1), ("O2^-", 1)],
            "note": "potassium superoxide (O2^-)"},
    "H2SO5": {"per_atom": {"H": [1, 1], "S": [6], "O": [-1, -1, -2, -2, -2]},
              "lewis": ([("H", 0), ("O", 0), ("O", 0), ("S", 0), ("O", 0), ("O", 0), ("O", 0), ("H", 0)],
                        [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 2), (3, 5, 2), (3, 6, 1), (6, 7, 1)]),
              "note": "Caro's acid HO-O-S(=O)2-OH (one peroxide bridge)"},
    "H2S2O8": {"per_atom": {"H": [1, 1], "S": [6, 6], "O": [-1, -1] + [-2] * 6},
               "lewis": ([("H", 0), ("O", 0), ("S", 0), ("O", 0), ("O", 0), ("O", 0), ("O", 0), ("S", 0),
                          ("O", 0), ("O", 0), ("O", 0), ("H", 0)],
                         [(0, 1, 1), (1, 2, 1), (2, 3, 2), (2, 4, 2), (2, 5, 1), (5, 6, 1), (6, 7, 1),
                          (7, 8, 2), (7, 9, 2), (7, 10, 1), (10, 11, 1)]),
               "note": "Marshall's acid HO-S(=O)2-O-O-S(=O)2-OH"},
    "S2O8^2-": {"per_atom": {"S": [6, 6], "O": [-1, -1] + [-2] * 6},
                "lewis": ([("O", -1), ("S", 0), ("O", 0), ("O", 0), ("O", 0), ("O", 0), ("S", 0),
                           ("O", 0), ("O", 0), ("O", -1)],
                          [(0, 1, 1), (1, 2, 2), (1, 3, 2), (1, 4, 1), (4, 5, 1), (5, 6, 1), (6, 7, 2),
                           (6, 8, 2), (6, 9, 1)]),
                "note": "peroxodisulphate"},
    "CrO5": {"per_atom": {"Cr": [6], "O": [-2, -1, -1, -1, -1]},
             "lewis": ([("Cr", 0), ("O", 0), ("O", 0), ("O", 0), ("O", 0), ("O", 0)],
                       [(0, 1, 2), (0, 2, 1), (0, 3, 1), (2, 3, 1), (0, 4, 1), (0, 5, 1), (4, 5, 1)]),
             "note": "chromium peroxide CrO(O2)2 (butterfly structure)"},
    "S4O6^2-": {"per_atom": {"S": [5, 0, 0, 5], "O": [-2] * 6},
                "lewis": ([("O", -1), ("S", 0), ("O", 0), ("O", 0), ("S", 0), ("S", 0), ("S", 0), ("O", 0),
                           ("O", 0), ("O", -1)],
                          [(0, 1, 1), (1, 2, 2), (1, 3, 2), (1, 4, 1), (4, 5, 1), (5, 6, 1), (6, 7, 2),
                           (6, 8, 2), (6, 9, 1)]),
                "note": "tetrathionate -O3S-S-S-SO3-: terminal S +5, bridging S 0 (average +5/2)"},
    "S2O3^2-": {"per_atom": None, "note": "thiosulphate: per-atom values are convention-dependent "
                                          "(+5/-1, +6/-2 or +4/0 in different texts); only the average +2 is "
                                          "asserted"},
    "Fe3O4": {"per_atom": {"Fe": [2, 3, 3], "O": [-2] * 4}, "fragments": [("FeO", 1), ("Fe2O3", 1)],
              "note": "mixed oxide FeO.Fe2O3"},
    "Pb3O4": {"per_atom": {"Pb": [2, 2, 4], "O": [-2] * 4}, "fragments": [("PbO", 2), ("PbO2", 1)],
              "note": "red lead 2PbO.PbO2"},
    "Mn3O4": {"per_atom": {"Mn": [2, 3, 3], "O": [-2] * 4}, "fragments": [("MnO", 1), ("Mn2O3", 1)],
              "note": "mixed oxide MnO.Mn2O3"},
    "N3^-": {"per_atom": {"N": [-1, 1, -1]},
             "lewis": ([("N", -1), ("N", 1), ("N", -1)], [(0, 1, 2), (1, 2, 2)]),
             "note": "azide [N=N=N]^- (average -1/3)"},
    "HN3": {"per_atom": {"H": [1], "N": [-1, 1, -1]},
            "lewis": ([("H", 0), ("N", 0), ("N", 1), ("N", -1)], [(0, 1, 1), (1, 2, 2), (2, 3, 2)]),
            "note": "hydrazoic acid H-N=N+=N- (average -1/3)"},
    "NaN3": {"per_atom": {"Na": [1], "N": [-1, 1, -1]}, "fragments": [("Na^+", 1), ("N3^-", 1)],
             "note": "sodium azide"},
    "C3O2": {"per_atom": {"C": [2, 0, 2], "O": [-2, -2]},
             "lewis": ([("O", 0), ("C", 0), ("C", 0), ("C", 0), ("O", 0)],
                       [(0, 1, 2), (1, 2, 2), (2, 3, 2), (3, 4, 2)]),
             "note": "carbon suboxide O=C=C=C=O (average +4/3)"},
    "CH3COOH": {"per_atom": {"C": [-3, 3], "H": [1] * 4, "O": [-2, -2]},
                "lewis": ([("C", 0), ("H", 0), ("H", 0), ("H", 0), ("C", 0), ("O", 0), ("O", 0), ("H", 0)],
                          [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1), (4, 5, 2), (4, 6, 1), (6, 7, 1)]),
                "note": "acetic acid (average C 0)"},
    "C2H5OH": {"per_atom": {"C": [-3, -1], "H": [1] * 6, "O": [-2]},
               "lewis": ([("C", 0), ("H", 0), ("H", 0), ("H", 0), ("C", 0), ("H", 0), ("H", 0), ("O", 0),
                          ("H", 0)],
                         [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1), (4, 5, 1), (4, 6, 1), (4, 7, 1),
                          (7, 8, 1)]),
               "note": "ethanol (average C -2)"},
    "CN^-": {"per_atom": {"C": [2], "N": [-3]},
             "lewis": ([("C", -1), ("N", 0)], [(0, 1, 3)]), "note": "cyanide [:C#N:]^-"},
    "Fe(CO)5": {"per_atom": {"Fe": [0], "C": [2] * 5, "O": [-2] * 5},
                "lewis": ([("Fe", -5)] + [("C", 0), ("O", 1)] * 5,
                          [b for k in range(5) for b in ((0, 1 + 2 * k, 1), (1 + 2 * k, 2 + 2 * k, 3))]),
                "note": "iron pentacarbonyl: neutral CO ligands, M<-C dative bonds"},
    "Ni(CO)4": {"per_atom": {"Ni": [0], "C": [2] * 4, "O": [-2] * 4},
                "lewis": ([("Ni", -4)] + [("C", 0), ("O", 1)] * 4,
                          [b for k in range(4) for b in ((0, 1 + 2 * k, 1), (1 + 2 * k, 2 + 2 * k, 3))]),
                "note": "nickel tetracarbonyl"},
    "[Fe(H2O)5(NO)]^2+": {"per_atom": {"Fe": [1], "N": [3], "O": [-2] * 6, "H": [1] * 10},
                          "fragments": [("H2O", 5), ("NO^+", 1)], "remainder": ("Fe", 1),
                          "note": "brown-ring complex; NO bound as nitrosonium NO+ (NCERT convention)"},
    "CrO2Cl2": {"per_atom": {"Cr": [6], "O": [-2, -2], "Cl": [-1, -1]},
                "lewis": ([("Cr", 0), ("O", 0), ("O", 0), ("Cl", 0), ("Cl", 0)],
                          [(0, 1, 2), (0, 2, 2), (0, 3, 1), (0, 4, 1)]),
                "note": "chromyl chloride"},
    "POCl3": {"per_atom": {"P": [5], "O": [-2], "Cl": [-1, -1, -1]},
              "lewis": ([("P", 0), ("O", 0), ("Cl", 0), ("Cl", 0), ("Cl", 0)],
                        [(0, 1, 2), (0, 2, 1), (0, 3, 1), (0, 4, 1)]), "note": "phosphoryl chloride"},
    "SO2Cl2": {"per_atom": {"S": [6], "O": [-2, -2], "Cl": [-1, -1]},
               "lewis": ([("S", 0), ("O", 0), ("O", 0), ("Cl", 0), ("Cl", 0)],
                         [(0, 1, 2), (0, 2, 2), (0, 3, 1), (0, 4, 1)]), "note": "sulphuryl chloride"},
    "XeOF4": {"per_atom": {"Xe": [6], "O": [-2], "F": [-1] * 4},
              "lewis": ([("Xe", 0), ("O", 0)] + [("F", 0)] * 4,
                        [(0, 1, 2)] + [(0, k, 1) for k in range(2, 6)]), "note": "xenon oxytetrafluoride"},
    "XeO2F2": {"per_atom": {"Xe": [6], "O": [-2, -2], "F": [-1, -1]},
               "lewis": ([("Xe", 0), ("O", 0), ("O", 0), ("F", 0), ("F", 0)],
                         [(0, 1, 2), (0, 2, 2), (0, 3, 1), (0, 4, 1)]), "note": "xenon dioxydifluoride"},
    "NH4NO3": {"per_atom": {"N": [-3, 5], "H": [1] * 4, "O": [-2] * 3},
               "fragments": [("NH4^+", 1), ("NO3^-", 1)], "note": "ammonium nitrate"},
    "NH4NO2": {"per_atom": {"N": [-3, 3], "H": [1] * 4, "O": [-2] * 2},
               "fragments": [("NH4^+", 1), ("NO2^-", 1)], "note": "ammonium nitrite"},
    "(NH4)2Cr2O7": {"per_atom": {"N": [-3, -3], "H": [1] * 8, "Cr": [6, 6], "O": [-2] * 7},
                    "fragments": [("NH4^+", 2), ("Cr2O7^2-", 1)], "note": "ammonium dichromate"},
}
MEDIUM = {"H^+", "OH^-", "H2O", "e^-"}


# =============================================================================== context
@dataclass
class Ctx:
    steps: list[str] = field(default_factory=list)
    crosses: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    curated: list[tuple[bool, str]] = field(default_factory=list)
    pending: list[VerificationRecord] = field(default_factory=list)
    exact: bool = False          # a balancing was established (EXACT_CHECKED record)

    def step(self, s):
        if s not in self.steps:
            self.steps.append(s)

    def cross(self, s):
        if s not in self.crosses:
            self.crosses.append(s)

    def assume(self, s):
        if s not in self.assumptions:
            self.assumptions.append(s)


def _parse(text: str):
    from cqse.chemistry.engine import FormulaError, parse_formula
    try:
        return parse_formula(text)
    except FormulaError as e:
        raise RedoxError(f"cannot parse species {text!r}: {e}")


def _key(text: str) -> str:
    return text.replace(" ", "")


# =============================================================================== oxidation numbers
def _rule_assign(text: str, fixed_out: Optional[set] = None) -> dict[str, sp.Rational]:
    """Method (a): sequential NCERT rules -> average ON of every element. Raises when the formula alone
    cannot fix the values (structure-dependent species must be in STRUCTURES)."""
    s = _parse(text)
    atoms, q = dict(s.atoms), s.charge
    if len(atoms) == 1:
        (el, n), = atoms.items()
        return {el: R(q, n)}
    k_nh4 = min(atoms.get("N", 0), atoms.get("H", 0) // 4)
    if k_nh4 >= 1 and atoms["N"] > k_nh4 and "O" in atoms:
        raise RedoxError(f"{text}: N may sit in two environments (ammonium salt of an N oxoanion) - "
                         "structure table needed")
    known: dict[str, sp.Rational] = {}
    for e in atoms:
        if e == "F":
            known[e] = R(-1)
        elif e in G1:
            known[e] = R(1)
        elif e in G2:
            known[e] = R(2)
        elif e == "Al":
            known[e] = R(3)
    if "H" in atoms:
        others = [e for e in atoms if e != "H"]
        known["H"] = R(-1) if all(e not in NONMETALS for e in others) else R(1)
    if "O" in atoms and "F" not in atoms:
        known["O"] = R(-2)
    if fixed_out is not None:
        fixed_out |= set(known)
    sol = _assign_search(text, atoms, q, dict(known))
    if sol is None:
        raise RedoxError(f"{text}: no admissible rule assignment (peroxide/superoxide, M-M bond or unusual "
                         "bonding?) - structure table needed")
    return sol


def _assign_search(text, atoms, q, known, depth=0):
    """Ordered depth-first search (NCERT priority: polyatomic groups in GROUPS order, then the most
    electronegative unknown at its group valence); a group is used only if k copies cover every atom of its
    element. The first complete assignment that closes the charge inside the oxidation-state limits wins;
    method (b) cross-checks it independently."""
    unknown = [e for e in atoms if e not in known]
    if depth > 6:
        return None
    if len(unknown) <= 1:
        k = dict(known)
        if unknown:
            u = unknown[0]
            k[u] = R(q - sum(k[e] * n for e, n in atoms.items() if e != u), atoms[u])
        if sum(k[e] * n for e, n in atoms.items()) != q:
            return None
        for e, v in k.items():
            lo, hi = limits(e)
            if not (lo <= v <= hi):
                return None
        return k
    for name, comp, gq, ons in GROUPS:
        tg = {e: R(v) for e, v in ons.items() if e in unknown}
        if not tg:
            continue
        t0 = next(iter(tg))
        if atoms.get(t0, 0) % comp[t0]:
            continue
        kk = atoms[t0] // comp[t0]
        if not all(atoms.get(e, 0) >= n * kk for e, n in comp.items()):
            continue
        if any(e in known and e in ons and known[e] != ons[e] for e in comp):
            continue
        r = _assign_search(text, atoms, q, {**known, **tg}, depth + 1)
        if r is not None:
            return r
    cand = sorted(unknown, key=lambda e: -EN.get(e, 0))
    top = cand[0]
    if top in NEG_VALENCE and EN.get(top, 0) > EN.get(cand[1], 0):
        return _assign_search(text, atoms, q, {**known, top: R(NEG_VALENCE[top])}, depth + 1)
    return None


def _lewis_per_atom(atoms: list, bonds: list) -> dict[str, list]:
    on = [R(fc) for _, fc in atoms]
    deg = [0] * len(atoms)
    for i, j, o in bonds:
        ei, ej = EN[atoms[i][0]], EN[atoms[j][0]]
        if ei > ej:
            on[i] -= o
            on[j] += o
        elif ej > ei:
            on[i] += o
            on[j] -= o
        deg[i] += 1
        deg[j] += 1
    out: dict[str, list] = {}
    for (el, _), v in zip(atoms, on):
        out.setdefault(el, []).append(v)
    return out


def _rules_py_value(text: str, el: str, fixed: set, a: dict) -> Optional[tuple[str, sp.Rational]]:
    """Independent implementation in cqse.chemistry.rules: directly, or by charge balance over its values for
    the other non-fixed elements (fixed-rule elements enter with their definitional values)."""
    from cqse.chemistry.rules import Ctx as RCtx, oxidation_state as rules_os
    try:
        return "cqse.chemistry.rules", sp.Rational(rules_os(text, el, RCtx()))
    except Exception:  # noqa: BLE001 - not applicable
        pass
    s = _parse(text)
    tot = 0
    for e, n in s.atoms.items():
        if e == el:
            continue
        if e in fixed:
            tot += a[e] * n
            continue
        try:
            tot += sp.Rational(rules_os(text, e, RCtx())) * n
        except Exception:  # noqa: BLE001
            return None
    return "charge balance over cqse.chemistry.rules values", R(s.charge - tot, s.atoms[el])


def _fragments_per_atom(text: str, entry: dict, depth: int) -> dict[str, list]:
    s = _parse(text)
    out: dict[str, list] = {}
    comp: Counter = Counter()
    qsum = 0
    for ftext, cnt in entry["fragments"]:
        fs = _parse(ftext)
        rep = species_on(ftext, depth + 1)
        for _ in range(cnt):
            for e, vals in rep["per_atom_or_avg"].items():
                out.setdefault(e, []).extend(vals)
        for e, n in fs.atoms.items():
            comp[e] += n * cnt
        qsum += fs.charge * cnt
    if "remainder" in entry:
        el, n = entry["remainder"]
        out.setdefault(el, []).extend([R(s.charge - qsum, n)] * n)
        comp[el] += n
        qsum = s.charge
    if dict(comp) != dict(s.atoms) or qsum != s.charge:
        raise RedoxError(f"{text}: fragments {entry['fragments']} do not add up to the species")
    return out


ANIONS = {"CN": -1, "NO3": -1, "NO2": -1, "SO4": -2, "C2O4": -2, "CO3": -2, "OH": -1, "Cl": -1, "Br": -1,
          "I": -1, "ClO4": -1, "PO4": -3}
LIGANDS = {"CN": ("CN^-", -1), "H2O": ("H2O", 0), "NH3": ("NH3", 0), "CO": ("CO", 0), "Cl": ("Cl^-", -1),
           "C2O4": ("C2O4^2-", -2), "OH": ("OH^-", -1)}


def _ion(text: str, q: int) -> str:
    if q == 0:
        return text
    return f"{text}^{abs(q) if abs(q) != 1 else ''}{'+' if q > 0 else '-'}"


def _auto_fragments(text: str) -> Optional[list[tuple[str, int]]]:
    """Independent ionic decomposition: hydrate/adduct dots; [complex] + counter-ions; metal + polyatomic
    anion; complex ion -> metal + ligands (ligand charges from a ligand table)."""
    t = _key(text)
    if re.search(r"[.·*]", t) and "^" not in t:
        parts = re.split(r"[.·*]", t)
        out = []
        for i, p in enumerate(parts):
            m = re.match(r"^(\d+)(.*)$", p)
            out.append((m.group(2), int(m.group(1))) if (m and i > 0) else (p, 1))
        return out
    an = "|".join(sorted(ANIONS, key=len, reverse=True))
    m = re.fullmatch(rf"\[([^\]]+)\](?:\(({an})\)(\d*)|({an})(\d*))", t)
    if m:
        ion = m.group(2) or m.group(4)
        n = int(m.group(3) or m.group(5) or 1)
        cq = -ANIONS[ion] * n
        return [(_ion(f"[{m.group(1)}]", cq), 1), (_ion(ion, ANIONS[ion]), n)]
    m = re.fullmatch(r"(K|Na)(\d*)\[([^\]]+)\]", t)
    if m:
        n = int(m.group(2) or 1)
        return [(f"{m.group(1)}^+", n), (_ion(f"[{m.group(3)}]", -n), 1)]
    m = re.fullmatch(rf"([A-Z][a-z]?)(\d*)(?:\(({an})\)(\d+)|({an}))", t)
    if m and m.group(1) not in NONMETALS:
        ion = m.group(3) or m.group(5)
        nm, na = int(m.group(2) or 1), int(m.group(4) or 1)
        q = -ANIONS[ion] * na
        if q % nm:
            return None
        return [(_ion(m.group(1), q // nm), nm), (_ion(ion, ANIONS[ion]), na)]
    lg = "|".join(sorted(LIGANDS, key=len, reverse=True))
    m = re.fullmatch(rf"\[?([A-Z][a-z]?)((?:\((?:{lg})\)\d*)+)\]?(?:\^(\d*)([+-]))?", t)
    if m and m.group(1) not in NONMETALS:
        q = (int(m.group(3) or 1) * (1 if m.group(4) == "+" else -1)) if m.group(4) else 0
        out, lq = [], 0
        for L, n in re.findall(r"\(([A-Za-z0-9]+)\)(\d*)", m.group(2)):
            ftext, fq = LIGANDS[L]
            out.append((ftext, int(n or 1)))
            lq += fq * int(n or 1)
        return [(_ion(m.group(1), q - lq), 1)] + out
    return None


def species_on(text: str, depth: int = 0) -> dict:
    """Average ON per element (two methods) and per-atom values where established.
    Returns {"avg": {el: v}, "per_atom": {el: [..]} | None, "per_atom_or_avg": {...}, "method": str}."""
    if depth > 4:
        raise RedoxError("fragment recursion too deep")
    k = _key(text)
    s = _parse(text)
    entry = STRUCTURES.get(k)
    if entry is not None and entry.get("per_atom") is not None:
        cur = {e: [R(v) for v in vals] for e, vals in entry["per_atom"].items()}
        if "lewis" in entry:
            comp = _lewis_per_atom(*entry["lewis"])
            how = "Lewis bond list"
        elif "fragments" in entry:
            comp = _fragments_per_atom(text, entry, depth)
            how = "ionic/ligand fragments"
        else:
            raise RedoxError(f"{text}: table entry without a structure check")
        if {e: sorted(v) for e, v in comp.items()} != {e: sorted(v) for e, v in cur.items()}:
            raise RedoxError(f"{text}: curated per-atom ONs {cur} disagree with {how} {comp}")
        cnt = {e: len(v) for e, v in cur.items()}
        if cnt != dict(s.atoms):
            raise RedoxError(f"{text}: table atom count {cnt} != formula {dict(s.atoms)}")
        tot = sum(sum(v) for v in cur.values())
        if tot != s.charge:
            raise RedoxError(f"{text}: per-atom ONs sum to {tot}, charge is {s.charge}")
        avg = {e: sum(v) / len(v) for e, v in cur.items()}
        return {"avg": avg, "per_atom": cur, "per_atom_or_avg": cur,
                "method": f"structure table v1 (curated) == {how}; sum = charge {s.charge}",
                "note": entry.get("note", "")}
    # ---- method (a)
    fixed: set = set()
    a = _rule_assign(text, fixed)
    # ---- method (b): independent routes for every element not fixed by a definitional rule; at least one
    #      route must apply and all applicable routes must agree. Fixed-rule elements (F, group 1/2, Al, H, O)
    #      are confirmed by closure: the independently computed values + fixed values sum to the charge.
    routes = []
    frag = _auto_fragments(text)
    for el in s.atoms:
        if el in fixed and len(s.atoms) > 1:
            continue
        vals = []
        if len(s.atoms) == 1:
            vals.append(("homoatomic: charge / atoms", R(s.charge, s.atoms[el])))
        else:
            v = _rules_py_value(text, el, fixed, a)
            if v is not None:
                vals.append(v)
        if frag:
            try:
                fv = []
                for ftext, cnt in frag:
                    fr = species_on(ftext, depth + 1)
                    if el in fr["avg"]:
                        fv.append((fr["avg"][el], _parse(ftext).atoms[el] * cnt))
                if fv:
                    num = sum(x * n for x, n in fv)
                    vals.append(("ionic/ligand fragments", num / sum(n for _, n in fv)))
            except RedoxError:
                pass
        if not vals:
            raise RedoxError(f"{text}: no independent second method for {el} (rule assignment gave {a[el]})")
        for name, v in vals:
            if v != a[el]:
                raise RedoxError(f"{text}: ON of {el} rule assignment {a[el]} != {name} {v}")
        routes.append(f"{el} {a[el]} ({', '.join(n for n, _ in vals)})")
    if len(s.atoms) > 1 and fixed & set(s.atoms):
        routes.append(f"fixed-rule {sorted(fixed & set(s.atoms))} confirmed by charge closure")
    per = None
    if entry is not None:  # tabulated but per-atom convention-dependent (e.g. S2O3^2-)
        note = entry.get("note", "")
    else:
        note = ""
        if all(n == 1 for n in s.atoms.values()) or len(s.atoms) == 1:
            per = {e: [a[e]] * n for e, n in s.atoms.items()}
    return {"avg": a, "per_atom": per, "per_atom_or_avg": {e: [a[e]] * n for e, n in s.atoms.items()},
            "method": "rule assignment == " + "; ".join(routes), "note": note}


def oxidation_state(text: str, el: str, ctx: Ctx, which: str = "average") -> sp.Basic:
    rep = species_on(text)
    if el not in rep["avg"]:
        raise RedoxError(f"{el} not in {text}")
    ctx.step(f"ON in {text}: {dict((e, str(v)) for e, v in rep['avg'].items())} [{rep['method']}]"
             + (f" ({rep['note']})" if rep.get("note") else ""))
    ctx.cross(f"{text}: {rep['method']}")
    if which == "average":
        return rep["avg"][el]
    if rep["per_atom"] is None and not (len(set([rep["avg"][el]])) == 1 and _parse(text).atoms[el] == 1):
        raise RedoxError(f"{text}: per-atom ONs of {el} not established (only the average {rep['avg'][el]})")
    vals = (rep["per_atom"] or {el: [rep["avg"][el]]})[el]
    if which == "max":
        return max(vals)
    if which == "min":
        return min(vals)
    if which == "count_distinct":
        return sp.Integer(len(set(vals)))
    raise RedoxError(f"unknown 'which' {which!r}")


# =============================================================================== equations
@dataclass
class Eq:
    text: str
    left: list[tuple[Optional[int], str]]
    right: list[tuple[Optional[int], str]]
    medium: Optional[str]
    on: dict[str, dict[str, sp.Rational]]      # species -> element -> average ON
    pa: Optional[dict] = None                  # species -> element -> per-atom ON list (avg repeated if unknown)

    @property
    def names(self):
        return [n for _, n in self.left] + [n for _, n in self.right]


def parse_eq(text: str, medium: Optional[str] = None) -> Eq:
    from cqse.chemistry.engine import FormulaError, parse_reaction
    text = re.sub(r"(^|\s)(\d+)e\^", r"\1\2 e^", text.strip())
    try:
        rx = parse_reaction(text)
    except FormulaError as e:
        raise RedoxError(f"cannot parse equation {text!r}: {e}")
    left = [(c, _key(s.text)) for c, s in rx.reactants]
    right = [(c, _key(s.text)) for c, s in rx.products]
    names = [n for _, n in left + right]
    if len(set(names)) != len(names):
        raise RedoxError(f"species repeated on both sides of {text!r}")
    inferred = "acidic" if "H^+" in names else ("basic" if "OH^-" in names else None)
    if "H^+" in names and "OH^-" in names:
        raise RedoxError("both H+ and OH- in one equation")
    if medium and inferred and medium != inferred:
        raise RedoxError(f"medium {medium} contradicts species in the equation ({inferred})")
    reps = {n: species_on(n) for n in names if n != "e^-"}
    on = {n: r["avg"] for n, r in reps.items()}
    eq = Eq(text, left, right, medium or inferred, on)
    eq.pa = _pa_table(eq, reps)
    return eq


def _pa_table(eq: Eq, reps: dict) -> dict:
    """ON states used by reaction analysis, chosen per element:
      * every species holding it has exact per-atom ONs (curated structure, one atom, or an element)
          -> per atom  (NH4NO2 -> N2; NH4NO3 -> NH4+ + NO3- is correctly NOT redox)
      * otherwise, the averages hide the change completely (no average-ON link) although a species holds the
        element at different per-atom ONs -> curated per-atom ONs, other species at their average
          (NH4NO3 -> N2O: N -3, +5 -> +1, textbook comproportionation)
      * otherwise averages (S2O3 2- -> S4O6 2-: +2 -> +2.5, as textbooks treat it). If the mixed per-atom reading
        would classify differently, refuse - unless a species holding the element is recorded as
        convention-dependent (thiosulphate), where textbooks use averages by definition."""
    avg_linked = {l[2] for l in _links(eq)}
    els = {el for r in reps.values() for el in r["avg"]}
    exact, mixed_cur, conv_dep = {}, set(), set()
    for n, r in reps.items():
        atoms = _parse(n).atoms
        ent = STRUCTURES.get(n)
        for el in r["avg"]:
            ok = bool(r["per_atom"] and el in r["per_atom"]) or atoms[el] == 1 or len(atoms) == 1
            exact[el] = exact.get(el, True) and ok
            if r["per_atom"] and len(set(r["per_atom"].get(el, []))) > 1:
                mixed_cur.add(el)
            if ent is not None and ent.get("per_atom") is None and atoms[el] > 1:
                conv_dep.add(el)

    def table(per_atom_els):
        out = {}
        for n, r in reps.items():
            atoms = _parse(n).atoms
            out[n] = {el: (list(r["per_atom"][el]) if el in per_atom_els and r["per_atom"] and el in r["per_atom"]
                           else [r["avg"][el]] * atoms[el]) for el in r["avg"]}
        return out

    use = {el for el in els if exact[el] or (el in mixed_cur and el not in avg_linked)}
    pa = table(use)
    for el in mixed_cur - use - conv_dep:
        a_cls = _link_class(eq, pa, el)
        b_cls = _link_class(eq, table(use | {el}), el)
        if a_cls != b_cls:
            raise RedoxError(f"{eq.text!r}: {el} classified {a_cls} with average ONs but {b_cls} per atom - "
                             "convention needed")
    return pa


def _link_class(eq: Eq, pa: dict, el: str) -> tuple[bool, bool, bool]:
    links = [l for l in _state_links(Eq(eq.text, eq.left, eq.right, eq.medium, eq.on, pa)) if l[2] == el]
    disp = any({l[3] for l in links if (l[0], l[4]) == k} == {1, -1} for k in {(l[0], l[4]) for l in links})
    comp = any({l[3] for l in links if (l[1], l[5]) == k} == {1, -1} for k in {(l[1], l[5]) for l in links})
    return bool(links), disp, comp


def _per_atom(eq: Eq, n: str) -> dict[str, list]:
    if eq.pa is not None and n in eq.pa:
        return eq.pa[n]
    r = species_on(n)
    return {el: [r["avg"][el]] * _parse(n).atoms[el] for el in r["avg"]}


def _vec_norm(v: dict[str, sp.Rational], first: str) -> dict[str, int]:
    v = {k: sp.Rational(x) for k, x in v.items() if x != 0}
    den = reduce(sp.ilcm, [sp.fraction(x)[1] for x in v.values()], 1)
    v = {k: x * den for k, x in v.items()}
    g = reduce(sp.igcd, [abs(int(x)) for x in v.values()], 0)
    v = {k: int(x / g) for k, x in v.items()}
    if v.get(first, -1) > 0:
        v = {k: -x for k, x in v.items()}
    return v


def balance_nullspace(eq: Eq, half: bool = False) -> dict[str, int]:
    """Method (b): existing unique-nullspace balancer, medium species tried on each side or omitted."""
    import itertools

    from cqse.chemistry.engine import FormulaError, Reaction, balance, parse_formula
    extra = []
    med = {"acidic": ["H^+", "H2O"], "basic": ["OH^-", "H2O"], None: [], "neutral": ["H2O"]}[eq.medium]
    for m in med + (["e^-"] if half else []):
        if m not in eq.names:
            extra.append(m)
    sols = set()
    base_l = [parse_formula(n) for _, n in eq.left]
    base_r = [parse_formula(n) for _, n in eq.right]
    for place in itertools.product((None, "L", "R"), repeat=len(extra)):
        L, Rr = list(base_l), list(base_r)
        for m, p in zip(extra, place):
            if p == "L":
                L.append(parse_formula(m))
            elif p == "R":
                Rr.append(parse_formula(m))
        try:
            co = balance(Reaction([(None, x) for x in L], [(None, x) for x in Rr]))
        except FormulaError:
            continue
        nl = len(L)
        vec = {}
        for i, (c, x) in enumerate(zip(co, L + Rr)):
            vec[_key(x.text)] = -c if i < nl else c
        sols.add(tuple(sorted(_vec_norm(vec, eq.left[0][1]).items())))
    if len(sols) != 1:
        raise RedoxError(f"nullspace balancing: {len(sols)} admissible balancings for {eq.text!r}")
    return dict(sols.pop())


def _links(eq: Eq):
    """(reactant, product, element, +1 oxidation / -1 reduction) for every ON change."""
    out = []
    for _, r in eq.left:
        if r == "e^-":
            continue
        for _, p in eq.right:
            if p == "e^-":
                continue
            for el, a in eq.on[r].items():
                b = eq.on[p].get(el)
                if b is None or b == a:
                    continue
                # a medium species (H2O, H+, OH-) holding the element at the product's ON could be the source,
                # or one holding it at the reactant's ON could be the destination: no electron transfer implied
                if any(n in MEDIUM and n != r and eq.on[n].get(el) == b for _, n in eq.left if n != "e^-"):
                    continue
                if any(n in MEDIUM and n != p and eq.on[n].get(el) == a for _, n in eq.right if n != "e^-"):
                    continue
                out.append((r, p, el, 1 if b > a else -1))
    return out


def _state_links(eq: Eq):
    """Per-atom version of _links: (reactant, product, element, +1/-1, source ON, destination ON).
    For each reactant/product pair, ON states of an element present in both are carried over unchanged; the
    remaining (unmatched) states are linked. With one state per species this is exactly _links; with per-atom
    states it sees intramolecular redox (NH4NO2 -> N2: N -3 and +3 -> 0) that averages hide."""
    out = []
    for _, r in eq.left:
        if r == "e^-":
            continue
        sr = _per_atom(eq, r)
        for _, p in eq.right:
            if p == "e^-":
                continue
            sp_ = _per_atom(eq, p)
            for el in sr:
                if el not in sp_:
                    continue
                A, B = set(sr[el]), set(sp_[el])
                common = A & B
                for a in sorted(A - common):
                    for b in sorted(B - common):
                        if any(n in MEDIUM and n != r and eq.on[n].get(el) == b for _, n in eq.left if n != "e^-"):
                            continue
                        if any(n in MEDIUM and n != p and eq.on[n].get(el) == a for _, n in eq.right if n != "e^-"):
                            continue
                        out.append((r, p, el, 1 if b > a else -1, a, b))
    return out


def _balance_half(species_l: list[str], species_r: list[str], redox_els: set[str], ctx: Ctx, tag: str
                  ) -> dict[str, sp.Rational]:
    sp_all = species_l + species_r
    atoms = {n: _parse(n).atoms for n in sp_all}
    els = sorted({e for n in sp_all for e in atoms[n] if e not in ("H", "O")} | (redox_els & {"H", "O"}))
    if not els:
        raise RedoxError(f"{tag}: nothing to balance")
    M = sp.Matrix([[atoms[n].get(e, 0) * (-1 if i < len(species_l) else 1) for i, n in enumerate(sp_all)]
                   for e in els])
    ns = M.nullspace()
    if len(ns) != 1:
        raise RedoxError(f"{tag}: redox-atom balance not unique ({len(ns)} solutions)")
    v = ns[0]
    if any(x == 0 for x in v):
        raise RedoxError(f"{tag}: a species gets coefficient 0")
    if all(x < 0 for x in v):
        v = -v
    if any(x < 0 for x in v):
        raise RedoxError(f"{tag}: no positive redox-atom balance")
    vec = {n: (-v[i] if i < len(species_l) else v[i]) for i, n in enumerate(sp_all)}

    def tot(el):  # right - left
        return sum(c * atoms[n].get(el, 0) for n, c in vec.items() if n not in ("H2O", "H^+", "e^-")) + \
            sum(c * {"H2O": {"H": 2, "O": 1}, "H^+": {"H": 1}}.get(n, {}).get(el, 0)
                for n, c in vec.items() if n in ("H2O", "H^+"))

    dO = tot("O")
    if dO:
        vec["H2O"] = vec.get("H2O", 0) - dO          # add |dO| water on the O-deficient side
    dH = tot("H")
    if dH:
        vec["H^+"] = vec.get("H^+", 0) - dH
    q = sum(c * _parse(n).charge for n, c in vec.items())
    if q:
        vec["e^-"] = vec.get("e^-", 0) + q           # q > 0: right more positive -> e- on the right
    ctx.step(f"{tag}: " + _fmt(vec))
    return vec


def _fmt(vec: dict) -> str:
    L = [f"{-c if -c != 1 else ''}{n}" for n, c in vec.items() if c < 0]
    Rr = [f"{c if c != 1 else ''}{n}" for n, c in vec.items() if c > 0]
    return " + ".join(L) + " -> " + " + ".join(Rr)


def _half_species(eq: Eq, ls: list) -> tuple[list[str], list[str]]:
    """Species of one half: the ON-linked ones, closed under 'an element (not H/O) present on only one side
    is supplied by an unchanged species of the equation holding it at the same ON' (e.g. I- in
    2Cu2+ + 2I- + 2e- -> Cu2I2)."""
    Lh = {l[0] for l in ls}
    Rh = {l[1] for l in ls}
    lnames = [n for _, n in eq.left if n not in MEDIUM]
    rnames = [n for _, n in eq.right if n not in MEDIUM]
    for _ in range(6):
        changed = False
        for side, other, pool in ((Lh, Rh, rnames), (Rh, Lh, lnames)):
            for n in list(side):
                for el, v in eq.on[n].items():
                    if el in ("H", "O") or any(el in eq.on[m] for m in other):
                        continue
                    cands = [m for m in pool if eq.on[m].get(el) == v and m not in other]
                    if len(cands) == 1:
                        other.add(cands[0])
                        changed = True
        if not changed:
            break
    return [n for _, n in eq.left if n in Lh], [n for _, n in eq.right if n in Rh]


def balance_ion_electron(eq: Eq, ctx: Ctx, half: bool = False) -> tuple[dict[str, int], sp.Rational]:
    """Method (a): ion-electron method. Returns (normalised coefficients, electrons transferred)."""
    links = _links(eq)
    ox = [l for l in links if l[3] > 0]
    red = [l for l in links if l[3] < 0]
    built = []
    for tag, ls in (("oxidation half", ox), ("reduction half", red)):
        if ls:
            built.append((tag, ls) + _half_species(eq, ls))
    used = {n for b in built for n in b[2] + b[3]}
    for _, n in eq.left + eq.right:
        if n in used or n in MEDIUM:
            continue
        els = {e for e in eq.on[n] if e not in ("H", "O")}
        homes = [i for i, b in enumerate(built) if any(els & set(eq.on[m]) for m in b[2] + b[3])]
        if len(homes) != 1:
            raise RedoxError(f"half-reaction method: cannot place {n} (no ON change) in a unique half-reaction")
        b = built[homes[0]]
        (b[2] if n in [x for _, x in eq.left] else b[3]).append(n)
    halves = []
    for tag, ls, Lh, Rh in built:
        halves.append((tag, _balance_half(Lh, Rh, {l[2] for l in ls}, ctx, tag)))
    if not halves:
        raise RedoxError("no oxidation-number change: not a redox equation")
    if len(halves) == 1 and not (half or "e^-" in eq.names):
        raise RedoxError("only one half-reaction found in a full equation")
    if len(halves) == 2 and "e^-" in eq.names:
        raise RedoxError("electrons written in an equation with two half-reactions")
    total: dict[str, sp.Rational] = {}
    ne = [abs(h.get("e^-", 0)) for _, h in halves]
    if len(halves) == 2:
        L = sp.ilcm(*ne)
        for (_, h), n in zip(halves, ne):
            for k, c in h.items():
                total[k] = total.get(k, 0) + c * L / n
        if total.get("e^-", 0) != 0:
            raise RedoxError("electrons do not cancel")
        n_el = L
    else:
        total = dict(halves[0][1])
        n_el = ne[0]
    if eq.medium == "basic":
        s = total.pop("H^+", 0)
        if s:
            total["H2O"] = total.get("H2O", 0) + s
            total["OH^-"] = total.get("OH^-", 0) - s
    elif eq.medium is None and total.get("H^+", 0) != 0:
        raise RedoxError("H+ needed but no medium stated")
    first = eq.left[0][1]
    raw = {k: v for k, v in total.items() if v != 0}
    norm = _vec_norm(raw, first)
    scale = sp.Rational(norm[first], raw[first])
    n_el = sp.Rational(n_el) * abs(scale)
    ctx.step(f"ion-electron result: {_fmt(norm)}; electrons transferred {n_el}")
    return norm, n_el


def balanced(eq: Eq, ctx: Ctx, half: bool = False) -> tuple[dict[str, int], sp.Rational]:
    a, n = balance_ion_electron(eq, ctx, half)
    b = balance_nullspace(eq, half=half or "e^-" in eq.names)
    if a != b:
        raise RedoxError(f"ion-electron {a} != nullspace {b}")
    for c, nm in eq.left:
        if b.get(nm, 0) > 0:
            raise RedoxError(f"{nm} written as reactant but balances as product")
    for c, nm in eq.right:
        if b.get(nm, 0) < 0:
            raise RedoxError(f"{nm} written as product but balances as reactant")
    # electron bookkeeping cross-check from ON changes and the balanced coefficients
    if "e^-" not in b and not half:
        lost = _electron_flow(eq, b)
        if lost != n:
            raise RedoxError(f"ON bookkeeping gives {lost} electrons, ion-electron gives {n}")
        ctx.cross(f"electrons lost = electrons gained = {n} from ON changes x coefficients")
    ctx.cross(f"ion-electron method == unique nullspace balance: {_fmt(b)}")
    ctx.exact = True
    return b, n


def _electron_flow(eq: Eq, co: dict[str, int]) -> sp.Rational:
    """Total electrons lost, from the multisets of atom ON states (balanced coefficients)."""
    st_l, st_r = _states(eq, co)
    return _min_cost_up(st_l - st_r, st_r - st_l)


def _states(eq: Eq, co: dict[str, int], per_atom: bool = False) -> tuple[Counter, Counter]:
    L, Rr = Counter(), Counter()
    for n in co:
        if n == "e^-":
            continue
        c = co.get(n, 0)
        if per_atom:
            pairs = [(el, v, 1) for el, vals in _per_atom(eq, n).items() for v in vals]
        else:
            els = eq.on[n] if n in eq.on else species_on(n)["avg"]
            pairs = [(el, v, _parse(n).atoms[el]) for el, v in els.items()]
        for el, v, m in pairs:
            k = abs(c) * m
            if c < 0:
                L[(el, v)] += k
            elif c > 0:
                Rr[(el, v)] += k
    return L, Rr


def _hidden_by_average(eq: Eq) -> set[str]:
    """Elements whose redox change is invisible to average ONs but visible per atom (intramolecular redox,
    e.g. NH4NO2 -> N2). Role / n-factor are computed from averages, so they must refuse these."""
    try:
        co = balance_nullspace(eq, half="e^-" in eq.names)
    except RedoxError:
        return set()
    la, ra = _states(eq, co)
    lp, rp = _states(eq, co, per_atom=True)
    avg_ch = {e for e, _ in (la - ra) + (ra - la)}
    pa_ch = {e for e, _ in (lp - rp) + (rp - lp)}
    return pa_ch - avg_ch


def _min_cost_up(gone: Counter, new: Counter) -> sp.Rational:
    """Electrons lost = sum over elements of upward ON movement; for each element the vanished states
    (reactant side) turn into the new states (product side); with a single source or single sink ON per
    element this is unique."""
    total = sp.Integer(0)
    for el in {e for e, _ in list(gone) + list(new)}:
        g = [(v, k) for (e, v), k in gone.items() if e == el]
        n = [(v, k) for (e, v), k in new.items() if e == el]
        if sum(k for _, k in g) != sum(k for _, k in n):
            raise RedoxError(f"atom count of {el} not conserved")
        if len(g) == 1:
            src = g[0][0]
            total += sum(k * max(0, v - src) for v, k in n)
        elif len(n) == 1:
            dst = n[0][0]
            total += sum(k * max(0, dst - v) for v, k in g)
        elif g or n:
            raise RedoxError(f"{el}: several source and destination ONs - electron count ambiguous")
    return total


# =============================================================================== reaction analysis
def _is_element(n: str) -> bool:
    s = _parse(n)
    return len(s.atoms) == 1 and s.charge == 0


def analyse(eq: Eq, ctx: Ctx) -> dict[str, Any]:
    links = _state_links(eq)
    redox_a = bool(links)
    # (a) coefficient-free, per atom state: disproportionation = one source state goes both up and down;
    #     comproportionation = one destination state is reached from below and from above
    disp_a = comp_a = False
    for key in {(l[0], l[2], l[4]) for l in links}:
        dirs = {l[3] for l in links if (l[0], l[2], l[4]) == key}
        if dirs == {1, -1}:
            disp_a = True
    for key in {(l[1], l[2], l[5]) for l in links}:
        dirs = {l[3] for l in links if (l[1], l[2], l[5]) == key}
        if dirs == {1, -1}:
            comp_a = True
    # (b) balanced multisets
    try:
        co = balance_nullspace(eq, half="e^-" in eq.names)
    except RedoxError as e:
        raise RedoxError(f"equation {eq.text!r} cannot be balanced uniquely - check transcription ({e})")
    st_l, st_r = _states(eq, co, per_atom=True)
    gone, new = st_l - st_r, st_r - st_l
    redox_b = bool(gone or new)
    disp_b = comp_b = False
    for el in {e for e, _ in list(gone) + list(new)}:
        g = sorted(v for (e, v) in gone if e == el)
        n = sorted(v for (e, v) in new if e == el)
        if len(g) == 1 and n and min(n) < g[0] < max(n):
            disp_b = True
        if len(n) == 1 and g and min(g) < n[0] < max(g):
            comp_b = True
    if (redox_a, disp_a, comp_a) != (redox_b, disp_b, comp_b):
        raise RedoxError(f"ON-link analysis (redox {redox_a}, disp {disp_a}, comp {comp_a}) != balanced "
                         f"atom-state analysis ({redox_b}, {disp_b}, {comp_b})")
    ctx.cross(f"{eq.text}: redox={redox_a}, disproportionation={disp_a}, comproportionation={comp_a} "
              "(coefficient-free ON links == balanced atom-state multisets)")
    # reaction type: (a) species pattern, (b) ON pattern
    EXCL = {"H^+", "OH^-", "e^-"}
    L = [n for _, n in eq.left if n not in EXCL]
    Rr = [n for _, n in eq.right if n not in EXCL]
    elL = [n for n in L if _is_element(n)]
    elR = [n for n in Rr if _is_element(n)]
    sym = lambda n: next(iter(_parse(n).atoms))  # noqa: E731
    displ_a = bool(len(L) >= 2 and any(sym(a) != sym(b) and any(sym(a) in _parse(c).atoms for c in Rr if c != a)
                                       and any(sym(b) in _parse(c).atoms for c in L if c != b)
                                       for a in elL for b in elR))
    decomp_a = len(L) == 1 and len(Rr) >= 2
    combo_a = len(L) >= 2 and bool(elL) and not elR
    al, ar = _states(eq, co)            # type rules: free element = average ON 0 (S4O6 2- holds per-atom 0 S)
    ag, an = al - ar, ar - al
    freed = {e for (e, v) in an if v == 0} - {e for (e, v) in ag if v == 0}
    bound = {e for (e, v) in ag if v == 0} - {e for (e, v) in an if v == 0}
    displ_b = bool(freed and bound and freed != bound)
    decomp_b = len({n for n, c in co.items() if c < 0 and n not in EXCL}) == 1 and \
        len({n for n, c in co.items() if c > 0 and n not in EXCL}) >= 2
    combo_b = bool(bound) and not freed and len({n for n, c in co.items() if c < 0 and n not in EXCL}) >= 2
    if "e^-" not in eq.names and (displ_a, decomp_a, combo_a) != (displ_b, decomp_b, combo_b):
        raise RedoxError(f"type rules disagree: pattern {(displ_a, decomp_a, combo_a)} vs ON "
                         f"{(displ_b, decomp_b, combo_b)}")
    if "e^-" in eq.names:
        typ = "half_reaction"
    elif not redox_a:
        typ = "non_redox"
    elif disp_a:
        typ = "disproportionation"
    elif comp_a:
        typ = "comproportionation"
    elif displ_a:
        typ = "displacement"
    elif decomp_a:
        typ = "decomposition"
    elif combo_a:
        typ = "combination"
    else:
        typ = "other_redox"
    ctx.step(f"{eq.text}: ON changes {[(l[0], l[1], l[2], f'{l[4]}->{l[5]}', 'ox' if l[3] > 0 else 'red') for l in links]}; "
             f"type = {typ}")
    return {"redox": redox_a, "disproportionation": disp_a, "comproportionation": comp_a, "type": typ,
            "links": links, "coeffs": co}


def role(eq: Eq, species: str, ctx: Ctx) -> str:
    sp_ = _key(species)
    if sp_ not in eq.names:
        raise RedoxError(f"{species} not in equation")
    hidden = _hidden_by_average(eq)
    if hidden:
        raise RedoxError(f"intramolecular redox of {sorted(hidden)} in {eq.text!r}: average ONs hide it, "
                         "role / n-factor need per-atom treatment")
    links = _links(eq)
    left = sp_ in [n for _, n in eq.left]
    if left:
        ox = any(l[0] == sp_ and l[3] > 0 for l in links)
        rd = any(l[0] == sp_ and l[3] < 0 for l in links)
    else:
        raise RedoxError("role is defined for reactants")
    # (b) independent: electrons on the side of a half-reaction / sign of per-element ON sum change
    if "e^-" in eq.names:
        e_left = "e^-" in [n for _, n in eq.left]
        ox_b, rd_b = (not e_left), e_left
        if not (ox or rd):
            ox_b = rd_b = False
    else:
        ox_b = rd_b = False
        for el, a in eq.on[sp_].items():
            outs = [eq.on[p][el] for _, p in eq.right if p != "e^-" and el in eq.on[p]]
            if any(v > a for v in outs):
                ox_b = True
            if any(v < a for v in outs):
                rd_b = True
    if (ox, rd) != (ox_b, rd_b):
        raise RedoxError(f"role of {species}: ON links {(ox, rd)} != electron side / product ONs {(ox_b, rd_b)}")
    r = {(True, True): "both", (True, False): "reductant", (False, True): "oxidant",
         (False, False): "neither"}[(ox, rd)]
    ctx.step(f"{species} in {eq.text}: {'oxidised' if ox else ''}{' and ' if ox and rd else ''}"
             f"{'reduced' if rd else ''}{'no ON change' if not (ox or rd) else ''} -> {r}")
    ctx.cross(f"role of {species}: ON links == electron/product-ON check")
    return r


def n_factor(eq: Eq, species: str, ctx: Ctx) -> sp.Rational:
    s = _key(species)
    if s not in eq.names:
        raise RedoxError(f"{species} not in equation")
    hidden = _hidden_by_average(eq)
    if hidden:
        raise RedoxError(f"intramolecular redox of {sorted(hidden)} in {eq.text!r}: average ONs hide it, "
                         "role / n-factor need per-atom treatment")
    links = _links(eq)
    involved = [l for l in links if s in l[:2]]
    is_left = s in [n for _, n in eq.left]
    # (b) ON-only: per formula unit, sum over redox atoms of |dON|
    nb = sp.Integer(0)
    for el, v in eq.on[s].items():
        other = {(l[1] if is_left else l[0]) for l in involved if l[2] == el}
        dest = {eq.on[o][el] for o in other}
        if len(dest) > 1:
            raise RedoxError(f"{species}: {el} goes to several ONs {dest} - n-factor needs a convention")
        if dest:
            nb += abs(dest.pop() - v) * _parse(s).atoms[el]
    ups = {l[3] for l in involved}
    if len(ups) > 1:
        raise RedoxError(f"{species} is both oxidised and reduced - n-factor convention needed")
    if not involved:
        ctx.step(f"{species}: no ON change -> n-factor 0")
        ctx.cross(f"{species}: n = 0 (no atom changes ON)")
        return sp.Integer(0)
    # (a) electrons in the balanced half containing the species, per formula unit
    single_half = len({l[3] for l in links}) == 1
    sub = Eq(eq.text, eq.left, eq.right, eq.medium, eq.on, eq.pa)
    if single_half:
        co, _ = balanced(sub, ctx, half=True)
        na = sp.Rational(abs(co.get("e^-", 0)), abs(co[s]))
    else:
        direction = next(iter(ups))
        hl = [l for l in links if l[3] == direction]
        Lh, Rh = _half_species(eq, hl)
        h = _balance_half(Lh, Rh, {l[2] for l in hl}, ctx, "half containing " + species)
        na = sp.Rational(abs(h["e^-"]), abs(h[s]))
        balanced(sub, ctx)   # the full equation must balance consistently as well
    if na != nb:
        raise RedoxError(f"n-factor of {species}: ion-electron {na} != ON change {nb}")
    ctx.cross(f"n-factor of {species} = {na} (balanced half-reaction == sum of |ON change|)")
    ctx.step(f"n-factor of {species} = {na}")
    return na


def capability(text: str, el: str, ctx: Ctx) -> str:
    v = oxidation_state(text, el, ctx)
    lo, hi = limits(el)
    a = (v > lo, v < hi)
    ks = KNOWN_STATES.get(el)
    if ks is None:
        raise RedoxError(f"no known-state list for {el}")
    b = (any(x < v for x in ks), any(x > v for x in ks))
    if a != b:
        raise RedoxError(f"{el} at {v}: extremes rule {a} != known-state list {b}")
    r = {(True, True): "both", (True, False): "oxidant_only", (False, True): "reductant_only",
         (False, False): "neither"}[a]
    ctx.step(f"{text}: {el} at {v} within [{lo}, {hi}] -> can be reduced: {a[0]}, oxidised: {a[1]} -> {r}")
    ctx.cross(f"{text}/{el}: extremes table == known-state list")
    return r


# =============================================================================== query evaluation
def _claim_ok(val: sp.Basic, claim: str) -> bool:
    m = re.match(r"\s*(==|!=|<=|>=|<|>)\s*(.+)$", str(claim))
    if not m:
        raise RedoxError(f"bad claim {claim!r}")
    op, rhs = m.groups()
    r = sp.sympify(rhs.strip())
    if op in ("==", "!="):
        eq = sp.simplify(val - r) == 0
        return eq if op == "==" else not eq
    return bool({"<": val < r, ">": val > r, "<=": val <= r, ">=": val >= r}[op])


def _molar_mass(text: str, masses: Optional[dict]) -> sp.Rational:
    from cqse.chemistry.rules import ATOMIC_MASS
    s = _parse(text)
    tab = {k: sp.Rational(str(v)) for k, v in (masses or {}).items()}
    tot = 0
    for e, n in s.atoms.items():
        m = tab.get(e) if e in tab else (sp.Rational(ATOMIC_MASS[e]) if e in ATOMIC_MASS else None)
        if m is None:
            raise RedoxError(f"no atomic mass for {e}")
        tot += m * n
    return tot


def _sub_formal(spec: dict, ctx: Ctx) -> sp.Basic:
    from cqse.core.problem import Subject
    from cqse.verification.pipeline import canonical_answer, software_blocking
    can = canonical_answer(Subject(spec.get("subject", "CHEMISTRY")), spec["formal"])
    if can.value is None or software_blocking(can.records):
        raise RedoxError(f"sub-formal ({spec['formal'].get('kind')}) not established: "
                         f"{[r.result for r in can.records if not r.is_affirmative()][:2]}")
    ctx.pending += [r for r in can.records if r.hard and not r.is_affirmative()]
    ctx.step(f"sub-formal {spec['formal'].get('kind')}: {can.value} {can.units}")
    return can.value


def evaluate(q: dict, ctx: Ctx) -> sp.Basic:
    k = q.get("query")
    if k == "oxidation_state":
        return oxidation_state(q["species"], q["element"], ctx, q.get("which", "average"))
    if k == "on_change":
        a = oxidation_state(q["from"], q["element"], ctx)
        b = oxidation_state(q["to"], q["element"], ctx)
        ctx.step(f"{q['element']}: {q['from']} ({a}) -> {q['to']} ({b}): change {abs(b - a)} per atom")
        return abs(b - a)
    if k in ("balance", "n_factor", "equivalent_weight", "stoich", "role", "is_redox", "is_disproportionation",
             "is_comproportionation", "reaction_type", "has_type"):
        eq = parse_eq(q["equation"], q.get("medium"))
        if k == "balance":
            co, n = balanced(eq, ctx, half=q.get("half", False))
            co = {kk: sp.Rational(v) for kk, v in co.items()}
            for nm, want in q.get("scale_to", {}).items():
                f = sp.Rational(want) / abs(co[_key(nm)])
                co = {kk: v * f for kk, v in co.items()}
                n = n * f
            ret = q.get("return", "coefficient")
            ctx.step(f"balanced: {_fmt(co)}")
            if ret == "coefficient":
                return abs(co.get(_key(q["species"]), 0))
            if ret == "electrons":
                return n
            if ret == "ratio":
                a, b = (_key(x) for x in q["species"])
                return abs(co[a]) / abs(co[b])
            if ret == "code":
                vals = [abs(co.get(_key(x), 0)) for x in q["species"]]
                if any(v >= 1000 or not v.is_integer for v in vals):
                    raise RedoxError("code needs integer coefficients < 1000")
                return sum(v * 1000 ** (len(vals) - 1 - i) for i, v in enumerate(vals))
            if ret == "expr":
                from cqse.math.expr import parse
                syms = {nm: sp.Symbol(nm) for nm in q["map"]}
                e = parse(q["expr"], syms)
                return sp.nsimplify(e.subs({syms[nm]: abs(co.get(_key(s), 0)) for nm, s in q["map"].items()}))
            raise RedoxError(f"unknown return {ret!r}")
        if k in ("n_factor", "equivalent_weight"):
            n = n_factor(eq, q["species"], ctx)
            if k == "n_factor":
                return n
            if n == 0:
                raise RedoxError("n-factor 0: equivalent weight undefined")
            M = _molar_mass(q.get("formula", q["species"]), q.get("atomic_masses"))
            if "formula" in q:
                ctx.assume(f"n-factor of {q['formula']} taken from its ion {q['species']} in the equation")
            ctx.step(f"equivalent weight = M/n = {M}/{n}")
            return M / n
        if k == "stoich":
            co, _ = balanced(eq, ctx, half=q.get("half", False))
            (g, amt), = q["given"].items()
            v = sp.Rational(str(amt)) * abs(co[_key(q["target"])]) / abs(co[_key(g)])
            ctx.step(f"{q['target']} = {amt} x {abs(co[_key(q['target'])])}/{abs(co[_key(g)])} = {v} mol")
            return v
        if k == "role":
            return sp.Symbol(role(eq, q["species"], ctx))
        an = analyse(eq, ctx)
        if k == "is_redox":
            return sp.Integer(int(an["redox"]))
        if k == "is_disproportionation":
            return sp.Integer(int(an["disproportionation"]))
        if k == "is_comproportionation":
            return sp.Integer(int(an["comproportionation"]))
        if k == "reaction_type":
            return sp.Symbol(an["type"])
        return sp.Integer(int(an["type"] == q["type"]))
    if k == "verify_equation":
        from cqse.chemistry.engine import balance_report
        eq = parse_eq(q["equation"])
        from cqse.chemistry.engine import Reaction, parse_formula
        rx = Reaction([(c, parse_formula(n)) for c, n in eq.left], [(c, parse_formula(n)) for c, n in eq.right])
        given = [1 if c is None else c for c, _ in eq.left + eq.right]
        ok, probs = balance_report(rx, given)
        if ok:
            b = balance_nullspace(Eq(eq.text, eq.left, eq.right, None, eq.on, eq.pa), half=False)
            vec = {n: (-c if i < len(eq.left) else c) for i, (c, n) in enumerate(zip(given, eq.names))}
            same = _vec_norm(vec, eq.left[0][1]) == b
            if not same:
                raise RedoxError("atom/charge balance holds but differs from the unique balancing")
            ctx.cross("recount of atoms + charge == unique nullspace balancing")
        ctx.step(f"{q['equation']}: {'balanced' if ok else 'NOT balanced: ' + str(probs)}")
        ctx.exact = True
        return sp.Integer(int(ok))
    if k == "capability":
        return sp.Symbol(capability(q["species"], q["element"], ctx))
    if k in ("all", "count"):
        res = []
        for chk in q["checks"]:
            if "curated" in chk:
                ctx.curated.append((bool(chk["curated"]), chk.get("note", "")))
                res.append(bool(chk["curated"]))
                continue
            v = evaluate(chk, ctx)
            ok = _claim_ok(v, chk["claim"])
            ctx.step(f"  check {chk.get('query')} {chk.get('species', chk.get('equation', ''))} = {v} "
                     f"{chk['claim']}: {ok}")
            res.append(ok)
        return sp.Integer(int(all(res))) if k == "all" else sp.Integer(sum(res))
    if k == "expr":
        vals = {}
        for name, sub in q["terms"].items():
            vals[name] = _sub_formal(sub, ctx) if "formal" in sub else evaluate(sub, ctx)
        from cqse.math.expr import parse
        syms = {n: sp.Symbol(n) for n in vals}
        out = sp.nsimplify(parse(q["expr"], syms).subs({syms[n]: v for n, v in vals.items()}))
        ctx.step(f"{q['expr']} with {dict((kk, str(v)) for kk, v in vals.items())} = {out}")
        return out
    if k == "equivalence":
        import copy
        sysf = copy.deepcopy(q["system"])
        for name, sub in q["n_factors"].items():
            v = evaluate(sub, ctx)
            sysf.setdefault("knowns", {})[name] = {"value": str(v), "unit": ""}
            sysf.setdefault("model", []).append(f"{name} = {v} (n-factor from the redox engine)")
        sysf["kind"] = "equation_system"
        return _sub_formal({"formal": sysf, "subject": "CHEMISTRY"}, ctx)
    raise RedoxError(f"unknown query {k!r}")


def solve_and_verify(formal: dict, subject=None) -> EngineResult:  # noqa: ARG001 - registry signature
    out = EngineResult()
    ctx = Ctx()
    try:
        val = evaluate(formal, ctx)
    except (RedoxError, KeyError, ValueError, TypeError, ZeroDivisionError) as e:
        out.records.append(VerificationRecord(
            check_id="redox.rules", status=CheckStatus.UNRESOLVED, method=f"versioned rule set: {RULESET}",
            tool=TOOL, result=f"not established: {type(e).__name__}: {e}"[:1500], assumptions=ctx.assumptions))
        out.steps = list(ctx.steps)
        return out
    out.value, out.steps = val, list(ctx.steps)
    if formal.get("query") == "equivalence":
        out.unit = formal["system"].get("unknowns", {}).get(formal["system"].get("target"), {}).get("unit", "")
    out.records.append(VerificationRecord(
        check_id="redox.value", status=CheckStatus.RULE_CHECKED, method=f"versioned rule set: {RULESET}",
        tool=TOOL, tool_version="1.0", result=f"value {val}", assumptions=list(ctx.assumptions),
        domain_coverage="formula-rule ONs + structure table v1; ionic redox equations",
        data={"steps": ctx.steps[:60]}))
    if ctx.crosses:
        out.records.append(VerificationRecord(
            check_id="redox.cross_check", status=CheckStatus.EXACT_CHECKED if ctx.exact else CheckStatus.RULE_CHECKED,
            method="two independent methods agree", tool=TOOL, result="; ".join(ctx.crosses)[:2000]))
    for truth, note in ctx.curated:
        out.records.append(VerificationRecord(
            check_id="statement.truth", status=CheckStatus.UNRESOLVED, method="curated sub-check",
            result=f"curated as {truth} - teacher must confirm: {note}", assumptions=[note]))
    out.records += ctx.pending
    for p in formal.get("premises", []):
        out.records.append(VerificationRecord(
            check_id="chem.reaction_feasibility", status=CheckStatus.UNRESOLVED, method="curated premise",
            result=f"premise needs chemist confirmation: {p.get('statement', '')}",
            assumptions=[p.get("note", ""), f"basis: {p.get('basis', 'curated')}"]))
    return out
