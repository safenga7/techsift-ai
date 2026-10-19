"""
TechSift AI - FastAPI Dependency Injection.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.services.assessment_service import AssessmentService
from src.services.document_service import DocumentService
from src.services.learning_progress_service import LearningProgressService
from src.services.learning_path_service import LearningPathService
from src.services.summary_service import SummaryService


async def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    """Dependency provider for DocumentService with injected database session."""
    return DocumentService(db)


async def get_summary_service(
    db: AsyncSession = Depends(get_db),
) -> SummaryService:
    """Dependency provider for SummaryService with injected database session."""
    return SummaryService(db)


async def get_learning_path_service(
    db: AsyncSession = Depends(get_db),
) -> LearningPathService:
    """Dependency provider for LearningPathService with injected database session."""
    return LearningPathService(db)


async def get_assessment_service(
    db: AsyncSession = Depends(get_db),
) -> AssessmentService:
    """Dependency provider for AssessmentService with injected database session."""
    return AssessmentService(db)


async def get_learning_progress_service(
    db: AsyncSession = Depends(get_db),
) -> LearningProgressService:
    """Dependency provider for LearningProgressService with injected database session."""
    return LearningProgressService(db)
