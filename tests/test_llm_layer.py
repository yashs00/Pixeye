"""LLM layer tests with a fake client: no network, no API key, no cost."""
import json
from types import SimpleNamespace

import pytest

from cqse.ingest.pyq import IngestStatus, PYQRecord
from cqse.llm.cache import ResultCache
from cqse.llm.formalize import formalize_records, triage
from cqse.llm.gateway import Gateway
from cqse.llm.ledger import BudgetExceeded, Ledger
from cqse.llm.prompts import SYSTEM_FORMALIZE


def _draft(kind, formal, opts=(), decision="formalized"):
    return {"decision": decision, "kind": kind, "formal_json": json.dumps(formal),
            "option_values": [{"id": i, "value": v} for i, v in opts], "notes": ""}


class FakeClient:
    """Returns scripted drafts; records every request for inspection."""

    def __init__(self, script):
        self.script = script  # list of (stem substring, [draft for call 1, draft for call 2...])
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        user = kw["messages"][0]["content"]
        for sub, drafts in self.script:
            if sub in user:
                n = sum(1 for c in self.calls if sub in c["messages"][0]["content"])
                d = drafts[min(n, len(drafts)) - 1]
                if d == "REFUSE":
                    return SimpleNamespace(stop_reason="refusal", content=[], model=kw["model"],
                                           usage=SimpleNamespace(input_tokens=10, output_tokens=0))
                return SimpleNamespace(stop_reason="end_turn", model=kw["model"],
                                       content=[SimpleNamespace(type="text", text=json.dumps(d))],
                                       usage=SimpleNamespace(input_tokens=120, output_tokens=300,
                                                             cache_read_input_tokens=1500 if len(self.calls) > 1 else 0,
                                                             cache_creation_input_tokens=0 if len(self.calls) > 1 else 1500))
        raise AssertionError(f"unscripted request: {user[:80]}")


SRC = {"document": "w.pdf", "page": 1, "rights_status": "TEACHER_OWNED",
       "permitted_uses": ["storage", "search", "derive", "llm"]}


def rec(pid, stem, opts, key, fmt="single_correct_mcq", **kw):
    return PYQRecord(pyq_id=pid, exam="SAMPLE", year=2025, subject=kw.get("subject", "MATHEMATICS"),
                     question_format=fmt, stem=stem,
                     options=[{"id": i, "text": t} for i, t in opts], answer_key=key,
                     source=kw.get("source", SRC))


EQ_STEM = "The sum of all real x satisfying (x^2 - x - 6)/(x + 2) = 0 is"
EQ_OPTS = [("A", "1"), ("B", "3"), ("C", "-2"), ("D", "-1")]
EQ_FORMAL = {"kind": "equation", "lhs": "(x**2-x-6)/(x+2)", "rhs": "0", "var": "x", "domain": "reals",
             "target": "sum"}


def gw(client, budget=None):
    return Gateway(client=client, ledger=Ledger(budget_usd=budget), cache=ResultCache(path=None))


def test_correct_draft_verifies_and_cache_prevents_second_payment():
    fc = FakeClient([("x^2 - x - 6", [_draft("equation", EQ_FORMAL, EQ_OPTS)])])
    g = gw(fc)
    out = formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B")], g)[0]
    assert IngestStatus.PARENT_VERIFIED in out.ingest.statuses and len(fc.calls) == 1
    out2 = formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B")], g)[0]
    assert len(fc.calls) == 1 and g.ledger.saved_by_cache == 1      # no second API call
    assert out2.record["formal_provenance"]["status"] == "LLM_DRAFT_NEEDS_TEACHER_CHECK"


def test_answer_key_never_sent_and_system_prompt_frozen():
    fc = FakeClient([("x^2 - x - 6", [_draft("equation", EQ_FORMAL, EQ_OPTS)]),
                     ("projected", [_draft("projectile_level", {"kind": "projectile_level", "u": "20",
                                                               "theta_deg": "30", "g": "10", "target": "max_height"},
                                           decision="formalized")])])
    g = gw(fc)
    formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B"),
                       rec("P1", "A ball is projected at 20 m/s at 30 degrees (g = 10). Max height?", [], "5",
                           fmt="numerical_integer", subject="PHYSICS")], g)
    systems = {json.dumps(c["system"]) for c in fc.calls}
    assert len(systems) == 1                                   # byte-identical -> prompt cache hits
    assert fc.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    for c in fc.calls:
        assert "answer_key" not in c["messages"][0]["content"]
        assert c["output_config"]["format"]["type"] == "json_schema"


def test_triage_rights_and_duplicates_save_calls():
    fc = FakeClient([("x^2 - x - 6", [_draft("equation", EQ_FORMAL, EQ_OPTS)])])
    g = gw(fc)
    no_llm = dict(SRC, permitted_uses=["storage", "search"])
    outs = formalize_records([
        rec("Q1", EQ_STEM, EQ_OPTS, "B"),
        rec("Q2", EQ_STEM, EQ_OPTS, "B"),                                          # duplicate text
        rec("Q3", "The number of geometrical isomers of [Co(NH3)4Cl2]+ is", [("A", "2"), ("B", "3")], "A",
            subject="CHEMISTRY"),                                                  # triage: unsupported
        rec("Q4", EQ_STEM + " (copy)", EQ_OPTS, "B", source=no_llm),               # rights: no 'llm'
    ], g)
    assert len(fc.calls) == 1
    assert [o.action for o in outs] == ["llm", "reused", "skipped_triage", "skipped_rights"]
    assert IngestStatus.PARENT_VERIFIED in outs[1].ingest.statuses


def test_structural_error_gets_one_escalated_retry():
    bad = _draft("equation", {**EQ_FORMAL, "lhs": "(x^2-x-6)/(x+2) ; import os"}, EQ_OPTS)
    fc = FakeClient([("x^2 - x - 6", [bad, _draft("equation", EQ_FORMAL, EQ_OPTS)])])
    out = formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B")], gw(fc))[0]
    assert out.attempts == 2 and len(fc.calls) == 2
    assert fc.calls[0]["output_config"]["effort"] == "medium"
    assert fc.calls[1]["output_config"]["effort"] == "high"
    assert "rejected by the verifier" in fc.calls[1]["messages"][0]["content"]
    assert IngestStatus.PARENT_VERIFIED in out.ingest.statuses


def test_key_disagreement_quarantined_without_retry():
    wrong = _draft("equation", {**EQ_FORMAL, "target": "product"},
                   [("A", "1"), ("B", "3"), ("C", "-2"), ("D", "-6")])
    fc = FakeClient([("x^2 - x - 6", [wrong])])
    opts = [("A", "1"), ("B", "3"), ("C", "-2"), ("D", "-6")]
    out = formalize_records([rec("Q1", EQ_STEM, opts, "D")], gw(fc))[0]   # key D (-6) vs derived 3 (B)
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in out.ingest.statuses
    assert len(fc.calls) == 1                                            # never "fit the key"


def test_unsupported_and_refusal_routed_to_teacher():
    fc = FakeClient([("x^2 - x - 6", [_draft("none", {}, decision="unsupported")]),
                     ("satisfying x", ["REFUSE", "REFUSE"])])
    outs = formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B"),
                              rec("Q2", "Find roots satisfying x = 2", [("A", "2"), ("B", "3")], "A")], gw(fc))
    assert outs[0].llm_decision == "unsupported" and outs[0].ingest is None
    assert outs[1].ingest is None and any("refusal" in n for n in outs[1].notes)


def test_budget_blocks_before_spending():
    fc = FakeClient([("x^2 - x - 6", [_draft("equation", EQ_FORMAL, EQ_OPTS)])])
    with pytest.raises(BudgetExceeded):
        formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B")], gw(fc, budget=0.0001))
    assert fc.calls == []


def test_ledger_costs_and_triage_rules():
    fc = FakeClient([("x^2 - x - 6", [_draft("equation", EQ_FORMAL, EQ_OPTS)])])
    g = gw(fc)
    formalize_records([rec("Q1", EQ_STEM, EQ_OPTS, "B")], g)
    row = g.ledger.rows[0]
    # opus 5.5: 120*4 + 300*20 + 1500*5 (cache write) per 1M
    assert abs(row.cost_usd - (120 * 4 + 300 * 20 + 1500 * 5) / 1e6) < 1e-12
    assert triage("Which combination is not a meaningful quantity? dimensions") == "dimension_meaningful"
    assert triage("Draw the mechanism and IUPAC name") is None
    assert len(SYSTEM_FORMALIZE) > 2500   # long enough to clear the 512-token cache minimum
