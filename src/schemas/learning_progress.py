"""
TechSift AI - Learning Progress & Dashboard Schemas (Phase 5C).
Defines request and response schemas for progress tracking, knowledge mastery,
rule-based learning recommendations, and session continuity.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LessonProgressStatusEnum(str, Enum):
    """Status lifecycle for an individual instructional lesson."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class UpdateLessonProgressRequest(BaseModel):
    """Payload to update reading / completion state of a lesson."""
    status: LessonProgressStatusEnum = Field(
        default=LessonProgressStatusEnum.IN_PROGRESS,
        description="Target status: 'in_progress' or 'completed'",
    )


# ---------------------------------------------------------------------------
# Progress Response Schemas
# ---------------------------------------------------------------------------


class LessonProgressResponse(BaseModel):
    """Individual lesson progress record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    learning_path_id: str
    lesson_id: str
    status: LessonProgressStatusEnum
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_accessed_at: datetime
    created_at: datetime
    updated_at: datetime


class LessonProgressSummaryItem(BaseModel):
    """Lesson progress metadata embedded within curriculum hierarchies."""
    lesson_id: str
    module_id: str
    sequence_order: int
    title: str
    status: LessonProgressStatusEnum
    completed: bool
    last_accessed_at: Optional[datetime] = None
    has_quiz: bool = False
    quiz_passed: bool = False
    quiz_score: Optional[float] = None
    quiz_attempts_count: int = 0


class ModuleProgressItem(BaseModel):
    """Calculated progress indicators for a single module."""
    module_id: str
    sequence_order: int
    title: str
    total_lessons: int
    completed_lessons: int
    completion_percentage: float
    is_completed: bool
    has_assessment: bool = False
    assessment_passed: bool = False
    assessment_score: Optional[float] = None
    assessment_attempts_count: int = 0
    lessons: List[LessonProgressSummaryItem] = []


class PathProgressOverviewResponse(BaseModel):
    """Comprehensive progress metrics for an entire learning path."""
    learning_path_id: str
    total_lessons: int
    completed_lessons: int
    remaining_lessons: int
    overall_completion_percentage: float
    is_curriculum_completed: bool
    final_assessment_passed: bool
    final_assessment_score: Optional[float] = None
    last_visited_lesson_id: Optional[str] = None
    last_accessed_at: Optional[datetime] = None
    modules: List[ModuleProgressItem] = []


# ---------------------------------------------------------------------------
# Assessment Performance & History Schemas
# ---------------------------------------------------------------------------


class AssessmentStatItem(BaseModel):
    """Performance statistics for an individual assessment."""
    assessment_id: str
    title: str
    assessment_type: str
    module_id: Optional[str] = None
    lesson_id: Optional[str] = None
    attempts_count: int
    latest_score: Optional[int] = None
    latest_percentage: Optional[float] = None
    best_percentage: Optional[float] = None
    passed: bool
    passing_threshold: float
    last_attempt_at: Optional[datetime] = None


class AssessmentOverviewStats(BaseModel):
    """Aggregated assessment metrics across a learning path."""
    total_assessments: int
    attempted_assessments: int
    passed_assessments: int
    failed_assessments: int
    pass_rate: float
    average_score: float
    recent_assessments: List[AssessmentStatItem] = []


# ---------------------------------------------------------------------------
# Knowledge Mastery Schemas
# ---------------------------------------------------------------------------


class ConceptMasteryItem(BaseModel):
    """Evidence-grounded technical concept mastery indicator."""
    term: str
    explanation: str
    lesson_id: str
    lesson_title: str
    module_id: str
    status: str  # "mastered", "proficient", "needs_review", "not_assessed"
    accuracy_percentage: Optional[float] = None
    evidence: str


class MissedQuestionItem(BaseModel):
    """Frequently missed assessment question with failure rate."""
    question_id: str
    question_text: str
    assessment_type: str
    total_answers: int
    incorrect_count: int
    failure_rate: float
    lesson_title: Optional[str] = None


class LessonMasteryPerformance(BaseModel):
    """Performance summary at the lesson level."""
    lesson_id: str
    lesson_title: str
    module_id: str
    status: str  # "mastered", "proficient", "needs_review", "not_assessed"
    best_percentage: Optional[float] = None
    attempts_count: int = 0
    lesson_completed: bool = False


class KnowledgeMasteryResponse(BaseModel):
    """Deterministic knowledge mastery report."""
    learning_path_id: str
    strong_concepts: List[ConceptMasteryItem] = []
    concepts_needing_review: List[ConceptMasteryItem] = []
    frequently_missed_questions: List[MissedQuestionItem] = []
    lessons_performance: List[LessonMasteryPerformance] = []


# ---------------------------------------------------------------------------
# Personalized Recommendations & Continuity
# ---------------------------------------------------------------------------


class LearningRecommendationItem(BaseModel):
    """Explainable rule-based pedagogical recommendation."""
    id: str
    type: str  # "continue_lesson", "review_lesson", "retake_assessment", "take_module_assessment", "take_final_assessment", "curriculum_mastered"
    title: str
    description: str
    target_id: Optional[str] = None
    priority: int  # 1 (highest) to 5 (lowest)


class LearningRecommendationsResponse(BaseModel):
    """Prioritized pedagogical recommendations list."""
    learning_path_id: str
    items: List[LearningRecommendationItem] = []


class ResumeLearningResponse(BaseModel):
    """Target lesson and module for seamless 'Resume Learning' continuity."""
    learning_path_id: str
    lesson_id: str
    lesson_title: str
    module_id: str
    module_title: str
    module_sequence: int
    lesson_sequence: int
    status: LessonProgressStatusEnum
    reason: str


# ---------------------------------------------------------------------------
# Consolidated Dashboard Schema
# ---------------------------------------------------------------------------


class LearningDashboardResponse(BaseModel):
    """Unified Learning Progress & Dashboard response for Phase 5C."""
    learning_path_id: str
    path_title: str
    difficulty: str
    language: str
    progress: PathProgressOverviewResponse
    assessments_overview: AssessmentOverviewStats
    knowledge_mastery: KnowledgeMasteryResponse
    recommendations: List[LearningRecommendationItem] = []
    resume_target: Optional[ResumeLearningResponse] = None
