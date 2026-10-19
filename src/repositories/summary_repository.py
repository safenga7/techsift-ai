"""
TechSift AI - Summary Repository.
Data access layer for bilingual summaries with SQLite caching support.
"""

from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.summary import Summary


class SummaryRepository:
    """Manages persistence, retrieval, and caching of document summaries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, summary: Summary) -> Summary:
        """Persist a new summary."""
        self.db.add(summary)
        await self.db.flush()
        await self.db.refresh(summary)
        return summary

    async def get_by_id(self, summary_id: str) -> Optional[Summary]:
        """Fetch summary by primary key UUID."""
        stmt = select(Summary).where(Summary.id == summary_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_document_id(self, document_id: str) -> List[Summary]:
        """List all summaries generated for a document ordered by newest first."""
        stmt = (
            select(Summary)
            .where(Summary.document_id == document_id)
            .order_by(Summary.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_cached_summary(
        self,
        document_id: str,
        language: str,
        detail_level: str,
        model_used: str,
    ) -> Optional[Summary]:
        """
        Locates a cached completed summary matching document, language, detail level, and model.
        Returns None if not found, allowing zero-cost cache hits without repeated LLM calls.
        """
        stmt = (
            select(Summary)
            .where(
                Summary.document_id == document_id,
                Summary.language == language,
                Summary.detail_level == detail_level,
                Summary.model_used == model_used,
                Summary.status == "completed",
            )
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_in_flight_summary(
        self,
        document_id: str,
        language: str,
        detail_level: str,
        model_used: str,
    ) -> Optional[Summary]:
        """
        Locates any pending or processing summary matching parameters to prevent duplicate concurrent runs.
        """
        stmt = (
            select(Summary)
            .where(
                Summary.document_id == document_id,
                Summary.language == language,
                Summary.detail_level == detail_level,
                Summary.model_used == model_used,
                Summary.status.in_(["pending", "processing"]),
            )
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, summary: Summary) -> Summary:
        """Update and refresh existing summary."""
        await self.db.flush()
        await self.db.refresh(summary)
        return summary

    async def count_completed(self) -> int:
        """Count all completed summaries across the collection."""
        stmt = select(func.count(Summary.id)).where(Summary.status == "completed")
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0

