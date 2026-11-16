import json

from cqse.generation import framework as fw
from cqse.generation.families.pnc import VOWELS_BLOCK


def test_family_review_upgrades_status_and_is_voided_by_code_change(tmp_path, monkeypatch):
    path = tmp_path / "reviews.json"
    monkeypatch.setattr(fw, "REVIEWS_PATH", path)
    p = {"word": "ARRANGE", "mode": "together"}
    g, _ = fw.build(VOWELS_BLOCK, p)
    assert g.status == "VERIFIED_TEACHER_SIGNOFF"
    path.write_text(json.dumps({VOWELS_BLOCK.id: {"reviewer": "T", "date": "2026-11-16",
                                                  "fingerprint": fw.family_fingerprint(VOWELS_BLOCK)}}))
    g, _ = fw.build(VOWELS_BLOCK, p)
    assert g.status == "VERIFIED"
    path.write_text(json.dumps({VOWELS_BLOCK.id: {"reviewer": "T", "date": "2026-11-16", "fingerprint": "stale"}}))
    g, _ = fw.build(VOWELS_BLOCK, p)
    assert g.status == "VERIFIED_TEACHER_SIGNOFF"
