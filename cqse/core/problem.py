"""Formal problem state (blueprint sections 3, 10, 11, 36).

The formal state is the single source of truth. Stem text, options, answer key
and solution are rendered from / checked against it. Natural-language text is
stored separately so several wordings can share one verified problem.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Subject(str, Enum):
    MATHEMATICS = "MATHEMATICS"
    PHYSICS = "PHYSICS"
    CHEMISTRY = "CHEMISTRY"


class QuestionFormat(str, Enum):
    SINGLE_CORRECT_MCQ = "single_correct_mcq"
    MULTIPLE_CORRECT_MCQ = "multiple_correct_mcq"
    NUMERICAL_INTEGER = "numerical_integer"
    NUMERICAL_DECIMAL = "numerical_decimal"
    ASSERTION_REASON = "assertion_reason"


class Identity(BaseModel):
    problem_id: str
    parent_id: Optional[str] = None
    family_id: Optional[str] = None
    lineage: list[str] = Field(default_factory=list)  # operator ids applied, in order
    version: int = 1


class Knowledge(BaseModel):
    chapter: str = ""
    topic: str = ""
    subtopics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    source_documents: list[str] = Field(default_factory=list)
    pyq_ids: list[str] = Field(default_factory=list)
    rights_status: Literal["CLEARED", "TEACHER_OWNED", "GENERATED", "UNKNOWN", "RESTRICTED"] = "UNKNOWN"
    permitted_uses: list[str] = Field(default_factory=list)
    extraction_confidence: Optional[float] = None
    source_answer_key: Optional[str] = None  # a CLAIM, never ground truth


class Option(BaseModel):
    option_id: str
    value: str  # canonical machine-readable value (sympy expr, set literal, number, statement id)
    display: str = ""


class Distractor(BaseModel):
    """Blueprint section 11: every wrong option has an executable origin."""
    option_id: str
    value: str
    misconception_id: str
    error_operation: str
    derivation_trace: list[str]
    why_students_make_this_error: str
    why_it_is_wrong: str
    verified_wrong: bool = False
    teacher_approval: Optional[str] = None


class Answer(BaseModel):
    exact_answer: Optional[str] = None
    units: Optional[str] = None
    correct_option_ids: list[str] = Field(default_factory=list)
    accepted_forms: list[str] = Field(default_factory=list)


class ProblemState(BaseModel):
    identity: Identity
    subject: Subject
    exam_profile_id: str  # e.g. "JEE_MAIN-2027-v1"
    question_format: QuestionFormat
    knowledge: Knowledge = Field(default_factory=Knowledge)
    # Subject-specific formal problem; validated by the subject engine.
    formal: dict[str, Any]
    invariants: list[str] = Field(default_factory=list)
    stem: str = ""
    diagram_svg: str = ""  # rendered FROM the formal state; part of the approved content
    options: list[Option] = Field(default_factory=list)
    answer: Answer = Field(default_factory=Answer)
    distractors: list[Distractor] = Field(default_factory=list)
    solution_steps: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="after")
    def _structural(self) -> "ProblemState":
        if "kind" not in self.formal:
            raise ValueError("formal problem must declare a 'kind'")
        ids = [o.option_id for o in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate option ids")
        mcq = {QuestionFormat.SINGLE_CORRECT_MCQ, QuestionFormat.MULTIPLE_CORRECT_MCQ,
               QuestionFormat.ASSERTION_REASON}
        if self.question_format in mcq and self.options and len(self.options) < 2:
            raise ValueError("MCQ needs at least two options")
        return self

    def student_view(self) -> dict[str, Any]:
        """What a learner sees: answer and traces removed."""
        return {"stem": self.stem,
                "options": [{"id": o.option_id, "text": o.display or o.value} for o in self.options],
                "format": self.question_format.value}

    def release_payload(self) -> dict[str, Any]:
        """Fields whose change must invalidate approval (stem, options, key, formal...)."""
        return self.model_dump(mode="json", include={
            "subject", "exam_profile_id", "question_format", "formal", "stem", "diagram_svg",
            "options", "answer", "distractors", "solution_steps"})
