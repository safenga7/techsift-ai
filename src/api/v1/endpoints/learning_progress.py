"""
TechSift AI - Learning Progress & Dashboard Endpoints (Phase 5C).
Provides REST APIs for tracking lesson completion, retrieving curriculum progress,
deterministic knowledge mastery, explainable recommendations, and resume continuity.
"""

import logging
from fastapi import APIRouter, Depends, status
from src.api.dependencies import get_learning_progress_service
from src.schemas.learning_progress import (
    LearningDashboardResponse,
    LearningRecommendationsResponse,
    LessonProgressResponse,
    PathProgressOverviewResponse,
    ResumeLearningResponse,
    UpdateLessonProgressRequest,
)
from src.services.learning_progress_service import LearningProgressService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Learning Progress & Dashboard"])


@router.get(
    "/learning-paths/{path_id}/progress",
    response_model=PathProgressOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Learning Path Progress Overview",
)
async def get_learning_path_progress(
    path_id: str,
    service: LearningProgressService = Depends(get_learning_progress_service),
) -> PathProgressOverviewResponse:
    """Calculates real-time completion percentages and module lesson breakdown."""
    return await service.get_path_progress(path_id)


@router.get(
    "/learning-paths/{path_id}/dashboard",
    response_model=LearningDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Consolidated Learning Dashboard",
)
async def get_learning_path_dashboard(
    path_id: str,
    service: LearningProgressService = Depends(get_learning_progress_service),
) -> LearningDashboardResponse:
    """Returns unified dashboard including progress, assessments, mastery, and recommendations."""
    return await service.get_dashboard(path_id)


@router.get(
    "/learning-paths/{path_id}/recommendations",
    response_model=LearningRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Rule-Based Pedagogical Recommendations",
)
async def get_learning_path_recommendations(
    path_id: str,
    service: LearningProgressService = Depends(get_learning_progress_service),
) -> LearningRecommendationsResponse:
    """Returns explainable learning recommendations based on progress and quiz history."""
    return await service.get_recommendations(path_id)


@router.get(
    "/learning-paths/{path_id}/resume",
    response_model=ResumeLearningResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Resume Learning Target",
)
async def get_resume_target(
    path_id: str,
    service: LearningProgressService = Depends(get_learning_progress_service),
) -> ResumeLearningResponse:
    """Resolves the last visited or next incomplete lesson for instant session continuity."""
    return await service.get_resume_target(path_id)


@router.put(
    "/lessons/{lesson_id}/progress",
    response_model=LessonProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Lesson Reading Progress",
)
async def update_lesson_progress(
    lesson_id: str,
    request: UpdateLessonProgressRequest,
    service: LearningProgressService = Depends(get_learning_progress_service),
) -> LessonProgressResponse:
    """
    Updates lesson status (in_progress or completed).
    Completed lessons are protected from reverting to in_progress.
    """
    return await service.update_lesson_progress(lesson_id, request)
