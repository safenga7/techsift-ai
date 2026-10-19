"""
TechSift AI - Assessment Service (Phase 5B).
Coordinates quiz generation, SQLite caching, background workers, attempt lifecycles,
and deterministic local grading with answer key confidentiality before submission.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import (
    AITimeoutError,
    NotFoundError,
    RateLimitExceededError,
)
from src.db.session import async_session_maker
from src.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
)
from src.models.document import Document
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.processing_job import ProcessingJob
from src.repositories.assessment_repository import AssessmentRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository
from src.repositories.learning_path_repository import LearningPathRepository
from src.schemas.assessment import (
    AnswerRecordResponse,
    AnswerReviewItem,
    AssessmentAttemptResponse,
    AssessmentDetailResponse,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentTypeEnum,
    AttemptResultResponse,
    AttemptStatusEnum,
    CreateAssessmentRequest,
    GeneratedAssessmentContent,
    QuestionForTaker,
    SourceReference,
    SubmitAnswerRequest,
)
from src.services.assessment_generator import (
    AssessmentGenerator,
    assessment_generator,
)

logger = logging.getLogger(__name__)


class AssessmentService:
    """Manages assessment lifecycle, caching, attempts, and zero-cost server-side grading."""

    def __init__(
        self,
        db: AsyncSession,
        generator: Optional[AssessmentGenerator] = None,
    ):
        self.db = db
        self.assessment_repo = AssessmentRepository(db)
        self.path_repo = LearningPathRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.job_repo = JobRepository(db)
        self.generator = generator or assessment_generator

    # -----------------------------------------------------------------------
    # Assessment Generation & Retrieval
    # -----------------------------------------------------------------------

    async def get_or_create_assessment(
        self,
        learning_path_id: str,
        request: CreateAssessmentRequest,
    ) -> AssessmentResponse:
        """
        Retrieves or generates an assessment for the specified scope.
        Checks SQLite cache first for zero-cost immediate returns.
        """
        # 1. Verify learning path
        path = await self.path_repo.get_by_id(learning_path_id)
        if not path:
            raise NotFoundError(resource="LearningPath", identifier=learning_path_id)

        # 2. Scope validation
        target_module: Optional[LearningModule] = None
        target_lesson: Optional[LearningLesson] = None

        if request.assessment_type == AssessmentTypeEnum.LESSON_QUIZ:
            if not request.lesson_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lesson_id is required when assessment_type is 'lesson_quiz'.",
                )
            # Find lesson in path modules
            for mod in path.modules or []:
                for les in mod.lessons or []:
                    if les.id == request.lesson_id:
                        target_lesson = les
                        target_module = mod
                        break
                if target_lesson:
                    break
            if not target_lesson:
                raise NotFoundError(resource="LearningLesson", identifier=request.lesson_id)

        elif request.assessment_type == AssessmentTypeEnum.MODULE_ASSESSMENT:
            if not request.module_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="module_id is required when assessment_type is 'module_assessment'.",
                )
            for mod in path.modules or []:
                if mod.id == request.module_id:
                    target_module = mod
                    break
            if not target_module:
                raise NotFoundError(resource="LearningModule", identifier=request.module_id)

        resolved_module_id = target_module.id if target_module else request.module_id
        resolved_lesson_id = target_lesson.id if target_lesson else request.lesson_id

        # 3. Check SQLite Cache for identical completed assessment
        cached = await self.assessment_repo.find_cached_assessment(
            learning_path_id=learning_path_id,
            assessment_type=request.assessment_type.value,
            module_id=resolved_module_id,
            lesson_id=resolved_lesson_id,
        )
        if cached:
            logger.info(f"Zero-cost assessment cache hit for path {learning_path_id} ({request.assessment_type.value})")
            return self._to_assessment_response(cached, is_cached=True)

        # 4. In-flight deduplication
        in_flight = await self.assessment_repo.find_in_flight_assessment(
            learning_path_id=learning_path_id,
            assessment_type=request.assessment_type.value,
            module_id=resolved_module_id,
            lesson_id=resolved_lesson_id,
        )
        if in_flight:
            logger.info(f"Duplicate assessment request: returning in-flight {in_flight.id}")
            return self._to_assessment_response(in_flight, is_cached=False)

        # 5. Fetch document and chunks
        doc = await self.doc_repo.get_by_id(path.document_id)
        if not doc:
            raise NotFoundError(resource="Document", identifier=path.document_id)

        chunks = await self.chunk_repo.get_chunks_by_document_id(doc.id)

        # 6. Create pending assessment record
        title_prefix = (
            f"Quiz: {target_lesson.title}"
            if target_lesson
            else f"Assessment: {target_module.title}"
            if target_module
            else f"Final Assessment: {path.title}"
        )
        assessment_record = Assessment(
            learning_path_id=path.id,
            module_id=target_module.id if target_module else None,
            lesson_id=target_lesson.id if target_lesson else None,
            assessment_type=request.assessment_type.value,
            title=title_prefix,
            description="Generating interactive source-grounded questions...",
            language=path.language,
            difficulty=path.difficulty,
            status="pending",
            passing_threshold=70.0,
        )
        created_assessment = await self.assessment_repo.create_assessment(assessment_record)

        # Create processing job
        job = ProcessingJob(
            document_id=doc.id,
            job_type=f"assessment_{request.assessment_type.value}_{path.language}",
            status="in_progress",
        )
        await self.job_repo.create(job)
        await self.db.commit()

        if request.wait:
            # Synchronous generation
            return await self._execute_assessment_job(
                assessment_id=created_assessment.id,
                assessment_type=request.assessment_type,
                learning_path=path,
                document=doc,
                chunks=chunks,
                module=target_module,
                lesson=target_lesson,
                question_count=request.question_count,
                job_id=job.id,
            )
        else:
            # Asynchronous background execution
            asyncio.create_task(
                self._run_background_assessment_task(
                    assessment_id=created_assessment.id,
                    assessment_type=request.assessment_type,
                    learning_path_id=path.id,
                    document_id=doc.id,
                    module_id=target_module.id if target_module else None,
                    lesson_id=target_lesson.id if target_lesson else None,
                    question_count=request.question_count,
                    job_id=job.id,
                )
            )
            return self._to_assessment_response(created_assessment, is_cached=False)

    async def _execute_assessment_job(
        self,
        assessment_id: str,
        assessment_type: AssessmentTypeEnum,
        learning_path: LearningPath,
        document: Document,
        chunks: list,
        module: Optional[LearningModule] = None,
        lesson: Optional[LearningLesson] = None,
        question_count: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> AssessmentResponse:
        """Executes question synthesis synchronously."""
        sync_start = time.monotonic()
        assessment = await self.assessment_repo.get_assessment_by_id(assessment_id)
        if not assessment:
            raise NotFoundError(resource="Assessment", identifier=assessment_id)

        assessment.status = "processing"
        await self.assessment_repo.update_assessment(assessment)
        await self.db.commit()

        try:
            generated: GeneratedAssessmentContent = await self.generator.generate_assessment(
                assessment_type=assessment_type,
                learning_path=learning_path,
                document=document,
                chunks=chunks,
                module=module,
                lesson=lesson,
                question_count=question_count,
            )

            assessment.title = generated.title
            assessment.description = generated.description
            assessment.status = "completed"
            assessment.error_message = None
            assessment.updated_at = datetime.now(timezone.utc)

            # Persist questions
            assessment.questions.clear()
            for q_data in generated.questions:
                q_model = AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_text=q_data.question_text,
                    question_type=q_data.question_type.value,
                    answer_options=q_data.answer_options,
                    correct_answer=q_data.correct_answer,
                    explanation=q_data.explanation,
                    source_references=[r.model_dump() for r in q_data.source_references],
                    sequence_order=q_data.sequence_order,
                )
                assessment.questions.append(q_model)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(timezone.utc)
                    await self.job_repo.update(job)

            await self.db.commit()
            elapsed = time.monotonic() - sync_start
            logger.info(f"[Timing] Assessment {assessment_id} generated in {elapsed:.2f}s with {len(assessment.questions)} questions")
            refreshed = await self.assessment_repo.get_assessment_by_id(assessment_id)
            return self._to_assessment_response(refreshed, is_cached=False)

        except Exception as exc:
            elapsed = time.monotonic() - sync_start
            err_msg = str(exc)
            if isinstance(exc, AITimeoutError):
                err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
            elif isinstance(exc, RateLimitExceededError):
                err_msg = "Google Gemini free-tier rate limit reached. Please wait a moment before sending another request."

            logger.error(f"[Timing] Assessment job failed after {elapsed:.2f}s for {assessment_id}: {err_msg}")
            assessment.status = "failed"
            assessment.error_message = err_msg
            assessment.updated_at = datetime.now(timezone.utc)
            await self.assessment_repo.update_assessment(assessment)

            if job_id:
                job = await self.job_repo.get_by_id(job_id)
                if job:
                    job.status = "failed"
                    job.error_message = err_msg
                    await self.job_repo.update(job)

            await self.db.commit()
            refreshed = await self.assessment_repo.get_assessment_by_id(assessment_id)
            return self._to_assessment_response(refreshed, is_cached=False)

    async def _run_background_assessment_task(
        self,
        assessment_id: str,
        assessment_type: AssessmentTypeEnum,
        learning_path_id: str,
        document_id: str,
        module_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        question_count: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> None:
        """Executes question synthesis in an isolated background session."""
        bg_start = time.monotonic()
        try:
            async with async_session_maker() as session:
                assessment_repo = AssessmentRepository(session)
                path_repo = LearningPathRepository(session)
                chunk_repo = ChunkRepository(session)
                doc_repo = DocumentRepository(session)
                job_repo = JobRepository(session)

                assessment = await assessment_repo.get_assessment_by_id(assessment_id)
                path = await path_repo.get_by_id(learning_path_id)
                doc = await doc_repo.get_by_id(document_id)

                if not assessment or not path or not doc:
                    logger.error(f"Background assessment task aborted: missing entity for {assessment_id}")
                    return

                assessment.status = "processing"
                await assessment_repo.update_assessment(assessment)
                await session.commit()

                chunks = await chunk_repo.get_chunks_by_document_id(document_id)

                target_module = None
                target_lesson = None
                if lesson_id:
                    for m in path.modules or []:
                        for l in m.lessons or []:
                            if l.id == lesson_id:
                                target_lesson = l
                                target_module = m
                                break
                elif module_id:
                    for m in path.modules or []:
                        if m.id == module_id:
                            target_module = m
                            break

                try:
                    generated: GeneratedAssessmentContent = await self.generator.generate_assessment(
                        assessment_type=assessment_type,
                        learning_path=path,
                        document=doc,
                        chunks=chunks,
                        module=target_module,
                        lesson=target_lesson,
                        question_count=question_count,
                    )

                    assessment.title = generated.title
                    assessment.description = generated.description
                    assessment.status = "completed"
                    assessment.error_message = None
                    assessment.updated_at = datetime.now(timezone.utc)

                    assessment.questions.clear()
                    for q_data in generated.questions:
                        q_model = AssessmentQuestion(
                            assessment_id=assessment.id,
                            question_text=q_data.question_text,
                            question_type=q_data.question_type.value,
                            answer_options=q_data.answer_options,
                            correct_answer=q_data.correct_answer,
                            explanation=q_data.explanation,
                            source_references=[r.model_dump() for r in q_data.source_references],
                            sequence_order=q_data.sequence_order,
                        )
                        assessment.questions.append(q_model)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "completed"
                            job.completed_at = datetime.now(timezone.utc)
                            await job_repo.update(job)

                    await session.commit()
                    elapsed = time.monotonic() - bg_start
                    logger.info(f"[Timing] Background assessment {assessment_id} completed successfully in {elapsed:.2f}s")

                except Exception as exc:
                    elapsed = time.monotonic() - bg_start
                    err_msg = str(exc)
                    if isinstance(exc, AITimeoutError):
                        err_msg = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT_SECONDS}s on model '{settings.GEMINI_MODEL}'."
                    elif isinstance(exc, RateLimitExceededError):
                        err_msg = "Google Gemini free-tier rate limit reached. Please wait a moment before sending another request."

                    logger.error(f"[Timing] Background assessment {assessment_id} failed after {elapsed:.2f}s: {err_msg}")
                    assessment.status = "failed"
                    assessment.error_message = err_msg
                    assessment.updated_at = datetime.now(timezone.utc)
                    await assessment_repo.update_assessment(assessment)

                    if job_id:
                        job = await job_repo.get_by_id(job_id)
                        if job:
                            job.status = "failed"
                            job.error_message = err_msg
                            await job_repo.update(job)

                    await session.commit()

        except Exception as exc:
            logger.error(f"Unhandled background assessment error for {assessment_id}: {exc}")

    async def list_assessments(
        self,
        learning_path_id: str,
        assessment_type: Optional[str] = None,
        module_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
    ) -> AssessmentListResponse:
        """Lists assessments for a learning path."""
        items = await self.assessment_repo.list_assessments(
            learning_path_id=learning_path_id,
            assessment_type=assessment_type,
            module_id=module_id,
            lesson_id=lesson_id,
        )
        return AssessmentListResponse(
            items=[self._to_assessment_response(a) for a in items],
            total=len(items),
        )

    async def get_assessment_detail(self, assessment_id: str) -> AssessmentDetailResponse:
        """
        Retrieves assessment with taker-safe question schema.
        CRITICAL: Never exposes correct_answer or explanation to taker.
        """
        assessment = await self.assessment_repo.get_assessment_by_id(assessment_id)
        if not assessment:
            raise NotFoundError(resource="Assessment", identifier=assessment_id)

        # Sanitize questions for taker
        taker_questions = [
            QuestionForTaker(
                id=q.id,
                assessment_id=q.assessment_id,
                question_text=q.question_text,
                question_type=q.question_type,
                answer_options=q.answer_options,
                sequence_order=q.sequence_order,
            )
            for q in assessment.questions
        ]

        resp = self._to_assessment_response(assessment)
        return AssessmentDetailResponse(
            **resp.model_dump(),
            questions=taker_questions,
        )

    # -----------------------------------------------------------------------
    # Assessment Attempts & Server-Side Deterministic Grading
    # -----------------------------------------------------------------------

    async def start_attempt(self, assessment_id: str) -> AssessmentAttemptResponse:
        """Starts a new test-taking attempt for a completed assessment."""
        assessment = await self.assessment_repo.get_assessment_by_id(assessment_id)
        if not assessment:
            raise NotFoundError(resource="Assessment", identifier=assessment_id)

        if assessment.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start attempt: assessment status is '{assessment.status}'.",
            )

        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            status=AttemptStatusEnum.IN_PROGRESS.value,
            score=0,
            max_score=len(assessment.questions),
            percentage=0.0,
            passed=False,
            started_at=datetime.now(timezone.utc),
        )
        created = await self.assessment_repo.create_attempt(attempt)
        await self.db.commit()
        return AssessmentAttemptResponse.model_validate(created)

    async def submit_answer(
        self,
        attempt_id: str,
        request: SubmitAnswerRequest,
    ) -> AnswerRecordResponse:
        """
        Submits and evaluates an answer for a question in an active attempt.
        Validates question belongs to attempt's assessment and prevents duplicate submissions.
        """
        attempt = await self.assessment_repo.get_attempt_by_id(attempt_id, include_answers=False)
        if not attempt:
            raise NotFoundError(resource="AssessmentAttempt", identifier=attempt_id)

        if attempt.status != AttemptStatusEnum.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit answer: attempt status is '{attempt.status}'.",
            )

        # Verify question exists
        question = await self.assessment_repo.get_question_by_id(request.question_id)
        if not question:
            raise NotFoundError(resource="AssessmentQuestion", identifier=request.question_id)

        # Cross-assessment validation: Question must belong to attempt's assessment
        if question.assessment_id != attempt.assessment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to the assessment for this attempt.",
            )

        # Validate that selected answer is one of the question's answer options
        if request.selected_answer not in question.answer_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Selected answer '{request.selected_answer}' is not in valid answer options.",
            )

        # Prevent duplicate answer submissions for the same question
        existing_answer = await self.assessment_repo.get_answer(attempt_id, request.question_id)
        if existing_answer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This question has already been answered for this attempt.",
            )

        # Server-side deterministic grading
        is_correct = request.selected_answer.strip() == question.correct_answer.strip()

        answer = AssessmentAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer=request.selected_answer,
            is_correct=is_correct,
            feedback=question.explanation,
        )
        created = await self.assessment_repo.create_answer(answer)
        await self.db.commit()

        return AnswerRecordResponse.model_validate(created)

    async def submit_attempt(self, attempt_id: str) -> AttemptResultResponse:
        """
        Finalizes and grades the entire attempt locally.
        Idempotent: if already completed, returns existing results.
        Reveals correct answers and explanations ONLY after final submission.
        """
        attempt = await self.assessment_repo.get_attempt_by_id(attempt_id, include_answers=True)
        if not attempt:
            raise NotFoundError(resource="AssessmentAttempt", identifier=attempt_id)

        assessment = attempt.assessment
        if not assessment:
            raise NotFoundError(resource="Assessment", identifier=attempt.assessment_id)

        # If already completed, return existing graded results idempotently
        if attempt.status != AttemptStatusEnum.COMPLETED.value:
            # Deterministic scoring calculation
            questions_list = assessment.questions or []
            max_score = len(questions_list)
            score = sum(1 for a in attempt.answers if a.is_correct)
            percentage = round((score / max_score) * 100.0, 1) if max_score > 0 else 0.0
            passed = percentage >= assessment.passing_threshold

            attempt.status = AttemptStatusEnum.COMPLETED.value
            attempt.score = score
            attempt.max_score = max_score
            attempt.percentage = percentage
            attempt.passed = passed
            attempt.completed_at = datetime.now(timezone.utc)
            await self.assessment_repo.update_attempt(attempt)
            await self.db.commit()

        # Build full pedagogical review items
        answer_map = {a.question_id: a for a in attempt.answers}
        review_items: List[AnswerReviewItem] = []

        for q in assessment.questions:
            user_ans = answer_map.get(q.id)
            review_items.append(
                AnswerReviewItem(
                    question_id=q.id,
                    question_text=q.question_text,
                    answer_options=q.answer_options,
                    selected_answer=user_ans.selected_answer if user_ans else None,
                    correct_answer=q.correct_answer,
                    is_correct=user_ans.is_correct if user_ans else False,
                    explanation=q.explanation,
                    source_references=[
                        SourceReference(**ref) for ref in (q.source_references or [])
                    ],
                )
            )

        return AttemptResultResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            status=AttemptStatusEnum(attempt.status),
            score=attempt.score,
            max_score=attempt.max_score,
            percentage=attempt.percentage,
            passed=attempt.passed,
            passing_threshold=assessment.passing_threshold,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            answers=review_items,
        )

    async def get_attempt_results(self, attempt_id: str) -> AttemptResultResponse:
        """Retrieves results of a completed attempt."""
        attempt = await self.assessment_repo.get_attempt_by_id(attempt_id, include_answers=True)
        if not attempt:
            raise NotFoundError(resource="AssessmentAttempt", identifier=attempt_id)

        if attempt.status != AttemptStatusEnum.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment attempt is still in progress. Please submit the attempt to view results.",
            )

        return await self.submit_attempt(attempt_id)

    # -----------------------------------------------------------------------
    # Helper Serialization
    # -----------------------------------------------------------------------

    def _to_assessment_response(self, a: Assessment, is_cached: bool = False) -> AssessmentResponse:
        questions_count = (
            len(a.questions)
            if ("questions" in a.__dict__ and a.questions is not None)
            else 0
        )
        return AssessmentResponse(
            id=a.id,
            learning_path_id=a.learning_path_id,
            module_id=a.module_id,
            lesson_id=a.lesson_id,
            assessment_type=AssessmentTypeEnum(a.assessment_type),
            title=a.title,
            description=a.description,
            language=a.language,
            difficulty=a.difficulty,
            status=a.status,
            error_message=a.error_message,
            passing_threshold=a.passing_threshold,
            questions_count=questions_count,
            is_cached=is_cached,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
