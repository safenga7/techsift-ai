"""
TechSift AI - Document Text Extraction & Validation Service.
Extracts text from PDF, TXT, and Markdown documents.
Detects image-only / scanned PDFs and enforces format signatures.
"""

from dataclasses import dataclass
import io
from pathlib import Path
from typing import Optional
from pypdf import PdfReader
from src.core.config import settings
from src.core.exceptions import FileValidationError, UnsupportedDocumentError


@dataclass
class ExtractionResult:
    text: str
    word_count: int
    page_count: Optional[int]


class TextExtractorService:
    """Handles file validation and robust text extraction across supported formats."""

    @staticmethod
    def validate_file_format(filename: str, content: bytes) -> str:
        """
        Validates file extension and binary magic signatures.
        Returns the normalized file type ('pdf', 'txt', 'md').
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in settings.allowed_extensions_set:
            raise FileValidationError(
                f"Unsupported file extension '.{ext}'. "
                f"Allowed formats: {', '.join(sorted(settings.allowed_extensions_set))}"
            )

        if len(content) == 0:
            raise FileValidationError("Uploaded file is empty (0 bytes).")

        # Validate PDF signature
        if ext == "pdf":
            if not content.startswith(b"%PDF-"):
                raise FileValidationError(
                    "Invalid PDF file: File lacks the required '%PDF-' header signature."
                )
            return "pdf"

        # Validate TXT & Markdown content (must not be arbitrary binary)
        if ext in ("txt", "md"):
            # Check for binary null bytes common in executables/archives
            if b"\x00" in content[:1024]:
                raise FileValidationError(
                    f"Invalid {ext.upper()} file: Binary content detected."
                )
            # Verify decodeability
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content.decode("latin-1")
                except Exception as exc:
                    raise FileValidationError(
                        f"Unable to decode {ext.upper()} text file."
                    ) from exc
            return ext

        raise FileValidationError(f"Unsupported file format: {ext}")

    def extract(self, content: bytes, file_type: str) -> ExtractionResult:
        """Extract text and metadata from document content based on validated type."""
        if file_type == "pdf":
            return self._extract_pdf(content)
        elif file_type == "txt":
            return self._extract_txt(content)
        elif file_type == "md":
            return self._extract_markdown(content)
        else:
            raise FileValidationError(f"Cannot extract from unrecognized file type: {file_type}")

    def _extract_pdf(self, content: bytes) -> ExtractionResult:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as exc:
            raise FileValidationError(f"Corrupted or invalid PDF document: {str(exc)}") from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise UnsupportedDocumentError("PDF document has 0 pages.")

        extracted_pages: list[str] = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())
            except Exception:
                # Tolerate individual malformed page streams
                continue

        full_text = "\n\n".join(extracted_pages).strip()

        # Scanned PDF detection
        if not full_text:
            raise UnsupportedDocumentError(
                "Unsupported document: Scanned or image-only PDF contains no extractable text. "
                "OCR is not supported in the zero-cost tier."
            )

        word_count = len(full_text.split())
        return ExtractionResult(
            text=full_text,
            word_count=word_count,
            page_count=page_count,
        )

    def _extract_txt(self, content: bytes) -> ExtractionResult:
        try:
            text = content.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = content.decode("latin-1").strip()

        word_count = len(text.split())
        return ExtractionResult(
            text=text,
            word_count=word_count,
            page_count=None,
        )

    def _extract_markdown(self, content: bytes) -> ExtractionResult:
        try:
            text = content.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = content.decode("latin-1").strip()

        word_count = len(text.split())
        return ExtractionResult(
            text=text,
            word_count=word_count,
            page_count=None,
        )


text_extractor_service = TextExtractorService()
