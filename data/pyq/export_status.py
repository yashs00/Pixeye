"""Build a per-question verification status file for the ascent question bank (nothing is written to the DB).

Inputs (whatever exists):  out/free_checks.json, out/ascent300_report.json, data/pyq/ascent_all.jsonl
Output:  out/review_status.json  and  out/review_status.csv, one row per question:
  sourceName, externalId, cqse_status, suggested_reviewStatus, reasons, derived_answer, explanation_value

cqse_status
  VERIFIED          key agrees with an answer computed by two independent methods / a versioned rule set
  NEEDS_TEACHER     key agrees, but a curated fact or the stem->equations write-up awaits a teacher
  KEY_DISPUTED      the engine finds a different answer, or no option is correct
  FLAGGED           structural problem (duplicate options, bonus question, broken LaTeX, missing key...)
  UNCHECKED         not yet formalized
suggested_reviewStatus maps onto the backend enum, conservatively: only VERIFIED -> "VERIFIED";
everything else stays "PENDING_REVIEW" (a teacher decides REJECTED / UNPUBLISHED).

Run:  python data/pyq/export_status.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys_path = str(ROOT)
import sys  # noqa: E402

sys.path.insert(0, sys_path)
from cqse.ingest.explanation import final_value  # noqa: E402

FLAG_TEXT = {
    "duplicate_options": "two options are identical",
    "bonus": "source marks this question as bonus/dropped",
    "latex_unbalanced": "LaTeX delimiters/braces unbalanced",
    "bad_key": "key is not one of the option ids",
    "option_count": "fewer than 4 options or an empty option",
    "explanation_disagrees": "explanation names a different option than the key (likely option re-ordering)",
    "duplicate_question": "duplicate of another question",
}


def main() -> None:
    recs = [json.loads(l) for l in (ROOT / "data/pyq/ascent_all.jsonl").read_text(encoding="utf-8").splitlines()]
    flags = json.loads((ROOT / "out/free_checks.json").read_text()) if (ROOT / "out/free_checks.json").exists() else {}
    engine = {}
    rp = ROOT / "out/ascent300_report.json"
    if rp.exists():
        engine = {r["id"]: r for r in json.loads(rp.read_text())}

    by_id: dict[str, list[str]] = {}
    for k, items in flags.items():
        if k in ("missing_key", "image_dependent"):
            continue
        for it in items:
            for qid in it.split(":")[0].split("~"):
                by_id.setdefault(qid, []).append(FLAG_TEXT.get(k, k) + (f" ({it})" if ":" in it or "~" in it else ""))
    missing_mcq = {q for q in flags.get("missing_key", [])}

    rows = []
    for r in recs:
        qid = r["pyq_id"].removeprefix("ASCENT-")
        reasons = list(by_id.get(qid, []))
        mcq = r["question_format"].endswith("mcq")
        if mcq and qid in missing_mcq:
            reasons.append("MCQ has no answer key")
        ev, conf = (None, None) if mcq else final_value(r.get("solution"))
        e = engine.get(qid)
        derived = e["derived"] if e else None
        if e and e["verdict"].startswith(("KEY DISAGREES", "NO OPTION CORRECT")) or (e and "MISMATCH" in e["verdict"]):
            status = "KEY_DISPUTED"
            reasons.insert(0, e["verdict"].lower())
        elif e and "AMBIGUOUS" in e["verdict"]:
            status = "KEY_DISPUTED"
            reasons.insert(0, "answer is exactly x.5 and the question gives no rounding rule")
        elif reasons:
            status = "FLAGGED"
        elif e and e["verdict"] == "VERIFIED":
            status = "VERIFIED"
        elif e and e["verdict"].startswith("VERIFIED"):
            status = "NEEDS_TEACHER"
            reasons.append("key agrees with the engine; a curated fact or the write-up needs a teacher's sign-off")
        else:
            status = "UNCHECKED"
        rows.append({"sourceName": r["source"]["document"].split(" / ")[0], "externalId": qid, "cqse_status": status,
                     "suggested_reviewStatus": "VERIFIED" if status == "VERIFIED" else "PENDING_REVIEW",
                     "reasons": reasons, "derived_answer": derived,
                     "explanation_value": ev, "explanation_value_confidence": conf})
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/review_status.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    with open(ROOT / "out/review_status.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({**row, "reasons": " | ".join(row["reasons"])})
    from collections import Counter
    print(len(rows), "questions:", dict(Counter(x["cqse_status"] for x in rows)))
    print("numerical reference values from explanations:",
          dict(Counter(x["explanation_value_confidence"] for x in rows if x["explanation_value_confidence"] or
                       x["explanation_value"] is None and x["externalId"] in missing_mcq)))


if __name__ == "__main__":
    main()
