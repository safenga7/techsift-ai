"""
TechSift AI - Automated Unit Tests for Audio Subsystem & Dialogue Stitching
Uses mocked TTS providers to guarantee 100% offline, zero-network pytest execution.
"""

import io
import struct
import wave
from pathlib import Path
import pytest


def create_mock_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates valid in-memory PCM WAV audio bytes without external dependencies."""
    num_samples = int(duration_seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        # Write silence (zeros)
        wav_file.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


class MockTTSProvider:
    """Mock offline TTS engine for deterministic unit testing."""

    def __init__(self, should_fail: bool = False, fail_error: Exception | None = None):
        self.should_fail = should_fail
        self.fail_error = fail_error or ConnectionError("Network unreachable")
        self.call_count = 0

    async def synthesize(self, text: str, voice: str) -> bytes:
        self.call_count += 1
        if self.should_fail:
            raise self.fail_error
        # Return mock audio proportional to text length
        duration = max(0.5, len(text.split()) * 0.3)
        return create_mock_wav_bytes(duration_seconds=duration)


class AudioFallbackChain:
    """Orchestrates primary and fallback TTS providers."""

    def __init__(self, primary_provider, fallback_provider):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.last_provider_used = None

    async def generate_speech(self, text: str, primary_voice: str, fallback_voice: str) -> bytes:
        try:
            audio = await self.primary.synthesize(text, primary_voice)
            self.last_provider_used = "primary"
            return audio
        except Exception:
            audio = await self.fallback.synthesize(text, fallback_voice)
            self.last_provider_used = "fallback"
            return audio


def stitch_audio_turns(turn_audios: list[bytes]) -> bytes:
    """
    Concatenates multiple WAV audio segments with header recalculation.
    """
    if not turn_audios:
        raise ValueError("Cannot stitch empty audio list")

    total_frames = bytearray()
    sample_rate = 16000

    for audio_bytes in turn_audios:
        with wave.open(io.BytesIO(audio_bytes), "rb") as r:
            sample_rate = r.getframerate()
            frames = r.readframes(r.getnframes())
            total_frames.extend(frames)

    out_buf = io.BytesIO()
    with wave.open(out_buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(total_frames)

    return out_buf.getvalue()


# ==============================================================================
# Pytest Test Cases
# ==============================================================================

@pytest.mark.asyncio
async def test_mock_tts_provider_success():
    """Verifies that mock TTS provider synthesizes valid decodable WAV audio."""
    provider = MockTTSProvider()
    audio_bytes = await provider.synthesize("FastAPI and SQLite testing", "test-voice")
    
    assert len(audio_bytes) > 44  # WAV header is 44 bytes
    with wave.open(io.BytesIO(audio_bytes), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 16000
        assert w.getnframes() > 0


@pytest.mark.asyncio
async def test_audio_fallback_chain_primary_success():
    """Verifies that primary TTS provider is used when available."""
    primary = MockTTSProvider()
    fallback = MockTTSProvider()
    chain = AudioFallbackChain(primary, fallback)

    audio = await chain.generate_speech("Test sentence", "primary-voice", "fallback-voice")
    assert len(audio) > 0
    assert chain.last_provider_used == "primary"
    assert primary.call_count == 1
    assert fallback.call_count == 0


@pytest.mark.asyncio
async def test_audio_fallback_chain_failover():
    """Verifies graceful failover to fallback TTS when primary fails (e.g. 403 or offline)."""
    primary = MockTTSProvider(should_fail=True, fail_error=ConnectionError("Microsoft 403 Forbidden"))
    fallback = MockTTSProvider()
    chain = AudioFallbackChain(primary, fallback)

    audio = await chain.generate_speech("Test sentence", "primary-voice", "fallback-voice")
    assert len(audio) > 0
    assert chain.last_provider_used == "fallback"
    assert primary.call_count == 1
    assert fallback.call_count == 1


def test_stitch_audio_turns():
    """Verifies concatenation of multiple speaker turns into a single valid WAV stream."""
    turn_1 = create_mock_wav_bytes(duration_seconds=1.0)
    turn_2 = create_mock_wav_bytes(duration_seconds=1.5)
    turn_3 = create_mock_wav_bytes(duration_seconds=2.0)

    combined = stitch_audio_turns([turn_1, turn_2, turn_3])
    assert len(combined) > 0

    with wave.open(io.BytesIO(combined), "rb") as w:
        duration = w.getnframes() / w.getframerate()
        assert round(duration, 1) == 4.5  # 1.0 + 1.5 + 2.0


def test_stitch_audio_empty_raises():
    """Verifies that stitching an empty dialogue list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot stitch empty audio list"):
        stitch_audio_turns([])
