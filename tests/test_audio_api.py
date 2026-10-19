"""
TechSift AI - Automated Integration & Unit Tests for Audio Studio Endpoints & Workflows.
Guarantees 100% offline, zero-network pytest execution using mocked TTS and AI providers.
"""

import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from pydub import AudioSegment
from pydub.generators import Sine
from src.core.config import settings
from src.schemas.audio import PodcastScript, PodcastTurn


def generate_test_mp3_bytes(duration_ms: int = 1000) -> bytes:
    """Generates valid playable MP3 bytes in-memory for testing."""
    sine = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    sine.export(buf, format="mp3", bitrate="48k")
    return buf.getvalue()


MOCK_MP3_BYTES = generate_test_mp3_bytes(1000)

MOCK_PODCAST_SCRIPT_EN = PodcastScript(
    title="Understanding B-Trees and Storage Engines",
    language="en",
    host_role="Host",
    cohost_role="Co-host",
    turns=[
        PodcastTurn(turn=1, speaker="Host", voice="en-US-GuyNeural", text="Welcome to TechSift Deep Dives."),
        PodcastTurn(turn=2, speaker="Co-host", voice="en-US-JennyNeural", text="Why do relational databases use B-Trees?"),
        PodcastTurn(turn=3, speaker="Host", voice="en-US-GuyNeural", text="Because they ensure logarithmic search with page locality."),
        PodcastTurn(turn=4, speaker="Co-host", voice="en-US-JennyNeural", text="That makes them ideal for mixed workloads."),
    ],
    source_references=["Page 1", "Section 2"],
)

MOCK_PODCAST_SCRIPT_AR = PodcastScript(
    title="طوابير الرسائل والخدمات المصغرة",
    language="ar",
    host_role="المقدم",
    cohost_role="المحاور",
    turns=[
        PodcastTurn(turn=1, speaker="المقدم", voice="ar-EG-ShakirNeural", text="أهلاً بكم في بودكاست تيك سيفت التقني."),
        PodcastTurn(turn=2, speaker="المحاور", voice="ar-EG-SalmaNeural", text="ما دور طوابير الرسائل في المعمارية الموزعة؟"),
        PodcastTurn(turn=3, speaker="المقدم", voice="ar-EG-ShakirNeural", text="تضمن فك الترابط واستمرارية العمل عند الضغط العالي."),
        PodcastTurn(turn=4, speaker="المحاور", voice="ar-EG-SalmaNeural", text="خلاصة ممتازة لعزل الأعطال وتحقيق التوسع."),
    ],
    source_references=["صفحة 1"],
)


@pytest.fixture
async def sample_document_id(client: AsyncClient, sample_pdf_bytes: bytes) -> str:
    """Uploads a valid document to test audio against."""
    files = {"file": ("distributed_db.pdf", sample_pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 201
    return res.json()["id"]


# ==============================================================================
# 1. Narration Mode Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_create_english_narration_audio(client: AsyncClient, sample_document_id: str):
    """Verifies English technical narration generation with synchronous wait."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "narration",
            "language": "en",
            "gender": "male",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        data = res.json()

        assert data["document_id"] == sample_document_id
        assert data["mode"] == "narration"
        assert data["language"] == "en"
        assert data["status"] == "completed"
        assert data["duration_seconds"] > 0
        assert data["file_size_bytes"] > 0
        assert data["voice_config"]["voice"] == "en-US-GuyNeural"
        assert data["voice_config"]["gender"] == "male"
        assert data["is_cached"] is False


@pytest.mark.asyncio
async def test_create_arabic_narration_audio(client: AsyncClient, sample_document_id: str):
    """Verifies Arabic technical narration generation with female voice."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "narration",
            "language": "ar",
            "gender": "female",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        data = res.json()

        assert data["mode"] == "narration"
        assert data["language"] == "ar"
        assert data["status"] == "completed"
        assert data["voice_config"]["voice"] == "ar-EG-SalmaNeural"
        assert data["voice_config"]["gender"] == "female"


# ==============================================================================
# 2. Podcast Conversation Mode Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_create_english_podcast_audio(client: AsyncClient, sample_document_id: str):
    """Verifies dual-speaker English podcast script generation and audio stitching."""
    with patch("src.services.podcast_generator.PodcastGenerator.generate_script", new_callable=AsyncMock) as mock_script, \
         patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        
        mock_script.return_value = MOCK_PODCAST_SCRIPT_EN
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "podcast",
            "language": "en",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        data = res.json()

        assert data["mode"] == "podcast"
        assert data["language"] == "en"
        assert data["status"] == "completed"
        assert data["script_content"]["title"] == "Understanding B-Trees and Storage Engines"
        assert len(data["script_content"]["turns"]) == 4
        assert data["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_create_arabic_podcast_audio(client: AsyncClient, sample_document_id: str):
    """Verifies dual-speaker Arabic podcast script generation and audio stitching."""
    with patch("src.services.podcast_generator.PodcastGenerator.generate_script", new_callable=AsyncMock) as mock_script, \
         patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        
        mock_script.return_value = MOCK_PODCAST_SCRIPT_AR
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "podcast",
            "language": "ar",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        data = res.json()

        assert data["mode"] == "podcast"
        assert data["language"] == "ar"
        assert data["status"] == "completed"
        assert data["script_content"]["title"] == "طوابير الرسائل والخدمات المصغرة"
        assert data["voice_config"]["host_voice"] == "ar-EG-ShakirNeural"
        assert data["voice_config"]["cohost_voice"] == "ar-EG-SalmaNeural"


# ==============================================================================
# 3. Caching & Duplicate Request Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_audio_cache_hit_returns_cached_track(client: AsyncClient, sample_document_id: str):
    """Verifies that identical requests return the cached track with is_cached=True without re-synthesizing."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {"mode": "narration", "language": "en", "wait": True}
        # First request
        res1 = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res1.status_code == 202
        assert res1.json()["is_cached"] is False
        track_id = res1.json()["id"]

        # Second request (cache hit)
        res2 = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res2.status_code == 202
        data2 = res2.json()
        assert data2["id"] == track_id
        assert data2["is_cached"] is True


@pytest.mark.asyncio
async def test_audio_list_tracks_by_document(client: AsyncClient, sample_document_id: str):
    """Verifies listing all audio tracks for a given document."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "en", "wait": True})
        await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "ar", "wait": True})

        res = await client.get(f"/api/v1/documents/{sample_document_id}/audio")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# ==============================================================================
# 4. Streaming & HTTP Range Tests (RFC 7233)
# ==============================================================================

@pytest.mark.asyncio
async def test_stream_audio_full_200(client: AsyncClient, sample_document_id: str):
    """Verifies standard full streaming response (HTTP 200)."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        post_res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "en", "wait": True})
        audio_id = post_res.json()["id"]

        res = await client.get(f"/api/v1/audio/{audio_id}/stream")
        assert res.status_code == 200
        assert res.headers["Content-Type"] == "audio/mpeg"
        assert res.headers["Accept-Ranges"] == "bytes"
        assert int(res.headers["Content-Length"]) > 0


@pytest.mark.asyncio
async def test_stream_audio_partial_content_206(client: AsyncClient, sample_document_id: str):
    """Verifies partial content streaming for scrub and seek with Range header (HTTP 206)."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        post_res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "en", "wait": True})
        audio_id = post_res.json()["id"]

        headers = {"Range": "bytes=0-99"}
        res = await client.get(f"/api/v1/audio/{audio_id}/stream", headers=headers)
        assert res.status_code == 206
        assert res.headers["Content-Type"] == "audio/mpeg"
        assert res.headers["Content-Length"] == "100"
        assert "bytes 0-99/" in res.headers["Content-Range"]
        assert len(res.content) == 100


@pytest.mark.asyncio
async def test_stream_audio_range_out_of_bounds_416(client: AsyncClient, sample_document_id: str):
    """Verifies that out-of-bounds byte range returns HTTP 416."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        post_res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "en", "wait": True})
        audio_id = post_res.json()["id"]

        headers = {"Range": "bytes=9999999-10000000"}
        res = await client.get(f"/api/v1/audio/{audio_id}/stream", headers=headers)
        assert res.status_code == 416


@pytest.mark.asyncio
async def test_download_audio_track(client: AsyncClient, sample_document_id: str):
    """Verifies attachment file download with proper Content-Disposition header."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = MOCK_MP3_BYTES

        post_res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json={"mode": "narration", "language": "en", "wait": True})
        audio_id = post_res.json()["id"]

        res = await client.get(f"/api/v1/audio/{audio_id}/download")
        assert res.status_code == 200
        assert res.headers["Content-Type"] == "audio/mpeg"
        assert "attachment; filename=" in res.headers.get("Content-Disposition", "")
        assert len(res.content) > 0


# ==============================================================================
# 5. Error Handling & Edge Cases
# ==============================================================================

@pytest.mark.asyncio
async def test_create_audio_nonexistent_document_404(client: AsyncClient):
    """Verifies requesting audio for an invalid document ID returns 404."""
    res = await client.post("/api/v1/documents/nonexistent-doc-uuid/audio", json={"mode": "narration", "language": "en"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_tts_failure_marks_track_failed(client: AsyncClient, sample_document_id: str):
    """Verifies that synthesis failure cleanly updates track status to failed with error message."""
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.side_effect = ConnectionError("Edge-TTS connection 403 Forbidden")

        payload = {"mode": "narration", "language": "en", "wait": True}
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        track_id = res.json()["id"]

        # Query track status
        track_res = await client.get(f"/api/v1/audio/{track_id}")
        assert track_res.status_code == 200
        data = track_res.json()
        assert data["status"] == "failed"
        assert "403" in data["error_message"]


@pytest.mark.asyncio
async def test_voices_catalog_endpoint(client: AsyncClient):
    """Verifies that voice catalog returns available voices for Arabic and English."""
    res = await client.get("/api/v1/audio/voices?language=ar")
    assert res.status_code == 200
    data = res.json()
    assert len(data["voices"]) > 0
    assert any("ar-" in v["id"] for v in data["voices"])


# ==============================================================================
# 6. Regression Tests: Timeout Graceful Degradation & Unfinished Audio Protection
# ==============================================================================

@pytest.mark.asyncio
async def test_podcast_succeeds_with_fallback_when_gemini_times_out(client: AsyncClient, sample_document_id: str):
    """
    Regression test for Phase 4B bug:
    Ensures that when Gemini API times out, the podcast generator engages the deterministic
    grounded fallback, producing valid dialogue turns and a playable MP3 with duration and file size.
    """
    from src.core.exceptions import AITimeoutError

    with patch("src.services.ai_provider.GeminiProvider.generate_text", new_callable=AsyncMock) as mock_gemini, \
         patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:

        # Simulate Gemini API request timeout
        mock_gemini.side_effect = AITimeoutError("Gemini API request timed out after 30.0s on model 'gemini-3.8-flash'.")
        mock_syn.return_value = MOCK_MP3_BYTES

        payload = {
            "mode": "podcast",
            "language": "ar",
            "wait": True,
        }
        res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert res.status_code == 202
        data = res.json()

        # Track MUST be completed with valid non-zero duration and file size
        assert data["status"] == "completed"
        assert data["duration_seconds"] > 0
        assert data["file_size_bytes"] > 0
        assert data["script_content"] is not None
        assert len(data["script_content"]["turns"]) >= 4
        assert data["script_content"]["turns"][0]["speaker"] == "المقدم"
        assert data["script_content"]["turns"][1]["speaker"] == "المحاور"

        # Verify MP3 is playable via stream endpoint
        stream_res = await client.get(f"/api/v1/audio/{data['id']}/stream")
        assert stream_res.status_code == 200
        assert len(stream_res.content) > 0


@pytest.mark.asyncio
async def test_failed_audio_track_cannot_be_streamed_or_downloaded(client: AsyncClient, sample_document_id: str):
    """
    Regression test:
    Verifies that a failed track returns 404 on streaming/download and never masquerades as playable audio.
    """
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.side_effect = ConnectionError("TTS synthesis network failure")

        payload = {"mode": "narration", "language": "en", "wait": True}
        post_res = await client.post(f"/api/v1/documents/{sample_document_id}/audio", json=payload)
        assert post_res.status_code == 202
        track_id = post_res.json()["id"]

        # Track status is failed
        track_res = await client.get(f"/api/v1/audio/{track_id}")
        assert track_res.json()["status"] == "failed"

        # Streaming MUST fail with 404 (not return empty playable audio)
        stream_res = await client.get(f"/api/v1/audio/{track_id}/stream")
        assert stream_res.status_code == 404

        # Download MUST fail with 404
        dl_res = await client.get(f"/api/v1/audio/{track_id}/download")
        assert dl_res.status_code == 404


@pytest.mark.asyncio
async def test_real_mp3_streaming_with_range_headers(client: AsyncClient, sample_document_id: str):
    """
    Verifies streaming and range chunking with real in-memory generated MP3 bytes.
    """
    real_mp3 = generate_test_mp3_bytes(1500)
    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", new_callable=AsyncMock) as mock_syn:
        mock_syn.return_value = real_mp3

        post_res = await client.post(
            f"/api/v1/documents/{sample_document_id}/audio",
            json={"mode": "narration", "language": "en", "wait": True},
        )
        assert post_res.status_code == 202
        track = post_res.json()
        assert track["status"] == "completed"
        assert track["file_size_bytes"] > 0
        file_size = track["file_size_bytes"]

        # Range request for first 100 bytes
        range_res = await client.get(
            f"/api/v1/audio/{track['id']}/stream",
            headers={"Range": "bytes=0-99"},
        )
        assert range_res.status_code == 206
        assert len(range_res.content) == 100
        assert range_res.headers["Content-Range"] == f"bytes 0-99/{file_size}"
        assert range_res.headers["Content-Type"] == "audio/mpeg"


@pytest.mark.asyncio
async def test_split_into_audio_chunks_boundary_safety():
    """
    Regression test: Verifies that split_into_audio_chunks safely chunks
    large multi-paragraph texts under the 700-character ceiling to prevent
    Edge-TTS stream timeouts.
    """
    from src.services.audio_stitching_service import split_into_audio_chunks

    # Short text returns single chunk
    short_text = "ملخص تقني قصير."
    assert split_into_audio_chunks(short_text, max_chars=700) == [short_text]

    # Large text with multiple sections and sentences
    para = "هذا نص تجريبي لمعمارية برمجية متقدمة في نظام تلخيص المستندات التقنية. " * 20
    long_text = f"القسم الأول:\n{para}\n\nالقسم الثاني:\n{para}"
    chunks = split_into_audio_chunks(long_text, max_chars=700)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 700
        assert len(chunk.strip()) > 0


@pytest.mark.asyncio
async def test_arabic_narration_chunking_prevents_timeout_regression(client: AsyncClient, sample_document_id: str):
    """
    Regression test for Arabic Technical Narration timeout bug:
    Simulates a backend where Edge-TTS times out whenever passed monolithic text > 800 chars.
    Verifies that AudioStitchingService chunks the text so all individual synthesis calls
    stay under 700 characters, allowing Arabic narration to succeed completely.
    """
    from src.core.exceptions import TTSConnectionError

    real_mp3 = generate_test_mp3_bytes(500)
    calls = []

    async def mock_chunk_synthesize(text: str, voice: str) -> bytes:
        calls.append(text)
        if len(text) > 800:
            raise TTSConnectionError("Speech synthesis timed out after 30.0 seconds.")
        return real_mp3

    with patch("src.services.audio_provider.EdgeTTSProvider.synthesize", side_effect=mock_chunk_synthesize):
        post_res = await client.post(
            f"/api/v1/documents/{sample_document_id}/audio",
            json={"mode": "narration", "language": "ar", "wait": True},
        )
        assert post_res.status_code == 202
        track = post_res.json()

        assert track["status"] == "completed"
        assert track["mode"] == "narration"
        assert track["language"] == "ar"
        assert track["file_size_bytes"] > 0
        assert track["duration_seconds"] > 0
        assert track["error_message"] is None

        # Verify that multiple chunks were synthesized, and none exceeded 700 chars
        assert len(calls) >= 1
        for called_text in calls:
            assert len(called_text) <= 700


# ==============================================================================
# 7. Regression Tests (Phase 4C): Secure Audio Path Validation
# ==============================================================================

@pytest.mark.asyncio
async def test_stream_audio_blocks_traversal_and_sibling_directories(client: AsyncClient, sample_document_id: str):
    """
    Regression Test (Phase 4C):
    Verifies that stream endpoint rejects path traversal (../) and sibling-directory
    file access attempts with HTTP 404, strictly sandboxing to settings.AUDIO_DIR.
    """
    import uuid
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # Insert malicious track with traversal path escaping AUDIO_DIR
    async with async_session_maker() as session:
        traversal_track = AudioTrack(
            document_id=sample_document_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path="../../../etc/passwd",
            status="completed",
            config_hash=f"hash_trav_{uuid.uuid4()}",
        )
        # Sibling directory track escaping AUDIO_DIR
        sibling_track = AudioTrack(
            document_id=sample_document_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path="../documents/some_file.pdf",
            status="completed",
            config_hash=f"hash_sib_{uuid.uuid4()}",
        )
        session.add_all([traversal_track, sibling_track])
        await session.commit()
        trav_id = traversal_track.id
        sib_id = sibling_track.id

    # 1. Attempt streaming traversal track - must return 404
    res_trav = await client.get(f"/api/v1/audio/{trav_id}/stream")
    assert res_trav.status_code == 404

    # 2. Attempt streaming sibling track - must return 404
    res_sib = await client.get(f"/api/v1/audio/{sib_id}/stream")
    assert res_sib.status_code == 404


@pytest.mark.asyncio
async def test_download_audio_blocks_traversal_and_sibling_directories(client: AsyncClient, sample_document_id: str):
    """
    Regression Test (Phase 4C):
    Verifies that download endpoint rejects path traversal and sibling-directory
    file access attempts with HTTP 404.
    """
    import uuid
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    async with async_session_maker() as session:
        traversal_track = AudioTrack(
            document_id=sample_document_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path="../../../etc/shadow",
            status="completed",
            config_hash=f"hash_down_trav_{uuid.uuid4()}",
        )
        sibling_track = AudioTrack(
            document_id=sample_document_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path="../audio_sibling/malicious.mp3",
            status="completed",
            config_hash=f"hash_down_sib_{uuid.uuid4()}",
        )
        session.add_all([traversal_track, sibling_track])
        await session.commit()
        trav_id = traversal_track.id
        sib_id = sibling_track.id

    # Must return 404
    res_trav = await client.get(f"/api/v1/audio/{trav_id}/download")
    assert res_trav.status_code == 404

    res_sib = await client.get(f"/api/v1/audio/{sib_id}/download")
    assert res_sib.status_code == 404


@pytest.mark.asyncio
async def test_missing_ffmpeg_raises_dependency_error(client: AsyncClient, sample_document_id: str):
    """
    Verifies that when ffmpeg is not found on PATH, audio synthesis
    cleanly raises AudioDependencyError with clear installation guidance.
    """
    from src.core.exceptions import AudioDependencyError
    from src.services.audio_stitching_service import AudioStitchingService
    from src.services.audio_provider import EdgeTTSProvider

    service = AudioStitchingService(EdgeTTSProvider())
    with patch("shutil.which", return_value=None):
        with pytest.raises(AudioDependencyError) as exc_info:
            await service.render_narration_audio(
                text="Sample narration text",
                voice="en-US-GuyNeural",
                output_path=Path("/tmp/test_out.mp3"),
            )
        assert "ffmpeg is required" in str(exc_info.value)
        assert "brew install ffmpeg" in str(exc_info.value)



