"""
TechSift AI - Learning Progress & Continuity SQLAlchemy Models (Phase 5C).
Tracks lesson completion status, path progression, last visited lessons,
and session continuity in local SQLite without external dependencies.
"""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

if TYPE_CHECKING:
    from src.models.learning_path import LearningLesson, LearningPath


class LessonProgress(Base):
    """
    Granular progress state for an individual lesson.
    Distinguishes reading/completion from assessment passing.
    Guarantees idempotency and prevents completed lessons from reverting to in_progress.
    """

    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("learning_path_id", "lesson_id", name="uq_path_lesson_progress"),
    )

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
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="not_started",
        nullable=False,
        index=True,
    )  # "not_started", "in_progress", "completed"

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
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
    learning_path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="lesson_progress_records")
    lesson: Mapped["LearningLesson"] = relationship("LearningLesson", back_populates="progress")


class PathProgress(Base):
    """
    Curriculum-level session continuity tracking.
    Maintains the pointer to the last visited lesson for one-click 'Resume Learning'.
    Aggregates are calculated dynamically from LessonProgress and AssessmentAttempt.
    """

    __tablename__ = "path_progress"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    learning_path_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    last_visited_lesson_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("learning_lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
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
    learning_path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="path_progress")
    last_visited_lesson: Mapped[Optional["LearningLesson"]] = relationship("LearningLesson")
