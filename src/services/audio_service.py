"""
TechSift AI - Audio Studio Business Service.
Coordinates narration script assembly, podcast dialogue generation, background synthesis,
SQLite audio persistence, and zero-cost configuration fingerprint caching.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.core.exceptions import NotFoundError, UnsupportedDocumentError
from src.db.session import async_session_maker
from src.models.audio_track import AudioTrack
from src.models.document import Document
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary
from src.repositories.audio_repository import AudioRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.summary_repository import SummaryRepository
from src.schemas.audio import (
    AudioLanguageEnum,
    AudioModeEnum,
    AudioTrackResponse,
    CreateAudioRequest,
    PodcastScript,
)
from src.services.audio_provider import AudioProvider, EdgeTTSProvider, get_default_voice
from src.services.audio_stitching_service import AudioStitchingService
from src.services.podcast_generator import PodcastGenerator

logger = logging.getLogger(__name__)


def compute_audio_config_hash(
    document_id: str,
    summary_id: Optional[str],
    mode: str,
    language: str,
    voice_config: Dict[str, Any],
) -> str:
    """Computes a deterministic SHA-256 fingerprint for caching audio synthesis."""
    sorted_voice = json.dumps(voice_config, sort_keys=True)
    raw = f"{document_id}:{summary_id or ''}:{mode}:{language}:{sorted_voice}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AudioService:
    """Manages audio generation, background job orchestration, and caching."""

    def __init__(
        self,
        db: AsyncSession,
        audio_provider: Optional[AudioProvider] = None,
        podcast_generator: Optional[PodcastGenerator] = None,
        stitching_service: Optional[AudioStitchingService] = None,
    ):
        self.db = db
        self.audio_repo = AudioRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.job_repo = JobRepository(db)

        self.audio_provider = audio_provider or EdgeTTSProvider()
        self.podcast_generator = podcast_generator or PodcastGenerator()
        self.stitching_service = stitching_service or AudioStitchingService(self.audio_provider)

    async def get_audio_track(self, audio_id: str) -> AudioTrack:
        """Retrieves a single audio track or raises NotFoundError."""
        track = await self.audio_repo.get_by_id(audio_id)
        if not track:
            raise NotFoundError("AudioTrack", audio_id)
        return track

    async def list_document_audio(self, document_id: str) -> List[AudioTrack]:
        """Lists all audio tracks for a given document."""
        await self._ensure_document_exists(document_id)
        return await self.audio_repo.list_by_document_id(document_id)

    async def _ensure_document_exists(self, document_id: str) -> Document:
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document", document_id)
        if doc.status == "unsupported":
            raise UnsupportedDocumentError(
                "Cannot generate audio for an unsupported document (e.g. image-only PDF)."
            )
        return doc

    async def _resolve_summary(
        self, document_id: str, summary_id: Optional[str], language: AudioLanguageEnum
    ) -> Optional[Summary]:
        if summary_id:
            summary = await self.summary_repo.get_by_id(summary_id)
            if not summary or summary.document_id != document_id:
                raise NotFoundError("Summary", summary_id)
            return summary

        # Find latest completed summary matching language
        summaries = await self.summary_repo.list_by_document_id(document_id)
        matching = [s for s in summaries if s.status == "completed" and s.language == language.value]
        if matching:
            return matching[0]

        # Any completed summary
        any_completed = [s for s in summaries if s.status == "completed"]
        return any_completed[0] if any_completed else None

    def _resolve_voice_config(self, request: CreateAudioRequest) -> Dict[str, Any]:
        lang_str = request.language.value
        if request.mode == AudioModeEnum.NARRATION:
            gender_str = request.gender.value if request.gender else "male"
            voice = get_default_voice(lang_str, gender_str)
            return {"voice": voice, "gender": gender_str}
        else:
            host_voice = request.host_voice or get_default_voice(lang_str, "male")
            cohost_voice = request.cohost_voice or get_default_voice(lang_str, "female")
            return {"host_voice": host_voice, "cohost_voice": cohost_voice}

    def _build_narration_script_text(
        self, document: Document, summary: Optional[Summary], language: AudioLanguageEnum
    ) -> str:
        """Builds a coherent, grounded narration script from existing technical summaries."""
        if summary and summary.content_data:
            data = summary.content_data
            exec_summary = data.get("executive_summary", "")
            concepts = data.get("main_concepts", [])
            findings = data.get("key_findings", [])
            takeaways = data.get("key_takeaways", [])
            arch = data.get("architecture_overview") or ""

            if language == AudioLanguageEnum.AR:
                sections = [f"ملخص تحليلي للمستند التقني: {document.filename}."]
                if exec_summary:
                    sections.append(f"الملخص التنفيذي:\n{exec_summary}")
                if concepts:
                    c_text = " ".join(f"{c.get('term', '')}: {c.get('definition', '')}." for c in concepts[:5])
                    sections.append(f"أهم المفاهيم المعمارية:\n{c_text}")
                if arch:
                    sections.append(f"نظرة عامة على البنية البرمجية:\n{arch}")
                if findings:
                    sections.append("النتائج الفنية الأساسية:\n" + " ".join(findings))
                if takeaways:
                    sections.append("الخلاصة وأفضل الممارسات:\n" + " ".join(takeaways))
                return "\n\n".join(sections)
            else:
                sections = [f"Technical analysis narration for document: {document.filename}."]
                if exec_summary:
                    sections.append(f"Executive Summary:\n{exec_summary}")
                if concepts:
                    c_text = " ".join(f"{c.get('term', '')}: {c.get('definition', '')}." for c in concepts[:5])
                    sections.append(f"Core Architectural Concepts:\n{c_text}")
                if arch:
                    sections.append(f"Architecture Overview:\n{arch}")
                if findings:
                    sections.append("Key Findings:\n" + " ".join(findings))
                if takeaways:
                    sections.append("Key Takeaways:\n" + " ".join(takeaways))
                return "\n\n".join(sections)

        # Fallback to plain document text (first 3500 chars)
        raw = document.extracted_text or ""
        return raw[:3500]

    async def create_or_get_audio(
        self, document_id: str, request: CreateAudioRequest
    ) -> Tuple[AudioTrack, bool]:
        """
        Creates an audio track or returns an existing cached track.
        Returns (track, is_cached).
        """
        document = await self._ensure_document_exists(document_id)
        summary = await self._resolve_summary(document_id, request.summary_id, request.language)
        summary_id = summary.id if summary else None

        voice_config = self._resolve_voice_config(request)
        config_hash = compute_audio_config_hash(
            document_id=document_id,
            summary_id=summary_id,
            mode=request.mode.value,
            language=request.language.value,
            voice_config=voice_config,
        )

        # 1. Zero-Cost Cache Check
        cached_track = await self.audio_repo.get_by_config_hash(config_hash)
        if cached_track and cached_track.file_path:
            physical_path = settings.STORAGE_DIR / cached_track.file_path
            if physical_path.exists() and physical_path.stat().st_size > 0:
                logger.info(f"Audio cache hit for document {document_id} (track {cached_track.id})")
                return cached_track, True

        # 2. Check for in-flight jobs to prevent duplicates
        in_flight = await self.audio_repo.get_pending_or_processing_by_hash(config_hash)
        if in_flight:
            logger.info(f"Duplicate audio request: returning in-flight track {in_flight.id}")
            return in_flight, False

        # 3. Create persistent AudioTrack entity in SQLite
        new_track = AudioTrack(
            document_id=document_id,
            summary_id=summary_id,
            mode=request.mode.value,
            language=request.language.value,
            voice_config=voice_config,
            status="pending",
            config_hash=config_hash,
        )
        new_track = await self.audio_repo.create(new_track)

        # 4. Create ProcessingJob metadata
        job = ProcessingJob(
            document_id=document_id,
            job_type=f"audio_{request.mode.value}",
            status="pending",
        )
        job = await self.job_repo.create(job)
        await self.db.commit()

        if request.wait:
            # Synchronous processing using current request session
            await self._execute_audio_synthesis(new_track.id, job.id, session=self.db)
            refreshed = await self.audio_repo.get_by_id(new_track.id)
            return refreshed or new_track, False
        else:
            # Asynchronous background processing (does not block FastAPI event loop)
            asyncio.create_task(self._run_background_audio_task(new_track.id, job.id))
            return new_track, False

    async def _run_background_audio_task(self, track_id: str, job_id: str) -> None:
        """Executes audio synthesis in an isolated background database session."""
        try:
            await self._execute_audio_synthesis(track_id, job_id)
        except Exception as exc:
            logger.error(f"Unhandled background audio task failure for track {track_id}: {exc}")

    async def _execute_audio_synthesis(
        self, track_id: str, job_id: str, session: Optional[AsyncSession] = None
    ) -> None:
        """Core synthesis pipeline: script generation, audio rendering, and persistence."""
        if session is not None:
            await self._run_synthesis_pipeline(track_id, job_id, session)
        else:
            async with async_session_maker() as new_session:
                await self._run_synthesis_pipeline(track_id, job_id, new_session)

    async def _run_synthesis_pipeline(
        self, track_id: str, job_id: str, session: AsyncSession
    ) -> None:
        audio_repo = AudioRepository(session)
        job_repo = JobRepository(session)
        doc_repo = DocumentRepository(session)
        summary_repo = SummaryRepository(session)

        track = await audio_repo.get_by_id(track_id)
        job = await job_repo.get_by_id(job_id)
        if not track:
            logger.error(f"AudioTrack {track_id} not found during synthesis execution.")
            return

        document = await doc_repo.get_by_id(track.document_id)
        summary = await summary_repo.get_by_id(track.summary_id) if track.summary_id else None

        # Mark status as processing
        track.status = "processing"
        await audio_repo.update(track)
        if job:
            job.status = "in_progress"
            await job_repo.update(job)

            output_filename = f"{track.id}.mp3"
            rel_file_path = f"audio/{output_filename}"
            full_output_path = settings.STORAGE_DIR / rel_file_path

            try:
                lang_enum = AudioLanguageEnum(track.language)
                mode_enum = AudioModeEnum(track.mode)

                if mode_enum == AudioModeEnum.NARRATION:
                    voice = track.voice_config.get("voice") or get_default_voice(track.language, "male")
                    narration_text = self._build_narration_script_text(document, summary, lang_enum)
                    track.script_content = {"text": narration_text}

                    duration, file_size = await self.stitching_service.render_narration_audio(
                        text=narration_text,
                        voice=voice,
                        output_path=full_output_path,
                    )

                elif mode_enum == AudioModeEnum.PODCAST:
                    host_voice = track.voice_config.get("host_voice") or get_default_voice(track.language, "male")
                    cohost_voice = track.voice_config.get("cohost_voice") or get_default_voice(track.language, "female")

                    # Generate dialogue script via Gemini provider
                    script = await self.podcast_generator.generate_script(
                        document=document,
                        summary=summary,
                        language=lang_enum,
                        host_voice=host_voice,
                        cohost_voice=cohost_voice,
                    )
                    track.script_content = script.model_dump()

                    duration, file_size = await self.stitching_service.render_podcast_audio(
                        script=script,
                        output_path=full_output_path,
                    )

                # Update track with completion metadata
                track.file_path = rel_file_path
                track.file_size_bytes = file_size
                track.duration_seconds = duration
                track.status = "completed"
                track.error_message = None
                await audio_repo.update(track)

                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    await job_repo.update(job)

                await session.commit()
                logger.info(f"AudioTrack {track_id} rendered successfully ({duration}s, {file_size} bytes)")

            except Exception as exc:
                error_msg = str(exc)
                logger.error(f"AudioTrack {track_id} failed: {error_msg}")
                track.status = "failed"
                track.error_message = error_msg
                await audio_repo.update(track)

                if job:
                    job.status = "failed"
                    job.error_message = error_msg
                    job.completed_at = datetime.now(timezone.utc)
                    await job_repo.update(job)

                await session.commit()
