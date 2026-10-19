"""
TechSift AI - AudioTrack SQLAlchemy Model.
Stores audio narrations and dual-speaker podcast episodes with configuration fingerprint caching.
"""

from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.summary import Summary


class AudioTrack(Base):
    """Represents a generated or cached audio narration or podcast dialogue."""

    __tablename__ = "audio_tracks"

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
    summary_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # "narration" or "podcast"
    language: Mapped[str] = mapped_column(String(5), nullable=False)  # "ar" or "en"
    voice_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    script_content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending", "processing", "completed", "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # SHA-256 fingerprint of (document_id, summary_id, mode, language, voice_config)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

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
    document: Mapped["Document"] = relationship("Document", back_populates="audio_tracks")
    summary: Mapped[Optional["Summary"]] = relationship("Summary")
