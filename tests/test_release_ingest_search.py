from pathlib import Path

import pytest

from cqse.core.problem import Subject
from cqse.exam.profiles import ProfileStatus, all_profiles
from cqse.ingest.pyq import IngestStatus, ingest_file
from cqse.release.workflow import RELEASE_CHECKLIST, RUBRIC, ItemRecord, ItemState, ReleaseError, Reviewer
from cqse.search.engine import search
from cqse.verification.pipeline import software_blocking, verify_item

T1 = Reviewer(reviewer_id="teacher-1", subjects=[Subject.MATHEMATICS, Subject.PHYSICS, Subject.CHEMISTRY])
T2 = Reviewer(reviewer_id="teacher-2", subjects=[Subject.MATHEMATICS, Subject.PHYSICS, Subject.CHEMISTRY])
PHYS_ONLY = Reviewer(reviewer_id="phys-1", subjects=[Subject.PHYSICS])
PASS = {d: "pass" for d in RUBRIC}
CHECK = {k: True for k in RELEASE_CHECKLIST}


def _approved(item):
    rec = ItemRecord(item=item)
    rec.run_verification()
    if rec.item.subject == Subject.CHEMISTRY:
        rec.attest(T1, "chem.reaction_feasibility", "NCERT Class 11 Unit 1: 2H2 + O2 -> 2H2O")
    rec.approve(T1, PASS)
    if rec.state == ItemState.INDEPENDENT_REVIEW_2:
        rec.approve(T2, PASS)
    return rec


def test_full_release_lifecycle(good_item):
    rec = _approved(good_item)
    assert rec.state == ItemState.APPROVED
    rec.publish("coordinator", CHECK)
    assert rec.state == ItemState.PUBLISHED
    with pytest.raises(ReleaseError):
        rec.edit("x", rec.item, "silent overwrite")      # published = immutable
    rec.suspend("teacher-1", "student reports ambiguity")
    new = rec.correct("teacher-1", rec.item, "clarified wording")
    assert rec.state == ItemState.RETIRED and new.supersedes == rec.published_hash
    assert new.item.identity.version == rec.item.identity.version + 1 and new.state == ItemState.DRAFT


def test_cannot_approve_without_verification(good_item):
    with pytest.raises(ReleaseError):
        ItemRecord(item=good_item).approve(T1, PASS)


def test_chemistry_needs_attestation_and_two_reviews():
    from tests.conftest import GOOD_FORMALS, PROFILE
    from cqse.verification.pipeline import build_item
    subj, f = GOOD_FORMALS["stoich"]
    rec = ItemRecord(item=build_item("C1", subj, f, PROFILE))
    rec.run_verification()
    with pytest.raises(ReleaseError):
        rec.approve(T1, PASS)                          # feasibility unresolved
    with pytest.raises(ReleaseError):
        rec.attest(T1, "chem.reaction_feasibility", "  ")  # evidence required
    with pytest.raises(ReleaseError):
        rec.attest(T1, "math.solve.primary", "trust me")   # not expert-resolvable
    rec.attest(T1, "chem.reaction_feasibility", "NCERT Class 11 Unit 1")
    rec.approve(T1, PASS)
    assert rec.state == ItemState.INDEPENDENT_REVIEW_2
    with pytest.raises(ReleaseError):
        rec.approve(T1, PASS)                          # same reviewer twice
    rec.approve(T2, PASS)
    assert rec.state == ItemState.APPROVED


def test_edit_invalidates_approval(good_item):
    rec = _approved(good_item)
    changed = rec.item.model_copy(deep=True)
    changed.stem += " (edited)"
    rec.edit("teacher-1", changed, "typo fix")
    assert rec.state == ItemState.DRAFT and not rec.approvals
    with pytest.raises(ReleaseError):
        rec.publish("coordinator", CHECK)


def test_incomplete_rubric_or_checklist_blocks(good_item):
    rec = ItemRecord(item=good_item)
    rec.run_verification()
    with pytest.raises(ReleaseError):
        rec.approve(T1, {**PASS, "scientific_correctness": "revise"})
    rec = _approved(good_item)
    with pytest.raises(ReleaseError):
        rec.publish("coordinator", {**CHECK, "every_option_tested": False})


def test_subject_qualification():
    from tests.conftest import GOOD_FORMALS, PROFILE
    from cqse.verification.pipeline import build_item
    subj, f = GOOD_FORMALS["math_domain"]
    rec = ItemRecord(item=build_item("M1", subj, f, PROFILE))
    rec.run_verification()
    with pytest.raises(ReleaseError):
        rec.approve(PHYS_ONLY, PASS)


def test_ingest_sample_routes_every_defect():
    res = {r.pyq_id: r for r in ingest_file(Path(__file__).parent.parent / "data/samples/pyq_sample.jsonl")}
    assert res["SAMPLE-M-001"].statuses == [IngestStatus.PARENT_VERIFIED]
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in res["SAMPLE-M-002"].statuses   # printed key wrong
    assert {IngestStatus.NEEDS_SOURCE, IngestStatus.NEEDS_VISUAL_REVIEW,
            IngestStatus.QUARANTINED_KEY_DISAGREEMENT} <= set(res["SAMPLE-P-002"].statuses)
    assert IngestStatus.NEEDS_EXPERT_REVIEW in res["SAMPLE-C-001"].statuses
    assert res["SAMPLE-C-002"].statuses == [IngestStatus.NEEDS_FORMALIZATION]
    assert IngestStatus.QUARANTINED_UNVERIFIABLE in res["SAMPLE-M-003"].statuses        # 1 == 0.5*2
    assert res["SAMPLE-M-003"].duplicate_of == ["SAMPLE-M-001"]


def test_profiles_governance():
    st = {p.profile_id: p.status for p in all_profiles()}
    assert st["JEE_ADVANCED-2027-v0"] == ProfileStatus.PROVISIONAL
    assert st["MHT_CET-2026-v1"] == ProfileStatus.HISTORICAL_BASELINE


@pytest.mark.parametrize("subject,formal", [
    (Subject.MATHEMATICS, dict(kind="equation", lhs="x**2-x-6", rhs="0", var="x", domain="reals", target="sum")),
    (Subject.PHYSICS, dict(kind="incline_friction", m="2", theta_deg="30", mu_s="0.7", mu_k="0.5", g="10",
                           target="acceleration")),
])
def test_search_children_reverify_independently(subject, formal):
    r = search("S", subject, formal, "JEE_MAIN-2027-v1", depth=2, top_k=5, max_children=60)
    assert r.candidates
    for c in r.candidates:
        assert c.item.identity.parent_id == "S" and c.item.identity.lineage
        rep = verify_item(c.item)  # fresh verification, nothing inherited from the parent
        assert not software_blocking(rep), rep.summary()
