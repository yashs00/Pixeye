import json
from pathlib import Path

from cqse.ingest.ascent import convert, html_to_text, import_file

FIX = Path(__file__).parent / "fixtures/ascent_sample.json"


def test_import_flags_images_missing_keys_and_rights(tmp_path):
    rep = import_file(FIX, tmp_path / "out.jsonl")
    assert rep["records"] == 6 and rep["image_dependent"] == 1 and rep["numerical_without_key"] == 2
    rows = [json.loads(l) for l in (tmp_path / "out.jsonl").read_text().splitlines()]
    assert all(r["source"]["rights_status"] == "UNKNOWN" for r in rows)
    assert all(r["key_source"] == "provisional" for r in rows)       # third-party key, never "official"
    img = next(r for r in rows if r["pyq_id"] == "ASCENT-m6rp6klo")
    assert img["extraction"]["visual_review_done"] is False and "[IMAGE]" in img["stem"]
    num = next(r for r in rows if r["pyq_id"] == "ASCENT-m9ghxnwx")
    assert num["answer_key"] is None                                  # never scraped from the explanation


def test_html_cleanup():
    t, n = html_to_text("<p>SO<sub>2</sub> and NO<sub>2</sub><sup>-</sup> &amp; <img src='x'></p>")
    assert t.startswith("SO_2 and NO_2^- &") and n == 1


def test_clearing_rights_requires_a_recorded_basis(tmp_path):
    import pytest
    from cqse.ingest.ascent import import_file
    src = Path(__file__).parent / "fixtures/ascent_sample.json"
    with pytest.raises(ValueError):
        import_file(src, tmp_path / "x.jsonl", rights="CLEARED")
    import_file(src, tmp_path / "y.jsonl", rights="CLEARED", uses=["storage", "derive", "llm"], basis="owner, 2026-11-15")
    rec = json.loads((tmp_path / "y.jsonl").read_text().splitlines()[0])
    assert rec["source"]["rights_status"] == "CLEARED" and rec["source"]["rights_basis"] == "owner, 2026-11-15"


def test_latex_less_than_is_not_an_html_tag():
    t, _ = html_to_text("<p>$f(x)=1-2x, & x<-1 \\\\ 3, & x>2$ and <b>bold</b></p>")
    assert "x<-1" in t and "x>2" in t and "bold" in t and "<b>" not in t
