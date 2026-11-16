"""Token/cost ledger with a hard budget. Every API call is recorded."""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cqse.llm.config import BATCH_DISCOUNT, PRICES


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class UsageRow:
    task: str
    model: str
    key: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    batch: bool = False
    cost_usd: float = 0.0
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def cost_of(model: str, inp: int, out: int, cread: int, cwrite: int, batch: bool) -> float:
    p = PRICES.get(model)
    if p is None:
        raise KeyError(f"no price for {model}; add it to cqse/llm/config.py PRICES")
    c = (inp * p["in"] + out * p["out"] + cread * p["cache_read"] + cwrite * p["cache_write"]) / 1e6
    return c * (BATCH_DISCOUNT if batch else 1.0)


class Ledger:
    def __init__(self, budget_usd: Optional[float] = None, path: Optional[Path] = None):
        self.budget = budget_usd
        self.rows: list[UsageRow] = []
        self.path = path
        self.saved_by_cache = 0  # calls avoided by local cache
        self.skipped_by_triage = 0
        self._lock = threading.Lock()

    @property
    def spent(self) -> float:
        return sum(r.cost_usd for r in self.rows)

    def check(self, estimate_usd: float = 0.0) -> None:
        if self.budget is not None and self.spent + estimate_usd > self.budget:
            raise BudgetExceeded(f"budget ${self.budget:.2f} would be exceeded "
                                 f"(spent ${self.spent:.4f}, next call ~${estimate_usd:.4f})")

    def record(self, task: str, model: str, key: str, usage, batch: bool = False) -> UsageRow:
        g = lambda n: int(getattr(usage, n, 0) or 0)  # noqa: E731
        row = UsageRow(task=task, model=model, key=key, input_tokens=g("input_tokens"),
                       output_tokens=g("output_tokens"), cache_read=g("cache_read_input_tokens"),
                       cache_write=g("cache_creation_input_tokens"), batch=batch)
        row.cost_usd = cost_of(model, row.input_tokens, row.output_tokens, row.cache_read, row.cache_write, batch)
        with self._lock:
            self.rows.append(row)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(asdict(row)) + "\n")
        return row

    def summary(self) -> str:
        tot = lambda a: sum(getattr(r, a) for r in self.rows)  # noqa: E731
        inp, cr = tot("input_tokens"), tot("cache_read")
        hit = cr / max(1, inp + cr + tot("cache_write"))
        return (f"API calls: {len(self.rows)} | avoided by local cache: {self.saved_by_cache} | "
                f"skipped by triage: {self.skipped_by_triage}\n"
                f"tokens in: {inp}  cache-read: {cr}  cache-write: {tot('cache_write')}  out: {tot('output_tokens')}"
                f"  (prompt-cache hit share {hit:.0%})\n"
                f"cost: ${self.spent:.4f}" + (f" of budget ${self.budget:.2f}" if self.budget is not None else ""))
