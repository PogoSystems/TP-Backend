from shared.value_objects.Bloom import BloomLevel
from typing import Protocol
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz


class QuizGeneratorPort(Protocol):
    """
    Port defined by the quiz_generation domain to be implemented
    by LLM adapters (such as Gemini) to generate structured quizzes.
    """

    async def generate_quiz_from_context(
        self,
        *,
        context_text: str,
        num_questions: int,
        bloom_levels: list[BloomLevel]
    ) -> GeneratedQuiz:
        """
        Generates a structured quiz from the provided document context
        using an LLM.
        """
        ...
