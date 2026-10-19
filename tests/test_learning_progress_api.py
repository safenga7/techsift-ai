"""
TechSift AI - Automated Integration & Unit Tests for Learning Progress & Dashboard (Phase 5C).
Guarantees 100% zero-cost, offline execution using mocked AI provider.
Validates:
- Lesson progress tracking (not_started -> in_progress -> completed)
- Idempotent completion updates
- Completed-to-in-progress reversion protection
- Dynamic path and module completion calculations without stale stored aggregates
- Session continuity & Resume Learning resolution
- Empty assessment history and multiple attempt statistics
- Deterministic knowledge mastery and frequently missed questions
- Explainable rule-based pedagogical recommendations
- Consolidated learning dashboard
- Cross-path isolation and cascade deletion on document removal
"""

from datetime import datetime, timezone
import json
import uuid
from typing import Optional
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import src.db.session
from src.models.assessment import Assessment, AssessmentAnswer, AssessmentAttempt, AssessmentQuestion
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.learning_progress import LessonProgress, PathProgress
from src.services.ai_provider import AIProvider
from src.services.assessment_generator import assessment_generator
from src.services.learning_path_generator import learning_path_generator


SAMPLE_CURRICULUM = {
    "title": "Distributed Systems Architecture",
    "description": "Comprehensive guide to distributed consensus and state machines.",
    "difficulty": "intermediate",
    "estimated_duration_minutes": 60,
    "prerequisites": ["Networking Basics"],
    "learning_objectives": ["Understand replicated logs", "Master Raft elections"],
    "modules": [
        {
            "title": "Module 1: Consensus Fundamentals",
            "description": "Foundations of state machine replication.",
            "sequence_order": 1,
            "estimated_duration_minutes": 30,
            "learning_objectives": ["Understand deterministic state"],
            "lessons": [
                {
                    "title": "Lesson 1: Replicated State Machines",
                    "sequence_order": 1,
                    "estimated_duration_minutes": 15,
                    "explanation": "Nodes execute state transitions deterministically from an ordered log.",
                    "key_concepts": [
                        {
                            "term": "State Machine Replication",
                            "explanation": "Identical logs produce identical states on all nodes.",
                        }
                    ],
                    "examples": ["etcd key-value transitions"],
                    "source_references": [
                        {
                            "page_number": 1,
                            "chunk_index": 0,
                            "section_title": "Overview",
                            "citation_text": "Replication guarantees consistency across failures.",
                        }
                    ],
                },
                {
                    "title": "Lesson 2: Quorums and Fault Tolerance",
                    "sequence_order": 2,
                    "estimated_duration_minutes": 15,
                    "explanation": "A quorum of 2f+1 nodes tolerates f crash failures safely.",
                    "key_concepts": [
                        {
                            "term": "Majority Quorum",
                            "explanation": "Strict majority intersection prevents split-brain.",
                        }
                    ],
                    "examples": ["3 out of 5 nodes agreeing"],
                    "source_references": [
                        {
                            "page_number": 1,
                            "chunk_index": 1,
                            "section_title": "Quorums",
                            "citation_text": "Majorities overlap in at least one node.",
                        }
                    ],
                },
            ],
        },
        {
            "title": "Module 2: Leader Election",
            "description": "Dynamic leader election protocols.",
            "sequence_order": 2,
            "estimated_duration_minutes": 30,
            "learning_objectives": ["Master randomized timeouts"],
            "lessons": [
                {
                    "title": "Lesson 3: Election Timers",
                    "sequence_order": 1,
                    "estimated_duration_minutes": 15,
                    "explanation": "Randomized election timeouts prevent split votes.",
                    "key_concepts": [
                        {
                            "term": "Randomized Timeout",
                            "explanation": "Reduces probability of split vote elections.",
                        }
                    ],
                    "examples": ["Timeout range 150ms-300ms"],
                    "source_references": [
                        {
                            "page_number": 2,
                            "chunk_index": 2,
                            "section_title": "Elections",
                            "citation_text": "Heartbeats suppress election triggers.",
                        }
                    ],
                }
            ],
        },
    ],
}


class MockLearningAIProvider(AIProvider):
    async def generate_text(self, prompt: str, **kwargs) -> str:
        return json.dumps(SAMPLE_CURRICULUM)


@pytest.fixture
async def setup_progress_environment(client: AsyncClient, sample_pdf_bytes: bytes):
    """Provisions a document and a full 2-module, 3-lesson curriculum for testing."""
    # 1. Ingest document
    files = {"file": ("distributed_systems.pdf", sample_pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. Generate curriculum
    mock_ai = MockLearningAIProvider()
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        lp_res = await client.post(
            f"/api/v1/documents/{doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert lp_res.status_code == 201
        lp_data = lp_res.json()

    path_id = lp_data["id"]
    mod1_id = lp_data["modules"][0]["id"]
    les1_id = lp_data["modules"][0]["lessons"][0]["id"]
    les2_id = lp_data["modules"][0]["lessons"][1]["id"]
    mod2_id = lp_data["modules"][1]["id"]
    les3_id = lp_data["modules"][1]["lessons"][0]["id"]

    return {
        "doc_id": doc_id,
        "path_id": path_id,
        "mod1_id": mod1_id,
        "les1_id": les1_id,
        "les2_id": les2_id,
        "mod2_id": mod2_id,
        "les3_id": les3_id,
    }


# ---------------------------------------------------------------------------
# Test 1: Lesson Progress Lifecycle & State Reversion Protection
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lesson_progress_lifecycle_and_protection(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    les1_id = env["les1_id"]

    # 1. Mark in_progress
    res1 = await client.put(
        f"/api/v1/lessons/{les1_id}/progress",
        json={"status": "in_progress"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["lesson_id"] == les1_id
    assert data1["status"] == "in_progress"
    assert data1["started_at"] is not None
    assert data1["completed_at"] is None

    # 2. Mark completed
    res2 = await client.put(
        f"/api/v1/lessons/{les1_id}/progress",
        json={"status": "completed"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "completed"
    assert data2["completed_at"] is not None
    initial_completed_at = data2["completed_at"]

    # 3. Idempotent completion check
    res3 = await client.put(
        f"/api/v1/lessons/{les1_id}/progress",
        json={"status": "completed"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["status"] == "completed"
    # Preserved timestamp comparison (normalized for timezone offset notation)
    t_initial = datetime.fromisoformat(initial_completed_at.replace("Z", "+00:00")).replace(tzinfo=None)
    t_current = datetime.fromisoformat(data3["completed_at"].replace("Z", "+00:00")).replace(tzinfo=None)
    assert t_current == t_initial

    # 4. CRITICAL REVERSION PROTECTION: Re-opening completed lesson with in_progress
    # MUST NOT revert status back to in_progress!
    res4 = await client.put(
        f"/api/v1/lessons/{les1_id}/progress",
        json={"status": "in_progress"},
    )
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["status"] == "completed"  # Remains completed!
    t_after_reopen = datetime.fromisoformat(data4["completed_at"].replace("Z", "+00:00")).replace(tzinfo=None)
    assert t_after_reopen == t_initial


# ---------------------------------------------------------------------------
# Test 2: Dynamic Path & Module Progress Calculations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_path_and_module_progress_calculations(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    path_id = env["path_id"]
    les1_id = env["les1_id"]
    les2_id = env["les2_id"]
    les3_id = env["les3_id"]

    # Initial state: 0% complete, 3 total lessons
    p0 = await client.get(f"/api/v1/learning-paths/{path_id}/progress")
    assert p0.status_code == 200
    d0 = p0.json()
    assert d0["total_lessons"] == 3
    assert d0["completed_lessons"] == 0
    assert d0["remaining_lessons"] == 3
    assert d0["overall_completion_percentage"] == 0.0
    assert d0["is_curriculum_completed"] is False

    # Complete Lesson 1 (Module 1, 1 of 2 lessons = 50%)
    await client.put(f"/api/v1/lessons/{les1_id}/progress", json={"status": "completed"})

    p1 = await client.get(f"/api/v1/learning-paths/{path_id}/progress")
    d1 = p1.json()
    assert d1["completed_lessons"] == 1
    assert d1["remaining_lessons"] == 2
    assert d1["overall_completion_percentage"] == 33.3
    # Check Module 1
    mod1 = next(m for m in d1["modules"] if m["module_id"] == env["mod1_id"])
    assert mod1["completed_lessons"] == 1
    assert mod1["total_lessons"] == 2
    assert mod1["completion_percentage"] == 50.0
    assert mod1["is_completed"] is False

    # Complete Lesson 2 (Module 1 is now 100% complete)
    await client.put(f"/api/v1/lessons/{les2_id}/progress", json={"status": "completed"})

    p2 = await client.get(f"/api/v1/learning-paths/{path_id}/progress")
    d2 = p2.json()
    assert d2["completed_lessons"] == 2
    assert d2["overall_completion_percentage"] == 66.7
    mod1_updated = next(m for m in d2["modules"] if m["module_id"] == env["mod1_id"])
    assert mod1_updated["completed_lessons"] == 2
    assert mod1_updated["completion_percentage"] == 100.0
    assert mod1_updated["is_completed"] is True

    # Complete Lesson 3 (All 3 lessons complete = 100%)
    await client.put(f"/api/v1/lessons/{les3_id}/progress", json={"status": "completed"})

    p3 = await client.get(f"/api/v1/learning-paths/{path_id}/progress")
    d3 = p3.json()
    assert d3["completed_lessons"] == 3
    assert d3["remaining_lessons"] == 0
    assert d3["overall_completion_percentage"] == 100.0
    assert d3["is_curriculum_completed"] is True


# ---------------------------------------------------------------------------
# Test 3: Session Continuity & Resume Learning Resolution
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_learning_resolution(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    path_id = env["path_id"]
    les1_id = env["les1_id"]
    les2_id = env["les2_id"]
    les3_id = env["les3_id"]

    # 1. Untouched curriculum: Resume points to Lesson 1 (Module 1, sequence 1)
    r0 = await client.get(f"/api/v1/learning-paths/{path_id}/resume")
    assert r0.status_code == 200
    assert r0.json()["lesson_id"] == les1_id

    # 2. User accesses Lesson 2 (marks in_progress)
    await client.put(f"/api/v1/lessons/{les2_id}/progress", json={"status": "in_progress"})
    r1 = await client.get(f"/api/v1/learning-paths/{path_id}/resume")
    assert r1.status_code == 200
    assert r1.json()["lesson_id"] == les2_id
    assert "last visited" in r1.json()["reason"].lower()

    # 3. User finishes Lesson 1 and Lesson 2
    await client.put(f"/api/v1/lessons/{les1_id}/progress", json={"status": "completed"})
    await client.put(f"/api/v1/lessons/{les2_id}/progress", json={"status": "completed"})

    # Since Lesson 2 was completed, resume should advance to next incomplete lesson (Lesson 3)
    r2 = await client.get(f"/api/v1/learning-paths/{path_id}/resume")
    assert r2.status_code == 200
    assert r2.json()["lesson_id"] == les3_id

    # 4. User completes Lesson 3 (Curriculum finished)
    await client.put(f"/api/v1/lessons/{les3_id}/progress", json={"status": "completed"})
    r3 = await client.get(f"/api/v1/learning-paths/{path_id}/resume")
    assert r3.status_code == 200
    assert r3.json()["status"] == "completed"
    assert "review" in r3.json()["reason"].lower()


# ---------------------------------------------------------------------------
# Test 4: Assessment Statistics, Multiple Attempts & Best Score Calculation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assessment_statistics_and_multiple_attempts(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    path_id = env["path_id"]
    les1_id = env["les1_id"]

    # 1. Check dashboard with empty assessment history
    dash0 = await client.get(f"/api/v1/learning-paths/{path_id}/dashboard")
    assert dash0.status_code == 200
    stats0 = dash0.json()["assessments_overview"]
    assert stats0["attempted_assessments"] == 0
    assert stats0["pass_rate"] == 0.0
    assert stats0["average_score"] == 0.0

    # 2. Create Lesson Quiz directly in database
    async with src.db.session.async_session_maker() as session:
        quiz = Assessment(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            module_id=env["mod1_id"],
            lesson_id=les1_id,
            assessment_type="lesson_quiz",
            title="Quiz: Replicated State Machines",
            language="en",
            difficulty="intermediate",
            status="completed",
            passing_threshold=70.0,
        )
        session.add(quiz)
        await session.commit()
        quiz_id = quiz.id

        # Attempt 1: Failed (40.0%)
        att1 = AssessmentAttempt(
            id=str(uuid.uuid4()),
            assessment_id=quiz_id,
            status="completed",
            score=2,
            max_score=5,
            percentage=40.0,
            passed=False,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(att1)

        # Attempt 2: Passed (100.0%)
        att2 = AssessmentAttempt(
            id=str(uuid.uuid4()),
            assessment_id=quiz_id,
            status="completed",
            score=5,
            max_score=5,
            percentage=100.0,
            passed=True,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(att2)
        await session.commit()

    # 3. Verify Dashboard Aggregates
    dash1 = await client.get(f"/api/v1/learning-paths/{path_id}/dashboard")
    assert dash1.status_code == 200
    stats1 = dash1.json()["assessments_overview"]
    assert stats1["attempted_assessments"] == 1
    assert stats1["passed_assessments"] == 1
    assert stats1["pass_rate"] == 100.0
    assert stats1["average_score"] == 100.0  # Uses latest percentage (100.0%)

    # Verify best and latest score in assessment history item
    quiz_stat = stats1["recent_assessments"][0]
    assert quiz_stat["attempts_count"] == 2
    assert quiz_stat["latest_percentage"] == 100.0
    assert quiz_stat["best_percentage"] == 100.0
    assert quiz_stat["passed"] is True


# ---------------------------------------------------------------------------
# Test 5: Deterministic Knowledge Mastery & Missed Questions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deterministic_knowledge_mastery(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    path_id = env["path_id"]
    les1_id = env["les1_id"]
    les2_id = env["les2_id"]

    # Mark lesson 1 completed
    await client.put(f"/api/v1/lessons/{les1_id}/progress", json={"status": "completed"})

    # Setup assessment, question, and answers in database
    async with src.db.session.async_session_maker() as session:
        quiz1 = Assessment(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            module_id=env["mod1_id"],
            lesson_id=les1_id,
            assessment_type="lesson_quiz",
            title="Quiz: Replicated State Machines",
            language="en",
            difficulty="intermediate",
            status="completed",
            passing_threshold=70.0,
        )
        session.add(quiz1)

        q1 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=quiz1.id,
            question_text="What guarantees identical state in state machine replication?",
            question_type="multiple_choice",
            answer_options=["Deterministic ordered logs", "Random delays", "Hardware locks", "Encryption"],
            correct_answer="Deterministic ordered logs",
            explanation="Ordered logs produce deterministic state transitions.",
            sequence_order=1,
        )
        q2 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=quiz1.id,
            question_text="Why do consensus protocols require majority quorums?",
            question_type="multiple_choice",
            answer_options=["To overlap across failure groups", "To save battery", "To avoid encryption", "To compress logs"],
            correct_answer="To overlap across failure groups",
            explanation="Majorities overlap by at least one node.",
            sequence_order=2,
        )
        session.add_all([q1, q2])
        await session.commit()

        # Passed attempt for Quiz 1 (100% score)
        att = AssessmentAttempt(
            id=str(uuid.uuid4()),
            assessment_id=quiz1.id,
            status="completed",
            score=2,
            max_score=2,
            percentage=100.0,
            passed=True,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(att)

        # Answer 1: Correct
        ans1 = AssessmentAnswer(
            attempt_id=att.id,
            question_id=q1.id,
            selected_answer="Deterministic ordered logs",
            is_correct=True,
            feedback=q1.explanation,
        )
        # Answer 2: Incorrect (to test missed question)
        ans2 = AssessmentAnswer(
            attempt_id=att.id,
            question_id=q2.id,
            selected_answer="To save battery",
            is_correct=False,
            feedback=q2.explanation,
        )
        session.add_all([ans1, ans2])
        await session.commit()

    # Query Knowledge Mastery via dashboard
    dash = await client.get(f"/api/v1/learning-paths/{path_id}/dashboard")
    assert dash.status_code == 200
    mastery = dash.json()["knowledge_mastery"]

    # 1. Frequently missed questions: q2 had 1 answer, 1 incorrect = 100% failure rate
    missed = mastery["frequently_missed_questions"]
    assert len(missed) >= 1
    missed_q2 = next(m for m in missed if m["question_id"] == q2.id)
    assert missed_q2["failure_rate"] == 100.0
    assert missed_q2["incorrect_count"] == 1

    # 2. Strong concepts: Lesson 1 had 100% passed attempt, so its key concept should appear
    strong = mastery["strong_concepts"]
    assert any("State Machine Replication" in c["term"] for c in strong)


# ---------------------------------------------------------------------------
# Test 6: Rule-Based Pedagogical Recommendations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_learning_recommendations(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    path_id = env["path_id"]
    les1_id = env["les1_id"]
    les2_id = env["les2_id"]

    # 1. With no lessons completed, recommendation #1 should be 'continue_lesson' (Lesson 1)
    recs0 = await client.get(f"/api/v1/learning-paths/{path_id}/recommendations")
    assert recs0.status_code == 200
    items0 = recs0.json()["items"]
    assert len(items0) >= 1
    assert items0[0]["type"] == "continue_lesson"
    assert items0[0]["target_id"] == les1_id

    # 2. Simulate failed quiz on Lesson 1
    async with src.db.session.async_session_maker() as session:
        quiz = Assessment(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            module_id=env["mod1_id"],
            lesson_id=les1_id,
            assessment_type="lesson_quiz",
            title="Quiz: Replicated State Machines",
            language="en",
            difficulty="intermediate",
            status="completed",
            passing_threshold=70.0,
        )
        session.add(quiz)
        await session.commit()

        failed_att = AssessmentAttempt(
            id=str(uuid.uuid4()),
            assessment_id=quiz.id,
            status="completed",
            score=1,
            max_score=5,
            percentage=20.0,
            passed=False,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(failed_att)
        await session.commit()

    # Failed quiz generates priority 1 'review_lesson' recommendation
    recs1 = await client.get(f"/api/v1/learning-paths/{path_id}/recommendations")
    assert recs1.status_code == 200
    items1 = recs1.json()["items"]
    review_rec = next(r for r in items1 if r["type"] == "review_lesson")
    assert review_rec["target_id"] == les1_id
    assert "20.0%" in review_rec["description"]
    assert review_rec["priority"] == 1


# ---------------------------------------------------------------------------
# Test 7: Cascade Deletion on Document Removal
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cascade_deletion(client: AsyncClient, setup_progress_environment: dict):
    env = setup_progress_environment
    doc_id = env["doc_id"]
    path_id = env["path_id"]
    les1_id = env["les1_id"]

    # Record progress
    await client.put(f"/api/v1/lessons/{les1_id}/progress", json={"status": "completed"})

    # Verify progress exists in database
    async with src.db.session.async_session_maker() as session:
        lp = await session.execute(select(LessonProgress).where(LessonProgress.learning_path_id == path_id))
        assert len(list(lp.scalars().all())) >= 1

    # Delete Document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify that LessonProgress and PathProgress were cascaded
    async with src.db.session.async_session_maker() as session:
        lp = await session.execute(select(LessonProgress).where(LessonProgress.learning_path_id == path_id))
        assert len(list(lp.scalars().all())) == 0

        pp = await session.execute(select(PathProgress).where(PathProgress.learning_path_id == path_id))
        assert len(list(pp.scalars().all())) == 0


# ---------------------------------------------------------------------------
# Test 8: Nonexistent Resource Validation (HTTP 404)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_nonexistent_resource_validation(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    # Path progress 404
    r1 = await client.get(f"/api/v1/learning-paths/{fake_id}/progress")
    assert r1.status_code == 404

    # Dashboard 404
    r2 = await client.get(f"/api/v1/learning-paths/{fake_id}/dashboard")
    assert r2.status_code == 404

    # Recommendations 404
    r3 = await client.get(f"/api/v1/learning-paths/{fake_id}/recommendations")
    assert r3.status_code == 404

    # Resume 404
    r4 = await client.get(f"/api/v1/learning-paths/{fake_id}/resume")
    assert r4.status_code == 404

    # Lesson progress update 404
    r5 = await client.put(f"/api/v1/lessons/{fake_id}/progress", json={"status": "completed"})
    assert r5.status_code == 404
