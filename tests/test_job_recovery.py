"""
TechSift AI - Automated Unit & Integration Tests for Job Recovery Service (Phase 4C).
Verifies startup reconciliation of interrupted background tasks, preservation of active tasks,
and UI retry enablement after server restarts.
"""

from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
import src.db.session
from src.models.audio_track import AudioTrack
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary
from src.schemas.audio import AudioLanguageEnum, AudioModeEnum
from src.services.audio_provider import get_default_voice
from src.services.audio_service import compute_audio_config_hash
from src.services.recovery_service import reconcile_interrupted_jobs
from tests.test_audio_api import MOCK_MP3_BYTES


@pytest.mark.asyncio
async def test_reconcile_interrupted_jobs_marks_stale_tasks_failed(client: AsyncClient):
    """
    Verifies that:
    1. In-progress and pending jobs created before the cutoff are marked as 'failed'.
    2. Proper explanatory error messages are populated.
    3. Completed_at and updated_at timestamps are recorded.
    """
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("recovery_stale_test.txt", b"Document content for stale test.", "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with src.db.session.async_session_maker() as session:
        # Create stale processing jobs
        job_ip = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            job_type="audio_narration",
            status="in_progress",
            created_at=past_time,
        )
        job_pen = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            job_type="summary_en_standard",
            status="pending",
            created_at=past_time,
        )

        # Create stale audio track
        track_proc = AudioTrack(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            status="processing",
            config_hash=f"hash_proc_{uuid.uuid4()}",
            created_at=past_time,
        )
        track_pen = AudioTrack(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            mode="podcast",
            language="ar",
            voice_config={"host_voice": "ar-EG-ShakirNeural"},
            status="pending",
            config_hash=f"hash_pen_{uuid.uuid4()}",
            created_at=past_time,
        )

        # Create stale summary
        sum_proc = Summary(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            language="ar",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="processing",
            created_at=past_time,
        )
        sum_pen = Summary(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="pending",
            created_at=past_time,
        )

        session.add_all([job_ip, job_pen, track_proc, track_pen, sum_proc, sum_pen])
        await session.commit()

        job_ip_id = job_ip.id
        job_pen_id = job_pen.id
        track_proc_id = track_proc.id
        track_pen_id = track_pen.id
        sum_proc_id = sum_proc.id
        sum_pen_id = sum_pen.id

    # Run reconciliation with cutoff
    async with src.db.session.async_session_maker() as session:
        stats = await reconcile_interrupted_jobs(session, startup_cutoff=cutoff)
        assert stats["processing_jobs"] >= 2
        assert stats["audio_tracks"] >= 2
        assert stats["summaries"] >= 2

    # Assert entities were transitioned to failed
    async with src.db.session.async_session_maker() as session:
        j_ip = await session.get(ProcessingJob, job_ip_id)
        assert j_ip.status == "failed"
        assert "interrupted by server shutdown" in j_ip.error_message
        assert j_ip.completed_at is not None

        j_pen = await session.get(ProcessingJob, job_pen_id)
        assert j_pen.status == "failed"
        assert "queued in a previous session" in j_pen.error_message

        t_proc = await session.get(AudioTrack, track_proc_id)
        assert t_proc.status == "failed"
        assert "interrupted by server shutdown" in t_proc.error_message

        t_pen = await session.get(AudioTrack, track_pen_id)
        assert t_pen.status == "failed"
        assert "queued in a previous session" in t_pen.error_message

        s_proc = await session.get(Summary, sum_proc_id)
        assert s_proc.status == "failed"
        assert "interrupted by server shutdown" in s_proc.error_message

        s_pen = await session.get(Summary, sum_pen_id)
        assert s_pen.status == "failed"
        assert "queued in a previous session" in s_pen.error_message


@pytest.mark.asyncio
async def test_reconcile_interrupted_jobs_protects_active_jobs_after_cutoff(client: AsyncClient):
    """
    Verifies that jobs created after startup cutoff (e.g. actively running in the
    current process) are NEVER marked as failed.
    """
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("recovery_active_test.txt", b"Document content for active test.", "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    future_time = datetime.now(timezone.utc)

    async with src.db.session.async_session_maker() as session:
        active_job = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            job_type="audio_narration",
            status="in_progress",
            created_at=future_time,
        )
        active_track = AudioTrack(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            status="processing",
            config_hash=f"hash_active_{uuid.uuid4()}",
            created_at=future_time,
        )
        session.add_all([active_job, active_track])
        await session.commit()
        job_id = active_job.id
        track_id = active_track.id

    async with src.db.session.async_session_maker() as session:
        await reconcile_interrupted_jobs(session, startup_cutoff=cutoff)

    # Verify they were NOT touched
    async with src.db.session.async_session_maker() as session:
        refreshed_job = await session.get(ProcessingJob, job_id)
        assert refreshed_job.status == "in_progress"

        refreshed_track = await session.get(AudioTrack, track_id)
        assert refreshed_track.status == "processing"


@pytest.mark.asyncio
async def test_interrupted_audio_job_reconciliation_enables_ui_retry(client: AsyncClient):
    """
    Verifies that after reconciliation marks an interrupted track as 'failed',
    re-requesting audio with the same configuration produces a new generation
    rather than blocking the user with an in-flight duplicate response.
    """
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("recovery_retry_test.txt", b"Document content for retry test.", "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    voice_config = {"voice": get_default_voice("en", "male"), "gender": "male"}
    config_hash = compute_audio_config_hash(
        document_id=doc_id,
        summary_id=None,
        mode=AudioModeEnum.NARRATION.value,
        language=AudioLanguageEnum.EN.value,
        voice_config=voice_config,
    )

    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Simulate an interrupted track left in 'processing' before restart
    async with src.db.session.async_session_maker() as session:
        stale_track = AudioTrack(
            document_id=doc_id,
            mode=AudioModeEnum.NARRATION.value,
            language=AudioLanguageEnum.EN.value,
            voice_config=voice_config,
            status="processing",
            config_hash=config_hash,
            created_at=past_time,
        )
        session.add(stale_track)
        await session.commit()
        stale_track_id = stale_track.id

    # 1. Run startup reconciliation
    async with src.db.session.async_session_maker() as session:
        await reconcile_interrupted_jobs(session, startup_cutoff=datetime.now(timezone.utc))

    # Verify stale track is marked failed
    async with src.db.session.async_session_maker() as session:
        t = await session.get(AudioTrack, stale_track_id)
        assert t.status == "failed"

    # 2. User retries audio generation with the exact same configuration
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "narration",
            "language": "en",
            "gender": "male",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{doc_id}/audio", json=payload)
        assert res.status_code == 202
        new_track_data = res.json()

        # Crucial assertion: A fresh track was created and succeeded, not the old failed one
        assert new_track_data["id"] != stale_track_id
        assert new_track_data["status"] == "completed"
        assert new_track_data["is_cached"] is False
