"""
Automated Integration Tests for TechSift AI Summarization Pipeline (Phase 2).
Uses mocked AI provider to ensure 100% zero-cost execution during test runs.
Validates bilingual translations (en->ar, ar->en, en->en, ar->ar),
caching, detail levels, status transitions, and chunk source grounding.
"""

import json
from typing import Optional
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from src.core.exceptions import RateLimitExceededError
from src.schemas.summary import (
    DetailLevelEnum,
    LanguageEnum,
    SummaryResponse,
    TechnicalSummaryContent,
)
from src.services.ai_provider import AIProvider
from src.services.summary_service import SummaryService

SAMPLE_EN_JSON = {
    "executive_summary": "Raft is an understandable consensus algorithm for managing replicated logs.",
    "main_concepts": [
        {
            "term": "Raft Protocol",
            "definition": "A consensus algorithm for managing a replicated state machine.",
            "relationships": ["Leader Election", "Log Replication"],
        },
        {
            "term": "Leader Election",
            "definition": "Elects a single leader server to handle client requests.",
            "relationships": ["Safety"],
        },
    ],
    "key_findings": [
        "Equivalent to Paxos in fault-tolerance and throughput.",
        "Significantly easier to reason about and teach.",
    ],
    "important_definitions": [
        {
            "term": "Log Replication",
            "definition": "Distributing log entries from leader to follower nodes.",
            "relationships": [],
        }
    ],
    "architecture_overview": "Three-state machine: Leader, Follower, Candidate communicating via RPCs.",
    "practical_applications": ["Distributed Key-Value Stores (etcd, Consul)"],
    "limitations": ["Requires 2f + 1 nodes to survive f server crashes."],
    "key_takeaways": [
        "Strong leader simplifies coordination.",
        "Safety invariant prevents conflicting log commitments.",
    ],
    "source_pages": [1],
    "source_chunks": [0],
}

SAMPLE_AR_JSON = {
    "executive_summary": "بروتوكول Raft هو خوارزمية إجماع وتوافق موزعة (Consensus Algorithm) لإدارة سجل السجلات المكرر (Replicated Log).",
    "main_concepts": [
        {
            "term": "بروتوكول Raft (Raft Protocol)",
            "definition": "خوارزمية إدارة السجلات المكررة وضمان التوافق بين الأجهزة الموزعة.",
            "relationships": ["Leader Election", "Log Replication"],
        },
        {
            "term": "انتخاب القائد (Leader Election)",
            "definition": "آلية لاختيار منسق رئيسي لمعالجة طلبات العملاء وتنسيق المزامنة.",
            "relationships": ["Safety"],
        },
    ],
    "key_findings": [
        "مكافئ لبروتوكول Paxos في تحمل الأخطاء والأداء.",
        "مصمم لسهولة الفهم والتنفيذ في الأنظمة الموزعة.",
    ],
    "important_definitions": [
        {
            "term": "Log Replication",
            "definition": "توزيع قيود السجل من الخادم القائد إلى الخوادم التابعة.",
            "relationships": [],
        }
    ],
    "architecture_overview": "تعتمد البنية على ثلاث حالات للعقد: Leader و Follower و Candidate.",
    "practical_applications": ["قواعد البيانات الموزعة مثل etcd و Consul"],
    "limitations": ["تتطلب أغلبية النصاب القانوني (Quorum) لتحمل فشل العقد."],
    "key_takeaways": [
        "القيادة الموحدة تبسط إدارة ومزامنة السجلات.",
        "ضمان الأمان يمنع تضارب الحالات بين الخوادم.",
    ],
    "source_pages": [1],
    "source_chunks": [0],
}


class MockBilingualAIProvider(AIProvider):
    """Mocks AI provider generating valid structured JSON in English or Arabic."""

    def __init__(self):
        self.call_count = 0

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        self.call_count += 1
        # If target language requested is Arabic
        if system_instruction and "MODERN STANDARD ARABIC" in system_instruction:
            return f"```json\n{json.dumps(SAMPLE_AR_JSON, ensure_ascii=False)}\n```"
        return f"```json\n{json.dumps(SAMPLE_EN_JSON)}\n```"


@pytest.fixture
def mock_ai_provider():
    return MockBilingualAIProvider()


@pytest.fixture(autouse=True)
def override_summarizer_ai_provider(mock_ai_provider):
    """Overrides the global SummarizerService AI provider with zero-cost mock."""
    with patch("src.services.summarizer_service.summarizer_service.ai_provider", mock_ai_provider):
        with patch("src.services.summary_service.SummarizerService") as mock_summarizer_cls:
            from src.services.summarizer_service import SummarizerService
            real_summarizer = SummarizerService(ai_provider=mock_ai_provider)
            mock_summarizer_cls.return_value = real_summarizer
            yield mock_ai_provider


@pytest.mark.asyncio
async def test_summarize_en_to_en(client: AsyncClient, sample_pdf_bytes: bytes):
    # 1. Upload English document
    files = {"file": ("raft.pdf", sample_pdf_bytes, "application/pdf")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Request English summary
    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "en"
    assert data["status"] == "completed"
    assert data["is_cached"] is False
    assert "Raft is an understandable consensus algorithm" in data["summary"]["executive_summary"]
    assert len(data["summary"]["main_concepts"]) >= 2
    assert data["summary"]["source_pages"] == [1]


@pytest.mark.asyncio
async def test_summarize_en_to_ar(client: AsyncClient, sample_pdf_bytes: bytes):
    # 1. Upload English document
    files = {"file": ("raft_en.pdf", sample_pdf_bytes, "application/pdf")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Request Arabic summary
    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "ar", "detail_level": "standard"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "ar"
    assert data["status"] == "completed"
    assert "بروتوكول Raft هو خوارزمية إجماع" in data["summary"]["executive_summary"]
    # Verify technical English terms are preserved alongside Arabic
    concept_terms = [c["term"] for c in data["summary"]["main_concepts"]]
    assert any("Raft Protocol" in term for term in concept_terms)
    assert any("Leader Election" in term for term in concept_terms)


@pytest.mark.asyncio
async def test_summarize_ar_to_en(client: AsyncClient):
    # 1. Upload Arabic document
    ar_text = "تعتبر الأنظمة الموزعة من أهم التحديات في هندسة البرمجيات. خوارزمية Raft توفر التوافق الفعال."
    files = {"file": ("arabic_doc.txt", ar_text.encode("utf-8"), "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Request English summary
    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "en"
    assert data["status"] == "completed"
    assert "Raft is an understandable consensus algorithm" in data["summary"]["executive_summary"]


@pytest.mark.asyncio
async def test_summarize_ar_to_ar(client: AsyncClient):
    # 1. Upload Arabic document
    ar_text = "خوارزمية Raft لإدارة السجلات المكررة وضمان التوافق."
    files = {"file": ("arabic_doc2.txt", ar_text.encode("utf-8"), "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Request Arabic summary
    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "ar", "detail_level": "standard"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "ar"
    assert "بروتوكول Raft" in data["summary"]["executive_summary"]


@pytest.mark.asyncio
async def test_summarize_all_detail_levels(client: AsyncClient):
    files = {"file": ("levels_test.txt", b"Consensus content for detail levels", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    for level in ["short", "standard", "detailed"]:
        res = await client.post(
            f"/api/v1/documents/{doc_id}/summaries",
            json={"language": "en", "detail_level": level},
        )
        assert res.status_code == 201
        assert res.json()["detail_level"] == level
        assert res.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_summary_caching_hit_and_miss(client: AsyncClient, mock_ai_provider):
    files = {"file": ("cache_test.txt", b"Caching test content", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    initial_calls = mock_ai_provider.call_count

    # First Call: Cache MISS
    res1 = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res1.status_code == 201
    assert res1.json()["is_cached"] is False
    assert mock_ai_provider.call_count == initial_calls + 1

    # Second Call (Identical params): Cache HIT (zero new AI calls)
    res2 = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res2.status_code == 201
    assert res2.json()["is_cached"] is True
    assert res2.json()["id"] == res1.json()["id"]
    # Assert zero additional calls to AI provider
    assert mock_ai_provider.call_count == initial_calls + 1


@pytest.mark.asyncio
async def test_list_and_get_summaries(client: AsyncClient):
    files = {"file": ("list_test.txt", b"Technical architecture notes", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # Generate English & Arabic summaries
    await client.post(f"/api/v1/documents/{doc_id}/summaries", json={"language": "en"})
    await client.post(f"/api/v1/documents/{doc_id}/summaries", json={"language": "ar"})

    # List summaries for document
    list_res = await client.get(f"/api/v1/documents/{doc_id}/summaries")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2

    # Get single summary by ID
    summary_id = list_data["items"][0]["id"]
    get_res = await client.get(f"/api/v1/summaries/{summary_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == summary_id


@pytest.mark.asyncio
async def test_summarize_nonexistent_document(client: AsyncClient):
    non_existent = "00000000-0000-0000-0000-000000000000"
    res = await client.post(
        f"/api/v1/documents/{non_existent}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_summarize_unsupported_scanned_pdf(client: AsyncClient, scanned_pdf_bytes: bytes):
    files = {"file": ("scanned.pdf", scanned_pdf_bytes, "application/pdf")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_CONTENT"


@pytest.mark.asyncio
async def test_summary_rate_limit_failure_recording(client: AsyncClient, monkeypatch):
    """Verifies that an AI rate limit or provider error marks the summary as failed."""
    files = {"file": ("rate_test.txt", b"Content that triggers rate limit", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    async def failing_generate(prompt, system_instruction=None):
        raise RateLimitExceededError("Google Gemini free-tier rate limit reached.")

    with patch("src.services.summarizer_service.summarizer_service.ai_provider.generate_text", failing_generate):
        res = await client.post(
            f"/api/v1/documents/{doc_id}/summaries",
            json={"language": "en", "detail_level": "standard"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "failed"
        assert "rate limit reached" in data["error_message"].lower()


@pytest.mark.asyncio
async def test_summary_background_status_transition(client: AsyncClient):
    """Verifies wait=False returns a pending/processing job and records in DB."""
    files = {"file": ("async_test.txt", b"Asynchronous summary test", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=false",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] in ("pending", "processing", "completed")
    summary_id = data["id"]

    # Verify queryable by ID
    get_res = await client.get(f"/api/v1/summaries/{summary_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == summary_id


@pytest.mark.asyncio
async def test_summary_async_full_lifecycle_and_polling(client: AsyncClient):
    """Verifies that wait=false starts background generation, poll succeeds with completed content, and cache is populated."""
    import asyncio

    files = {"file": ("async_full_cycle.txt", b"Full async lifecycle content test", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # Trigger async generation
    res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=false",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res.status_code == 201
    init_data = res.json()
    summary_id = init_data["id"]
    assert init_data["status"] in ("pending", "processing")
    assert init_data["summary"] is None

    # Poll until completed
    completed_data = None
    for _ in range(30):
        await asyncio.sleep(0.05)
        poll_res = await client.get(f"/api/v1/summaries/{summary_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed_data = poll_data
            break

    assert completed_data is not None, "Summary did not transition to completed in time"
    assert completed_data["status"] == "completed"
    assert completed_data["summary"] is not None
    assert "Raft is an understandable consensus algorithm" in completed_data["summary"]["executive_summary"]

    # Next call should hit SQLite cache
    cached_res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries",
        json={"language": "en", "detail_level": "standard"},
    )
    assert cached_res.status_code == 201
    assert cached_res.json()["is_cached"] is True
    assert cached_res.json()["id"] == summary_id


@pytest.mark.asyncio
async def test_summary_async_in_flight_deduplication(client: AsyncClient):
    """Verifies duplicate requests return the in-flight summary without duplicate jobs."""
    import asyncio

    files = {"file": ("async_dedup.txt", b"Deduplication test document content", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # Patch summarizer to delay so summary stays in-flight
    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.3)
        return f"```json\n{json.dumps(SAMPLE_EN_JSON)}\n```"

    with patch("src.services.summarizer_service.summarizer_service.ai_provider.generate_text", slow_generate):
        # First request starts in-flight job
        res1 = await client.post(
            f"/api/v1/documents/{doc_id}/summaries?wait=false",
            json={"language": "en", "detail_level": "standard"},
        )
        assert res1.status_code == 201
        data1 = res1.json()

        # Immediate second request for same params returns existing in-flight summary
        res2 = await client.post(
            f"/api/v1/documents/{doc_id}/summaries?wait=false",
            json={"language": "en", "detail_level": "standard"},
        )
        assert res2.status_code == 201
        data2 = res2.json()

        assert data2["id"] == data1["id"]
        assert data2["status"] in ("pending", "processing")


@pytest.mark.asyncio
async def test_summary_async_failure_allows_retry(client: AsyncClient):
    """Verifies that an async failure transitions to failed, and subsequent retry succeeds."""
    import asyncio

    files = {"file": ("async_retry.txt", b"Retry test document content", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 1. Trigger failure in background task
    async def failing_generate(*args, **kwargs):
        raise RateLimitExceededError("Simulated LLM rate limit")

    with patch("src.services.summarizer_service.summarizer_service.ai_provider.generate_text", failing_generate):
        res1 = await client.post(
            f"/api/v1/documents/{doc_id}/summaries?wait=false",
            json={"language": "en", "detail_level": "standard"},
        )
        assert res1.status_code == 201
        summary_id = res1.json()["id"]

        # Poll until failed
        failed_data = None
        for _ in range(30):
            await asyncio.sleep(0.05)
            poll_res = await client.get(f"/api/v1/summaries/{summary_id}")
            poll_data = poll_res.json()
            if poll_data["status"] == "failed":
                failed_data = poll_data
                break

        assert failed_data is not None, "Summary did not transition to failed"
        assert failed_data["status"] == "failed"
        assert "rate limit" in failed_data["error_message"].lower()

    # 2. Retry with normal mock provider
    retry_res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=false",
        json={"language": "en", "detail_level": "standard"},
    )
    assert retry_res.status_code == 201
    retry_data = retry_res.json()
    new_summary_id = retry_data["id"]
    assert new_summary_id != summary_id

    # Poll until new attempt is completed
    completed_data = None
    for _ in range(30):
        await asyncio.sleep(0.05)
        poll_res = await client.get(f"/api/v1/summaries/{new_summary_id}")
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed_data = poll_data
            break

    assert completed_data is not None, "Retried summary did not transition to completed"
    assert completed_data["status"] == "completed"
    assert completed_data["summary"] is not None


@pytest.mark.asyncio
async def test_summary_async_timeout_transitions_to_failed_and_retry_succeeds(client: AsyncClient):
    """
    Regression Test (Phase 4C Timeout Investigation):
    Verifies that when a Gemini call times out, the summary transitions to 'failed' with
    the explicit timeout error message, and a subsequent retry succeeds cleanly.
    """
    import asyncio
    from src.core.exceptions import AITimeoutError

    files = {"file": ("timeout_test.txt", b"Timeout test document content.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 1. Simulate Gemini timeout in background task
    async def timing_out_generate(*args, **kwargs):
        raise AITimeoutError("Gemini API request timed out after 60.0s on model 'gemini-3.8-flash'.")

    with patch("src.services.summarizer_service.summarizer_service.ai_provider.generate_text", timing_out_generate):
        res1 = await client.post(
            f"/api/v1/documents/{doc_id}/summaries?wait=false",
            json={"language": "ar", "detail_level": "detailed"},
        )
        assert res1.status_code == 201
        summary_id = res1.json()["id"]

        # Poll until status is 'failed'
        failed_data = None
        for _ in range(30):
            await asyncio.sleep(0.05)
            poll_res = await client.get(f"/api/v1/summaries/{summary_id}")
            poll_data = poll_res.json()
            if poll_data["status"] == "failed":
                failed_data = poll_data
                break

        assert failed_data is not None, "Summary did not transition to failed"
        assert failed_data["status"] == "failed"
        assert "timed out after 60.0s" in failed_data["error_message"]

    # 2. Retry with normal mock provider
    retry_res = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=false",
        json={"language": "ar", "detail_level": "detailed"},
    )
    assert retry_res.status_code == 201
    retry_data = retry_res.json()
    new_summary_id = retry_data["id"]
    assert new_summary_id != summary_id

    # Poll until completed
    completed_data = None
    for _ in range(30):
        await asyncio.sleep(0.05)
        poll_res = await client.get(f"/api/v1/summaries/{new_summary_id}")
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed_data = poll_data
            break

    assert completed_data is not None, "Retried summary did not transition to completed"
    assert completed_data["status"] == "completed"
    assert completed_data["summary"] is not None


@pytest.mark.asyncio
async def test_summary_permanent_failure_marks_job_and_summary_as_failed(client: AsyncClient):
    """Verifies that permanent failure marks both summary and processing job as failed."""
    import asyncio
    from src.db.session import async_session_maker
    from src.repositories.job_repository import JobRepository
    from src.core.exceptions import AIModelUnavailableError

    files = {"file": ("perm_fail.txt", b"Permanent failure document content", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    async def permanent_failure(*args, **kwargs):
        raise AIModelUnavailableError("All candidate models exhausted.")

    with patch("src.services.summarizer_service.summarizer_service.ai_provider.generate_text", permanent_failure):
        res = await client.post(
            f"/api/v1/documents/{doc_id}/summaries?wait=false",
            json={"language": "en", "detail_level": "standard"},
        )
        assert res.status_code == 201
        summary_id = res.json()["id"]

        failed_data = None
        for _ in range(30):
            await asyncio.sleep(0.05)
            poll_res = await client.get(f"/api/v1/summaries/{summary_id}")
            poll_data = poll_res.json()
            if poll_data["status"] == "failed":
                failed_data = poll_data
                break

        assert failed_data is not None
        assert failed_data["status"] == "failed"
        assert "All candidate models exhausted" in failed_data["error_message"]

        # Check job in database
        async with async_session_maker() as session:
            job_repo = JobRepository(session)
            jobs = await job_repo.list_by_document_id(doc_id)
            assert len(jobs) >= 1
            latest_job = jobs[0]
            assert latest_job.status == "failed"
            assert "All candidate models exhausted" in latest_job.error_message


@pytest.mark.asyncio
async def test_summary_schema_normalization_executive_overview_and_taxonomy():
    """Regression test for Bug 1: Verifies that TechnicalSummaryContent normalizes legacy/synonymous keys."""
    from src.schemas.summary import TechnicalSummaryContent

    raw_data = {
        "executive_overview": "This is an executive overview of the system architecture.",
        "key_takeaways": ["Takeaway 1", "Takeaway 2"],
        "concepts_taxonomy": [
            {
                "term": "Raft Invariant",
                "definition": "Monotonic term sequence enforcing state consistency.",
                "category": "Safety"
            }
        ],
        "citations": [
            {"section": "Section 1", "page_chunk": "Chunk 0"},
            {"section": "Section 2", "page_chunk": "Chunk 3"}
        ]
    }

    content = TechnicalSummaryContent.model_validate(raw_data)
    assert content.executive_summary == "This is an executive overview of the system architecture."
    assert len(content.main_concepts) == 1
    assert content.main_concepts[0].term == "Raft Invariant"
    assert content.main_concepts[0].definition == "Monotonic term sequence enforcing state consistency."
    assert content.main_concepts[0].category == "Safety"
    assert len(content.key_takeaways) == 2
    assert content.source_chunks == [0, 3]


@pytest.mark.asyncio
async def test_summary_response_from_orm_model_with_aliased_keys():
    """Regression test for Bug 1: Verifies SummaryResponse.from_orm_model parses aliased content_data."""
    from datetime import datetime, timezone
    import uuid
    from src.models.summary import Summary
    from src.schemas.summary import SummaryResponse

    now = datetime.now(timezone.utc)
    mock_summary = Summary(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        language="ar",
        detail_level="standard",
        model_used="gemini-3.8-flash",
        status="completed",
        content_data={
            "executive_overview": "تستعرض هذه الوثيقة خوارزمية رافت للتوافق الموزع.",
            "key_takeaways": ["القائد المركزي يستقبل طلبات التعديل."],
            "concepts_taxonomy": [
                {
                    "term": "الفترة الزمنية",
                    "definition": "عداد زمني متزايد يحدد الحقبة المنطقية.",
                    "category": "التزامن"
                }
            ],
            "citations": [{"section": "المقدمة", "page_chunk": "القسم الأول"}]
        },
        error_message=None,
        created_at=now,
        updated_at=now,
    )

    response = SummaryResponse.from_orm_model(mock_summary, is_cached=True)
    assert response.status.value == "completed"
    assert response.is_cached is True
    assert response.summary is not None
    assert "خوارزمية رافت" in response.summary.executive_summary
    assert len(response.summary.main_concepts) == 1
    assert response.summary.main_concepts[0].term == "الفترة الزمنية"
    assert response.summary.main_concepts[0].category == "التزامن"


@pytest.mark.asyncio
async def test_cached_summary_retrieval_returns_populated_content(client: AsyncClient):
    """Regression test for Bug 2: Verifies that cached summary retrieval returns full summary content."""
    files = {"file": ("cached_test.txt", b"Deterministic consensus protocol documentation.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 1. Generate first summary (synchronous wait=true)
    res1 = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=true",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["status"] == "completed"
    assert data1["is_cached"] is False
    assert data1["summary"] is not None
    assert len(data1["summary"]["executive_summary"]) > 0

    # 2. Second request with identical parameters must hit cache and return populated content
    res2 = await client.post(
        f"/api/v1/documents/{doc_id}/summaries?wait=false",
        json={"language": "en", "detail_level": "standard"},
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["id"] == data1["id"]
    assert data2["status"] == "completed"
    assert data2["is_cached"] is True
    assert data2["summary"] is not None
    assert data2["summary"]["executive_summary"] == data1["summary"]["executive_summary"]



