"""Generated Rotational Motion questions: every family yields verified items, and verify_item catches a planted
wrong key."""
import copy

import pytest
import sympy as sp

import cqse.generation.families.rot  # noqa: F401  (registers the families)
from cqse.generation.framework import FAMILIES, _solve, generate
from cqse.verification.pipeline import EXPERT_RESOLVABLE, verify_item

ROT = sorted(f for f in FAMILIES if f.startswith("rot."))


def _hard_failures(rep):
    return [r for r in rep.records if r.hard and not r.is_affirmative()
            and not (r.status.value == "UNRESOLVED" and r.check_id in EXPERT_RESOLVABLE)]


@pytest.fixture(scope="module")
def generated():
    return {fid: generate(FAMILIES[fid], 2, seed=3)[0] for fid in ROT}


def test_enough_families():
    assert len(ROT) >= 8
    assert sum(FAMILIES[f].numerical for f in ROT) >= 2
    assert {FAMILIES[f].difficulty for f in ROT} == {"EASY", "MEDIUM", "HARD"}


@pytest.mark.parametrize("fid", ROT)
def test_family_generates_verified_items(fid, generated):
    got = generated[fid]
    assert len(got) >= 2, fid
    fam = FAMILIES[fid]
    assert fam.modelled_on and len(fam.mistakes(got[0].params)) >= 4
    for g in got:
        assert g.status in ("VERIFIED", "VERIFIED_TEACHER_SIGNOFF")
        assert not _hard_failures(g.report)
        it = g.item
        val, _ = _solve(fam.subject, it.formal)
        assert val is not None and sp.sympify(it.answer.exact_answer) == val
        assert "g = 10" in it.stem or "$g" not in it.stem
        if fam.numerical:
            assert sp.sympify(val).is_integer
            continue
        disp = [o.display for o in it.options]
        assert len(disp) == 4 and len(set(disp)) == 4
        assert len({sp.sympify(o.value) for o in it.options}) == 4
        (key,) = it.answer.correct_option_ids
        assert sp.sympify(next(o.value for o in it.options if o.option_id == key)) == val
        assert all(d.verified_wrong and d.misconception_id for d in it.distractors)
        assert fam.explain(g.params, val)


@pytest.mark.parametrize("fid", ROT)
def test_planted_wrong_key_rejected(fid, generated):
    g = generated[fid][0]
    bad = copy.deepcopy(g.item)
    if FAMILIES[fid].numerical:
        bad.answer.exact_answer = str(int(sp.sympify(bad.answer.exact_answer)) + 1)
    else:
        key = bad.answer.correct_option_ids[0]
        wrong = next(o for o in bad.options if o.option_id != key)
        bad.answer.correct_option_ids = [wrong.option_id]
        bad.answer.exact_answer = wrong.value
    assert _hard_failures(verify_item(bad)), fid


R = sp.Rational


def test_hand_derived_values():
    """Instances checked by hand from textbook results (independent of the engine's methods)."""
    cases = [
        ("rot.axis_theorems", {"case": 0}, R(5, 4)),            # disc, tangent in plane: 1/4 + 1
        ("rot.axis_theorems", {"case": 8}, R(1, 3)),            # rod about an end
        ("rot.axis_theorems", {"case": 12}, R(2, 3)),           # square plate, corner, normal axis
        ("rot.removed_disc", {"n": 2, "d": "R/2", "axis": "perp_O"}, R(13, 32)),
        ("rot.removed_disc", {"n": 3, "d": "R - R/3", "axis": "diam_OC"}, R(20, 81)),
        ("rot.composite_rod_body", {"shape": "solid_sphere", "m1": 3, "m2": 4, "L": 50, "r": 5}, R(183, 125)),
        ("rot.gyration_particles", {"axis": "sq_perpA", "mass": "equal"}, sp.Integer(1)),
        ("rot.rolling_speed", {"shape": "solid_sphere", "v": 10, "h": "7", "M": 2, "R": 10}, 10),
        ("rot.rolling_friction", {"shape": "solid_sphere", "th": 30}, 2 * sp.sqrt(3) / 21),
        ("rot.ke_split", {"shape": "disc", "ask": "rot_total"}, R(1, 3)),
        ("rot.pulley_hanging_mass", {"shape": "disc", "M": 4, "m": 2, "R": 20, "ask": "T"}, 10),
        ("rot.turntable_person", {"M": 120, "m": 40, "R": 3, "w1": 8, "move": "rim_half"}, R(80, 7)),
        ("rot.coupled_discs_ke_loss", {"M1": 8, "R1": "0.5", "M2": 5, "R2": "0.4", "w1": 5, "w2": 2,
                                       "sense": "opposite"}, 7),
        ("rot.rod_release", {"L": "1.2", "m": 2, "ask": "w"}, 5),
        ("rot.torque_work_power", {"shape": "solid_cylinder", "M": 5, "R": "0.25", "F": 10, "t": 3, "ask": "w"}, 48),
    ]
    for fid, p, want in cases:
        val, _ = _solve(FAMILIES[fid].subject, FAMILIES[fid].formal(p))
        assert val is not None and sp.simplify(val - want) == 0, (fid, p, val)
