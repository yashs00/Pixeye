"""Redox Reactions generator families: every family yields verified items; planted wrong keys are caught."""
import pytest
import sympy as sp

from cqse.core.problem import QuestionFormat
from cqse.generation.framework import FAMILIES, _solve, generate, to_bank_row
from cqse.generation.families import redox  # noqa: F401  (registers the families)
from cqse.math.expr import parse_value, tri_equal
from cqse.verification.pipeline import verify_item

REDOX = sorted(f for f in FAMILIES if f.startswith("redox."))


def _blocking(rep):
    return [r for r in rep.records if r.hard and r.status.value == "FAILED"]


@pytest.fixture(scope="module")
def generated():
    return {fid: generate(FAMILIES[fid], 3, seed=7)[0] for fid in REDOX}


def test_at_least_eight_families():
    assert len(REDOX) >= 8
    assert sum(FAMILIES[f].numerical for f in REDOX) >= 2


@pytest.mark.parametrize("fid", REDOX)
def test_family_generates_verified_items(fid, generated):
    got = generated[fid]
    assert len(got) >= 2, fid
    for g in got:
        it = g.item
        val, _ = _solve(it.subject, it.formal)
        assert val is not None
        assert tri_equal(parse_value(it.answer.exact_answer), val) is True
        assert not _blocking(g.report)
        if it.question_format == QuestionFormat.SINGLE_CORRECT_MCQ:
            vals = [parse_value(o.value) for o in it.options]
            assert len({o.display for o in it.options}) == 4
            for i in range(4):
                for j in range(i + 1, 4):
                    assert tri_equal(vals[i], vals[j]) is False
            key = [o for o in it.options if o.option_id in it.answer.correct_option_ids]
            assert len(key) == 1 and tri_equal(parse_value(key[0].value), val) is True
            assert all(d.misconception_id and d.verified_wrong for d in it.distractors)
        row = to_bank_row(g)
        assert row["chapter"] == "Redox Reactions" and row["explanation"]["content"]


@pytest.mark.parametrize("fid", REDOX)
def test_planted_wrong_key_rejected(fid, generated):
    it = generated[fid][0].item
    if it.question_format == QuestionFormat.SINGLE_CORRECT_MCQ:
        wrong = next(o.option_id for o in it.options if o.option_id not in it.answer.correct_option_ids)
        bad = it.model_copy(update={"answer": it.answer.model_copy(update={"correct_option_ids": [wrong]})})
    else:
        v = sp.sympify(it.answer.exact_answer) + 1
        bad = it.model_copy(update={"answer": it.answer.model_copy(update={"exact_answer": str(v)})})
    assert _blocking(verify_item(bad)), fid


def test_known_values():
    """Spot-check the engine values the families rely on (textbook answers)."""
    def val(f):
        return _solve(redox.SUBJ, f)[0]
    assert val(redox.RX("oxidation_state", species="CrO5", element="Cr")) == 6
    assert val(redox.RX("oxidation_state", species="S4O6^2-", element="S")) == sp.Rational(5, 2)
    assert val(redox.RX("oxidation_state", species="Fe3O4", element="Fe")) == sp.Rational(8, 3)
    assert val(redox.charge_balance(0, 1, [(5, "O^2-", "O")])) == 10          # CrO5 with every O at -2
    assert val(redox.RX("n_factor", equation="FeC2O4 -> Fe^3+ + CO2", species="FeC2O4", medium="acidic")) == 3
    assert val(redox.RX("balance", equation="MnO4^- + C2O4^2- -> Mn^2+ + CO2", medium="acidic",
                        species="H^+")) == 16
