"""
TechSift AI - Document Chunking Service.
Splits technical documents into sliding-window chunks with page number tracking
and heading/section preservation for map-reduce summarization.
"""

from dataclasses import dataclass
import io
import re
from typing import List, Optional
from pypdf import PdfReader
from src.models.document_chunk import DocumentChunk


@dataclass
class ChunkData:
    chunk_index: int
    content: str
    page_number: Optional[int]
    section_title: Optional[str]
    start_char: int
    end_char: int


class ChunkerService:
    """Chunks documents into contextual segments with verified page and section references."""

    def __init__(self, chunk_size: int = 2500, chunk_overlap: int = 300):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pdf(self, pdf_bytes: bytes) -> List[ChunkData]:
        """
        Extracts chunks from PDF, precisely binding each chunk to its source page number.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        chunks: List[ChunkData] = []
        global_char_offset = 0
        chunk_idx = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            if not page_text:
                continue

            page_len = len(page_text)
            if page_len <= self.chunk_size:
                chunks.append(
                    ChunkData(
                        chunk_index=chunk_idx,
                        content=page_text,
                        page_number=page_num,
                        section_title=f"Page {page_num}",
                        start_char=global_char_offset,
                        end_char=global_char_offset + page_len,
                    )
                )
                chunk_idx += 1
            else:
                # Sliding window within the page
                start = 0
                while start < page_len:
                    end = min(start + self.chunk_size, page_len)
                    sub_text = page_text[start:end].strip()
                    if sub_text:
                        chunks.append(
                            ChunkData(
                                chunk_index=chunk_idx,
                                content=sub_text,
                                page_number=page_num,
                                section_title=f"Page {page_num} (Part {chunk_idx + 1})",
                                start_char=global_char_offset + start,
                                end_char=global_char_offset + end,
                            )
                        )
                        chunk_idx += 1
                    if end >= page_len:
                        break
                    start += (self.chunk_size - self.chunk_overlap)

            global_char_offset += page_len + 2

        return chunks

    def chunk_text(self, text: str, is_markdown: bool = False) -> List[ChunkData]:
        """
        Splits plain text or Markdown into overlapping chunks, tracking section headings.
        """
        if not text or not text.strip():
            return []

        chunks: List[ChunkData] = []
        text_len = len(text)
        start = 0
        chunk_idx = 0

        # Pattern to detect Markdown headings
        heading_pattern = re.compile(r"^(#{1,6}\s+.*|[A-Z0-9\s_\-]{3,}:)$", re.MULTILINE)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_content = text[start:end].strip()

            # Attempt to find closest section title
            section_title = None
            if is_markdown:
                matches = list(heading_pattern.finditer(text[:end]))
                if matches:
                    section_title = matches[-1].group(0).strip("# ").strip()

            if chunk_content:
                chunks.append(
                    ChunkData(
                        chunk_index=chunk_idx,
                        content=chunk_content,
                        page_number=None,
                        section_title=section_title or f"Section {chunk_idx + 1}",
                        start_char=start,
                        end_char=end,
                    )
                )
                chunk_idx += 1

            if end >= text_len:
                break
            start += (self.chunk_size - self.chunk_overlap)

        return chunks

    def to_orm_chunks(self, document_id: str, chunk_items: List[ChunkData]) -> List[DocumentChunk]:
        """Converts ChunkData dataclasses to SQLAlchemy DocumentChunk entities."""
        return [
            DocumentChunk(
                document_id=document_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                section_title=c.section_title,
                start_char=c.start_char,
                end_char=c.end_char,
                content=c.content,
            )
            for c in chunk_items
        ]


chunker_service = ChunkerService()
