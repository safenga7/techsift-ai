"""
TechSift AI - Audio Stitching & Processing Service.
Handles audio concatenation, turn pause injection, format normalization, and duration probing.
"""

import io
import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
from typing import List, Optional, Tuple
from pydub import AudioSegment
from src.core.exceptions import AudioDependencyError
from src.schemas.audio import PodcastScript
from src.services.audio_provider import AudioProvider

logger = logging.getLogger(__name__)


def probe_audio_metadata(file_path: Path) -> Tuple[float, int]:
    """Uses ffprobe to extract exact duration (seconds) and file size (bytes)."""
    file_size = file_path.stat().st_size
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        return round(duration, 2), file_size
    except Exception as exc:
        logger.warning(f"ffprobe metadata extraction failed for {file_path}: {exc}. Fallback to pydub.")
        seg = AudioSegment.from_file(str(file_path))
        duration = round(len(seg) / 1000.0, 2)
        return duration, file_size


def split_into_audio_chunks(text: str, max_chars: int = 700) -> List[str]:
    """
    Splits long narration text into natural semantic chunks
    (by sections, paragraphs, and sentences) strictly under max_chars.
    Prevents Edge-TTS WebSocket stream timeouts on large monolingual/bilingual scripts.
    """
    clean_text = text.strip()
    if not clean_text:
        return []
    if len(clean_text) <= max_chars:
        return [clean_text]

    raw_paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    for para in raw_paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
            continue

        # Split paragraph by sentence boundaries (Arabic & English punctuation)
        sentences = re.split(r"(?<=[.!?؟\n])\s+", para)
        current = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(current) + len(s) + 1 <= max_chars:
                current = f"{current} {s}" if current else s
            else:
                if current:
                    chunks.append(current)
                if len(s) <= max_chars:
                    current = s
                else:
                    # Very long sentence: split by secondary clause punctuation
                    subparts = re.split(r"(?<=[،,;:])\s+", s)
                    sub_curr = ""
                    for sp in subparts:
                        if len(sub_curr) + len(sp) + 1 <= max_chars:
                            sub_curr = f"{sub_curr} {sp}" if sub_curr else sp
                        else:
                            if sub_curr:
                                chunks.append(sub_curr)
                            sub_curr = sp
                    current = sub_curr if sub_curr else ""
        if current:
            chunks.append(current)

    return chunks or [clean_text]


class AudioStitchingService:
    """Orchestrates TTS synthesis and audio segment concatenation."""

    def __init__(self, audio_provider: AudioProvider):
        self.audio_provider = audio_provider

    async def render_narration_audio(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Tuple[float, int]:
        """
        Synthesizes single-speaker technical narration and saves to MP3.
        Chunks long narration text to prevent Edge-TTS stream timeouts,
        injects 350ms natural breathing pauses between paragraphs,
        and standardizes export with 24kHz/48kbps MP3 normalization.
        """
        if not shutil.which("ffmpeg"):
            raise AudioDependencyError(
                "ffmpeg is required for audio synthesis and MP3 export, but was not found on the system PATH. "
                "Installation instructions: macOS: 'brew install ffmpeg' | "
                "Ubuntu/Debian: 'sudo apt install ffmpeg' | Windows: 'winget install Gyan.FFmpeg'"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        chunks = split_into_audio_chunks(text, max_chars=700)
        if not chunks:
            chunks = [text.strip()]

        combined_audio = AudioSegment.empty()
        pause_between_chunks = AudioSegment.silent(duration=350)

        for chunk in chunks:
            chunk_bytes = await self.audio_provider.synthesize(text=chunk, voice=voice)
            chunk_segment = AudioSegment.from_file(io.BytesIO(chunk_bytes))
            if len(combined_audio) > 0:
                combined_audio += pause_between_chunks
            combined_audio += chunk_segment

        padded = AudioSegment.silent(duration=200) + combined_audio + AudioSegment.silent(duration=300)
        padded.export(str(output_path), format="mp3", bitrate="48k")

        return probe_audio_metadata(output_path)

    async def render_podcast_audio(
        self,
        script: PodcastScript,
        output_path: Path,
    ) -> Tuple[float, int]:
        """
        Synthesizes each dialogue turn with its assigned voice,
        injects 450ms conversational pauses, and stitches into a single MP3 episode.
        """
        if not shutil.which("ffmpeg"):
            raise AudioDependencyError(
                "ffmpeg is required for audio synthesis and MP3 export, but was not found on the system PATH. "
                "Installation instructions: macOS: 'brew install ffmpeg' | "
                "Ubuntu/Debian: 'sudo apt install ffmpeg' | Windows: 'winget install Gyan.FFmpeg'"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_audio = AudioSegment.empty()
        pause_between_turns = AudioSegment.silent(duration=450)

        for turn in script.turns:
            turn_bytes = await self.audio_provider.synthesize(text=turn.text, voice=turn.voice)
            turn_segment = AudioSegment.from_file(io.BytesIO(turn_bytes))

            if len(combined_audio) > 0:
                combined_audio += pause_between_turns
            combined_audio += turn_segment

        # Export unified MP3 episode
        combined_audio.export(str(output_path), format="mp3", bitrate="48k")

        return probe_audio_metadata(output_path)
