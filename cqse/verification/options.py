"""Option / answer-key / cardinality gate (blueprint sections 14, 36).

Every option is evaluated individually against the canonical answer derived
from the formal state. Undecidable comparisons are UNRESOLVED (blocking).
"""
from __future__ import annotations

from typing import Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.core.problem import ProblemState, QuestionFormat
from cqse.math.expr import is_exact_integer, parse_value, tri_equal

TOOL = f"sympy {sp.__version__}"


def check_options_and_key(item: ProblemState, canonical: sp.Basic,
                          rounding: Optional[str] = None) -> list[VerificationRecord]:
    """rounding: exam rule for numerical answers, e.g. "nearest_integer" (JEE Main)."""
    recs: list[VerificationRecord] = []
    fmt = item.question_format

    if canonical is None or canonical == sp.nan or (isinstance(canonical, sp.Expr) and canonical.has(sp.nan)):
        return [VerificationRecord(check_id="key.canonical", status=CheckStatus.UNRESOLVED,
                                   method="canonical answer", result="no verified canonical answer")]

    if fmt in (QuestionFormat.NUMERICAL_INTEGER, QuestionFormat.NUMERICAL_DECIMAL):
        return _numerical(item, canonical, rounding)
    if item.formal.get("options_rounded"):
        return _rounded_options(item, canonical)

    # ---- parse every option
    parsed: dict[str, sp.Basic] = {}
    for o in item.options:
        try:
            parsed[o.option_id] = parse_value(o.value)
        except Exception as e:  # noqa: BLE001
            recs.append(VerificationRecord(check_id="options.parse", status=CheckStatus.FAILED,
                                           method="whitelist parse", result=f"{o.option_id}: {e}"))
            return recs
    recs.append(VerificationRecord(check_id="options.parse", status=CheckStatus.EXACT_CHECKED,
                                   method="whitelist parse", tool=TOOL, result=f"{len(parsed)} options parsed"))

    # ---- pairwise distinctness (catches 1/2 vs 0.5 vs 2/4)
    ids = list(parsed)
    dup, undecided = [], []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            r = tri_equal(parsed[ids[i]], parsed[ids[j]])
            if r is True:
                dup.append((ids[i], ids[j]))
            elif r is None:
                undecided.append((ids[i], ids[j]))
    if dup:
        recs.append(VerificationRecord(check_id="options.distinct", status=CheckStatus.FAILED,
                                       method="pairwise exact equivalence", tool=TOOL,
                                       result=f"equivalent options {dup}"))
    elif undecided:
        recs.append(VerificationRecord(check_id="options.distinct", status=CheckStatus.UNRESOLVED,
                                       method="pairwise exact equivalence", result=f"undecidable {undecided}"))
    else:
        recs.append(VerificationRecord(check_id="options.distinct", status=CheckStatus.EXACT_CHECKED,
                                       method="pairwise exact equivalence", tool=TOOL, result="all distinct"))

    # ---- which options are correct?
    correct, unk = [], []
    for oid, v in parsed.items():
        r = _option_correct(fmt, v, canonical)
        if r is True:
            correct.append(oid)
        elif r is None:
            unk.append(oid)
    if unk:
        recs.append(VerificationRecord(check_id="options.correctness", status=CheckStatus.UNRESOLVED,
                                       method="per-option evaluation", result=f"undecidable options {unk}"))
        return recs

    declared = sorted(item.answer.correct_option_ids)
    computed = sorted(correct)
    if fmt == QuestionFormat.SINGLE_CORRECT_MCQ and len(computed) != 1:
        recs.append(VerificationRecord(check_id="options.cardinality", status=CheckStatus.FAILED,
                                       method="per-option evaluation", tool=TOOL,
                                       result=f"single-correct item has {len(computed)} correct options {computed}"))
    elif fmt == QuestionFormat.MULTIPLE_CORRECT_MCQ and not computed:
        recs.append(VerificationRecord(check_id="options.cardinality", status=CheckStatus.FAILED,
                                       method="per-option evaluation", result="no correct option"))
    else:
        recs.append(VerificationRecord(check_id="options.cardinality", status=CheckStatus.EXACT_CHECKED,
                                       method="per-option evaluation", tool=TOOL,
                                       result=f"correct options {computed}", data={"correct": computed}))

    if declared != computed:
        recs.append(VerificationRecord(check_id="key.matches_derivation", status=CheckStatus.FAILED,
                                       method="declared key vs derived key", tool=TOOL,
                                       result=f"declared {declared} but derivation gives {computed}"))
    else:
        recs.append(VerificationRecord(check_id="key.matches_derivation", status=CheckStatus.EXACT_CHECKED,
                                       method="declared key vs derived key", tool=TOOL, result=f"key {declared}"))
    return recs


def _option_correct(fmt: QuestionFormat, v: sp.Basic, canonical: sp.Basic) -> Optional[bool]:
    if fmt == QuestionFormat.MULTIPLE_CORRECT_MCQ and isinstance(canonical, (sp.FiniteSet,)) \
            and not isinstance(v, sp.Set):
        # option is correct iff it equals some member of the canonical set
        undecided = False
        for m in canonical:
            r = tri_equal(v, m)
            if r is True:
                return True
            if r is None:
                undecided = True
        return None if undecided else False
    if fmt == QuestionFormat.MULTIPLE_CORRECT_MCQ and canonical == sp.S.EmptySet and not isinstance(v, sp.Set):
        return False
    return tri_equal(v, canonical)


def _rounded_options(item: ProblemState, canonical: sp.Basic) -> list[VerificationRecord]:
    """Printed options are rounded (e.g. -0.38 for -0.3778). An option is correct iff it lies
    within rel_tol of the exact answer; every other option must be clearly further away
    (>= 3 x rel_tol), otherwise the item is ambiguous and FAILS."""
    recs: list[VerificationRecord] = []
    tol = float(sp.nsimplify(item.formal["options_rounded"].get("rel_tol", "0.01")))
    exact = complex(sp.N(canonical, 30))
    if abs(exact.imag) > 1e-30:
        return [VerificationRecord(check_id="options.rounded", status=CheckStatus.FAILED, method="numeric",
                                   result="rounded-option comparison needs a real answer")]
    exact = exact.real
    scale = max(abs(exact), 1e-300)
    dist = {}
    for o in item.options:
        try:
            v = complex(sp.N(parse_value(o.value), 30)).real
        except Exception as e:  # noqa: BLE001
            return [VerificationRecord(check_id="options.parse", status=CheckStatus.FAILED,
                                       method="whitelist parse", result=f"{o.option_id}: {e}")]
        dist[o.option_id] = abs(v - exact) / scale
    close = sorted(o for o, d in dist.items() if d <= tol)
    far_enough = all(d >= 3 * tol for o, d in dist.items() if o not in close)
    detail = ", ".join(f"{o}: {d:.2%}" for o, d in sorted(dist.items()))
    if len(close) != 1 or not far_enough:
        recs.append(VerificationRecord(
            check_id="options.cardinality", status=CheckStatus.FAILED, method="rounded-option match",
            tool=TOOL, result=f"exact {exact:.6g}; relative distances {detail}; options within {tol:.0%}: "
                              f"{close} - not a unique, clear match"))
    else:
        recs.append(VerificationRecord(
            check_id="options.cardinality", status=CheckStatus.EXACT_CHECKED, method="rounded-option match",
            tool=TOOL, result=f"exact {exact:.6g}; option {close[0]} within {tol:.0%}; others >= {3 * tol:.0%} "
                              f"away ({detail})", data={"correct": close}))
    declared = sorted(item.answer.correct_option_ids)
    ok = declared == close
    recs.append(VerificationRecord(check_id="key.matches_derivation",
                                   status=CheckStatus.EXACT_CHECKED if ok else CheckStatus.FAILED,
                                   method="declared key vs derived key", tool=TOOL,
                                   result=f"declared {declared}; derived {close}"))
    return recs


def _numerical(item: ProblemState, canonical: sp.Basic, rounding: Optional[str] = None
               ) -> list[VerificationRecord]:
    recs: list[VerificationRecord] = []
    if item.question_format == QuestionFormat.NUMERICAL_INTEGER and rounding == "nearest_integer" \
            and isinstance(canonical, sp.Expr) and is_exact_integer(canonical) is not True:
        v = complex(sp.N(canonical, 40))
        if abs(v.imag) > 1e-30:
            return [VerificationRecord(check_id="numerical.rounding", status=CheckStatus.FAILED,
                                       method="nearest integer", result="answer is not real")]
        frac = v.real - sp.floor(v.real)
        if abs(float(frac) - 0.5) < 0.05:
            return [VerificationRecord(check_id="numerical.rounding", status=CheckStatus.FAILED,
                                       method="nearest integer", tool=TOOL,
                                       result=f"exact value {v.real:.6g} is within 0.05 of a .5 boundary: "
                                              "rounding is ambiguous")]
        rounded = sp.Integer(round(v.real))
        recs.append(VerificationRecord(check_id="numerical.rounding", status=CheckStatus.EXACT_CHECKED,
                                       method="exam rule: nearest integer", tool=TOOL,
                                       result=f"exact {v.real:.6g} -> {rounded}"))
        canonical = rounded
    if item.question_format == QuestionFormat.NUMERICAL_INTEGER:
        isint = is_exact_integer(canonical) if isinstance(canonical, sp.Expr) else False
        if isint is not True:
            st = CheckStatus.FAILED if isint is False else CheckStatus.UNRESOLVED
            recs.append(VerificationRecord(
                check_id="numerical.integer", status=st, method="exact integer test", tool=TOOL,
                result=f"canonical answer {canonical} is not an exact integer; rounding rules would be "
                       f"needed - generation requires an exact integer to avoid key ambiguity"))
            return recs
        recs.append(VerificationRecord(check_id="numerical.integer", status=CheckStatus.EXACT_CHECKED,
                                       method="exact integer test", tool=TOOL, result=f"answer {canonical}"))
    declared = item.answer.exact_answer
    if declared is None:
        recs.append(VerificationRecord(check_id="key.matches_derivation", status=CheckStatus.FAILED,
                                       method="declared key vs derived key", result="no declared answer"))
        return recs
    try:
        r = tri_equal(parse_value(declared), canonical)
    except Exception as e:  # noqa: BLE001
        r, declared = False, f"{declared} (unparseable: {e})"
    st = {True: CheckStatus.EXACT_CHECKED, False: CheckStatus.FAILED, None: CheckStatus.UNRESOLVED}[r]
    recs.append(VerificationRecord(check_id="key.matches_derivation", status=st,
                                   method="declared key vs derived key", tool=TOOL,
                                   result=f"declared {declared}; derived {canonical}"))
    return recs
