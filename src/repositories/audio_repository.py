"""
TechSift AI - Audio Repository.
Encapsulates SQLite database operations for AudioTrack persistence and cache lookups.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audio_track import AudioTrack


class AudioRepository:
    """Handles database transactions for AudioTrack entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, track: AudioTrack) -> AudioTrack:
        """Persists a new audio track entity."""
        self.db.add(track)
        await self.db.commit()
        await self.db.refresh(track)
        return track

    async def get_by_id(self, track_id: str) -> Optional[AudioTrack]:
        """Retrieves an audio track by its primary UUID."""
        stmt = select(AudioTrack).where(AudioTrack.id == track_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_config_hash(self, config_hash: str) -> Optional[AudioTrack]:
        """
        Retrieves a completed audio track matching the configuration fingerprint.
        Used for zero-cost caching.
        """
        stmt = (
            select(AudioTrack)
            .where(
                AudioTrack.config_hash == config_hash,
                AudioTrack.status == "completed",
            )
            .order_by(AudioTrack.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_pending_or_processing_by_hash(self, config_hash: str) -> Optional[AudioTrack]:
        """Finds any currently running track with the same config hash to prevent duplicates."""
        stmt = (
            select(AudioTrack)
            .where(
                AudioTrack.config_hash == config_hash,
                AudioTrack.status.in_(["pending", "processing"]),
            )
            .order_by(AudioTrack.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_document_id(self, document_id: str) -> List[AudioTrack]:
        """Retrieves all audio tracks for a given document ordered by recency."""
        stmt = (
            select(AudioTrack)
            .where(AudioTrack.document_id == document_id)
            .order_by(AudioTrack.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, track: AudioTrack) -> AudioTrack:
        """Updates and flushes audio track changes."""
        await self.db.commit()
        await self.db.refresh(track)
        return track

    async def delete(self, track: AudioTrack) -> None:
        """Removes an audio track record."""
        await self.db.delete(track)
        await self.db.commit()
