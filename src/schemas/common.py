"""
TechSift AI - Common Pydantic Response & Error Schemas.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(None, description="Optional diagnostic details")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always False for error responses")
    error: ErrorDetail


class PaginationMetadata(BaseModel):
    total: int = Field(..., description="Total number of items available")
    skip: int = Field(..., description="Number of items skipped (offset)")
    limit: int = Field(..., description="Maximum items returned")
    page: int = Field(..., description="Current page number (1-indexed)")
    total_pages: int = Field(..., description="Total pages available")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMetadata
