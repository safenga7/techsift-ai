"""
TechSift AI - Pydantic V2 Schemas for Audio Studio & Podcast Subsystem.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AudioModeEnum(str, Enum):
    NARRATION = "narration"
    PODCAST = "podcast"


class AudioLanguageEnum(str, Enum):
    AR = "ar"
    EN = "en"


class AudioVoiceGenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"


class PodcastTurn(BaseModel):
    """Single speaker turn in a technical podcast dialogue."""

    model_config = ConfigDict(extra="ignore")

    turn: int = Field(..., description="1-indexed sequence number of the turn")
    speaker: str = Field(..., description="Role/Name of the speaker (e.g. Host, Co-host)")
    voice: str = Field(..., description="TTS voice identifier (e.g. ar-EG-ShakirNeural)")
    text: str = Field(..., min_length=2, description="Dialogue text spoken during this turn")


class PodcastScript(BaseModel):
    """Structured, grounded script for a two-speaker educational podcast episode."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=3, description="Episode title")
    language: AudioLanguageEnum = Field(..., description="Language of the podcast dialogue")
    host_role: str = Field(default="Host", description="Description or name of the host")
    cohost_role: str = Field(default="Co-host", description="Description or name of the co-host")
    turns: List[PodcastTurn] = Field(..., min_length=2, max_length=12, description="Dialogue turns")
    source_references: Optional[List[str]] = Field(default=None, description="Grounded source citations or concepts")


class CreateAudioRequest(BaseModel):
    """Payload to request audio narration or podcast generation."""

    model_config = ConfigDict(extra="ignore")

    mode: AudioModeEnum = Field(
        default=AudioModeEnum.NARRATION,
        description="Audio mode: 'narration' (single-speaker summary) or 'podcast' (two-speaker dialogue)",
    )
    language: AudioLanguageEnum = Field(
        default=AudioLanguageEnum.EN,
        description="Target audio language ('ar' or 'en')",
    )
    summary_id: Optional[str] = Field(
        default=None,
        description="Optional summary ID to ground the narration/podcast on. Defaults to latest summary.",
    )
    gender: Optional[AudioVoiceGenderEnum] = Field(
        default=AudioVoiceGenderEnum.MALE,
        description="Preferred voice gender for narration mode ('male' or 'female')",
    )
    host_voice: Optional[str] = Field(
        default=None,
        description="Optional voice override for podcast host",
    )
    cohost_voice: Optional[str] = Field(
        default=None,
        description="Optional voice override for podcast co-host",
    )
    wait: bool = Field(
        default=False,
        description="If True, wait synchronously until audio finishes. If False, returns immediately with pending track.",
    )


class AudioTrackResponse(BaseModel):
    """API response model for an audio track."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    summary_id: Optional[str] = None
    mode: AudioModeEnum
    language: AudioLanguageEnum
    voice_config: Dict[str, Any]
    script_content: Optional[Dict[str, Any]] = None
    file_size_bytes: int
    duration_seconds: float
    status: str  # "pending", "processing", "completed", "failed"
    error_message: Optional[str] = None
    is_cached: bool = False
    created_at: datetime
    updated_at: datetime


class AudioTrackListResponse(BaseModel):
    """List of audio tracks associated with a document."""

    items: List[AudioTrackResponse]
    total: int


class VoiceItem(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    locale: str


class VoiceCatalogResponse(BaseModel):
    voices: List[VoiceItem]
