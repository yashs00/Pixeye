"""Release workflow (blueprint 21, 33, 40, 42).

Default is BLOCKED. Software verification and teacher approval are separate
facts. Any edit to release-relevant fields invalidates approvals. Published
versions are immutable; corrections create a new version with a change log.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from cqse.core.evidence import CheckStatus, VerificationRecord, VerificationReport, content_hash
from cqse.core.problem import ProblemState, Subject
from cqse.verification.pipeline import EXPERT_RESOLVABLE, verify_item


class ItemState(str, Enum):
    DRAFT = "DRAFT"
    VERIFIED_BY_SOFTWARE = "VERIFIED_BY_SOFTWARE"
    QUARANTINED = "QUARANTINED"
    TEACHER_REVIEW_1 = "TEACHER_REVIEW_1"
    INDEPENDENT_REVIEW_2 = "INDEPENDENT_REVIEW_2"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class Reviewer(BaseModel):
    reviewer_id: str
    subjects: list[Subject]
    qualified: bool = True


class AuditEvent(BaseModel):
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str
    action: str
    detail: str = ""
    item_hash: str = ""


class Approval(BaseModel):
    reviewer_id: str
    item_hash: str
    rubric: dict[str, str]  # dimension -> pass/revise/fail/n.a.
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


RUBRIC = ["scientific_correctness", "syllabus_fit", "clarity_assumptions", "answer_uniqueness",
          "options_and_distractors", "solution_and_alternatives", "notation_units_figures",
          "intended_concept", "difficulty_time", "no_accidental_clues", "provenance_rights",
          "student_feedback"]


class ReleaseError(RuntimeError):
    pass


class ItemRecord(BaseModel):
    item: ProblemState
    state: ItemState = ItemState.DRAFT
    high_stakes: bool = False
    report: Optional[VerificationReport] = None
    attestations: list[VerificationRecord] = Field(default_factory=list)
    approvals: list[Approval] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
    published_hash: Optional[str] = None
    supersedes: Optional[str] = None
    change_log: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------ helpers
    @property
    def item_hash(self) -> str:
        return content_hash(self.item.release_payload())

    def _log(self, actor: str, action: str, detail: str = "") -> None:
        self.audit.append(AuditEvent(actor=actor, action=action, detail=detail, item_hash=self.item_hash))

    def requires_second_review(self) -> bool:
        if self.high_stakes or self.item.subject == Subject.CHEMISTRY:
            return True
        if self.item.formal.get("kind") == "equation_system":  # model correctness rests on a teacher
            return True
        if self.report and any("second expert review" in " ".join(r.limitations) for r in self.report.records):
            return True
        return bool(self.item.identity.lineage)  # generated/novel variants

    def effective_blocking(self) -> list[VerificationRecord]:
        if self.report is None or self.report.item_hash != self.item_hash:
            return [VerificationRecord(check_id="report.stale", status=CheckStatus.UNRESOLVED,
                                       method="hash compare", result="no report for this exact version")]
        att = {a.check_id for a in self.attestations
               if a.input_artifact_hash == self.item_hash and a.status == CheckStatus.EXPERT_REVIEWED}
        out = []
        for r in self.report.blocking:
            if r.status == CheckStatus.UNRESOLVED and r.check_id in EXPERT_RESOLVABLE and r.check_id in att:
                continue
            out.append(r)
        return out

    # ------------------------------------------------------------ transitions
    def run_verification(self, teacher_override_profile: bool = False) -> VerificationReport:
        if self.state in (ItemState.PUBLISHED, ItemState.RETIRED):
            raise ReleaseError("published/retired versions are immutable")
        self.report = verify_item(self.item, teacher_override_profile)
        failed = [r for r in self.report.records if r.hard and r.status == CheckStatus.FAILED]
        if failed:
            self.state = ItemState.QUARANTINED
        elif self.effective_blocking():
            self.state = ItemState.QUARANTINED if not all(
                r.check_id in EXPERT_RESOLVABLE for r in self.effective_blocking()) else ItemState.TEACHER_REVIEW_1
        else:
            self.state = ItemState.VERIFIED_BY_SOFTWARE
        self._log("system", "verify", f"-> {self.state.value}; blocking="
                  f"{[r.check_id for r in self.effective_blocking()]}")
        return self.report

    def attest(self, reviewer: Reviewer, check_id: str, evidence: str) -> None:
        """Expert resolves an EXPERT_RESOLVABLE UNRESOLVED check with cited evidence."""
        self._require_reviewer(reviewer)
        if check_id not in EXPERT_RESOLVABLE:
            raise ReleaseError(f"{check_id} cannot be resolved by attestation")
        if not evidence.strip():
            raise ReleaseError("attestation needs cited evidence (source, page, reasoning)")
        rec = next((r for r in (self.report.records if self.report else []) if r.check_id == check_id), None)
        if rec is None or rec.status != CheckStatus.UNRESOLVED:
            raise ReleaseError(f"{check_id} is not an UNRESOLVED check on the current report")
        self.attestations.append(VerificationRecord(
            check_id=check_id, status=CheckStatus.EXPERT_REVIEWED, method="expert attestation",
            input_artifact_hash=self.item_hash, reviewer=reviewer.reviewer_id, result=evidence))
        self._log(reviewer.reviewer_id, "attest", f"{check_id}: {evidence}")

    def approve(self, reviewer: Reviewer, rubric: dict[str, str]) -> None:
        self._require_reviewer(reviewer)
        if self.state in (ItemState.QUARANTINED, ItemState.REJECTED, ItemState.PUBLISHED, ItemState.RETIRED,
                          ItemState.DRAFT, ItemState.SUSPENDED):
            raise ReleaseError(f"cannot approve from state {self.state.value}")
        blocking = self.effective_blocking()
        if blocking:
            raise ReleaseError("unresolved hard gates: " + ", ".join(r.check_id for r in blocking))
        missing = [d for d in RUBRIC if d not in rubric]
        if missing:
            raise ReleaseError(f"rubric incomplete: {missing}")
        bad = {d: v for d, v in rubric.items() if v not in ("pass", "n.a.")}
        if bad:
            raise ReleaseError(f"rubric not passing: {bad}")
        if any(a.reviewer_id == reviewer.reviewer_id and a.item_hash == self.item_hash for a in self.approvals):
            raise ReleaseError("same reviewer cannot approve twice; second review must be independent")
        self.approvals.append(Approval(reviewer_id=reviewer.reviewer_id, item_hash=self.item_hash, rubric=rubric))
        valid = [a for a in self.approvals if a.item_hash == self.item_hash]
        need = 2 if self.requires_second_review() else 1
        self.state = ItemState.APPROVED if len(valid) >= need else ItemState.INDEPENDENT_REVIEW_2
        self._log(reviewer.reviewer_id, "approve", f"{len(valid)}/{need} approvals")

    def edit(self, actor: str, new_item: ProblemState, reason: str) -> None:
        if self.state == ItemState.PUBLISHED:
            raise ReleaseError("published items are immutable; use correct()")
        old = self.item_hash
        self.item = new_item
        if self.item_hash != old:
            self.approvals = [a for a in self.approvals if a.item_hash == self.item_hash]
            self.report = None
            self.state = ItemState.DRAFT
            self._log(actor, "edit", f"{reason}; approvals and verification invalidated")

    def publish(self, actor: str, checklist: dict[str, bool]) -> None:
        if self.state != ItemState.APPROVED:
            raise ReleaseError(f"only APPROVED items can be published (state {self.state.value})")
        if self.effective_blocking():
            raise ReleaseError("hard gates no longer pass for this version")
        missing = [k for k in RELEASE_CHECKLIST if checklist.get(k) is not True]
        if missing:
            raise ReleaseError(f"release checklist not complete: {missing}")
        if self.item.provenance.rights_status in ("UNKNOWN", "RESTRICTED"):
            raise ReleaseError("rights status does not permit publication")
        self.published_hash = self.item_hash
        self.state = ItemState.PUBLISHED
        self._log(actor, "publish", self.item_hash)

    def suspend(self, actor: str, report: str) -> None:
        if self.state != ItemState.PUBLISHED:
            raise ReleaseError("only published items can be suspended")
        self.state = ItemState.SUSPENDED
        self._log(actor, "suspend", report)

    def correct(self, actor: str, corrected: ProblemState, note: str) -> "ItemRecord":
        """Create a NEW version; the attempted version is preserved unchanged."""
        if self.state not in (ItemState.SUSPENDED, ItemState.PUBLISHED):
            raise ReleaseError("correct() applies to published/suspended items")
        self.state = ItemState.RETIRED
        self._log(actor, "retire", f"superseded: {note}")
        corrected = corrected.model_copy(deep=True)
        corrected.identity.version = self.item.identity.version + 1
        new = ItemRecord(item=corrected, high_stakes=self.high_stakes, supersedes=self.published_hash,
                         change_log=self.change_log + [note])
        new._log(actor, "created_as_correction", note)
        return new

    @staticmethod
    def _require_reviewer(r: Reviewer) -> None:
        if not r.qualified:
            raise ReleaseError("reviewer not qualified")


def _subject_guard(fn):
    def wrapper(self: ItemRecord, reviewer: Reviewer, *a, **k):
        if self.item.subject not in reviewer.subjects:
            raise ReleaseError(f"reviewer {reviewer.reviewer_id} not qualified for {self.item.subject.value}")
        return fn(self, reviewer, *a, **k)
    return wrapper


ItemRecord.approve = _subject_guard(ItemRecord.approve)  # type: ignore[method-assign]
ItemRecord.attest = _subject_guard(ItemRecord.attest)    # type: ignore[method-assign]


RELEASE_CHECKLIST = [
    "provenance_and_rights_recorded",
    "student_render_checked_against_formal_state",
    "exam_profile_official_and_current",
    "assumptions_units_conventions_explicit",
    "solutions_reach_canonical_answer",
    "every_option_tested",
    "rollback_and_incident_tracking_available",
]
