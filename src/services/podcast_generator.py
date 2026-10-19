"""
TechSift AI - Podcast Script Generation Service.
Generates structured, grounded two-speaker technical dialogues using the Gemini AI Provider.
"""

import json
import logging
import re
from typing import Any, Dict, Optional
from src.core.exceptions import AIProviderException
from src.models.document import Document
from src.models.summary import Summary
from src.schemas.audio import AudioLanguageEnum, PodcastScript, PodcastTurn
from src.services.ai_provider import AIProvider, GeminiProvider

logger = logging.getLogger(__name__)


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """Extracts and parses JSON object from LLM response text."""
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


class PodcastGenerator:
    """Produces grounded dual-speaker technical educational dialogues."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or GeminiProvider()

    def _build_context(self, document: Document, summary: Optional[Summary]) -> str:
        """Constructs grounded context, favoring existing summary data to avoid token waste."""
        if summary and summary.content_data:
            data = summary.content_data
            exec_summary = data.get("executive_summary", "")
            concepts = data.get("main_concepts", [])
            concepts_text = "\n".join(
                f"- {c.get('term', '')}: {c.get('definition', '')}" for c in concepts
            )
            findings = "\n".join(f"- {f}" for f in data.get("key_findings", []))
            takeaways = "\n".join(f"- {t}" for f in [data.get("key_takeaways", [])] for t in f)
            arch = data.get("architecture_overview") or ""

            context_parts = [
                f"DOCUMENT TITLE: {document.filename}",
                f"EXECUTIVE SUMMARY:\n{exec_summary}",
            ]
            if concepts_text:
                context_parts.append(f"CORE CONCEPTS:\n{concepts_text}")
            if arch:
                context_parts.append(f"ARCHITECTURE:\n{arch}")
            if findings:
                context_parts.append(f"KEY FINDINGS:\n{findings}")
            if takeaways:
                context_parts.append(f"KEY TAKEAWAYS:\n{takeaways}")

            return "\n\n".join(context_parts)

        # Fallback to extracted document text (capped to 6000 chars for safety)
        raw_text = document.extracted_text or ""
        return f"DOCUMENT TITLE: {document.filename}\n\nDOCUMENT CONTENT:\n{raw_text[:6000]}"

    def _build_system_instruction(self, language: AudioLanguageEnum) -> str:
        if language == AudioLanguageEnum.AR:
            return (
                "You are a Senior Technical Podcast Producer and AI Systems Specialist. "
                "Your mission is to generate an educational, conversational podcast script between two engineers: "
                "Host (المقدم - Alex/طارق) and Co-host (المحاور - Sarah/نور).\n\n"
                "CRITICAL BILINGUAL RULES FOR ARABIC:\n"
                "- Write clear, professional Modern Standard Arabic (الفصحى الحديثة).\n"
                "- PRESERVE all technical terms, code keywords, API names, protocols, and architecture acronyms "
                "in English alongside Arabic (e.g. 'خوارزمية Raft', 'FastAPI', 'SQLite', 'ACID').\n"
                "- Structure the episode into 4 to 8 turns:\n"
                "  1. Host introduces the technical problem and context.\n"
                "  2. Co-host asks an insightful question about trade-offs or implementation.\n"
                "  3. Host breaks down the architecture and mechanics.\n"
                "  4. Co-host summarizes practical engineering takeaways.\n\n"
                "STRICT GROUNDING:\n"
                "- Rely EXCLUSIVELY on the provided document context. Do NOT invent facts or citations.\n"
                "- Output ONLY a valid JSON object matching the required schema."
            )
        else:
            return (
                "You are a Senior Technical Podcast Producer and AI Systems Specialist. "
                "Your mission is to generate an educational, conversational podcast script between two engineers: "
                "Host (Alex) and Co-host (Sarah).\n\n"
                "STRUCTURE (4 to 8 turns):\n"
                "1. Host introduces the technical problem and architectural context.\n"
                "2. Co-host asks an insightful question about trade-offs, constraints, or edge cases.\n"
                "3. Host breaks down the mechanics and design decisions.\n"
                "4. Co-host summarizes practical engineering takeaways.\n\n"
                "STRICT GROUNDING:\n"
                "- Rely EXCLUSIVELY on the provided document context. Do NOT invent facts or citations.\n"
                "- Output ONLY a valid JSON object matching the required schema."
            )

    async def generate_script(
        self,
        document: Document,
        summary: Optional[Summary],
        language: AudioLanguageEnum,
        host_voice: str,
        cohost_voice: str,
    ) -> PodcastScript:
        """Generates a structured podcast script validated with Pydantic."""
        context = self._build_context(document, summary)
        system_instruction = self._build_system_instruction(language)

        prompt = (
            f"SOURCE MATERIAL:\n{context}\n\n"
            "TASK: Generate a podcast dialogue script conforming to this exact JSON structure:\n"
            "{\n"
            '  "title": "Engaging Episode Title",\n'
            f'  "language": "{language.value}",\n'
            '  "host_role": "Host (Alex)",\n'
            '  "cohost_role": "Co-host (Sarah)",\n'
            '  "turns": [\n'
            '    {\n'
            '      "turn": 1,\n'
            '      "speaker": "Host",\n'
            f'      "voice": "{host_voice}",\n'
            '      "text": "Introductory statement..."\n'
            '    },\n'
            '    {\n'
            '      "turn": 2,\n'
            '      "speaker": "Co-host",\n'
            f'      "voice": "{cohost_voice}",\n'
            '      "text": "Insightful question..."\n'
            '    }\n'
            '  ],\n'
            '  "source_references": ["Reference 1", "Reference 2"]\n'
            "}\n\n"
            "Respond ONLY with the JSON object."
        )

        try:
            raw_response = await self.ai_provider.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
            )
            data = extract_json_from_llm_response(raw_response)

            # Ensure voices in turns match the designated host/cohost voices
            turns_data = data.get("turns", [])
            for turn in turns_data:
                speaker_str = str(turn.get("speaker", "")).lower()
                if "host" in speaker_str and "co" not in speaker_str and "محاور" not in speaker_str:
                    turn["voice"] = host_voice
                    turn["speaker"] = "Host" if language == AudioLanguageEnum.EN else "المقدم"
                else:
                    turn["voice"] = cohost_voice
                    turn["speaker"] = "Co-host" if language == AudioLanguageEnum.EN else "المحاور"

            data["turns"] = turns_data
            data["language"] = language.value
            return PodcastScript.model_validate(data)

        except Exception as exc:
            logger.warning(
                f"LLM podcast script generation encountered an issue ({exc}). "
                "Engaging deterministic grounded fallback script generator per AGENTS.md rule 2."
            )
            try:
                return self._generate_fallback_script(
                    document=document,
                    summary=summary,
                    language=language,
                    host_voice=host_voice,
                    cohost_voice=cohost_voice,
                )
            except Exception as fallback_exc:
                logger.error(f"Fallback podcast script generation also failed: {fallback_exc}")
                raise AIProviderException(
                    f"Failed to generate structured podcast script: {str(exc)}"
                ) from exc

    def _generate_fallback_script(
        self,
        document: Document,
        summary: Optional[Summary],
        language: AudioLanguageEnum,
        host_voice: str,
        cohost_voice: str,
    ) -> PodcastScript:
        """
        Deterministic, zero-cost grounded fallback dialogue generator.
        Guarantees that audio generation never completely crashes due to
        temporary LLM network timeouts or rate limits (per AGENTS.md deterministic fallback rule).
        """
        if language == AudioLanguageEnum.AR:
            title = f"تحليل معماري: {document.filename}"
            host_name = "المقدم"
            cohost_name = "المحاور"

            if summary and summary.content_data:
                data = summary.content_data
                exec_sum = data.get("executive_summary", "")
                concepts = data.get("main_concepts", [])
                findings = data.get("key_findings", [])
                takeaways = data.get("key_takeaways", [])

                c1 = concepts[0].get("term", "") + ": " + concepts[0].get("definition", "") if concepts else ""
                c2 = concepts[1].get("term", "") + ": " + concepts[1].get("definition", "") if len(concepts) > 1 else ""
                f1 = findings[0] if findings else ""
                t1 = takeaways[0] if takeaways else ""

                turns = [
                    PodcastTurn(
                        turn=1,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"أهلاً بكم في بودكاست تيك سيفت التقني. نستعرض اليوم تحليلاً معمارياً لمستند: {document.filename}. {exec_sum[:280]}.",
                    ),
                    PodcastTurn(
                        turn=2,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="مرحباً بك. ما هي أهم المفاهيم التقنية والأسس الهندسية التي يقوم عليها هذا النظام؟",
                    ),
                    PodcastTurn(
                        turn=3,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"يرتكز النظام على عدة مبادئ معمارية أساسية. أولاً: {c1}. " + (f"وثانياً: {c2}. " if c2 else "") + (f"ومن أبرز النتائج الهندسية: {f1}." if f1 else ""),
                    ),
                    PodcastTurn(
                        turn=4,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="هذا توضيح دقيق ومفيد. وما هي أهم التوصيات العملية والخلاصات الهندسية للمطورين؟",
                    ),
                    PodcastTurn(
                        turn=5,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"الخلاصة الأساسية تكمن في إدارة المفاضلات التقنية بحذر، مع مراعاة القيود التشغيلية. {t1}.",
                    ),
                    PodcastTurn(
                        turn=6,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="خلاصة ممتازة تساعد في اتخاذ القرارات المعمارية السليمة. شكراً لكم على المتابعة، وإلى اللقاء في حلقة قادمة.",
                    ),
                ]
            else:
                raw_preview = (document.extracted_text or "")[:400].replace("\n", " ")
                turns = [
                    PodcastTurn(
                        turn=1,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"أهلاً بكم في بودكاست تيك سيفت التقني. نستعرض اليوم ملف: {document.filename}. {raw_preview}.",
                    ),
                    PodcastTurn(
                        turn=2,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="ما هي أبرز الجوانب المعمارية والتصميمية التي يتناولها هذا المستند؟",
                    ),
                    PodcastTurn(
                        turn=3,
                        speaker=host_name,
                        voice=host_voice,
                        text="يقدم المستند مواصفات هندسية تهدف لتحقيق التوافق والأداء المستقر مع معايير الأنظمة الحديثة.",
                    ),
                    PodcastTurn(
                        turn=4,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="شكراً لك على هذا الملخص المفيد، ونلقاكم في مناقشة تقنية جديدة.",
                    ),
                ]

        else:
            title = f"Architectural Deep Dive: {document.filename}"
            host_name = "Host"
            cohost_name = "Co-host"

            if summary and summary.content_data:
                data = summary.content_data
                exec_sum = data.get("executive_summary", "")
                concepts = data.get("main_concepts", [])
                findings = data.get("key_findings", [])
                takeaways = data.get("key_takeaways", [])

                c1 = concepts[0].get("term", "") + ": " + concepts[0].get("definition", "") if concepts else ""
                c2 = concepts[1].get("term", "") + ": " + concepts[1].get("definition", "") if len(concepts) > 1 else ""
                f1 = findings[0] if findings else ""
                t1 = takeaways[0] if takeaways else ""

                turns = [
                    PodcastTurn(
                        turn=1,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"Welcome to TechSift Deep Dives. Today we are breaking down the technical specifications of {document.filename}. {exec_sum[:280]}.",
                    ),
                    PodcastTurn(
                        turn=2,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="Great to be here. What are the key architectural mechanisms and engineering principles defined in this document?",
                    ),
                    PodcastTurn(
                        turn=3,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"The architecture is grounded on several core components. First, {c1}. " + (f"Additionally, {c2}. " if c2 else "") + (f"Key finding: {f1}." if f1 else ""),
                    ),
                    PodcastTurn(
                        turn=4,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="That makes total sense. And what are the actionable engineering takeaways and trade-offs for engineers?",
                    ),
                    PodcastTurn(
                        turn=5,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"The primary takeaway is balancing latency and reliability guarantees. {t1}.",
                    ),
                    PodcastTurn(
                        turn=6,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="A fantastic summary for systems architects. Thank you everyone for listening, and join us on our next technical deep dive.",
                    ),
                ]
            else:
                raw_preview = (document.extracted_text or "")[:400].replace("\n", " ")
                turns = [
                    PodcastTurn(
                        turn=1,
                        speaker=host_name,
                        voice=host_voice,
                        text=f"Welcome to TechSift Deep Dives. Today we're reviewing {document.filename}. {raw_preview}.",
                    ),
                    PodcastTurn(
                        turn=2,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="What are the main engineering considerations and design patterns discussed in this document?",
                    ),
                    PodcastTurn(
                        turn=3,
                        speaker=host_name,
                        voice=host_voice,
                        text="The document details implementation specifications aimed at ensuring scalable and resilient system behavior.",
                    ),
                    PodcastTurn(
                        turn=4,
                        speaker=cohost_name,
                        voice=cohost_voice,
                        text="Thank you for this concise overview, and see you all in the next episode.",
                    ),
                ]

        return PodcastScript(
            title=title,
            language=language,
            host_role=host_name,
            cohost_role=cohost_name,
            turns=turns,
            source_references=[f"Document: {document.filename}"],
        )
