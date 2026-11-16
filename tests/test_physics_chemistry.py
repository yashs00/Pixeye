from fractions import Fraction

import pytest
import sympy as sp

from cqse.chemistry.engine import FormulaError, balance, parse_formula, parse_reaction
from cqse.chemistry.engine import solve_and_verify as chem_solve
from cqse.core.evidence import CheckStatus
from cqse.physics.engine import dimension_check
from cqse.physics.engine import solve_and_verify as phys_solve


@pytest.mark.parametrize("formal,expected", [
    (dict(kind="projectile_level", u="20", theta_deg="30", g="10", target="range"), 20 * sp.sqrt(3)),
    (dict(kind="projectile_level", u="20", theta_deg="30", g="10", target="max_height"), 5),
    (dict(kind="projectile_level", u="20", theta_deg="30", g="10", target="time_of_flight"), 2),
    (dict(kind="projectile_level", u="10", theta_deg="45", g="10", target="range"), 10),
    (dict(kind="incline_friction", m="2", theta_deg="30", mu_s="0.7", mu_k="0.5", g="10",
          target="acceleration"), 0),                                  # static: tan30 < 0.7
    (dict(kind="incline_friction", m="2", theta_deg="30", mu_s="0.7", mu_k="0.5", g="10",
          target="friction_force"), 10),                               # mg sin30, NOT mu N
    (dict(kind="incline_friction", m="2", theta_deg="45", mu_s="0.5", mu_k="0.4", g="10",
          target="acceleration"), 3 * sp.sqrt(2)),
])
def test_physics_values(formal, expected):
    s = phys_solve(formal)
    assert sp.simplify(s.value - expected) == 0
    assert all(r.is_affirmative() for r in s.records)


def test_friction_threshold_is_ambiguous():
    s = phys_solve(dict(kind="incline_friction", m="2", theta_deg="45", mu_s="1", mu_k="0.4", g="10",
                        target="acceleration"))
    assert any(r.status == CheckStatus.FAILED for r in s.records)


def test_mu_k_greater_than_mu_s_rejected():
    s = phys_solve(dict(kind="incline_friction", m="2", theta_deg="45", mu_s="0.3", mu_k="0.4", g="10",
                        target="acceleration"))
    assert not all(r.is_affirmative() for r in s.records)


def test_dimension_check_catches_bad_formula():
    import math
    rec = dimension_check(lambda u, th, g: u * math.sin(th) / g + u, ("m/s", "radian", "m/s^2"), "s", "bad")
    assert rec.status == CheckStatus.FAILED


@pytest.mark.parametrize("f,atoms,charge", [
    ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}, 0),
    ("CuSO4.5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
    ("K4[Fe(CN)6]", {"K": 4, "Fe": 1, "C": 6, "N": 6}, 0),
    ("SO4^2-", {"S": 1, "O": 4}, -2),
])
def test_formula_parser(f, atoms, charge):
    s = parse_formula(f)
    assert s.atoms == atoms and s.charge == charge


def test_unknown_element_rejected():
    with pytest.raises(FormulaError):
        parse_formula("Xx2O")


@pytest.mark.parametrize("rx,coeffs", [
    ("C3H8 + O2 -> CO2 + H2O", [1, 5, 3, 4]),
    ("MnO4^- + Fe^2+ + H^+ -> Mn^2+ + Fe^3+ + H2O", [1, 5, 8, 1, 5, 4]),
    ("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2", [2, 16, 2, 2, 8, 5]),
])
def test_balancer(rx, coeffs):
    assert balance(parse_reaction(rx)) == coeffs


def test_non_unique_balancing_refused():
    # two independent reactions mixed: H2 + O2 -> H2O and H2O2 decomposition
    with pytest.raises(FormulaError):
        balance(parse_reaction("H2 + O2 -> H2O + H2O2"))


BASE = dict(kind="stoichiometry", given={"H2": {"mass_g": "4"}, "O2": {"mass_g": "48"}},
            atomic_masses={"H": "1", "O": "16"}, target={"species": "H2O", "quantity": "mass_g"})


def test_stoichiometry_value_and_feasibility_gate():
    s = chem_solve({**BASE, "reaction": "2 H2 + O2 -> 2 H2O"})
    assert s.value == Fraction(36) and s.limiting == "H2"
    feas = next(r for r in s.records if r.check_id == "chem.reaction_feasibility")
    assert feas.status == CheckStatus.UNRESOLVED  # never auto-passed


@pytest.mark.parametrize("rx", ["H2 + O2 -> 2 H2O", "2 H2 + 2 O2 -> 2 H2O", "H2 + O2 -> H2O2 + H2O"])
def test_unbalanced_or_wrong_equations_blocked(rx):
    s = chem_solve({**BASE, "reaction": rx})
    assert s.value is None or any(r.status in (CheckStatus.FAILED, CheckStatus.UNRESOLVED)
                                  for r in s.records if r.check_id != "chem.reaction_feasibility")


def test_missing_atomic_mass_refused():
    s = chem_solve({**BASE, "reaction": "2 H2 + O2 -> 2 H2O", "atomic_masses": {"H": "1"}})
    assert s.value is None
