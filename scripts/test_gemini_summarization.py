"""
TechSift AI - Live Integration Verification for Gemini Summarization (Phase 2).
Performs strictly 1 real API request with gemini-3.8-flash to conserve free-tier quota.
Validates end-to-end English -> Modern Standard Arabic technical summarization
and Pydantic JSON schema validation.
"""

import asyncio
import json
import logging
import sys
import src.models  # Ensures all SQLAlchemy models are registered
from src.core.config import settings
from src.models.document_chunk import DocumentChunk
from src.schemas.summary import DetailLevelEnum, LanguageEnum, TechnicalSummaryContent
from src.services.ai_provider import GeminiProvider
from src.services.summarizer_service import SummarizerService


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_gemini_summarization")


SAMPLE_TECHNICAL_TEXT = """
Raft is a consensus algorithm designed as an alternative to Paxos. It was meant to be more understandable
than Paxos by means of separation of logic, but it is also formally proven safe and offers some additional
features. Raft offers a generic way to distribute a state machine across a cluster of computing systems,
ensuring that each node in the cluster agrees upon the same series of state transitions.

Key features include:
1. Leader Election: A single leader server is elected by cluster members. The leader handles all client requests.
2. Log Replication: The leader accepts log entries from clients and replicates them across followers.
3. Safety: If any server has applied a particular log entry to its state machine, then no other server may apply a different command for the same log index.
4. RPC Communication: Raft nodes communicate using two main RPCs: RequestVote RPC and AppendEntries RPC.
"""


async def run_live_verification():
    logger.info("Starting Live Gemini Summarization Verification (Zero-Cost Free-Tier)...")
    logger.info(f"Target Model: {settings.GEMINI_MODEL}")
    logger.info(f"Target Output Language: Arabic (Modern Standard Arabic)")
    logger.info(f"Detail Level: Standard")

    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Aborting.")
        sys.exit(1)

    provider = GeminiProvider()
    summarizer = SummarizerService(ai_provider=provider)

    test_chunk = DocumentChunk(
        document_id="live-test-doc",
        chunk_index=0,
        content=SAMPLE_TECHNICAL_TEXT,
        page_number=1,
        start_char=0,
        end_char=len(SAMPLE_TECHNICAL_TEXT),
        section_title="Introduction to Raft Consensus",
    )

    logger.info("Executing 1 real Gemini request (English source -> Arabic summary)...")
    summary: TechnicalSummaryContent = await summarizer.summarize_document(
        chunks=[test_chunk],
        language=LanguageEnum.AR,
        detail_level=DetailLevelEnum.STANDARD,
    )

    logger.info("=== SUCCESS: Summary generated and validated by Pydantic ===")
    print("\n" + "=" * 60)
    print("EXECUTIVE SUMMARY (ARABIC):")
    print(summary.executive_summary)
    print("\nMAIN CONCEPTS IDENTIFIED:")
    for concept in summary.main_concepts:
        rels = f" (Related: {', '.join(concept.relationships)})" if concept.relationships else ""
        print(f" - {concept.term}: {concept.definition}{rels}")
    print("\nKEY FINDINGS:")
    for finding in summary.key_findings:
        print(f" * {finding}")
    print("\nKEY TAKEAWAYS:")
    for takeaway in summary.key_takeaways:
        print(f" > {takeaway}")
    print("\nMETADATA CITATIONS:")
    print(f" Source Pages: {summary.source_pages}")
    print(f" Source Chunks: {summary.source_chunks}")
    print("=" * 60 + "\n")

    # Assertions
    assert summary.executive_summary, "Executive summary must not be empty"
    assert len(summary.main_concepts) > 0, "Main concepts must not be empty"
    assert summary.source_pages == [1], f"Expected source pages [1], got {summary.source_pages}"
    assert 0 in summary.source_chunks, f"Expected chunk 0 in source chunks, got {summary.source_chunks}"

    logger.info("All live assertions PASSED. Exactly 1 API call consumed.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
