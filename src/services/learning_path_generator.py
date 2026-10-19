"""
TechSift AI - Structured AI Learning Path Generator (Phase 5A).
Transforms technical documents into grounded, modular curricula using Gemini AI Provider
with strict citation validation and deterministic fallback degradation.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from src.core.exceptions import AIProviderException
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.schemas.learning_path import (
    DifficultyEnum,
    GeneratedLearningPathContent,
    GeneratedLesson,
    GeneratedModule,
    KeyConceptItem,
    SourceReference,
)
from src.schemas.summary import LanguageEnum
from src.services.ai_provider import AIProvider, GeminiProvider

logger = logging.getLogger(__name__)


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """Robustly extracts and parses JSON object from LLM response text."""
    text = text.strip()
    json_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_block:
        clean_text = json_block.group(1).strip()
    else:
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            clean_text = brace_match.group(1).strip()
        else:
            clean_text = text
    return json.loads(clean_text)


class LearningPathGenerator:
    """Generates structured, source-grounded bilingual curricula."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or GeminiProvider()

    def _build_system_instruction(
        self,
        language: LanguageEnum,
        difficulty: DifficultyEnum,
    ) -> str:
        lang_instruction = (
            "You are a Senior Technical Curriculum Architect and Systems Pedagogy Specialist. "
            "Your output language MUST BE MODERN STANDARD ARABIC (اللغة العربية الفصحى الحديثة).\n"
            "CRITICAL BILINGUAL RULES FOR ARABIC:\n"
            "- Write in clear, professional Modern Standard Arabic.\n"
            "- PRESERVE all technical terms, code keywords, identifiers, protocols, and architectural acronyms "
            "in English alongside Arabic (e.g. 'خوارزمية الإجماع (Consensus Algorithm)', 'FastAPI', 'SQLite ACID').\n"
            "- NEVER translate programming keywords, CLI commands, or variable names."
            if language == LanguageEnum.AR
            else
            "You are a Senior Technical Curriculum Architect and Systems Pedagogy Specialist. "
            "Your output language MUST BE PRECISE TECHNICAL ENGLISH.\n"
            "Preserve exact architectural taxonomy, identifiers, and formal terms."
        )

        diff_instruction = {
            DifficultyEnum.BEGINNER: (
                "TARGET AUDIENCE: BEGINNER / JUNIOR ENGINEER.\n"
                "Focus on fundamental mental models, foundational terminology, high-level intuition, "
                "and why this technology exists before deep mechanics. Break concepts into 2-3 accessible modules."
            ),
            DifficultyEnum.INTERMEDIATE: (
                "TARGET AUDIENCE: PRACTICING SOFTWARE ENGINEER.\n"
                "Focus on architectural mechanisms, component interactions, trade-offs, practical implementations, "
                "and production engineering decisions. Structure into 3-4 comprehensive modules."
            ),
            DifficultyEnum.ADVANCED: (
                "TARGET AUDIENCE: SENIOR / PRINCIPAL SYSTEMS ARCHITECT.\n"
                "Focus on failure modes, concurrency guarantees, performance edge cases, formal invariants, "
                "and deep distributed/low-level mechanics. Structure into 3-5 rigorous modules."
            ),
        }[difficulty]

        return (
            f"{lang_instruction}\n\n"
            f"DIFFICULTY LEVEL SPECIFICATIONS:\n{diff_instruction}\n\n"
            "STRICT GROUNDING & CITATION RULES:\n"
            "1. Ground all explanations, concepts, and examples EXCLUSIVELY in the provided document content.\n"
            "2. Never hallucinate facts, APIs, or architectural claims not present in or directly derived from the document.\n"
            "3. For each lesson's source_references, ONLY cite chunk indices and page numbers that exist in the source.\n"
            "4. Respond with a SINGLE RAW VALID JSON object adhering strictly to the requested schema. No conversational preamble."
        )

    def _build_prompt(
        self,
        document_text: str,
        available_pages: List[int],
        available_chunks: List[int],
        language: LanguageEnum,
        difficulty: DifficultyEnum,
    ) -> str:
        lang_str = "Modern Standard Arabic" if language == LanguageEnum.AR else "English"
        schema_format = {
            "title": f"Complete Guide to ... ({difficulty.value.capitalize()} Path)",
            "description": "Comprehensive course description overview",
            "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
            "learning_objectives": ["Overall course objective 1", "Overall course objective 2"],
            "estimated_duration_minutes": 60,
            "modules": [
                {
                    "title": "Module 1: Title",
                    "description": "Module summary",
                    "learning_objectives": ["Module objective 1"],
                    "sequence_order": 1,
                    "estimated_duration_minutes": 25,
                    "lessons": [
                        {
                            "title": "Lesson 1.1: Title",
                            "explanation": "Detailed, source-grounded technical explanation paragraphs.",
                            "key_concepts": [
                                {
                                    "term": "Term or concept",
                                    "explanation": "Grounded explanation",
                                }
                            ],
                            "examples": ["Concrete practical example or code illustration"],
                            "source_references": [
                                {
                                    "page_number": available_pages[0] if available_pages else None,
                                    "chunk_index": available_chunks[0] if available_chunks else None,
                                    "section_title": "Section Title if known",
                                    "citation_text": "Supporting text quote or fact from document",
                                }
                            ],
                            "sequence_order": 1,
                            "estimated_duration_minutes": 10,
                        }
                    ],
                }
            ],
        }

        return (
            f"Analyze the following technical document and construct a complete, structured learning path in {lang_str} "
            f"at '{difficulty.value}' difficulty level.\n\n"
            f"AVAILABLE SOURCE CITATIONS:\n"
            f"- Valid page numbers: {available_pages}\n"
            f"- Valid chunk indices: {available_chunks}\n\n"
            f"SOURCE DOCUMENT CONTENT:\n\"\"\"\n{document_text}\n\"\"\"\n\n"
            f"Respond with a single valid JSON object following this exact JSON structure:\n"
            f"{json.dumps(schema_format, ensure_ascii=False, indent=2)}\n\n"
            f"CRITICAL: Lessons must ONLY reference available page numbers ({available_pages}) "
            f"and chunk indices ({available_chunks}). Return ONLY raw valid JSON."
        )

    def _sanitize_source_references(
        self,
        content: GeneratedLearningPathContent,
        available_pages: List[int],
        available_chunks: List[int],
    ) -> GeneratedLearningPathContent:
        """Enforces that AI citations strictly match actual document chunks and pages."""
        valid_pages_set = set(available_pages)
        valid_chunks_set = set(available_chunks)

        for module in content.modules:
            for lesson in module.lessons:
                sanitized_refs = []
                for ref in lesson.source_references:
                    # Validate page number
                    valid_page = ref.page_number if ref.page_number in valid_pages_set else None
                    # Validate chunk index
                    valid_chunk = ref.chunk_index if ref.chunk_index in valid_chunks_set else None

                    # Only keep citation if it has at least one valid reference or non-empty citation text
                    if valid_page is not None or valid_chunk is not None or ref.citation_text:
                        sanitized_refs.append(
                            SourceReference(
                                page_number=valid_page,
                                chunk_index=valid_chunk,
                                section_title=ref.section_title,
                                citation_text=ref.citation_text,
                            )
                        )
                lesson.source_references = sanitized_refs

        return content

    async def generate_curriculum(
        self,
        document: Document,
        chunks: List[DocumentChunk],
        language: LanguageEnum = LanguageEnum.EN,
        difficulty: DifficultyEnum = DifficultyEnum.INTERMEDIATE,
    ) -> GeneratedLearningPathContent:
        """
        Generates a structured, validated curriculum with citation grounding.
        Falls back to a deterministic curriculum if LLM fails.
        """
        if not chunks:
            raise ValueError(f"Document '{document.id}' has zero text chunks.")

        available_pages = sorted(list({c.page_number for c in chunks if c.page_number is not None}))
        available_chunks = [c.chunk_index for c in chunks]

        # Combine chunks (cap preview for safety if document is massive)
        combined_text = "\n\n".join(
            f"[Chunk {c.chunk_index} | Page {c.page_number or 'N/A'}]:\n{c.content}"
            for c in chunks[:12]
        )

        system_instruction = self._build_system_instruction(language, difficulty)
        prompt = self._build_prompt(
            document_text=combined_text,
            available_pages=available_pages,
            available_chunks=available_chunks,
            language=language,
            difficulty=difficulty,
        )

        try:
            raw_response = await self.ai_provider.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
            )
            data = extract_json_from_llm_response(raw_response)
            parsed_content = GeneratedLearningPathContent.model_validate(data)
            return self._sanitize_source_references(parsed_content, available_pages, available_chunks)

        except Exception as exc:
            logger.warning(
                f"LLM learning path generation encountered an issue ({exc}). "
                "Engaging deterministic grounded fallback generator per AGENTS.md rule 2."
            )
            return self._generate_fallback_curriculum(
                document=document,
                chunks=chunks,
                language=language,
                difficulty=difficulty,
            )

    def _generate_fallback_curriculum(
        self,
        document: Document,
        chunks: List[DocumentChunk],
        language: LanguageEnum,
        difficulty: DifficultyEnum,
    ) -> GeneratedLearningPathContent:
        """
        Deterministic, zero-cost grounded fallback curriculum generator.
        Guarantees that Learning Path generation never crashes due to
        temporary LLM network timeouts or rate limits.
        """
        doc_title = document.filename
        available_pages = [c.page_number for c in chunks if c.page_number is not None]
        first_page = available_pages[0] if available_pages else None

        if language == LanguageEnum.AR:
            title = f"المسار التعليمي التقني: {doc_title}"
            desc = f"مسار تعليمي منهجي مبني مباشرة على توثيق: {doc_title}، بمستوى صعوبة: {difficulty.value}."
            prereqs = [
                "المعرفة الأساسية بهندسة البرمجيات وبنية النظم الموزعة",
                "الإلمام بمصطلحات المعمارية التقنية ومبادئ الأداء",
            ]
            objectives = [
                f"فهم الأسس الهندسية والمعمارية الواردة في {doc_title}",
                "التعرف على المفاهيم والمصطلحات الرئيسية وتطبيقاتها العملية",
                "تقييم المفاضلات الهندسية والقيود التشغيلية",
            ]

            modules = []
            for i, chunk in enumerate(chunks[:3]):
                snippet = (chunk.content or "").strip()[:400]
                module = GeneratedModule(
                    title=f"الوحدة {i + 1}: {chunk.section_title or f'المفاهيم المعمارية (الجزء {i + 1})'}",
                    description=f"تحليل معماري لمحتوى الجزء {i + 1} من المستند.",
                    learning_objectives=[f"استيعاب المبادئ التقنية الموثقة في الجزء {i + 1}"],
                    sequence_order=i + 1,
                    estimated_duration_minutes=20,
                    lessons=[
                        GeneratedLesson(
                            title=f"الدرس {i + 1}.1: التحليل التفصيلي والأسس الهندسية",
                            explanation=f"يستعرض هذا الدرس الركائز المعمارية للنظام: {snippet}...",
                            key_concepts=[
                                KeyConceptItem(
                                    term=chunk.section_title or "المفهوم المعماري (Architectural Concept)",
                                    explanation="مبدأ تصميمي أساسي موثق في المستند لتحقيق الموثوقية والأداء.",
                                )
                            ],
                            examples=["تطبيق المفهوم في بناء بنية تحتية مقاومة للأعطال وعالية التوافر."],
                            source_references=[
                                SourceReference(
                                    page_number=chunk.page_number,
                                    chunk_index=chunk.chunk_index,
                                    section_title=chunk.section_title or "توثيق النظام",
                                    citation_text=snippet[:180],
                                )
                            ],
                            sequence_order=1,
                            estimated_duration_minutes=15,
                        )
                    ],
                )
                modules.append(module)

        else:
            title = f"Technical Learning Path: {doc_title}"
            desc = f"Structured, source-grounded curriculum derived directly from {doc_title} at {difficulty.value} level."
            prereqs = [
                "Foundational understanding of software engineering and system architecture",
                "Familiarity with distributed systems and performance trade-offs",
            ]
            objectives = [
                f"Understand the core architectural mechanisms defined in {doc_title}",
                "Master key concepts, terminology, and engineering invariants",
                "Evaluate operational trade-offs and real-world system patterns",
            ]

            modules = []
            for i, chunk in enumerate(chunks[:3]):
                snippet = (chunk.content or "").strip()[:400]
                module = GeneratedModule(
                    title=f"Module {i + 1}: {chunk.section_title or f'System Architecture (Part {i + 1})'}",
                    description=f"Architectural breakdown of part {i + 1} of the document.",
                    learning_objectives=[f"Master technical specifications in part {i + 1}"],
                    sequence_order=i + 1,
                    estimated_duration_minutes=20,
                    lessons=[
                        GeneratedLesson(
                            title=f"Lesson {i + 1}.1: Core Principles and Mechanisms",
                            explanation=f"This lesson details the foundational architecture: {snippet}...",
                            key_concepts=[
                                KeyConceptItem(
                                    term=chunk.section_title or "System Specification",
                                    explanation="Core architectural mechanism documented in technical source.",
                                )
                            ],
                            examples=["Implementing resilient, fault-tolerant component designs in production."],
                            source_references=[
                                SourceReference(
                                    page_number=chunk.page_number,
                                    chunk_index=chunk.chunk_index,
                                    section_title=chunk.section_title or "Technical Source",
                                    citation_text=snippet[:180],
                                )
                            ],
                            sequence_order=1,
                            estimated_duration_minutes=15,
                        )
                    ],
                )
                modules.append(module)

        return GeneratedLearningPathContent(
            title=title,
            description=desc,
            prerequisites=prereqs,
            learning_objectives=objectives,
            estimated_duration_minutes=len(modules) * 20,
            modules=modules,
        )


learning_path_generator = LearningPathGenerator()
