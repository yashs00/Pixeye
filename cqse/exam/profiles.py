"""Versioned exam profiles with status governance (blueprint 16-17)."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel

from cqse.core.evidence import CheckStatus, VerificationRecord
from cqse.core.problem import ProblemState

PROFILE_DIR = Path(__file__).parent / "profiles"


class ProfileStatus(str, Enum):
    OFFICIAL = "OFFICIAL"
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"
    PROVISIONAL = "PROVISIONAL"
    UNCONFIRMED = "UNCONFIRMED"
    SUPERSEDED = "SUPERSEDED"


class ExamProfile(BaseModel):
    profile_id: str
    exam: str
    year: int
    version: int
    status: ProfileStatus
    source_url: str
    last_verified: str
    verified_by: str = ""
    time_limit_minutes: Optional[int] = None
    subjects: dict[str, Any] = {}

    def formats_for(self, subject: str) -> set[str]:
        s = self.subjects.get(subject) or {}
        return {sec["format"] for sec in (s.get("sections") or {}).values()}

    def section_for(self, subject: str, fmt: str) -> Optional[dict]:
        for sec in ((self.subjects.get(subject) or {}).get("sections") or {}).values():
            if sec["format"] == fmt:
                return sec
        return None


def load_profile(profile_id: str) -> ExamProfile:
    path = PROFILE_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no exam profile {profile_id!r}")
    return ExamProfile(**yaml.safe_load(path.read_text()))


def all_profiles() -> list[ExamProfile]:
    return [load_profile(p.stem) for p in sorted(PROFILE_DIR.glob("*.yaml"))]


def check_profile(item: ProblemState, teacher_override: bool = False) -> VerificationRecord:
    """Hard gate: the item's format must be allowed by a usable profile."""
    try:
        prof = load_profile(item.exam_profile_id)
    except Exception as e:  # noqa: BLE001
        return VerificationRecord(check_id="exam.profile", status=CheckStatus.FAILED,
                                  method="profile lookup", result=str(e))
    usable = {ProfileStatus.OFFICIAL}
    if teacher_override:
        usable |= {ProfileStatus.HISTORICAL_BASELINE}
    if prof.status not in usable:
        return VerificationRecord(
            check_id="exam.profile", status=CheckStatus.FAILED, method="profile status governance",
            result=f"profile {prof.profile_id} is {prof.status.value}; not usable"
                   + ("" if teacher_override else " (HISTORICAL_BASELINE needs explicit teacher override)"))
    fmt = item.question_format.value
    sec = prof.section_for(item.subject.value, fmt)
    if sec is None:
        return VerificationRecord(check_id="exam.profile", status=CheckStatus.FAILED, method="format check",
                                  result=f"{fmt} not in {prof.profile_id} for {item.subject.value}")
    if "options" in sec and item.options and len(item.options) != sec["options"]:
        return VerificationRecord(check_id="exam.profile", status=CheckStatus.FAILED, method="option count",
                                  result=f"{len(item.options)} options; profile requires {sec['options']}")
    return VerificationRecord(check_id="exam.profile", status=CheckStatus.RULE_CHECKED,
                              method="versioned profile", tool=f"profile {prof.profile_id}",
                              result=f"{fmt} allowed ({prof.status.value}, verified {prof.last_verified})",
                              data={"source_url": prof.source_url})
