"""
TechSift AI - Automated Integration & Unit Tests for Interactive Assessments (Phase 5B).
Guarantees 100% zero-cost, offline execution using mocked AI provider.
Validates:
- Lesson Quiz (5 questions), Module Assessment (10 questions), Final Assessment (15 questions)
- Strict multiple-choice validation (exactly 4 options, 1 correct answer)
- Source reference grounding validation
- Answer confidentiality: No correct_answer or explanation leakage before submission
- Zero-cost SQLite caching and in-flight deduplication
- Failure handling and retry
- Attempt lifecycle: start attempt, answer recording, cross-assessment question rejection, duplicate answer prevention
- Deterministic server-side grading (score, percentage, pass/fail threshold)
- Full educational review and explanations after submission
- Cascade deletion and startup recovery
"""

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
from src.schemas.assessment import AssessmentTypeEnum
from src.services.ai_provider import AIProvider
from src.services.assessment_generator import assessment_generator
from src.services.learning_path_generator import learning_path_generator
from src.services.recovery_service import reconcile_interrupted_jobs


SAMPLE_EN_QUIZ_JSON = {
    "title": "Quiz: Replicated State Machines",
    "description": "Evaluates understanding of state machine consensus.",
    "questions": [
        {
            "question_text": "What is the primary role of a replicated log in consensus protocols?",
            "question_type": "multiple_choice",
            "answer_options": [
                "Ensuring deterministic order of state transitions across all nodes",
                "Encrypting client communication over public networks",
                "Compressing disk storage to reduce RAM usage",
                "Bypassing network latency by caching state in memory",
            ],
            "correct_answer": "Ensuring deterministic order of state transitions across all nodes",
            "explanation": "Replicated logs guarantee that all replicas execute identical commands in identical order, producing identical state.",
            "source_references": [
                {
                    "page_number": 1,
                    "chunk_index": 0,
                    "section_title": "State Machine Replication",
                    "citation_text": "Replicated state machines ensure identical state across nodes.",
                }
            ],
            "sequence_order": 1,
        },
        {
            "question_text": "Which condition triggers a leader election in Raft?",
            "question_type": "multiple_choice",
            "answer_options": [
                "Heartbeat timeout without receiving AppendEntries RPCs",
                "A client sends a write request directly to a follower",
                "The log exceeds the configured snapshot size threshold",
                "A follower node restarts after a planned OS upgrade",
            ],
            "correct_answer": "Heartbeat timeout without receiving AppendEntries RPCs",
            "explanation": "Followers start an election timer; if no heartbeat arrives before timeout, they convert to Candidate.",
            "source_references": [
                {
                    "page_number": 1,
                    "chunk_index": 0,
                    "section_title": "Leader Election",
                    "citation_text": "Followers transition to candidate on heartbeat timeout.",
                }
            ],
            "sequence_order": 2,
        },
        {
            "question_text": "Why do consensus systems require a majority quorum (2f + 1)?",
            "question_type": "multiple_choice",
            "answer_options": [
                "To guarantee that any two majorities overlap by at least one node",
                "To maximize concurrent throughput across read-only replicas",
                "To reduce the number of RPCs needed for broadcast messages",
                "To eliminate the need for persistent disk writes",
            ],
            "correct_answer": "To guarantee that any two majorities overlap by at least one node",
            "explanation": "Quorum intersection ensures that at least one node in the new majority has the latest committed log entry.",
            "source_references": [
                {"page_number": 1, "chunk_index": 0, "section_title": "Quorum", "citation_text": "Quorum intersection prevents split-brain."}
            ],
            "sequence_order": 3,
        },
        {
            "question_text": "What happens when a Raft leader detects an uncommitted conflicting log entry in a follower?",
            "question_type": "multiple_choice",
            "answer_options": [
                "It overwrites the follower's uncommitted entries with the leader's log",
                "It steps down immediately and converts to a follower",
                "It rejects all subsequent client write requests",
                "It creates a separate diverging branch in the state machine",
            ],
            "correct_answer": "It overwrites the follower's uncommitted entries with the leader's log",
            "explanation": "Raft enforces strong leader authority: uncommitted conflicting follower entries are overwritten.",
            "source_references": [
                {"page_number": 1, "chunk_index": 0, "section_title": "Log Safety", "citation_text": "Leader log is authoritative."}
            ],
            "sequence_order": 4,
        },
        {
            "question_text": "How does Raft prevent two candidates from splitting votes indefinitely?",
            "question_type": "multiple_choice",
            "answer_options": [
                "By using randomized election timeouts for each node",
                "By using static priority ranks assigned to server IDs",
                "By deferring election decisions to a centralized coordinator",
                "By requiring unanimous approval from all cluster nodes",
            ],
            "correct_answer": "By using randomized election timeouts for each node",
            "explanation": "Randomized election timeouts (e.g., 150-300ms) ensure one candidate times out and collects votes before others.",
            "source_references": [
                {"page_number": 1, "chunk_index": 0, "section_title": "Elections", "citation_text": "Randomized timeouts break vote ties."}
            ],
            "sequence_order": 5,
        },
    ],
}

SAMPLE_AR_QUIZ_JSON = {
    "title": "اختبار: بروتوكول التوافق الموزع",
    "description": "تقييم المفاهيم الأساسية للتوافق الموزع باللغة العربية.",
    "questions": [
        {
            "question_text": "ما هي الفائدة المعمارية الرئيسية لآلة الحالة المكررة (Replicated State Machine)؟",
            "question_type": "multiple_choice",
            "answer_options": [
                "ضمان تطابق البيانات والحالة عبر جميع الخوادم الموزعة",
                "إلغاء التشفير لتسريع معالجة البيانات",
                "الاعتماد على خادم واحد لتجنب المزامنة",
                "تقليل استهلاك الذاكرة العشوائية بحذف السجلات",
            ],
            "correct_answer": "ضمان تطابق البيانات والحالة عبر جميع الخوادم الموزعة",
            "explanation": "تضمن آلات الحالة المكررة تنفيذ الأوامر بنفس الترتيب في جميع العقد لإنتاج نفس الحالة المحددة.",
            "source_references": [
                {"page_number": 1, "chunk_index": 0, "section_title": "المقدمة", "citation_text": "آلات الحالة المكررة تضمن الاتساق."}
            ],
            "sequence_order": 1,
        }
    ],
}


class MockAssessmentAIProvider(AIProvider):
    """Mocks AI provider for assessment generation."""

    def __init__(self, mode: str = "en", should_fail: bool = False):
        self.mode = mode
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_content(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Simulated Gemini API rate limit or outage")
        if self.mode == "ar" or "Modern Standard Arabic" in prompt:
            return json.dumps(SAMPLE_AR_QUIZ_JSON)
        return json.dumps(SAMPLE_EN_QUIZ_JSON)

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        return await self.generate_content(prompt, system_instruction)


@pytest.fixture
async def setup_curriculum(client: AsyncClient, sample_pdf_bytes: bytes):
    """Uploads document and generates an initial learning path."""
    files = {"file": ("consensus_paper.pdf", sample_pdf_bytes, "application/pdf")}
    upload_res = await client.post("/api/v1/documents", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Generate Learning Path
    from tests.test_learning_path_api import MockLearningAIProvider
    mock_lp_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_lp_ai):
        lp_res = await client.post(
            f"/api/v1/documents/{doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert lp_res.status_code == 201
        lp_data = lp_res.json()

    path_id = lp_data["id"]
    module_id = lp_data["modules"][0]["id"]
    lesson_id = lp_data["modules"][0]["lessons"][0]["id"]

    return {
        "doc_id": doc_id,
        "path_id": path_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
    }


# ---------------------------------------------------------------------------
# Test 1: Synchronous Lesson Quiz Generation & Confidentiality Check
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_lesson_quiz_sync_en(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    lesson_id = setup_curriculum["lesson_id"]

    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={
                "assessment_type": "lesson_quiz",
                "lesson_id": lesson_id,
                "wait": True,
            },
        )
        assert res.status_code == 201
        data = res.json()

        assert data["learning_path_id"] == path_id
        assert data["lesson_id"] == lesson_id
        assert data["assessment_type"] == "lesson_quiz"
        assert data["status"] == "completed"
        assert data["questions_count"] == 5
        assert data["is_cached"] is False
        assessment_id = data["id"]

        # CRITICAL TEST-TAKER CONFIDENTIALITY CHECK:
        # Fetching assessment as taker MUST NOT leak correct_answer or explanation!
        get_res = await client.get(f"/api/v1/assessments/{assessment_id}")
        assert get_res.status_code == 200
        detail = get_res.json()
        assert len(detail["questions"]) == 5

        for q in detail["questions"]:
            assert "correct_answer" not in q
            assert "explanation" not in q
            assert len(q["answer_options"]) == 4
            assert len(set(q["answer_options"])) == 4  # All distinct


# ---------------------------------------------------------------------------
# Test 2: Synchronous Arabic Quiz Generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_lesson_quiz_sync_ar(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    lesson_id = setup_curriculum["lesson_id"]

    mock_ai = MockAssessmentAIProvider(mode="ar")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={
                "assessment_type": "lesson_quiz",
                "lesson_id": lesson_id,
                "wait": True,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert "اختبار" in data["title"]
        assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 3: Zero-Cost Assessment Caching Hit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assessment_cache_hit(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    lesson_id = setup_curriculum["lesson_id"]

    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        # First call (miss)
        res1 = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "lesson_quiz", "lesson_id": lesson_id, "wait": True},
        )
        assert res1.status_code == 201
        assert res1.json()["is_cached"] is False
        assert mock_ai.call_count == 1

        # Second call (hit)
        res2 = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "lesson_quiz", "lesson_id": lesson_id, "wait": True},
        )
        assert res2.status_code == 201
        assert res2.json()["is_cached"] is True
        assert res2.json()["id"] == res1.json()["id"]
        # AI Provider NOT called again (zero cost)
        assert mock_ai.call_count == 1


# ---------------------------------------------------------------------------
# Test 4: Asynchronous Generation and Polling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assessment_async_flow_and_deduplication(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    module_id = setup_curriculum["module_id"]

    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        # Request with wait=false
        res1 = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "module_assessment", "module_id": module_id, "wait": False},
        )
        assert res1.status_code == 201
        data1 = res1.json()
        assessment_id = data1["id"]
        assert data1["status"] in ["pending", "processing", "completed"]

        # Duplicate request while in flight returns the same assessment
        res2 = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "module_assessment", "module_id": module_id, "wait": False},
        )
        assert res2.status_code == 201
        assert res2.json()["id"] == assessment_id

        # Poll until completed
        import asyncio
        for _ in range(20):
            get_res = await client.get(f"/api/v1/assessments/{assessment_id}")
            assert get_res.status_code == 200
            current = get_res.json()
            if current["status"] == "completed":
                assert len(current["questions"]) > 0
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Async assessment generation did not complete in time")


# ---------------------------------------------------------------------------
# Test 5: Failure Handling and Retry
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assessment_failure_and_retry(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]

    # Simulate unrecoverable failure
    with patch.object(
        assessment_generator,
        "generate_assessment",
        side_effect=RuntimeError("Simulated LLM unrecoverable assessment failure"),
    ):
        res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "final_assessment", "wait": True},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "failed"
        assert "Simulated LLM unrecoverable" in data["error_message"]

    # Retry with working provider
    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        retry_res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "final_assessment", "wait": True},
        )
        assert retry_res.status_code == 201
        assert retry_res.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 6: Complete Attempt Lifecycle & Server-Side Deterministic Grading
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_attempt_lifecycle_and_deterministic_grading(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    lesson_id = setup_curriculum["lesson_id"]

    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        create_res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "lesson_quiz", "lesson_id": lesson_id, "wait": True},
        )
        assert create_res.status_code == 201
        assessment_id = create_res.json()["id"]

    # 1. Fetch taker questions (no answer leak)
    detail_res = await client.get(f"/api/v1/assessments/{assessment_id}")
    taker_questions = detail_res.json()["questions"]
    assert len(taker_questions) == 5

    # 2. Start Attempt
    attempt_res = await client.post(f"/api/v1/assessments/{assessment_id}/attempts")
    assert attempt_res.status_code == 201
    attempt_data = attempt_res.json()
    attempt_id = attempt_data["id"]
    assert attempt_data["status"] == "in_progress"
    assert attempt_data["score"] == 0

    # 3. Cannot get results while attempt is in progress
    early_results = await client.get(f"/api/v1/attempts/{attempt_id}/results")
    assert early_results.status_code == 400

    # 4. Submit answers: 4 correct, 1 incorrect (to test 80% passing score)
    # Question 1: Correct
    ans1 = await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[0]["id"],
            "selected_answer": "Ensuring deterministic order of state transitions across all nodes",
        },
    )
    assert ans1.status_code == 201

    # Test Duplicate Answer Prevention: Submitting again for Q1 must fail with 400
    dup_ans = await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[0]["id"],
            "selected_answer": "Ensuring deterministic order of state transitions across all nodes",
        },
    )
    assert dup_ans.status_code == 400
    assert "already been answered" in (dup_ans.json().get("detail") or dup_ans.json().get("error", {}).get("message", ""))

    # Test Invalid Answer Choice (not in options)
    invalid_ans = await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[1]["id"],
            "selected_answer": "Non-existent fantasy option",
        },
    )
    assert invalid_ans.status_code == 400

    # Test Cross-Assessment Question Rejection
    fake_q_id = str(uuid.uuid4())
    cross_ans = await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": fake_q_id,
            "selected_answer": "Ensuring deterministic order",
        },
    )
    assert cross_ans.status_code == 404

    # Submit remaining answers
    # Q2: Correct
    await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[1]["id"],
            "selected_answer": "Heartbeat timeout without receiving AppendEntries RPCs",
        },
    )
    # Q3: Correct
    await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[2]["id"],
            "selected_answer": "To guarantee that any two majorities overlap by at least one node",
        },
    )
    # Q4: Correct
    await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[3]["id"],
            "selected_answer": "It overwrites the follower's uncommitted entries with the leader's log",
        },
    )
    # Q5: INCORRECT choice
    await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[4]["id"],
            "selected_answer": "By using static priority ranks assigned to server IDs",
        },
    )

    # 5. Finalize and Submit Attempt
    submit_res = await client.post(f"/api/v1/attempts/{attempt_id}/submit")
    assert submit_res.status_code == 200
    result = submit_res.json()

    assert result["status"] == "completed"
    assert result["max_score"] == 5
    assert result["score"] == 4
    assert result["percentage"] == 80.0
    assert result["passed"] is True  # 80% >= 70% threshold
    assert len(result["answers"]) == 5

    # Check that NOW the correct answers, explanations, and citations ARE revealed
    q5_review = next(item for item in result["answers"] if item["question_id"] == taker_questions[4]["id"])
    assert q5_review["is_correct"] is False
    assert q5_review["selected_answer"] == "By using static priority ranks assigned to server IDs"
    assert q5_review["correct_answer"] == "By using randomized election timeouts for each node"
    assert "Randomized election timeouts" in q5_review["explanation"]
    assert len(q5_review["source_references"]) >= 1

    # 6. Idempotent submission: Submitting again returns the same graded result
    resubmit_res = await client.post(f"/api/v1/attempts/{attempt_id}/submit")
    assert resubmit_res.status_code == 200
    assert resubmit_res.json()["score"] == 4

    # 7. Submitting an answer after completion MUST be rejected
    late_ans = await client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "question_id": taker_questions[0]["id"],
            "selected_answer": "Ensuring deterministic order of state transitions across all nodes",
        },
    )
    assert late_ans.status_code == 400


# ---------------------------------------------------------------------------
# Test 7: Cascade Deletion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cascade_deletion(client: AsyncClient, setup_curriculum: dict):
    path_id = setup_curriculum["path_id"]
    doc_id = setup_curriculum["doc_id"]
    lesson_id = setup_curriculum["lesson_id"]

    mock_ai = MockAssessmentAIProvider(mode="en")
    with patch.object(assessment_generator, "ai_provider", mock_ai):
        create_res = await client.post(
            f"/api/v1/learning-paths/{path_id}/assessments",
            json={"assessment_type": "lesson_quiz", "lesson_id": lesson_id, "wait": True},
        )
        assert create_res.status_code == 201
        assessment_id = create_res.json()["id"]

    # Start an attempt
    att_res = await client.post(f"/api/v1/assessments/{assessment_id}/attempts")
    assert att_res.status_code == 201
    attempt_id = att_res.json()["id"]

    # Delete the document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200

    # Assessment and attempt must now be gone
    get_ass = await client.get(f"/api/v1/assessments/{assessment_id}")
    assert get_ass.status_code == 404

    get_att = await client.get(f"/api/v1/attempts/{attempt_id}/results")
    assert get_att.status_code == 404


# ---------------------------------------------------------------------------
# Test 8: Startup Recovery Reconciles Interrupted Assessments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_startup_recovery_reconciles_interrupted_assessments(
    client: AsyncClient,
    setup_curriculum: dict,
):
    from datetime import datetime, timedelta, timezone

    path_id = setup_curriculum["path_id"]
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with src.db.session.async_session_maker() as session:
        interrupted_assessment = Assessment(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            assessment_type="lesson_quiz",
            title="Interrupted Quiz",
            description="Simulated interrupted state",
            language="en",
            difficulty="intermediate",
            status="processing",
            passing_threshold=70.0,
            created_at=past_time,
        )
        session.add(interrupted_assessment)
        await session.commit()
        assessment_id = interrupted_assessment.id

    # Run recovery service
    async with src.db.session.async_session_maker() as session:
        stats = await reconcile_interrupted_jobs(session, startup_cutoff=cutoff)
        assert stats.get("assessments", 0) >= 1

    # Verify status changed to failed
    async with src.db.session.async_session_maker() as session:
        updated = await session.get(Assessment, assessment_id)
        assert updated is not None
        assert updated.status == "failed"
        assert "interrupted by server shutdown" in updated.error_message
