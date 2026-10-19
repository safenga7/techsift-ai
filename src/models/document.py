"""
TechSift AI - Document SQLAlchemy Model.
"""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

if TYPE_CHECKING:
    from src.models.processing_job import ProcessingJob
    from src.models.document_chunk import DocumentChunk
    from src.models.summary import Summary
    from src.models.audio_track import AudioTrack
    from src.models.learning_path import LearningPath


class Document(Base):
    """Represents an uploaded technical document."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf, txt, md
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending, processed, failed, unsupported
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProcessingJob.created_at.desc()",
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )
    summaries: Mapped[List["Summary"]] = relationship(
        "Summary",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Summary.created_at.desc()",
    )
    audio_tracks: Mapped[List["AudioTrack"]] = relationship(
        "AudioTrack",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="AudioTrack.created_at.desc()",
    )
    learning_paths: Mapped[List["LearningPath"]] = relationship(
        "LearningPath",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="LearningPath.created_at.desc()",
    )
