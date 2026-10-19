# TechSift AI — Portfolio Demo Video Script

**Target Audience**: Technical Recruiters, Engineering Hiring Managers, AI Tech Leads  
**Target Duration**: 2 minutes 45 seconds  
**Voiceover Tone**: Confident, articulate, engineering-focused, structured  
**Presenter Setup**: 1080p 60fps screen recording, clean browser window (dark mode), high-quality microphone.

---

## 1. Video Timeline & Script

| Timestamp | Visual Action | Spoken Narration (English) | On-Screen Captions / Callouts |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:25** | Screen shows terminal starting FastAPI (`uvicorn src.api.main:app`) and Vite frontend (`npm run dev`), then transitions cleanly into browser dashboard at `localhost:5173`. Mouse hovers over real-time aggregate metric cards. | *"Hi! I'm showcasing **TechSift AI**, an end-to-end technical document intelligence and interactive learning platform built with FastAPI, React 19, SQLite, and Google Gemini. The system transforms dense architectural whitepapers and RFCs into structured summaries, studio-grade audio narration, multi-speaker podcasts, and source-grounded learning curricula—using a local-first architecture and free-tier AI services."* | **TechSift AI**<br>• FastAPI + React 19 + TypeScript<br>• SQLite with Async SQLAlchemy 2.0<br>• Local-first architecture with free-tier AI |
| **0:25 – 0:55** | Navigate to `/documents`. Drag and drop `samples/distributed_consensus_raft_architecture.md` into the ingestion dropzone. Show real-time extraction and transition into `/workspace/:id`. Reveal executive summary and taxonomy (pre-rendered for zero-latency demonstration). | *"Let's ingest an architectural whitepaper on Raft Distributed Consensus. The backend extracts content, executes sliding-window chunking, and leverages Google Gemini (configured with gemini-3.8-flash and automatic fallback). Here we see the generated executive overview, prioritized architectural takeaways, and a domain glossary with strict Pydantic JSON schema validation."* | **Multi-Format Ingestion**<br>• Markdown, PDF, Plain Text<br>• Sliding-window text chunking<br>• Structured Pydantic JSON validation |
| **0:55 – 1:30** | Switch to the "Audio Studio" tab. Toggle language to Arabic (showing clean RTL transition). Play generated Arabic narration clip with waveform scrubber. Switch to "Educational Podcast" tab and play multi-speaker technical dialogue. | *"Next is the Audio Studio. Built on an asynchronous Edge-TTS pipeline, it produces bilingual speech with zero external billing. Here's our native Arabic narration with full right-to-left layout alignment. Beyond single narration, TechSift generates multi-speaker educational podcasts—synthesizing a natural dialogue between two technical hosts, stitched seamlessly with local FFmpeg."* | **Audio Studio & Podcasts**<br>• Microsoft Edge TTS (Free Tier)<br>• Native English & Arabic RTL<br>• Multi-speaker audio stitched via FFmpeg |
| **1:30 – 2:10** | Click on "Learning Studio" tab. Show generated 3-module curriculum. Click on "Module 1" $\to$ "Start Lesson 1 Quiz". Answer questions, demonstrating instant feedback and verifiable source citations. | *"In the Interactive Learning Studio, TechSift decomposes the whitepaper into structured modules and lessons. Every lesson features an interactive quiz generated from the text. Grading is completely deterministic and runs locally in SQLite without external LLM calls. Each answer provides instant pedagogical rationale grounded in exact source sections to minimize hallucination risks."* | **Interactive Learning Studio**<br>• Pedagogical Curriculum Generation<br>• Local deterministic grading engine<br>• Verifiable source citations |
| **2:10 – 2:35** | Click "Finish Quiz" and navigate to "Progress Dashboard" tab. Show animated completion percentage bar, assessment score averages, module mastery tiers, and attempt history table. | *"All learning activity feeds into the Learning Progress Dashboard. It computes real-time curriculum completion, assessment averages, and module mastery breakdown. Everything is persisted locally in SQLite with SQLAlchemy 2.0 async transactions and managed through Alembic migrations."* | **Progress & Mastery Dashboard**<br>• Real-time progress aggregation<br>• Attempt history & score distribution<br>• SQLite 3.35+ Async Persistence |
| **2:35 – 2:45** | Return to Dashboard showing refreshed aggregate stats, toggle Light Mode briefly to show theme support, then show terminal running pytest (`107 passed`). Display closing slide with portfolio links. | *"TechSift AI demonstrates production full-stack engineering, clean asynchronous Python design, robust frontend state management, and practical AI systems design. Thank you for watching!"* | **107 Unit & Integration Tests Passing**<br>• Python 3.12 • FastAPI • React 19<br>• Portfolio Showcase Edition |

---

## 2. Recording Tips & Best Practices

1. **Resolution & Scaling**: Record at native 1080p with browser zoom set to 100% or 110% for optimal text legibility.
2. **Audio Setup**: Use a directional cardioid microphone with noise suppression (e.g. OBS Noise Gate).
3. **Pacing**: Move mouse smoothly; pause 1-2 seconds after opening a new modal or tab before clicking.
4. **Pre-Generated Demo State**: For a smooth 2-minute video without API latency, pre-generate summaries and audio in the isolated demo database (`demo_techsift.db`) prior to recording, clearly explaining during narration that complex outputs were generated via the identical pipeline.
