"""Question generation for the pitch chapters: question FAMILIES -> verified, original MCQs / numericals.

A family is a parameterised question pattern (modelled on bank questions, never copying their numbers or wording).
For one parameter draw it supplies
  formal(p)      the engine formal for the CORRECT reading (solved by two independent methods)
  stem(p)        the question text (HTML with $...$ LaTeX), rendered only from p
  mistakes(p)    student mistakes, each a formal for the WRONG reading; the engine solves it the same way, so every
                 wrong option is the verified answer to a named misreading (never a random number)
  display(v)     how a value is printed in an option
  explain(p, v)  a short worked solution (HTML)

generate(family, n) keeps only items where
  * the correct answer is established (engine value, no blocking record),
  * at least 3 mistake values are established, distinct from each other and from the answer,
  * the printed options are distinct as text (no two options look the same),
  * the assembled item passes verify_item (key re-derived from the stored formal, exactly one option correct,
    every distractor traced to its mistake), apart from checks a teacher signs off.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import sympy as sp

from cqse.core.problem import (Answer, Distractor, Identity, Knowledge, Option, ProblemState, Provenance,
                               QuestionFormat, Subject)
from cqse.math.expr import tri_equal

FAMILIES: dict[str, "Family"] = {}


@dataclass
class Mistake:
    id: str
    formal: dict                       # formal of the wrong reading (same kind as the correct one)
    why_students: str                  # why students make this error
    why_wrong: str                     # why it is wrong


@dataclass
class Family:
    id: str
    subject: Subject
    chapter: str
    topic: str
    difficulty: str                    # EASY / MEDIUM / HARD
    sample: Callable[[random.Random], dict]
    formal: Callable[[dict], dict]
    stem: Callable[[dict], str]
    mistakes: Callable[[dict], list[Mistake]]
    display: Callable[[sp.Basic, dict], str] = lambda v, p: str(v)
    explain: Callable[[dict, sp.Basic], str] = lambda p, v: ""
    numerical: bool = False            # True -> integer-answer numerical question (no options)
    modelled_on: list[str] = field(default_factory=list)   # bank externalIds of the pattern (lineage)

    def register(self) -> "Family":
        FAMILIES[self.id] = self
        return self


REVIEWS_PATH = __import__("pathlib").Path(__file__).resolve().parents[2] / "data/generation/family_reviews.json"


def family_fingerprint(fam: "Family") -> str:
    """Hash of the family's code: any change to sampling, model, stem or mistakes voids a teacher review."""
    import inspect
    src = "".join(inspect.getsource(fn) for fn in (fam.sample, fam.formal, fam.stem, fam.mistakes))
    return hashlib.sha256(src.encode()).hexdigest()[:16]


def family_review(fam: "Family") -> Optional[dict]:
    """A teacher's approval of the family's MODEL (stem <-> formal correspondence, mistakes realistic)."""
    try:
        reviews = json.loads(REVIEWS_PATH.read_text())
    except (OSError, ValueError):
        return None
    r = reviews.get(fam.id)
    return r if r and r.get("fingerprint") == family_fingerprint(fam) else None


def family_stem(formal: dict) -> Optional[str]:
    """Re-render a generated item's stem from its formal (used by verify_item's stem check)."""
    g = formal.get("generated_by")
    if not g or g["family"] not in FAMILIES:
        return None
    return FAMILIES[g["family"]].stem(g["params"])


def _solve(subject: Subject, formal: dict):
    from cqse.verification.pipeline import canonical_answer, software_blocking
    can = canonical_answer(subject, formal)
    if can.value is None or software_blocking(can.records):
        return None, can
    return can.value, can


@dataclass
class Generated:
    item: ProblemState
    report: Any
    status: str                         # VERIFIED / VERIFIED_TEACHER_SIGNOFF
    family: Family
    params: dict


def build(fam: Family, p: dict, seed: int = 0) -> tuple[Optional[Generated], str]:
    from cqse.verification.pipeline import EXPERT_RESOLVABLE, verify_item
    formal = dict(fam.formal(p))
    formal["generated_by"] = {"family": fam.id, "params": p}
    val, can = _solve(fam.subject, formal)
    if val is None:
        return None, "correct answer not established"
    stem = fam.stem(p)
    pid = "GEN-" + hashlib.sha1(f"{fam.id}:{json.dumps(p, sort_keys=True)}".encode()).hexdigest()[:12]
    base = dict(identity=Identity(problem_id=pid, family_id=fam.id, lineage=list(fam.modelled_on)),
                subject=fam.subject, exam_profile_id="JEE_MAIN-2027-v1",
                knowledge=Knowledge(chapter=fam.chapter, topic=fam.topic),
                formal=formal, stem=stem, solution_steps=can.steps,
                provenance=Provenance(rights_status="GENERATED"))
    if fam.numerical:
        if not (sp.sympify(val).is_integer):
            return None, f"numerical answer {val} is not an integer"
        item = ProblemState(**base, question_format=QuestionFormat.NUMERICAL_INTEGER,
                            answer=Answer(exact_answer=str(val)))
    else:
        chosen: list[tuple[Mistake, sp.Basic]] = []
        for m in fam.mistakes(p):
            try:
                mv, _ = _solve(fam.subject, m.formal)
            except Exception:            # a misreading the engine cannot pose is simply not used
                continue
            if mv is None or tri_equal(mv, val) is not False:
                continue
            if isinstance(mv, sp.FiniteSet) and len(mv) != 1 and not fam.display(mv, p).strip():
                continue
            if any(tri_equal(mv, c[1]) is not False for c in chosen):
                continue
            if fam.display(mv, p) in {fam.display(val, p)} | {fam.display(c[1], p) for c in chosen}:
                continue
            chosen.append((m, mv))
            if len(chosen) == 3:
                break
        if len(chosen) < 3:
            return None, f"only {len(chosen)} distinct verified mistake values"
        rng = random.Random(f"{pid}:{seed}")
        entries = [(None, val)] + chosen
        rng.shuffle(entries)
        options, distractors, key = [], [], []
        for oid, (m, v) in zip("ABCD", entries):
            options.append(Option(option_id=oid, value=str(v), display=fam.display(v, p)))
            if m is None:
                key.append(oid)
            else:
                distractors.append(Distractor(option_id=oid, value=str(v), misconception_id=m.id,
                                              error_operation=m.id,
                                              derivation_trace=[f"engine-verified value of the misreading: {v}"],
                                              why_students_make_this_error=m.why_students,
                                              why_it_is_wrong=m.why_wrong, verified_wrong=True))
        item = ProblemState(**base, question_format=QuestionFormat.SINGLE_CORRECT_MCQ, options=options,
                            distractors=distractors, answer=Answer(exact_answer=str(val), correct_option_ids=key))
    rep = verify_item(item)
    hard_fail = [r for r in rep.records if r.hard and not r.is_affirmative()
                 and not (r.status.value == "UNRESOLVED" and r.check_id in EXPERT_RESOLVABLE)]
    if hard_fail:
        return None, "; ".join(f"{r.check_id}: {r.result}" for r in hard_fail)[:300]
    pending = [r for r in rep.records if r.hard and not r.is_affirmative()]
    rv = family_review(fam)
    if rv and pending and all(r.check_id in ("model.correspondence", "distractors.plausibility",
                                             "stem.formal_correspondence") for r in pending):
        from cqse.core.evidence import CheckStatus, VerificationRecord
        rep.add(VerificationRecord(check_id="family.teacher_review", status=CheckStatus.EXPERT_REVIEWED,
                                   method="teacher approved this family's model and mistakes",
                                   reviewer=rv["reviewer"], result=f"approved {rv['date']} "
                                   f"(family code fingerprint {rv['fingerprint']})"))
        pending = []
    status = "VERIFIED" if not pending else "VERIFIED_TEACHER_SIGNOFF"
    return Generated(item, rep, status, fam, p), "ok"


def generate(fam: Family, n: int, seed: int = 0, max_tries: int = 200) -> tuple[list[Generated], list[str]]:
    rng = random.Random(f"{fam.id}:{seed}")
    out, seen, rejects = [], set(), []
    for _ in range(max_tries):
        if len(out) >= n:
            break
        p = fam.sample(rng)
        k = json.dumps(p, sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        g, why = build(fam, p, seed)
        if g is None:
            rejects.append(f"{p}: {why}")
            continue
        out.append(g)
    return out, rejects


def to_bank_row(g: Generated) -> dict:
    """Export in the question bank's own schema (Prisma model Question / all_questions.json)."""
    it, fam = g.item, g.family
    expl = fam.explain(g.params, sp.sympify(it.answer.exact_answer))
    mistakes = {d.option_id: {"mistake": d.misconception_id, "why_students": d.why_students_make_this_error,
                              "why_wrong": d.why_it_is_wrong} for d in it.distractors}
    return {
        "externalId": it.identity.problem_id, "sourceName": "CQSE Generator", "exam": "JEE_MAIN",
        "subject": fam.subject.value, "chapter": fam.chapter, "topic": fam.topic, "year": 2026,
        "paperTitle": "CQSE generated (verified)", "difficulty": fam.difficulty,
        "questionType": "NUMERICAL" if fam.numerical else "MCQ_SINGLE",
        "questionContent": {"format": "html", "content": it.stem},
        "options": [{"id": o.option_id, "content": o.display} for o in it.options],
        "correctAnswers": it.answer.correct_option_ids,
        "answer": {"value": it.answer.exact_answer} if fam.numerical else None,
        "explanation": {"format": "html", "content": expl},
        "media": [],
        "sourceMetadata": {"generator": "cqse", "family": fam.id, "params": g.params,
                           "verification": g.status, "modelled_on": fam.modelled_on,
                           "distractor_origins": mistakes,
                           "checks": [{"id": r.check_id, "status": r.status.value} for r in g.report.records]},
        "reviewStatus": "PENDING_REVIEW",
    }
