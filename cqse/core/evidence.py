"""Typed verification evidence (blueprint section 34).

A check never returns a bare boolean. It returns a VerificationRecord with an
explicit status, method, tool version, assumptions and limitations. A report
aggregates records and FAILS CLOSED: anything that is not an affirmative pass
on a hard check blocks release.
"""
from __future__ import annotations

import hashlib
import json
import signal
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterator, TypeVar

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PROVED = "PROVED"                       # formal proof under declared axioms
    EXACT_CHECKED = "EXACT_CHECKED"         # exact symbolic / exhaustive within declared scope
    NUMERICALLY_CHECKED = "NUMERICALLY_CHECKED"  # evidence only, never proof
    RULE_CHECKED = "RULE_CHECKED"           # versioned curated rule set passed
    EXPERT_REVIEWED = "EXPERT_REVIEWED"
    NOT_APPLICABLE = "NOT_APPLICABLE"       # must carry a reason
    UNRESOLVED = "UNRESOLVED"               # insufficient evidence / disagreement / timeout
    FAILED = "FAILED"


# Statuses that count as an affirmative pass for a HARD check.
AFFIRMATIVE = {
    CheckStatus.PROVED,
    CheckStatus.EXACT_CHECKED,
    CheckStatus.RULE_CHECKED,
    CheckStatus.EXPERT_REVIEWED,
}
# NUMERICALLY_CHECKED is deliberately NOT affirmative for hard checks unless the
# check explicitly declares numeric evidence acceptable (e.g. a cross-check).


class VerificationRecord(BaseModel):
    check_id: str
    status: CheckStatus
    hard: bool = True
    numeric_evidence_sufficient: bool = False
    method: str
    tool: str = "cqse"
    tool_version: str = ""
    input_artifact_hash: str = ""
    assumptions: list[str] = Field(default_factory=list)
    domain_coverage: str = ""
    result: str = ""
    limitations: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reviewer: str = "automated"

    def is_affirmative(self) -> bool:
        if self.status in AFFIRMATIVE:
            return True
        if self.status == CheckStatus.NUMERICALLY_CHECKED and self.numeric_evidence_sufficient:
            return True
        if self.status == CheckStatus.NOT_APPLICABLE:
            # N/A is acceptable only with a stated reason.
            return bool(self.result.strip())
        return False


class VerificationReport(BaseModel):
    item_hash: str
    records: list[VerificationRecord] = Field(default_factory=list)

    def add(self, rec: VerificationRecord) -> VerificationRecord:
        rec.input_artifact_hash = rec.input_artifact_hash or self.item_hash
        self.records.append(rec)
        return rec

    def extend(self, recs: list[VerificationRecord]) -> None:
        for r in recs:
            self.add(r)

    @property
    def blocking(self) -> list[VerificationRecord]:
        return [r for r in self.records if r.hard and not r.is_affirmative()]

    @property
    def failed(self) -> list[VerificationRecord]:
        return [r for r in self.records if r.status == CheckStatus.FAILED]

    @property
    def passed_hard_gates(self) -> bool:
        # Empty report never passes: absence of evidence is not evidence.
        return bool(self.records) and not self.blocking

    def summary(self) -> str:
        lines = [f"item {self.item_hash[:12]}  hard-gates: {'PASS' if self.passed_hard_gates else 'BLOCKED'}"]
        for r in self.records:
            flag = "ok " if r.is_affirmative() else ("-- " if not r.hard else "XX ")
            lines.append(f"  {flag}{r.check_id:<38} {r.status.value:<20} {r.result}")
        return "\n".join(lines)


def content_hash(obj: Any) -> str:
    """Stable sha256 over a JSON-serialisable object (pydantic models allowed)."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CheckTimeout(Exception):
    pass


@contextmanager
def time_limit(seconds: int) -> Iterator[None]:
    """SIGALRM-based limit (POSIX main thread). Timeout -> CheckTimeout.

    Callers must convert CheckTimeout into UNRESOLVED, never into a pass.
    """
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(signum, frame):  # noqa: ARG001
        raise CheckTimeout(f"exceeded {seconds}s")

    try:
        old = signal.signal(signal.SIGALRM, _handler)
    except ValueError:  # not main thread
        yield
        return
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


T = TypeVar("T")


def guarded(check_id: str, fn: Callable[[], VerificationRecord], seconds: int = 20,
            hard: bool = True) -> VerificationRecord:
    """Run a check; any exception or timeout becomes UNRESOLVED (fail closed)."""
    try:
        with time_limit(seconds):
            return fn()
    except CheckTimeout as e:
        return VerificationRecord(check_id=check_id, status=CheckStatus.UNRESOLVED, hard=hard,
                                  method="timeout-guard", result=f"timeout: {e}")
    except Exception as e:  # noqa: BLE001 - any solver error must block, not pass
        return VerificationRecord(check_id=check_id, status=CheckStatus.UNRESOLVED, hard=hard,
                                  method="exception-guard", result=f"{type(e).__name__}: {e}")
