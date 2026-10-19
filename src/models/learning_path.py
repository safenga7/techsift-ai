"""
TechSift AI - Learning Path, Module, and Lesson SQLAlchemy Models (Phase 5A).
Defines structured, source-grounded educational curricula derived from technical documents.
"""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

if TYPE_CHECKING:
    from src.models.assessment import Assessment
    from src.models.document import Document
    from src.models.learning_progress import LessonProgress, PathProgress


class LearningPath(Base):
    """
    Root educational curriculum for a technical document.
    Configured by language and difficulty level with SQLite caching.
    """

    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(5), nullable=False)  # "en" or "ar"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "beginner", "intermediate", "advanced"
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending", "processing", "completed", "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    prerequisites: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    learning_objectives: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

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
    document: Mapped["Document"] = relationship("Document", back_populates="learning_paths")
    modules: Mapped[List["LearningModule"]] = relationship(
        "LearningModule",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        order_by="LearningModule.sequence_order",
    )
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="learning_path",
        cascade="all, delete-orphan",
    )
    lesson_progress_records: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    path_progress: Mapped[Optional["PathProgress"]] = relationship(
        "PathProgress",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class LearningModule(Base):
    """
    Sequential conceptual unit within a Learning Path.
    """

    __tablename__ = "learning_modules"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    learning_objectives: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    learning_path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="modules")
    lessons: Mapped[List["LearningLesson"]] = relationship(
        "LearningLesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="LearningLesson.sequence_order",
    )
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="module",
        cascade="all, delete-orphan",
    )


class LearningLesson(Base):
    """
    Granular, source-grounded instructional lesson containing explanations,
    key concepts, examples, and document citations.
    """

    __tablename__ = "learning_lessons"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    module_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    key_concepts: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    examples: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    source_references: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    module: Mapped["LearningModule"] = relationship("LearningModule", back_populates="lessons")
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    progress: Mapped[Optional["LessonProgress"]] = relationship(
        "LessonProgress",
        back_populates="lesson",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
