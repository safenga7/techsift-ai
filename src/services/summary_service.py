"""
TechSift AI - Summary Business Service.
Coordinates chunk verification, SQLite caching, background summarization, and retrieval.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.exceptions import (
    AITimeoutError,
    NotFoundError,
    RateLimitExceededError,
    UnsupportedDocumentError,
)
from src.db.session import async_session_maker
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.summary_repository import SummaryRepository
from src.schemas.summary import (
    DetailLevelEnum,
    LanguageEnum,
    SummaryListResponse,
    SummaryResponse,
    TechnicalSummaryContent,
)
from src.services.chunker_service import chunker_service
from src.services.storage_service import storage_service
from src.services.summarizer_service import SummarizerService

logger = logging.getLogger(__name__)


class SummaryService:
    """Manages document summarization workflows and SQLite caching."""

    def __init__(
        self,
        db: AsyncSession,
        summarizer: Optional[SummarizerService] = None,
    ):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.job_repo = JobRepository(db)
        self.summarizer = summarizer or SummarizerService()

    async def _ensure_document_chunks(self, document) -> list:
        """Ensures chunks are generated and stored in SQLite for the document."""
        existing_chunks = await self.chunk_repo.get_chunks_by_document_id(document.id)
        if existing_chunks:
            return existing_chunks

        # Generate chunks
        if document.file_type == "pdf":
            pdf_bytes = storage_service.read_file(document.storage_filename)
            chunk_data_list = chunker_service.chunk_pdf(pdf_bytes)
        else:
            text = document.extracted_text or ""
            chunk_data_list = chunker_service.chunk_text(
                text,
                is_markdown=(document.file_type == "md"),
            )

        if not chunk_data_list and document.extracted_text:
            # Fallback single chunk
            from src.services.chunker_service import ChunkData
            chunk_data_list = [
                ChunkData(
                    chunk_index=0,
                    content=document.extracted_text,
                    page_number=1 if document.file_type == "pdf" else None,
                    section_title="Full Content",
                    start_char=0,
                    end_char=len(document.extracted_text),
                )
            ]

        orm_chunks = chunker_service.to_orm_chunks(document.id, chunk_data_list)
        persisted_chunks = await self.chunk_repo.create_chunks(orm_chunks)
        return persisted_chunks

    async def generate_summary(
        self,
        document_id: str,
        language: LanguageEnum = LanguageEnum.EN,
        detail_level: DetailLevelEnum = DetailLevelEnum.STANDARD,
        wait: bool = True,
    ) -> SummaryResponse:
        """
        Generates or retrieves a cached summary for a document.
        If a completed summary exists for the exact parameters, returns the cached
        result with zero LLM API consumption.
        """
        # 1. Fetch document
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(resource="Document", identifier=document_id)

        if doc.status in ("unsupported", "failed"):
            raise UnsupportedDocumentError(
                f"Cannot summarize document with status '{doc.status}': "
                f"{doc.error_message or 'Text extraction failed or was unsupported.'}"
            )

        model_name = settings.GEMINI_MODEL

        # 2. Check SQLite cache (Zero-cost optimization)
        cached = await self.summary_repo.find_cached_summary(
            document_id=doc.id,
            language=language.value,
            detail_level=detail_level.value,
            model_used=model_name,
        )
        if cached:
            logger.info(f"Summary cache HIT for doc {doc.id} [{language.value}/{detail_level.value}].")
            return SummaryResponse.from_orm_model(cached, is_cached=True)

        # 3. Check for in-flight summary to prevent duplicate concurrent LLM jobs
        in_flight = await self.summary_repo.find_in_flight_summary(
            document_id=doc.id,
            language=language.value,
            detail_level=detail_level.value,
            model_used=model_name,
        )
        if in_flight:
            logger.info(f"Duplicate summary request: returning in-flight summary {in_flight.id}")
            return SummaryResponse.from_orm_model(in_flight, is_cached=False)

        # 4. Ensure chunks exist in database
        chunks = await self._ensure_document_chunks(doc)

        # 5. Create pending summary and processing job
        summary = Summary(
            document_id=doc.id,
            language=language.value,
            detail_level=detail_level.value,
            model_used=model_name,
            status="pending",
        )
        created_summary = await self.summary_repo.create(summary)

        job = ProcessingJob(
            document_id=doc.id,
            job_type=f"summary_{language.value}_{detail_level.value}",
            status="in_progress",
        )
        await self.job_repo.create(job)
        await self.db.commit()

        if wait:
            # Synchronous non-blocking execution using request session
            return await self._execute_summarization_job(
                summary_id=created_summary.id,
                chunks=chunks,
                language=language,
                detail_level=detail_level,
                job_id=job.id,
            )
        else:
            # Asynchronous background execution using dedicated isolated session
            asyncio.create_task(
                self._run_background_summary_task(
                    summary_id=created_summary.id,
                    language=language,
                    detail_level=detail_level,
                    job_id=job.id,
                )
            )
            return SummaryResponse.from_orm_model(created_summary, is_cached=False)

    async def _run_background_summary_task(
        self,
        summary_id: str,
        language: LanguageEnum,
        detail_level: DetailLevelEnum,
        job_id: Optional[str] = None,
    ) -> None:
        """Executes summarization in an isolated background database session."""
        try:
            async with async_session_maker() as session:
                summary_repo = SummaryRepository(session)
                chunk_repo = ChunkRepository(session)
                job_repo = JobRepository(session)

                summary = await summary_repo.get_by_id(summary_id)
                if not summary:
                    logger.error(f"Background summarization failed: summary {summary_id} not found.")
                    return

                summary.status = "processing"
                await summary_repo.update(summary)
                await session.commit()

                chunks = await chunk_repo.get_chunks_by_document_id(summary.document_id)

                bg_start = time.monotonic()
                logger.info(f"[Timing] Background summarization task started for summary {summary_id}")

                try:
                    content: TechnicalSummaryContent = await self.summarizer.summarize_document(
                        chunks=chunks,
                        language=language,
                        detail_level=detail_level,
                    )
                    summary.status = "completed"
                    summary.content_data = content.model_dump()
                    summary.error_message = None
                    summary.updated_at = datetime.now(timezone.utc)
                    await summary_repo.update(summary)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "completed"
                            job.completed_at = datetime.now(timezone.utc)
                            await job_repo.update(job)

                    await session.commit()
                    elapsed = time.monotonic() - bg_start
                    logger.info(f"[Timing] Background summarization succeeded for summary {summary_id} in {elapsed:.2f}s")

                except Exception as exc:
                    elapsed = time.monotonic() - bg_start
                    err_msg = str(exc)
                    if isinstance(exc, AITimeoutError):
                        err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
                    elif isinstance(exc, RateLimitExceededError):
                        err_msg = "Google Gemini free-tier rate limit reached (RPM/RPD exhausted). Please wait a moment before sending another request."

                    logger.error(f"[Timing] Background summarization failed after {elapsed:.2f}s for {summary_id}: {err_msg}")
                    summary.status = "failed"
                    summary.error_message = err_msg
                    summary.updated_at = datetime.now(timezone.utc)
                    await summary_repo.update(summary)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "failed"
                            job.error_message = err_msg
                            await job_repo.update(job)

                    await session.commit()

        except Exception as exc:
            logger.error(f"Unhandled background summary error for {summary_id}: {exc}")

    async def _execute_summarization_job(
        self,
        summary_id: str,
        chunks: list,
        language: LanguageEnum,
        detail_level: DetailLevelEnum,
        job_id: Optional[str] = None,
    ) -> SummaryResponse:
        """Executes LLM summarization and records state transitions in database."""
        sync_start = time.monotonic()
        summary = await self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise NotFoundError(resource="Summary", identifier=summary_id)

        summary.status = "processing"
        await self.summary_repo.update(summary)
        await self.db.commit()

        try:
            # Generate structured technical summary
            content: TechnicalSummaryContent = await self.summarizer.summarize_document(
                chunks=chunks,
                language=language,
                detail_level=detail_level,
            )

            summary.status = "completed"
            summary.content_data = content.model_dump()
            summary.error_message = None
            summary.updated_at = datetime.now(timezone.utc)
            updated_summary = await self.summary_repo.update(summary)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    await self.job_repo.update(job)

            await self.db.commit()
            elapsed = time.monotonic() - sync_start
            logger.info(f"[Timing] Synchronous summarization succeeded for summary {summary_id} in {elapsed:.2f}s")
            return SummaryResponse.from_orm_model(updated_summary, is_cached=False)

        except Exception as exc:
            elapsed = time.monotonic() - sync_start
            err_msg = str(exc)
            if isinstance(exc, AITimeoutError):
                err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
            elif isinstance(exc, RateLimitExceededError):
                err_msg = "Google Gemini free-tier rate limit reached (RPM/RPD exhausted). Please wait a moment before sending another request."

            logger.error(f"[Timing] Summarization job failed after {elapsed:.2f}s for {summary_id}: {err_msg}")
            summary.status = "failed"
            summary.error_message = err_msg
            summary.updated_at = datetime.now(timezone.utc)
            updated_summary = await self.summary_repo.update(summary)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "failed"
                    job.error_message = err_msg
                    await self.job_repo.update(job)

            await self.db.commit()
            return SummaryResponse.from_orm_model(updated_summary, is_cached=False)


    async def get_summary(self, summary_id: str) -> SummaryResponse:
        """Fetch a summary by ID."""
        summary = await self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise NotFoundError(resource="Summary", identifier=summary_id)
        return SummaryResponse.from_orm_model(summary, is_cached=False)

    async def list_summaries_for_document(self, document_id: str) -> SummaryListResponse:
        """List all summaries generated for a document."""
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(resource="Document", identifier=document_id)

        summaries = await self.summary_repo.list_by_document_id(document_id)
        return SummaryListResponse(
            items=[SummaryResponse.from_orm_model(s) for s in summaries],
            total=len(summaries),
        )
