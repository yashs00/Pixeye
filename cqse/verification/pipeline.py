"""End-to-end item verification and MCQ assembly.

verify_item(item)  -> VerificationReport (fail closed)
build_item(...)    -> ProblemState whose stem, options, key and distractors are
                      all derived from the formal state.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

import sympy as sp

from cqse.chemistry import engine as chem
from cqse.core.evidence import CheckStatus, VerificationRecord, VerificationReport, content_hash
from cqse.core.problem import (Answer, Distractor, Identity, Knowledge, Option, ProblemState, Provenance,
                               QuestionFormat, Subject)
from cqse.exam.profiles import check_profile
from cqse.math import engine as math_engine
from cqse.math import misconceptions as math_mis
from cqse.math.expr import tri_equal
from cqse.physics import engine as phys
from cqse.verification.options import check_options_and_key

# Checks a qualified expert may resolve by attestation. Nothing else can be
# overridden by a human; a FAILED check can never be overridden.
EXPERT_RESOLVABLE = {"chem.reaction_feasibility", "stem.formal_correspondence",
                     "model.correspondence", "distractors.plausibility",
                     "diagram.formal_correspondence",
                     "statement.truth"}  # curated statement truth awaiting a teacher  # only when UNRESOLVED (hand-drawn source figure)


def software_blocking(records) -> list[VerificationRecord]:
    """Hard checks that block even before human review.

    Only an UNRESOLVED expert-resolvable check may wait for an expert; a FAILED
    check always blocks, whatever its id.
    """
    if isinstance(records, VerificationReport):
        records = records.records
    return [r for r in records if r.hard and not r.is_affirmative()
            and not (r.status == CheckStatus.UNRESOLVED and r.check_id in EXPERT_RESOLVABLE)]


@dataclass
class Canonical:
    value: Optional[sp.Basic]
    units: str
    records: list[VerificationRecord]
    steps: list[str]


def _to_sympy(v) -> sp.Basic:
    if isinstance(v, Fraction):
        return sp.Rational(v.numerator, v.denominator)
    return v


def value_str(v: sp.Basic) -> str:
    v = _to_sympy(v)
    if v == sp.S.EmptySet:
        return "{}"
    return str(v)


_CANON_CACHE: dict[str, Canonical] = {}


def canonical_answer(subject: Subject, formal: dict) -> Canonical:
    """Memoised by content hash: search and re-verification never solve the same state twice.
    Records are copied on every hit so per-report mutation cannot leak between items."""
    key = content_hash({"s": subject.value, "f": formal})
    hit = _CANON_CACHE.get(key)
    if hit is None:
        hit = _canonical_uncached(subject, formal)
        if len(_CANON_CACHE) > 5000:
            _CANON_CACHE.clear()
        _CANON_CACHE[key] = hit
    return Canonical(hit.value, hit.units, [r.model_copy(deep=True) for r in hit.records], list(hit.steps))


META_KEYS = ("generated_by",)   # provenance carried on a formal; never part of the mathematics


def _canonical_uncached(subject: Subject, formal: dict) -> Canonical:
    if any(k in formal for k in META_KEYS):
        formal = {k: v for k, v in formal.items() if k not in META_KEYS}
    from cqse.engines import REGISTRY, lookup
    if formal.get("kind") in REGISTRY:
        fn = lookup(formal["kind"])
        if fn is None:
            return Canonical(None, "", [VerificationRecord(check_id="engine.available", status=CheckStatus.UNRESOLVED,
                                                           method="engine registry",
                                                           result=f"engine for {formal['kind']!r} not installed")], [])
        try:
            r = fn(formal, subject)
        except Exception as e:  # noqa: BLE001 - an engine crash is never a pass
            return Canonical(None, "", [VerificationRecord(check_id="engine.run", status=CheckStatus.UNRESOLVED,
                                                           method=formal["kind"],
                                                           result=f"{type(e).__name__}: {e}")], [])
        return Canonical(r.value, r.unit, r.records, r.steps)
    if formal.get("kind") == "circuit_dc":
        from cqse.physics import circuits
        s = circuits.solve_and_verify(formal)
        steps = ["Netlist solved by exact modified nodal analysis",
                 "Certificate: KCL at every node, every element law, Tellegen power balance",
                 f"{formal.get('target', {}).get('quantity')} = {s.value} {s.unit}"]
        return Canonical(s.value, s.unit, s.records, steps)
    if formal.get("kind") == "equation_system":
        from cqse.generic.system import solve_system
        s = solve_system(formal)
        steps = [f"Model: {formal.get('model', [])}"] + [f"Equation {i + 1}: {e}" for i, e in
                 enumerate(formal.get("equations", []))] + [f"{formal.get('target')} = {s.value} {s.unit}"]
        return Canonical(s.value, s.unit, s.records, steps)
    if subject == Subject.MATHEMATICS:
        s = math_engine.solve_and_verify(formal)
        steps = [f"Definedness conditions: {s.records[0].data.get('conditions', [])}",
                 f"Candidate roots rejected on back-substitution/domain: {[str(r[0]) for r in s.rejected]}",
                 f"Verified solutions: {s.solutions}",
                 f"{formal.get('target', 'solution_set')} = {value_str(s.target_value)}"]
        ok = s.target_value is not None and s.target_value != sp.nan
        return Canonical(s.target_value if ok else None, "", s.records, steps)
    if subject == Subject.PHYSICS:
        s = phys.solve_and_verify(formal)
        ok = s.value is not None and s.value != sp.nan
        steps = [f"Regime: {s.regime}" if s.regime else "Model: level-ground projectile",
                 f"{formal.get('target')} = {s.value} {s.units}"]
        return Canonical(s.value if ok else None, s.units, s.records, steps)
    s = chem.solve_and_verify(formal)
    steps = [f"Balanced coefficients: {s.coeffs}", f"Limiting reagent: {s.limiting}",
             f"Answer: {s.value} {s.units}"]
    return Canonical(_to_sympy(s.value) if s.value is not None else None, s.units, s.records, steps)


def render_stem(subject: Subject, formal: dict) -> str:
    if formal.get("generated_by"):
        from cqse.generation.framework import family_stem
        st = family_stem(formal)
        if st is not None:
            return st
    if formal.get("kind") == "circuit_dc":
        from cqse.physics import circuits
        return circuits.render_stem(formal)
    if formal.get("kind") == "equation_system":
        if not formal.get("stem"):
            raise AssemblyError("equation_system items carry their own stem text (teacher/LLM written)")
        return formal["stem"]
    if subject == Subject.MATHEMATICS:
        return math_engine.render_equation_stem(formal)
    if subject == Subject.PHYSICS:
        if formal["kind"] == "projectile_level":
            what = {"range": "horizontal range", "max_height": "maximum height",
                    "time_of_flight": "time of flight"}[formal["target"]]
            return (f"A particle is projected from level ground with speed {formal['u']} m/s at "
                    f"{formal['theta_deg']} degrees above the horizontal. Take g = {formal['g']} m/s^2 and "
                    f"neglect air resistance. Find the {what} (landing at the launch height).")
        what = {"acceleration": "magnitude of the acceleration of the block",
                "friction_force": "magnitude of the friction force on the block"}[formal["target"]]
        return (f"A block of mass {formal['m']} kg is released from rest on a fixed rough incline of angle "
                f"{formal['theta_deg']} degrees. The coefficients of static and kinetic friction are "
                f"{formal['mu_s']} and {formal['mu_k']}. Take g = {formal['g']} m/s^2. Find the {what}.")
    given = ", ".join(f"{v.get('mass_g', v.get('moles'))} {'g' if 'mass_g' in v else 'mol'} of {k}"
                      for k, v in formal["given"].items())
    masses = ", ".join(f"{k} = {v}" for k, v in formal["atomic_masses"].items())
    q = "mass (in g)" if formal["target"]["quantity"] == "mass_g" else "amount (in mol)"
    return (f"For the reaction {formal['reaction']}, {given} are allowed to react completely. "
            f"Find the {q} of {formal['target']['species']} formed. (Atomic masses: {masses})")


def _misconception_candidates(subject: Subject, formal: dict, canonical: sp.Basic):
    if formal.get("kind") == "circuit_dc":
        from cqse.physics import circuits
        return circuits.misconceptions(formal)
    if formal.get("kind") == "equation_system":
        from cqse.generic.system import misconceptions as generic_mis
        return generic_mis(formal)
    if subject == Subject.MATHEMATICS:
        res, _ = math_mis.generate(formal, canonical)
        return [(r.misconception_id, r.value, r.trace, r.why_students, r.why_wrong) for r in res]
    if subject == Subject.PHYSICS:
        return phys.misconceptions(formal)
    return [(a, _to_sympy(b), c, d, e) for a, b, c, d, e in chem.misconceptions(formal)]


class AssemblyError(RuntimeError):
    pass


def build_item(problem_id: str, subject: Subject, formal: dict, exam_profile_id: str,
               question_format: QuestionFormat = QuestionFormat.SINGLE_CORRECT_MCQ,
               n_options: int = 4, seed: int = 0, knowledge: Optional[Knowledge] = None,
               parent_id: Optional[str] = None, lineage: Optional[list[str]] = None) -> ProblemState:
    if formal.get("kind") == "dimension_meaningful":
        return _build_dimension_item(problem_id, formal, exam_profile_id, question_format, n_options, seed,
                                     knowledge, parent_id, lineage)
    can = canonical_answer(subject, formal)
    if can.value is None:
        raise AssemblyError("no verified canonical answer: " +
                            "; ".join(f"{r.check_id}={r.status.value}:{r.result}" for r in can.records
                                      if not r.is_affirmative()))
    base = dict(identity=Identity(problem_id=problem_id, parent_id=parent_id, lineage=lineage or []),
                subject=subject, exam_profile_id=exam_profile_id, question_format=question_format,
                knowledge=knowledge or Knowledge(), formal=formal, stem=render_stem(subject, formal),
                solution_steps=can.steps, provenance=Provenance(rights_status="GENERATED"),
                diagram_svg=_render_diagram(formal))

    if question_format in (QuestionFormat.NUMERICAL_INTEGER, QuestionFormat.NUMERICAL_DECIMAL):
        return ProblemState(**base, answer=Answer(exact_answer=value_str(can.value), units=can.units or None))

    if question_format != QuestionFormat.SINGLE_CORRECT_MCQ:
        raise AssemblyError(f"automatic assembly not implemented for {question_format.value}")

    chosen: list[tuple] = []
    for cand in _misconception_candidates(subject, formal, can.value):
        val = cand[1]
        if tri_equal(val, can.value) is not False:
            continue
        if any(tri_equal(val, c[1]) is not False for c in chosen):
            continue
        if isinstance(val, sp.Expr) and val.is_number and can.units and val.is_negative:
            continue  # magnitude asked: negative values are not plausible distractors
        chosen.append(cand)
        if len(chosen) == n_options - 1:
            break
    if len(chosen) < n_options - 1:
        raise AssemblyError(f"only {len(chosen)} verified misconception distractor(s); need {n_options - 1}. "
                            "Refusing to pad with random values.")
    rng = random.Random(f"{problem_id}:{seed}")
    entries = [("correct", can.value, None)] + [("d", c[1], c) for c in chosen]
    rng.shuffle(entries)
    letters = "ABCDEFGH"
    options, distractors, correct_ids = [], [], []
    for i, (kind, val, meta) in enumerate(entries):
        oid = letters[i]
        disp = value_str(val) + (f" {can.units}" if can.units else "")
        options.append(Option(option_id=oid, value=value_str(val), display=disp))
        if kind == "correct":
            correct_ids.append(oid)
        else:
            mid, _, trace, why_s, why_w = meta
            distractors.append(Distractor(option_id=oid, value=value_str(val), misconception_id=mid,
                                          error_operation=mid, derivation_trace=trace,
                                          why_students_make_this_error=why_s, why_it_is_wrong=why_w,
                                          verified_wrong=True))
    return ProblemState(**base, options=options, distractors=distractors,
                        answer=Answer(exact_answer=value_str(can.value), units=can.units or None,
                                      correct_option_ids=correct_ids))


def _render_diagram(formal: dict) -> str:
    if formal.get("kind") == "circuit_dc":
        from cqse.physics import circuits
        return circuits.render_svg(formal)
    return ""


def verify_item(item: ProblemState, teacher_override_profile: bool = False) -> VerificationReport:
    rep = VerificationReport(item_hash=content_hash(item.release_payload()))
    rep.add(check_profile(item, teacher_override_profile))
    if item.formal.get("kind") == "dimension_meaningful":
        return _verify_dimension_item(item, rep)
    can = canonical_answer(item.subject, item.formal)
    rep.extend(can.records)

    # Stem must be the exact version that was solved.
    if item.provenance.rights_status == "GENERATED":
        rendered = render_stem(item.subject, item.formal) if can.value is not None else None
        same = rendered == item.stem
        rep.add(VerificationRecord(
            check_id="stem.formal_correspondence",
            status=CheckStatus.EXACT_CHECKED if same else CheckStatus.FAILED,
            method="stem re-rendered from formal state", result="identical" if same else "stem was edited or "
            "does not match the formal state; re-render or re-formalize"))
    else:
        rep.add(VerificationRecord(check_id="stem.formal_correspondence", status=CheckStatus.UNRESOLVED,
                                   method="human comparison required",
                                   result="source/hand-written stem: expert must confirm it encodes the formal state"))

    expected_svg = _render_diagram(item.formal)
    if expected_svg or item.diagram_svg:
        same = expected_svg == item.diagram_svg
        rep.add(VerificationRecord(
            check_id="diagram.formal_correspondence",
            status=CheckStatus.EXACT_CHECKED if same else (
                CheckStatus.UNRESOLVED if item.provenance.rights_status != "GENERATED" else CheckStatus.FAILED),
            method="diagram re-rendered from the formal state",
            result="diagram drawn from the same netlist" if same else
            "diagram differs from the formal state (edited or hand-drawn): must match exactly"))

    if can.value is not None:
        rounding = None
        try:
            from cqse.exam.profiles import load_profile
            sec = load_profile(item.exam_profile_id).section_for(item.subject.value, item.question_format.value)
            rounding = (sec or {}).get("rounding")
        except Exception:  # noqa: BLE001 - profile problems are reported by exam.profile
            pass
        rep.extend(check_options_and_key(item, can.value, rounding))
        # Units on numerical answers must match the derivation.
        if can.units and item.answer.units and item.answer.units != can.units:
            rep.add(VerificationRecord(check_id="key.units", status=CheckStatus.FAILED, method="unit compare",
                                       result=f"declared {item.answer.units}, derived {can.units}"))
        # Distractor traces: every non-key option must have a verified origin.
        if item.question_format == QuestionFormat.SINGLE_CORRECT_MCQ:
            rep.add(_check_distractor_coverage(item, can.value))
            if item.formal.get("kind") == "equation_system":
                rep.add(VerificationRecord(
                    check_id="distractors.plausibility", status=CheckStatus.UNRESOLVED,
                    method="teacher review",
                    result="wrong options come from mechanical equation mutations; a teacher must confirm "
                           "each is a realistic student error"))
    return rep


def _check_distractor_coverage(item: ProblemState, canonical: sp.Basic) -> VerificationRecord:
    from cqse.math.expr import parse_value
    dmap = {d.option_id: d for d in item.distractors}
    missing, bad = [], []
    for o in item.options:
        if o.option_id in item.answer.correct_option_ids:
            continue
        d = dmap.get(o.option_id)
        if d is None or not d.derivation_trace or not d.misconception_id:
            missing.append(o.option_id)
            continue
        if d.value != o.value:
            bad.append(f"{o.option_id}: trace value {d.value} != option {o.value}")
            continue
        if tri_equal(parse_value(o.value), canonical) is not False:
            bad.append(f"{o.option_id}: not provably wrong")
    if bad:
        return VerificationRecord(check_id="distractors.traces", status=CheckStatus.FAILED,
                                  method="trace coverage", result="; ".join(bad))
    if missing:
        return VerificationRecord(check_id="distractors.traces", status=CheckStatus.UNRESOLVED,
                                  method="trace coverage",
                                  result=f"options {missing} have no executable misconception trace")
    return VerificationRecord(check_id="distractors.traces", status=CheckStatus.EXACT_CHECKED,
                              method="trace coverage + wrongness", result="every distractor traced and wrong")


# ------------------------------------------------------------ dimensional-analysis items
def _build_dimension_item(problem_id, formal, exam_profile_id, question_format, n_options, seed,
                          knowledge, parent_id, lineage) -> ProblemState:
    from cqse.physics import dimensions as dim
    if question_format != QuestionFormat.SINGLE_CORRECT_MCQ:
        raise AssemblyError("dimension items are single-correct MCQs")
    picked = dim.pick_options(formal, n_options, seed)
    if picked is None:
        raise AssemblyError("could not find one asked-for option plus enough unambiguous opposite options")
    exprs, verdicts = picked
    rng = random.Random(f"{problem_id}:{seed}")
    order = list(range(len(exprs)))
    rng.shuffle(order)
    letters = "ABCDEFGH"
    options, distractors, correct = [], [], []
    want = "not_meaningful" if formal.get("ask", "not_meaningful") == "not_meaningful" else "meaningful"
    for pos, idx in enumerate(order):
        oid, ex, v = letters[pos], exprs[idx], verdicts[idx]
        options.append(Option(option_id=oid, value=ex, display=ex.replace("**", "^")))
        if idx == 0:
            correct.append(oid)
            continue
        if want == "not_meaningful":   # distractor is actually consistent
            mid = "PHYS.DIM.DIFFERENT_LETTERS_CANNOT_ADD"
            why_s = "Students assume quantities with different letters can never be added or subtracted."
            why_w = "Using the given relation, the added terms have identical dimensions."
        else:                          # distractor is inconsistent
            mid = "PHYS.DIM.IGNORES_LOG_ARGUMENT_RULE"
            why_s = "Students do not use the rule that the argument of ln/exp/sin must be dimensionless."
            why_w = v.reason
        distractors.append(Distractor(option_id=oid, value=ex, misconception_id=mid, error_operation=mid,
                                      derivation_trace=v.trace, why_students_make_this_error=why_s,
                                      why_it_is_wrong=why_w, verified_wrong=True))
    return ProblemState(
        identity=Identity(problem_id=problem_id, parent_id=parent_id, lineage=lineage or []),
        subject=Subject.PHYSICS, exam_profile_id=exam_profile_id, question_format=question_format,
        knowledge=knowledge or Knowledge(chapter="Units and Measurements", topic="Dimensional analysis"),
        formal=formal, stem=dim.render_dimension_stem(formal), options=options, distractors=distractors,
        answer=Answer(correct_option_ids=correct, exact_answer=exprs[0]),
        solution_steps=verdicts[0].trace + [verdicts[0].reason],
        provenance=Provenance(rights_status="GENERATED"))


def _verify_dimension_item(item: ProblemState, rep: VerificationReport) -> VerificationReport:
    from cqse.physics import dimensions as dim
    recs, verdicts = dim.verify_dimension_item(item.formal, [(o.option_id, o.value) for o in item.options],
                                               item.answer.correct_option_ids,
                                               item.question_format == QuestionFormat.SINGLE_CORRECT_MCQ)
    rep.extend(recs)
    if item.provenance.rights_status == "GENERATED":
        same = dim.render_dimension_stem(item.formal) == item.stem
        rep.add(VerificationRecord(check_id="stem.formal_correspondence",
                                   status=CheckStatus.EXACT_CHECKED if same else CheckStatus.FAILED,
                                   method="stem re-rendered from formal state",
                                   result="identical" if same else "stem edited / does not match formal state"))
    else:
        rep.add(VerificationRecord(check_id="stem.formal_correspondence", status=CheckStatus.UNRESOLVED,
                                   method="human comparison required", result="expert must confirm stem"))
    dmap = {d.option_id: d for d in item.distractors}
    missing = [o.option_id for o in item.options if o.option_id not in item.answer.correct_option_ids
               and (o.option_id not in dmap or dmap[o.option_id].value != o.value)]
    rep.add(VerificationRecord(check_id="distractors.traces",
                               status=CheckStatus.UNRESOLVED if missing else CheckStatus.EXACT_CHECKED,
                               method="trace coverage",
                               result=f"untraced options {missing}" if missing else "every distractor traced"))
    return rep
