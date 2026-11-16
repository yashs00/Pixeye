import itertools

import pytest

from cqse.core.problem import Subject
from cqse.physics.dimensions import (RELATION_TEMPLATES, DimensionError, build_dim_model, classify,
                                     generate_formal)
from cqse.verification.pipeline import build_item, software_blocking, verify_item

BASE = {"kind": "dimension_meaningful", "quantities": ["A", "B", "C", "D"],
        "relation": "A*D = C*log(B*D)", "ask": "not_meaningful"}


@pytest.mark.parametrize("expr,verdict", [
    ("(A - C)/D", "NEVER"),             # needs [A]=[C] -> B dimensionless: forbidden
    ("A/B - C", "ALWAYS"),              # [A]/[B] = [C]
    ("C/(B*D) - A*D**2/C", "NEVER"),    # [C] vs 1/[B] -> A dimensionless: forbidden
    ("A*D - C", "ALWAYS"),
    ("A/D - B", "NEVER"),
    ("A - C*B", "ALWAYS"),
    ("B*D - 1", "ALWAYS"),              # BD is dimensionless
    ("log(A*D/C)", "ALWAYS"),
    ("A - B", "NEVER"),                 # stated: A and B have different dimensions
])
def test_classification(expr, verdict):
    assert classify(build_dim_model(BASE), expr).verdict == verdict


def test_contingent_option_detected():
    # A - B^2 is NEVER: [A] = 2[B] would force [C] = [B], which the facts forbid.
    assert classify(build_dim_model(BASE), "A - B**2").verdict == "NEVER"
    # A - B^3: [A] = 3[B] contradicts no stated fact, but is not implied -> ambiguous
    assert classify(build_dim_model(BASE), "A - B**3").verdict == "CONTINGENT"


def test_relation_contradicting_facts_rejected():
    with pytest.raises(DimensionError):
        build_dim_model({**BASE, "relation": "A = C*exp(B*D)"})   # forces [A] = [C]


@pytest.mark.parametrize("tmpl", RELATION_TEMPLATES)
def test_templates_consistent(tmpl):
    for p in itertools.permutations("ABCD"):
        build_dim_model({**BASE, "relation": tmpl.format(a=p[0], b=p[1], c=p[2], d=p[3])})


def test_two_never_options_means_ambiguous_item():
    item = build_item("D1", Subject.PHYSICS, BASE, "JEE_MAIN-2027-v1")
    assert not software_blocking(verify_item(item))
    bad = item.model_copy(deep=True)
    # replace a (consistent) distractor with a second never-meaningful combination
    wrong = next(o for o in bad.options if o.option_id not in bad.answer.correct_option_ids)
    wrong.value = "C/(B*D) - A*D**2/C" if bad.answer.exact_answer != "C/(B*D) - A*D**2/C" else "(A - C)/D"
    rep = verify_item(bad)
    assert any(r.check_id == "options.cardinality" and r.status.value == "FAILED" for r in rep.records)


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("ask", ["not_meaningful", "meaningful"])
def test_generated_items_verify(seed, ask):
    item = build_item(f"G{seed}", Subject.PHYSICS, generate_formal(seed, ask), "JEE_MAIN-2027-v1", seed=seed)
    assert not software_blocking(verify_item(item))
