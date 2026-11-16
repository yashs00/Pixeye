"""Common result type returned by every pluggable engine (see cqse/engines.py)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sympy as sp

from cqse.core.evidence import VerificationRecord


@dataclass
class EngineResult:
    value: Optional[sp.Basic] = None          # canonical answer; None = not verified
    unit: str = ""
    records: list[VerificationRecord] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
