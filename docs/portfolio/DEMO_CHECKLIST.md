# TechSift AI — Reusable Demo Preparation Checklist

Use this checklist prior to recording a portfolio demo video or conducting a live technical interview walkthrough.

---

## 1. System & Environment Verification

- [ ] **Python Version**: Verify Python 3.12 is active:
  ```bash
  python3 --version
  ```
- [ ] **Virtual Environment**: Ensure dependencies are installed:
  ```bash
  source .venv/bin/activate
  pip list | grep -E "fastapi|google-genai|edge-tts|pydub|sqlalchemy"
  ```
- [ ] **System Audio Tools**: Confirm FFmpeg and FFprobe are accessible in `$PATH`:
  ```bash
  ffmpeg -version
  ffprobe -version
  ```
- [ ] **Frontend Dependencies**: Ensure Node modules are installed and built (requires Node.js 20.19+ or 22+):
  ```bash
  cd frontend && npm run build && cd ..
  ```
- [ ] **API Keys (Presence Check Only — Never Print Secret Values)**:
  ```bash
  test -n "${GEMINI_API_KEY}" && echo "GEMINI_API_KEY is set in environment" || (grep -q "^GEMINI_API_KEY=..*" .env 2>/dev/null && echo "GEMINI_API_KEY is configured in .env" || echo "WARNING: GEMINI_API_KEY not configured")
  ```

---

## 2. Safe Demo Asset Verification

- [ ] Inspect the original synthetic sample documents in `samples/`:
  - `samples/distributed_consensus_raft_architecture.md` (Markdown format, ~5 KB)
  - `samples/event_driven_microservices_architecture.txt` (Plain text format, ~6 KB)
  - `samples/distributed_caching_and_consistency.pdf` (Synthetic PDF format, ~5 KB)
- [ ] **Crucial Rule**: Verify NO private, copyrighted, or confidential documents are loaded into the demo library.

---

## 3. Isolated Demo Database & Cache Setup

To protect user documents and production data from being modified or overwritten, **never** wipe `techsift.db` or `./storage`. Always run demos in an isolated environment:

### Setting Up an Isolated Demo Environment
```bash
# 1. Point to dedicated demo database and demo storage directory
export DATABASE_URL="sqlite+aiosqlite:///./demo_techsift.db"
export STORAGE_DIR="./demo_storage"

# 2. Run migrations to initialize the clean demo schema
alembic upgrade head
```

### Choosing Demo Execution Strategy:

#### Option A: Live Generation Showcase
* Demonstrates real-time ingestion, sliding-window chunking, Gemini API summarization, and Edge-TTS audio generation on camera.
* *Note*: Subject to external Gemini free-tier rate limits and latency (~15–30 seconds for complete generation).

#### Option B: Pre-Generated Zero-Latency Walkthrough (Recommended for 2-Minute Videos)
* Pre-load `samples/distributed_consensus_raft_architecture.md` into `demo_techsift.db` and generate summary, audio, podcast, and learning path *before* recording.
* During the video, clicking into the workspace reveals pre-generated outputs instantly, ensuring snappy pacing while clearly explaining that outputs are pre-rendered artifacts from the same pipeline.

---

## 4. Services Startup Procedure

1. **Terminal 1 (Backend)**:
   ```bash
   source .venv/bin/activate
   export DATABASE_URL="sqlite+aiosqlite:///./demo_techsift.db"
   export STORAGE_DIR="./demo_storage"
   uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *Assert*: Confirms `Startup audio dependency check passed (ffmpeg and ffprobe found)`.

2. **Terminal 2 (Frontend)**:
   ```bash
   cd frontend
   npm run dev
   ```
   *Assert*: Vite dev server starts at `http://localhost:5173`.

3. **Browser Setup**:
   - Open Chrome or Brave at `http://localhost:5173`.
   - Set viewport to 100% zoom, 1920×1080 resolution.
   - Set Dark Mode as the initial theme.

---

## 5. Walkthrough Rehearsal Steps

- [ ] **Step 1: Dashboard (`/`)**: Show live aggregate metrics (Total Docs, Ready, Summaries, Issues).
- [ ] **Step 2: Library (`/documents`)**: Drop `samples/distributed_consensus_raft_architecture.md` into dropzone.
- [ ] **Step 3: Workspace (`/workspace/:id`)**:
  - Show extracted text and document metadata.
  - Review Executive Summary, Key Takeaways, and Glossary.
- [ ] **Step 4: Audio Studio**:
  - Play English narration clip.
  - Switch language to Arabic (RTL) and play sample.
  - Switch to Podcast tab and preview multi-speaker dialogue.
- [ ] **Step 5: Learning Studio**:
  - Open Module 1, start a lesson quiz.
  - Select correct answer, review source citation and pedagogical rationale.
  - Submit quiz to register attempt.
- [ ] **Step 6: Progress Dashboard**:
  - Review updated progress bars, mastery tier, and attempt history table.
- [ ] **Step 7: Code Quality**:
  - Show clean test run: `.venv/bin/pytest tests/ -q` (107 passed).

---

## 6. Post-Demo Cleanup

- [ ] Stop backend and frontend dev servers (`Ctrl+C`).
- [ ] Clean up demo artifacts if desired:
  ```bash
  rm -f demo_techsift.db demo_techsift.db-shm demo_techsift.db-wal
  rm -rf ./demo_storage
  ```
- [ ] Your primary `techsift.db` and `./storage` remain completely untouched.
