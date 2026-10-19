"""
TechSift AI - Safe Portfolio Demo Environment Preparation Script.
Initializes an isolated demo database (demo_techsift.db) and storage directory (demo_storage/)
using ONLY original synthetic technical documents from samples/.
Zero modification of user data, zero external paid API calls.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
import uuid

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.models.audio_track import AudioTrack
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
)
from src.models.learning_progress import LessonProgress, PathProgress


DEMO_DB_PATH = Path(os.environ.get("DEMO_DB_PATH", "./demo_techsift.db"))
DEMO_STORAGE_DIR = Path(os.environ.get("DEMO_STORAGE_DIR", "./demo_storage"))
DEMO_DOCUMENTS_DIR = DEMO_STORAGE_DIR / "documents"
DEMO_AUDIO_DIR = DEMO_STORAGE_DIR / "audio"
SAMPLES_DIR = Path("./samples")
FEASIBILITY_AUDIO_DIR = Path("./storage/audio_feasibility")

ASYNC_DB_URL = f"sqlite+aiosqlite:///{DEMO_DB_PATH.resolve()}"


def init_demo_storage():
    """Create isolated demo storage folders."""
    DEMO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


async def create_demo_tables(engine):
    """Create all schema tables in demo_techsift.db."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_demo_data():
    """Seed comprehensive realistic demonstration data into demo_techsift.db."""
    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    await create_demo_tables(engine)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now(timezone.utc)

    # 1. Read synthetic sample files
    raft_md_path = SAMPLES_DIR / "distributed_consensus_raft_architecture.md"
    microservices_txt_path = SAMPLES_DIR / "event_driven_microservices_architecture.txt"
    caching_pdf_path = SAMPLES_DIR / "distributed_caching_and_consistency.pdf"

    raft_content = raft_md_path.read_text(encoding="utf-8")
    microservices_content = microservices_txt_path.read_text(encoding="utf-8")
    caching_bytes = caching_pdf_path.read_bytes()

    # Copy files into demo storage
    doc1_storage_name = f"doc_{uuid.uuid4().hex[:8]}_raft.md"
    doc2_storage_name = f"doc_{uuid.uuid4().hex[:8]}_microservices.txt"
    doc3_storage_name = f"doc_{uuid.uuid4().hex[:8]}_caching.pdf"

    (DEMO_DOCUMENTS_DIR / doc1_storage_name).write_text(raft_content, encoding="utf-8")
    (DEMO_DOCUMENTS_DIR / doc2_storage_name).write_text(microservices_content, encoding="utf-8")
    (DEMO_DOCUMENTS_DIR / doc3_storage_name).write_bytes(caching_bytes)

    # Copy synthetic feasibility audio files into demo storage
    audio_narration_filename = "raft_narration_ar.mp3"
    audio_podcast_filename = "raft_podcast_episode.mp3"

    src_ar_audio = FEASIBILITY_AUDIO_DIR / "edge_tts" / "arabic_male_shakir.mp3"
    src_podcast_audio = FEASIBILITY_AUDIO_DIR / "podcast_en" / "podcast_en_episode.mp3"

    if src_ar_audio.exists():
        shutil.copy2(src_ar_audio, DEMO_AUDIO_DIR / audio_narration_filename)
    else:
        (DEMO_AUDIO_DIR / audio_narration_filename).write_bytes(b"\xff\xfb\x90\x00" * 200)

    if src_podcast_audio.exists():
        shutil.copy2(src_podcast_audio, DEMO_AUDIO_DIR / audio_podcast_filename)
    else:
        (DEMO_AUDIO_DIR / audio_podcast_filename).write_bytes(b"\xff\xfb\x90\x00" * 400)

    async with session_maker() as session:
        # Document 1: Raft Consensus Architecture (Markdown)
        doc1_id = str(uuid.uuid4())
        doc1 = Document(
            id=doc1_id,
            filename="distributed_consensus_raft_architecture.md",
            file_type="md",
            file_size=len(raft_content.encode("utf-8")),
            storage_filename=f"documents/{doc1_storage_name}",
            content_hash=hashlib.sha256(raft_content.encode("utf-8")).hexdigest(),
            extracted_text=raft_content,
            word_count=len(raft_content.split()),
            page_count=None,
            status="processed",
            created_at=now,
            updated_at=now,
        )

        # Document 2: Event-Driven Microservices (TXT)
        doc2_id = str(uuid.uuid4())
        doc2 = Document(
            id=doc2_id,
            filename="event_driven_microservices_architecture.txt",
            file_type="txt",
            file_size=len(microservices_content.encode("utf-8")),
            storage_filename=f"documents/{doc2_storage_name}",
            content_hash=hashlib.sha256(microservices_content.encode("utf-8")).hexdigest(),
            extracted_text=microservices_content,
            word_count=len(microservices_content.split()),
            page_count=None,
            status="processed",
            created_at=now,
            updated_at=now,
        )

        # Document 3: Distributed In-Memory Caching (PDF)
        doc3_id = str(uuid.uuid4())
        doc3 = Document(
            id=doc3_id,
            filename="distributed_caching_and_consistency.pdf",
            file_type="pdf",
            file_size=len(caching_bytes),
            storage_filename=f"documents/{doc3_storage_name}",
            content_hash=hashlib.sha256(caching_bytes).hexdigest(),
            extracted_text="Distributed In-Memory Caching & Stampede Prevention Architecture...",
            word_count=650,
            page_count=3,
            status="processed",
            created_at=now,
            updated_at=now,
        )

        session.add_all([doc1, doc2, doc3])
        await session.flush()

        # Document Chunks for Doc 1
        chunk1 = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            chunk_index=0,
            section_title="Leader Election & Consensus Overview",
            start_char=0,
            end_char=2000,
            content=raft_content[:2000],
            created_at=now,
        )
        chunk2 = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            chunk_index=1,
            section_title="Log Replication & Safety Invariants",
            start_char=2000,
            end_char=len(raft_content),
            content=raft_content[2000:],
            created_at=now,
        )
        session.add_all([chunk1, chunk2])

        # Summaries for Doc 1
        # 1. English Summary
        summary1_en = Summary(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="completed",
            content_data={
                "executive_overview": (
                    "This specification details the Raft distributed consensus protocol, designed as an "
                    "understandable alternative to Paxos. It decomposes consensus into distinct subproblems: "
                    "leader election, log replication, and safety invariants. Through strong leader mechanics, "
                    "Raft guarantees replicated state machine consistency across distributed server clusters."
                ),
                "key_takeaways": [
                    "Strong Leader: Only the leader accepts client write requests and manages log entry dissemination.",
                    "Leader Election: Randomized election timeouts prevent split-vote deadlocks when electing candidates.",
                    "Log Matching Invariant: If two logs contain an entry with the same index and term, they are identical up to that index.",
                    "State Machine Safety: If a server applies a log entry at a given index, no other server will ever apply a different entry at that index.",
                    "Quorum Rule: All cluster state transitions require acknowledgment from a strict majority (N/2 + 1) of nodes.",
                ],
                "concepts_taxonomy": [
                    {
                        "term": "Term",
                        "definition": "Monotonically increasing logical epoch acting as a logical clock to detect obsolete leaders and stale candidates.",
                        "category": "Core Mechanism",
                    },
                    {
                        "term": "Log Matching Property",
                        "definition": "Invariant ensuring that log entries matching in term and index share identical preceding history.",
                        "category": "Safety Invariant",
                    },
                    {
                        "term": "Heartbeat",
                        "definition": "Periodic empty AppendEntries RPC broadcast by the leader to suppress candidate elections.",
                        "category": "Liveness",
                    },
                    {
                        "term": "Quorum",
                        "definition": "Strict majority of cluster nodes ((N/2) + 1) required to validate elections and commit log entries.",
                        "category": "Topology",
                    },
                ],
                "citations": [
                    {"section": "1. Introduction & Invariants", "page_chunk": "Chunk 0"},
                    {"section": "2. Protocol State Machine", "page_chunk": "Chunk 0"},
                    {"section": "3. Leader Election Mechanism", "page_chunk": "Chunk 1"},
                ],
            },
            created_at=now,
            updated_at=now,
        )

        # 2. Arabic Summary (RTL)
        summary1_ar = Summary(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            language="ar",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="completed",
            content_data={
                "executive_overview": (
                    "تستعرض هذه الوثيقة خوارزمية رافت (Raft) للتوافق الموزع كبديل منظم وقابل للفهم مقارنة ببروتوكول باكسوس. "
                    "تقوم الخوارزمية بتفكيك معضلة التوافق إلى ثلاث ركائز منفصلة: انتخاب القائد، تكرار سجل العمليات، وضمانات الأمان."
                ),
                "key_takeaways": [
                    "القائد المركزي: يستقبل القائد حصرياً جميع طلبات التعديل ويوزعها بتسلسل خطي صارم.",
                    "فترات الانتخاب العشوائية: استخدام مؤقتات عشوائية يمنع انقسام الأصوات وتكرار التعادل بين الخوادم.",
                    "قاعدة الأغلبية المطلقة: تتطلب كافة قرارات التثبيت موافقة أغلبية العقد (N/2 + 1) لضمان متانة النظام.",
                ],
                "concepts_taxonomy": [
                    {
                        "term": "الفترة الزمنية (Term)",
                        "definition": "عداد زمني متزايد يحدد الحقبة المنطقية للخادم ويكشف القادة غير النشطين.",
                        "category": "التزامن والوقت",
                    },
                    {
                        "term": "نبضات القلب (Heartbeat)",
                        "definition": "رسائل دورية فارغة يرسلها القائد إلى التوابع لتأكيد ليدرشيب العقدة وتفادي الانتخابات.",
                        "category": "حيوية النظام",
                    },
                ],
                "citations": [
                    {"section": "المقدمة والركائز", "page_chunk": "القسم الأول"},
                    {"section": "آلية الانتخاب", "page_chunk": "القسم الثاني"},
                ],
            },
            created_at=now,
            updated_at=now,
        )

        # Summaries for Doc 2 & Doc 3
        summary2 = Summary(
            id=str(uuid.uuid4()),
            document_id=doc2_id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="completed",
            content_data={
                "executive_overview": "Architectural patterns for asynchronous event sourcing, CQRS command-query separation, and consumer idempotency.",
                "key_takeaways": ["Outbox pattern guarantees at-least-once delivery.", "Consumers must enforce idempotency keys."],
                "concepts_taxonomy": [{"term": "CQRS", "definition": "Separating read and write data models."}],
            },
            created_at=now,
            updated_at=now,
        )

        summary3 = Summary(
            id=str(uuid.uuid4()),
            document_id=doc3_id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="completed",
            content_data={
                "executive_overview": "Comprehensive design for distributed in-memory caching, probabilistic early expiration, and cache stampede mitigation.",
                "key_takeaways": ["Cache-aside pattern minimizes memory exhaustion.", "Mutex locking prevents thundering herd."],
                "concepts_taxonomy": [{"term": "Cache Stampede", "definition": "Simultaneous cache misses overwhelming backend DB."}],
            },
            created_at=now,
            updated_at=now,
        )

        session.add_all([summary1_en, summary1_ar, summary2, summary3])

        # Audio Tracks for Doc 1
        # Track 1: Arabic Single Narration
        audio1 = AudioTrack(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            mode="narration",
            language="ar",
            voice_config={"voice": "ar-EG-ShakirNeural"},
            file_path=f"audio/{audio_narration_filename}",
            duration_seconds=42.5,
            file_size_bytes=68112,
            status="completed",
            config_hash=f"demo_hash_ar_{uuid.uuid4().hex[:6]}",
            script_content=None,
            created_at=now,
            updated_at=now,
        )

        # Track 2: English Multi-Speaker Educational Podcast
        podcast_script = [
            {
                "turn": 1,
                "speaker": "Host (Alex)",
                "voice": "en-US-GuyNeural",
                "text": "Welcome to TechSift Deep Dives. Today, we're dissecting Raft, one of the most elegant distributed consensus algorithms in modern computing.",
            },
            {
                "turn": 2,
                "speaker": "Co-host (Sarah)",
                "voice": "en-US-JennyNeural",
                "text": "Thanks Alex. Many engineers know Paxos is notoriously difficult to implement correctly. How does Raft make distributed consensus understandable?",
            },
            {
                "turn": 3,
                "speaker": "Host (Alex)",
                "voice": "en-US-GuyNeural",
                "text": "Raft breaks consensus into explicit, independent state transitions: leader election, log replication, and safety invariants, governed by terms that act as logical clocks.",
            },
            {
                "turn": 4,
                "speaker": "Co-host (Sarah)",
                "voice": "en-US-JennyNeural",
                "text": "And by enforcing the Log Matching Invariant and quorum commits across an N/2 + 1 majority, Raft guarantees zero data loss and state machine safety.",
            },
        ]

        audio2 = AudioTrack(
            id=str(uuid.uuid4()),
            document_id=doc1_id,
            mode="podcast",
            language="en",
            voice_config={"host_voice": "en-US-GuyNeural", "cohost_voice": "en-US-JennyNeural"},
            file_path=f"audio/{audio_podcast_filename}",
            duration_seconds=78.0,
            file_size_bytes=277292,
            status="completed",
            config_hash=f"demo_hash_pod_{uuid.uuid4().hex[:6]}",
            script_content={"dialogue": podcast_script},
            created_at=now,
            updated_at=now,
        )

        session.add_all([audio1, audio2])

        # Learning Path for Doc 1
        path_id = str(uuid.uuid4())
        path = LearningPath(
            id=path_id,
            document_id=doc1_id,
            title="Mastering Raft Distributed Consensus & Fault Tolerance",
            description="Comprehensive engineering curriculum covering leader elections, quorum mathematics, replicated log state machines, and compaction.",
            difficulty="intermediate",
            language="en",
            estimated_duration_minutes=95,
            status="completed",
            prerequisites=["Basic networking and RPC fundamentals", "Understanding of state machine replication"],
            learning_objectives=[
                "Explain the role of logical terms in detecting split-brain states.",
                "Trace the lifecycle of a log entry from client write to quorum commit.",
                "Analyze safety invariants that prevent state machine divergence.",
            ],
            created_at=now,
            updated_at=now,
        )
        session.add(path)
        await session.flush()

        # Module 1
        mod1_id = str(uuid.uuid4())
        mod1 = LearningModule(
            id=mod1_id,
            learning_path_id=path_id,
            title="Module 1: Foundations of Distributed Consensus",
            description="Core concepts of replicated state machines, Paxos vs Raft design philosophy, and quorum requirements.",
            sequence_order=1,
            estimated_duration_minutes=30,
            learning_objectives=["Understand state machine replication", "Calculate quorum majorities"],
            created_at=now,
        )

        # Module 2
        mod2_id = str(uuid.uuid4())
        mod2 = LearningModule(
            id=mod2_id,
            learning_path_id=path_id,
            title="Module 2: Raft Protocol State Machine & Quorum Mechanics",
            description="Leader election timeouts, AppendEntries RPC payloads, and log consistency invariants.",
            sequence_order=2,
            estimated_duration_minutes=35,
            learning_objectives=["Trace heartbeat exchanges", "Analyze log matching proofs"],
            created_at=now,
        )

        # Module 3
        mod3_id = str(uuid.uuid4())
        mod3 = LearningModule(
            id=mod3_id,
            learning_path_id=path_id,
            title="Module 3: Membership Transitions & Log Compaction",
            description="Dynamic cluster reconfiguration using joint consensus and memory snapshotting.",
            sequence_order=3,
            estimated_duration_minutes=30,
            learning_objectives=["Implement log compaction snapshots", "Manage live cluster reconfigurations"],
            created_at=now,
        )
        session.add_all([mod1, mod2, mod3])
        await session.flush()

        # Lessons for Module 1
        les1_id = str(uuid.uuid4())
        les1 = LearningLesson(
            id=les1_id,
            module_id=mod1_id,
            title="Lesson 1.1: Replicated State Machine Architecture",
            explanation=(
                "A replicated state machine operates on the principle that identical deterministic state machines "
                "starting from identical initial states and executing the identical sequence of operations will "
                "reach identical final states. The consensus module ensures every server's log receives identical inputs."
            ),
            sequence_order=1,
            estimated_duration_minutes=15,
            key_concepts=[
                {
                    "term": "Deterministic State Machine",
                    "explanation": "A state machine where identical inputs produce identical state transitions across all replica nodes.",
                },
                {
                    "term": "Consensus Module",
                    "explanation": "The algorithmic component ensuring all servers maintain an identical ordered sequence of log entries.",
                },
                {
                    "term": "WAL Replication",
                    "explanation": "Write-ahead logging discipline guaranteeing mutations are durable on disk before execution.",
                },
            ],
            examples=[
                (
                    "# State machine execution handler\n"
                    "def apply_log_entry(state: dict, entry: dict) -> dict:\n"
                    "    state[entry['key']] = entry['value']\n"
                    "    return state"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 1: Replicated State Machines",
                    "chunk_index": 0,
                    "citation_text": "Consensus algorithms keep the replicated log consistent across all cluster nodes.",
                }
            ],
            created_at=now,
        )

        les2_id = str(uuid.uuid4())
        les2 = LearningLesson(
            id=les2_id,
            module_id=mod1_id,
            title="Lesson 1.2: Quorum Mathematics & Fault Tolerance",
            explanation=(
                "In a cluster of N nodes, Raft requires a majority of floor(N/2) + 1 nodes to proceed. "
                "This guarantees that any two quorums overlap by at least one server, preserving safety."
            ),
            sequence_order=2,
            estimated_duration_minutes=15,
            key_concepts=[
                {
                    "term": "Quorum Majority",
                    "explanation": "Strict majority threshold (N/2 + 1) preventing split-brain states during network partitions.",
                },
                {
                    "term": "Fault Tolerance",
                    "explanation": "A cluster of 2F + 1 nodes can tolerate F node crashes without downtime.",
                },
                {
                    "term": "Overlapping Quorums",
                    "explanation": "Mathematical property ensuring any two majorities intersect on at least one shared node.",
                },
            ],
            examples=[
                (
                    "# Quorum calculation formula\n"
                    "def required_quorum(cluster_size: int) -> int:\n"
                    "    return (cluster_size // 2) + 1"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 1: Architectural Context",
                    "chunk_index": 0,
                    "citation_text": "A 5-node cluster requires 3 nodes to form a quorum and withstands 2 failures.",
                }
            ],
            created_at=now,
        )

        # Lessons for Module 2
        les3_id = str(uuid.uuid4())
        les3 = LearningLesson(
            id=les3_id,
            module_id=mod2_id,
            title="Lesson 2.1: Leader Election & Randomized Timeouts",
            explanation=(
                "Servers start as followers. If heartbeats from the leader cease, followers transition to candidates "
                "after a randomized timeout (150ms-300ms) to avoid simultaneous split votes."
            ),
            sequence_order=1,
            estimated_duration_minutes=20,
            key_concepts=[
                {
                    "term": "Candidate State",
                    "explanation": "Intermediate state where a node increments the current term and requests votes from peers.",
                },
                {
                    "term": "Randomized Timeouts",
                    "explanation": "Election timeouts scattered between 150ms-300ms preventing concurrent elections.",
                },
                {
                    "term": "RequestVote RPC",
                    "explanation": "Message sent by candidates requesting peer endorsement for cluster leadership.",
                },
            ],
            examples=[
                (
                    "# Randomized election timeout\n"
                    "import random, time\n"
                    "timeout = random.uniform(0.150, 0.300)  # 150ms to 300ms"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 2: Leader Election",
                    "chunk_index": 1,
                    "citation_text": "Randomized election timeouts ensure split-vote deadlocks are rapidly resolved.",
                }
            ],
            created_at=now,
        )

        les4_id = str(uuid.uuid4())
        les4 = LearningLesson(
            id=les4_id,
            module_id=mod2_id,
            title="Lesson 2.2: Log Matching Property & Invariants",
            explanation=(
                "When a leader appends a log entry, it sends AppendEntries containing prevLogIndex and prevLogTerm. "
                "Followers reject entries if their log does not match, enforcing log consistency."
            ),
            sequence_order=2,
            estimated_duration_minutes=15,
            key_concepts=[
                {
                    "term": "prevLogIndex",
                    "explanation": "Index of the log entry immediately preceding new entries sent in AppendEntries RPC.",
                },
                {
                    "term": "Log Truncation",
                    "explanation": "Overwriting uncommitted conflicting follower log entries with authoritative leader entries.",
                },
                {
                    "term": "Commit Index",
                    "explanation": "Highest known log entry index acknowledged by a strict cluster majority.",
                },
            ],
            examples=[
                (
                    "# Consistency verification check\n"
                    "if follower.log[prevLogIndex].term != prevLogTerm:\n"
                    "    return RejectAppendEntries()"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 3: Log Replication",
                    "chunk_index": 1,
                    "citation_text": "The Log Matching Invariant guarantees identical historical entries across matching prefixes.",
                }
            ],
            created_at=now,
        )

        # Lessons for Module 3
        les5_id = str(uuid.uuid4())
        les5 = LearningLesson(
            id=les5_id,
            module_id=mod3_id,
            title="Lesson 3.1: Log Compaction & Snapshotting",
            explanation="Logs cannot grow indefinitely. Raft takes point-in-time state snapshots and discards committed entries.",
            sequence_order=1,
            estimated_duration_minutes=15,
            key_concepts=[
                {
                    "term": "Snapshot Chunking",
                    "explanation": "Dividing massive in-memory snapshots into streamable network chunks.",
                },
                {
                    "term": "InstallSnapshot RPC",
                    "explanation": "Leader RPC sending complete state snapshots to lagging or newly added cluster nodes.",
                },
            ],
            examples=[
                (
                    "# Snapshot creation\n"
                    "snapshot = state_machine.serialize()\n"
                    "log.discard_entries_up_to(last_included_index)"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 4: Log Compaction",
                    "chunk_index": 1,
                    "citation_text": "Snapshots allow servers to discard committed log entries and reclaim storage space.",
                }
            ],
            created_at=now,
        )

        les6_id = str(uuid.uuid4())
        les6 = LearningLesson(
            id=les6_id,
            module_id=mod3_id,
            title="Lesson 3.2: Joint Consensus Configuration Changes",
            explanation="Adding or removing nodes uses joint consensus transitions (C_old + C_new) to prevent dual leaders.",
            sequence_order=2,
            estimated_duration_minutes=15,
            key_concepts=[
                {
                    "term": "Joint Consensus",
                    "explanation": "Configuration transition requiring simultaneous majorities from both old and new configurations.",
                },
                {
                    "term": "Cluster Reconfiguration",
                    "explanation": "Dynamic scaling of nodes without halting client request servicing.",
                },
            ],
            examples=[
                (
                    "# Joint consensus configuration\n"
                    "configuration = {'C_old': [node1, node2, node3], 'C_new': [node1, node2, node3, node4, node5]}"
                )
            ],
            source_references=[
                {
                    "section_title": "Section 5: Cluster Membership Changes",
                    "chunk_index": 1,
                    "citation_text": "Joint consensus prevents split clusters during configuration membership transitions.",
                }
            ],
            created_at=now,
        )

        session.add_all([les1, les2, les3, les4, les5, les6])
        await session.flush()

        # Assessments:
        # 1. Lesson 1.1 Check-for-Understanding Quiz
        quiz1_id = str(uuid.uuid4())
        quiz1 = Assessment(
            id=quiz1_id,
            learning_path_id=path_id,
            module_id=mod1_id,
            lesson_id=les1_id,
            assessment_type="lesson_quiz",
            title="Lesson 1.1 Quiz: Replicated State Machines",
            description="Verify understanding of deterministic state machines and write-ahead log replication.",
            language="en",
            difficulty="intermediate",
            status="completed",
            passing_threshold=70.0,
            created_at=now,
            updated_at=now,
        )
        session.add(quiz1)
        await session.flush()

        q1_1 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=quiz1_id,
            sequence_order=1,
            question_text="What is the primary role of the consensus module in a replicated state machine?",
            question_type="multiple_choice",
            answer_options=[
                "Directly execute business logic transactions.",
                "Ensure that all servers maintain an identical ordered sequence of log entries.",
                "Encrypt incoming network packets from clients.",
                "Manage local disk partitioning.",
            ],
            correct_answer="Ensure that all servers maintain an identical ordered sequence of log entries.",
            explanation="The consensus module's sole responsibility is agreeing upon an identical, deterministic sequence of log entries across all nodes.",
            source_references=[{"section": "Section 1", "chunk": "Chunk 0"}],
            created_at=now,
        )

        q1_2 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=quiz1_id,
            sequence_order=2,
            question_text="Why must the underlying state machine in a consensus system be strictly deterministic?",
            question_type="multiple_choice",
            answer_options=[
                "To optimize CPU cache locality.",
                "To prevent multithreading deadlocks.",
                "Because executing identical input sequences must yield identical final state outputs.",
                "To reduce network bandwidth consumption.",
            ],
            correct_answer="Because executing identical input sequences must yield identical final state outputs.",
            explanation="If state machines were non-deterministic, identical logs would produce divergent states across nodes.",
            source_references=[{"section": "Section 1", "chunk": "Chunk 0"}],
            created_at=now,
        )

        q1_3 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=quiz1_id,
            sequence_order=3,
            question_text="In a 5-node cluster, what is the minimum quorum needed to commit a state transition?",
            question_type="multiple_choice",
            answer_options=["2 nodes", "3 nodes", "4 nodes", "All 5 nodes"],
            correct_answer="3 nodes",
            explanation="A strict majority for N=5 is floor(5/2) + 1 = 3 nodes.",
            source_references=[{"section": "Section 1", "chunk": "Chunk 0"}],
            created_at=now,
        )
        session.add_all([q1_1, q1_2, q1_3])

        # 2. Final Comprehensive Capstone Assessment
        final_exam_id = str(uuid.uuid4())
        final_exam = Assessment(
            id=final_exam_id,
            learning_path_id=path_id,
            module_id=None,
            lesson_id=None,
            assessment_type="final_assessment",
            title="Capstone Certification Exam: Raft Consensus Mastery",
            description="Comprehensive evaluation testing quorum mathematics, election safety invariants, and log replication.",
            language="en",
            difficulty="intermediate",
            status="completed",
            passing_threshold=80.0,
            created_at=now,
            updated_at=now,
        )
        session.add(final_exam)
        await session.flush()

        # 12 Comprehensive Final Exam Questions across all 3 modules & 6 lessons
        fe_q1 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=1,
            question_text="In a replicated state machine architecture, what fundamental requirement must the state machine satisfy to guarantee cluster-wide consistency?",
            question_type="multiple_choice",
            answer_options=[
                "It must execute on identical hardware architectures.",
                "It must be strictly deterministic so that identical input sequences produce identical states.",
                "It must maintain a permanent synchronous connection to an external NTP time server.",
                "It must execute client write commands asynchronously without write-ahead logging.",
            ],
            correct_answer="It must be strictly deterministic so that identical input sequences produce identical states.",
            explanation="Deterministic state machines ensure that when identical log sequences are applied starting from identical initial states, every replica reaches identical final states.",
            source_references=[{"section_title": "1. Core Principles and Node States", "chunk_index": 0, "citation_text": "Time in Raft is partitioned into arbitrary terms... logical clocks"}],
            created_at=now,
        )

        fe_q2 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=2,
            question_text="Which of the following describes the operational responsibility of a follower node in a Raft cluster?",
            question_type="multiple_choice",
            answer_options=[
                "It directly responds to client read and write requests independently.",
                "It initiates periodic election heartbeats to verify candidate liveness.",
                "It remains passive, responding to RPCs from leaders and candidates without initiating communication.",
                "It independently commits entries to disk without awaiting majority consensus.",
            ],
            correct_answer="It remains passive, responding to RPCs from leaders and candidates without initiating communication.",
            explanation="Followers are passive and only respond to incoming RPCs from leaders (AppendEntries) or candidates (RequestVote).",
            source_references=[{"section_title": "1. Core Principles and Node States", "chunk_index": 0, "citation_text": "Follower: Completely passive; responds to remote procedure calls (RPCs)"}],
            created_at=now,
        )

        fe_q3 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=3,
            question_text="For a Raft cluster of N server nodes, what is the minimum quorum required to validate an election or commit a log entry?",
            question_type="multiple_choice",
            answer_options=[
                "A simple plurality of surviving active nodes.",
                "A strict majority calculated as floor(N/2) + 1 nodes.",
                "Two-thirds supermajority (2N/3) of all configured nodes.",
                "Unanimous consent across all N nodes.",
            ],
            correct_answer="A strict majority calculated as floor(N/2) + 1 nodes.",
            explanation="A strict majority of floor(N/2) + 1 ensures that any two quorums must overlap by at least one server, preventing split-brain states.",
            source_references=[{"section_title": "2. Leader Election Protocol", "chunk_index": 0, "citation_text": "A candidate wins the election if it receives affirmative votes from a strict majority (N/2 + 1)"}],
            created_at=now,
        )

        fe_q4 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=4,
            question_text="How many server node failures can a cluster of 5 nodes tolerate while maintaining safe linearizable operation?",
            question_type="multiple_choice",
            answer_options=[
                "1 node failure",
                "2 node failures",
                "3 node failures",
                "4 node failures",
            ],
            correct_answer="2 node failures",
            explanation="A cluster of 2f + 1 nodes tolerates up to f crash failures. For N=5, 2f + 1 = 5 yields f = 2 nodes.",
            source_references=[{"section_title": "5. Architectural Trade-Offs", "chunk_index": 1, "citation_text": "Fault Tolerance: Tolerates up to f failures in a cluster of 2f + 1 nodes."}],
            created_at=now,
        )

        fe_q5 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=5,
            question_text="Why do Raft candidates use randomized election timeouts (e.g. 150ms-300ms)?",
            question_type="multiple_choice",
            answer_options=[
                "To reduce power consumption on battery-powered edge nodes.",
                "To prevent simultaneous candidacy declarations that cause split-vote deadlocks.",
                "To ensure the oldest hardware always wins election.",
                "To benchmark network latency.",
            ],
            correct_answer="To prevent simultaneous candidacy declarations that cause split-vote deadlocks.",
            explanation="Randomized timeouts scatter candidate transitions across time, allowing one candidate to quickly obtain a majority.",
            source_references=[{"section_title": "2. Leader Election Protocol", "chunk_index": 0, "citation_text": "Followers maintain an election timer randomized between 150ms and 300ms to prevent split-vote scenarios."}],
            created_at=now,
        )

        fe_q6 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=6,
            question_text="What is the primary function of monotonic terms in the Raft consensus protocol?",
            question_type="multiple_choice",
            answer_options=[
                "They measure wall-clock latency to benchmark RPC transmission speeds.",
                "They act as logical clocks, enabling nodes to detect and discard stale leaders or obsolete RPCs.",
                "They designate the total number of committed client transactions.",
                "They allocate heap memory buffers for write-ahead log chunks.",
            ],
            correct_answer="They act as logical clocks, enabling nodes to detect and discard stale leaders or obsolete RPCs.",
            explanation="Terms increase monotonically and act as logical clocks. Any node that receives an RPC with a lower term rejects it, and nodes seeing a higher term step down to follower.",
            source_references=[{"section_title": "1. Core Principles and Node States", "chunk_index": 0, "citation_text": "Terms act as a logical clock, allowing nodes to detect obsolete information such as stale leaders."}],
            created_at=now,
        )

        fe_q7 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=7,
            question_text="What invariant ensures that two logs matching in term and index contain identical entries up to that index?",
            question_type="multiple_choice",
            answer_options=[
                "Leader Completeness Invariant",
                "Log Matching Property",
                "State Machine Safety Invariant",
                "Election Safety Rule",
            ],
            correct_answer="Log Matching Property",
            explanation="The Log Matching Property proves that matching term/index guarantees identical preceding log history.",
            source_references=[{"section_title": "4. Safety Invariants & Boundary Conditions", "chunk_index": 1, "citation_text": "Log Matching Property: If two distinct logs contain an entry with the same index and term, they are identical up to that index."}],
            created_at=now,
        )

        fe_q8 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=8,
            question_text="At what point does the Raft leader officially increment its commitIndex for a new log entry?",
            question_type="multiple_choice",
            answer_options=[
                "Immediately when the client sends the HTTP write request.",
                "As soon as the entry is written to the leader's local in-memory log buffer.",
                "Only after a strict majority of follower nodes have acknowledged persisting the entry to disk.",
                "When all cluster nodes, including partitioned nodes, acknowledge receipt.",
            ],
            correct_answer="Only after a strict majority of follower nodes have acknowledged persisting the entry to disk.",
            explanation="The leader increments commitIndex only after majority replication is confirmed, ensuring safety before applying the mutation to the state machine.",
            source_references=[{"section_title": "3. Log Replication & Commit Index", "chunk_index": 1, "citation_text": "When a majority of followers safely persist the entry to disk, the leader increments its commitIndex."}],
            created_at=now,
        )

        fe_q9 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=9,
            question_text="What problem does log compaction (snapshotting) resolve in long-running production Raft systems?",
            question_type="multiple_choice",
            answer_options=[
                "It prevents unconstrained log growth on disk and enables rapid state catch-up for lagging nodes.",
                "It eliminates the need for randomized election timeouts during network partitions.",
                "It allows follower nodes to process client write requests without contacting the leader.",
                "It bypasses quorum requirements for read-only query requests.",
            ],
            correct_answer="It prevents unconstrained log growth on disk and enables rapid state catch-up for lagging nodes.",
            explanation="Without compaction, write-ahead logs would consume unbounded disk space. Snapshots capture accumulated state and allow committed log entries to be discarded.",
            source_references=[{"section_title": "5. Architectural Trade-Offs", "chunk_index": 1, "citation_text": "Fast recovery via follower log synchronization without complex multi-phase consensus reconfiguration."}],
            created_at=now,
        )

        fe_q10 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=10,
            question_text="What does the State Machine Safety invariant guarantee in the Raft protocol?",
            question_type="multiple_choice",
            answer_options=[
                "No server will apply more than one command per second to its state machine.",
                "If a server applies a log entry at a given index, no other server will ever apply a different entry at that index.",
                "State machines automatically recover from unhandled runtime exceptions without restarting.",
                "Followers can apply uncommitted entries speculatively to reduce query latency.",
            ],
            correct_answer="If a server applies a log entry at a given index, no other server will ever apply a different entry at that index.",
            explanation="State Machine Safety ensures linearizability: two state machines can never diverge by executing different commands at the same log index.",
            source_references=[{"section_title": "4. Safety Invariants & Boundary Conditions", "chunk_index": 1, "citation_text": "State Machine Safety: If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index."}],
            created_at=now,
        )

        fe_q11 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=11,
            question_text="Why can directly switching cluster configurations from C_old to C_new without transition phases cause split-brain states?",
            question_type="multiple_choice",
            answer_options=[
                "Network routers do not support dynamic IP address updates.",
                "Two separate leaders could be elected simultaneously—one under C_old majority and one under C_new majority.",
                "Followers will permanently corrupt their local write-ahead log files.",
                "The randomized election timer would reset to zero on all nodes.",
            ],
            correct_answer="Two separate leaders could be elected simultaneously—one under C_old majority and one under C_new majority.",
            explanation="Because different servers switch at different times, two independent majorities could form during uncoordinated reconfiguration. Raft uses joint consensus to prevent this.",
            source_references=[{"section_title": "4. Safety Invariants & Boundary Conditions", "chunk_index": 1, "citation_text": "Election Safety: At most one leader can be elected in a given term."}],
            created_at=now,
        )

        fe_q12 = AssessmentQuestion(
            id=str(uuid.uuid4()),
            assessment_id=final_exam_id,
            sequence_order=12,
            question_text="Under the CAP theorem, how does a Raft cluster behave during an asymmetric network partition that isolates a minority of nodes?",
            question_type="multiple_choice",
            answer_options=[
                "It operates as an AP system, allowing the minority partition to continue accepting client writes.",
                "It operates as a CP system; the minority partition cannot reach quorum and rejects client write commits.",
                "The entire cluster immediately shuts down until network connectivity is fully restored.",
                "The minority nodes automatically elect an authoritative leader that overrides the majority.",
            ],
            correct_answer="It operates as a CP system; the minority partition cannot reach quorum and rejects client write commits.",
            explanation="Raft prioritizes Consistency over Availability under partitions (CP). A minority partition cannot obtain majority acknowledgments (N/2 + 1) and will not commit writes.",
            source_references=[{"section_title": "5. Architectural Trade-Offs", "chunk_index": 1, "citation_text": "Minority partitions cannot commit entries, preserving consistency (CP system under CAP theorem)."}],
            created_at=now,
        )

        session.add_all([fe_q1, fe_q2, fe_q3, fe_q4, fe_q5, fe_q6, fe_q7, fe_q8, fe_q9, fe_q10, fe_q11, fe_q12])
        await session.flush()

        # Lesson Progress Records
        lp1 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les1_id,
            status="completed",
            started_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        lp2 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les2_id,
            status="completed",
            started_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        lp3 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les3_id,
            status="completed",
            started_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        lp4 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les4_id,
            status="in_progress",
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        lp5 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les5_id,
            status="not_started",
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        lp6 = LessonProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            lesson_id=les6_id,
            status="not_started",
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add_all([lp1, lp2, lp3, lp4, lp5, lp6])

        # Assessment Attempts:
        # Attempt 1: 100% on Lesson 1 Quiz
        att1_id = str(uuid.uuid4())
        att1 = AssessmentAttempt(
            id=att1_id,
            assessment_id=quiz1_id,
            status="completed",
            score=3,
            max_score=3,
            percentage=100.0,
            passed=True,
            started_at=now,
            completed_at=now,
            created_at=now,
        )
        session.add(att1)
        await session.flush()

        ans1_1 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att1_id,
            question_id=q1_1.id,
            selected_answer="Ensure that all servers maintain an identical ordered sequence of log entries.",
            is_correct=True,
            feedback="Correct. The consensus module orders and replicates log inputs.",
            created_at=now,
        )
        ans1_2 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att1_id,
            question_id=q1_2.id,
            selected_answer="Because executing identical input sequences must yield identical final state outputs.",
            is_correct=True,
            feedback="Correct. Determinism guarantees safety across all state machine replicas.",
            created_at=now,
        )
        ans1_3 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att1_id,
            question_id=q1_3.id,
            selected_answer="3 nodes",
            is_correct=True,
            feedback="Correct. (5/2) + 1 = 3.",
            created_at=now,
        )
        session.add_all([ans1_1, ans1_2, ans1_3])

        # Attempt 2: 91.7% on Final Exam (11/12 Correct Answers)
        att2_id = str(uuid.uuid4())
        att2 = AssessmentAttempt(
            id=att2_id,
            assessment_id=final_exam_id,
            status="completed",
            score=11,
            max_score=12,
            percentage=91.7,
            passed=True,
            started_at=now,
            completed_at=now,
            created_at=now,
        )
        session.add(att2)
        await session.flush()

        fe_ans1 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q1.id,
            selected_answer="It must be strictly deterministic so that identical input sequences produce identical states.",
            is_correct=True,
            feedback="Correct. Determinism guarantees safety across all state machine replicas.",
            created_at=now,
        )
        fe_ans2 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q2.id,
            selected_answer="It remains passive, responding to RPCs from leaders and candidates without initiating communication.",
            is_correct=True,
            feedback="Correct. Followers only respond to incoming RPCs without initiating requests.",
            created_at=now,
        )
        fe_ans3 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q3.id,
            selected_answer="A strict majority calculated as floor(N/2) + 1 nodes.",
            is_correct=True,
            feedback="Correct. A majority of floor(N/2) + 1 prevents split-brain majorities.",
            created_at=now,
        )
        fe_ans4 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q4.id,
            selected_answer="2 node failures",
            is_correct=True,
            feedback="Correct. 2f + 1 = 5, so f = 2 nodes.",
            created_at=now,
        )
        fe_ans5 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q5.id,
            selected_answer="To prevent simultaneous candidacy declarations that cause split-vote deadlocks.",
            is_correct=True,
            feedback="Correct. Randomized timers scatter candidate transitions.",
            created_at=now,
        )
        fe_ans6 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q6.id,
            selected_answer="They act as logical clocks, enabling nodes to detect and discard stale leaders or obsolete RPCs.",
            is_correct=True,
            feedback="Correct. Terms provide logical clocks to detect stale servers.",
            created_at=now,
        )
        fe_ans7 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q7.id,
            selected_answer="Log Matching Property",
            is_correct=True,
            feedback="Correct. Log Matching Property proves matching prefix history.",
            created_at=now,
        )
        fe_ans8 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q8.id,
            selected_answer="Only after a strict majority of follower nodes have acknowledged persisting the entry to disk.",
            is_correct=True,
            feedback="Correct. The leader only increments commitIndex upon majority acknowledgment.",
            created_at=now,
        )
        fe_ans9 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q9.id,
            selected_answer="It prevents unconstrained log growth on disk and enables rapid state catch-up for lagging nodes.",
            is_correct=True,
            feedback="Correct. Snapshots compact logs and reclaim disk space.",
            created_at=now,
        )
        fe_ans10 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q10.id,
            selected_answer="No server will apply more than one command per second to its state machine.",
            is_correct=False,
            feedback="Incorrect. State Machine Safety guarantees that if a server applies an entry at a given index, no other server will ever apply a different entry at that index.",
            created_at=now,
        )
        fe_ans11 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q11.id,
            selected_answer="Two separate leaders could be elected simultaneously—one under C_old majority and one under C_new majority.",
            is_correct=True,
            feedback="Correct. Joint consensus prevents split-brain majorities during reconfigurations.",
            created_at=now,
        )
        fe_ans12 = AssessmentAnswer(
            id=str(uuid.uuid4()),
            attempt_id=att2_id,
            question_id=fe_q12.id,
            selected_answer="It operates as a CP system; the minority partition cannot reach quorum and rejects client write commits.",
            is_correct=True,
            feedback="Correct. Raft is a CP system prioritizing consistency under network partitions.",
            created_at=now,
        )
        session.add_all([
            fe_ans1, fe_ans2, fe_ans3, fe_ans4, fe_ans5, fe_ans6,
            fe_ans7, fe_ans8, fe_ans9, fe_ans10, fe_ans11, fe_ans12
        ])

        # PathProgress Session Continuity Pointer
        path_progress = PathProgress(
            id=str(uuid.uuid4()),
            learning_path_id=path_id,
            last_visited_lesson_id=les4_id,
            last_accessed_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(path_progress)

        await session.commit()

    await engine.dispose()
    print("Demo environment successfully prepared and seeded!")
    print(f"Isolated Database: {DEMO_DB_PATH.resolve()}")
    print(f"Isolated Storage:  {DEMO_STORAGE_DIR.resolve()}")


def main():
    print("Step 1: Setting up isolated demo storage directories...")
    init_demo_storage()

    print("Step 2: Initializing schema and seeding realistic synthetic demo data...")
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
