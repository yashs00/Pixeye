"""CQSE command line.

  python -m cqse ingest  data/samples/pyq_sample.jsonl [--out report.json]
  python -m cqse search  --subject MATHEMATICS --formal '{"kind":"equation",...}' [--depth 2]
  python -m cqse verify  item.json
  python -m cqse profiles
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from cqse.core.problem import ProblemState, Subject


def _ingest(a) -> int:
    from cqse.ingest.pyq import ingest_file
    res = ingest_file(a.path)
    for r in res:
        print(f"{r.pyq_id:<22} {', '.join(s.value for s in r.statuses):<60} derived={r.derived_answer}"
              + (f"  DUP-OF {r.duplicate_of}" if r.duplicate_of else ""))
        for n in r.notes:
            print(f"{'':<24}- {n}")
    c = Counter(s.value for r in res for s in r.statuses)
    print("\nSummary:", dict(c))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump([r.model_dump(mode="json") for r in res], fh, indent=2)
        print("report written to", a.out)
    return 0


def _search(a) -> int:
    from cqse.search.engine import search
    r = search(a.seed_id, Subject(a.subject), json.loads(a.formal), a.profile, depth=a.depth, top_k=a.top_k)
    print(f"expanded {r.expanded} candidate states; {len(r.candidates)} shown; {len(r.rejected)} rejected\n")
    for c in r.candidates:
        it = c.item
        print(f"[{c.score:.2f}] lineage: {' > '.join(c.lineage)}")
        print("  ", it.stem)
        for o in it.options:
            d = next((d for d in it.distractors if d.option_id == o.option_id), None)
            print(f"     {o.option_id}) {o.display:<18} {'<- CORRECT' if d is None else '<- ' + d.misconception_id}")
        if it.answer.exact_answer and not it.options:
            print(f"     answer: {it.answer.exact_answer} {it.answer.units or ''}")
        print("   status: software-verified candidate - NOT approved; needs teacher review\n")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump([c.item.model_dump(mode="json") for c in r.candidates], fh, indent=2)
    return 0


def _verify(a) -> int:
    from cqse.verification.pipeline import verify_item
    with open(a.path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data if isinstance(data, list) else [data]
    worst = 0
    for d in items:
        rep = verify_item(ProblemState(**d), teacher_override_profile=a.override_profile)
        print(rep.summary(), "\n")
        worst = max(worst, 0 if rep.passed_hard_gates else 1)
    return worst


def _formalize(a) -> int:
    from pathlib import Path

    from cqse.ingest.pyq import PYQRecord
    from cqse.llm.formalize import formalize_records, triage
    from cqse.llm.gateway import Gateway
    from cqse.llm.ledger import Ledger
    from cqse.llm.prompts import user_message, user_payload

    recs = [PYQRecord(**json.loads(l)) for l in Path(a.path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.dry_run:
        class _NoClient:  # never used: dry run makes no API call
            pass
        gw = Gateway(client=_NoClient(), ledger=Ledger())
        n, worst = 0, 0.0
        for r in recs:
            needs = (not r.formal and "llm" in r.source.permitted_uses
                     and r.source.rights_status not in ("UNKNOWN", "RESTRICTED"))
            kind = triage(r.stem) if needs else None
            if kind or (needs and a.force_triage):
                p = user_payload(r.question_format.value, r.stem, [o.model_dump() for o in r.options])
                worst += gw._estimate("formalize", user_message(p))
                n += 1
            print(f"{r.pyq_id:<22} {'CALL  (' + kind + ')' if kind else 'no call'}")
        factor = 0.5 if a.batch else 1.0
        print(f"\n{n} call(s) needed; worst-case cost ${worst * factor:.4f} "
              f"(assumes no prompt-cache hits and full max_tokens; real cost is usually far lower)")
        return 0
    led = Ledger(budget_usd=a.budget_usd, path=Path(a.ledger))
    outs = formalize_records(recs, Gateway(ledger=led), use_batch=a.batch, force_triage=a.force_triage)
    with open(a.out, "w", encoding="utf-8") as fh:
        for o in outs:
            print(f"{o.pyq_id:<22} {o.action:<20} {o.llm_decision or '':<12} "
                  f"{', '.join(s.value for s in o.ingest.statuses) if o.ingest else ''}")
            for n_ in o.notes:
                print(f"{'':<24}- {n_}")
            fh.write(json.dumps({"pyq_id": o.pyq_id, "action": o.action, "decision": o.llm_decision,
                                 "attempts": o.attempts, "notes": o.notes,
                                 "ingest": o.ingest.model_dump(mode="json") if o.ingest else None,
                                 "record": o.record}) + "\n")
    print("\n" + led.summary())
    return 0


def _import_ascent(a) -> int:
    from pathlib import Path
    from cqse.ingest.ascent import import_file
    uses = a.uses.split(",") if a.uses else None
    rep = import_file(Path(a.path), Path(a.out), rights=a.rights, uses=uses, basis=a.basis)
    print(json.dumps(rep, indent=2))
    print(f"\nwritten to {a.out}; run:  python -m cqse ingest {a.out}")
    return 0


def _profiles(_a) -> int:
    from cqse.exam.profiles import all_profiles
    for p in all_profiles():
        print(f"{p.profile_id:<24} {p.status.value:<20} verified {p.last_verified}  {p.source_url}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cqse")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest"); p.add_argument("path"); p.add_argument("--out"); p.set_defaults(fn=_ingest)
    p = sub.add_parser("search")
    p.add_argument("--subject", required=True, choices=[s.value for s in Subject])
    p.add_argument("--formal", required=True, help="formal state JSON")
    p.add_argument("--profile", default="JEE_MAIN-2027-v1")
    p.add_argument("--seed-id", default="SEED")
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--out")
    p.set_defaults(fn=_search)
    p = sub.add_parser("verify"); p.add_argument("path")
    p.add_argument("--override-profile", action="store_true"); p.set_defaults(fn=_verify)
    p = sub.add_parser("profiles"); p.set_defaults(fn=_profiles)
    p = sub.add_parser("import-ascent", help="convert an ascent question-bank JSON export to CQSE JSONL")
    p.add_argument("path"); p.add_argument("--out", default="data/pyq/ascent.jsonl")
    p.add_argument("--rights", default="UNKNOWN", choices=["CLEARED", "TEACHER_OWNED", "UNKNOWN", "RESTRICTED"])
    p.add_argument("--uses", help="comma list, e.g. storage,search,derive,display,export,training,llm")
    p.add_argument("--basis", help="who confirmed the rights, and when (required to clear)")
    p.set_defaults(fn=_import_ascent)
    p = sub.add_parser("formalize", help="draft formal states with Claude, then verify them")
    p.add_argument("path")
    p.add_argument("--out", default="formalized.jsonl")
    p.add_argument("--ledger", default="llm_usage.jsonl")
    p.add_argument("--budget-usd", type=float, default=1.0, help="hard spending cap for this run")
    p.add_argument("--batch", action="store_true", help="Message Batches API: 50%% cheaper, async")
    p.add_argument("--dry-run", action="store_true", help="show calls and worst-case cost; no API use")
    p.add_argument("--force-triage", action="store_true", help="call even when no supported kind matches")
    p.set_defaults(fn=_formalize)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
