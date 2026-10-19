"""
TechSift AI - Audio Studio API Endpoints.
Provides audio generation, metadata queries, download, and HTTP Range streaming.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db
from src.core.config import settings
from src.core.exceptions import NotFoundError
from src.schemas.audio import (
    AudioTrackListResponse,
    AudioTrackResponse,
    CreateAudioRequest,
    VoiceCatalogResponse,
    VoiceItem,
)
from src.services.audio_provider import EdgeTTSProvider, VERIFIED_VOICES
from src.services.audio_service import AudioService

logger = logging.getLogger(__name__)


def _resolve_and_validate_audio_path(raw_file_path: Optional[str]) -> Path:
    """
    Resolves the audio file path and verifies using is_relative_to() that it
    is strictly contained within the configured audio storage directory.
    Prevents path traversal, sibling-directory, and outside-directory escape attacks.
    """
    if not raw_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file was not found on disk.",
        )

    audio_base_dir = settings.AUDIO_DIR.resolve()
    target = Path(raw_file_path)

    if target.is_absolute():
        resolved_path = target.resolve()
    elif (settings.STORAGE_DIR / target).resolve().is_relative_to(audio_base_dir):
        resolved_path = (settings.STORAGE_DIR / target).resolve()
    elif (audio_base_dir / target).resolve().is_relative_to(audio_base_dir):
        resolved_path = (audio_base_dir / target).resolve()
    else:
        resolved_path = (settings.STORAGE_DIR / target).resolve()

    if not resolved_path.is_relative_to(audio_base_dir):
        logger.warning(
            f"Security alert: Audio path traversal attempt blocked: '{raw_file_path}' "
            f"resolved to '{resolved_path}' outside '{audio_base_dir}'"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file was not found on disk.",
        )

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file was not found on disk.",
        )

    return resolved_path

router = APIRouter(tags=["Audio Studio"])


def _to_response_schema(track, is_cached: bool = False) -> AudioTrackResponse:
    """Safely maps AudioTrack entity to response schema without exposing internal storage paths."""
    return AudioTrackResponse(
        id=track.id,
        document_id=track.document_id,
        summary_id=track.summary_id,
        mode=track.mode,
        language=track.language,
        voice_config=track.voice_config,
        script_content=track.script_content,
        file_size_bytes=track.file_size_bytes,
        duration_seconds=track.duration_seconds,
        status=track.status,
        error_message=track.error_message,
        is_cached=is_cached,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


@router.post(
    "/documents/{document_id}/audio",
    response_model=AudioTrackResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create or Retrieve Cached Audio Track",
    description="Synthesizes an audio narration or dual-speaker podcast episode. Returns cached track if available.",
)
async def create_document_audio(
    document_id: str,
    payload: CreateAudioRequest,
    db: AsyncSession = Depends(get_db),
) -> AudioTrackResponse:
    service = AudioService(db)
    track, is_cached = await service.create_or_get_audio(document_id, payload)
    return _to_response_schema(track, is_cached=is_cached)


@router.get(
    "/documents/{document_id}/audio",
    response_model=AudioTrackListResponse,
    summary="List Document Audio Tracks",
    description="Retrieves all audio tracks generated for a given document.",
)
async def list_document_audio_tracks(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> AudioTrackListResponse:
    service = AudioService(db)
    tracks = await service.list_document_audio(document_id)
    return AudioTrackListResponse(
        items=[_to_response_schema(t) for t in tracks],
        total=len(tracks),
    )


@router.get(
    "/audio/voices",
    response_model=VoiceCatalogResponse,
    summary="List Available Voices",
    description="Returns verified voices for Arabic and English narration and podcasting.",
)
async def list_voices(
    language: Optional[str] = Query(None, description="Optional filter ('ar' or 'en')"),
) -> VoiceCatalogResponse:
    provider = EdgeTTSProvider()
    raw_voices = await provider.list_voices(language)
    items = [
        VoiceItem(
            id=v["id"],
            name=v["name"],
            language=v["language"],
            gender=v["gender"],
            locale=v["locale"],
        )
        for v in raw_voices
    ]
    return VoiceCatalogResponse(voices=items)


@router.get(
    "/audio/{audio_id}",
    response_model=AudioTrackResponse,
    summary="Get Audio Track Details",
    description="Returns metadata, script transcript, duration, and processing status.",
)
async def get_audio_track(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
) -> AudioTrackResponse:
    service = AudioService(db)
    track = await service.get_audio_track(audio_id)
    return _to_response_schema(track)


@router.api_route(
    "/audio/{audio_id}/stream",
    methods=["GET", "HEAD"],
    summary="Stream Audio Track (HTTP Range)",
    description="Streams audio file with HTTP 206 Partial Content support for seeking and scrubbing.",
)
async def stream_audio_track(
    audio_id: str,
    request: Request,
    range_header: Optional[str] = Header(None, alias="Range"),
    db: AsyncSession = Depends(get_db),
):
    service = AudioService(db)
    track = await service.get_audio_track(audio_id)

    if track.status != "completed" or not track.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio track '{audio_id}' is not ready for playback (status: {track.status}).",
        )

    file_path = _resolve_and_validate_audio_path(track.file_path)

    file_size = file_path.stat().st_size
    content_type = "audio/mpeg"

    # Handle HEAD request probe
    if request.method == "HEAD":
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
        return Response(status_code=status.HTTP_200_OK, headers=headers)

    # Handle HTTP 206 Range Request
    if range_header:
        try:
            # Format: 'bytes=start-end'
            byte_range = range_header.strip().replace("bytes=", "")
            parts = byte_range.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

            if start >= file_size or end >= file_size or start > end:
                return Response(
                    status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            chunk_length = end - start + 1

            def _iter_range_file():
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_length
                    while remaining > 0:
                        chunk_size = min(64 * 1024, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_length),
                "Content-Type": content_type,
            }
            return StreamingResponse(_iter_range_file(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)

        except Exception as exc:
            logger.warning(f"Failed parsing Range header '{range_header}': {exc}. Falling back to full stream.")

    # Full Stream (HTTP 200)
    def _iter_full_file():
        with open(file_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": content_type,
    }
    return StreamingResponse(_iter_full_file(), status_code=status.HTTP_200_OK, headers=headers)


@router.api_route(
    "/audio/{audio_id}/download",
    methods=["GET", "HEAD"],
    summary="Download Audio Track",
    description="Downloads the generated MP3 file as an attachment.",
)
async def download_audio_track(
    audio_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = AudioService(db)
    track = await service.get_audio_track(audio_id)

    if track.status != "completed" or not track.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio track '{audio_id}' is not available for download.",
        )

    file_path = _resolve_and_validate_audio_path(track.file_path)

    filename = f"techsift_{track.mode}_{track.language}_{track.id[:8]}.mp3"
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=filename,
    )
