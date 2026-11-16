"""Generated P&C questions: every family yields verified items, and verify_item catches a planted wrong key."""
import copy

import pytest
import sympy as sp

import cqse.generation.families.pnc  # noqa: F401  (registers the families)
from cqse.generation.framework import FAMILIES, _solve, generate
from cqse.verification.pipeline import EXPERT_RESOLVABLE, verify_item

PNC = sorted(f for f in FAMILIES if f.startswith("pnc."))


def _hard_failures(rep):
    return [r for r in rep.records if r.hard and not r.is_affirmative()
            and not (r.status.value == "UNRESOLVED" and r.check_id in EXPERT_RESOLVABLE)]


@pytest.fixture(scope="module")
def generated():
    return {fid: generate(FAMILIES[fid], 3, seed=7)[0] for fid in PNC}


def test_enough_families():
    assert len(PNC) >= 9
    assert sum(FAMILIES[f].numerical for f in PNC) >= 2


@pytest.mark.parametrize("fid", PNC)
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


@pytest.mark.parametrize("fid", PNC)
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


def test_hand_derived_values():
    """A few instances checked by hand (independent of the engine's closed forms)."""
    cases = [("pnc.dictionary_rank", {"word": "BOTTLE"}, 36),
             ("pnc.digit_numbers", {"digits": [0, 1, 2, 4, 5], "k": 4, "cond": "div4"}, 30),
             ("pnc.committee_atleast", {"m": 8, "w": 4, "r": 5, "a": 3, "mode": "atleast", "g": 0}, 120),
             ("pnc.circular_seating", {"mode": "no_two", "n": 4, "k": 3}, 144),
             ("pnc.circular_seating", {"mode": "pair_apart", "n": 6}, 72),
             ("pnc.identical_into_boxes", {"n": 8, "k": 3, "b": 2, "t": 2}, 6),
             ("pnc.derangement", {"n": 5, "r": 2, "s": 0}, 20),
             ("pnc.gap_method", {"word": "BALLOON", "group": "V"}, 360),
             ("pnc.divisors", {"N": 2160, "mode": "square", "q": 0}, 6),
             ("pnc.points_triangles", {"mode": "lines_collinear", "n": 10, "m": 5}, 36),
             ("pnc.letter_selection", {"word": "PROPORTION", "r": 4, "mode": "select"}, 53),
             ("pnc.letter_selection", {"word": "PROPORTION", "r": 4, "mode": "arrange"}, 758)]
    for fid, p, want in cases:
        val, _ = _solve(FAMILIES[fid].subject, FAMILIES[fid].formal(p))
        assert val == want, (fid, p, val)
