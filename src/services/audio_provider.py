"""
TechSift AI - Audio Provider & Speech Synthesis Engines.
Provides Edge-TTS (primary cloud neural) and offline fallbacks (Piper / local).
"""

from abc import ABC, abstractmethod
import asyncio
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional
import edge_tts
from src.core.config import settings
from src.core.exceptions import TTSConnectionError, TTSVoiceUnavailableError

logger = logging.getLogger(__name__)

# Standard production voice catalog verified in Phase 4A
VERIFIED_VOICES: Dict[str, Dict[str, str]] = {
    "ar": {
        "male": "ar-EG-ShakirNeural",
        "female": "ar-EG-SalmaNeural",
    },
    "en": {
        "male": "en-US-GuyNeural",
        "female": "en-US-JennyNeural",
    },
}


class AudioProvider(ABC):
    """Abstract interface for text-to-speech synthesis."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> bytes:
        """Synthesizes text into audio bytes (e.g. MP3 or WAV)."""
        pass

    @abstractmethod
    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        """Lists available voice profiles."""
        pass


class EdgeTTSProvider(AudioProvider):
    """
    Primary Zero-Cost Neural Text-to-Speech Provider using Microsoft Edge Read Aloud.
    Offers high prosody and natural bilingual speech (32 Arabic, 47 English voices).
    """

    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds

    async def synthesize(self, text: str, voice: str) -> bytes:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot synthesize empty text.")

        buffer = io.BytesIO()
        try:
            communicate = edge_tts.Communicate(text=clean_text, voice=voice)
            
            async def _stream_chunks():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buffer.write(chunk["data"])

            await asyncio.wait_for(_stream_chunks(), timeout=self.timeout_seconds)
            
            audio_data = buffer.getvalue()
            if not audio_data:
                raise TTSConnectionError("Edge-TTS generated empty audio stream.")
            return audio_data

        except asyncio.TimeoutError:
            logger.error(f"Edge-TTS synthesis timed out after {self.timeout_seconds}s for voice '{voice}'")
            raise TTSConnectionError(f"Speech synthesis timed out after {self.timeout_seconds} seconds.")
        except Exception as exc:
            error_str = str(exc)
            logger.error(f"Edge-TTS error: {exc}")
            if "403" in error_str or "Handshake" in error_str:
                raise TTSConnectionError(
                    "Edge-TTS connection was rejected (403 Forbidden). Ensure edge-tts is updated to latest release."
                )
            raise TTSConnectionError(f"Failed to synthesize audio: {error_str}")

    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        try:
            voices = await edge_tts.list_voices()
            results = []
            for v in voices:
                locale = v.get("Locale", "")
                short_name = v.get("ShortName", "")
                gender = v.get("Gender", "Unknown")
                
                lang_code = locale.split("-")[0].lower()
                if language and lang_code != language.lower():
                    continue

                results.append({
                    "id": short_name,
                    "name": short_name,
                    "language": lang_code,
                    "gender": gender.lower(),
                    "locale": locale,
                })
            return results
        except Exception as exc:
            logger.warning(f"Failed to query dynamic Edge-TTS voice list: {exc}. Using verified defaults.")
            # Fallback to verified catalog
            return [
                {"id": "ar-EG-ShakirNeural", "name": "Shakir (Arabic Male)", "language": "ar", "gender": "male", "locale": "ar-EG"},
                {"id": "ar-EG-SalmaNeural", "name": "Salma (Arabic Female)", "language": "ar", "gender": "female", "locale": "ar-EG"},
                {"id": "en-US-GuyNeural", "name": "Guy (English Male)", "language": "en", "gender": "male", "locale": "en-US"},
                {"id": "en-US-JennyNeural", "name": "Jenny (English Female)", "language": "en", "gender": "female", "locale": "en-US"},
            ]


class PiperTTSProvider(AudioProvider):
    """
    Local Offline Neural TTS Provider (via Piper ONNX models).
    Runs entirely on-device on Apple Silicon CPU with zero internet connection.
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or (settings.STORAGE_DIR / "piper_models")

    async def synthesize(self, text: str, voice: str) -> bytes:
        import wave
        from piper import PiperVoice

        model_file = self.models_dir / f"{voice}.onnx"
        config_file = self.models_dir / f"{voice}.onnx.json"

        if not model_file.exists():
            raise TTSVoiceUnavailableError(
                f"Local Piper model '{voice}' was not found at {model_file}."
            )

        def _run_piper_syn() -> bytes:
            voice_engine = PiperVoice.load(str(model_file), config_path=str(config_file))
            out_buf = io.BytesIO()
            with wave.open(out_buf, "wb") as wav_file:
                voice_engine.synthesize_wav(text, wav_file)
            return out_buf.getvalue()

        return await asyncio.to_thread(_run_piper_syn)

    async def list_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        return [
            {"id": "en_US-lessac-low", "name": "Lessac (English)", "language": "en", "gender": "female", "locale": "en-US"},
            {"id": "ar_JO-kareem-low", "name": "Kareem (Arabic)", "language": "ar", "gender": "male", "locale": "ar-JO"},
        ]


def get_default_voice(language: str, gender: str = "male") -> str:
    """Returns the verified default voice identifier for a given language and gender."""
    lang_key = language.lower()
    gender_key = gender.lower()
    if lang_key in VERIFIED_VOICES and gender_key in VERIFIED_VOICES[lang_key]:
        return VERIFIED_VOICES[lang_key][gender_key]
    return "en-US-GuyNeural"
