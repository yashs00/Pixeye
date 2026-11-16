"""General calculation checker. Every expected value is hand-derived in the comment."""
import pytest
import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.core.problem import Subject
from cqse.generic.system import solve_system
from cqse.release.workflow import RUBRIC, ItemRecord, ItemState, ReleaseError, Reviewer
from cqse.verification.pipeline import build_item, software_blocking, verify_item

K = lambda v, u: {"value": v, "unit": u}  # noqa: E731
U = lambda u, d="real": {"unit": u, "domain": d}  # noqa: E731

LOOP = {"kind": "equation_system",
        "stem": "A 1 kg bead is released from rest at height 5 m on a frictionless track and enters a vertical "
                "loop of radius 2 m at the bottom. Find the normal force at the lowest point (g = 10 m/s^2).",
        "knowns": {"m": K("1", "kg"), "h": K("5", "m"), "g": K("10", "m/s^2"), "R": K("2", "m")},
        "unknowns": {"v": U("m/s", "positive"), "N": U("N")},
        "equations": ["m*g*h = m*v**2/2", "N - m*g = m*v**2/R"], "target": "N",
        "model": ["frictionless", "released from rest", "lowest point of the loop"]}

CASES = [
    # energy + circular motion: v^2 = 2gh = 100; N = mg + mv^2/R = 10 + 50 = 60 N
    (LOOP, 60),
    # braking, unit conversion: 72 km/h = 20 m/s; s = u^2/(2|a|) = 400/4 = 100 m
    ({"kind": "equation_system", "knowns": {"u": K("72", "km/h"), "a": K("-2", "m/s^2")},
      "unknowns": {"s": U("m", "positive")}, "equations": ["0 = u**2 + 2*a*s"], "target": "s"}, 100),
    # parallel resistors: Req = 3*6/9 = 2 ohm; I = 12/2 = 6 A
    ({"kind": "equation_system", "knowns": {"R1": K("3", "ohm"), "R2": K("6", "ohm"), "V": K("12", "V")},
      "unknowns": {"Req": U("ohm", "positive"), "I": U("A", "positive")},
      "equations": ["1/Req = 1/R1 + 1/R2", "V = I*Req"], "target": "I"}, 6),
    # ideal gas: n = PV/RT = 83000*0.03/(8.3*300) = 1 mol
    ({"kind": "equation_system", "knowns": {"P": K("83000", "Pa"), "V": K("0.03", "m^3"),
                                             "R": K("8.3", "J/(mol*K)"), "T": K("300", "K")},
      "unknowns": {"n": U("mol", "positive")}, "equations": ["P*V = n*R*T"], "target": "n"}, 1),
    # capacitor energy in mJ: U = C V^2 / 2 = 2e-6 * 100 / 2 = 1e-4 J = 0.1 mJ
    ({"kind": "equation_system", "knowns": {"C": K("2", "microfarad"), "V": K("10", "V")},
      "unknowns": {"W": U("mJ", "positive")}, "equations": ["W = C*V**2/2"], "target": "W"},
     sp.Rational(1, 10)),
    # first-order kinetics: k = ln2/10; [A] = 1*exp(-2 ln2) = 1/4 mol/L
    ({"kind": "equation_system", "knowns": {"th": K("10", "s"), "A0": K("1", "mol/L"), "t": K("20", "s")},
      "unknowns": {"k": U("1/s", "positive"), "A": U("mol/L", "positive")},
      "equations": ["k*th = log(2)", "A = A0*exp(-k*t)"], "target": "A"}, sp.Rational(1, 4)),
]


@pytest.mark.parametrize("formal,expected", CASES)
def test_values_and_gates(formal, expected):
    s = solve_system(formal)
    assert sp.simplify(s.value - expected) == 0, s.value
    blocking = [r for r in s.records if r.hard and not r.is_affirmative()]
    assert [r.check_id for r in blocking] == ["model.correspondence"]   # only the teacher check remains


def _status(formal, check):
    return next(r.status for r in solve_system(formal).records if r.check_id == check)


def test_missing_mass_is_a_dimension_failure():
    bad = dict(LOOP, equations=["m*g*h = v**2/2", "N - m*g = m*v**2/R"])
    assert _status(bad, "system.dimensions") == CheckStatus.FAILED


def test_trig_argument_must_be_dimensionless():
    f = {"kind": "equation_system", "knowns": {"x": K("2", "m")}, "unknowns": {"y": U("m")},
         "equations": ["y = x*sin(x)"], "target": "y"}
    assert _status(f, "system.dimensions") == CheckStatus.FAILED


def test_two_admissible_answers_is_ambiguous():
    # reaches 15 m at t = 1 s AND t = 3 s: stem must say "first" -> blocked
    f = {"kind": "equation_system", "knowns": {"g": K("10", "m/s^2"), "u": K("20", "m/s"), "y": K("15", "m")},
         "unknowns": {"t": U("s", "positive")}, "equations": ["y = u*t - g*t**2/2"], "target": "t"}
    assert _status(f, "system.solve.primary") == CheckStatus.FAILED


def test_no_admissible_solution_blocked():
    # cannot reach 25 m when the maximum height is 20 m
    f = {"kind": "equation_system", "knowns": {"g": K("10", "m/s^2"), "u": K("20", "m/s"), "y": K("25", "m")},
         "unknowns": {"t": U("s", "positive")}, "equations": ["y = u*t - g*t**2/2"], "target": "t"}
    assert solve_system(f).value is None


@pytest.mark.parametrize("bad", [{"knowns": {"I": K("1", "A")}}, {"target": "zz"}, {"equations": ["v == 2"]}])
def test_malformed_systems_blocked(bad):
    s = solve_system({**LOOP, **bad})
    assert s.value is None


def test_mcq_item_needs_teacher_attestations_and_two_reviews():
    item = build_item("G1", Subject.PHYSICS, LOOP, "JEE_MAIN-2027-v1")
    rep = verify_item(item)
    assert not software_blocking(rep)
    open_ = sorted(r.check_id for r in rep.blocking)
    assert open_ == ["distractors.plausibility", "model.correspondence"]
    t1 = Reviewer(reviewer_id="t1", subjects=[Subject.PHYSICS])
    t2 = Reviewer(reviewer_id="t2", subjects=[Subject.PHYSICS])
    passing = {d: "pass" for d in RUBRIC}
    rec = ItemRecord(item=item)
    rec.run_verification()
    with pytest.raises(ReleaseError):
        rec.approve(t1, passing)
    rec.attest(t1, "model.correspondence", "energy conservation + radial N2L at lowest point; frictionless stated")
    rec.attest(t1, "distractors.plausibility", "dropped weight term and halved KE are common errors")
    rec.approve(t1, passing)
    assert rec.state == ItemState.INDEPENDENT_REVIEW_2   # general-checker items always need two teachers
    rec.approve(t2, passing)
    assert rec.state == ItemState.APPROVED
