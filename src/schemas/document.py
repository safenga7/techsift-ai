"""
TechSift AI - Document Pydantic Request & Response Schemas.
Never exposes internal filesystem paths or raw server secrets.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.common import PaginationMetadata


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class DocumentResponse(BaseModel):
    """Public summary representation of a document."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original user file name")
    file_type: str = Field(..., description="File extension/type (pdf, txt, md)")
    file_size: int = Field(..., description="File size in bytes")
    word_count: int = Field(..., description="Calculated word count of extracted text")
    page_count: Optional[int] = Field(None, description="Page count (for PDF files)")
    status: DocumentStatus = Field(..., description="Processing status")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    created_at: datetime = Field(..., description="Timestamp of document creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")


class DocumentDetailResponse(DocumentResponse):
    """Detailed document representation including full extracted text."""
    extracted_text: Optional[str] = Field(None, description="Extracted plain text content")


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: List[DocumentResponse]
    pagination: PaginationMetadata


class DocumentStatsResponse(BaseModel):
    """Aggregate statistics for documents and summaries across the entire collection."""
    total_documents: int = Field(..., description="Total count of all ingested documents")
    processed_documents: int = Field(..., description="Count of successfully processed documents")
    pending_documents: int = Field(..., description="Count of pending documents")
    failed_documents: int = Field(..., description="Count of failed documents")
    unsupported_documents: int = Field(..., description="Count of unsupported documents")
    issues_documents: int = Field(..., description="Count of issues (failed plus unsupported)")
    total_summaries: int = Field(..., description="Count of completed generated summaries across all documents")

