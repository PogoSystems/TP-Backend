from shared.value_objects.Bloom import BloomLevel
from modules.quiz_generation.domain.aggregates.answer import AnswerAggregate
from modules.quiz_generation.domain.aggregates.question import QuestionAggregate
from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate
import logging

from core.settings import settings
from modules.quiz_generation.domain.ports.context_retrieval_port import ContextRetrievalPort
from modules.quiz_generation.domain.ports.quiz_generator_port import QuizGeneratorPort
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz

from modules.quiz_generation.domain.ports.quiz_persistance_port import QuizPersistencePort
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository

logger = logging.getLogger(__name__)


class QuizGenerationService:
    """
    Application Service responsible for orchestrating the RAG Quiz Generation.
    It retrieves textual context via ContextRetrievalPort and delegates the
    quiz generation to the LLM via QuizGeneratorPort.
    """

    def __init__(
        self,
        *,
        context_retriever: ContextRetrievalPort,
        quiz_generator: QuizGeneratorPort,
        quiz_repository: QuizPersistencePort,
        stats_repository: StatsQueryRepository,
    ) -> None:
        self._context_retriever = context_retriever
        self._quiz_generator = quiz_generator
        self._quiz_repository = quiz_repository
        self._stats_repository = stats_repository

    async def generate_quiz_from_course(
        self,
        *,
        course_id: int,
        query_text: str | None = None,
        num_questions: int,
        user_id: int,
        bloom_levels: list[BloomLevel]
    ) -> GeneratedQuiz:
        """
        Generates a quiz using context retrieved by course_id.
        """
        effective_query = query_text.strip() if query_text and query_text.strip() else (
            "Resumen principal, conceptos clave y temas principales."
        )

        context_text = await self._context_retriever.get_context_from_course(
            course_id=course_id,
            query_text=effective_query,
            limit=settings.TOP_K_RETRIEVAL,
        )

        if not bloom_levels:
            bloom_levels = await self._get_weakest_bloom_levels(user_id, course_id)

        generated_quiz = await self._generate_quiz_with_llm(
            context_text=context_text,
            num_questions=num_questions,
            bloom_levels = bloom_levels,
        )

        # Map GeneratedQuiz (LLM schema) → QuizAggregate (domain)
        quiz = QuizAggregate(
            user_id=user_id,
            course_id=course_id,
            title=generated_quiz.title,
            questions=[
                QuestionAggregate(
                    text=q.text,
                    bloom_level=q.bloom_level,
                    score=q.score,
                    explanation=q.explanation,
                    answers=[
                        AnswerAggregate(
                            text=a.text,
                            is_correct=a.is_correct,
                        )
                        for a in q.answers
                    ],
                )
                for q in generated_quiz.questions
            ],
        )

        await self._quiz_repository.save(quiz)
        return generated_quiz

    async def generate_quiz_from_documents(
        self,
        *,
        title: str,
        document_ids: list[int],
        query_text: str | None = None,
        num_questions: int,
        user_id: int,
        course_id: int,
        bloom_levels: list[BloomLevel]
    ) -> QuizAggregate:
        """
        Generates a quiz using context retrieved only from specific documents.
        """
        effective_query = query_text.strip() if query_text and query_text.strip() else (
            "Resumen principal, conceptos clave y temas principales."
        )

        context_text = await self._context_retriever.get_context_from_documents(
            document_ids=document_ids,
            query_text=effective_query,
            limit=settings.TOP_K_RETRIEVAL,
            course_id=course_id,
        )

        if not bloom_levels:
            bloom_levels = await self._get_weakest_bloom_levels(user_id, course_id)


        generated_quiz = await self._generate_quiz_with_llm(
            context_text=context_text,
            num_questions=num_questions,
            bloom_levels = bloom_levels,
        )

        # Map GeneratedQuiz (LLM schema) → QuizAggregate (domain)
        quiz = QuizAggregate(
            user_id=user_id,
            course_id=course_id,
            title=title,
            questions=[
                QuestionAggregate(
                    text=q.text,
                    bloom_level=q.bloom_level,
                    score=q.score,
                    explanation=q.explanation,
                    answers=[
                        AnswerAggregate(
                            text=a.text,
                            is_correct=a.is_correct,
                        )
                        for a in q.answers
                    ],
                )
                for q in generated_quiz.questions
            ],
        )

        await self._quiz_repository.save(quiz)
        return quiz

    async def _generate_quiz_with_llm(
        self,
        *,
        context_text: str,
        num_questions: int,
        bloom_levels: list[BloomLevel],
    ) -> GeneratedQuiz:
        """
        Helper method to call the LLM adapter.
        """
        generated_quiz = await self._quiz_generator.generate_quiz_from_context(
            context_text=context_text,
            num_questions=num_questions,
            bloom_levels = bloom_levels,
        )

        return generated_quiz

    async def get_quiz_by_id(
        self,
        *,
        quiz_id: int,
    ) -> QuizAggregate:
        """
        Retrieves a quiz by its ID.
        """
        return await self._quiz_repository.get_quiz_by_id(quiz_id)

    async def get_quizzes_by_course_id(
        self,
        *,
        course_id: int,
    ) -> list[QuizAggregate]:
        """
        Retrieves all quizzes for a given course ID.
        """
        return await self._quiz_repository.get_quizzes_by_course_id(course_id)

    async def _get_weakest_bloom_levels(
        self, user_id: int, course_id: int, count: int = 1
    ) -> list[BloomLevel]:
        """
        Returns the `count` bloom levels with the lowest performance for
        the given user and course. If no stats exist, returns an empty list
        so the LLM can decide freely.
        """
        bloom_rows = await self._stats_repository.get_bloom_stats_by_course(
            user_id, course_id
        )
        if not bloom_rows:
            return []

        def pct(row: object) -> float:
            attempted = getattr(row, "questions_attempted", 0) or 0
            correct = getattr(row, "questions_correct", 0) or 0
            return (correct / attempted * 100) if attempted > 0 else 0.0

        sorted_rows = sorted(bloom_rows, key=pct)
        return [BloomLevel(getattr(r, "bloom_level")) for r in sorted_rows[:count]]