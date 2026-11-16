"""PYQ ingestion (blueprint 9, 35).

Input: JSONL, one question per line (schema: PYQRecord below; see
data/samples/pyq_sample.jsonl and docs in README).

Rules:
* The source answer key is a CLAIM. When a formal state is supplied it is
  solved independently; disagreement -> QUARANTINED_KEY_DISAGREEMENT.
* Missing/unknown rights -> NEEDS_SOURCE (searchable internally only).
* OCR-extracted text without visual review -> NEEDS_VISUAL_REVIEW.
* No formal state -> NEEDS_FORMALIZATION (never guessed by the system).
* Near-duplicates are grouped, never silently dropped.
* A parent's verified status is NEVER inherited by generated children.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from cqse.core.evidence import CheckStatus
from cqse.core.problem import (Answer, Identity, Knowledge, Option, ProblemState, Provenance, QuestionFormat,
                               Subject)
from cqse.search.engine import equivalence_key
from cqse.verification.options import check_options_and_key
from cqse.verification.pipeline import canonical_answer


class PYQOption(BaseModel):
    id: str
    text: str
    value: Optional[str] = None  # machine-readable exact value (needed for automatic key check)


class PYQSource(BaseModel):
    document: str
    page: Optional[Union[int, str]] = None
    edition: Optional[str] = None
    rights_status: Literal["CLEARED", "TEACHER_OWNED", "UNKNOWN", "RESTRICTED"] = "UNKNOWN"
    permitted_uses: list[str] = Field(default_factory=list)  # storage, search, training, derive, display, export
    rights_basis: Optional[str] = None  # who confirmed the rights, and when (required for CLEARED)


class PYQExtraction(BaseModel):
    method: Literal["manual", "digital_text", "ocr"] = "manual"
    confidence: Optional[float] = None
    visual_review_done: bool = False
    unresolved_fragments: list[str] = Field(default_factory=list)


class PYQRecord(BaseModel):
    pyq_id: str
    exam: str
    year: int
    shift: Optional[str] = None
    subject: Subject
    chapter: str = ""
    topic: str = ""
    question_format: QuestionFormat
    stem: str
    options: list[PYQOption] = Field(default_factory=list)
    answer_key: Optional[Union[str, list[str]]] = None
    key_source: Literal["official", "provisional", "unofficial_reference"] = "official"
    numerical_rounding: Optional[Literal["nearest_integer"]] = None  # exam rule for numerical answers
    official_correction: Optional[str] = None
    solution: Optional[str] = None
    source: PYQSource
    extraction: PYQExtraction = Field(default_factory=PYQExtraction)
    formal: Optional[dict[str, Any]] = None
    diagram_files: list[str] = Field(default_factory=list)


class IngestStatus(str, Enum):
    PARENT_VERIFIED = "PARENT_VERIFIED"
    NEEDS_FORMALIZATION = "NEEDS_FORMALIZATION"
    NEEDS_SOURCE = "NEEDS_SOURCE"
    NEEDS_VISUAL_REVIEW = "NEEDS_VISUAL_REVIEW"
    NEEDS_EXPERT_REVIEW = "NEEDS_EXPERT_REVIEW"
    QUARANTINED_KEY_DISAGREEMENT = "QUARANTINED_KEY_DISAGREEMENT"
    NEEDS_OFFICIAL_KEY = "NEEDS_OFFICIAL_KEY"
    QUARANTINED_UNVERIFIABLE = "QUARANTINED_UNVERIFIABLE"
    INVALID_RECORD = "INVALID_RECORD"


class IngestResult(BaseModel):
    pyq_id: str
    statuses: list[IngestStatus]
    notes: list[str] = Field(default_factory=list)
    duplicate_of: list[str] = Field(default_factory=list)
    derived_answer: Optional[str] = None
    family_key: Optional[str] = None


def _norm_tokens(text: str) -> set[str]:
    t = re.sub(r"\s+", " ", text.lower())
    return set(re.findall(r"[a-z]+|\d+(?:\.\d+)?|[=+\-*/^()]", t))


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(1, len(a | b))


def to_problem_state(rec: PYQRecord) -> ProblemState:
    key = rec.official_correction or rec.answer_key
    keys = [] if key is None else (key if isinstance(key, list) else [key])
    mcq = rec.question_format in (QuestionFormat.SINGLE_CORRECT_MCQ, QuestionFormat.MULTIPLE_CORRECT_MCQ)
    return ProblemState(
        identity=Identity(problem_id=rec.pyq_id, family_id=None),
        subject=rec.subject, exam_profile_id=f"{rec.exam}-{rec.year}-historical",
        question_format=rec.question_format,
        knowledge=Knowledge(chapter=rec.chapter, topic=rec.topic),
        formal=rec.formal or {"kind": "unformalized"},
        stem=rec.stem,
        options=[Option(option_id=o.id, value=o.value or "", display=o.text) for o in rec.options],
        answer=Answer(correct_option_ids=keys if mcq else [],
                      exact_answer=None if (mcq or not keys) else str(keys[0])),
        provenance=Provenance(source_documents=[f"{rec.source.document}#p{rec.source.page}"], pyq_ids=[rec.pyq_id],
                              rights_status=rec.source.rights_status, permitted_uses=rec.source.permitted_uses,
                              extraction_confidence=rec.extraction.confidence,
                              source_answer_key=json.dumps(rec.answer_key)))


def ingest_record(rec: PYQRecord) -> IngestResult:
    res = IngestResult(pyq_id=rec.pyq_id, statuses=[])
    if rec.source.rights_status in ("UNKNOWN", "RESTRICTED"):
        res.statuses.append(IngestStatus.NEEDS_SOURCE)
        res.notes.append(f"rights {rec.source.rights_status}: internal search only; no derivation/display/training")
    if rec.extraction.method == "ocr" and not rec.extraction.visual_review_done:
        res.statuses.append(IngestStatus.NEEDS_VISUAL_REVIEW)
        res.notes.append("OCR text must be compared to the page image (exponents, charges, labels)")
    if rec.extraction.unresolved_fragments:
        res.statuses.append(IngestStatus.NEEDS_VISUAL_REVIEW)
        res.notes.append(f"unresolved fragments: {rec.extraction.unresolved_fragments}")
    if rec.diagram_files:
        res.notes.append("diagram present: expert must confirm the formal state encodes it")
    if rec.official_correction and rec.official_correction != rec.answer_key:
        res.notes.append(f"official correction {rec.official_correction!r} supersedes printed key")

    if not rec.formal:
        res.statuses.append(IngestStatus.NEEDS_FORMALIZATION)
        return res

    res.family_key = equivalence_key(rec.subject, rec.formal)
    try:
        item = to_problem_state(rec)
    except ValidationError as e:
        res.statuses.append(IngestStatus.INVALID_RECORD)
        res.notes.append(str(e).splitlines()[0])
        return res
    can = canonical_answer(rec.subject, rec.formal)
    blocking = [r for r in can.records if r.hard and not r.is_affirmative()]
    from cqse.verification.pipeline import software_blocking
    if can.value is None or software_blocking(can.records):
        res.statuses.append(IngestStatus.QUARANTINED_UNVERIFIABLE)
        res.notes += [f"{r.check_id}={r.status.value}: {r.result}" for r in software_blocking(can.records)
                      or blocking]
        return res
    res.derived_answer = str(can.value)

    if item.question_format in (QuestionFormat.SINGLE_CORRECT_MCQ, QuestionFormat.MULTIPLE_CORRECT_MCQ) and \
            any(not o.value for o in rec.options):
        res.statuses.append(IngestStatus.NEEDS_FORMALIZATION)
        res.notes.append("options lack machine-readable 'value'; key cannot be checked automatically")
        return res

    recs = check_options_and_key(item, can.value, rec.numerical_rounding)
    card = next((r for r in recs if r.check_id == "options.cardinality"), None)
    rnd = next((r for r in recs if r.check_id == "numerical.rounding"), None)
    if card is not None and card.data.get("correct"):
        res.notes.append(f"derived option(s): {card.data['correct']}")
    if rnd is not None:
        res.notes.append(f"rounding: {rnd.result}")
    if rec.answer_key is None and rec.official_correction is None:
        # no key to compare: the key check is not a disagreement, it is simply missing
        recs = [r for r in recs if r.check_id != "key.matches_derivation"]
        res.statuses.append(IngestStatus.NEEDS_OFFICIAL_KEY)
    elif rec.key_source != "official":
        res.statuses.append(IngestStatus.NEEDS_OFFICIAL_KEY)
        res.notes.append(f"key source is {rec.key_source}: compared, but an official key is still required")
    bad = [r for r in recs if r.hard and not r.is_affirmative()]
    if any(r.check_id == "key.matches_derivation" and r.status == CheckStatus.FAILED for r in bad):
        res.statuses.append(IngestStatus.QUARANTINED_KEY_DISAGREEMENT)
    elif bad:
        res.statuses.append(IngestStatus.QUARANTINED_UNVERIFIABLE)
    res.notes += [f"{r.check_id}={r.status.value}: {r.result}" for r in bad]
    if not bad:
        if blocking:  # only expert-resolvable checks outstanding
            res.statuses.append(IngestStatus.NEEDS_EXPERT_REVIEW)
            for r in blocking:
                res.notes.append({"chem.reaction_feasibility": "chemistry: reaction feasibility must be confirmed "
                                                              "by a chemist",
                                  "model.correspondence": "teacher must confirm the equations model the stem"
                                  }.get(r.check_id, f"expert check outstanding: {r.check_id}"))
        res.statuses.append(IngestStatus.PARENT_VERIFIED)
        res.notes.append("solution/key verified; stem-to-formal correspondence still needs expert confirmation")
    return res


def ingest_file(path: Union[str, Path], dup_threshold: float = 0.9) -> list[IngestResult]:
    results: list[IngestResult] = []
    seen: list[tuple[str, set[str], Optional[str]]] = []
    for ln, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = PYQRecord(**json.loads(line))
        except (ValidationError, json.JSONDecodeError) as e:
            results.append(IngestResult(pyq_id=f"line{ln}", statuses=[IngestStatus.INVALID_RECORD],
                                        notes=[str(e).splitlines()[0]]))
            continue
        r = ingest_record(rec)
        toks = _norm_tokens(rec.stem + " " + " ".join(o.text for o in rec.options))
        for pid, ptoks, pkey in seen:
            if _jaccard(toks, ptoks) >= dup_threshold or (r.family_key and r.family_key == pkey):
                r.duplicate_of.append(pid)
        seen.append((rec.pyq_id, toks, r.family_key))
        results.append(r)
    return results
