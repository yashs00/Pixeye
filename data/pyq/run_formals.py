"""Attach hand/engine formalizations to the 300-question ascent set and verify every one.

Formalizations live in data/pyq/formals/*.py, each defining
    FORMALS = {externalId: {"formal": {...},
                            "option_values": {"A": "...", ...},   # optional; auto-derived for statement_set
                            "explanation_value": "6",             # numericals: value stated in the explanation
                            "note": "..."}}

Run:  python data/pyq/run_formals.py [--only <formals file stem>]            (writes out/ascent300_report.json and *_formalized.jsonl)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import sympy as sp  # noqa: E402

from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record  # noqa: E402
from cqse.verification.formats import option_code  # noqa: E402

FILES = {"CHEMISTRY": "ascent_chem.jsonl", "MATHEMATICS": "ascent_maths.jsonl", "PHYSICS": "ascent_phy.jsonl"}


def load_formals(only: str | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted((ROOT / "data/pyq/formals").glob("*.py")):
        if f.name.startswith("_") or (only and f.stem != only):
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:  # noqa: BLE001 - one broken file must not hide the others
            print(f"!! {f.name} failed to load: {type(e).__name__}: {e}")
            continue
        for k, v in getattr(mod, "FORMALS", {}).items():
            if k in out:
                raise SystemExit(f"{k} formalized twice ({f.name})")
            out[k] = {**v, "_file": f.name}
    return out


def attach(rec: dict, entry: dict) -> tuple[dict, list[str]]:
    rec = dict(rec)
    notes = []
    rec["formal"] = entry["formal"]
    ov = entry.get("option_values")
    if ov is None and entry["formal"].get("kind") == "statement_set" and rec["options"]:
        ov = {}
        for o in rec["options"]:
            c = option_code(entry["formal"]["format"], o["text"])
            if c is None:
                notes.append(f"option {o['id']} text not parsed: {o['text'][:60]!r}")
            ov[o["id"]] = c
    if ov:
        rec["options"] = [{**o, "value": ov.get(o["id"])} for o in rec["options"]]
    return rec, notes


def _num_check(derived: str | None, expl: str | None) -> str:
    if derived is None or expl is None:
        return ""
    try:
        v = float(sp.N(sp.sympify(derived), 15))
    except Exception:  # noqa: BLE001
        return ""
    r = round(v)
    if abs(v - r) > 1e-9 and abs(abs(v - int(v)) - 0.5) < 0.05:
        return f"explanation {expl}: AMBIGUOUS ROUNDING ({v:.6g})"
    return f"explanation {expl}: {'MATCH' if str(r) == str(expl) else f'MISMATCH (engine {r})'}"


def main() -> None:
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    formals = load_formals(only)
    report, per_subject = [], defaultdict(Counter)
    for subj, fn in FILES.items():
        path = ROOT / "data/pyq" / fn
        out_lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            ext = rec["pyq_id"].removeprefix("ASCENT-")
            entry = formals.get(ext)
            if entry is None:
                per_subject[subj]["not formalized"] += 1
                out_lines.append(line)
                continue
            rec2, notes = attach(rec, entry)
            try:
                r = ingest_record(PYQRecord(**rec2))
            except Exception as e:  # noqa: BLE001
                per_subject[subj]["CRASH"] += 1
                report.append({"id": ext, "subject": subj, "chapter": rec["chapter"], "verdict": "CRASH",
                               "derived": None, "key": rec["answer_key"], "statuses": [], "numerical": "",
                               "notes": [f"{type(e).__name__}: {e}"], "file": entry["_file"], "note": ""})
                out_lines.append(line)
                continue
            sts = [s.value for s in r.statuses]
            if IngestStatus.QUARANTINED_KEY_DISAGREEMENT in r.statuses:
                no_match = rec["options"] and not any(str(n).startswith("derived option(s)") for n in r.notes)
                verdict = "NO OPTION CORRECT" if no_match else "KEY DISAGREES"
            elif IngestStatus.PARENT_VERIFIED in r.statuses:
                verdict = "VERIFIED" if IngestStatus.NEEDS_EXPERT_REVIEW not in r.statuses else "VERIFIED (teacher confirm)"
            elif IngestStatus.QUARANTINED_UNVERIFIABLE in r.statuses:
                verdict = "UNVERIFIABLE"
            else:
                verdict = "INCOMPLETE"
            num = _num_check(r.derived_answer, entry.get("explanation_value")) if not rec["options"] else ""
            if "MISMATCH" in num or "AMBIGUOUS" in num:
                verdict += " / " + num.split(": ")[1]
            per_subject[subj][verdict.split(" /")[0]] += 1
            report.append({"id": ext, "subject": subj, "chapter": rec["chapter"], "verdict": verdict,
                           "derived": r.derived_answer, "key": rec["answer_key"], "statuses": sts,
                           "numerical": num, "notes": notes + r.notes, "file": entry["_file"],
                           "note": entry.get("note", "")})
            out_lines.append(json.dumps(rec2, ensure_ascii=False))
        if only:
            continue
        (ROOT / "data/pyq" / fn.replace(".jsonl", "_formalized.jsonl")).write_text("\n".join(out_lines) + "\n",
                                                                                   encoding="utf-8")
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / ("out/ascent300_report.json" if not only else f"out/ascent300_{only}.json")).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    for row in report:
        flag = "" if row["verdict"].startswith("VERIFIED") and "/" not in row["verdict"] else "  <--"
        print(f"{row['subject'][:4]} {row['id']:<10} {row['verdict']:<40} derived={str(row['derived'])[:24]:<24} "
              f"key={row['key']} {row['numerical']}{flag}")
        if flag:
            for n in row["notes"][:4]:
                print(f"{'':<16}- {str(n)[:150]}")
    print()
    for s, c in per_subject.items():
        print(f"{s:<12} {dict(c)}")


if __name__ == "__main__":
    main()
