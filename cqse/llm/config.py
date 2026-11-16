"""Per-task model profiles and price table.

Token strategy (in order of savings):
  1. Don't call at all: deterministic triage, local result cache, dedupe.
  2. Prompt caching: one frozen system prompt shared by every call.
  3. Batch API for bulk jobs (50% off, async).
  4. Effort tuned per task (effort is the first quality/cost lever; escalate only on failure).
  5. Minimal inputs/outputs: only stem + options are sent; JSON-schema output, tight max_tokens.

Model: Claude Opus 5.5 everywhere by default. To use a cheaper model for a task,
change it here (e.g. "claude-sonnet-5-5" / "claude-haiku-5-5") and re-run the
eval on your own PYQs before trusting the change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = os.environ.get("CQSE_LLM_MODEL", "claude-opus-5-5")


@dataclass(frozen=True)
class TaskProfile:
    model: str
    effort: str          # low | medium | high | xhigh | max
    max_tokens: int      # thinking counts toward this; leave headroom
    escalate_effort: str  # used ONCE, only after the verifier rejects the first answer


TASKS: dict[str, TaskProfile] = {
    "formalize": TaskProfile(model=DEFAULT_MODEL, effort="medium", max_tokens=8000, escalate_effort="high"),
}

# USD per 1M tokens (first-party API, cached 2026-11-03). Cache write = 1.25x input (5-min TTL).
PRICES = {
    "claude-opus-5-5":   {"in": 4.00, "out": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.10, "cache_write": 2.50},
    "claude-haiku-5-5":  {"in": 0.10, "out": 0.50,  "cache_read": 0.01, "cache_write": 0.125},
}
BATCH_DISCOUNT = 0.5

# Server-side fallback when a request is declined (not available inside Batches).
FALLBACK_BETA = "server-side-fallback-2026-07-01"
USE_FALLBACKS = os.environ.get("CQSE_LLM_FALLBACKS", "1") == "1"
