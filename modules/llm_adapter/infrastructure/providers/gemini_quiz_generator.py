import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError

from core.settings import settings
from modules.quiz_generation.domain.ports.quiz_generator_port import QuizGeneratorPort
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz
from shared.value_objects.Bloom import BloomLevel

logger = logging.getLogger(__name__)


class GeminiQuizGenerator():
    """
    Gemini implementation of the QuizGeneratorPort.
    Responsible for sending prompt and context to Gemini using Structured Output.
    """

    def __init__(self, *, client: genai.Client) -> None:
        self._client = client
        self._model = settings.GEMINI_MODEL

    async def generate_quiz_from_context(
        self,
        *,
        context_text: str,
        num_questions: int,
        bloom_levels: list[BloomLevel]
    ) -> GeneratedQuiz:
        """
        Generate structured quiz using Gemini API.
        """
        bloom_instruction = ""
        focused_bloom_levels = ""
        if bloom_levels:
            for bloom_level in bloom_levels:
                match bloom_level:
                    case BloomLevel.REMEMBER:
                        focused_bloom_levels += "- Remember: retrieve and recognize previously learned information\n"
                    case BloomLevel.UNDERSTAND:
                        focused_bloom_levels += "- Understand: explain, interpret, compare, or summarize meaning\n"
                    case BloomLevel.APPLY:
                        focused_bloom_levels += "- Apply: use learned knowledge to solve or handle a new but relevant situation\n"
                    case BloomLevel.ANALYZE:
                        focused_bloom_levels += "- Analyze: examine information to identify relationships, differences, causes, components, or implications\n"
                    case BloomLevel.EVALUATE:
                        focused_bloom_levels += "- Evaluate: make or select a judgment using explicit criteria, evidence, or justification\n"
            bloom_instruction = f"\nCRITICAL INSTRUCTION: Focus EXCLUSIVELY on these levels of Bloom's Taxonomy: {focused_bloom_levels}\n"
        prompt = f"""
You are an expert educator. Generate exactly {num_questions} quiz questions in Spanish.

Bloom level:
{bloom_instruction}

The reference material contains:
1. Syllabus objectives and competencies.
2. Course content retrieved through RAG.

Every question must:
- Align with at least one syllabus objective or competency.
- Be answerable from the provided course content.
- Match the specified Bloom cognitive level. if specified.
- Test the student's knowledge rather than the ability to recall the wording of the source.
- Avoid mentioning the reference material, documents, or text.
- Use only information supported by the provided material.

Question types: Multiple Choice or True/False.

For Multiple Choice questions, provide one unambiguously correct answer and plausible distractors based on common misunderstandings.
Avoid making the correct choice considerably longer or shorter than the distractors, try to make them similar in length and complexity.
For True/False questions, ensure the statement is clearly true or false according to the course content.

Reference material:
---
{context_text}
---

Generate the output strictly following the requested JSON schema.
"""

        try:
            # Call Gemini using async client
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedQuiz,
                    temperature=0.1,  # Low temperature for factual consistency
                ),
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response")

            logger.info("Successfully received response from Gemini API for quiz generation")
            # Parse and run Pydantic validators on our side to guarantee correctness
            return GeneratedQuiz.model_validate_json(response.text)

        except APIError as e:
            is_503 = getattr(e, "code", None) == 503 or "503" in str(e) or "UNAVAILABLE" in str(e).upper() or "HIGH DEMAND" in str(e).upper()
            if is_503 and settings.GROQ_API_KEY:
                logger.warning(
                    f"Gemini API returned 503 UNAVAILABLE. Initiating fallback to Groq ({settings.GROQ_MODEL})..."
                )
                return await self._generate_with_groq(prompt)

            logger.error(f"Gemini APIError during quiz generation: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during quiz generation: {e}")
            raise RuntimeError(f"Quiz generation failed: {e}") from e

    async def _generate_with_groq(self, prompt: str) -> GeneratedQuiz:
        """
        Fallback generator using Groq when Gemini is unavailable.
        """
        from groq import AsyncGroq

        groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        schema_json = GeneratedQuiz.model_json_schema()
        try:
            completion = await groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert educator. Return valid JSON adhering strictly to this JSON Schema:\n"
                            f"{schema_json}\n"
                            "Do not include any conversational commentary or markdown code fence blocks."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = completion.choices[0].message.content
            if not content:
                raise ValueError("Groq returned an empty response")

            clean_json = content.strip()
            if clean_json.startswith("```"):
                clean_json = clean_json.split("\n", 1)[1]
            if clean_json.endswith("```"):
                clean_json = clean_json.rsplit("```", 1)[0]
            clean_json = clean_json.strip()

            logger.info("Successfully generated quiz via Groq fallback")
            return GeneratedQuiz.model_validate_json(clean_json)
        except Exception as err:
            logger.error(f"Groq fallback failed during quiz generation: {err}")
            raise RuntimeError(f"Fallback to Groq failed after Gemini 503: {err}") from err

