"""
TechSift AI - Assessment, Question, Attempt, and Answer SQLAlchemy Models (Phase 5B).
Defines source-grounded interactive quizzes, module assessments, and final assessments
with deterministic server-side grading and answer confidentiality safeguards.
"""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

if TYPE_CHECKING:
    from src.models.learning_path import LearningLesson, LearningModule, LearningPath


class Assessment(Base):
    """
    Evaluation assessment (lesson quiz, module assessment, or final comprehensive exam).
    Supports SQLite caching, in-flight deduplication, and zero-cost local grading.
    """

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    learning_path_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("learning_modules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("learning_lessons.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assessment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # "lesson_quiz", "module_assessment", "final_assessment"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False)  # "en" or "ar"
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "beginner", "intermediate", "advanced"
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending", "processing", "completed", "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    passing_threshold: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    learning_path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="assessments")
    module: Mapped[Optional["LearningModule"]] = relationship("LearningModule", back_populates="assessments")
    lesson: Mapped[Optional["LearningLesson"]] = relationship("LearningLesson", back_populates="assessments")
    questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.sequence_order",
        lazy="selectin",
    )
    attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentAttempt.started_at.desc()",
        lazy="selectin",
    )


class AssessmentQuestion(Base):
    """
    Multiple-choice question with exactly 4 options, 1 correct answer,
    and grounded citations to document chunks.
    """

    __tablename__ = "assessment_questions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(30),
        default="multiple_choice",
        nullable=False,
    )
    answer_options: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # Exactly 4 strings
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_references: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="questions")
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AssessmentAttempt(Base):
    """
    User attempt to take an assessment.
    Tracks progression, score, percentage, and pass/fail determination.
    """

    __tablename__ = "assessment_attempts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="in_progress",
        nullable=False,
        index=True,
    )  # "in_progress", "completed", "abandoned"
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="attempts")
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AssessmentAnswer(Base):
    """
    Individual answer submitted for a question during an attempt.
    Includes server-evaluated correctness and explanation feedback.
    """

    __tablename__ = "assessment_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    attempt: Mapped["AssessmentAttempt"] = relationship("AssessmentAttempt", back_populates="answers")
    question: Mapped["AssessmentQuestion"] = relationship("AssessmentQuestion", back_populates="answers")
