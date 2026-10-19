"""
TechSift AI - Automated Integration Tests for Interactive Learning Paths (Phase 5A).
Guarantees 100% zero-cost, offline execution using mocked AI provider.
Validates:
- Synchronous & asynchronous generation
- Bilingual English and Arabic curricula
- Beginner, Intermediate, and Advanced difficulties
- Strict source citation grounding against document chunks/pages
- Zero-cost caching & cache hits
- In-flight request deduplication
- Failure handling and retry
- Cascade deletion with parent document
- Startup recovery reconciliation
"""

import json
import uuid
from typing import Optional
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.learning_path import LearningPath, LearningModule, LearningLesson
from src.schemas.learning_path import GeneratedLearningPathContent, DifficultyEnum
from src.services.ai_provider import AIProvider
from src.db.session import async_session_maker
from src.services.learning_path_generator import learning_path_generator
from src.services.recovery_service import reconcile_interrupted_jobs


SAMPLE_EN_CURRICULUM = {
    "title": "Mastering Raft Distributed Consensus",
    "description": "A structured architectural curriculum on the Raft consensus protocol.",
    "difficulty": "intermediate",
    "estimated_duration_minutes": 45,
    "prerequisites": ["Basic understanding of distributed systems", "RPC mechanisms"],
    "learning_objectives": [
        "Explain leader election mechanisms",
        "Describe log replication invariants",
    ],
    "modules": [
        {
            "title": "Module 1: Foundations of Consensus",
            "description": "Introduction to replicated state machines and leader-based consensus.",
            "sequence_order": 1,
            "estimated_duration_minutes": 20,
            "learning_objectives": ["Identify split-brain conditions and resolution"],
            "lessons": [
                {
                    "title": "Lesson 1: Replicated State Machines",
                    "sequence_order": 1,
                    "estimated_duration_minutes": 10,
                    "explanation": "Replicated state machines ensure deterministic state across multiple independent nodes by executing log entries in identical order.",
                    "key_concepts": [
                        {
                            "term": "State Machine",
                            "explanation": "A system that transitions between states based on input events.",
                        }
                    ],
                    "examples": ["etcd and Consul use replicated logs for distributed configuration."],
                    "source_references": [
                        {
                            "page_number": 1,
                            "chunk_index": 0,
                            "section_title": "Introduction",
                            "citation_text": "Raft is an understandable consensus algorithm.",
                        }
                    ],
                }
            ],
        }
    ],
}

SAMPLE_AR_CURRICULUM = {
    "title": "إتقان خوارزمية التوافق الموزع Raft",
    "description": "منهج تعليمي معماري متكامل يشرح بروتوكول Raft لإدارة السجلات المكررة.",
    "difficulty": "beginner",
    "estimated_duration_minutes": 35,
    "prerequisites": ["أساسيات الشبكات وهندسة البرمجيات"],
    "learning_objectives": ["فهم آلية انتخاب القائد", "إدراك طريقة تكرار السجلات"],
    "modules": [
        {
            "title": "الوحدة 1: مقدمة في التوافق الموزع",
            "description": "مفهوم التوافق وكيفية تجنب تضارب البيانات في الخوادم الموزعة.",
            "sequence_order": 1,
            "estimated_duration_minutes": 15,
            "learning_objectives": ["التعرف على المشاكل التي تحلها خوارزميات التوافق"],
            "lessons": [
                {
                    "title": "الدرس 1: آلة الحالة المكررة (Replicated State Machine)",
                    "sequence_order": 1,
                    "estimated_duration_minutes": 10,
                    "explanation": "تعتمد الأنظمة الموزعة على آلات الحالة المكررة لضمان تطابق البيانات عند وقوع أعطال جزئية في الخوادم.",
                    "key_concepts": [
                        {
                            "term": "خوارزمية التوافق (Consensus)",
                            "explanation": "بروتوكول يتيح لمجموعة خوادم الاتفاق على قيمة مشتركة.",
                        }
                    ],
                    "examples": ["تستخدم قواعد البيانات الموزعة مثل etcd بروتوكول Raft."],
                    "source_references": [
                        {
                            "page_number": 1,
                            "chunk_index": 0,
                            "section_title": "مقدمة",
                            "citation_text": "بروتوكول Raft لإدارة سجل السجلات المكرر.",
                        }
                    ],
                }
            ],
        }
    ],
}


class MockLearningAIProvider(AIProvider):
    """Mocks AI provider generating valid learning curricula in English or Arabic."""

    def __init__(self, mode: str = "en", should_fail: bool = False):
        self.mode = mode
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Simulated Gemini API rate limit or outage")

        if self.mode == "ar" or "Modern Standard Arabic" in prompt:
            return json.dumps(SAMPLE_AR_CURRICULUM)
        return json.dumps(SAMPLE_EN_CURRICULUM)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        return await self.generate_content(prompt, system_instruction)


@pytest.fixture
async def sample_doc_id(client: AsyncClient, sample_pdf_bytes: bytes) -> str:
    """Uploads a PDF document and returns its ID."""
    files = {"file": ("raft_paper.pdf", sample_pdf_bytes, "application/pdf")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# Test 1: Synchronous English Learning Path Generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_learning_path_sync_en(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert res.status_code == 201
        data = res.json()

        assert data["document_id"] == sample_doc_id
        assert data["language"] == "en"
        assert data["difficulty"] == "intermediate"
        assert data["status"] == "completed"
        assert data["is_cached"] is False
        assert len(data["modules"]) == 1

        module = data["modules"][0]
        assert module["title"] == "Module 1: Foundations of Consensus"
        assert len(module["lessons"]) == 1

        lesson = module["lessons"][0]
        assert lesson["title"] == "Lesson 1: Replicated State Machines"
        assert len(lesson["key_concepts"]) == 1
        assert lesson["key_concepts"][0]["term"] == "State Machine"
        assert len(lesson["source_references"]) == 1
        assert lesson["source_references"][0]["chunk_index"] == 0
        assert mock_ai.call_count == 1


# ---------------------------------------------------------------------------
# Test 2: Synchronous Arabic Learning Path Generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_learning_path_sync_ar(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="ar")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "ar", "difficulty": "beginner"},
        )
        assert res.status_code == 201
        data = res.json()

        assert data["language"] == "ar"
        assert data["difficulty"] == "beginner"
        assert data["status"] == "completed"
        assert "إتقان خوارزمية" in data["title"]
        assert len(data["modules"]) == 1
        assert "الوحدة 1" in data["modules"][0]["title"]


# ---------------------------------------------------------------------------
# Test 3: Zero-Cost Cache Hit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_learning_path_cache_hit(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        # First request (miss)
        res1 = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert res1.status_code == 201
        assert res1.json()["is_cached"] is False
        assert mock_ai.call_count == 1

        # Second request (hit)
        res2 = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert res2.status_code == 201
        assert res2.json()["is_cached"] is True
        assert res2.json()["id"] == res1.json()["id"]
        # AI provider was NOT called again (zero cost)
        assert mock_ai.call_count == 1


# ---------------------------------------------------------------------------
# Test 4: Asynchronous Generation and Polling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_learning_path_async_flow(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        # Request with wait=false
        res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=false",
            json={"language": "en", "difficulty": "advanced"},
        )
        assert res.status_code == 201
        data = res.json()
        path_id = data["id"]
        assert data["status"] in ["pending", "processing", "completed"]

        # Poll path by ID until completed
        import asyncio
        for _ in range(20):
            get_res = await client.get(f"/api/v1/learning-paths/{path_id}")
            assert get_res.status_code == 200
            current = get_res.json()
            if current["status"] == "completed":
                assert len(current["modules"]) > 0
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Async learning path generation did not complete in time")


# ---------------------------------------------------------------------------
# Test 5: In-Flight Duplicate Request Deduplication
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_learning_path_in_flight_deduplication(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        # Create an async path
        res1 = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=false",
            json={"language": "en", "difficulty": "beginner"},
        )
        assert res1.status_code == 201
        path1 = res1.json()

        # Concurrent request while path is in flight
        res2 = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=false",
            json={"language": "en", "difficulty": "beginner"},
        )
        # Returns the same path ID without spawning duplicate work
        assert res2.status_code == 201
        assert res2.json()["id"] == path1["id"]


# ---------------------------------------------------------------------------
# Test 6: Failure Handling and Retry
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_learning_path_failure_and_retry(client: AsyncClient, sample_doc_id: str):
    with patch.object(
        learning_path_generator,
        "generate_curriculum",
        side_effect=RuntimeError("Simulated LLM unrecoverable pipeline failure"),
    ):
        res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        # Returns 201 with failed status and error message
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "failed"
        assert "Simulated LLM unrecoverable pipeline failure" in data["error_message"]

    # Now retry with working AI provider
    working_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", working_ai):
        retry_res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert retry_res.status_code == 201
        assert retry_res.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 7: Strict Source Reference Grounding Sanitization
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_source_reference_grounding_sanitization(client: AsyncClient, sample_doc_id: str):
    # Construct an AI response with hallucinated chunk index and page number
    hallucinated_curriculum = json.loads(json.dumps(SAMPLE_EN_CURRICULUM))
    hallucinated_curriculum["modules"][0]["lessons"][0]["source_references"].append({
        "page_number": 9999,  # Non-existent page
        "chunk_index": 8888,  # Non-existent chunk
        "section_title": "Phantom Section",
        "citation_text": "Hallucinated citation",
    })

    class HallucinatingAI(AIProvider):
        async def generate_content(self, *args, **kwargs) -> str:
            return json.dumps(hallucinated_curriculum)

        async def generate_text(self, *args, **kwargs) -> str:
            return json.dumps(hallucinated_curriculum)

    with patch.object(learning_path_generator, "ai_provider", HallucinatingAI()):
        res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert res.status_code == 201
        data = res.json()
        refs = data["modules"][0]["lessons"][0]["source_references"]
        # Assert the generator sanitized/cleared the invalid chunk_index and page_number
        for ref in refs:
            if ref.get("section_title") == "Phantom Section":
                assert ref["page_number"] is None
                assert ref["chunk_index"] is None


# ---------------------------------------------------------------------------
# Test 8: Document Deletion Cascades to Learning Paths
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_deletion_cascades_learning_paths(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        create_res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert create_res.status_code == 201
        path_id = create_res.json()["id"]

        # Verify path exists
        get_res = await client.get(f"/api/v1/learning-paths/{path_id}")
        assert get_res.status_code == 200

        # Delete document
        del_res = await client.delete(f"/api/v1/documents/{sample_doc_id}")
        assert del_res.status_code == 200

        # Path should now be deleted via cascade
        get_after_del = await client.get(f"/api/v1/learning-paths/{path_id}")
        assert get_after_del.status_code == 404


# ---------------------------------------------------------------------------
# Test 9: Startup Recovery Reconciles Interrupted Learning Paths
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_startup_recovery_reconciles_interrupted_learning_paths(
    client: AsyncClient,
    sample_doc_id: str,
):
    from datetime import datetime, timedelta, timezone
    import src.db.session

    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with src.db.session.async_session_maker() as session:
        interrupted_path = LearningPath(
            id=str(uuid.uuid4()),
            document_id=sample_doc_id,
            language="en",
            difficulty="intermediate",
            title="Interrupted Learning Path",
            description="Simulated interrupted state",
            estimated_duration_minutes=30,
            status="processing",
            prerequisites=[],
            learning_objectives=[],
            created_at=past_time,
        )
        session.add(interrupted_path)
        await session.commit()
        path_id = interrupted_path.id

    # Run recovery service
    async with src.db.session.async_session_maker() as session:
        stats = await reconcile_interrupted_jobs(session, startup_cutoff=cutoff)
        assert stats.get("learning_paths", 0) >= 1

    # Verify status changed to failed
    async with src.db.session.async_session_maker() as session:
        updated_path = await session.get(LearningPath, path_id)
        assert updated_path is not None
        assert updated_path.status == "failed"
        assert "interrupted by server shutdown" in updated_path.error_message


# ---------------------------------------------------------------------------
# Test 10: List and Get Nonexistent Endpoints
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_and_get_endpoints(client: AsyncClient, sample_doc_id: str):
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        # Create one path
        await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )

        # List paths for document
        list_res = await client.get(f"/api/v1/documents/{sample_doc_id}/learning-paths")
        assert list_res.status_code == 200
        data = list_res.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        # 404 on nonexistent path
        fake_id = str(uuid.uuid4())
        not_found_res = await client.get(f"/api/v1/learning-paths/{fake_id}")
        assert not_found_res.status_code == 404


# ---------------------------------------------------------------------------
# Test 11: Regression: Empty Path Response & Schema Compatibility
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_empty_learning_paths_and_serialization_compatibility(
    client: AsyncClient, sample_doc_id: str
):
    """
    Regression test ensuring:
    1. A fresh document with no paths returns empty items list without 404 or crash.
    2. Completed paths return properly typed key_concepts, examples, and citations.
    """
    # 1. Fresh document has empty items list
    empty_res = await client.get(f"/api/v1/documents/{sample_doc_id}/learning-paths")
    assert empty_res.status_code == 200
    empty_payload = empty_res.json()
    assert "items" in empty_payload
    assert empty_payload["items"] == []
    assert empty_payload["total"] == 0

    # 2. Path with rich lesson payloads validates without schema errors
    mock_ai = MockLearningAIProvider(mode="en")
    with patch.object(learning_path_generator, "ai_provider", mock_ai):
        gen_res = await client.post(
            f"/api/v1/documents/{sample_doc_id}/learning-paths?wait=true",
            json={"language": "en", "difficulty": "intermediate"},
        )
        assert gen_res.status_code == 201
        path_payload = gen_res.json()
        assert len(path_payload["modules"]) > 0
        first_mod = path_payload["modules"][0]
        assert len(first_mod["lessons"]) > 0
        first_les = first_mod["lessons"][0]
        assert "key_concepts" in first_les
        assert "examples" in first_les
        assert "source_references" in first_les

