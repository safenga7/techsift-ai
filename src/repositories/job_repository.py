"""
TechSift AI - ProcessingJob Repository.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.processing_job import ProcessingJob


class JobRepository:
    """Encapsulates database operations for ProcessingJob entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job: ProcessingJob) -> ProcessingJob:
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_document_id(self, document_id: str) -> List[ProcessingJob]:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, job: ProcessingJob) -> ProcessingJob:
        await self.db.flush()
        await self.db.refresh(job)
        return job
