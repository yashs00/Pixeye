"""CQSE variant service: a small HTTP API the question-bank backend calls (standard library only).

  python -m cqse.service [--port 8765] [--host 127.0.0.1]

  GET  /health
  POST /match     {externalId, chapter, stem}          -> patterns for a bank question, best first
  POST /variants  {family, n, seed, exclude: [ids]}    -> NDJSON stream, one verified variant per line
  POST /build     {family, params, seed}               -> one variant rebuilt + re-verified from its parameters

Every variant the service returns has passed the generator's checks (answer derived two ways, exactly one correct
option, every wrong option the engine-verified answer of a named mistake, originality vs the bank). Nothing
unverified is ever sent. /build exists so the backend never trusts a variant posted back by a browser: on Accept
it rebuilds the variant from (family, params, seed) and stores the server's copy.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cqse.generation import run as gen_run
from cqse.generation.framework import FAMILIES, build, family_review

for _m in gen_run.MODULES.values():
    __import__(_m)

_BANK = None
_BANK_LOCK = threading.Lock()


def bank():
    global _BANK
    with _BANK_LOCK:
        if _BANK is None:
            _BANK = gen_run._bank_stems()
        return _BANK


def _pretty(mistake_id: str) -> str:
    return mistake_id.replace("_", " ").capitalize()


def _tier(score: float, lineage: bool) -> str:
    if lineage:
        return "source"            # the pattern was modelled on this very question
    if score >= 0.30:
        return "same"              # same kind of question (measured on the bank: ~60% of questions)
    if score >= 0.20:
        return "related"
    return "none"


def _family_card(fam, score: float, reason: str) -> dict:
    return {"tier": _tier(score, reason.startswith("Made")),"id": fam.id, "topic": fam.topic, "chapter": fam.chapter, "difficulty": fam.difficulty,
            "numerical": fam.numerical, "score": round(score, 3), "reason": reason,
            "teacherApproved": family_review(fam) is not None}


def match(body: dict) -> dict:
    ext, chapter, stem = body.get("externalId", ""), body.get("chapter", ""), body.get("stem", "")
    fams = [f for f in FAMILIES.values() if f.chapter == chapter]
    if not fams:
        return {"supported": False, "patterns": [],
                "message": f"No verified patterns for '{chapter}' yet."}
    toks = gen_run._tokens(stem)
    stems_by_id = {qid: t for qid, t in bank().get(chapter, [])}
    out = []
    for fam in fams:
        if ext and ext in fam.modelled_on:
            out.append(_family_card(fam, 1.0, "Made from this question"))
            continue
        refs = [stems_by_id[q] for q in fam.modelled_on if q in stems_by_id]
        rng = random.Random(fam.id)
        for _ in range(3):
            try:
                refs.append(gen_run._tokens(fam.stem(fam.sample(rng))))
            except Exception:
                pass
        best = max((len(toks & r) / max(1, len(toks | r)) for r in refs), default=0.0)
        out.append(_family_card(fam, best, "Closest pattern in this chapter"))
    out.sort(key=lambda c: -c["score"])
    return {"supported": True, "patterns": out, "close": out[0]["tier"] != "none"}


def _variant(g, seed: int) -> dict | None:
    row = gen_run.to_bank_row(g)
    sim, who = gen_run.originality(row, bank())
    if sim >= gen_run.NEAR_COPY:
        return None
    md = row["sourceMetadata"]
    md["originality"] = {"max_similarity_to_bank": round(sim, 3), "closest": who}
    md["seed"] = seed
    traps = {oid: {"label": _pretty(d["mistake"]), "why": d["why_students"], "wrong": d["why_wrong"]}
             for oid, d in md["distractor_origins"].items()}
    return {"key": row["externalId"], "family": g.family.id, "params": g.params, "seed": seed,
            "status": g.status, "row": row, "traps": traps}


def variants(body: dict):
    fam = FAMILIES.get(body.get("family", ""))
    if fam is None:
        yield {"error": "unknown pattern"}
        return
    n = max(1, min(int(body.get("n", 5)), 12))
    seed = int(body.get("seed", 0))
    exclude = set(body.get("exclude", []))
    rng = random.Random(f"{fam.id}:{seed}:svc")
    seen, made, tries = set(), 0, 0
    while made < n and tries < 200:
        tries += 1
        p = fam.sample(rng)
        k = json.dumps(p, sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        g, _why = build(fam, p, seed)
        if g is None or g.item.identity.problem_id in exclude:
            continue
        v = _variant(g, seed)
        if v is None:
            continue
        made += 1
        yield v
    yield {"done": True, "made": made, "exhausted": made < n}


def rebuild(body: dict) -> dict:
    fam = FAMILIES.get(body.get("family", ""))
    if fam is None:
        return {"error": "unknown pattern"}
    g, why = build(fam, body.get("params") or {}, int(body.get("seed", 0)))
    if g is None:
        return {"error": f"variant failed verification: {why}"}
    v = _variant(g, int(body.get("seed", 0)))
    return v or {"error": "variant is too close to a bank question"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        print(f"[cqse] {self.address_string()} {fmt % args}")

    def _json(self, code: int, obj) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1_000_000:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"status": "ok", "patterns": len(FAMILIES)})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._body()
        except Exception as e:
            return self._json(400, {"error": f"bad request: {e}"})
        try:
            if self.path == "/match":
                return self._json(200, match(body))
            if self.path == "/build":
                r = rebuild(body)
                return self._json(422 if "error" in r else 200, r)
            if self.path == "/variants":
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                for v in variants(body):
                    self.wfile.write((json.dumps(v, ensure_ascii=False) + "\n").encode())
                    self.wfile.flush()
                return
            self._json(404, {"error": "not found"})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # never leak a half-verified result: report the failure only
            try:
                self._json(500, {"error": f"{type(e).__name__}: {e}"})
            except Exception:
                pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args(argv)
    t = time.time()
    bank()
    print(f"CQSE variant service: {len(FAMILIES)} patterns, bank loaded in {time.time() - t:.1f} s, "
          f"listening on http://{a.host}:{a.port}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
