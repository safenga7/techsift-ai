"""
TechSift AI - Document Repository.
Data access layer for Document entities using SQLAlchemy 2.0 AsyncSession.
"""

from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.document import Document


class DocumentRepository:
    """Encapsulates database operations for Document entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, document: Document) -> Document:
        """Persist a new document record."""
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """Fetch a document by its primary key UUID."""
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_content_hash(self, content_hash: str) -> Optional[Document]:
        """Fetch an existing document with matching SHA-256 hash."""
        stmt = select(Document).where(Document.content_hash == content_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[Document], int]:
        """
        List documents with pagination and optional status filter.
        Returns a tuple of (items, total_count).
        """
        query = select(Document)
        count_query = select(func.count(Document.id))

        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)

        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Get paginated items
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        items_result = await self.db.execute(query)
        items = list(items_result.scalars().all())

        return items, total

    async def delete(self, document: Document) -> None:
        """Delete document record from database."""
        await self.db.delete(document)
        await self.db.flush()

    async def update(self, document: Document) -> Document:
        """Update and refresh existing document."""
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_stats(self) -> dict:
        """
        Computes document totals and status breakdown across the entire collection,
        independently of pagination.
        """
        stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
        result = await self.db.execute(stmt)
        counts = dict(result.all())

        total_docs = sum(counts.values())
        processed = counts.get("processed", 0)
        pending = counts.get("pending", 0)
        failed = counts.get("failed", 0)
        unsupported = counts.get("unsupported", 0)
        issues = failed + unsupported

        return {
            "total_documents": total_docs,
            "processed_documents": processed,
            "pending_documents": pending,
            "failed_documents": failed,
            "unsupported_documents": unsupported,
            "issues_documents": issues,
        }

