"""Chemistry rule engine (cqse/chemistry/rules.py): configurations, magnetism, VSEPR, MO, fail-closed."""
import sympy as sp

from cqse.chemistry.rules import RULESET, solve_and_verify
from cqse.core.evidence import CheckStatus
from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record


def V(p, s, **k):
    return solve_and_verify({"kind": "chem_property", "query": "value", "property": p, "species": s, **k})


def val(p, s, **k):
    r = V(p, s, **k)
    assert r.value is not None, r.records[0].result
    return r.value


def test_configuration_exceptions_from_table():
    assert val("subshell_electrons", "Cr", subshell="3d") == 5 and val("subshell_electrons", "Cr", subshell="4s") == 1
    assert val("subshell_electrons", "Cu", subshell="3d") == 10
    assert val("subshell_electrons", "Nb", subshell="4d") == 4
    assert val("subshell_electrons", "Ru", subshell="4d") == 7
    assert val("subshell_electrons", "Pd", subshell="5s") == 0
    assert val("subshell_electrons", "Gd", subshell="5d") == 1 and val("subshell_electrons", "Gd", subshell="4f") == 7
    assert val("subshell_electrons", "Pt", subshell="5d") == 9


def test_ions_and_4f():
    assert val("subshell_electrons", "Fe^3+", subshell="4s") == 0
    assert val("subshell_electrons", "Eu^2+", subshell="4f") == 7
    assert val("subshell_electrons", "Gd^3+", subshell="4f") == 7
    assert val("subshell_electrons", "Eu^3+", subshell="4f") == 6
    assert val("subshell_electrons", "Tb^4+", subshell="4f") == 7


def test_unpaired_and_spin_only_moment():
    assert [val("unpaired_electrons", s) for s in ["Ti^3+", "V^2+", "Cr^2+", "Mn^2+", "Fe^2+", "Co^2+", "Ni^2+",
                                                   "Cu^2+", "Cu^+", "Cr", "Gd"]] == [1, 3, 4, 5, 4, 3, 2, 1, 0, 6, 8]
    assert val("spin_only_moment", "Co^2+") == sp.sqrt(15)
    r = V("spin_only_moment", "Fe^2+")
    assert r.records[0].status == CheckStatus.RULE_CHECKED and RULESET in r.records[0].method
    assert any(x.check_id == "chem.rule_cross_check" and "Hund" in x.result for x in r.records)


def test_vsepr_shapes_and_counts():
    shapes = {"SO2": "bent", "BeCl2": "linear", "N3^-": "linear", "NO2": "bent", "XeF2": "linear", "I3^-": "linear",
              "XeF4": "square_planar", "XeOF4": "square_pyramidal", "BrF5": "square_pyramidal", "ClF3": "T_shaped",
              "SF4": "see_saw", "PCl5": "trigonal_bipyramidal", "NH3": "trigonal_pyramidal", "BCl3": "trigonal_planar",
              "O3": "bent", "F2O": "bent", "NO2^+": "linear"}
    for s, sh in shapes.items():
        assert val("shape", s) == sp.Symbol(sh), s
    assert val("hybridization", "NO2^-") == sp.Symbol("sp2")
    assert val("lone_pairs_equatorial", "ClF3") == 2
    assert val("lewis_nonbonded_electrons", "NO2^-") == 12
    assert val("bond_pairs_total", "SO2") == 4      # expanded-octet convention recorded as assumption
    assert val("dipole_nonzero", "XeF4") == 0 and val("dipole_nonzero", "CHCl3") == 1
    assert val("dipole_nonzero", "NF3") == 1 and val("dipole_nonzero", "CO2") == 0


def test_mo_theory():
    assert val("bond_order", "O2") == 2 and val("mo_unpaired_electrons", "O2") == 2
    assert val("paramagnetic", "B2") == 1 and val("paramagnetic", "C2") == 0
    assert val("bond_order", "O2^-") == sp.Rational(3, 2)
    assert val("paramagnetic", "S2") == 1 and val("paramagnetic", "Cl2") == 0
    assert val("bond_order", "NO") == sp.Rational(5, 2)


def test_fail_closed_on_unknown_species():
    for p, s in [("shape", "FeCl3"), ("unpaired_electrons", "U"), ("shape", "C6H6"), ("molar_mass", "Xx2"),
                 ("lone_pairs_equatorial", "XeF4"), ("aq_colour", "Ag^+"), ("bond_order", "Br2")]:
        r = V(p, s)
        assert r.value is None and r.records[0].status == CheckStatus.UNRESOLVED, (p, s)


def test_premise_is_expert_resolvable():
    r = solve_and_verify({"kind": "chem_property", "query": "value", "property": "molar_mass", "species": "Fe2O3",
                          "premises": [{"statement": "product is Fe2O3", "basis": "curated"}]})
    assert r.value is not None
    assert any(x.check_id == "chem.reaction_feasibility" and x.status == CheckStatus.UNRESOLVED for x in r.records)


def _rec(key):
    opts = [("A", "A, D and E Only"), ("B", "B and C Only"), ("C", "A and D Only"), ("D", "B Only")]
    return PYQRecord(**{
        "pyq_id": "T-chem", "exam": "JEE_MAIN", "year": 2025, "subject": "CHEMISTRY",
        "question_format": "single_correct_mcq", "stem": "Which are paramagnetic? A O2 B N2 C F2 D S2 E Cl2",
        "options": [{"id": i, "text": t, "value": "{" + ", ".join(
            str(" ABCDE".index(c)) for c in t.replace(",", " ").split() if c in "ABCDE") + "}"} for i, t in opts],
        "answer_key": key, "key_source": "provisional",
        "source": {"document": "t", "rights_status": "CLEARED", "permitted_uses": ["derive"], "rights_basis": "test"},
        "formal": {"kind": "statement_set", "format": "select_combination", "statements": {
            k: {"formal": {"kind": "chem_property", "query": "value", "property": "paramagnetic", "species": s},
                "claim": "== 1", "subject": "CHEMISTRY"}
            for k, s in {"A": "O2", "B": "N2", "C": "F2", "D": "S2", "E": "Cl2"}.items()}}})


def test_planted_wrong_key_detected():
    ok = ingest_record(_rec("C"))
    assert IngestStatus.PARENT_VERIFIED in ok.statuses and IngestStatus.NEEDS_EXPERT_REVIEW not in ok.statuses
    bad = ingest_record(_rec("A"))
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in bad.statuses
