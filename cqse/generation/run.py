"""Generate verified questions for the pitch chapters and export them in the question bank's schema.

  python -m cqse.generation.run [--per-family N] [--chapter pnc|rot|redox] [--seed S]
  -> out/generated/<chapter>.json   (rows in the bank's own Question schema, reviewStatus PENDING_REVIEW)
     out/generated/summary.json     (per family: generated / rejected, with reasons)
"""
from __future__ import annotations

import argparse
import importlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from cqse.generation.framework import FAMILIES, generate, to_bank_row

MODULES = {"pnc": "cqse.generation.families.pnc", "rot": "cqse.generation.families.rot",
           "redox": "cqse.generation.families.redox"}
ROOT = Path(__file__).resolve().parents[2]


def _tokens(t: str) -> set[str]:
    import re
    t = re.sub(r"<[^>]+>|\\[a-zA-Z]+|[${}]", " ", t or "").lower()
    return set(re.findall(r"[a-z]+|\d+", t))


def _bank_stems() -> dict[str, list[tuple[str, set[str]]]]:
    p = ROOT / "data/pyq/ascent_all.jsonl"
    out: dict[str, list] = defaultdict(list)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            out[r["chapter"]].append((r["pyq_id"].removeprefix("ASCENT-"), _tokens(r["stem"])))
    return out


def originality(row: dict, bank: dict) -> tuple[float, str]:
    """Highest token-set (Jaccard) similarity of the generated stem to any bank stem of the same chapter."""
    toks = _tokens(row["questionContent"]["content"])
    best, who = 0.0, ""
    for qid, bt in bank.get(row["chapter"], []):
        j = len(toks & bt) / max(1, len(toks | bt))
        if j > best:
            best, who = j, qid
    return best, who


NEAR_COPY = 0.85


def to_import_row(row: dict) -> dict:
    """The ascent question-importer's canonical (snake_case) schema, read by backend ImportService."""
    return {"external_id": row["externalId"], "exam": row["exam"], "subject": row["subject"],
            "chapter": row["chapter"], "topic": row["topic"], "year": row["year"],
            "paper_title": row["paperTitle"], "difficulty": row["difficulty"], "type": row["questionType"],
            "question": row["questionContent"], "options": row["options"],
            "correct_answers": row["correctAnswers"], "answer": row["answer"],
            "explanation": row["explanation"]["content"], "media": [],
            "source": {"name": row["sourceName"], **row["sourceMetadata"]}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=5)
    ap.add_argument("--chapter", choices=list(MODULES))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    out_dir = ROOT / "out/generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for ch, mod in MODULES.items():
        if a.chapter and ch != a.chapter:
            continue
        try:
            m = importlib.import_module(mod)
        except ModuleNotFoundError:
            print(f"{ch}: no families yet")
            continue
        fams = [f for f in FAMILIES.values() if f.__class__ and f.id.split(".")[0] == ch]
        rows, per = [], {}
        bank = _bank_stems()
        for fam in fams:
            t = time.time()
            got, rej = generate(fam, a.per_family, seed=a.seed)
            for g in got:
                row = to_bank_row(g)
                sim, who = originality(row, bank)
                row["sourceMetadata"]["originality"] = {"max_similarity_to_bank": round(sim, 3), "closest": who}
                if sim >= NEAR_COPY:
                    rej.append(f"near-copy of bank question {who} (similarity {sim:.2f})")
                    continue
                rows.append(row)
            per[fam.id] = {"generated": sum(1 for r in rows if r["sourceMetadata"]["family"] == fam.id), "rejected": len(rej), "status": dict(Counter(g.status for g in got)),
                           "seconds": round(time.time() - t, 1), "reject_reasons": rej[:5]}
            print(f"{fam.id:<36} {len(got):>3} generated, {len(rej):>3} rejected  ({per[fam.id]['seconds']} s)")
        (out_dir / f"{ch}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        summary[ch] = {"questions": len(rows), "families": per}
        print(f"== {ch}: {len(rows)} questions -> out/generated/{ch}.json\n")
    every = []
    for ch in MODULES:
        f = out_dir / f"{ch}.json"
        if f.exists():
            every += [to_import_row(r) for r in json.loads(f.read_text())]
    (out_dir / "import_ready.json").write_text(json.dumps(every, indent=1, ensure_ascii=False))
    print(f"{len(every)} questions in out/generated/import_ready.json (backend importer format)")
    prev = json.loads((out_dir / "summary.json").read_text()) if (out_dir / "summary.json").exists() else {}
    prev.update(summary)
    (out_dir / "summary.json").write_text(json.dumps(prev, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
