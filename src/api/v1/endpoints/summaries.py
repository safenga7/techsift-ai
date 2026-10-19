"""
TechSift AI - Document Summarization Endpoints.
Handles bilingual summary generation, SQLite cache retrieval, and summary queries.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, Path, Query, status
from src.api.dependencies import get_summary_service
from src.schemas.common import ErrorResponse
from src.schemas.summary import (
    DetailLevelEnum,
    LanguageEnum,
    SummaryCreateRequest,
    SummaryListResponse,
    SummaryResponse,
)
from src.services.summary_service import SummaryService

router = APIRouter(tags=["Summaries"])


@router.post(
    "/documents/{document_id}/summaries",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Document Summary",
    description=(
        "Initiates bilingual (Arabic or English) technical summarization. "
        "Returns cached result immediately if an identical summary exists."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        422: {"model": ErrorResponse, "description": "Unsupported document or empty extraction"},
    },
)
async def create_document_summary(
    document_id: str = Path(..., description="Document UUID"),
    payload: Optional[SummaryCreateRequest] = Body(None, description="Summarization options"),
    language: Optional[LanguageEnum] = Query(None, description="Override target language ('ar' or 'en')"),
    detail_level: Optional[DetailLevelEnum] = Query(None, description="Override detail level"),
    wait: bool = Query(True, description="Whether to wait for completion or return pending job"),
    service: SummaryService = Depends(get_summary_service),
) -> SummaryResponse:
    target_lang = language or (payload.language if payload else LanguageEnum.EN)
    target_detail = detail_level or (payload.detail_level if payload else DetailLevelEnum.STANDARD)

    return await service.generate_summary(
        document_id=document_id,
        language=target_lang,
        detail_level=target_detail,
        wait=wait,
    )


@router.get(
    "/documents/{document_id}/summaries",
    response_model=SummaryListResponse,
    summary="List Document Summaries",
    description="Returns all generated summaries for a specific document.",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def list_document_summaries(
    document_id: str = Path(..., description="Document UUID"),
    service: SummaryService = Depends(get_summary_service),
) -> SummaryListResponse:
    return await service.list_summaries_for_document(document_id)


@router.get(
    "/summaries/{summary_id}",
    response_model=SummaryResponse,
    summary="Retrieve Summary by ID",
    description="Returns full structured technical summary by its unique summary UUID.",
    responses={
        404: {"model": ErrorResponse, "description": "Summary not found"},
    },
)
async def get_summary(
    summary_id: str = Path(..., description="Summary UUID"),
    service: SummaryService = Depends(get_summary_service),
) -> SummaryResponse:
    return await service.get_summary(summary_id)
