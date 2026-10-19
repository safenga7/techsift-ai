"""
TechSift AI - Learning Path Pydantic Schemas (Phase 5A).
Defines validation schemas for curriculum generation, strict source-grounded citations,
and REST API payloads.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.summary import LanguageEnum


class DifficultyEnum(str, Enum):
    """Pedagogical difficulty level of the generated curriculum."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# AI Structured Generation & Grounding Schemas
# ---------------------------------------------------------------------------

class SourceReference(BaseModel):
    """Explicitly verified citation mapping pedagogical content to document source."""
    page_number: Optional[int] = Field(None, description="Source PDF page number (1-indexed)")
    chunk_index: Optional[int] = Field(None, description="Source chunk index (0-indexed)")
    section_title: Optional[str] = Field(None, description="Source section or heading title")
    citation_text: Optional[str] = Field(None, description="Direct supporting fact or quote from document")


class KeyConceptItem(BaseModel):
    """Core technical concept, architectural term, or acronym."""
    term: str = Field(..., description="Technical term (preserves English name alongside Arabic if in AR mode)")
    explanation: str = Field(..., description="Grounded explanation derived from the document")


class GeneratedLesson(BaseModel):
    """Granular instructional lesson with grounding, concepts, and examples."""
    title: str = Field(..., description="Action-oriented lesson title")
    explanation: str = Field(..., description="In-depth, source-grounded technical explanation")
    key_concepts: List[KeyConceptItem] = Field(default_factory=list, description="Core concepts introduced in this lesson")
    examples: List[str] = Field(default_factory=list, description="Practical real-world code, architecture, or workflow examples")
    source_references: List[SourceReference] = Field(default_factory=list, description="Strictly verified document citations")
    sequence_order: int = Field(default=1, description="Order index within the module")
    estimated_duration_minutes: int = Field(default=10, description="Estimated reading/comprehension time")


class GeneratedModule(BaseModel):
    """Sequential learning module grouping related lessons."""
    title: str = Field(..., description="Module title")
    description: Optional[str] = Field(None, description="Brief narrative summary of this module")
    learning_objectives: List[str] = Field(default_factory=list, description="Key skills and takeaways gained from this module")
    sequence_order: int = Field(default=1, description="Order index within the learning path")
    estimated_duration_minutes: int = Field(default=30, description="Aggregated duration for module lessons")
    lessons: List[GeneratedLesson] = Field(default_factory=list, description="Ordered lessons in this module")


class GeneratedLearningPathContent(BaseModel):
    """Complete structured curriculum produced by the Gemini AI Provider."""
    title: str = Field(..., description="Curriculum title")
    description: str = Field(..., description="Comprehensive overview of the learning path")
    prerequisites: List[str] = Field(default_factory=list, description="Required foundational technical knowledge")
    learning_objectives: List[str] = Field(default_factory=list, description="Overarching course learning outcomes")
    estimated_duration_minutes: int = Field(default=60, description="Total estimated duration in minutes")
    modules: List[GeneratedModule] = Field(default_factory=list, description="Ordered sequential modules")


# ---------------------------------------------------------------------------
# REST API Request & Response Schemas
# ---------------------------------------------------------------------------

class CreateLearningPathRequest(BaseModel):
    """Request payload to initiate learning path generation."""
    language: LanguageEnum = Field(default=LanguageEnum.EN, description="Target curriculum language ('en' or 'ar')")
    difficulty: DifficultyEnum = Field(default=DifficultyEnum.INTERMEDIATE, description="Target difficulty level")


class LessonResponse(BaseModel):
    """API view for a single lesson."""
    id: str
    module_id: str
    title: str
    explanation: str
    key_concepts: List[Any] = Field(default_factory=list)
    examples: List[Any] = Field(default_factory=list)
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
    sequence_order: int
    estimated_duration_minutes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuleResponse(BaseModel):
    """API view for a module with nested lessons."""
    id: str
    learning_path_id: str
    title: str
    description: Optional[str] = None
    learning_objectives: List[str] = Field(default_factory=list)
    sequence_order: int
    estimated_duration_minutes: int
    lessons: List[LessonResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningPathResponse(BaseModel):
    """Complete API response for a learning path."""
    id: str
    document_id: str
    language: str
    difficulty: str
    title: str
    description: Optional[str] = None
    estimated_duration_minutes: int
    status: str
    error_message: Optional[str] = None
    prerequisites: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    modules: List[ModuleResponse] = Field(default_factory=list)
    is_cached: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, path: Any, is_cached: bool = False) -> "LearningPathResponse":
        """Transforms SQLAlchemy LearningPath model into typed Pydantic response."""
        modules_res = []
        for m in getattr(path, "modules", []) or []:
            lessons_res = [
                LessonResponse(
                    id=l.id,
                    module_id=l.module_id,
                    title=l.title,
                    explanation=l.explanation,
                    key_concepts=l.key_concepts or [],
                    examples=l.examples or [],
                    source_references=l.source_references or [],
                    sequence_order=l.sequence_order,
                    estimated_duration_minutes=l.estimated_duration_minutes,
                    created_at=l.created_at,
                )
                for l in getattr(m, "lessons", []) or []
            ]
            modules_res.append(
                ModuleResponse(
                    id=m.id,
                    learning_path_id=m.learning_path_id,
                    title=m.title,
                    description=m.description,
                    learning_objectives=m.learning_objectives or [],
                    sequence_order=m.sequence_order,
                    estimated_duration_minutes=m.estimated_duration_minutes,
                    lessons=lessons_res,
                    created_at=m.created_at,
                )
            )

        return cls(
            id=path.id,
            document_id=path.document_id,
            language=path.language,
            difficulty=path.difficulty,
            title=path.title,
            description=path.description,
            estimated_duration_minutes=path.estimated_duration_minutes,
            status=path.status,
            error_message=path.error_message,
            prerequisites=path.prerequisites or [],
            learning_objectives=path.learning_objectives or [],
            modules=modules_res,
            is_cached=is_cached,
            created_at=path.created_at,
            updated_at=path.updated_at,
        )


class LearningPathListResponse(BaseModel):
    """List response for document learning paths."""
    items: List[LearningPathResponse]
    total: int
