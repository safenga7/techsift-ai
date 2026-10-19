"""
TechSift AI - Learning Progress Repository (Phase 5C).
Data access layer for LessonProgress and PathProgress models.
Manages atomic updates, SQLite persistence, and session continuity.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning_progress import LessonProgress, PathProgress


class LearningProgressRepository:
    """Provides asynchronous CRUD and query operations for learning progress."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lesson_progress(
        self,
        learning_path_id: str,
        lesson_id: str,
    ) -> Optional[LessonProgress]:
        """Fetch existing progress record for a specific lesson."""
        stmt = select(LessonProgress).where(
            LessonProgress.learning_path_id == learning_path_id,
            LessonProgress.lesson_id == lesson_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_lesson_progress(
        self,
        learning_path_id: str,
        lesson_id: str,
    ) -> LessonProgress:
        """Fetch or initialize a default progress record for a lesson."""
        existing = await self.get_lesson_progress(learning_path_id, lesson_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        record = LessonProgress(
            learning_path_id=learning_path_id,
            lesson_id=lesson_id,
            status="not_started",
            last_accessed_at=now,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_lesson_progress_for_path(
        self,
        learning_path_id: str,
    ) -> List[LessonProgress]:
        """Fetch all lesson progress records for a curriculum."""
        stmt = (
            select(LessonProgress)
            .where(LessonProgress.learning_path_id == learning_path_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_path_progress(
        self,
        learning_path_id: str,
    ) -> Optional[PathProgress]:
        """Fetch curriculum-level session continuity record."""
        stmt = select(PathProgress).where(
            PathProgress.learning_path_id == learning_path_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_path_progress(
        self,
        learning_path_id: str,
    ) -> PathProgress:
        """Fetch or initialize a session continuity record for a path."""
        existing = await self.get_path_progress(learning_path_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        record = PathProgress(
            learning_path_id=learning_path_id,
            last_accessed_at=now,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def update_last_visited(
        self,
        learning_path_id: str,
        lesson_id: str,
    ) -> PathProgress:
        """Update last visited lesson and timestamp for resume continuity."""
        record = await self.get_or_create_path_progress(learning_path_id)
        record.last_visited_lesson_id = lesson_id
        record.last_accessed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return record
