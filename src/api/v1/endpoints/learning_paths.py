"""
TechSift AI - Learning Path Endpoints (Phase 5A).
Handles curriculum generation, caching, and retrieval of structured learning paths.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, Path, Query, status
from src.api.dependencies import get_learning_path_service
from src.schemas.common import ErrorResponse
from src.schemas.learning_path import (
    CreateLearningPathRequest,
    DifficultyEnum,
    LearningPathListResponse,
    LearningPathResponse,
)
from src.schemas.summary import LanguageEnum
from src.services.learning_path_service import LearningPathService

router = APIRouter(tags=["Learning Studio"])


@router.post(
    "/documents/{document_id}/learning-paths",
    response_model=LearningPathResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Learning Path",
    description=(
        "Initiates bilingual (Arabic or English) structured learning path generation "
        "at configurable difficulty levels ('beginner', 'intermediate', 'advanced'). "
        "Returns cached result immediately if an identical completed path exists."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        422: {"model": ErrorResponse, "description": "Unsupported document or extraction failure"},
    },
)
async def create_learning_path(
    document_id: str = Path(..., description="Document UUID"),
    payload: Optional[CreateLearningPathRequest] = Body(None, description="Generation options"),
    language: Optional[LanguageEnum] = Query(None, description="Override target language ('en' or 'ar')"),
    difficulty: Optional[DifficultyEnum] = Query(None, description="Override difficulty level"),
    wait: bool = Query(True, description="Whether to wait for completion or return pending job"),
    service: LearningPathService = Depends(get_learning_path_service),
) -> LearningPathResponse:
    target_lang = language or (payload.language if payload else LanguageEnum.EN)
    target_difficulty = difficulty or (payload.difficulty if payload else DifficultyEnum.INTERMEDIATE)

    return await service.generate_learning_path(
        document_id=document_id,
        language=target_lang,
        difficulty=target_difficulty,
        wait=wait,
    )


@router.get(
    "/documents/{document_id}/learning-paths",
    response_model=LearningPathListResponse,
    summary="List Document Learning Paths",
    description="Returns all generated learning paths for a specific document.",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def list_document_learning_paths(
    document_id: str = Path(..., description="Document UUID"),
    service: LearningPathService = Depends(get_learning_path_service),
) -> LearningPathListResponse:
    return await service.list_learning_paths_for_document(document_id)


@router.get(
    "/learning-paths/{learning_path_id}",
    response_model=LearningPathResponse,
    summary="Retrieve Learning Path by ID",
    description="Returns full structured learning path by its UUID including modules and lessons.",
    responses={
        404: {"model": ErrorResponse, "description": "Learning path not found"},
    },
)
async def get_learning_path(
    learning_path_id: str = Path(..., description="Learning Path UUID"),
    service: LearningPathService = Depends(get_learning_path_service),
) -> LearningPathResponse:
    return await service.get_learning_path(learning_path_id)
