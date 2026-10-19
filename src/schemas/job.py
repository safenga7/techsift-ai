"""
TechSift AI - ProcessingJob Pydantic Schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique job UUID")
    document_id: str = Field(..., description="Associated document UUID")
    job_type: str = Field(..., description="Job type (extraction, summarization, audio)")
    status: str = Field(..., description="Job status (pending, in_progress, completed, failed)")
    error_message: Optional[str] = Field(None, description="Diagnostic error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
