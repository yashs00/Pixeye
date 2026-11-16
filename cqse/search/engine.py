"""Beam search over legal transformations (blueprint 4).

Correctness is a constraint, not a reward: a child that fails assembly or any
non-expert-resolvable hard gate is discarded (with the reason recorded), never
scored. Only verified children are ranked; diversity is enforced in top-k.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sympy as sp

from cqse.core.evidence import content_hash
from cqse.core.problem import Knowledge, ProblemState, QuestionFormat, Subject
from cqse.search.operators import legal_moves
from cqse.verification.pipeline import (AssemblyError, build_item, canonical_answer, software_blocking,
                                        verify_item)


@dataclass
class Candidate:
    item: ProblemState
    lineage: list[str]
    score: float
    report_summary: str
    families: set[str] = field(default_factory=set)


@dataclass
class SearchResult:
    candidates: list[Candidate]
    rejected: list[tuple[str, str]]  # (lineage, reason)
    expanded: int


def equivalence_key(subject: Subject, formal: dict) -> str:
    if subject == Subject.MATHEMATICS:
        try:
            from cqse.math.engine import build_model
            m = build_model(formal)
            core = str(sp.together(m.lhs - m.rhs))  # 'together' does not cancel factors: traps stay distinct
            return content_hash({"e": core, "d": formal.get("domain", "reals"), "t": formal.get("target")})
        except Exception:  # noqa: BLE001
            pass
    return content_hash(formal)


def _score(item: ProblemState, families: set[str], parent_formal: dict) -> float:
    """Ranking among VALID items only: diversity of move families + conceptual traps."""
    s = 1.0 * len(families)
    if "trap" in families:
        s += 1.5
    if "regime" in families:
        s += 1.0
    if item.subject == Subject.MATHEMATICS:
        conds = len(item.solution_steps[0]) if item.solution_steps else 0
        s += 0.002 * conds
    if item.formal == parent_formal:
        s -= 10
    return s


def search(seed_id: str, subject: Subject, formal: dict, exam_profile_id: str,
           depth: int = 2, beam: int = 6, top_k: int = 5,
           question_format: QuestionFormat = QuestionFormat.SINGLE_CORRECT_MCQ,
           knowledge: Optional[Knowledge] = None, max_children: int = 120) -> SearchResult:
    # The parent itself must verify before anything is derived from it.
    # (Its solution must verify; it need not have enough distractors to be an MCQ itself.)
    if formal.get("kind") == "dimension_meaningful":
        from cqse.physics.dimensions import build_dim_model
        build_dim_model(formal)  # raises if the relation is impossible or contradicts the stated facts
    else:
        can = canonical_answer(subject, formal)
        bad = software_blocking(can.records)
        if can.value is None or bad:
            raise AssemblyError("parent solution does not verify: " +
                                "; ".join(f"{r.check_id}={r.status.value}: {r.result}" for r in bad))

    seen = {equivalence_key(subject, formal)}
    frontier: list[tuple[dict, list[str], set[str]]] = [(formal, [], set())]
    valid: list[Candidate] = []
    rejected: list[tuple[str, str]] = []
    expanded = 0

    for _ in range(depth):
        next_frontier: list[tuple[float, dict, list[str], set[str]]] = []
        for f, lineage, fams in frontier:
            for op in legal_moves(subject, f):
                for label, child in op.propose(f):
                    if expanded >= max_children:
                        break
                    key = equivalence_key(subject, child)
                    if key in seen:
                        continue
                    seen.add(key)
                    expanded += 1
                    lin = lineage + [f"{op.op_id}[{label}]"]
                    cid = f"{seed_id}.{len(valid) + len(rejected) + 1}"
                    try:
                        item = build_item(cid, subject, child, exam_profile_id, question_format,
                                          knowledge=knowledge, parent_id=seed_id, lineage=lin)
                    except Exception as e:  # noqa: BLE001
                        rejected.append((" > ".join(lin), f"assembly: {str(e)[:160]}"))
                        continue
                    rep = verify_item(item)
                    hard_block = software_blocking(rep)
                    if hard_block:
                        rejected.append((" > ".join(lin), "gate: " + ", ".join(
                            f"{r.check_id}={r.status.value}" for r in hard_block)))
                        continue
                    nf = fams | {op.family}
                    sc = _score(item, nf, formal)
                    valid.append(Candidate(item, lin, sc, rep.summary(), nf))
                    next_frontier.append((sc, child, lin, nf))
        next_frontier.sort(key=lambda t: -t[0])
        frontier = [(f, l, fm) for _, f, l, fm in next_frontier[:beam]]
        if not frontier:
            break

    # Diverse top-k: prefer distinct family signatures (multi-PV style).
    valid.sort(key=lambda c: -c.score)
    picked: list[Candidate] = []
    sigs: set[frozenset] = set()
    for c in valid:
        sig = frozenset(c.families)
        if sig in sigs:
            continue
        picked.append(c)
        sigs.add(sig)
        if len(picked) == top_k:
            break
    for c in valid:
        if len(picked) >= top_k:
            break
        if c not in picked:
            picked.append(c)
    return SearchResult(picked, rejected, expanded)
