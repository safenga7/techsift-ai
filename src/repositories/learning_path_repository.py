"""
TechSift AI - Learning Path Repository (Phase 5A).
Data access layer for LearningPath, LearningModule, and LearningLesson entities
with SQLite caching and eager relationship loading.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models.learning_path import LearningLesson, LearningModule, LearningPath


class LearningPathRepository:
    """Manages persistence, caching, and retrieval of structured learning curricula."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, path: LearningPath) -> LearningPath:
        """Persist a new learning path and cascade modules/lessons."""
        self.db.add(path)
        await self.db.flush()
        return await self.get_by_id(path.id)  # Returns with loaded relationships

    async def get_by_id(self, path_id: str) -> Optional[LearningPath]:
        """Fetch learning path by UUID with eager loaded modules and lessons."""
        stmt = (
            select(LearningPath)
            .where(LearningPath.id == path_id)
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.lessons)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_document_id(self, document_id: str) -> List[LearningPath]:
        """List all learning paths generated for a document ordered by newest first."""
        stmt = (
            select(LearningPath)
            .where(LearningPath.document_id == document_id)
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.lessons)
            )
            .order_by(LearningPath.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_cached_path(
        self,
        document_id: str,
        language: str,
        difficulty: str,
    ) -> Optional[LearningPath]:
        """
        Locates a cached completed learning path matching document, language, and difficulty.
        Returns None if not found, allowing zero-cost cache hits with 0 new API calls.
        """
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.document_id == document_id,
                LearningPath.language == language,
                LearningPath.difficulty == difficulty,
                LearningPath.status == "completed",
            )
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.lessons)
            )
            .order_by(LearningPath.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_in_flight_path(
        self,
        document_id: str,
        language: str,
        difficulty: str,
    ) -> Optional[LearningPath]:
        """
        Locates any pending or processing learning path matching parameters to prevent duplicate concurrent runs.
        """
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.document_id == document_id,
                LearningPath.language == language,
                LearningPath.difficulty == difficulty,
                LearningPath.status.in_(["pending", "processing"]),
            )
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.lessons)
            )
            .order_by(LearningPath.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, path: LearningPath) -> LearningPath:
        """Update and refresh existing learning path."""
        await self.db.flush()
        return await self.get_by_id(path.id)

    async def delete(self, path: LearningPath) -> None:
        """Delete learning path record (cascades to modules and lessons)."""
        await self.db.delete(path)
        await self.db.flush()
