"""
TechSift AI - Summary Pydantic Request & Response Schemas.
Enforces strict structured JSON validation for bilingual AI-generated content.
"""

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


class LanguageEnum(str, Enum):
    AR = "ar"
    EN = "en"


class DetailLevelEnum(str, Enum):
    SHORT = "short"
    STANDARD = "standard"
    DETAILED = "detailed"


class SummaryStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConceptItem(BaseModel):
    """Represents an extracted technical term, acronym, or definition."""
    term: str = Field(..., description="Technical term or acronym (e.g. 'Raft Consensus' or 'خوارزمية Raft')")
    definition: str = Field(..., description="Contextual definition derived strictly from document")
    relationships: Optional[List[str]] = Field(
        default=None,
        description="Associated technical concepts or components",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category classification if provided",
    )


class TechnicalSummaryContent(BaseModel):
    """
    Structured technical document summary.
    Omits missing or non-applicable sections rather than fabricating content.
    """
    executive_summary: str = Field(..., description="High-level technical executive summary")
    main_concepts: List[ConceptItem] = Field(default_factory=list, description="Core technical concepts identified")
    key_findings: List[str] = Field(default_factory=list, description="Key research or engineering findings")
    important_definitions: List[ConceptItem] = Field(default_factory=list, description="Important terminology definitions")
    architecture_overview: Optional[str] = Field(
        None,
        description="Technical architecture overview, if applicable to document",
    )
    practical_applications: List[str] = Field(default_factory=list, description="Real-world practical engineering applications")
    limitations: List[str] = Field(default_factory=list, description="Important limitations or trade-offs mentioned in source")
    key_takeaways: List[str] = Field(default_factory=list, description="Actionable architectural or technical takeaways")
    source_pages: List[int] = Field(
        default_factory=list,
        description="Referenced document page numbers (never fabricated)",
    )
    source_chunks: List[int] = Field(
        default_factory=list,
        description="Referenced chunk indices",
    )
    disclaimer: str = Field(
        default="Source references indicate origin context and are not an independent proof of factual correctness.",
        description="Notice on AI source citation boundaries",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_summary_content(cls, data: Any) -> Any:
        """
        Tolerantly normalizes legacy or synonymous schema keys (e.g. executive_overview -> executive_summary,
        concepts_taxonomy -> main_concepts, citations -> source_chunks).
        """
        if isinstance(data, dict):
            normalized = dict(data)
            # 1. Normalize executive_overview -> executive_summary
            if "executive_summary" not in normalized and "executive_overview" in normalized:
                normalized["executive_summary"] = normalized["executive_overview"]

            # 2. Normalize concepts_taxonomy -> main_concepts
            if "main_concepts" not in normalized and "concepts_taxonomy" in normalized:
                normalized["main_concepts"] = normalized["concepts_taxonomy"]

            # 3. Normalize citations -> source_chunks if absent
            if ("source_chunks" not in normalized or not normalized["source_chunks"]) and "citations" in normalized:
                chunks = []
                for cit in normalized.get("citations", []):
                    if isinstance(cit, dict):
                        pc = cit.get("page_chunk", "")
                        m = re.search(r"Chunk\s*(\d+)", pc, re.IGNORECASE)
                        if m:
                            c_idx = int(m.group(1))
                            if c_idx not in chunks:
                                chunks.append(c_idx)
                if chunks:
                    normalized["source_chunks"] = chunks

            return normalized
        return data


class SummaryCreateRequest(BaseModel):
    """Request payload for initiating document summarization."""
    language: LanguageEnum = Field(default=LanguageEnum.EN, description="Target summary language ('ar' or 'en')")
    detail_level: DetailLevelEnum = Field(
        default=DetailLevelEnum.STANDARD,
        description="Summary depth: 'short', 'standard', or 'detailed'",
    )


class SummaryResponse(BaseModel):
    """Public representation of a generated document summary."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique summary UUID")
    document_id: str = Field(..., description="Associated document UUID")
    language: str = Field(..., description="Summary language ('ar' or 'en')")
    detail_level: str = Field(..., description="Detail level ('short', 'standard', 'detailed')")
    model_used: str = Field(..., description="AI model used for generation")
    status: SummaryStatusEnum = Field(..., description="Processing status")
    is_cached: bool = Field(default=False, description="Whether summary was served from SQLite cache")
    summary: Optional[TechnicalSummaryContent] = Field(None, description="Structured technical summary content")
    error_message: Optional[str] = Field(None, description="Diagnostic error message if generation failed")
    created_at: datetime = Field(..., description="Summary creation timestamp")
    updated_at: datetime = Field(..., description="Summary last updated timestamp")

    @classmethod
    def from_orm_model(cls, summary_obj, is_cached: bool = False) -> "SummaryResponse":
        content = None
        if summary_obj.content_data:
            try:
                content = TechnicalSummaryContent.model_validate(summary_obj.content_data)
            except Exception as e:
                logger.warning(
                    f"Failed to validate summary content_data for summary {summary_obj.id}: {e}"
                )

        return cls(
            id=summary_obj.id,
            document_id=summary_obj.document_id,
            language=summary_obj.language,
            detail_level=summary_obj.detail_level,
            model_used=summary_obj.model_used,
            status=SummaryStatusEnum(summary_obj.status),
            is_cached=is_cached,
            summary=content,
            error_message=summary_obj.error_message,
            created_at=summary_obj.created_at,
            updated_at=summary_obj.updated_at,
        )


class SummaryListResponse(BaseModel):
    """List of summaries generated for a document."""
    items: List[SummaryResponse]
    total: int
