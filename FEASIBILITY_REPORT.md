# TechSift AI — Feasibility & Zero-Cost Architecture Audit Report (Phase 0)

**Date**: October 13, 2026  
**Final Status**: FULL GO — 100% Zero-Cost Technical Feasibility Confirmed  
**Audit Author**: Senior Python Backend Engineer, AI Engineer & System Architect  
**Project Repository**: `techsift-ai`  

---

## 1. Executive Summary & Audit Verdict

| Component | Tested Tool / Package | Version | Status | Zero-Cost Compliance Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Python Environment** | Python (Homebrew) | 3.12.15 | **PASSED** | Isolated `.venv`, zero third-party cloud SDK bloat. |
| **AI / LLM Provider** | `google-genai` SDK | 2.29.0 | **PASSED** | Official Free Tier (`gemini-3.8-flash`): $0.00 input/output, verified via official Google pricing docs. |
| **Document Processing** | `pypdf`, `reportlab` | 6.20.1 / 5.0.1 | **PASSED** | 100% local PDF generation, text extraction, and overlapping chunking with automated assertions. |
| **Text-to-Speech (TTS)** | `pyttsx3` / OS Native | 2.99 / Built-in | **PASSED** | 100% offline speech synthesis (172 KB audio generated); zero external billing or API keys. |
| **TTS (Client-Side)** | Browser Web Speech API | Native | **PASSED** | Modern browser standard (`window.speechSynthesis`), zero server compute, zero network cost. |
| **Backend API** | `fastapi`, `uvicorn`, `httpx` | 0.143.0 / 0.54.0 | **PASSED** | Local ASGI server returned HTTP 200 with typed JSON payload over real loopback HTTP request. |
| **Frontend Toolchain** | React 19 + TypeScript 6 + Vite | Vite 8.3.4 | **PASSED** | Dependencies installed, zero audit vulnerabilities, production build succeeded in 121ms (`dist/`). |
| **Test Automation** | `pytest`, `pytest-asyncio` | 9.1.1 / 1.4.0 | **PASSED** | 8 automated tests passed covering API health, chunking, rate limiting, and safeguards. |

### Final Audit Determination: **FULL GO**
The TechSift AI Minimum Viable Product (MVP) **can be completely developed, tested, and demonstrated with zero paid services, zero credit cards, and zero cloud billing**.

---

## 2. In-Depth Google Gemini Free Tier Audit

### 2.1 Official Documentation Verification (`ai.google.dev/pricing`)
Official documentation confirms that **Gemini 3.8 Flash** (`models/gemini-3.8-flash`) is provisioned on the **Gemini API Free Tier**:

* **Token Pricing (Free Tier)**:
  * Input Tokens: **$0.00 / 1M tokens** (Free of charge)
  * Output Tokens (including thinking tokens): **$0.00 / 1M tokens** (Free of charge)
  * Context Caching: **$0.00** (Free of charge)
* **Grounding with Search / Maps**:
  * *Disabled on Free Tier*: Grounding features require a paid billing account. TechSift AI strictly relies on local document context chunks in prompts, completely eliminating any reliance on grounding features.
* **Data Governance & Privacy Trade-off**:
  * Under the Free Tier, prompt and response data may be reviewed by human annotators and used to train Google machine learning models.
  * For an open-source technical document portfolio platform, this is fully acceptable. Documents remain strictly local; only extracted technical text chunks are sent for summarization.

### 2.2 Free Tier vs. Paid Tier Differentiation

| Attribute | Free Tier (TechSift AI Selection) | Paid Tier (STRICTLY PROHIBITED) |
| :--- | :--- | :--- |
| **Billing Account Required** | **NO** (0 credit cards required) | **YES** (Google Cloud Billing account) |
| **Cost per 1M Input Tokens** | **$0.00** | $0.75 – $1.50 |
| **Cost per 1M Output Tokens** | **$0.00** | $3.75 – $7.50 |
| **Rate Limits (Flash)** | 10–15 RPM, ~250–1,500 RPD, ~250k TPM | Up to 1,000+ RPM |
| **Model Sunset Behavior** | Legacy models (e.g. 2.5 Flash) return 404 to new users | Maintained longer for enterprise SLAs |

### 2.3 Account Quotas & Metadata for `gemini-3.8-flash`
Inspecting model metadata via `client.models.get("models/gemini-3.8-flash")` without running unneeded text generation confirmed:
* **Model Name**: `models/gemini-3.8-flash`
* **Input Token Limit**: **1,048,576 tokens** (enables full technical document analysis)
* **Output Token Limit**: **65,536 tokens**
* **Supported Methods**: `generateContent`, `countTokens`, `createCachedContent`, `batchGenerateContent`
* **Real-time Quota Dashboard**: Active quotas are managed per-project at [Google AI Studio Rate Limit Console](https://aistudio.google.com/rate-limit). Typical quotas provide ~15 RPM and up to 1,500 RPD.

---

## 3. Production Architecture & Safeguards Implemented

To protect against free-tier constraints and network fluctuations, the following safeguards are implemented in `src/core` and `src/services`:

```mermaid
flowchart LR
    REQ[Client Request] --> RL[Token-Bucket Rate Limiter]
    RL -->|Checks Max 10 RPM| TO[30s Request Timeout Wrapper]
    TO --> CALL[google-genai Client]
    CALL -->|Success| OUT[Sanitized Response]
    CALL -->|429 Resource Exhausted| ERR1[RateLimitExceededError]
    CALL -->|404 Sunset / Not Found| FB[Fallback Chain: 3.8 -> 3.5 -> Flash Latest]
    CALL -->|403 Auth Error| ERR2[AIAuthenticationError]
```

### 3.1 Rate Limit Protection (`src/core/rate_limiter.py`)
* Implemented an in-memory `FreeTierRateLimiter` token-bucket algorithm (`max_rpm=10`).
* Enforces an automated sleep delay between consecutive requests, ensuring execution remains well beneath Google's 15 RPM free-tier threshold with zero Redis overhead.

### 3.2 Request Timeout Safeguards (`src/core/config.py`)
* Configured `GEMINI_TIMEOUT_SECONDS = 30.0`.
* All asynchronous calls run via `asyncio.wait_for(asyncio.to_thread(...), timeout=30.0)` to ensure a slow network connection never starves the FastAPI event loop.

### 3.3 Dynamic Model Switching & Fallback Chain (`src/services/ai_provider.py`)
* The active model is dynamically controlled via the `GEMINI_MODEL` environment variable.
* If a model becomes unavailable (e.g., historical 404 on `gemini-2.5-flash`), the provider automatically cycles through a priority fallback chain (`gemini-3.8-flash` $\to$ `gemini-3.5-flash` $\to$ `gemini-flash-latest`).

### 3.4 Secret Isolation & Zero-Leakage Sanitizer
* All API keys are loaded via Pydantic `BaseSettings` from `.env`.
* Verified that `.env` is ignored by `.gitignore`.
* A recursive string sanitizer `mask_secret()` strips API keys from any error messages or tracebacks before logging.

---

## 4. Verification Checkpoint Matrix for All Modules

| Subsystem | Test Executed | Verification Standard | Result |
| :--- | :--- | :--- | :--- |
| **PDF Ingestion** | `test_document_processing.py` | Validated text extraction and sliding-window chunking (chunk=200, overlap=40) with automated assertions. | **PASSED** (100% assertions) |
| **FastAPI Backend** | `test_health_api.py` | Booted ASGI server; executed HTTP GET `/health`; verified HTTP 200 and schema response. | **PASSED** |
| **Audio Synthesis** | `test_tts.py` | Evaluated `edge-tts` (failed 403 on Cairo node) and verified offline `pyttsx3` (generated 172 KB audio). | **PASSED** (Local fallback verified) |
| **Frontend Toolchain** | `npm run build` | Scaffolding in `frontend/`, audited 28 dependencies, built production bundle in 121ms (`dist/`). | **PASSED** |
| **AI Safeguards** | `test_ai_provider.py` | Tested offline rate-limiter throttling, secret masking, and authentication exception raising. | **PASSED** (4/4 tests) |
| **Overall Pytest Suite**| `pytest tests/` | Full automated Python test suite. | **8 passed, 0 failed** |

---

## 5. Remaining Uncertainties & Mitigation Strategy

| Uncertainty | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Daily Request Cap (RPD ~1,500)** | Exhaustion under intensive continuous automated testing | Low | Cache all generated summaries and glossary extractions in local SQLite. Repeated document views consume 0 tokens. |
| **Client Audio Streaming across Platforms** | OS-dependent local TTS voices (`pyttsx3` vs. macOS vs. Linux) | Low | Use browser-native Web Speech API (`window.speechSynthesis`) on the frontend as the default playback engine. |
| **Future Model Deprecation by Google** | Configured model ID returning 404 in the future | Low | Dynamic fallback chain and configurable `GEMINI_MODEL` environment variable require zero code changes to update. |

---

## 6. Zero-Cost Architecture Guarantee

* **Hosting & Runtime**: 100% Local (Localhost 127.0.0.1)
* **Database**: Local SQLite via async SQLAlchemy (`techsift.db`)
* **Storage**: Local filesystem directory (`./storage`)
* **AI Engine**: Google AI Studio Free Tier ($0.00 / 0 credit cards)
* **Audio Engine**: Local offline synthesis (`pyttsx3`) + Browser Web Speech API ($0.00)
* **Frontend**: React 19 + TypeScript + Vite running locally ($0.00)

**Conclusion**: The system is completely viable, robustly guarded, and ready for Phase 1 implementation upon explicit user instruction.
