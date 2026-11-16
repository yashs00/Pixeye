"""Blind accuracy test: draw unseen questions, hide keys and explanations, compare only after formalizing.

  python data/pyq/blind_sample.py draw  <batch> <n> [--seed S]   -> blind/<batch>/questions.md (stem + options ONLY)
                                                                   blind/<batch>/sealed.json   (keys; do not open)
  (write data/pyq/formals/blind_<batch>.py from questions.md alone)
  python data/pyq/blind_sample.py solve <batch>                 -> engine answers only (keys stay sealed)
  python data/pyq/blind_sample.py score <batch>                 -> runs the engines, THEN unseals and compares

Draw rules: text-only questions (no images), not in the 300-question development set, stratified by subject.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _dev_ids() -> set[str]:
    ids = set()
    for s in ("chem", "maths", "phy"):
        p = ROOT / f"data/pyq/ascent_{s}.jsonl"
        if p.exists():
            ids |= {json.loads(l)["pyq_id"] for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}
    return ids


def draw(batch: str, n: int, seed: int) -> None:
    recs = [json.loads(l) for l in (ROOT / "data/pyq/ascent_all.jsonl").read_text(encoding="utf-8").splitlines()]
    dev = _dev_ids()
    used = set()
    for prev in (ROOT / "blind").glob("*/sealed.json"):
        used |= set(json.loads(prev.read_text()))
    pool = [r for r in recs if r["pyq_id"] not in dev and r["pyq_id"] not in used
            and not (r.get("extraction") or {}).get("unresolved_fragments")]
    rng = random.Random(seed)
    subjects = ["MATHEMATICS", "PHYSICS", "CHEMISTRY"]
    pick = []
    for i in range(n):
        s = subjects[i % 3]
        cands = [r for r in pool if r["subject"] == s and r not in pick]
        pick.append(rng.choice(cands))
    d = ROOT / "blind" / batch
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# Blind batch {batch}: {n} questions (keys and explanations withheld)\n"]
    for r in pick:
        qid = r["pyq_id"].removeprefix("ASCENT-")
        lines.append(f"## {qid}  [{r['subject']} / {r['chapter']} / {r['question_format']}]\n\n{r['stem']}\n")
        for o in r["options"]:
            lines.append(f"- ({o['id']}) {o['text']}")
        lines.append("")
    (d / "questions.md").write_text("\n".join(lines), encoding="utf-8")
    (d / "sealed.json").write_text(json.dumps({r["pyq_id"]: {"key": r["answer_key"], "solution": r.get("solution")}
                                               for r in pick}))
    print(f"wrote {d / 'questions.md'} ({n} questions); keys sealed in {d / 'sealed.json'}")


def draw_chapter(batch: str, chapter: str) -> None:
    """Every text-only question of one chapter (development-set questions included only if unseen)."""
    recs = [json.loads(l) for l in (ROOT / "data/pyq/ascent_all.jsonl").read_text(encoding="utf-8").splitlines()]
    dev = _dev_ids()
    pick = [r for r in recs if r["chapter"] == chapter and r["pyq_id"] not in dev
            and not (r.get("extraction") or {}).get("unresolved_fragments")]
    d = ROOT / "blind" / batch
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# Blind chapter batch {batch}: {chapter} - {len(pick)} questions (keys and explanations withheld)\n"]
    for r in pick:
        qid = r["pyq_id"].removeprefix("ASCENT-")
        lines.append(f"## {qid}  [{r['topic']} / {r['question_format']}]\n\n{r['stem']}\n")
        for o in r["options"]:
            lines.append(f"- ({o['id']}) {o['text']}")
        lines.append("")
    (d / "questions.md").write_text("\n".join(lines), encoding="utf-8")
    (d / "sealed.json").write_text(json.dumps({r["pyq_id"]: {"key": r["answer_key"], "solution": r.get("solution")}
                                               for r in pick}))
    print(f"{chapter}: {len(pick)} text-only questions -> {d / 'questions.md'}; keys sealed")


def score(batch: str, solve_only: bool = False) -> None:
    import importlib.util

    from cqse.ingest.explanation import final_value
    from cqse.ingest.pyq import PYQRecord
    from cqse.verification.formats import option_code
    from cqse.verification.options import check_options_and_key
    from cqse.ingest.pyq import to_problem_state
    from cqse.verification.pipeline import canonical_answer, software_blocking
    f = ROOT / f"data/pyq/formals/blind_{batch}.py"
    spec = importlib.util.spec_from_file_location(f.stem, f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    formals, skipped = mod.FORMALS, getattr(mod, "SKIPPED", {})
    recs = {json.loads(l)["pyq_id"]: json.loads(l) for l in
            (ROOT / "data/pyq/ascent_all.jsonl").read_text(encoding="utf-8").splitlines()}
    sealed_path = ROOT / "blind" / batch / "sealed.json"
    ids = [l.split()[1] for l in (ROOT / "blind" / batch / "questions.md").read_text(encoding="utf-8").splitlines()
           if l.startswith("## ")]
    # 1) engines first, with keys still unread
    derived = {}
    for pid in ["ASCENT-" + i for i in ids]:
        qid = pid.removeprefix("ASCENT-")
        if qid not in formals:
            continue
        rec = dict(recs[pid])
        ent = formals[qid]
        rec["formal"] = ent["formal"]
        ov = ent.get("option_values")
        if ov is None and ent["formal"].get("kind") == "statement_set":
            ov = {o["id"]: option_code(ent["formal"]["format"], o["text"]) for o in rec["options"]}
        if ov:
            rec["options"] = [{**o, "value": ov.get(o["id"])} for o in rec["options"]]
        rec["answer_key"] = None
        prec = PYQRecord(**rec)
        can = canonical_answer(prec.subject, prec.formal)
        if can.value is None or software_blocking(can.records):
            derived[qid] = ("UNVERIFIABLE", None, [r.result for r in software_blocking(can.records)][:2])
            continue
        if rec["options"]:
            recs_ = check_options_and_key(to_problem_state(prec), can.value)
            card = next((r for r in recs_ if r.check_id == "options.cardinality"), None)
            opts = (card.data.get("correct") if card else None) or []
            derived[qid] = ("ANSWERED", opts, str(can.value))
        else:
            derived[qid] = ("ANSWERED", None, str(can.value))
    if solve_only:
        for qid, d in derived.items():
            print(f"{qid:<34} {d[0]:<13} {str(d[1]) if d[1] is not None else '':<8} {str(d[2])[:90]}")
        missing = [i for i in ids if i not in formals and i not in skipped]
        print(f"\n{len(derived)} solved, {sum(1 for d in derived.values() if d[0] != 'ANSWERED')} unverifiable, "
              f"{len(skipped)} skipped, {len(missing)} not yet formalized")
        return
    # 2) only now unseal
    sealed = json.loads(sealed_path.read_text())
    rows, tally = [], {"agree": 0, "disagree": 0, "unverifiable": 0, "not formalized": 0}
    for pid, s in sealed.items():
        qid = pid.removeprefix("ASCENT-")
        key = s["key"]
        if qid not in derived:
            tally["not formalized"] += 1
            rows.append((qid, "NOT FORMALIZED", skipped.get(qid, ""), key))
            continue
        st, opts, val = derived[qid]
        if st == "UNVERIFIABLE":
            tally["unverifiable"] += 1
            rows.append((qid, "UNVERIFIABLE", val, key))
            continue
        if opts is not None and opts != []:
            ok = (opts == (key if isinstance(key, list) else [key]))
            shown = f"option {opts} (value {val})"
        elif opts == []:
            ok, shown = False, f"no option matches value {val}"
        else:
            ref, conf = final_value(s.get("solution"))
            if ref is None:
                tally.setdefault("no reference value", 0)
                tally["no reference value"] += 1
                rows.append((qid, "NO REFERENCE", val, "explanation states no clear final number"))
                continue
            try:
                ok = ref is not None and round(float(__import__('sympy').N(val))) == round(float(ref))
            except Exception:  # noqa: BLE001
                ok = False
            key = f"explanation:{ref} ({conf})"
            shown = val
        tally["agree" if ok else "disagree"] += 1
        rows.append((qid, "AGREE" if ok else "DISAGREE", shown, key))
    for r in rows:
        print(f"{r[0]:<34} {r[1]:<15} engine={str(r[2])[:60]:<60} key={r[3]}")
    print("\n", tally)
    (ROOT / "blind" / batch / "result.json").write_text(json.dumps({"rows": rows, "tally": tally}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "draw":
        seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
        draw(sys.argv[2], int(sys.argv[3]), seed)
    elif cmd == "chapter":
        draw_chapter(sys.argv[2], sys.argv[3])
    elif cmd == "solve":   # engines only; never opens sealed.json
        score(sys.argv[2], solve_only=True)
    elif cmd == "score":
        score(sys.argv[2])
