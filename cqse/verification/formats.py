"""Option-format engine for JEE "combination" question styles.

Given the truth of each labelled statement (or each List-I -> List-II pairing, or an ordering), it derives
WHICH OPTION is correct, as an integer/set code. Option texts are parsed into the same code, so the
ordinary option/key gate (verification/options.py) can then check the database key.

formal = {
  "kind": "statement_set",
  "format": "select_combination" | "statement_pair" | "assertion_reason" | "match_list" | "ordering",
  "statements": {label: TRUTH},                 # select_combination / statement_pair (labels "I","II") /
                                                #   assertion_reason (labels "A","R", plus "explains": TRUTH)
  "pairs": {left_label: [right_label, TRUTH]},  # match_list
  "order": {"items": [...], "values": {item: VALUE_OR_FORMAL}, "direction": "increasing"|"decreasing",
            "basis": ...}                       # ordering
}
TRUTH = {"truth": bool, "basis": "curated", "note": "..."}                    -> teacher must confirm
      | {"formal": {...}, "claim": "== 6", "subject": "CHEMISTRY"}           -> computed by an engine

Codes:
  select_combination  FiniteSet of statement indices (A/I/1 -> 1, B/II/2 -> 2, ...)
  statement_pair      10*t(I) + t(II)  -> 11, 10, 1, 0
  assertion_reason    3 both true & R explains A, 2 both true & R does not explain, 1 A true R false,
                      4 A false R true, 0 both false
  match_list          digits of the List-II index for List-I labels in order, e.g. A-III,B-I,C-IV,D-II -> 3142
  ordering            digits of item positions (1-based, in the order listed in "items")
"""
from __future__ import annotations

import re
from typing import Any, Optional

import sympy as sp

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.core.result import EngineResult

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
TOOL = "cqse.formats 1.0"


def label_index(label: str) -> int:
    t = label.strip().strip("()").upper()
    if t in ROMAN:
        return ROMAN[t]
    if t.isdigit():
        return int(t)
    if len(t) == 1 and "A" <= t <= "Z":
        return ord(t) - ord("A") + 1
    raise ValueError(f"unknown label {label!r}")


# ------------------------------------------------------------------ truth evaluation
def _truth(name: str, spec: dict, default_subject) -> tuple[Optional[bool], VerificationRecord]:
    if "formal" in spec:
        from cqse.core.problem import Subject
        from cqse.verification.pipeline import canonical_answer, software_blocking
        subj = Subject(spec.get("subject", default_subject.value if default_subject else "MATHEMATICS"))
        can = canonical_answer(subj, spec["formal"])
        if can.value is None or software_blocking(can.records):
            return None, VerificationRecord(check_id="statement.truth", status=CheckStatus.FAILED
                                            if software_blocking(can.records) else CheckStatus.UNRESOLVED,
                                            method="engine", result=f"{name}: engine could not establish value",
                                            data={"label": name})
        op, rhs = _parse_claim(spec["claim"])
        lhs = can.value
        val = sp.sympify(rhs) if not isinstance(rhs, sp.Basic) else rhs
        if op == "in":
            ok = bool(lhs in val)
        else:
            d = sp.nsimplify(lhs - val) if op in ("==", "!=") else None
            ok = {"==": lambda: d == 0, "!=": lambda: d != 0, "<": lambda: bool(lhs < val),
                  ">": lambda: bool(lhs > val), "<=": lambda: bool(lhs <= val), ">=": lambda: bool(lhs >= val)}[op]()
        weakest = min((r.status for r in can.records if r.hard), key=_rank, default=CheckStatus.EXACT_CHECKED)
        status = weakest if weakest in (CheckStatus.PROVED, CheckStatus.EXACT_CHECKED,
                                        CheckStatus.RULE_CHECKED) else CheckStatus.RULE_CHECKED
        pending = [r.model_copy(update={"result": f"{name}: {r.result}"}) for r in can.records
                   if r.hard and not r.is_affirmative()]  # expert-resolvable items still owed by the sub-model
        return ok, VerificationRecord(check_id="statement.truth", status=status, method="engine",
                                      result=f"{name}: value {lhs} {op} {rhs} is {ok}",
                                      data={"label": name, "pending": [p.model_dump(mode="json") for p in pending]})
    if "truth" in spec:
        return bool(spec["truth"]), VerificationRecord(
            check_id="statement.truth", status=CheckStatus.UNRESOLVED, method="curated",
            result=f"{name}: curated as {bool(spec['truth'])} - teacher must confirm",
            assumptions=[spec.get("note", "")], data={"label": name, "curated": bool(spec["truth"])})
    return None, VerificationRecord(check_id="statement.truth", status=CheckStatus.UNRESOLVED, method="none",
                                    result=f"{name}: no truth source", data={"label": name})


_ORDER = [CheckStatus.PROVED, CheckStatus.EXACT_CHECKED, CheckStatus.RULE_CHECKED]


def _rank(s: CheckStatus) -> int:
    return _ORDER.index(s) if s in _ORDER else -1


def _parse_claim(c: str) -> tuple[str, Any]:
    m = re.match(r"\s*(==|!=|<=|>=|<|>|in)\s*(.+)$", str(c))
    if not m:
        raise ValueError(f"bad claim {c!r}")
    op, rhs = m.groups()
    if op == "in":
        return op, sp.FiniteSet(*[sp.sympify(x) for x in rhs.strip("{} ").split(",")])
    return op, rhs


# ------------------------------------------------------------------ main
def solve_and_verify(formal: dict, subject=None) -> EngineResult:
    fmt = formal.get("format")
    out = EngineResult()
    truths: dict[str, Optional[bool]] = {}

    if fmt in ("select_combination", "statement_pair", "assertion_reason"):
        specs = dict(formal.get("statements", {}))
        if fmt == "assertion_reason" and "explains" in formal:
            specs["explains"] = formal["explains"]
        for lab, spec in specs.items():
            t, rec = _truth(lab, spec, subject)
            truths[lab] = t
            _add(out, rec)
        if any(v is None for v in truths.values()):
            return out
        if fmt == "select_combination":
            out.value = sp.FiniteSet(*sorted(label_index(k) for k, v in truths.items() if v))
            if out.value == sp.S.EmptySet:
                out.value = sp.S.EmptySet
        elif fmt == "statement_pair":
            t1, t2 = truths[_find(truths, "I")], truths[_find(truths, "II")]
            out.value = sp.Integer(10 * int(t1) + int(t2))
        else:
            a, r = truths["A"], truths["R"]
            if a and r:
                ex = truths.get("explains")
                if ex is None:
                    out.records.append(VerificationRecord(check_id="statement.truth", status=CheckStatus.UNRESOLVED,
                                                          method="none", result="explains: not given"))
                    return out
                out.value = sp.Integer(3 if ex else 2)
            else:
                out.value = sp.Integer({(True, False): 1, (False, True): 4, (False, False): 0}[(bool(a), bool(r))])
        out.steps = [f"{k}: {'true' if v else 'false'}" for k, v in truths.items()] + [f"code = {out.value}"]

    elif fmt == "match_list":
        digits = []
        for left in sorted(formal["pairs"], key=label_index):
            right, spec = formal["pairs"][left]
            t, rec = _truth(f"{left}-{right}", spec, subject)
            _add(out, rec)
            if t is not True:
                if t is False:
                    out.records.append(VerificationRecord(check_id="statement.truth", status=CheckStatus.FAILED,
                                                          method="match_list", result=f"pairing {left}-{right} is false"))
                return out
            digits.append(str(label_index(right)))
        rights = [label_index(formal["pairs"][k][0]) for k in formal["pairs"]]
        if len(set(rights)) != len(rights):
            out.records.append(VerificationRecord(check_id="match.bijection", status=CheckStatus.UNRESOLVED,
                                                  method="match_list", result="List-II used more than once"))
        out.value = sp.Integer(int("".join(digits)))
        out.steps = [f"{k}-{formal['pairs'][k][0]}" for k in sorted(formal["pairs"], key=label_index)]

    elif fmt == "ordering":
        o = formal["order"]
        vals = {}
        for item, v in o["values"].items():
            if isinstance(v, dict):
                from cqse.core.problem import Subject
                from cqse.verification.pipeline import canonical_answer, software_blocking
                can = canonical_answer(Subject(v.get("subject", "CHEMISTRY")), v["formal"])
                if can.value is None or software_blocking(can.records):
                    out.records.append(VerificationRecord(check_id="statement.truth", status=CheckStatus.UNRESOLVED,
                                                          method="engine", result=f"{item}: no value"))
                    return out
                vals[item] = can.value
                out.records += [r.model_copy(update={"result": f"{item}: {r.result}"}) for r in can.records
                                if r.hard and not r.is_affirmative()]  # teacher checks owed by the sub-model
            else:
                vals[item] = sp.nsimplify(v)
        basis = o.get("basis", "curated")
        out.records.append(VerificationRecord(
            check_id="statement.truth",
            status=CheckStatus.RULE_CHECKED if basis.startswith("rule") else CheckStatus.UNRESOLVED,
            method=basis, result=f"ordering values {dict((k, str(v)) for k, v in vals.items())}",
            assumptions=[o.get("note", "")]))
        seq = sorted(o["items"], key=lambda k: vals[k], reverse=o.get("direction") == "decreasing")
        if len({vals[k] for k in seq}) != len(seq):
            out.records.append(VerificationRecord(check_id="ordering.strict", status=CheckStatus.FAILED,
                                                  method="ordering", result="tie: order not strict"))
            return out
        out.value = sp.Integer(int("".join(str(o["items"].index(k) + 1) for k in seq)))
        out.steps = [" < ".join(seq) if o.get("direction") != "decreasing" else " > ".join(seq)]
    else:
        out.records.append(VerificationRecord(check_id="format.known", status=CheckStatus.FAILED,
                                              method="statement_set", result=f"unknown format {fmt!r}"))
        return out

    out.records.append(VerificationRecord(check_id="format.derive", status=CheckStatus.EXACT_CHECKED,
                                          method="deterministic option-code derivation", tool=TOOL,
                                          result=f"{fmt} -> {out.value}"))
    return out


def _add(out: EngineResult, rec: VerificationRecord) -> None:
    out.records.append(rec)
    for p in rec.data.get("pending", []):
        out.records.append(VerificationRecord(**p))


def _find(truths: dict, roman: str) -> str:
    for k in truths:
        if k.strip().upper() in (roman, f"STATEMENT {roman}", str(ROMAN[roman])):
            return k
    raise KeyError(roman)


# ------------------------------------------------------------------ option text -> code
def _clean(t: str) -> str:
    t = re.sub(r"\$|\\mathbf\{|\\mathrm\{|\\textbf\{|[{}]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def option_code(fmt: str, text: str) -> Optional[str]:
    """Parse an option's display text into the code for `fmt`. Returns None when it cannot be parsed."""
    t = _clean(text)
    low = t.lower()
    if fmt == "select_combination":
        labs = re.findall(r"\(?\b([A-H])\b\)?", t.replace("Only", "").replace("only", ""))
        if not labs:
            return None
        return "{" + ", ".join(str(label_index(x)) for x in sorted(set(labs), key=label_index)) + "}"
    if fmt == "statement_pair":
        tv = r"(true|correct)"
        fv = r"(false|incorrect)"
        if re.search(rf"both .*{fv}", low):
            return "0"
        if re.search(rf"both .*{tv}", low):
            return "11"
        m = re.search(rf"statement (i|1)\b.*?\b(is|are)\s+{tv}.*statement (ii|2)\b.*?\b(is|are)\s+{fv}", low)
        if m:
            return "10"
        m = re.search(rf"statement (i|1)\b.*?\b(is|are)\s+{fv}.*statement (ii|2)\b.*?\b(is|are)\s+{tv}", low)
        if m:
            return "1"
        return None
    if fmt == "assertion_reason":
        if "both" in low and ("true" in low or "correct" in low):
            return "2" if "not" in low else "3"
        if re.search(r"\ba\b.*(true|correct).*\br\b.*(false|incorrect)", low):
            return "1"
        if re.search(r"\ba\b.*(false|incorrect).*\br\b.*(true|correct)", low):
            return "4"
        if "both" in low and ("false" in low or "incorrect" in low):
            return "0"
        return None
    if fmt == "match_list":
        pairs = re.findall(r"\(?([A-D])\)?\s*[-–→]\s*\(?\s*(IV|V|I{1,3})\s*\)?", t)
        if not pairs:
            return None
        d = {label_index(a): ROMAN[b] for a, b in pairs}
        if sorted(d) != list(range(1, len(d) + 1)):
            return None
        return "".join(str(d[i]) for i in sorted(d))
    return None
