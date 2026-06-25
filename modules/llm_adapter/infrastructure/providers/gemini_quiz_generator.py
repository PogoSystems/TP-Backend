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
        if bloom_levels:
            bloom_str = ", ".join([level.value for level in bloom_levels])
            bloom_instruction = f"\nCRITICAL INSTRUCTION: Focus EXCLUSIVELY on these levels of Bloom's Taxonomy: {bloom_str}\n"
        prompt = f"""
You are an expert educator. Generate a quiz containing exactly {num_questions} questions using the bloom taxonomy based strictly on the following reference material.

{bloom_instruction}

The reference material is divided into two parts:
1. The syllabus objectives and competencies.
2. The actual course content (RAG Context).

CRITICAL INSTRUCTION: Ensure that every generated question aligns perfectly with the syllabus objectives, while extracting the specific factual answers from the course content.

The questions in the quiz can be one of two types: Multiple Choice or True/False.

The questions MUST be in spanish

DO NOT include in the questions frases like "according to the reference material" or "based on the text". Just ask the question directly.

Reference material (RAG Context):
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
            logger.error(f"Gemini APIError during quiz generation: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during quiz generation: {e}")
            raise RuntimeError(f"Quiz generation failed: {e}") from e
