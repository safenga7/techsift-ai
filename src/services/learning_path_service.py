"""
TechSift AI - Learning Path Service (Phase 5A).
Coordinates chunk verification, SQLite caching, asynchronous background curricula generation,
and relational persistence across LearningPath, LearningModule, and LearningLesson.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.exceptions import (
    AITimeoutError,
    NotFoundError,
    RateLimitExceededError,
    UnsupportedDocumentError,
)
from src.db.session import async_session_maker
from src.models.document import Document
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.processing_job import ProcessingJob
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.learning_path_repository import LearningPathRepository
from src.schemas.learning_path import (
    DifficultyEnum,
    GeneratedLearningPathContent,
    LearningPathListResponse,
    LearningPathResponse,
)
from src.schemas.summary import LanguageEnum
from src.services.chunker_service import chunker_service
from src.services.learning_path_generator import (
    LearningPathGenerator,
    learning_path_generator,
)
from src.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class LearningPathService:
    """Orchestrates learning path workflows, caching, and background workers."""

    def __init__(
        self,
        db: AsyncSession,
        generator: Optional[LearningPathGenerator] = None,
    ):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.path_repo = LearningPathRepository(db)
        self.job_repo = JobRepository(db)
        self.generator = generator or learning_path_generator

    async def _ensure_document_chunks(self, document) -> list:
        """Ensures chunks are generated and persisted in SQLite for the document."""
        existing_chunks = await self.chunk_repo.get_chunks_by_document_id(document.id)
        if existing_chunks:
            return existing_chunks

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
            from src.services.chunker_service import ChunkData
            chunk_data_list = [
                ChunkData(
                    chunk_index=0,
                    content=document.extracted_text,
                    page_number=1 if document.file_type == "pdf" else None,
                    section_title="Full Document",
                    start_char=0,
                    end_char=len(document.extracted_text),
                )
            ]

        orm_chunks = chunker_service.to_orm_chunks(document.id, chunk_data_list)
        return await self.chunk_repo.create_chunks(orm_chunks)

    async def generate_learning_path(
        self,
        document_id: str,
        language: LanguageEnum = LanguageEnum.EN,
        difficulty: DifficultyEnum = DifficultyEnum.INTERMEDIATE,
        wait: bool = True,
    ) -> LearningPathResponse:
        """
        Generates or retrieves a cached learning path for a document.
        Checks SQLite cache first for zero-cost API optimization.
        """
        # 1. Fetch document
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(resource="Document", identifier=document_id)

        if doc.status in ("unsupported", "failed"):
            raise UnsupportedDocumentError(
                f"Cannot generate learning path for document with status '{doc.status}': "
                f"{doc.error_message or 'Text extraction failed or was unsupported.'}"
            )

        # 2. Check SQLite cache (Zero-cost optimization)
        cached = await self.path_repo.find_cached_path(
            document_id=doc.id,
            language=language.value,
            difficulty=difficulty.value,
        )
        if cached:
            logger.info(f"Learning path cache HIT for doc {doc.id} [{language.value}/{difficulty.value}].")
            return LearningPathResponse.from_orm_model(cached, is_cached=True)

        # 3. Check for in-flight request to prevent duplicate concurrent runs
        in_flight = await self.path_repo.find_in_flight_path(
            document_id=doc.id,
            language=language.value,
            difficulty=difficulty.value,
        )
        if in_flight:
            logger.info(f"Duplicate learning path request: returning in-flight path {in_flight.id}")
            return LearningPathResponse.from_orm_model(in_flight, is_cached=False)

        # 4. Ensure chunks exist in database
        chunks = await self._ensure_document_chunks(doc)

        # 5. Create pending learning path and processing job
        path_record = LearningPath(
            document_id=doc.id,
            language=language.value,
            difficulty=difficulty.value,
            title=f"Learning Path: {doc.filename}",
            description="Generating structured curriculum...",
            estimated_duration_minutes=0,
            status="pending",
        )
        created_path = await self.path_repo.create(path_record)

        job = ProcessingJob(
            document_id=doc.id,
            job_type=f"learning_path_{language.value}_{difficulty.value}",
            status="in_progress",
        )
        await self.job_repo.create(job)
        await self.db.commit()

        if wait:
            # Synchronous execution
            return await self._execute_learning_path_job(
                path_id=created_path.id,
                chunks=chunks,
                document=doc,
                language=language,
                difficulty=difficulty,
                job_id=job.id,
            )
        else:
            # Asynchronous background execution with isolated session
            asyncio.create_task(
                self._run_background_learning_path_task(
                    path_id=created_path.id,
                    document_id=doc.id,
                    language=language,
                    difficulty=difficulty,
                    job_id=job.id,
                )
            )
            return LearningPathResponse.from_orm_model(created_path, is_cached=False)

    async def _run_background_learning_path_task(
        self,
        path_id: str,
        document_id: str,
        language: LanguageEnum,
        difficulty: DifficultyEnum,
        job_id: Optional[str] = None,
    ) -> None:
        """Executes curriculum generation in an isolated background session."""
        bg_start = time.monotonic()
        try:
            async with async_session_maker() as session:
                path_repo = LearningPathRepository(session)
                chunk_repo = ChunkRepository(session)
                doc_repo = DocumentRepository(session)
                job_repo = JobRepository(session)

                path = await path_repo.get_by_id(path_id)
                doc = await doc_repo.get_by_id(document_id)
                if not path or not doc:
                    logger.error(f"Background task aborted: path {path_id} or doc {document_id} not found.")
                    return

                path.status = "processing"
                await path_repo.update(path)
                await session.commit()

                chunks = await chunk_repo.get_chunks_by_document_id(document_id)

                try:
                    curriculum: GeneratedLearningPathContent = await self.generator.generate_curriculum(
                        document=doc,
                        chunks=chunks,
                        language=language,
                        difficulty=difficulty,
                    )

                    # Persist root curriculum attributes
                    path.title = curriculum.title
                    path.description = curriculum.description
                    path.prerequisites = curriculum.prerequisites
                    path.learning_objectives = curriculum.learning_objectives
                    path.estimated_duration_minutes = curriculum.estimated_duration_minutes
                    path.status = "completed"
                    path.error_message = None
                    path.updated_at = datetime.now(timezone.utc)

                    # Persist Modules and Lessons
                    path.modules.clear()
                    for mod_data in curriculum.modules:
                        module = LearningModule(
                            learning_path_id=path.id,
                            title=mod_data.title,
                            description=mod_data.description,
                            learning_objectives=mod_data.learning_objectives,
                            sequence_order=mod_data.sequence_order,
                            estimated_duration_minutes=mod_data.estimated_duration_minutes,
                        )
                        for les_data in mod_data.lessons:
                            lesson = LearningLesson(
                                module_id=module.id,
                                title=les_data.title,
                                explanation=les_data.explanation,
                                key_concepts=[c.model_dump() for c in les_data.key_concepts],
                                examples=les_data.examples,
                                source_references=[r.model_dump() for r in les_data.source_references],
                                sequence_order=les_data.sequence_order,
                                estimated_duration_minutes=les_data.estimated_duration_minutes,
                            )
                            module.lessons.append(lesson)
                        path.modules.append(module)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "completed"
                            job.completed_at = datetime.now(timezone.utc)
                            await job_repo.update(job)

                    await session.commit()
                    elapsed = time.monotonic() - bg_start
                    logger.info(f"[Timing] Background learning path {path_id} completed successfully in {elapsed:.2f}s")

                except Exception as exc:
                    elapsed = time.monotonic() - bg_start
                    err_msg = str(exc)
                    if isinstance(exc, AITimeoutError):
                        err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
                    elif isinstance(exc, RateLimitExceededError):
                        err_msg = "Google Gemini free-tier rate limit reached. Please wait a moment before sending another request."

                    logger.error(f"[Timing] Background learning path {path_id} failed after {elapsed:.2f}s: {err_msg}")
                    path.status = "failed"
                    path.error_message = err_msg
                    path.updated_at = datetime.now(timezone.utc)
                    await path_repo.update(path)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "failed"
                            job.error_message = err_msg
                            await job_repo.update(job)

                    await session.commit()

        except Exception as exc:
            logger.error(f"Unhandled background learning path error for {path_id}: {exc}")

    async def _execute_learning_path_job(
        self,
        path_id: str,
        chunks: list,
        document: Document,
        language: LanguageEnum,
        difficulty: DifficultyEnum,
        job_id: Optional[str] = None,
    ) -> LearningPathResponse:
        """Executes curriculum generation synchronously."""
        sync_start = time.monotonic()
        path = await self.path_repo.get_by_id(path_id)
        if not path:
            raise NotFoundError(resource="LearningPath", identifier=path_id)

        path.status = "processing"
        await self.path_repo.update(path)
        await self.db.commit()

        try:
            curriculum: GeneratedLearningPathContent = await self.generator.generate_curriculum(
                document=document,
                chunks=chunks,
                language=language,
                difficulty=difficulty,
            )

            path.title = curriculum.title
            path.description = curriculum.description
            path.prerequisites = curriculum.prerequisites
            path.learning_objectives = curriculum.learning_objectives
            path.estimated_duration_minutes = curriculum.estimated_duration_minutes
            path.status = "completed"
            path.error_message = None
            path.updated_at = datetime.now(timezone.utc)

            # Persist Modules and Lessons
            path.modules.clear()
            for mod_data in curriculum.modules:
                module = LearningModule(
                    learning_path_id=path.id,
                    title=mod_data.title,
                    description=mod_data.description,
                    learning_objectives=mod_data.learning_objectives,
                    sequence_order=mod_data.sequence_order,
                    estimated_duration_minutes=mod_data.estimated_duration_minutes,
                )
                for les_data in mod_data.lessons:
                    lesson = LearningLesson(
                        module_id=module.id,
                        title=les_data.title,
                        explanation=les_data.explanation,
                        key_concepts=[c.model_dump() for c in les_data.key_concepts],
                        examples=les_data.examples,
                        source_references=[r.model_dump() for r in les_data.source_references],
                        sequence_order=les_data.sequence_order,
                        estimated_duration_minutes=les_data.estimated_duration_minutes,
                    )
                    module.lessons.append(lesson)
                path.modules.append(module)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    await self.job_repo.update(job)

            await self.db.commit()
            elapsed = time.monotonic() - sync_start
            logger.info(f"[Timing] Synchronous learning path {path_id} generated in {elapsed:.2f}s")
            # Refresh path with loaded modules and lessons
            refreshed = await self.path_repo.get_by_id(path_id)
            return LearningPathResponse.from_orm_model(refreshed, is_cached=False)

        except Exception as exc:
            elapsed = time.monotonic() - sync_start
            err_msg = str(exc)
            if isinstance(exc, AITimeoutError):
                err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
            elif isinstance(exc, RateLimitExceededError):
                err_msg = "Google Gemini free-tier rate limit reached. Please wait a moment before sending another request."

            logger.error(f"[Timing] Learning path job failed after {elapsed:.2f}s for {path_id}: {err_msg}")
            path.status = "failed"
            path.error_message = err_msg
            path.updated_at = datetime.now(timezone.utc)
            await self.path_repo.update(path)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "failed"
                    job.error_message = err_msg
                    await self.job_repo.update(job)

            await self.db.commit()
            refreshed = await self.path_repo.get_by_id(path_id)
            return LearningPathResponse.from_orm_model(refreshed, is_cached=False)

    async def get_learning_path(self, path_id: str) -> LearningPathResponse:
        """Retrieves a single learning path by UUID."""
        path = await self.path_repo.get_by_id(path_id)
        if not path:
            raise NotFoundError(resource="LearningPath", identifier=path_id)
        return LearningPathResponse.from_orm_model(path, is_cached=False)

    async def list_learning_paths_for_document(self, document_id: str) -> LearningPathListResponse:
        """Lists all learning paths generated for a document."""
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(resource="Document", identifier=document_id)

        paths = await self.path_repo.list_by_document_id(document_id)
        return LearningPathListResponse(
            items=[LearningPathResponse.from_orm_model(p) for p in paths],
            total=len(paths),
        )
