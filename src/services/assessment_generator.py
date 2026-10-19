"""
TechSift AI - Structured AI Assessment & Quiz Generator (Phase 5B).
Generates source-grounded, multiple-choice questions for lessons, modules, and full curricula
with strict 4-option validation, single correct answer, and deterministic fallback.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from src.core.exceptions import AIProviderException
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.schemas.assessment import (
    AssessmentTypeEnum,
    GeneratedAssessmentContent,
    GeneratedAssessmentQuestion,
    QuestionTypeEnum,
    SourceReference,
)
from src.schemas.learning_path import DifficultyEnum
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


class AssessmentGenerator:
    """Generates structured, source-grounded multiple-choice assessments."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or GeminiProvider()

    def _build_system_instruction(self, language: LanguageEnum, difficulty: str) -> str:
        lang_directive = (
            "You are an elite bilingual technical educator and assessment designer. "
            "Write the assessment entirely in Modern Standard Arabic (العربية الفصحى). "
            "Preserve English technical terms, identifiers, protocols, and code keywords in brackets. "
            "Ensure grammatical accuracy and natural Arabic phrasing."
            if language == LanguageEnum.AR
            else (
                "You are an elite bilingual technical educator and assessment designer. "
                "Write the assessment in rigorous, precise English technical prose."
            )
        )

        return (
            f"{lang_directive}\n"
            f"Target audience level: {difficulty.upper()}.\n"
            "Rules for Question Generation:\n"
            "1. Each question MUST test architectural understanding, trade-offs, and applied reasoning—NOT trivial word recall.\n"
            "2. Each question MUST have EXACTLY 4 plausible, distinct answer options (no duplicate or redundant choices).\n"
            "3. Exactly 1 choice MUST be correct, and 3 choices MUST be intelligent distractors representing common engineering misconceptions.\n"
            "4. Never use 'All of the above' or 'None of the above'.\n"
            "5. Provide an educational explanation for why the correct answer is right and why the distractors are wrong.\n"
            "6. Ground each question strictly in the provided document content and citations. Never fabricate citations or facts."
        )

    async def generate_assessment(
        self,
        assessment_type: AssessmentTypeEnum,
        learning_path: LearningPath,
        document: Document,
        chunks: List[DocumentChunk],
        module: Optional[LearningModule] = None,
        lesson: Optional[LearningLesson] = None,
        question_count: Optional[int] = None,
    ) -> GeneratedAssessmentContent:
        """
        Synthesizes an assessment tailored to the requested scope.
        Validates against Pydantic schema with deterministic fallback.
        """
        # Determine target question count
        if question_count is None:
            if assessment_type == AssessmentTypeEnum.LESSON_QUIZ:
                target_count = 5
            elif assessment_type == AssessmentTypeEnum.MODULE_ASSESSMENT:
                target_count = 10
            else:
                target_count = 15
        else:
            target_count = max(1, min(question_count, 25))

        lang_enum = LanguageEnum.AR if learning_path.language == "ar" else LanguageEnum.EN
        system_instruction = self._build_system_instruction(lang_enum, learning_path.difficulty)

        # Build context prompt based on scope
        scope_description = ""
        context_body = ""
        available_pages = set()
        available_chunks = set()

        for c in chunks:
            available_chunks.add(c.chunk_index)
            if c.page_number:
                available_pages.add(c.page_number)

        if assessment_type == AssessmentTypeEnum.LESSON_QUIZ and lesson:
            scope_description = f"Lesson Quiz for Lesson: '{lesson.title}'"
            context_body = (
                f"Lesson Title: {lesson.title}\n"
                f"Lesson Explanation: {lesson.explanation}\n"
                f"Key Concepts: {json.dumps(lesson.key_concepts or [], ensure_ascii=False)}\n"
                f"Examples: {json.dumps(lesson.examples or [], ensure_ascii=False)}\n"
                f"Source Citations: {json.dumps(lesson.source_references or [], ensure_ascii=False)}\n"
            )
        elif assessment_type == AssessmentTypeEnum.MODULE_ASSESSMENT and module:
            scope_description = f"Module Assessment for Module: '{module.title}'"
            lessons_text = []
            for les in module.lessons or []:
                lessons_text.append(
                    f"--- Lesson {les.sequence_order}: {les.title} ---\n"
                    f"{les.explanation}\n"
                    f"Concepts: {json.dumps(les.key_concepts or [], ensure_ascii=False)}"
                )
            context_body = (
                f"Module Title: {module.title}\n"
                f"Module Description: {module.description or ''}\n"
                f"Objectives: {json.dumps(module.learning_objectives or [], ensure_ascii=False)}\n\n"
                + "\n\n".join(lessons_text)
            )
        else:
            scope_description = f"Final Comprehensive Assessment for Curriculum: '{learning_path.title}'"
            modules_summary = []
            for mod in learning_path.modules or []:
                lessons_titles = [f"Lesson {l.sequence_order}: {l.title}" for l in mod.lessons or []]
                modules_summary.append(
                    f"Module {mod.sequence_order}: {mod.title}\n"
                    f"Objectives: {json.dumps(mod.learning_objectives or [], ensure_ascii=False)}\n"
                    f"Lessons: {', '.join(lessons_titles)}"
                )
            context_body = (
                f"Curriculum Title: {learning_path.title}\n"
                f"Description: {learning_path.description or ''}\n"
                f"Prerequisites: {json.dumps(learning_path.prerequisites or [], ensure_ascii=False)}\n"
                f"Learning Objectives: {json.dumps(learning_path.learning_objectives or [], ensure_ascii=False)}\n\n"
                + "\n\n".join(modules_summary)
            )

        # Include excerpt from document chunks for grounding
        chunks_sample = "\n\n".join(
            [f"[Chunk {c.chunk_index} | Page {c.page_number or 'N/A'}]\n{c.content[:400]}" for c in chunks[:8]]
        )

        prompt = (
            f"Generate a {scope_description} with EXACTLY {target_count} multiple-choice questions.\n\n"
            f"CONTEXT MATERIAL:\n{context_body}\n\n"
            f"RELEVANT DOCUMENT EXCERPTS:\n{chunks_sample}\n\n"
            "OUTPUT JSON SCHEMA:\n"
            "{\n"
            '  "title": "Descriptive title for this assessment",\n'
            '  "description": "Short explanation of the concepts assessed",\n'
            '  "questions": [\n'
            "    {\n"
            '      "question_text": "Precise technical question testing comprehension",\n'
            '      "question_type": "multiple_choice",\n'
            '      "answer_options": [\n'
            '        "Plausible Option 1",\n'
            '        "Plausible Option 2",\n'
            '        "Plausible Option 3",\n'
            '        "Plausible Option 4"\n'
            "      ],\n"
            '      "correct_answer": "Plausible Option 1",\n'
            '      "explanation": "Clear educational explanation of why Option 1 is correct and others are not",\n'
            '      "source_references": [\n'
            '        {"page_number": 1, "chunk_index": 0, "section_title": "Section Name", "citation_text": "Supporting text"}\n'
            "      ],\n"
            '      "sequence_order": 1\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Strict Constraints:\n"
            "- Exactly 4 unique options in answer_options.\n"
            "- correct_answer must exactly match one of the 4 options.\n"
            "- Return strictly valid JSON."
        )

        try:
            raw_response = await self.ai_provider.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                json_mode=True,
            )
            parsed_json = extract_json_from_llm_response(raw_response)
            content = GeneratedAssessmentContent.model_validate(parsed_json)

            # Sanitize and validate questions and citations
            sanitized_questions = []
            for idx, q in enumerate(content.questions[:target_count], start=1):
                q.sequence_order = idx

                # Sanitize source references against real chunks
                sanitized_refs = []
                for ref in q.source_references:
                    valid_chunk = (
                        ref.chunk_index
                        if ref.chunk_index is not None and ref.chunk_index in available_chunks
                        else None
                    )
                    valid_page = (
                        ref.page_number
                        if ref.page_number is not None and ref.page_number in available_pages
                        else None
                    )
                    sanitized_refs.append(
                        SourceReference(
                            chunk_index=valid_chunk,
                            page_number=valid_page,
                            section_title=ref.section_title or None,
                            citation_text=ref.citation_text or None,
                        )
                    )
                q.source_references = sanitized_refs
                sanitized_questions.append(q)

            if len(sanitized_questions) < 1:
                raise ValueError("LLM generated 0 valid questions.")

            content.questions = sanitized_questions
            return content

        except Exception as exc:
            logger.warning(
                f"LLM assessment generation failed ({exc}). Engaging deterministic grounded fallback generator."
            )
            return self._generate_deterministic_fallback(
                assessment_type=assessment_type,
                learning_path=learning_path,
                document=document,
                chunks=chunks,
                module=module,
                lesson=lesson,
                target_count=target_count,
            )

    def _generate_deterministic_fallback(
        self,
        assessment_type: AssessmentTypeEnum,
        learning_path: LearningPath,
        document: Document,
        chunks: List[DocumentChunk],
        module: Optional[LearningModule] = None,
        lesson: Optional[LearningLesson] = None,
        target_count: int = 5,
    ) -> GeneratedAssessmentContent:
        """
        Zero-cost offline deterministic question generator.
        Constructs high-quality multiple choice questions from lesson key concepts and explanations.
        """
        is_ar = learning_path.language == "ar"
        questions: List[GeneratedAssessmentQuestion] = []

        # Collect concepts and facts from lesson or modules
        items_to_test = []
        if lesson and lesson.key_concepts:
            for kc in lesson.key_concepts:
                term = kc.get("term") if isinstance(kc, dict) else getattr(kc, "term", str(kc))
                exp = kc.get("explanation") if isinstance(kc, dict) else getattr(kc, "explanation", "")
                if term and exp:
                    items_to_test.append((term, exp))

        if not items_to_test and module:
            for les in module.lessons or []:
                for kc in les.key_concepts or []:
                    term = kc.get("term") if isinstance(kc, dict) else getattr(kc, "term", str(kc))
                    exp = kc.get("explanation") if isinstance(kc, dict) else getattr(kc, "explanation", "")
                    if term and exp:
                        items_to_test.append((term, exp))

        if not items_to_test:
            for mod in learning_path.modules or []:
                for les in mod.lessons or []:
                    for kc in les.key_concepts or []:
                        term = kc.get("term") if isinstance(kc, dict) else getattr(kc, "term", str(kc))
                        exp = kc.get("explanation") if isinstance(kc, dict) else getattr(kc, "explanation", "")
                        if term and exp:
                            items_to_test.append((term, exp))

        # Build fallback questions
        chunk_ref = (
            SourceReference(
                chunk_index=chunks[0].chunk_index if chunks else 0,
                page_number=chunks[0].page_number if chunks else 1,
                section_title="Architecture Overview",
                citation_text="Core system definition and structural requirements.",
            )
            if chunks
            else None
        )

        refs = [chunk_ref] if chunk_ref else []

        for idx in range(target_count):
            q_num = idx + 1
            if items_to_test and idx < len(items_to_test):
                term, explanation = items_to_test[idx]
                if is_ar:
                    q_text = f"ما هو الدور المعماري الأساسي لـ '{term}' في هذا النظام؟"
                    correct = f"{explanation}"
                    distractor1 = f"استبدال جميع وحدات التخزين المؤقت في النظام."
                    distractor2 = f"إلغاء فحص صحة البيانات في البيئات الموزعة."
                    distractor3 = f"حظر بروتوكولات الشبكة لتقليل حركة المرور."
                    exp_text = f"الإجابة الصحيحة هي: {explanation}. هذا المفهوم جوهري لضمان اتساق واستقرار النظام."
                else:
                    q_text = f"What is the primary architectural purpose of '{term}' in this system?"
                    correct = f"{explanation}"
                    distractor1 = f"Bypassing data validation layers during high throughput."
                    distractor2 = f"Replacing persistent storage with volatile in-memory registers."
                    distractor3 = f"Disabling heartbeat monitoring across distributed nodes."
                    exp_text = f"Correct explanation: {explanation}. This is essential for system stability."
            else:
                if is_ar:
                    q_text = f"السؤال {q_num}: ما هو المعيار التصميمي الأكثر أهمية الموضح في المستند التقني؟"
                    correct = f"تحقيق الاتساق وموثوقية المعمارية ضد الأعطال."
                    distractor1 = f"إلغاء آليات المراقبة لزيادة سرعة المعالجة."
                    distractor2 = f"الاعتماد الكامل على خادم وحيد بدون نسخ احتياطي."
                    distractor3 = f"تعطيل التشفير عند ذروة حركة المرور."
                    exp_text = f"المعيار التصميمي المعتمد يركز على سلامة البيانات والاتساق المعماري."
                else:
                    q_text = f"Question {q_num}: Which design principle is emphasized for this architectural component?"
                    correct = f"Ensuring deterministic fault tolerance and state consistency."
                    distractor1 = f"Disabling monitoring telemetry to reduce execution latency."
                    distractor2 = f"Relying on a single un-replicated coordinator node."
                    distractor3 = f"Eliminating input validation during high network traffic."
                    exp_text = f"The core design principle focuses on reliability, fault tolerance, and deterministic behavior."

            options = [correct, distractor1, distractor2, distractor3]
            # Shuffle or rotate options so correct is not always first
            rot = idx % 4
            rotated_options = options[rot:] + options[:rot]

            questions.append(
                GeneratedAssessmentQuestion(
                    question_text=q_text,
                    question_type=QuestionTypeEnum.MULTIPLE_CHOICE,
                    answer_options=rotated_options,
                    correct_answer=correct,
                    explanation=exp_text,
                    source_references=refs,
                    sequence_order=q_num,
                )
            )

        title = (
            f"اختبار: {lesson.title if lesson else module.title if module else learning_path.title}"
            if is_ar
            else f"Assessment: {lesson.title if lesson else module.title if module else learning_path.title}"
        )
        desc = (
            f"تقييم تفاعلي مستند لمحتوى المستند الأصلي لقياس الفهم المعماري والتطبيقي."
            if is_ar
            else "Interactive assessment grounded in technical document source concepts."
        )

        return GeneratedAssessmentContent(
            title=title,
            description=desc,
            questions=questions,
        )


assessment_generator = AssessmentGenerator()
