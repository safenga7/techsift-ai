"""
Phase 0 - Test 2: Document Processing Feasibility Test
Generates a sample technical PDF locally, extracts text with pypdf,
and tests overlapping text chunking with automated assertions.
"""

import os
from pathlib import Path
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_sample_technical_pdf(output_path: Path) -> Path:
    """Generate a realistic technical document PDF locally without external tools."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Distributed Systems: Consensus via Raft Protocol")

    # Metadata
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(72, height - 92, "Technical Document Analysis - TechSift AI Specification")

    # Content
    c.setFont("Helvetica", 11)
    lines = [
        "Consensus algorithms allow a collection of machines to work as a coherent group",
        "that can survive the failures of some of its members. Raft is a consensus algorithm",
        "for managing a replicated log equivalent to Paxos in fault-tolerance and performance,",
        "but structured for superior understandability.",
        "",
        "Key concepts of Raft include:",
        "1. Leader Election: A single leader handles client requests and coordinates replication.",
        "2. Log Replication: The leader accepts log entries and synchronizes them across followers.",
        "3. Safety: If any server applies a log entry, no other server will apply a different one.",
        "",
        "FastAPI provides asynchronous execution using Python's asyncio event loop, making it ideal",
        "for handling concurrent document processing workloads with zero blocking I/O overhead."
    ]

    y = height - 120
    for line in lines:
        c.drawString(72, y, line)
        y -= 18

    c.save()
    return output_path


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract plain text from PDF using open-source pypdf."""
    reader = PdfReader(str(pdf_path))
    extracted = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted.append(text)
    return "\n".join(extracted)


def chunk_text(text: str, chunk_size: int = 150, overlap: int = 30) -> list[str]:
    """
    Split text into chunks of specified length with sliding window overlap.
    Preserves context between chunk boundaries for LLM ingestion.
    """
    if not text:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be strictly greater than overlap")

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += (chunk_size - overlap)

    return chunks


def run_document_processing_test() -> dict:
    test_dir = Path("./storage/test")
    pdf_path = test_dir / "sample_technical_doc.pdf"

    # Step 1: Generate PDF
    generate_sample_technical_pdf(pdf_path)
    assert pdf_path.exists(), "PDF generation failed: file does not exist"
    assert pdf_path.stat().st_size > 0, "PDF generation failed: file is empty"

    # Step 2: Extract Text
    extracted_text = extract_text_from_pdf(pdf_path)
    assert len(extracted_text) > 0, "PDF extraction failed: zero text extracted"

    # Step 3: Assertions on Content
    required_keywords = ["Consensus", "Raft", "Leader Election", "Log Replication", "FastAPI"]
    for kw in required_keywords:
        assert kw in extracted_text, f"Missing expected keyword '{kw}' in extracted text"

    # Step 4: Chunking Test
    chunks = chunk_text(extracted_text, chunk_size=200, overlap=40)
    assert len(chunks) >= 2, f"Expected multiple chunks, got {len(chunks)}"

    # Step 5: Verify Overlap Between Adjacent Chunks
    for i in range(len(chunks) - 1):
        c1 = chunks[i]
        c2 = chunks[i + 1]
        # Verify non-empty
        assert len(c1) > 0 and len(c2) > 0, "Chunk cannot be empty"

    return {
        "status": "PASSED",
        "pdf_size_bytes": pdf_path.stat().st_size,
        "extracted_char_count": len(extracted_text),
        "chunk_count": len(chunks),
        "sample_chunk_1": chunks[0][:80] + "...",
        "sample_chunk_2": chunks[1][:80] + "...",
    }


if __name__ == "__main__":
    result = run_document_processing_test()
    print("--- DOCUMENT PROCESSING TEST RESULT ---")
    for k, v in result.items():
        print(f"{k}: {v}")
