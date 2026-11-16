"""Zero-cost structural checks over an imported question bank (no AI, no engines).

Run:  python data/pyq/free_checks.py data/pyq/ascent_all.jsonl   -> out/free_checks.json + printed summary

Checks (each is a FLAG for review, not a verdict):
  missing_key            MCQ with no key; numerical with no stored answer (expected for this export)
  bad_key                key not among option ids
  option_count           MCQ with fewer than 4 options, or an empty option
  duplicate_options      two options with identical normalised text
  duplicate_question     identical normalised stem+options elsewhere in the bank
  latex_unbalanced       odd number of $ delimiters or unbalanced braces in the stem/options
  explanation_disagrees  the explanation explicitly names an option different from the key (heuristic)
  bonus                  source marks the question as bonus/dropped
  image_dependent        question or options contain an image
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NUM2LET = {"1": "A", "2": "B", "3": "C", "4": "D"}


def norm(t: str) -> str:
    t = re.sub(r"\\(mathrm|text|mathbf|rm)\s*", "", t or "")
    t = re.sub(r"[\s$~{}]|\\,|\\;|\\!|\\quad", "", t)
    return t.lower()


def latex_ok(t: str) -> bool:
    t = (t or "").replace("\\$", "")
    if t.count("$") % 2:
        return False
    depth = 0
    for ch in re.sub(r"\\[{}]", "", t):
        depth += ch == "{"
        depth -= ch == "}"
        if depth < 0:
            return False
    return depth == 0


_EXPL = [
    r"correct (?:answer|option|choice)\s*(?:is|:)?\s*(?:option)?\s*\(?\s*([A-D1-4])\s*\)?(?![a-z0-9])",
    r"(?:hence|so|therefore|thus|answer\s*:?)[^.\n]{0,40}?\boption\s*\(?\s*([A-D1-4])\s*\)?(?![a-z0-9])",
    r"^\s*option\s*\(?\s*([A-D1-4])\s*\)?\s*(?:is correct)?\s*\.?\s*$",
]


def explanation_option(expl: str) -> str | None:
    t = re.sub(r"<[^>]+>", " ", expl or "")
    t = re.sub(r"\$+[^$]*\$+", " ", t)          # ignore maths
    found = []
    for line in t.splitlines()[-8:]:             # conclusions live at the end
        for pat in _EXPL:
            for m in re.finditer(pat, line.strip(), re.I | re.M):
                found.append(NUM2LET.get(m.group(1), m.group(1).upper()))
    return found[-1] if found else None


def main(path: str) -> None:
    recs = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    flags: dict[str, list[str]] = defaultdict(list)
    seen: dict[str, str] = {}
    for r in recs:
        qid = r["pyq_id"].removeprefix("ASCENT-")
        mcq = r["question_format"].endswith("mcq")
        key = r["answer_key"]
        keys = key if isinstance(key, list) else ([key] if key else [])
        ids = [o["id"] for o in r["options"]]
        if not keys:
            flags["missing_key"].append(qid)
        elif mcq and any(k not in ids for k in keys):
            flags["bad_key"].append(qid)
        if mcq and (len(ids) < 4 or any(not (o["text"] or "").strip() for o in r["options"])):
            flags["option_count"].append(qid)
        texts = [re.sub(r"\s+|\\,|\\;|\\!", "", o["text"]) for o in r["options"]
                 if (o["text"] or "").strip() and "[IMAGE]" not in o["text"]]  # exact up to spacing
        if len(texts) != len(set(texts)):
            flags["duplicate_options"].append(qid)
        sig = norm(r["stem"]) + "|" + "|".join(sorted(norm(o["text"]) for o in r["options"]))
        if "[IMAGE]" not in r["stem"] and len(sig) > 40:
            if sig in seen:
                flags["duplicate_question"].append(f"{qid}~{seen[sig]}")
            else:
                seen[sig] = qid
        if not latex_ok(r["stem"]) or any(not latex_ok(o["text"]) for o in r["options"]):
            flags["latex_unbalanced"].append(qid)
        negative = re.search(r"\b(not|incorrect|false|wrong|except)\b", re.sub(r"\$+[^$]*\$+", " ", r["stem"]), re.I)
        if mcq and len(keys) == 1 and not negative:
            e = explanation_option(r.get("solution") or "")
            if e and e != keys[0]:
                flags["explanation_disagrees"].append(f"{qid}:key={keys[0]},expl={e}")
        if (r.get("extraction") or {}).get("unresolved_fragments"):
            flags["image_dependent"].append(qid)
    bonus_src = ROOT / "ascent-feat-jee-que-bank/all_questions.json"
    if bonus_src.exists():
        flags["bonus"] = [x["external_id"] for x in json.loads(bonus_src.read_text()) if
                          (x.get("source") or {}).get("is_bonus")]
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/free_checks.json").write_text(json.dumps(flags, indent=1))
    print(f"{len(recs)} questions")
    for k, v in sorted(flags.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:<24} {len(v):>6}   e.g. {v[:3]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/pyq/ascent_all.jsonl")
