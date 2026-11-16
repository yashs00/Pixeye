"""Registry of pluggable engines: formal "kind" -> "module:function".

Each function has the signature  fn(formal: dict, subject: Subject) -> EngineResult  and must fail closed:
value=None (or a hard non-affirmative record) whenever the answer is not established by two independent
methods or by a versioned rule set.
"""
from __future__ import annotations

import importlib
from typing import Callable, Optional

REGISTRY: dict[str, str] = {
    "statement_set": "cqse.verification.formats:solve_and_verify",
    "area_region": "cqse.math.calculus:solve_and_verify",
    "extrema": "cqse.math.calculus:solve_and_verify",
    "calculus_value": "cqse.math.calculus:solve_and_verify",
    "geometry3d": "cqse.math.geometry3d:solve_and_verify",
    "series_sum": "cqse.math.series_stats:solve_and_verify",
    "statistics": "cqse.math.series_stats:solve_and_verify",
    "chem_property": "cqse.chemistry.rules:solve_and_verify",
    "redox": "cqse.chemistry.redox:solve_and_verify",
    "combinatorics": "cqse.math.combinatorics:solve_and_verify",
    "rigid_body": "cqse.physics.rigid_body:solve_and_verify",
}


def lookup(kind: Optional[str]) -> Optional[Callable]:
    target = REGISTRY.get(kind or "")
    if target is None:
        return None
    mod, fn = target.split(":")
    try:
        return getattr(importlib.import_module(mod), fn)
    except (ImportError, AttributeError):
        return None
