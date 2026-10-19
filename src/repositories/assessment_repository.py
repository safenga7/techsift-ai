"""
TechSift AI - Assessment Repository (Phase 5B).
Data access layer for Assessment, AssessmentQuestion, AssessmentAttempt, and AssessmentAnswer
with eager relationship loading, SQLite caching, and deduplication.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
)


class AssessmentRepository:
    """Manages persistence, caching, attempts, and queries for interactive assessments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_assessment(self, assessment: Assessment) -> Assessment:
        """Persist a new assessment."""
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def get_assessment_by_id(
        self,
        assessment_id: str,
        include_questions: bool = True,
    ) -> Optional[Assessment]:
        """Fetch assessment by UUID with optional eager loading of questions."""
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        if include_questions:
            stmt = stmt.options(
                selectinload(Assessment.questions),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assessments(
        self,
        learning_path_id: str,
        assessment_type: Optional[str] = None,
        module_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
    ) -> List[Assessment]:
        """List assessments for a learning path, optionally filtered by type, module, or lesson."""
        stmt = (
            select(Assessment)
            .where(Assessment.learning_path_id == learning_path_id)
            .options(selectinload(Assessment.questions))
            .order_by(Assessment.created_at.desc())
        )
        if assessment_type:
            stmt = stmt.where(Assessment.assessment_type == assessment_type)
        if module_id:
            stmt = stmt.where(Assessment.module_id == module_id)
        if lesson_id:
            stmt = stmt.where(Assessment.lesson_id == lesson_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_assessments_with_attempts(
        self,
        learning_path_id: str,
    ) -> List[Assessment]:
        """Fetch all assessments for a path with eager loaded attempts and answers."""
        stmt = (
            select(Assessment)
            .where(Assessment.learning_path_id == learning_path_id)
            .options(
                selectinload(Assessment.questions),
                selectinload(Assessment.attempts).selectinload(AssessmentAttempt.answers),
            )
            .order_by(Assessment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_cached_assessment(
        self,
        learning_path_id: str,
        assessment_type: str,
        module_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
    ) -> Optional[Assessment]:
        """
        Locates a cached completed assessment matching exact scope.
        Enables 100% zero-cost returns for repeated quiz requests.
        """
        stmt = (
            select(Assessment)
            .where(
                Assessment.learning_path_id == learning_path_id,
                Assessment.assessment_type == assessment_type,
                Assessment.status == "completed",
            )
            .options(selectinload(Assessment.questions))
        )
        if module_id:
            stmt = stmt.where(Assessment.module_id == module_id)
        else:
            stmt = stmt.where(Assessment.module_id.is_(None))

        if lesson_id:
            stmt = stmt.where(Assessment.lesson_id == lesson_id)
        else:
            stmt = stmt.where(Assessment.lesson_id.is_(None))

        stmt = stmt.order_by(Assessment.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_in_flight_assessment(
        self,
        learning_path_id: str,
        assessment_type: str,
        module_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
    ) -> Optional[Assessment]:
        """Locates an active (pending/processing) assessment to prevent duplicate generation."""
        stmt = select(Assessment).where(
            Assessment.learning_path_id == learning_path_id,
            Assessment.assessment_type == assessment_type,
            Assessment.status.in_(["pending", "processing"]),
        )
        if module_id:
            stmt = stmt.where(Assessment.module_id == module_id)
        else:
            stmt = stmt.where(Assessment.module_id.is_(None))

        if lesson_id:
            stmt = stmt.where(Assessment.lesson_id == lesson_id)
        else:
            stmt = stmt.where(Assessment.lesson_id.is_(None))

        stmt = stmt.order_by(Assessment.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_assessment(self, assessment: Assessment) -> Assessment:
        """Update assessment entity."""
        await self.db.flush()
        return assessment

    async def delete_assessment(self, assessment_id: str) -> bool:
        """Delete assessment and cascade questions, attempts, and answers."""
        assessment = await self.get_assessment_by_id(assessment_id, include_questions=False)
        if not assessment:
            return False
        await self.db.delete(assessment)
        await self.db.flush()
        return True

    # -----------------------------------------------------------------------
    # Question Access
    # -----------------------------------------------------------------------

    async def get_question_by_id(self, question_id: str) -> Optional[AssessmentQuestion]:
        """Fetch question by UUID."""
        stmt = select(AssessmentQuestion).where(AssessmentQuestion.id == question_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # Attempts & Answers
    # -----------------------------------------------------------------------

    async def create_attempt(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        """Persist a new assessment attempt."""
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    async def get_attempt_by_id(
        self,
        attempt_id: str,
        include_answers: bool = True,
    ) -> Optional[AssessmentAttempt]:
        """Fetch attempt with eager loaded answers and questions."""
        stmt = select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id)
        if include_answers:
            stmt = stmt.options(
                selectinload(AssessmentAttempt.answers).selectinload(AssessmentAnswer.question),
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.questions),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_attempt(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        """Update attempt status and scores."""
        await self.db.flush()
        return attempt

    async def create_answer(self, answer: AssessmentAnswer) -> AssessmentAnswer:
        """Record an answer submission."""
        self.db.add(answer)
        await self.db.flush()
        return answer

    async def get_answer(self, attempt_id: str, question_id: str) -> Optional[AssessmentAnswer]:
        """Fetch answer for a specific question in an attempt."""
        stmt = select(AssessmentAnswer).where(
            AssessmentAnswer.attempt_id == attempt_id,
            AssessmentAnswer.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
