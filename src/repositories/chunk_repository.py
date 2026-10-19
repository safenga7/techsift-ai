"""
TechSift AI - DocumentChunk Repository.
Data access layer for document text chunks and page references.
"""

from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.document_chunk import DocumentChunk


class ChunkRepository:
    """Manages persistence and retrieval of document chunks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Bulk-add and persist document chunks."""
        self.db.add_all(chunks)
        await self.db.flush()
        return chunks

    async def get_chunks_by_document_id(self, document_id: str) -> List[DocumentChunk]:
        """Fetch all chunks for a document ordered by chunk_index."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # Convenience alias
    get_by_document_id = get_chunks_by_document_id

    async def delete_chunks_by_document_id(self, document_id: str) -> None:
        """Purge all chunks associated with a document."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        await self.db.execute(stmt)
        await self.db.flush()
