"""
TechSift AI - Pydantic Schemas for Interactive Quizzes & Assessments (Phase 5B).
Enforces strict answer option validation, distinct choices, single correct answer,
and strict answer key confidentiality before submission.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssessmentTypeEnum(str, Enum):
    LESSON_QUIZ = "lesson_quiz"
    MODULE_ASSESSMENT = "module_assessment"
    FINAL_ASSESSMENT = "final_assessment"


class QuestionTypeEnum(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"


class AttemptStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SourceReference(BaseModel):
    """Source grounding reference indicating chunk index, page, and excerpt."""

    model_config = ConfigDict(extra="ignore")

    page_number: Optional[int] = Field(None, description="PDF page number if available (1-indexed)")
    chunk_index: Optional[int] = Field(None, description="Database chunk index")
    section_title: Optional[str] = Field(None, description="Section heading in source document")
    citation_text: Optional[str] = Field(None, description="Short supporting excerpt from the text")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            normalized = dict(data)
            if "section_title" not in normalized and "section" in normalized:
                normalized["section_title"] = normalized["section"]
            if "chunk_index" not in normalized and "chunk" in normalized:
                val = normalized["chunk"]
                if isinstance(val, int):
                    normalized["chunk_index"] = val
                elif isinstance(val, str):
                    m = re.search(r"\d+", val)
                    if m:
                        normalized["chunk_index"] = int(m.group(0))
            if "citation_text" not in normalized and "citation" in normalized:
                normalized["citation_text"] = normalized["citation"]
            return normalized
        return data


class GeneratedAssessmentQuestion(BaseModel):
    """AI-generated question item with strict 4-option validation."""

    model_config = ConfigDict(extra="ignore")

    question_text: str = Field(..., min_length=5, description="The test question prompt")
    question_type: QuestionTypeEnum = Field(
        default=QuestionTypeEnum.MULTIPLE_CHOICE,
        description="Format of the question",
    )
    answer_options: List[str] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exactly 4 distinct plausible answer choices",
    )
    correct_answer: str = Field(
        ...,
        min_length=1,
        description="The exact text of the single correct answer option",
    )
    explanation: str = Field(
        ...,
        min_length=10,
        description="Detailed pedagogical explanation of why the correct answer is right",
    )
    source_references: List[SourceReference] = Field(
        default_factory=list,
        description="Citations to document pages/chunks grounding this question",
    )
    sequence_order: int = Field(default=1, ge=1, description="Question sequence order")

    @field_validator("answer_options")
    @classmethod
    def validate_answer_options(cls, options: List[str]) -> List[str]:
        cleaned = [opt.strip() for opt in options if opt.strip()]
        if len(cleaned) != 4:
            raise ValueError(f"Each question must contain exactly 4 non-empty answer options (found {len(cleaned)}).")
        # Ensure choices are unique
        if len(set(cleaned)) != 4:
            raise ValueError("All 4 answer options must be unique and distinct.")
        return cleaned

    @model_validator(mode="after")
    def validate_correct_answer_in_options(self) -> "GeneratedAssessmentQuestion":
        options = [opt.strip() for opt in self.answer_options]
        correct = self.correct_answer.strip()
        if correct not in options:
            # Check for case-insensitive or close match
            matched = next((opt for opt in options if opt.lower() == correct.lower()), None)
            if matched:
                self.correct_answer = matched
            else:
                raise ValueError(
                    f"Correct answer '{self.correct_answer}' must exactly match one of the 4 answer options: {options}"
                )
        else:
            self.correct_answer = correct
        return self


class GeneratedAssessmentContent(BaseModel):
    """Container for AI-generated assessment questions."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=3, description="Descriptive assessment title")
    description: Optional[str] = Field(None, description="Overview of topics evaluated")
    questions: List[GeneratedAssessmentQuestion] = Field(
        ...,
        min_length=1,
        description="List of verified, source-grounded multiple-choice questions",
    )


# ---------------------------------------------------------------------------
# API Request Schemas
# ---------------------------------------------------------------------------


class CreateAssessmentRequest(BaseModel):
    """Payload to initiate interactive assessment generation."""

    assessment_type: AssessmentTypeEnum = Field(
        default=AssessmentTypeEnum.LESSON_QUIZ,
        description="Scope of assessment: 'lesson_quiz', 'module_assessment', or 'final_assessment'",
    )
    module_id: Optional[str] = Field(
        None,
        description="Required if assessment_type is 'module_assessment'",
    )
    lesson_id: Optional[str] = Field(
        None,
        description="Required if assessment_type is 'lesson_quiz'",
    )
    question_count: Optional[int] = Field(
        None,
        ge=1,
        le=25,
        description="Optional custom question count (default: lesson=5, module=10, final=15)",
    )
    wait: bool = Field(
        True,
        description="Wait for generation synchronously (True) or process in background (False)",
    )


class SubmitAnswerRequest(BaseModel):
    """Payload to record an answer to an assessment question."""

    question_id: str = Field(..., description="UUID of the question being answered")
    selected_answer: str = Field(..., min_length=1, description="Selected answer string matching an option")


# ---------------------------------------------------------------------------
# API Response Schemas
# ---------------------------------------------------------------------------


class QuestionForTaker(BaseModel):
    """
    Public question schema delivered to student taking an active assessment.
    CRITICAL SECURITY GUARANTEE: Does NOT contain correct_answer or explanation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    question_text: str
    question_type: str
    answer_options: List[str]
    sequence_order: int


class AssessmentResponse(BaseModel):
    """Summary metadata for an assessment."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    learning_path_id: str
    module_id: Optional[str] = None
    lesson_id: Optional[str] = None
    assessment_type: AssessmentTypeEnum
    title: str
    description: Optional[str] = None
    language: str
    difficulty: str
    status: str
    error_message: Optional[str] = None
    passing_threshold: float = 70.0
    questions_count: int = 0
    is_cached: bool = False
    created_at: datetime
    updated_at: datetime


class AssessmentDetailResponse(AssessmentResponse):
    """Full assessment payload with confidential questions for taker."""

    questions: List[QuestionForTaker] = []


class AssessmentListResponse(BaseModel):
    """Paginated or filtered list of assessments."""

    items: List[AssessmentResponse]
    total: int


class AssessmentAttemptResponse(BaseModel):
    """Attempt tracking response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    status: AttemptStatusEnum
    score: int = 0
    max_score: int = 0
    percentage: float = 0.0
    passed: bool = False
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime


class AnswerRecordResponse(BaseModel):
    """Confirmation that an answer was accepted and saved."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    attempt_id: str
    question_id: str
    selected_answer: str
    created_at: datetime


class AnswerReviewItem(BaseModel):
    """Post-submission evaluation item revealing correctness and explanation."""

    question_id: str
    question_text: str
    answer_options: List[str]
    selected_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    explanation: str
    source_references: Optional[List[SourceReference]] = None


class AttemptResultResponse(BaseModel):
    """Final graded result of an assessment attempt with full pedagogical review."""

    attempt_id: str
    assessment_id: str
    assessment_title: str
    status: AttemptStatusEnum
    score: int
    max_score: int
    percentage: float
    passed: bool
    passing_threshold: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    answers: List[AnswerReviewItem] = []
