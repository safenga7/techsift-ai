"""
TechSift AI - Bilingual Document Summarization & Technical Concept Intelligence Service.
Supports English <-> Arabic cross-lingual technical summarization,
map-reduce aggregation for long documents, and strict Pydantic JSON schema validation.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from src.core.config import settings
from src.models.document_chunk import DocumentChunk
from src.schemas.summary import (
    ConceptItem,
    DetailLevelEnum,
    LanguageEnum,
    TechnicalSummaryContent,
)
from src.services.ai_provider import AIProvider, GeminiProvider

logger = logging.getLogger(__name__)


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """
    Robustly parses JSON from LLM response, stripping markdown code fences
    or extraneous narrative if present.
    """
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    json_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_block:
        clean_text = json_block.group(1).strip()
    else:
        # Match outermost { ... }
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            clean_text = brace_match.group(1).strip()
        else:
            clean_text = text

    return json.loads(clean_text)


class SummarizerService:
    """Orchestrates structured, zero-cost bilingual technical document summarization."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or GeminiProvider()

    def _build_system_instruction(self, language: LanguageEnum, detail_level: DetailLevelEnum) -> str:
        """Constructs system prompt enforcing bilingual rules and zero hallucination."""
        lang_instruction = (
            "You are a Senior Technical Architect and AI Document Analyst. "
            "Your output language MUST BE MODERN STANDARD ARABIC (اللغة العربية الفصحى الحديثة). "
            "CRITICAL BILINGUAL RULES FOR ARABIC:\n"
            "- Explain concepts in clear, professional Modern Standard Arabic.\n"
            "- PRESERVE all technical terms, identifiers, code keywords, API routes, and acronyms in English alongside Arabic (e.g. 'خوارزمية Raft (Raft Algorithm)').\n"
            "- NEVER translate programming keywords, function names, variable names, or CLI commands (e.g. 'fastapi', 'async def', 'uvicorn', 'GET /health')."
            if language == LanguageEnum.AR
            else
            "You are a Senior Technical Architect and AI Document Analyst. "
            "Your output language MUST BE PRECISE TECHNICAL ENGLISH. "
            "Preserve original terminology, identifiers, and architectural taxonomy."
        )

        detail_instruction = {
            DetailLevelEnum.SHORT: "Provide a CONCISE, high-impact technical summary with 3-5 main concepts and 3 key takeaways.",
            DetailLevelEnum.STANDARD: "Provide a BALANCED, comprehensive technical summary with executive overview, 5-8 concepts, findings, and takeaways.",
            DetailLevelEnum.DETAILED: "Provide an IN-DEPTH, deep-dive architectural analysis detailing components, relationships, limitations, and practical applications.",
        }[detail_level]

        return (
            f"{lang_instruction}\n\n"
            f"DETAIL LEVEL: {detail_instruction}\n\n"
            "STRICT GROUNDING & ZERO-HALLUCINATION RULES:\n"
            "1. Base your summary EXCLUSIVELY on the provided source document text. Do NOT invent, assume, or fabricate any facts.\n"
            "2. If a section (like 'architecture_overview' or 'limitations') is not covered in the document, set it to null or an empty list rather than inventing content.\n"
            "3. You must respond with a SINGLE RAW VALID JSON object conforming to the required schema. No conversational filler."
        )

    def _build_summarization_prompt(
        self,
        document_text: str,
        available_pages: List[int],
        available_chunks: List[int],
        language: LanguageEnum,
        detail_level: DetailLevelEnum,
    ) -> str:
        schema_format = {
            "executive_summary": "High-level technical executive summary string",
            "main_concepts": [
                {
                    "term": "Technical term (preserve English name in parentheses if in Arabic)",
                    "definition": "Clear definition derived strictly from the text",
                    "relationships": ["Related concept 1", "Related concept 2"],
                }
            ],
            "key_findings": ["Finding 1", "Finding 2"],
            "important_definitions": [
                {
                    "term": "Term or acronym",
                    "definition": "Definition string",
                    "relationships": [],
                }
            ],
            "architecture_overview": "Optional architecture overview string, or null if not applicable",
            "practical_applications": ["Application 1", "Application 2"],
            "limitations": ["Limitation or trade-off 1", "Limitation 2"],
            "key_takeaways": ["Takeaway 1", "Takeaway 2"],
            "source_pages": available_pages,
            "source_chunks": available_chunks,
        }

        lang_name = "Modern Standard Arabic" if language == LanguageEnum.AR else "English"

        return (
            f"Please analyze the following technical document content and produce a structured technical summary "
            f"in {lang_name} at '{detail_level.value}' detail level.\n\n"
            f"Source document text:\n\"\"\"\n{document_text}\n\"\"\"\n\n"
            f"You MUST return your response as a valid JSON object matching this exact structure:\n"
            f"{json.dumps(schema_format, ensure_ascii=False, indent=2)}\n\n"
            f"Only include source_pages from: {available_pages}\n"
            f"Only include source_chunks from: {available_chunks}\n"
            f"Return ONLY valid JSON."
        )

    async def summarize_document(
        self,
        chunks: List[DocumentChunk],
        language: LanguageEnum = LanguageEnum.EN,
        detail_level: DetailLevelEnum = DetailLevelEnum.STANDARD,
    ) -> TechnicalSummaryContent:
        """
        Summarizes a document using either single-pass or map-reduce aggregation
        depending on document length.
        """
        if not chunks:
            raise ValueError("Cannot summarize document with zero text chunks.")

        available_pages = sorted(list({c.page_number for c in chunks if c.page_number is not None}))
        available_chunks = [c.chunk_index for c in chunks]

        # Calculate total characters
        total_chars = sum(len(c.content) for c in chunks)
        logger.info(
            f"[Timing] Summarization started: chunks={len(chunks)}, total_chars={total_chars}, "
            f"lang={language.value}, detail={detail_level.value}"
        )

        # Map-reduce threshold: 14,000 characters
        if total_chars > 14000 and len(chunks) > 3:
            logger.info(f"Document exceeds 14k chars ({total_chars} chars). Running Map-Reduce summarization.")
            return await self._map_reduce_summarize(
                chunks=chunks,
                available_pages=available_pages,
                available_chunks=available_chunks,
                language=language,
                detail_level=detail_level,
            )
        else:
            # Single-pass summarization
            combined_text = "\n\n".join(
                f"[Chunk {c.chunk_index} | Page {c.page_number or 'N/A'}]:\n{c.content}"
                for c in chunks
            )
            return await self._single_pass_summarize(
                text=combined_text,
                available_pages=available_pages,
                available_chunks=available_chunks,
                language=language,
                detail_level=detail_level,
            )

    async def _single_pass_summarize(
        self,
        text: str,
        available_pages: List[int],
        available_chunks: List[int],
        language: LanguageEnum,
        detail_level: DetailLevelEnum,
    ) -> TechnicalSummaryContent:
        t_start = time.monotonic()
        system_instruction = self._build_system_instruction(language, detail_level)
        prompt = self._build_summarization_prompt(
            document_text=text,
            available_pages=available_pages,
            available_chunks=available_chunks,
            language=language,
            detail_level=detail_level,
        )
        t_prompt = time.monotonic() - t_start

        t_llm_start = time.monotonic()
        response_raw = await self.ai_provider.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
        )
        t_llm = time.monotonic() - t_llm_start

        t_val_start = time.monotonic()
        parsed_json = extract_json_from_llm_response(response_raw)
        # Verify source references cannot exceed actual source metadata
        if "source_pages" in parsed_json:
            parsed_json["source_pages"] = [p for p in parsed_json["source_pages"] if p in available_pages]
        if "source_chunks" in parsed_json:
            parsed_json["source_chunks"] = [c for c in parsed_json["source_chunks"] if c in available_chunks]

        # Validate with Pydantic
        content = TechnicalSummaryContent.model_validate(parsed_json)
        t_val = time.monotonic() - t_val_start
        t_total = time.monotonic() - t_start

        logger.info(
            f"[Timing] Single-pass summary pipeline complete: prompt_prep={t_prompt:.3f}s, "
            f"llm_generate={t_llm:.2f}s, parse_validate={t_val:.3f}s, total={t_total:.2f}s"
        )
        return content

    async def _map_reduce_summarize(
        self,
        chunks: List[DocumentChunk],
        available_pages: List[int],
        available_chunks: List[int],
        language: LanguageEnum,
        detail_level: DetailLevelEnum,
    ) -> TechnicalSummaryContent:
        """Map-reduce workflow for multi-page or lengthy technical documents."""
        t_mr_start = time.monotonic()
        logger.info(f"[Timing] Map-Reduce Phase 1 (Map) started for {len(chunks)} chunks...")
        chunk_digests: List[str] = []
        for c in chunks:
            t_chunk_start = time.monotonic()
            map_prompt = (
                f"Extract 3-5 core technical facts, definitions, and architecture notes from this chunk "
                f"(Page {c.page_number or 'N/A'}):\n\n{c.content}"
            )
            digest = await self.ai_provider.generate_text(prompt=map_prompt)
            chunk_digests.append(f"[Chunk {c.chunk_index} (Page {c.page_number or 'N/A'}) Digest]:\n{digest}")
            logger.info(f"[Timing] Chunk {c.chunk_index} map digest generated in {time.monotonic() - t_chunk_start:.2f}s")

        t_map_total = time.monotonic() - t_mr_start
        logger.info(f"[Timing] Map phase complete in {t_map_total:.2f}s. Starting Phase 2 (Reduce)...")

        # 2. Reduce Phase: Synthesize final comprehensive summary from digests
        reduced_content = "\n\n".join(chunk_digests)
        summary = await self._single_pass_summarize(
            text=reduced_content,
            available_pages=available_pages,
            available_chunks=available_chunks,
            language=language,
            detail_level=detail_level,
        )
        logger.info(f"[Timing] Map-Reduce summarization complete in {time.monotonic() - t_mr_start:.2f}s")
        return summary


summarizer_service = SummarizerService()
