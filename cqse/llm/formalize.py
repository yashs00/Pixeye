"""Draft formal states for PYQs with Claude, then verify them deterministically.

Flow per record (cheapest exit first):
  1. already has 'formal'                     -> no call
  2. rights do not allow external processing  -> no call   (needs "llm" in permitted_uses)
  3. triage says no supported kind fits       -> no call   (keyword rules, free)
  4. identical stem already formalized        -> reuse     (dedupe within the run)
  5. local result cache hit                   -> reuse     (across runs)
  6. API call at the task's normal effort
  7. the draft goes through the SAME verifier as hand-written formal states
  8. structural rejection (bad JSON, unparseable expression, solver cannot verify)
       -> ONE retry at higher effort with the verifier's message
     answer-key disagreement -> NO retry (feedback would leak the key and bias the
       model towards fitting it); quarantined for a teacher with both answers shown.

The model is never told the answer key and never decides correctness.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from cqse.ingest.pyq import IngestResult, IngestStatus, PYQRecord, ingest_record
from cqse.llm.config import TASKS
from cqse.llm.gateway import Gateway, LLMResult
from cqse.llm.prompts import user_message, user_payload

SUPPORTED = {"equation", "projectile_level", "incline_friction", "stoichiometry", "dimension_meaningful",
             "circuit_dc", "equation_system"}

# Cheap, conservative triage. A miss costs nothing but a human formalization;
# a false hit costs one call that will come back "unsupported".
_TRIAGE = [
    ("dimension_meaningful", r"\bdimension|\bdimensionless|meaningful quantity"),
    ("projectile_level", r"\bprojected\b|\bprojectile\b"),
    ("incline_friction", r"\bincline|inclined plane|coefficient of (static|kinetic) friction"),
    ("circuit_dc", r"\bcircuit|\bresistor|\bresistance|\bbattery|\bemf\b|Ω|\bohm"),
    ("stoichiometry", r"->|→|\blimiting reagent|\bmoles? of\b|\breact(s|ed)? (completely|with)"),
    ("equation", r"=|\broots?\b|\bsolutions?\b|\bsatisfying\b"),
    # any quantity with a unit -> general calculation checker
    ("equation_system", r"\d\s*(m|cm|km|s|kg|g|N|J|W|V|A|K|mol|Pa|atm|C|F|ohm|Ω|L|eV|Hz|T)(/|\^|\b)"),
]
_EXCLUDE = re.compile(r"\bisomer|\bhybridi[sz]ation|\bIUPAC|\bmechanism|\bdiagram\b|\bfigure\b|\bgraph\b",
                      re.IGNORECASE)


def triage(stem: str) -> Optional[str]:
    if _EXCLUDE.search(stem):
        return None
    for kind, pat in _TRIAGE:
        if re.search(pat, stem, re.IGNORECASE):
            return kind
    return None


@dataclass
class FormalizeOutcome:
    pyq_id: str
    action: str                     # skipped_has_formal | skipped_rights | skipped_triage | llm | reused
    llm_decision: Optional[str] = None
    attempts: int = 0
    ingest: Optional[IngestResult] = None
    record: Optional[dict] = None   # record with the drafted formal/option values (provenance-tagged)
    notes: list[str] = field(default_factory=list)


def _norm(stem: str) -> str:
    return re.sub(r"\s+", " ", stem.strip().lower())


def _apply_draft(rec: PYQRecord, data: dict) -> tuple[Optional[PYQRecord], str]:
    """Attach a draft to a copy of the record. Returns (record, structural_error)."""
    if data.get("decision") != "formalized":
        return None, ""
    if data.get("kind") not in SUPPORTED:
        return None, f"kind {data.get('kind')!r} is not supported"
    try:
        formal = json.loads(data["formal_json"])
    except (json.JSONDecodeError, TypeError) as e:
        return None, f"formal_json is not valid JSON: {e}"
    if not isinstance(formal, dict) or formal.get("kind") != data["kind"]:
        return None, "formal_json.kind does not match kind"
    new = rec.model_copy(deep=True)
    new.formal = formal
    vals = {v["id"]: v["value"] for v in data.get("option_values", [])}
    if new.options:
        if set(vals) != {o.id for o in new.options}:
            return None, f"option ids {sorted(vals)} do not match the question's {sorted(o.id for o in new.options)}"
        for o in new.options:
            o.value = vals[o.id]
    return new, ""


def _structural_problem(res: IngestResult) -> Optional[str]:
    """Verifier failures worth one retry (NOT key disagreement)."""
    if IngestStatus.QUARANTINED_KEY_DISAGREEMENT in res.statuses:
        return None
    if IngestStatus.QUARANTINED_UNVERIFIABLE in res.statuses or IngestStatus.INVALID_RECORD in res.statuses:
        return "; ".join(res.notes)[:600]
    return None


def formalize_records(records: list[PYQRecord], gateway: Gateway, use_batch: bool = False,
                      force_triage: bool = False) -> list[FormalizeOutcome]:
    outcomes: dict[str, FormalizeOutcome] = {}
    todo: list[tuple[PYQRecord, dict]] = []
    by_stem: dict[str, str] = {}

    for rec in records:
        if rec.formal:
            outcomes[rec.pyq_id] = FormalizeOutcome(rec.pyq_id, "skipped_has_formal")
            continue
        if "llm" not in rec.source.permitted_uses or rec.source.rights_status in ("UNKNOWN", "RESTRICTED"):
            outcomes[rec.pyq_id] = FormalizeOutcome(
                rec.pyq_id, "skipped_rights",
                notes=["sending text to an external API needs rights CLEARED/TEACHER_OWNED and 'llm' in permitted_uses"])
            continue
        if not force_triage and triage(rec.stem) is None:
            gateway.ledger.skipped_by_triage += 1
            outcomes[rec.pyq_id] = FormalizeOutcome(rec.pyq_id, "skipped_triage",
                                                    notes=["no supported kind matches; route to a teacher"])
            continue
        if rec.extraction.method == "ocr" and not rec.extraction.visual_review_done:
            outcomes[rec.pyq_id] = FormalizeOutcome(rec.pyq_id, "skipped_rights",
                                                    notes=["OCR text not visually reviewed; fix the text before "
                                                           "spending tokens on it"])
            continue
        key = _norm(rec.stem) + "|" + "|".join(o.text for o in rec.options)
        if key in by_stem:
            outcomes[rec.pyq_id] = FormalizeOutcome(rec.pyq_id, "reused", notes=[f"same text as {by_stem[key]}"])
            todo.append((rec, {"reuse_of": by_stem[key]}))
            continue
        by_stem[key] = rec.pyq_id
        payload = user_payload(rec.question_format.value, rec.stem, [o.model_dump() for o in rec.options])
        todo.append((rec, payload))

    fresh = [(r, p) for r, p in todo if "reuse_of" not in p]
    first: dict[str, LLMResult] = {}
    if use_batch and fresh:
        first = gateway.batch("formalize", [(r.pyq_id, p, user_message(p)) for r, p in fresh])
    for rec, payload in fresh:
        res = first.get(rec.pyq_id) or gateway.call("formalize", payload, user_message(payload))
        out = FormalizeOutcome(rec.pyq_id, "llm", attempts=1)
        out = _finish(rec, payload, res, gateway, out)
        outcomes[rec.pyq_id] = out

    for rec, payload in todo:
        if "reuse_of" in payload:
            src = outcomes[payload["reuse_of"]]
            o = outcomes[rec.pyq_id]
            o.llm_decision = src.llm_decision
            if src.record:
                new = rec.model_copy(deep=True)
                new.formal = src.record["formal"]
                for opt in new.options:
                    opt.value = next((x["value"] for x in src.record["options"] if x["id"] == opt.id), None)
                o.ingest = ingest_record(new)
                o.record = _tag(new)
    return [outcomes[r.pyq_id] for r in records]


def _finish(rec: PYQRecord, payload: dict, res: LLMResult, gw: Gateway, out: FormalizeOutcome) -> FormalizeOutcome:
    for attempt in (1, 2):
        if not res.ok:
            out.notes.append(f"attempt {attempt}: {res.error}")
            feedback = res.error
        else:
            out.llm_decision = res.data.get("decision")
            if res.data.get("notes"):
                out.notes.append(f"model note: {res.data['notes']}")
            if out.llm_decision != "formalized":
                return out  # unsupported / ambiguous: route to a teacher, no retry
            draft, err = _apply_draft(rec, res.data)
            if draft is not None:
                ing = ingest_record(draft)
                feedback = _structural_problem(ing)
                if feedback is None:
                    out.ingest, out.record = ing, _tag(draft)
                    return out
                out.ingest, out.record = ing, _tag(draft)
            else:
                feedback = err
            out.notes.append(f"attempt {attempt} rejected: {feedback}")
        if attempt == 2:
            break
        out.attempts = 2
        res = gw.call("formalize", payload, user_message(payload, feedback),
                      effort=TASKS["formalize"].escalate_effort)
    return out


def _tag(rec: PYQRecord) -> dict:
    d = rec.model_dump(mode="json")
    d["formal_provenance"] = {"drafted_by": TASKS["formalize"].model, "status": "LLM_DRAFT_NEEDS_TEACHER_CHECK"}
    return d
