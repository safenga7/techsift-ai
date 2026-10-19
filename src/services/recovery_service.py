"""
TechSift AI - Startup Background Job Reconciliation Service.
Reconciles interrupted in-flight jobs and orphaned tasks caused by server restarts.

Single-Process Architecture Assumption:
In TechSift AI's zero-cost, local-first architecture, background jobs (summarization, audio synthesis)
are dispatched in-process using asyncio.create_task(). When the application process terminates
or the server restarts, all in-memory event loops and task queues are destroyed by the operating system.
No external broker (Redis/Celery/RabbitMQ) persists these in-memory tasks.

At application startup (lifespan hook), any tasks recorded in SQLite with active ('in_progress', 'processing')
or orphaned unstarted ('pending') status from previous server sessions must be reconciled to 'failed'.
This frees duplicate configuration hashes (preventing permanent cache deadlocks) and allows the
frontend UI to immediately display the failure with a retry action.
Active tasks started in the *current* process session are protected by timestamp boundaries.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Optional
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.assessment import Assessment
from src.models.audio_track import AudioTrack
from src.models.learning_path import LearningPath
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary

logger = logging.getLogger(__name__)


async def reconcile_interrupted_jobs(
    db: AsyncSession,
    startup_cutoff: Optional[datetime] = None,
) -> Dict[str, int]:
    """
    Reconciles interrupted jobs from prior server sessions at application startup.

    1. ProcessingJob: Marks 'in_progress' and stale 'pending' jobs as 'failed'.
    2. AudioTrack: Marks 'processing' and stale 'pending' tracks as 'failed'.
    3. Summary: Marks 'processing' and stale 'pending' summaries as 'failed'.

    Ensures that config_hash uniqueness and in-flight filters no longer block user retries.
    Uses startup_cutoff to ensure that actively running jobs created during or after current
    server startup are never touched.
    """
    cutoff = startup_cutoff or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    reconciled_counts = {
        "processing_jobs": 0,
        "audio_tracks": 0,
        "summaries": 0,
        "learning_paths": 0,
        "assessments": 0,
    }

    # 1. Reconcile ProcessingJob
    # In-progress jobs were actively running when server stopped
    stmt_jobs_in_progress = (
        update(ProcessingJob)
        .where(
            ProcessingJob.status == "in_progress",
            ProcessingJob.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Job interrupted by server shutdown. Please retry.",
            completed_at=now,
        )
    )
    result_jobs_ip = await db.execute(stmt_jobs_in_progress)

    # Orphaned pending jobs from prior sessions (never started before shutdown)
    stmt_jobs_pending = (
        update(ProcessingJob)
        .where(
            ProcessingJob.status == "pending",
            ProcessingJob.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Job was queued in a previous session and interrupted before execution started. Please retry.",
            completed_at=now,
        )
    )
    result_jobs_p = await db.execute(stmt_jobs_pending)
    reconciled_counts["processing_jobs"] = (result_jobs_ip.rowcount or 0) + (result_jobs_p.rowcount or 0)

    # 2. Reconcile AudioTrack
    stmt_audio_processing = (
        update(AudioTrack)
        .where(
            AudioTrack.status == "processing",
            AudioTrack.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Audio synthesis was interrupted by server shutdown. Please retry.",
            updated_at=now,
        )
    )
    result_audio_proc = await db.execute(stmt_audio_processing)

    stmt_audio_pending = (
        update(AudioTrack)
        .where(
            AudioTrack.status == "pending",
            AudioTrack.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Audio generation request was queued in a previous session and interrupted before execution. Please retry.",
            updated_at=now,
        )
    )
    result_audio_pen = await db.execute(stmt_audio_pending)
    reconciled_counts["audio_tracks"] = (result_audio_proc.rowcount or 0) + (result_audio_pen.rowcount or 0)

    # 3. Reconcile Summary
    stmt_summary_processing = (
        update(Summary)
        .where(
            Summary.status == "processing",
            Summary.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Summary generation was interrupted by server shutdown. Please retry.",
            updated_at=now,
        )
    )
    result_summary_proc = await db.execute(stmt_summary_processing)

    stmt_summary_pending = (
        update(Summary)
        .where(
            Summary.status == "pending",
            Summary.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Summary generation was queued in a previous session and interrupted before execution. Please retry.",
            updated_at=now,
        )
    )
    result_summary_pen = await db.execute(stmt_summary_pending)
    reconciled_counts["summaries"] = (result_summary_proc.rowcount or 0) + (result_summary_pen.rowcount or 0)

    # 4. Reconcile LearningPath
    stmt_path_processing = (
        update(LearningPath)
        .where(
            LearningPath.status == "processing",
            LearningPath.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Learning path generation was interrupted by server shutdown. Please retry.",
            updated_at=now,
        )
    )
    result_path_proc = await db.execute(stmt_path_processing)

    stmt_path_pending = (
        update(LearningPath)
        .where(
            LearningPath.status == "pending",
            LearningPath.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Learning path generation was queued in a previous session and interrupted before execution. Please retry.",
            updated_at=now,
        )
    )
    result_path_pen = await db.execute(stmt_path_pending)
    reconciled_counts["learning_paths"] = (result_path_proc.rowcount or 0) + (result_path_pen.rowcount or 0)

    # 5. Reconcile Assessment
    stmt_assessment_processing = (
        update(Assessment)
        .where(
            Assessment.status == "processing",
            Assessment.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Assessment generation was interrupted by server shutdown. Please retry.",
            updated_at=now,
        )
    )
    result_assessment_proc = await db.execute(stmt_assessment_processing)

    stmt_assessment_pending = (
        update(Assessment)
        .where(
            Assessment.status == "pending",
            Assessment.created_at <= cutoff,
        )
        .values(
            status="failed",
            error_message="Assessment generation was queued in a previous session and interrupted before execution. Please retry.",
            updated_at=now,
        )
    )
    result_assessment_pen = await db.execute(stmt_assessment_pending)
    reconciled_counts["assessments"] = (result_assessment_proc.rowcount or 0) + (result_assessment_pen.rowcount or 0)

    await db.commit()

    total = sum(reconciled_counts.values())
    if total > 0:
        logger.info(
            f"Startup reconciliation reconciled {total} stale entities: "
            f"{reconciled_counts['processing_jobs']} jobs, "
            f"{reconciled_counts['audio_tracks']} audio tracks, "
            f"{reconciled_counts['summaries']} summaries, "
            f"{reconciled_counts['learning_paths']} learning paths, "
            f"{reconciled_counts['assessments']} assessments."
        )

    return reconciled_counts
