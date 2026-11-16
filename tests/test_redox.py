"""Redox engine (kind "redox"): oxidation numbers, ion-electron balancing, n-factors, reaction types."""
import pytest
import sympy as sp

from cqse.chemistry import redox
from cqse.chemistry.redox import solve_and_verify
from cqse.core.evidence import CheckStatus
from cqse.engines import lookup


def run(**q):
    return solve_and_verify({"kind": "redox", **q})


def val(**q):
    r = run(**q)
    assert r.value is not None, [x.result for x in r.records]
    assert all(x.is_affirmative() for x in r.records if x.hard and x.check_id.startswith("redox")), \
        [x.result for x in r.records]
    return r.value


def blocked(**q):
    r = run(**q)
    assert r.value is None
    assert any(x.status == CheckStatus.UNRESOLVED and x.hard for x in r.records)
    return r


def test_registered():
    assert lookup("redox") is solve_and_verify


# ------------------------------------------------------------------ oxidation numbers
@pytest.mark.parametrize("species,el,expected", [
    ("H2SO5", "S", 6), ("CrO5", "Cr", 6), ("H2S2O8", "S", 6), ("S2O8^2-", "S", 6),
    ("S4O6^2-", "S", sp.Rational(5, 2)), ("S2O3^2-", "S", 2), ("Fe3O4", "Fe", sp.Rational(8, 3)),
    ("Pb3O4", "Pb", sp.Rational(8, 3)), ("KO2", "O", sp.Rational(-1, 2)), ("KO2", "K", 1),
    ("Na2O2", "O", -1), ("BaO2", "Ba", 2), ("N3^-", "N", sp.Rational(-1, 3)), ("HN3", "N", sp.Rational(-1, 3)),
    ("C3O2", "C", sp.Rational(4, 3)), ("CH3COOH", "C", 0), ("C2H5OH", "C", -2), ("OF2", "O", 2),
    ("O2F2", "O", 1), ("NaH", "H", -1), ("K2FeO4", "Fe", 6), ("Fe(CO)5", "Fe", 0), ("VO^2+", "V", 4),
    ("[Fe(H2O)5(NO)]^2+", "Fe", 1), ("(NH4)3PO4.12MoO3", "Mo", 6), ("CrO2Cl2", "Cr", 6),
    ("[Co(H2O)6](NO3)3", "Co", 3), ("Zn(CN)2", "Zn", 2), ("H4P2O6", "P", 4), ("FeC2O4", "Fe", 2),
])
def test_oxidation_numbers(species, el, expected):
    assert val(query="oxidation_state", species=species, element=el) == expected


@pytest.mark.parametrize("species,el,which,expected", [
    ("H2SO5", "O", "min", -2), ("H2SO5", "O", "max", -1), ("CrO5", "O", "count_distinct", 2),
    ("S4O6^2-", "S", "max", 5), ("S4O6^2-", "S", "min", 0), ("Fe3O4", "Fe", "min", 2),
    ("Pb3O4", "Pb", "max", 4), ("C3O2", "C", "max", 2), ("CH3COOH", "C", "min", -3), ("N3^-", "N", "max", 1),
])
def test_per_atom_values(species, el, which, expected):
    assert val(query="oxidation_state", species=species, element=el, which=which) == expected


def test_per_atom_structure_check_sums_to_charge():
    for name, entry in redox.STRUCTURES.items():
        if entry.get("per_atom") is None:
            continue
        rep = redox.species_on(name)
        assert sum(sum(v) for v in rep["per_atom"].values()) == redox._parse(name).charge, name


def test_thiosulphate_per_atom_is_convention_dependent():
    blocked(query="oxidation_state", species="S2O3^2-", element="S", which="max")


def test_unknown_or_unparseable_species_fail_closed():
    blocked(query="oxidation_state", species="Xq2O", element="O")
    # peroxide not in the structure table: formula rules cannot close the charge
    blocked(query="oxidation_state", species="Li2O2", element="O")
    # ammonium nitrite written as N2H4O2 is structure-dependent (two N environments)
    blocked(query="oxidation_state", species="N2H4O3", element="N")


def test_curated_table_disagreeing_with_lewis_blocks(monkeypatch):
    bad = dict(redox.STRUCTURES["H2SO5"])
    bad["per_atom"] = {"H": [1, 1], "S": [8], "O": [-2] * 5}
    monkeypatch.setitem(redox.STRUCTURES, "H2SO5", bad)
    blocked(query="oxidation_state", species="H2SO5", element="S")


# ------------------------------------------------------------------ balancing
def test_permanganate_oxalate_acidic():
    code = val(query="balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
               **{"return": "code", "species": ["MnO4^-", "C2O4^2-", "H^+", "Mn^2+", "CO2", "H2O"]})
    assert code == sum(c * 1000 ** (5 - i) for i, c in enumerate([2, 5, 16, 2, 10, 8]))
    assert val(query="balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
               **{"return": "electrons"}) == 10


def test_dichromate_ferrous_scaled():
    v = val(query="balance", equation="Cr2O7^2- + H^+ + Fe^2+ -> Cr^3+ + Fe^3+ + H2O", scale_to={"Fe^2+": 6},
            **{"return": "expr", "map": {"X": "H^+", "Y": "Cr^3+", "Z": "H2O"}, "expr": "X+Y+Z"})
    assert v == 23


def test_basic_medium_disproportionation_and_permanganate_iodide():
    assert val(query="balance", equation="Cl2 + OH^- -> ClO^- + Cl^- + H2O",
               **{"return": "code", "species": ["Cl2", "OH^-", "ClO^-", "Cl^-", "H2O"]}) == \
        sum(c * 1000 ** (4 - i) for i, c in enumerate([1, 2, 1, 1, 1]))
    assert val(query="balance", equation="2MnO4^- + I^- + H2O -> I2 + MnO2 + OH^-", scale_to={"MnO4^-": 2},
               **{"return": "coefficient", "species": "OH^-"}) == 8
    assert val(query="balance", equation="MnO4^- + I^- -> MnO2 + IO3^-", medium="basic",
               **{"return": "coefficient", "species": "OH^-"}) == 2


def test_half_reaction_and_verify_equation():
    assert val(query="balance", equation="Cr2O7^2- -> Cr^3+", medium="acidic", half=True,
               **{"return": "coefficient", "species": "e^-"}) == 6
    assert val(query="verify_equation", equation="Cr2O7^2- + 14H^+ + 6e^- -> 2Cr^3+ + 7H2O") == 1
    assert val(query="verify_equation", equation="Cr2O7^2- + 14H^+ + 7e^- -> 2Cr^3+ + 6H2O") == 0


def test_balancing_methods_must_agree(monkeypatch):
    monkeypatch.setattr(redox, "balance_nullspace", lambda eq, half=False: {"MnO4^-": -1, "Mn^2+": 1})
    blocked(query="balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
            **{"return": "electrons"})


def test_unbalanceable_equation_fails_closed():
    blocked(query="is_disproportionation", equation="2KMnO4 -> 2KMnO4 + MnO2 + O2")


# ------------------------------------------------------------------ n-factor / equivalents
@pytest.mark.parametrize("eq,species,medium,n", [
    ("MnO4^- -> Mn^2+", "MnO4^-", "acidic", 5), ("MnO4^- -> MnO2", "MnO4^-", "basic", 3),
    ("Cr2O7^2- -> Cr^3+", "Cr2O7^2-", "acidic", 6), ("FeC2O4 -> Fe^3+ + CO2", "FeC2O4", "acidic", 3),
    ("Fe2(C2O4)3 -> Fe^3+ + CO2", "Fe2(C2O4)3", "acidic", 6), ("Fe2(SO4)3 -> Fe^3+ + SO4^2-", "Fe2(SO4)3", "acidic", 0),
    ("I2 + 2S2O3^2- -> 2I^- + S4O6^2-", "S2O3^2-", None, 1), ("2Cu^2+ + 4I^- -> Cu2I2 + I2", "Cu^2+", None, 1),
    ("MnO4^- + C2O4^2- -> Mn^2+ + CO2", "CO2", "acidic", 1),
])
def test_n_factor(eq, species, medium, n):
    assert val(query="n_factor", equation=eq, species=species, medium=medium) == n


def test_n_factor_of_disproportionating_species_needs_convention():
    blocked(query="n_factor", equation="Cl2 + OH^- -> ClO^- + Cl^- + H2O", species="Cl2")


def test_equivalent_weight_kio3():
    from cqse.chemistry.rules import ATOMIC_MASS
    M = sum(sp.Rational(ATOMIC_MASS[e]) * n for e, n in {"K": 1, "I": 1, "O": 3}.items())
    assert val(query="equivalent_weight", equation="5I^- + IO3^- + 6H^+ -> 3I2 + 3H2O", species="IO3^-",
               formula="KIO3") == M / 5


def test_equivalence_injects_n_factors_into_equation_system():
    v = val(query="equivalence",
            n_factors={"nK": {"query": "n_factor", "equation": "MnO4^- -> Mn^2+", "species": "MnO4^-",
                              "medium": "acidic"},
                       "nO": {"query": "n_factor", "equation": "H2C2O4 -> CO2", "species": "H2C2O4",
                              "medium": "acidic"}},
            system={"knowns": {"Mo": {"value": "2", "unit": "mol/L"}, "Vo": {"value": "20", "unit": "mL"},
                               "Vk": {"value": "2", "unit": "mL"}},
                    "unknowns": {"Mk": {"unit": "mol/L", "domain": "positive"}},
                    "equations": ["Mk*nK*Vk = Mo*nO*Vo"], "target": "Mk", "model": ["equivalents equal"]})
    assert v == 8


# ------------------------------------------------------------------ roles and reaction types
@pytest.mark.parametrize("eq,expected", [
    ("H2O2 + 2H^+ + 2e^- -> 2H2O", "oxidant"), ("H2O2 -> O2 + 2H^+ + 2e^-", "reductant"),
    ("H2O2 + 2OH^- -> O2 + 2H2O + 2e^-", "reductant"), ("2H2O2 -> 2H2O + O2", "both"),
])
def test_roles(eq, expected):
    assert val(query="role", equation=eq, species="H2O2") == sp.Symbol(expected)


@pytest.mark.parametrize("eq,typ", [
    ("N2 + O2 -> 2NO", "combination"), ("CH4 + 2O2 -> CO2 + 2H2O", "combination"),
    ("2Pb(NO3)2 -> 2PbO + 4NO2 + O2", "decomposition"), ("2NaH -> 2Na + H2", "decomposition"),
    ("2Na + 2H2O -> 2NaOH + H2", "displacement"), ("V2O5 + 5Ca -> 2V + 5CaO", "displacement"),
    ("2NO2 + 2OH^- -> NO2^- + NO3^- + H2O", "disproportionation"), ("2CuBr -> CuBr2 + Cu", "disproportionation"),
    ("2MnO4^- + 3Mn^2+ + 2H2O -> 5MnO2 + 4H^+", "comproportionation"), ("3O2 -> 2O3", "non_redox"),
    ("NaCl + KNO3 -> NaNO3 + KCl", "non_redox"), ("2KMnO4 -> K2MnO4 + MnO2 + O2", "decomposition"),
])
def test_reaction_types(eq, typ):
    assert val(query="reaction_type", equation=eq) == sp.Symbol(typ)


@pytest.mark.parametrize("species,el,cap", [
    ("H3PO4", "P", "oxidant_only"), ("H2SO3", "S", "both"), ("N^3-", "N", "reductant_only"),
    ("F2", "F", "oxidant_only"), ("Cu^+", "Cu", "both"), ("ClO4^-", "Cl", "oxidant_only"),
    ("NaH", "H", "reductant_only"), ("P4", "P", "both"),
])
def test_capability(species, el, cap):
    assert val(query="capability", species=species, element=el) == sp.Symbol(cap)


def test_premise_is_expert_resolvable():
    r = run(query="oxidation_state", species="CrO4^2-", element="Cr",
            premises=[{"statement": "dichromate + OH- gives chromate", "note": "NCERT XII 8"}])
    assert r.value == 6
    assert any(x.check_id == "chem.reaction_feasibility" and x.status == CheckStatus.UNRESOLVED for x in r.records)


# --- intramolecular redox: average ONs hide it, per-atom states must see it ---------------------------------
import pytest as _pt

from cqse.chemistry.redox import Ctx as _Ctx, RedoxError as _RE, analyse as _an, n_factor as _nf, \
    parse_eq as _pe, role as _role


@_pt.mark.parametrize("eq,typ", [
    ("NH4NO2 -> N2 + 2H2O", "comproportionation"),
    ("NH4NO3 -> N2O + 2H2O", "comproportionation"),
    ("NH4NO3 -> NH4^+ + NO3^-", "non_redox"),            # dissolution: per-atom states carried over
    ("Fe3O4 + 8H^+ -> Fe^2+ + 2Fe^3+ + 4H2O", "non_redox"),
    ("2Cu^+ -> Cu + Cu^2+", "disproportionation"),
    ("Hg + Hg^2+ -> Hg2^2+", "comproportionation"),
    ("2H2O2 -> 2H2O + O2", "disproportionation"),
])
def test_intramolecular_and_per_atom(eq, typ):
    assert _an(_pe(eq), _Ctx())["type"] == typ


def test_thiosulphate_keeps_average_convention():
    a = _an(_pe("2S2O3^2- + I2 -> S4O6^2- + 2I^-"), _Ctx())
    assert a["redox"] and not a["disproportionation"] and not a["comproportionation"]


def test_role_and_nfactor_refuse_hidden_intramolecular_redox():
    for fn in (_role, _nf):
        with _pt.raises(_RE):
            fn(_pe("NH4NO2 -> N2 + 2H2O"), "NH4NO2", _Ctx())
