# TechSift AI — Portfolio Screenshot Plan

This document outlines the professional screenshot capture guide for the TechSift AI GitHub showcase, documentation, and portfolio presentations.

---

## 1. General Capture Guidelines

* **Target Viewport**: 1920 × 1080 (16:9 Desktop Full-HD) or 1440 × 900 (MacBook Retina Standard).
* **Browser Chrome**: Hide bookmarks bar, extensions, and URL address bar (clean framed window or browser mockup frame).
* **Theme Recommendation**: Dark mode (`dark`) for high-contrast technical aesthetic, with select screenshots highlighting clean bilingual light mode.
* **Sensitive Data Protocol**:
  * **Zero Private Documents**: Only use synthetic documents from `samples/` (`distributed_consensus_raft_architecture.md`, `event_driven_microservices_architecture.txt`, `distributed_caching_and_consistency.pdf`).
  * **API Keys & Paths**: Never display terminal windows with `.env` or local filesystem absolute paths (`/Users/username/...`).

---

## 2. Screenshot Specifications

### Screenshot 01: Multi-Format Ingestion & Library
* **Route**: `/documents`
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: Document library containing 3 synthetic files (`distributed_consensus_raft_architecture.md`, `event_driven_microservices_architecture.txt`, `distributed_caching_and_consistency.pdf`), all with `PROCESSED` status badges.
* **Highlighted UI Elements**:
  * Dropzone upload zone banner with drag-and-drop support for PDF, Markdown, and TXT.
  * Status filter pills (`All`, `Processed`, `Pending`, `Failed`).
  * Document cards/table showing format badges (`PDF`, `MD`, `TXT`), file sizes, and clean workspace launch action.
* **Sensitive Info to Exclude**: Personal folder names or private filenames.

---

### Screenshot 02: Processing Pipeline & Real-Time Feedback
* **Route**: `/documents` (active upload) or `/workspace/:id`
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: Ingestion of a synthetic document showing active progress bar or processing indicators.
* **Highlighted UI Elements**:
  * Live status pill (`Processing` / `Ready`).
  * Ingestion phase feedback (PDF text extraction, chunking, database registration).
  * Breadcrumb navigation and header action bar.

---

### Screenshot 03: Executive Document Summary & Key Takeaways
* **Route**: `/workspace/:id` (Tab: "Document Summary")
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Sample Document**: `samples/distributed_consensus_raft_architecture.md`
* **Highlighted UI Elements**:
  * Executive Overview callout box.
  * Structured key takeaways with bulleted technical insights.
  * Extracted domain glossary terms with concise definitions.
  * Language toggle pill (highlighting bilingual generation option).

---

### Screenshot 04: Bilingual Audio Studio & Synchronized Player
* **Route**: `/workspace/:id` (Tab: "Audio Studio")
* **Theme**: Dark Mode
* **Language & Direction**: Arabic (RTL) — *Demonstrating native RTL engineering*
* **Demo State**: Arabic narration generated and loaded into the custom HTML5 wave-styled audio player.
* **Highlighted UI Elements**:
  * Arabic typography and full RTL layout alignment.
  * Voice persona selector (`Hamdan - Empathic Male` / `Salma - Dynamic Female`).
  * Playback speed controls (`0.75x`, `1.0x`, `1.25x`, `1.5x`).
  * Waveform/scrubber progress bar and volume controls.

---

### Screenshot 05: Multi-Speaker Educational Podcast
* **Route**: `/workspace/:id` (Tab: "Audio Studio" $\to$ Sub-tab: "Educational Podcast")
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: Generated two-host dialogue ("Dr. Maya Chen & Alex Rivera") breaking down technical concepts.
* **Highlighted UI Elements**:
  * Multi-voice dialogue script preview showing speaker tags and timestamps.
  * Dual-track audio synthesis indicator powered by Microsoft Edge TTS.
  * Single combined playable MP3 audio stream with instant download action.

---

### Screenshot 06: Interactive Learning Path
* **Route**: `/workspace/:id` (Tab: "Learning Studio")
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: Generated 3-module curriculum with structured pedagogical progression (Foundational $\to$ Intermediate $\to$ Advanced).
* **Highlighted UI Elements**:
  * Module accordion cards with estimated study durations and prerequisite indicators.
  * Lesson list showing completion checkmarks and interactive study links.
  * Source grounding pill showing exact source section references.

---

### Screenshot 07: Source-Grounded Quiz & Instant Feedback
* **Route**: `/workspace/:id` (Lesson Modal / Assessment View)
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: 5-question multiple choice quiz with an answered question showing instant feedback.
* **Highlighted UI Elements**:
  * Source citation citation box (`Referenced from Section 3.2`).
  * Clear visual indicator of correct/incorrect choice with explanation rationale.
  * Question navigator stepper pills at top of modal.

---

### Screenshot 08: Comprehensive Assessment / Final Exam
* **Route**: `/workspace/:id` (Learning Studio $\to$ "Final Assessment")
* **Theme**: Light Mode — *Demonstrating crisp high-contrast light mode*
* **Language & Direction**: English (LTR)
* **Demo State**: Final Exam submission summary showing score percentage (e.g., 90%), mastery tier badge (`Mastery`), and question breakdown.
* **Highlighted UI Elements**:
  * Score gauge / progress radial or percentage badge.
  * Retake exam button and detailed answer review drawer.
  * Passing threshold comparison (80% minimum passing requirement).

---

### Screenshot 09: Learning Progress & Mastery Dashboard
* **Route**: `/workspace/:id` (Tab: "Progress Dashboard")
* **Theme**: Dark Mode
* **Language & Direction**: English (LTR)
* **Demo State**: Fully tracked learning progress with 1 completed module, 3 completed lessons, and 1 passed assessment.
* **Highlighted UI Elements**:
  * Overall Curriculum Completion bar (e.g., `67% Complete`).
  * Average Assessment Score card with pass/fail ratio.
  * Module-by-module breakdown progress bars.
  * Recent quiz attempt history table with timestamps and scores.
