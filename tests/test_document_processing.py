"""
Automated unit tests for document processing and chunking.
"""

from pathlib import Path
from scripts.test_document_processing import (
    generate_sample_technical_pdf,
    extract_text_from_pdf,
    chunk_text,
)


def test_pdf_generation_and_extraction(tmp_path: Path):
    pdf_path = tmp_path / "test_doc.pdf"
    generate_sample_technical_pdf(pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    text = extract_text_from_pdf(pdf_path)
    assert "Consensus" in text
    assert "Raft" in text
    assert "FastAPI" in text


def test_chunking_with_overlap():
    sample_text = (
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau"
    )
    chunks = chunk_text(sample_text, chunk_size=30, overlap=10)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 30
        assert len(chunk) > 0


def test_chunking_invalid_parameters():
    try:
        chunk_text("test", chunk_size=10, overlap=10)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
