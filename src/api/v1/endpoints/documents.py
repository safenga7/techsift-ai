"""
TechSift AI - Document Management Endpoints.
Handles document uploads, paginated listings, retrieval, and deletions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel
from src.api.dependencies import get_document_service
from src.schemas.common import ErrorResponse
from src.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatsResponse,
    DocumentStatus,
)
from src.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentDeleteResponse(BaseModel):
    success: bool = True
    message: str
    id: str


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Process Document",
    description=(
        "Accepts a technical PDF, TXT, or Markdown document. "
        "Validates magic signatures, extracts text, and stores metadata in SQLite."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format or corrupt content"},
        413: {"model": ErrorResponse, "description": "File exceeds maximum size limit"},
        422: {"model": ErrorResponse, "description": "Unsupported document (e.g. scanned image-only PDF)"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.pdf, .txt, .md)"),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    from src.services.document_service import read_upload_stream_with_size_limit

    # Enforce size limits while reading streaming chunks into memory
    content = await read_upload_stream_with_size_limit(file)
    filename = file.filename or "uploaded_document"
    doc = await service.upload_document(filename=filename, content=content)
    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Documents with Pagination",
    description="Returns a paginated list of documents with optional filtering by status.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    status_filter = status.value if status else None
    return await service.list_documents(page=page, page_size=page_size, status=status_filter)


@router.get(
    "/stats",
    response_model=DocumentStatsResponse,
    summary="Get Document and Summary Aggregates",
    description=(
        "Computes document collection totals, status counts, issues count, and completed summaries "
        "across the entire applicable collection, independently of pagination."
    ),
)
async def get_document_stats(
    service: DocumentService = Depends(get_document_service),
) -> DocumentStatsResponse:
    return await service.get_stats()


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Retrieve Document Details",
    description="Returns metadata and full extracted text for a specific document.",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    doc = await service.get_document(document_id)
    return DocumentDetailResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Deletes document record from database and purges file from local storage.",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    await service.delete_document(document_id)
    return DocumentDeleteResponse(
        success=True,
        message="Document and associated files successfully deleted.",
        id=document_id,
    )
