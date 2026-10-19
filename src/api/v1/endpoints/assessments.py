"""
TechSift AI - Assessment & Quiz Endpoints (Phase 5B).
Provides REST endpoints for assessment creation, taker question delivery (without answer leaks),
attempt management, answer recording, and local deterministic grading.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, Path, Query, status

from src.api.dependencies import get_assessment_service
from src.schemas.assessment import (
    AnswerRecordResponse,
    AssessmentAttemptResponse,
    AssessmentDetailResponse,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentTypeEnum,
    AttemptResultResponse,
    CreateAssessmentRequest,
    SubmitAnswerRequest,
)
from src.schemas.common import ErrorResponse
from src.services.assessment_service import AssessmentService

router = APIRouter(tags=["Assessments & Quizzes"])


@router.post(
    "/learning-paths/{path_id}/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Retrieve Assessment",
    description=(
        "Initiates interactive assessment generation for a lesson, module, or entire learning path. "
        "Checks SQLite cache first and returns existing completed assessments with zero API consumption."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scope or missing required parent ID"},
        404: {"model": ErrorResponse, "description": "LearningPath, Module, or Lesson not found"},
    },
)
async def create_assessment(
    path_id: str = Path(..., description="Learning Path UUID"),
    payload: CreateAssessmentRequest = Body(...),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    return await service.get_or_create_assessment(
        learning_path_id=path_id,
        request=payload,
    )


@router.get(
    "/learning-paths/{path_id}/assessments",
    response_model=AssessmentListResponse,
    summary="List Assessments for Learning Path",
    description="Returns all generated assessments associated with a specific curriculum.",
)
async def list_assessments(
    path_id: str = Path(..., description="Learning Path UUID"),
    assessment_type: Optional[AssessmentTypeEnum] = Query(None, description="Filter by assessment type"),
    module_id: Optional[str] = Query(None, description="Filter by module UUID"),
    lesson_id: Optional[str] = Query(None, description="Filter by lesson UUID"),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentListResponse:
    return await service.list_assessments(
        learning_path_id=path_id,
        assessment_type=assessment_type.value if assessment_type else None,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentDetailResponse,
    summary="Get Assessment for Test Taker",
    description=(
        "Retrieves assessment metadata and questions prepared for active test-taking. "
        "CRITICAL: Correct answers and explanations are strictly omitted to prevent cheating."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Assessment not found"},
    },
)
async def get_assessment(
    assessment_id: str = Path(..., description="Assessment UUID"),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentDetailResponse:
    return await service.get_assessment_detail(assessment_id)


@router.post(
    "/assessments/{assessment_id}/attempts",
    response_model=AssessmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Assessment Attempt",
    description="Initializes a new test-taking session for a completed assessment.",
    responses={
        400: {"model": ErrorResponse, "description": "Assessment is not completed or cannot be attempted"},
        404: {"model": ErrorResponse, "description": "Assessment not found"},
    },
)
async def start_attempt(
    assessment_id: str = Path(..., description="Assessment UUID"),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentAttemptResponse:
    return await service.start_attempt(assessment_id)


@router.post(
    "/attempts/{attempt_id}/answers",
    response_model=AnswerRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Question Answer",
    description=(
        "Records an answer to a question in an active attempt. "
        "Validates question belongs to attempt's assessment and prevents duplicate submissions."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Attempt completed, duplicate answer, or invalid option"},
        404: {"model": ErrorResponse, "description": "Attempt or Question not found"},
    },
)
async def submit_answer(
    attempt_id: str = Path(..., description="Attempt UUID"),
    payload: SubmitAnswerRequest = Body(...),
    service: AssessmentService = Depends(get_assessment_service),
) -> AnswerRecordResponse:
    return await service.submit_answer(attempt_id, payload)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AttemptResultResponse,
    summary="Finalize and Grade Attempt",
    description=(
        "Calculates final score, percentage, and pass/fail status. "
        "Reveals correct answers, explanations, and source references for full educational review. Idempotent."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Attempt not found"},
    },
)
async def submit_attempt(
    attempt_id: str = Path(..., description="Attempt UUID"),
    service: AssessmentService = Depends(get_assessment_service),
) -> AttemptResultResponse:
    return await service.submit_attempt(attempt_id)


@router.get(
    "/attempts/{attempt_id}/results",
    response_model=AttemptResultResponse,
    summary="Get Graded Attempt Results",
    description="Retrieves the final graded results and review of a completed assessment attempt.",
    responses={
        400: {"model": ErrorResponse, "description": "Attempt is still in progress"},
        404: {"model": ErrorResponse, "description": "Attempt not found"},
    },
)
async def get_attempt_results(
    attempt_id: str = Path(..., description="Attempt UUID"),
    service: AssessmentService = Depends(get_assessment_service),
) -> AttemptResultResponse:
    return await service.get_attempt_results(attempt_id)
