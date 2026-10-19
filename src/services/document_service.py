"""
TechSift AI - Document Service.
Business logic layer coordinating storage, extraction, validation, and repository persistence.
Features streaming upload size limits and rollback safeguards against partial failures.
"""

from datetime import datetime, timezone
import logging
import math
from pathlib import Path
from typing import Optional
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.exceptions import (
    AppException,
    FileTooLargeError,
    NotFoundError,
    StorageError,
    UnsupportedDocumentError,
)
from src.models.document import Document
from src.models.processing_job import ProcessingJob
from src.repositories.audio_repository import AudioRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.summary_repository import SummaryRepository
from src.schemas.common import PaginationMetadata
from src.schemas.document import DocumentListResponse, DocumentResponse, DocumentStatsResponse
from src.services.storage_service import storage_service
from src.services.text_extractor import text_extractor_service

logger = logging.getLogger(__name__)


async def read_upload_stream_with_size_limit(
    file: UploadFile,
    max_size: int = settings.MAX_UPLOAD_SIZE_BYTES,
    chunk_size: int = 64 * 1024,  # 64 KB chunks
) -> bytes:
    """
    Reads an UploadFile in streaming chunks and enforces max_size immediately
    during ingestion, without buffering oversized payloads into memory.
    """
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_size:
            raise FileTooLargeError(file_size=total_bytes, max_size=max_size)
        chunks.append(chunk)

    return b"".join(chunks)


class DocumentService:
    """Coordinates business operations for technical document management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.job_repo = JobRepository(db)
        self.summary_repo = SummaryRepository(db)

    async def get_stats(self) -> DocumentStatsResponse:
        """
        Computes document totals, status breakdown, issues count, and completed summaries
        across the entire collection, independently of pagination.
        """
        stats_data = await self.doc_repo.get_stats()
        total_summaries = await self.summary_repo.count_completed()
        return DocumentStatsResponse(
            **stats_data,
            total_summaries=total_summaries,
        )

    async def upload_document(self, filename: str, content: bytes) -> Document:
        """
        Processes and stores an uploaded document:
        1. Checks file size against configured limit (defense-in-depth).
        2. Validates format and binary magic signatures.
        3. Sandboxes and saves file to local storage.
        4. Extracts document text and handles scanned/unsupported files gracefully.
        5. Persists metadata and job status in SQLite.
        6. Safely rolls back and deletes storage file if any database failure occurs.
        """
        file_size = len(content)

        # 1. Enforce size limit
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeError(file_size=file_size, max_size=settings.MAX_UPLOAD_SIZE_BYTES)

        # 2. Validate format and signature
        file_type = text_extractor_service.validate_file_format(filename, content)

        # 3. Secure storage filename generation
        clean_filename = storage_service.sanitize_filename(filename)
        storage_filename = storage_service.generate_storage_filename(clean_filename)
        content_hash = storage_service.compute_sha256(content)

        # Persist to local filesystem
        await storage_service.save_file(content, storage_filename)

        try:
            # 4. Extract text
            extracted_text = None
            word_count = 0
            page_count = None
            status = "pending"
            error_message = None

            try:
                extraction = text_extractor_service.extract(content, file_type)
                extracted_text = extraction.text
                word_count = extraction.word_count
                page_count = extraction.page_count
                status = "processed"
            except UnsupportedDocumentError as ude:
                status = "unsupported"
                error_message = str(ude)
            except Exception as exc:
                status = "failed"
                error_message = f"Text extraction failed: {str(exc)}"

            # 5. Persist document in database
            document = Document(
                filename=clean_filename,
                file_type=file_type,
                file_size=file_size,
                storage_filename=storage_filename,
                content_hash=content_hash,
                extracted_text=extracted_text,
                word_count=word_count,
                page_count=page_count,
                status=status,
                error_message=error_message,
            )
            created_doc = await self.doc_repo.create(document)

            # Create corresponding processing job
            job = ProcessingJob(
                document_id=created_doc.id,
                job_type="extraction",
                status="completed" if status == "processed" else "failed",
                error_message=error_message,
                completed_at=datetime.now(timezone.utc) if status == "processed" else None,
            )
            await self.job_repo.create(job)

            return created_doc

        except AppException:
            storage_service.delete_file(storage_filename)
            raise
        except Exception as exc:
            # Partial failure rollback safeguard: purge physical storage file on database error
            storage_service.delete_file(storage_filename)
            raise StorageError(f"Failed to persist document to database: {str(exc)}") from exc

    async def get_document(self, document_id: str) -> Document:
        """Fetch document by UUID or raise NotFoundError."""
        document = await self.doc_repo.get_by_id(document_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=document_id)
        return document

    async def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> DocumentListResponse:
        """Fetch paginated document records."""
        page = max(1, page)
        limit = min(max(1, page_size), 100)
        skip = (page - 1) * limit

        items, total = await self.doc_repo.list_documents(skip=skip, limit=limit, status=status)
        total_pages = math.ceil(total / limit) if total > 0 else 1

        pagination = PaginationMetadata(
            total=total,
            skip=skip,
            limit=limit,
            page=page,
            total_pages=total_pages,
        )

        return DocumentListResponse(
            items=[DocumentResponse.model_validate(item) for item in items],
            pagination=pagination,
        )

    async def delete_document(self, document_id: str) -> None:
        """
        Deletes a document:
        - Collects and validates all associated audio files and source document file.
        - Enforces strict sandboxing against permitted storage directories.
        - Employs reversible file staging (.del_<token> in-place rename):
          1. Renames all target files to staged paths before deleting DB records.
          2. If any file fails to stage, immediately rolls back already-staged files to original names.
          3. Flushes SQLite deletion within the active transaction.
          4. If database deletion fails, restores all staged files to original names.
          5. Only unlinks staged files after database deletion succeeds.
        Guarantees that a database rollback never leaves orphaned DB records pointing to unlinked files.
        """
        document = await self.get_document(document_id)

        # 1. Collect associated audio tracks and validate file paths BEFORE any filesystem modifications
        audio_repo = AudioRepository(self.db)
        audio_tracks = await audio_repo.list_by_document_id(document_id)

        audio_base_dir = settings.AUDIO_DIR.resolve()
        target_files: list[Path] = []

        for track in audio_tracks:
            if not track.file_path:
                continue

            raw_path = Path(track.file_path)
            if raw_path.is_absolute():
                resolved_audio_path = raw_path.resolve()
            elif (settings.STORAGE_DIR / raw_path).resolve().is_relative_to(audio_base_dir):
                resolved_audio_path = (settings.STORAGE_DIR / raw_path).resolve()
            elif (audio_base_dir / raw_path).resolve().is_relative_to(audio_base_dir):
                resolved_audio_path = (audio_base_dir / raw_path).resolve()
            else:
                resolved_audio_path = (settings.STORAGE_DIR / raw_path).resolve()

            # Security: strictly enforce that audio path is within AUDIO_DIR
            if not resolved_audio_path.is_relative_to(audio_base_dir):
                raise StorageError(
                    f"Security violation: audio track '{track.id}' references file '{track.file_path}' "
                    f"outside permitted audio directory."
                )

            if resolved_audio_path.exists() and resolved_audio_path.is_file():
                target_files.append(resolved_audio_path)

        # 2. Validate and collect document source file
        doc_file_path = storage_service.get_absolute_path(document.storage_filename)
        if doc_file_path.exists() and doc_file_path.is_file():
            target_files.append(doc_file_path)

        # 3. Reversibly stage files by renaming in-place within their respective directories
        staging_token = uuid.uuid4().hex[:8]
        staged_pairs: list[tuple[Path, Path]] = []  # (original_path, staged_path)

        try:
            for original_path in target_files:
                staged_path = original_path.with_name(f"{original_path.name}.del_{staging_token}")
                original_path.rename(staged_path)
                staged_pairs.append((original_path, staged_path))
        except OSError as stage_exc:
            # Revert any files that were already staged back to their original names
            for orig, staged in staged_pairs:
                try:
                    if staged.exists():
                        staged.rename(orig)
                except Exception as rollback_exc:
                    logger.critical(f"Failed restoring staged file '{staged}' to '{orig}': {rollback_exc}")
            raise StorageError(f"Document deletion aborted during file staging: {stage_exc}") from stage_exc

        # 4. Delete database record (flushes cascade deletion in SQLite within active transaction)
        try:
            await self.doc_repo.delete(document)
            await self.db.commit()
        except Exception as db_exc:
            # Database deletion failed: revert all staged files to restore exact pre-deletion state
            for orig, staged in staged_pairs:
                try:
                    if staged.exists():
                        staged.rename(orig)
                except Exception as rollback_exc:
                    logger.critical(f"Failed restoring staged file '{staged}' to '{orig}': {rollback_exc}")
            from src.core.exceptions import AppException
            if isinstance(db_exc, AppException):
                raise
            raise StorageError(f"Document deletion aborted during database delete: {db_exc}") from db_exc

        # 5. Finalize deletion: unlink the staged files (DB deletion has already succeeded)
        for orig, staged in staged_pairs:
            try:
                if staged.exists():
                    staged.unlink()
                    logger.info(f"Purged staged file: {staged.name}")
            except OSError as finalize_exc:
                logger.warning(f"Could not immediately unlink staged file '{staged}': {finalize_exc}")
