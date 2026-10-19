# TechSift AI — Project Roadmap & Task Breakdown

This document tracks all implementation phases, milestones, acceptance criteria, and task statuses for **TechSift AI**.

---

## Phase 0: Feasibility Validation (COMPLETED ✅)
*Goal: Prove technical viability in an isolated environment with zero cost.*

* [x] **Task 0.1**: Inspect development environment (Python 3.12, Node v22, Git).
* [x] **Task 0.2**: Create virtual environment (`.venv`) and install baseline dependencies.
* [x] **Task 0.3**: Test 1 — Google Gemini API feasibility:
  * [x] Install official `google-genai` SDK.
  * [x] Document official Google AI Studio free-tier quotas and free models (`gemini-3.8-flash`).
  * [x] Implement secure API key loading mechanism via `.env`.
  * [x] Build safe validation script (`scripts/test_gemini.py`) with zero secret leakage.
* [x] **Task 0.4**: Test 2 — Document processing:
  * [x] Install `pypdf` and `reportlab`.
  * [x] Generate sample technical PDF locally (`storage/test/sample_technical_doc.pdf`).
  * [x] Extract text and verify content with automated assertions.
  * [x] Implement and test sliding-window overlapping chunking.
* [x] **Task 0.5**: Test 3 — Text-to-Speech:
  * [x] Test `edge-tts` over WebSocket.
  * [x] Diagnose 403 handshake error (Microsoft regional edge node restriction).
  * [x] Implement and verify offline local fallback (`pyttsx3` / OS native) generating valid audio.
* [x] **Task 0.6**: Test 4 — FastAPI backend:
  * [x] Implement minimal app with `GET /health`.
  * [x] Test live server HTTP request and verify 200 OK + JSON response.
* [x] **Task 0.7**: Test 5 — Frontend toolchain:
  * [x] Scaffold React 19 + TypeScript + Vite project in `frontend/`.
  * [x] Install dependencies and verify production build (`npm run build`).
* [x] **Task 0.8**: Deliverables & documentation:
  * [x] Create `FEASIBILITY_REPORT.md`
  * [x] Create `PROJECT_SPEC.md`
  * [x] Create `AGENTS.md`
  * [x] Create `TASKS.md`
  * [x] Create `requirements.txt`
  * [x] Create `.env.example`
  * [x] Create `.gitignore`
  * [x] Verify automated pytest test suite (`tests/`).

---

## Phase 1: Core Backend & Data Persistence (COMPLETED ✅)
*Goal: Build asynchronous SQLite database layer, storage management, and core FastAPI structure.*

* [x] **Task 1.1**: Set up layered service architecture (`src/core`, `src/db`, `src/models`, `src/repositories`, `src/schemas`, `src/services`, `src/api`).
* [x] **Task 1.2**: Implement SQLite async connection with SQLAlchemy 2.0 and aiosqlite.
* [x] **Task 1.3**: Configure and run Alembic migrations (`alembic/versions/4acccbc0737c_create_documents_and_processing_jobs.py`).
* [x] **Task 1.4**: Define database models (`Document`, `ProcessingJob`) with cascade deletes and constraints.
* [x] **Task 1.5**: Implement repository pattern (`DocumentRepository`, `JobRepository`) with pagination.
* [x] **Task 1.6**: Implement secure local storage service (`StorageService`) with path traversal protection and automatic disk cleanup.
* [x] **Task 1.7**: Implement text extraction service (`TextExtractorService`) supporting PDF, TXT, and Markdown with scanned PDF detection.
* [x] **Task 1.8**: Implement REST API endpoints (`GET /api/v1/health`, `POST /api/v1/documents`, `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`).
* [x] **Task 1.9**: Implement global error handlers, custom exception hierarchy, and Pydantic schemas.
* [x] **Task 1.10**: Author and verify automated pytest integration test suite with isolated databases (21 tests passing).

---

## Phase 2: Ingestion & AI Summarization Pipeline (COMPLETED ✅)
*Goal: Implement bilingual document parsing, chunking, and free-tier Gemini summarization engine.*

* [x] **Task 2.1**: Implement modular `TextExtractor` supporting PDF (page-aware `pypdf`), Markdown, and plain text with scanned PDF detection.
* [x] **Task 2.2**: Implement production `ChunkerService` with page-aware chunking, Markdown heading preservation, and configurable character windowing and overlap.
* [x] **Task 2.3**: Build abstract `AIProvider` base class and `GeminiProvider` implementation using verified free-tier `gemini-3.8-flash` with in-memory token bucket rate limiting (10 RPM limit to protect 15 RPM free tier).
* [x] **Task 2.4**: Implement structured prompt engineering and Pydantic schemas (`TechnicalSummaryContent`, `ConceptItem`) enforcing:
  * Executive Summary
  * Main Concepts with inter-relationships
  * Key Findings and Takeaways
  * Architecture Overview and Practical Applications
  * Limitations and Trade-offs
  * Source Page and Chunk Citations
* [x] **Task 2.5**: Implement bilingual summarization logic supporting English and Modern Standard Arabic (`en->ar`, `ar->en`, `en->en`, `ar->ar`) with strict preservation of English technical terms, identifiers, and acronyms in Arabic summaries.
* [x] **Task 2.6**: Implement Map-Reduce summarization strategy for long documents exceeding 14,000 characters.
* [x] **Task 2.7**: Implement zero-cost SQLite caching tier: returns existing completed summaries for identical `(document_id, language, detail_level, model_used)` with `is_cached=True` and 0 LLM API calls.
* [x] **Task 2.8**: Implement database models (`DocumentChunk`, `Summary`) and Alembic migration `abdc5e85ecbe`.
* [x] **Task 2.9**: Implement REST API endpoints:
  * `POST /api/v1/documents/{id}/summaries` (supports `language`, `detail_level`, `wait`)
  * `GET /api/v1/documents/{id}/summaries`
  * `GET /api/v1/summaries/{id}`
* [x] **Task 2.10**: Write comprehensive automated pytest test suite (`tests/test_summary_api.py`) with mocked AI provider (11 tests covering all translations, detail levels, caching hits/misses, and edge cases; 34 total test suite passing).
* [x] **Task 2.11**: Perform real integration verification (`scripts/test_gemini_summarization.py`) with strictly 1 live request to `gemini-3.8-flash` verifying end-to-end English -> Arabic summarization and Pydantic schema validation.


---

## Phase 3: Professional Frontend & Document Workspace (COMPLETED ✅)
*Goal: Build modern, developer-centric technical document learning dashboard and bilingual workspace.*

* [x] **Task 3.1**: Design System & Aesthetics: React 19, TypeScript, Tailwind CSS v4, Lucide React icons, dark/light theme toggle.
* [x] **Task 3.2**: Bilingual Interface & RTL: Static translation dictionaries in English (LTR) and Modern Standard Arabic (RTL) with dynamic `dir="rtl"` and font switching.
* [x] **Task 3.3**: Centralized Typed API Client: Created `src/services/api.ts` with timeout handling, progress reporting, and TanStack Query integration.
* [x] **Task 3.4**: Dashboard: Real document ingestion metrics, processing status counts, Knowledge Journey workflow banner, and quick ingestion dropzone.
* [x] **Task 3.5**: Document Library: Drag-and-drop upload zone with validation (.pdf, .txt, .md, max 15MB), search by filename, status filter, pagination, and safe deletion modal.
* [x] **Task 3.6**: Document Workspace:
  * Document metadata inspection header
  * Bilingual summarization controls (Arabic / English output)
  * Detail level selector (Short, Standard, Detailed)
  * Structured summary viewer (Executive summary, Core concepts & taxonomy with relationships, Key findings, Architecture overview, Practical applications, Limitations & trade-offs, Takeaways)
  * Grounded source citations (Referenced page numbers & chunk indices, citation disclaimer)
  * Previous summaries history dropdown
  * Extracted plain text viewer tab
  * SQLite cache origin badge (`is_cached: true` vs newly generated)
* [x] **Task 3.7**: Knowledge Journey: Visual workflow stepper (Understand active, Listen / Practice / Master visibly labeled Coming Soon).
* [x] **Task 3.8**: Settings: UI language switcher, Theme toggle, Default summary language preference, Default detail level preference, and Live backend health diagnostics ping.
* [x] **Task 3.9**: Testing & Build: Verified `npm run build` (364ms production build) and `npm run lint` passing.

---

## Phase 4: Audio & Podcast Studio Subsystem (COMPLETED ✅)
*Goal: Implement zero-cost bilingual audio narration, educational dual-speaker podcasts, HTTP 206 streaming, and React Audio Studio.*

### Phase 4A: Audio Feasibility & Quality Validation (COMPLETED ✅)
* [x] **Task 4A.1**: Verified zero-cost speech synthesis ecosystem (`edge-tts` and local offline `piper-tts`).
* [x] **Task 4A.2**: Evaluated and validated Arabic and English neural voices (`ar-EG-ShakirNeural`, `ar-EG-SalmaNeural`, `en-US-GuyNeural`, `en-US-JennyNeural`).
* [x] **Task 4A.3**: Generated offline audio test samples for pronunciation, pause pacing, and two-speaker audio stitching.
* [x] **Task 4A.4**: Authored `AUDIO_FEASIBILITY_REPORT.md` documenting verified voices, zero-cost architecture, and recommendations.

### Phase 4B: Audio & Podcast Studio Implementation (COMPLETED ✅)
* [x] **Task 4B.1**: Database & Persistence: Created `AudioTrack` SQLAlchemy model, relationship on `Document`, and Alembic migration `6b09d70617e4_create_audio_tracks_table.py`.
* [x] **Task 4B.2**: Pydantic V2 Schemas: Implemented `CreateAudioRequest`, `AudioTrackResponse`, `PodcastScript`, `PodcastTurn`, `AudioTrackListResponse`, and `VoiceCatalogResponse`.
* [x] **Task 4B.3**: Repositories & Audio Service: Implemented `AudioRepository` and `AudioService` with SHA-256 fingerprint caching and SQLite `ProcessingJob` tracking.
* [x] **Task 4B.4**: Core Speech & Dialogue Engines:
  * Abstract `AudioProvider` with `EdgeTTSProvider` and offline `PiperTTSProvider`.
  * `PodcastGenerator`: Grounded dual-speaker educational dialogue engine via Gemini AI provider with structured JSON schema output.
  * `AudioStitchingService`: MP3 concatenation using `pydub` and `ffmpeg` with 450ms conversational pauses between turns.
* [x] **Task 4B.5**: FastAPI Audio Endpoints:
  * `POST /api/v1/documents/{document_id}/audio`: Trigger narration or podcast generation (sync `wait=true` or background async).
  * `GET /api/v1/documents/{document_id}/audio`: List all audio tracks for document.
  * `GET /api/v1/audio/{audio_id}`: Track metadata and status inspection.
  * `GET /api/v1/audio/{audio_id}/stream`: RFC 7233 HTTP 206 Partial Content byte-range streaming for seeking and scrubbing.
  * `GET /api/v1/audio/{audio_id}/download`: Attachment file download with sanitized filename headers.
  * `GET /api/v1/audio/voices`: Available voice catalog.
* [x] **Task 4B.6**: Automated Test Suite: Created comprehensive unit and integration tests in `tests/test_audio_api.py` (13 tests passing, 52/52 total tests passing 100% offline).
* [x] **Task 4B.7**: Frontend Audio Studio:
  * Built typed API client methods in `frontend/src/services/api.ts` and types in `frontend/src/types/api.ts`.
  * Built custom HTML5 `<AudioPlayer />` with streaming, play/pause, time scrubber, speed rates (0.75x–2x), volume/mute, and MP3 download.
  * Built `<AudioStudio />` with Mode toggle (Narration vs Podcast), Language selector (AR/EN), voice config, generation controls, dialogue transcript viewer with speaker badges, and audio history.
  * Integrated studio seamlessly into `WorkspacePage.tsx` with top mode switcher tabs and RTL/LTR and Dark/Light support.
  * Verified `npm run build && npm run lint` passing with zero errors.

---

## Phase 4C: Stability & Security Hardening (COMPLETED ✅)
*Goal: Harden deletion atomicity and background task crash recovery.*

* [x] **Task 4C.1**: Audio Deletion Atomicity: Implemented reversible file staging in `DocumentService.delete_document()` preventing orphaned disk files or database desynchronization upon deletion failures.
* [x] **Task 4C.2**: Startup Job Reconciliation: Implemented single-process crash recovery (`reconcile_interrupted_jobs()`) executed on FastAPI startup to reconcile interrupted in-flight jobs.
* [x] **Task 4C.3**: Regression Tests: Authored 14 regression tests in `tests/test_document_api.py` and `tests/test_job_recovery.py` (66/66 total tests passing).

---

## Phase 5: Interactive Learning Studio Subsystem (COMPLETED ✅)
*Goal: Transform technical documents into structured learning paths, quizzes, and mastery tracking.*

### Phase 5A: Learning Path Foundation (COMPLETED ✅)
* [x] **Task 5A.1**: Database Models: Created `LearningPath`, `LearningModule`, `LearningLesson` models and Alembic migration `32d2f5140837`.
* [x] **Task 5A.2**: AI Curriculum Generator: Built Gemini curriculum generation engine with tiered difficulty (Beginner, Intermediate, Advanced) and source grounding citations.
* [x] **Task 5A.3**: REST API Endpoints: `POST /api/v1/documents/{id}/learning-paths`, `GET /api/v1/documents/{id}/learning-paths`, `GET /api/v1/learning-paths/{id}`.
* [x] **Task 5A.4**: Frontend Learning Studio: Built `<LearningStudio />` with accordion navigation, code snippet blocks, and source citations.
* [x] **Task 5A.5**: Test Suite: Authored 10 integration tests in `tests/test_learning_path_api.py` (76/76 total tests passing).

### Phase 5B: Interactive Quizzes & Assessments (COMPLETED ✅)
* [x] **Task 5B.1**: Database Models: Created `Assessment`, `AssessmentQuestion`, `AssessmentAnswer`, `AssessmentAttempt` models and Alembic migration `b7203b47c6e9`.
* [x] **Task 5B.2**: Tiered Assessment Generation: Built lesson quizzes, module assessments, and capstone final exams via Gemini.
* [x] **Task 5B.3**: Deterministic Local Grading Engine: Local evaluation in SQLite with score computation, threshold checks, and pedagogical feedback without LLM API calls.
* [x] **Task 5B.4**: Frontend Assessment Modal: Built `<AssessmentModal />` with interactive question answering, instant grading review, and retake controls.
* [x] **Task 5B.5**: Test Suite: Authored 8 integration tests in `tests/test_assessment_api.py` (84/84 total tests passing).

### Phase 5C: Learning Progress & Dashboard (COMPLETED ✅)
* [x] **Task 5C.1**: Database Models: Created `LessonProgress` (state machine) and `PathProgress` (session continuity) models and Alembic migration `ffc42a801e14`.
* [x] **Task 5C.2**: Progress Service & Regression Protection: Implemented status transitions (`not_started`, `in_progress`, `completed`) with completed-state protection and dynamic metric calculation.
* [x] **Task 5C.3**: Deterministic Knowledge Mastery: Built evaluation engine identifying Strong Concepts ($\ge 80\%$), Concepts Needing Review ($< 70\%$), and Frequently Missed Questions ($\ge 50\%$) with zero LLM API calls.
* [x] **Task 5C.4**: Explainable Recommendations: Built prioritized rule-based pedagogical recommendation engine.
* [x] **Task 5C.5**: Frontend Dashboard & View Switcher: Built `<LearningDashboard />` with KPI cards, module progress bars, mastery cards, and unified studio tab navigation.
* [x] **Task 5C.6**: Test Suite: Authored 8 integration tests in `tests/test_learning_progress_api.py` (103/103 total tests passing).

---

## Phase 6: Portfolio Readiness & Release Hardening (COMPLETED ✅)
*Goal: Prepare TechSift AI for professional private portfolio presentation and future commercial evolution.*

### Phase 6A: Portfolio Readiness Audit (COMPLETED ✅)
* [x] **Task 6A.1**: Performed read-only audit across 10 engineering dimensions (backend, frontend, security, secrets, git hygiene, licensing, tests).
* [x] **Task 6A.2**: Identified missing `pydub` dependency and unannounced `ffmpeg` requirement.
* [x] **Task 6A.3**: Formulated prioritized remediation plan.

### Phase 6B: GitHub Release Hardening (COMPLETED ✅)
* [x] **Task 6B.1**: Fixed `requirements.txt`: Added `pydub>=0.25.1` and verified clean Python 3.12 install.
* [x] **Task 6B.2**: System Prerequisites: Documented `ffmpeg`/`ffprobe` in `README.md` for macOS, Ubuntu/Debian, and Windows.
* [x] **Task 6B.3**: Startup Pre-Flight Checks: Added `ffmpeg`/`ffprobe` detection in FastAPI `lifespan` and pre-flight `AudioDependencyError` check in audio stitching service.
* [x] **Task 6B.4**: Authored Demo Documents: Created 3 synthetic safe technical documents in `samples/` (`.md`, `.txt`, `.pdf`) and `samples/README.md`.
* [x] **Task 6B.5**: Automated Test Coverage: Added regression test `test_missing_ffmpeg_raises_dependency_error` (104/104 tests passing).

### Phase 6C: Private Portfolio & Documentation (COMPLETED ✅)
* [x] **Task 6C.1**: Proprietary Licensing Policy: Affirmed proprietary status (exclusive source code rights retained, no open-source license, no public repository).
* [x] **Task 6C.2**: Copyright Notice: Embedded prominent `Copyright (c) 2026. All rights reserved.` notice in `README.md`.
* [x] **Task 6C.3**: Comprehensive `README.md`: Documented full architecture, technology stack, setup guide, and complete REST API catalog.
* [ ] **Task 6C.5**: Dependency Licensing & Legal Review: Preliminary audit recorded; unverified pending formal inventory of all direct and transitive third-party package licenses and commercial service terms.

### Phase 6D: Final Portfolio Review & Demo Preparation (COMPLETED ✅)
* [x] **Task 6D.1**: 16-Domain Review: Conducted full-stack inspection across all 16 application areas.
* [x] **Task 6D.2**: Dashboard Metrics & Aggregates Fix: Implemented backend endpoint `GET /api/v1/documents/stats` computing document totals, status breakdown, issues count (failed + unsupported), and completed summaries independently of pagination. Configured Recent Documents table to fetch strictly top 5 records. Added query invalidation on upload, deletion, and summary creation.
* [x] **Task 6D.3**: Portfolio Screenshot Plan: Authored `docs/portfolio/SCREENSHOT_PLAN.md` covering 9 high-impact screenshots with exact viewports, themes, routes, data masking guidelines, and existing sample filenames.
* [x] **Task 6D.4**: Demo Video Script: Authored `docs/portfolio/DEMO_VIDEO_SCRIPT.md` with complete 2m45s timeline, screen actions, English narration, recruiter-focused callouts, and distinction between live triggers vs pre-rendered outputs.
* [x] **Task 6D.5**: Demo Preparation Checklist: Created `docs/portfolio/DEMO_CHECKLIST.md` with presence-only API key check, correct `src.api.main:app` import, isolated demo DB instructions (`demo_techsift.db`), and zero-latency recording strategies.
* [x] **Task 6D.6**: Final Verification: Executed full test suite (107/107 passing with regression coverage for >50 documents, empty library, and zero summaries), verified 0 lint errors, 0 Vite build errors, 0 Alembic migration drift, and git hygiene.

---

## Phase 7: Commercial SaaS Production Roadmap (PLANNED ⏳)
*Goal: Scale from local-first prototype to distributed, multi-tenant commercial cloud SaaS.*

* [ ] **Task 7.1**: **Multi-Tenant Data Tier**:
  * Migrate from SQLite to managed PostgreSQL (AWS RDS / Neon) with connection pooling (`pgbouncer`).
  * Implement tenant isolation (schema-per-tenant or row-level security `tenant_id`).
* [ ] **Task 7.2**: **Cloud Object Storage**:
  * Replace local filesystem storage (`./storage`) with AWS S3 / Cloudflare R2 using presigned upload/download URLs.
* [ ] **Task 7.3**: **Distributed Background Job Workers**:
  * Replace in-process `BackgroundTasks` with distributed Celery or Temporal workers backed by Redis.
* [ ] **Task 7.4**: **Enterprise User Authentication & RBAC**:
  * Integrate Clerk / Auth0 for organization accounts, team workspaces, and role-based permissions (Admin, Editor, Learner).
* [ ] **Task 7.5**: **Commercial Speech Synthesis Tier**:
  * Implement enterprise TTS adapters (Google Cloud Text-to-Speech / Azure Cognitive Services) with commercial SLAs to replace consumer Edge speech endpoints.
* [ ] **Task 7.6**: **Billing & Quota Management**:
  * Integrate Stripe for subscription billing, metered token usage, and automated tier upgrades.

