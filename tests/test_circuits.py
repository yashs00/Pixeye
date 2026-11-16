"""DC circuits. Expected values are hand-derived in comments."""
import pytest
import sympy as sp

from cqse.core.problem import Subject
from cqse.physics.circuits import (CircuitError, DCSolution, certify, parse_circuit, solve_and_verify,
                                   solve_mna)
from cqse.search.engine import search
from cqse.verification.pipeline import build_item, software_blocking, verify_item

R = lambda i, v, a, b, u="ohm": {"id": i, "type": "resistor", "value": v, "unit": u, "nodes": [a, b]}  # noqa: E731
V = lambda i, v, a, b, u="V": {"id": i, "type": "vsource", "value": v, "unit": u, "nodes": [a, b]}  # noqa: E731
BASE = [V("V1", "12", "A", "G"), R("R1", "2", "A", "B"), R("R2", "3", "B", "G"), R("R3", "6", "B", "G")]


def ckt(comps, **target):
    return {"kind": "circuit_dc", "components": comps, "target": target}


CASES = [
    # R2||R3 = 2, total 4 -> I = 3 A, V_B = 6 V -> I_R2 = 2 A
    (ckt(BASE, quantity="current", element="R2"), 2),
    (ckt(BASE, quantity="voltage", element="R1"), 6),           # 3 A * 2 ohm
    (ckt(BASE, quantity="power", element="R3"), 6),             # (6 V)^2 / 6 ohm
    # capacitor across B-G holds 6 V: Q = 2 uF * 6 V = 12 uC ; U = 1/2 C V^2 = 36 uJ
    (ckt(BASE + [{"id": "C1", "type": "capacitor", "value": "2", "unit": "uF", "nodes": ["B", "G"]}],
         quantity="charge", element="C1"), sp.Rational(12, 10**6)),
    (ckt(BASE + [{"id": "C1", "type": "capacitor", "value": "2", "unit": "uF", "nodes": ["B", "G"]}],
         quantity="energy", element="C1"), sp.Rational(36, 10**6)),
    # capacitor in series with R3 blocks it: total 2+3 = 5 -> 12/5 A through R2
    (ckt([V("V1", "12", "A", "G"), R("R1", "2", "A", "B"), R("R2", "3", "B", "G"), R("R3", "6", "B", "X"),
          {"id": "C1", "type": "capacitor", "value": "1", "unit": "uF", "nodes": ["X", "G"]}],
         quantity="current", element="R2"), sp.Rational(12, 5)),
    # inductor is a short in DC: L across R3 shorts B-G -> all 6 A through R1 and L, 0 through R2... ask R1
    (ckt(BASE + [{"id": "L1", "type": "inductor", "value": "1", "unit": "H", "nodes": ["B", "G"]}],
         quantity="current", element="R1"), 6),
    # two batteries opposing: 12 V and 4 V in series loop with 4 ohm -> (12-4)/4 = 2 A
    (ckt([V("V1", "12", "A", "G"), V("V2", "4", "A", "B"), R("R1", "4", "B", "G")],
         quantity="current", element="R1"), 2),
    # current source 2 A into 3 ohm || 6 ohm: Req 2 -> V = 4 V -> I(6 ohm) = 2/3 A
    (ckt([{"id": "I1", "type": "isource", "value": "2", "unit": "A", "nodes": ["G", "A"]},
          R("R1", "3", "A", "G"), R("R2", "6", "A", "G")], quantity="current", element="R2"), sp.Rational(2, 3)),
    # units: 1.2 kohm with 12 V -> 10 mA
    (ckt([V("V1", "12", "A", "G"), R("R1", "1.2", "A", "G", "kohm")], quantity="current", element="R1"),
     sp.Rational(1, 100)),
    # unbalanced Wheatstone bridge (1,2 / 2,1 arms, 1 ohm galvanometer): Req = 7/5 by symmetry
    (ckt([R("R1", "1", "A", "B"), R("R2", "2", "A", "C"), R("R3", "2", "B", "D"), R("R4", "1", "C", "D"),
          R("R5", "1", "B", "C")], quantity="equivalent_resistance", terminals=["A", "D"]), sp.Rational(7, 5)),
    # balanced bridge (1,2 / 1,2): middle resistor carries nothing; Req = (3*3)/6 = 3/2
    (ckt([R("R1", "1", "A", "B"), R("R2", "2", "B", "D"), R("R3", "1", "A", "C"), R("R4", "2", "C", "D"),
          R("R5", "5", "B", "C")], quantity="equivalent_resistance", terminals=["A", "D"]), sp.Rational(3, 2)),
    # series-parallel Req (reduction cross-check applies): 2 + 3||6 = 4
    (ckt([R("R1", "2", "A", "B"), R("R2", "3", "B", "G"), R("R3", "6", "B", "G")],
         quantity="equivalent_resistance", terminals=["A", "G"]), 4),
]


@pytest.mark.parametrize("formal,expected", CASES)
def test_values_proved(formal, expected):
    r = solve_and_verify(formal)
    assert r.value is not None, [(x.check_id, x.result) for x in r.records]
    assert sp.simplify(r.value - expected) == 0, r.value
    assert all(x.is_affirmative() for x in r.records if x.hard)


@pytest.mark.parametrize("comps,why", [
    ([V("V1", "12", "A", "G"), R("R1", "2", "A", "B"),
      {"id": "C1", "type": "capacitor", "value": "1", "unit": "uF", "nodes": ["B", "X"]},
      {"id": "C2", "type": "capacitor", "value": "1", "unit": "uF", "nodes": ["X", "G"]}], "floating node"),
    ([V("V1", "12", "A", "G"), V("V2", "6", "A", "G"), R("R1", "2", "A", "G")], "source loop"),
    ([V("V1", "12", "A", "G"), R("R1", "2", "A", "B")], "dangling node B is fine; R1 open-ended"),
])
def test_ill_posed_networks_blocked(comps, why):
    r = solve_and_verify(ckt(comps, quantity="current", element="R1"))
    if why.startswith("dangling"):
        assert r.value == 0   # well-posed: no current flows - but zero is excluded as a distractor value
    else:
        assert r.value is None


@pytest.mark.parametrize("bad", [R("R1", "2", "A", "B", "V"), R("R1", "-2", "A", "B"), R("R1", "2", "A", "A")])
def test_bad_components_rejected(bad):
    with pytest.raises(CircuitError):
        parse_circuit(ckt([V("V1", "12", "A", "G"), bad, R("R2", "1", "B", "G")], quantity="current",
                          element="R2"))


def test_certificate_catches_a_wrong_solution():
    c = parse_circuit(ckt(BASE, quantity="current", element="R2"))
    sol = solve_mna(c)
    bad = DCSolution(dict(sol.V), dict(sol.I))
    bad.I["V1"] = -bad.I["V1"]                     # the sign bug found during development
    assert any("KCL" in p for p in certify(c, bad))
    bad = DCSolution(dict(sol.V), dict(sol.I))
    bad.V["B"] += 1
    assert certify(c, bad)


def test_item_is_fully_software_verified_with_diagram():
    item = build_item("C1", Subject.PHYSICS, ckt(BASE, quantity="current", element="R2"), "JEE_MAIN-2027-v1")
    rep = verify_item(item)
    assert rep.passed_hard_gates, rep.summary()     # no teacher-model check needed for netlists
    assert item.diagram_svg.startswith("<svg") and "R2" in item.diagram_svg
    edited = item.model_copy(deep=True)
    edited.diagram_svg = edited.diagram_svg.replace("3 Ω", "4 Ω")
    assert software_blocking(verify_item(edited))   # a diagram that disagrees with the netlist blocks


def test_circuit_search_children_verify():
    r = search("S", Subject.PHYSICS, ckt(BASE, quantity="current", element="R2"), "JEE_MAIN-2027-v1",
               depth=2, top_k=5, max_children=40)
    assert r.candidates
    for c in r.candidates:
        assert verify_item(c.item).passed_hard_gates
