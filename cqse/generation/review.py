"""Record a teacher's approval of a question family (its stem <-> model correspondence and its mistakes).

  python -m cqse.generation.review show    <family_id>          -> stem, model and mistakes of one sample item
  python -m cqse.generation.review approve <family_id> --reviewer "Name"
  python -m cqse.generation.review list

An approval is tied to the family's code fingerprint: editing the family voids it automatically.
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import json
import random

from cqse.generation.framework import FAMILIES, REVIEWS_PATH, family_fingerprint
from cqse.generation.run import MODULES


def _load():
    for m in MODULES.values():
        try:
            importlib.import_module(m)
        except ModuleNotFoundError:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "approve", "list"])
    ap.add_argument("family", nargs="?")
    ap.add_argument("--reviewer")
    a = ap.parse_args(argv)
    _load()
    reviews = json.loads(REVIEWS_PATH.read_text()) if REVIEWS_PATH.exists() else {}
    if a.cmd == "list":
        for fid, fam in sorted(FAMILIES.items()):
            r = reviews.get(fid)
            ok = r and r["fingerprint"] == family_fingerprint(fam)
            print(f"{fid:<34} {'APPROVED by ' + r['reviewer'] + ' ' + r['date'] if ok else ('STALE (family changed)' if r else 'not reviewed')}")
        return 0
    fam = FAMILIES[a.family]
    if a.cmd == "show":
        p = fam.sample(random.Random(0))
        print("PARAMS:", p, "\nSTEM:", fam.stem(p), "\nMODEL:", json.dumps(fam.formal(p).get("model", []), indent=1))
        for m in fam.mistakes(p):
            print(f"MISTAKE {m.id}: {m.why_students} | {m.why_wrong}")
        return 0
    if not a.reviewer:
        raise SystemExit("--reviewer is required")
    reviews[fam.id] = {"reviewer": a.reviewer, "date": datetime.date.today().isoformat(),
                       "fingerprint": family_fingerprint(fam)}
    REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEWS_PATH.write_text(json.dumps(reviews, indent=1))
    print(f"approved {fam.id} (fingerprint {reviews[fam.id]['fingerprint']}); regenerate to upgrade its items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
