"""
TechSift AI - Learning Progress, Mastery & Dashboard Service (Phase 5C).
Provides:
- Lesson completion state management with idempotency and state protection.
- Session continuity and resume target resolution.
- Dynamic completion and performance calculations without stale stored aggregates.
- Deterministic knowledge mastery from assessment attempts and answers ($0 cost).
- Explainable, rule-based pedagogical learning recommendations.
- Consolidated Learning Dashboard.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError
from src.models.assessment import Assessment, AssessmentAttempt
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.learning_progress import LessonProgress
from src.repositories.assessment_repository import AssessmentRepository
from src.repositories.learning_path_repository import LearningPathRepository
from src.repositories.learning_progress_repository import LearningProgressRepository
from src.schemas.learning_progress import (
    AssessmentOverviewStats,
    AssessmentStatItem,
    ConceptMasteryItem,
    KnowledgeMasteryResponse,
    LearningDashboardResponse,
    LearningRecommendationItem,
    LearningRecommendationsResponse,
    LessonMasteryPerformance,
    LessonProgressResponse,
    LessonProgressStatusEnum,
    LessonProgressSummaryItem,
    MissedQuestionItem,
    ModuleProgressItem,
    PathProgressOverviewResponse,
    ResumeLearningResponse,
    UpdateLessonProgressRequest,
)

logger = logging.getLogger(__name__)


class LearningProgressService:
    """Manages learning progress, deterministic mastery, recommendations, and dashboard."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.progress_repo = LearningProgressRepository(db)
        self.path_repo = LearningPathRepository(db)
        self.assessment_repo = AssessmentRepository(db)

    # -----------------------------------------------------------------------
    # Lesson Progress Tracking & Continuity
    # -----------------------------------------------------------------------

    async def update_lesson_progress(
        self,
        lesson_id: str,
        request: UpdateLessonProgressRequest,
    ) -> LessonProgressResponse:
        """
        Updates progress for a lesson.
        Guarantees:
        - Completed lessons do NOT accidentally revert to in_progress.
        - Reopening a completed lesson updates last_accessed_at while preserving completion.
        - Repeated completion requests are idempotent.
        - Updates PathProgress session pointer for instant resume.
        """
        # 1. Resolve lesson and its learning path
        stmt = (
            select(LearningLesson)
            .where(LearningLesson.id == lesson_id)
            .options(selectinload(LearningLesson.module))
        )
        result = await self.db.execute(stmt)
        lesson = result.scalar_one_or_none()
        if not lesson:
            raise NotFoundError(resource="LearningLesson", identifier=lesson_id)

        learning_path_id = lesson.module.learning_path_id
        now = datetime.now(timezone.utc)

        # 2. Get or create progress record
        progress = await self.progress_repo.get_or_create_lesson_progress(
            learning_path_id=learning_path_id,
            lesson_id=lesson_id,
        )

        # 3. Apply state transition rules
        if request.status == LessonProgressStatusEnum.COMPLETED:
            if progress.status != "completed":
                progress.status = "completed"
                progress.completed_at = now
                if not progress.started_at:
                    progress.started_at = now
            progress.last_accessed_at = now
        elif request.status == LessonProgressStatusEnum.IN_PROGRESS:
            # Protection rule: Completed lessons must NOT revert to in_progress
            if progress.status != "completed":
                progress.status = "in_progress"
                if not progress.started_at:
                    progress.started_at = now
            progress.last_accessed_at = now
        else:
            progress.last_accessed_at = now

        # 4. Update path-level session continuity pointer
        await self.progress_repo.update_last_visited(
            learning_path_id=learning_path_id,
            lesson_id=lesson_id,
        )

        await self.db.commit()
        return LessonProgressResponse.model_validate(progress)

    # -----------------------------------------------------------------------
    # Path Progress Calculation (Dynamic aggregates)
    # -----------------------------------------------------------------------

    async def get_path_progress(
        self,
        learning_path_id: str,
    ) -> PathProgressOverviewResponse:
        """
        Calculates real-time curriculum progress across all modules and lessons.
        Avoids redundant stored aggregate values by computing dynamically.
        """
        path = await self._get_full_learning_path(learning_path_id)
        progress_records = await self.progress_repo.list_lesson_progress_for_path(learning_path_id)
        progress_map: Dict[str, LessonProgress] = {p.lesson_id: p for p in progress_records}
        path_progress_record = await self.progress_repo.get_path_progress(learning_path_id)

        assessments = await self.assessment_repo.list_assessments_with_attempts(learning_path_id)
        assessments_by_lesson: Dict[str, List[Assessment]] = {}
        assessments_by_module: Dict[str, List[Assessment]] = {}
        final_assessment: Optional[Assessment] = None

        for a in assessments:
            if a.assessment_type == "lesson_quiz" and a.lesson_id:
                assessments_by_lesson.setdefault(a.lesson_id, []).append(a)
            elif a.assessment_type == "module_assessment" and a.module_id:
                assessments_by_module.setdefault(a.module_id, []).append(a)
            elif a.assessment_type == "final_assessment":
                final_assessment = a

        # Aggregate module and lesson metrics
        total_lessons = 0
        completed_lessons = 0
        module_items: List[ModuleProgressItem] = []

        for mod in path.modules or []:
            mod_lessons: List[LessonProgressSummaryItem] = []
            m_total = len(mod.lessons or [])
            m_completed = 0
            total_lessons += m_total

            for les in mod.lessons or []:
                p = progress_map.get(les.id)
                status = LessonProgressStatusEnum(p.status) if p else LessonProgressStatusEnum.NOT_STARTED
                is_comp = status == LessonProgressStatusEnum.COMPLETED
                if is_comp:
                    m_completed += 1
                    completed_lessons += 1

                # Lesson quiz stats
                l_quizzes = assessments_by_lesson.get(les.id, [])
                has_quiz = len(l_quizzes) > 0
                quiz_passed = False
                quiz_score: Optional[float] = None
                quiz_attempts_count = 0

                if has_quiz:
                    all_attempts: List[AssessmentAttempt] = []
                    for q in l_quizzes:
                        all_attempts.extend([att for att in q.attempts if att.status == "completed"])
                    quiz_attempts_count = len(all_attempts)
                    if all_attempts:
                        quiz_passed = any(att.passed for att in all_attempts)
                        quiz_score = max(att.percentage for att in all_attempts)

                mod_lessons.append(
                    LessonProgressSummaryItem(
                        lesson_id=les.id,
                        module_id=mod.id,
                        sequence_order=les.sequence_order,
                        title=les.title,
                        status=status,
                        completed=is_comp,
                        last_accessed_at=p.last_accessed_at if p else None,
                        has_quiz=has_quiz,
                        quiz_passed=quiz_passed,
                        quiz_score=quiz_score,
                        quiz_attempts_count=quiz_attempts_count,
                    )
                )

            # Module assessment stats
            m_assessments = assessments_by_module.get(mod.id, [])
            has_mod_assessment = len(m_assessments) > 0
            mod_assessment_passed = False
            mod_assessment_score: Optional[float] = None
            mod_assessment_attempts_count = 0

            if has_mod_assessment:
                all_mod_attempts: List[AssessmentAttempt] = []
                for ma in m_assessments:
                    all_mod_attempts.extend([att for att in ma.attempts if att.status == "completed"])
                mod_assessment_attempts_count = len(all_mod_attempts)
                if all_mod_attempts:
                    mod_assessment_passed = any(att.passed for att in all_mod_attempts)
                    mod_assessment_score = max(att.percentage for att in all_mod_attempts)

            m_percentage = round((m_completed / m_total) * 100.0, 1) if m_total > 0 else 0.0
            is_mod_completed = (m_completed == m_total and m_total > 0)

            module_items.append(
                ModuleProgressItem(
                    module_id=mod.id,
                    sequence_order=mod.sequence_order,
                    title=mod.title,
                    total_lessons=m_total,
                    completed_lessons=m_completed,
                    completion_percentage=m_percentage,
                    is_completed=is_mod_completed,
                    has_assessment=has_mod_assessment,
                    assessment_passed=mod_assessment_passed,
                    assessment_score=mod_assessment_score,
                    assessment_attempts_count=mod_assessment_attempts_count,
                    lessons=mod_lessons,
                )
            )

        # Final assessment stats
        final_assessment_passed = False
        final_assessment_score: Optional[float] = None
        if final_assessment:
            completed_final_attempts = [att for att in final_assessment.attempts if att.status == "completed"]
            if completed_final_attempts:
                final_assessment_passed = any(att.passed for att in completed_final_attempts)
                final_assessment_score = max(att.percentage for att in completed_final_attempts)

        remaining_lessons = max(0, total_lessons - completed_lessons)
        overall_pct = round((completed_lessons / total_lessons) * 100.0, 1) if total_lessons > 0 else 0.0
        is_curriculum_completed = (completed_lessons == total_lessons and total_lessons > 0)

        return PathProgressOverviewResponse(
            learning_path_id=learning_path_id,
            total_lessons=total_lessons,
            completed_lessons=completed_lessons,
            remaining_lessons=remaining_lessons,
            overall_completion_percentage=overall_pct,
            is_curriculum_completed=is_curriculum_completed,
            final_assessment_passed=final_assessment_passed,
            final_assessment_score=final_assessment_score,
            last_visited_lesson_id=path_progress_record.last_visited_lesson_id if path_progress_record else None,
            last_accessed_at=path_progress_record.last_accessed_at if path_progress_record else None,
            modules=module_items,
        )

    # -----------------------------------------------------------------------
    # Resume Continuity
    # -----------------------------------------------------------------------

    async def get_resume_target(
        self,
        learning_path_id: str,
    ) -> ResumeLearningResponse:
        """
        Determines the optimal lesson to resume learning.
        Strategy:
        1. If last_visited_lesson exists and is incomplete: resume that lesson.
        2. Else, find the first incomplete lesson in curriculum order.
        3. If all lessons are completed, return the last completed lesson for review.
        4. If nothing has been started, return the first lesson in the curriculum.
        """
        path = await self._get_full_learning_path(learning_path_id)
        progress_records = await self.progress_repo.list_lesson_progress_for_path(learning_path_id)
        progress_map = {p.lesson_id: p for p in progress_records}
        path_progress_record = await self.progress_repo.get_path_progress(learning_path_id)

        # Build ordered list of lessons
        ordered_lessons: List[tuple[LearningModule, LearningLesson]] = []
        for mod in path.modules or []:
            for les in mod.lessons or []:
                ordered_lessons.append((mod, les))

        if not ordered_lessons:
            raise NotFoundError(resource="LearningLesson in Path", identifier=learning_path_id)

        # Check candidate 1: last visited lesson
        if path_progress_record and path_progress_record.last_visited_lesson_id:
            last_id = path_progress_record.last_visited_lesson_id
            for mod, les in ordered_lessons:
                if les.id == last_id:
                    p = progress_map.get(les.id)
                    status = LessonProgressStatusEnum(p.status) if p else LessonProgressStatusEnum.NOT_STARTED
                    if status != LessonProgressStatusEnum.COMPLETED:
                        return ResumeLearningResponse(
                            learning_path_id=learning_path_id,
                            lesson_id=les.id,
                            lesson_title=les.title,
                            module_id=mod.id,
                            module_title=mod.title,
                            module_sequence=mod.sequence_order,
                            lesson_sequence=les.sequence_order,
                            status=status,
                            reason="Resume last visited lesson in progress",
                        )
                    break

        # Check candidate 2: first incomplete lesson
        for mod, les in ordered_lessons:
            p = progress_map.get(les.id)
            status = LessonProgressStatusEnum(p.status) if p else LessonProgressStatusEnum.NOT_STARTED
            if status != LessonProgressStatusEnum.COMPLETED:
                return ResumeLearningResponse(
                    learning_path_id=learning_path_id,
                    lesson_id=les.id,
                    lesson_title=les.title,
                    module_id=mod.id,
                    module_title=mod.title,
                    module_sequence=mod.sequence_order,
                    lesson_sequence=les.sequence_order,
                    status=status,
                    reason="Continue next incomplete lesson in curriculum",
                )

        # Check candidate 3: all completed, return first or last lesson for review
        first_mod, first_les = ordered_lessons[0]
        return ResumeLearningResponse(
            learning_path_id=learning_path_id,
            lesson_id=first_les.id,
            lesson_title=first_les.title,
            module_id=first_mod.id,
            module_title=first_mod.title,
            module_sequence=first_mod.sequence_order,
            lesson_sequence=first_les.sequence_order,
            status=LessonProgressStatusEnum.COMPLETED,
            reason="All curriculum lessons completed — Review material",
        )

    # -----------------------------------------------------------------------
    # Knowledge Mastery & Evidence-Grounded Performance
    # -----------------------------------------------------------------------

    async def get_knowledge_mastery(
        self,
        learning_path_id: str,
    ) -> KnowledgeMasteryResponse:
        """
        Calculates deterministic, evidence-based technical concept mastery
        and question failure rates without any LLM calls.
        """
        path = await self._get_full_learning_path(learning_path_id)
        assessments = await self.assessment_repo.list_assessments_with_attempts(learning_path_id)
        progress_records = await self.progress_repo.list_lesson_progress_for_path(learning_path_id)
        progress_map = {p.lesson_id: p for p in progress_records}

        # 1. Frequently Missed Questions Analysis
        question_stats: Dict[str, Dict[str, Any]] = {}
        for a in assessments:
            for att in a.attempts:
                if att.status != "completed":
                    continue
                for ans in att.answers:
                    q_id = ans.question_id
                    if q_id not in question_stats:
                        # Find question entity
                        q_obj = next((q for q in (a.questions or []) if q.id == q_id), None)
                        q_text = q_obj.question_text if q_obj else "Assessment Question"
                        question_stats[q_id] = {
                            "question_text": q_text,
                            "assessment_type": a.assessment_type,
                            "lesson_id": a.lesson_id,
                            "total": 0,
                            "incorrect": 0,
                        }
                    question_stats[q_id]["total"] += 1
                    if not ans.is_correct:
                        question_stats[q_id]["incorrect"] += 1

        frequently_missed: List[MissedQuestionItem] = []
        for q_id, s in question_stats.items():
            if s["total"] >= 1:
                failure_rate = round((s["incorrect"] / s["total"]) * 100.0, 1)
                if failure_rate >= 50.0:
                    frequently_missed.append(
                        MissedQuestionItem(
                            question_id=q_id,
                            question_text=s["question_text"],
                            assessment_type=s["assessment_type"],
                            total_answers=s["total"],
                            incorrect_count=s["incorrect"],
                            failure_rate=failure_rate,
                        )
                    )
        frequently_missed.sort(key=lambda x: x.failure_rate, reverse=True)

        # 2. Lesson-level Performance & Concept Grounding
        strong_concepts: List[ConceptMasteryItem] = []
        concepts_needing_review: List[ConceptMasteryItem] = []
        lessons_performance: List[LessonMasteryPerformance] = []

        for mod in path.modules or []:
            for les in mod.lessons or []:
                p = progress_map.get(les.id)
                lesson_completed = p is not None and p.status == "completed"

                # Find assessments for this lesson
                les_assessments = [a for a in assessments if a.lesson_id == les.id]
                completed_attempts: List[AssessmentAttempt] = []
                for a in les_assessments:
                    completed_attempts.extend([att for att in a.attempts if att.status == "completed"])

                attempts_count = len(completed_attempts)
                status = "not_assessed"
                best_pct: Optional[float] = None

                if attempts_count > 0:
                    best_pct = max(att.percentage for att in completed_attempts)
                    has_passed = any(att.passed for att in completed_attempts)
                    if has_passed and best_pct >= 80.0 and lesson_completed:
                        status = "mastered"
                    elif has_passed and best_pct >= 70.0:
                        status = "proficient"
                    else:
                        status = "needs_review"

                lessons_performance.append(
                    LessonMasteryPerformance(
                        lesson_id=les.id,
                        lesson_title=les.title,
                        module_id=mod.id,
                        status=status,
                        best_percentage=best_pct,
                        attempts_count=attempts_count,
                        lesson_completed=lesson_completed,
                    )
                )

                # Concept extraction
                for kc in les.key_concepts or []:
                    term = kc.get("term", "") if isinstance(kc, dict) else str(kc)
                    explanation = kc.get("explanation", "") if isinstance(kc, dict) else ""
                    if not term:
                        continue

                    if status in ["mastered", "proficient"]:
                        strong_concepts.append(
                            ConceptMasteryItem(
                                term=term,
                                explanation=explanation,
                                lesson_id=les.id,
                                lesson_title=les.title,
                                module_id=mod.id,
                                status=status,
                                accuracy_percentage=best_pct,
                                evidence=f"{best_pct}% quiz score across {attempts_count} attempt(s)",
                            )
                        )
                    elif status == "needs_review":
                        concepts_needing_review.append(
                            ConceptMasteryItem(
                                term=term,
                                explanation=explanation,
                                lesson_id=les.id,
                                lesson_title=les.title,
                                module_id=mod.id,
                                status=status,
                                accuracy_percentage=best_pct,
                                evidence=f"{best_pct}% quiz score (below 70% threshold) across {attempts_count} attempt(s)",
                            )
                        )

        return KnowledgeMasteryResponse(
            learning_path_id=learning_path_id,
            strong_concepts=strong_concepts,
            concepts_needing_review=concepts_needing_review,
            frequently_missed_questions=frequently_missed,
            lessons_performance=lessons_performance,
        )

    # -----------------------------------------------------------------------
    # Explainable Rule-Based Pedagogical Recommendations
    # -----------------------------------------------------------------------

    async def get_recommendations(
        self,
        learning_path_id: str,
    ) -> LearningRecommendationsResponse:
        """
        Generates explainable pedagogical recommendations using deterministic business rules.
        Strictly zero-cost without LLM inference.
        """
        path = await self._get_full_learning_path(learning_path_id)
        assessments = await self.assessment_repo.list_assessments_with_attempts(learning_path_id)
        progress_records = await self.progress_repo.list_lesson_progress_for_path(learning_path_id)
        progress_map = {p.lesson_id: p for p in progress_records}

        recommendations: List[LearningRecommendationItem] = []

        # Rule 1: Review failed quizzes
        for a in assessments:
            if a.assessment_type == "lesson_quiz" and a.lesson_id:
                completed_attempts = [att for att in a.attempts if att.status == "completed"]
                if completed_attempts:
                    latest = max(completed_attempts, key=lambda x: x.started_at)
                    if not latest.passed:
                        # Find lesson title
                        les_title = "Lesson"
                        for m in path.modules or []:
                            for l in m.lessons or []:
                                if l.id == a.lesson_id:
                                    les_title = l.title
                                    break
                        recommendations.append(
                            LearningRecommendationItem(
                                id=f"rec-quiz-fail-{a.id}",
                                type="review_lesson",
                                title=f"Review: {les_title}",
                                description=f"Your latest quiz score was {latest.percentage}%. Revisit the key technical concepts and retake the quiz.",
                                target_id=a.lesson_id,
                                priority=1,
                            )
                        )

        # Rule 2: Retake failed module or final assessment
        for a in assessments:
            if a.assessment_type in ["module_assessment", "final_assessment"]:
                completed_attempts = [att for att in a.attempts if att.status == "completed"]
                if completed_attempts:
                    latest = max(completed_attempts, key=lambda x: x.started_at)
                    if not latest.passed:
                        recommendations.append(
                            LearningRecommendationItem(
                                id=f"rec-assess-fail-{a.id}",
                                type="retake_assessment",
                                title=f"Retake: {a.title}",
                                description=f"Latest score was {latest.percentage}% (passing threshold is {a.passing_threshold}%). Retake the assessment to solidify understanding.",
                                target_id=a.id,
                                priority=2,
                            )
                        )

        # Rule 3: Continue next incomplete lesson
        next_incomplete_lesson: Optional[tuple[LearningModule, LearningLesson]] = None
        for mod in path.modules or []:
            for les in mod.lessons or []:
                p = progress_map.get(les.id)
                if not p or p.status != "completed":
                    next_incomplete_lesson = (mod, les)
                    break
            if next_incomplete_lesson:
                break

        if next_incomplete_lesson:
            mod, les = next_incomplete_lesson
            recommendations.append(
                LearningRecommendationItem(
                    id=f"rec-next-lesson-{les.id}",
                    type="continue_lesson",
                    title=f"Continue: Module {mod.sequence_order}.{les.sequence_order} — {les.title}",
                    description="Advance your learning by working through the next scheduled lesson and examples.",
                    target_id=les.id,
                    priority=3,
                )
            )

        # Rule 4: Ready for Module Assessment
        for mod in path.modules or []:
            all_mod_lessons = mod.lessons or []
            if all_mod_lessons and all(progress_map.get(l.id) and progress_map[l.id].status == "completed" for l in all_mod_lessons):
                # Check if module assessment was attempted
                mod_assessments = [a for a in assessments if a.module_id == mod.id and a.assessment_type == "module_assessment"]
                has_completed_attempt = any(
                    any(att.status == "completed" for att in a.attempts) for a in mod_assessments
                )
                if not has_completed_attempt:
                    recommendations.append(
                        LearningRecommendationItem(
                            id=f"rec-mod-ready-{mod.id}",
                            type="take_module_assessment",
                            title=f"Assessment Ready: {mod.title}",
                            description="All lessons in this module are complete. Take the module assessment to test your synthesis.",
                            target_id=mod.id,
                            priority=4,
                        )
                    )

        # Rule 5: Capstone Ready or Mastered
        total_lessons = sum(len(m.lessons or []) for m in path.modules or [])
        completed_lessons = sum(1 for p in progress_map.values() if p.status == "completed")
        final_assessment = next((a for a in assessments if a.assessment_type == "final_assessment"), None)

        if total_lessons > 0 and completed_lessons == total_lessons:
            final_completed = [att for att in (final_assessment.attempts if final_assessment else []) if att.status == "completed"]
            if final_completed:
                latest_final = max(final_completed, key=lambda x: x.started_at)
                if latest_final.passed:
                    recommendations.append(
                        LearningRecommendationItem(
                            id="rec-curriculum-mastered",
                            type="curriculum_mastered",
                            title="Curriculum Mastered!",
                            description=f"Congratulations! You completed all lessons and passed the Final Comprehensive Exam with {latest_final.percentage}%.",
                            target_id=final_assessment.id if final_assessment else None,
                            priority=5,
                        )
                    )
            else:
                recommendations.append(
                    LearningRecommendationItem(
                        id="rec-final-ready",
                        type="take_final_assessment",
                        title="Final Comprehensive Exam Ready",
                        description="You have completed all curriculum modules! Validate your mastery with the comprehensive final exam.",
                        target_id=final_assessment.id if final_assessment else None,
                        priority=3,
                    )
                )

        recommendations.sort(key=lambda x: x.priority)
        return LearningRecommendationsResponse(
            learning_path_id=learning_path_id,
            items=recommendations,
        )

    # -----------------------------------------------------------------------
    # Consolidated Learning Dashboard
    # -----------------------------------------------------------------------

    async def get_dashboard(
        self,
        learning_path_id: str,
    ) -> LearningDashboardResponse:
        """
        Returns full consolidated dashboard for a learning path.
        Combines progress overview, assessment statistics, knowledge mastery,
        and recommendations in one high-performance payload.
        """
        path = await self._get_full_learning_path(learning_path_id)
        progress_overview = await self.get_path_progress(learning_path_id)
        mastery = await self.get_knowledge_mastery(learning_path_id)
        recommendations = await self.get_recommendations(learning_path_id)
        resume_target = await self.get_resume_target(learning_path_id)

        # Assessments Overview Calculation
        assessments = await self.assessment_repo.list_assessments_with_attempts(learning_path_id)
        stat_items: List[AssessmentStatItem] = []
        total_assessments = len(assessments)
        attempted_count = 0
        passed_count = 0
        scores: List[float] = []

        for a in assessments:
            completed_attempts = [att for att in a.attempts if att.status == "completed"]
            attempts_count = len(completed_attempts)
            if attempts_count > 0:
                attempted_count += 1
                latest = max(completed_attempts, key=lambda x: x.started_at)
                best_pct = max(att.percentage for att in completed_attempts)
                has_passed = any(att.passed for att in completed_attempts)
                if has_passed:
                    passed_count += 1
                scores.append(latest.percentage)

                stat_items.append(
                    AssessmentStatItem(
                        assessment_id=a.id,
                        title=a.title,
                        assessment_type=a.assessment_type,
                        module_id=a.module_id,
                        lesson_id=a.lesson_id,
                        attempts_count=attempts_count,
                        latest_score=latest.score,
                        latest_percentage=latest.percentage,
                        best_percentage=best_pct,
                        passed=has_passed,
                        passing_threshold=a.passing_threshold,
                        last_attempt_at=latest.completed_at or latest.started_at,
                    )
                )

        pass_rate = round((passed_count / attempted_count) * 100.0, 1) if attempted_count > 0 else 0.0
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        failed_count = attempted_count - passed_count

        assessment_stats = AssessmentOverviewStats(
            total_assessments=total_assessments,
            attempted_assessments=attempted_count,
            passed_assessments=passed_count,
            failed_assessments=failed_count,
            pass_rate=pass_rate,
            average_score=avg_score,
            recent_assessments=stat_items,
        )

        return LearningDashboardResponse(
            learning_path_id=learning_path_id,
            path_title=path.title,
            difficulty=path.difficulty,
            language=path.language,
            progress=progress_overview,
            assessments_overview=assessment_stats,
            knowledge_mastery=mastery,
            recommendations=recommendations.items,
            resume_target=resume_target,
        )

    # -----------------------------------------------------------------------
    # Helper: Eagerly fetch path with modules and lessons
    # -----------------------------------------------------------------------

    async def _get_full_learning_path(self, learning_path_id: str) -> LearningPath:
        stmt = (
            select(LearningPath)
            .where(LearningPath.id == learning_path_id)
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.lessons),
            )
        )
        result = await self.db.execute(stmt)
        path = result.scalar_one_or_none()
        if not path:
            raise NotFoundError(resource="LearningPath", identifier=learning_path_id)
        return path
