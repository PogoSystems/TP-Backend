"""Tests unitarios para Casos de Uso - CU05: Generar Cuestionario Personalizado (quiz_generation)."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from shared.value_objects.Bloom import BloomLevel
from pydantic import ValidationError
from modules.quiz_generation.schemas.request_schemas import QuizGenerationRequest
from modules.quiz_generation.application.services.quiz_generation_service import QuizGenerationService
from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz, GeneratedQuestion, GeneratedAnswer


def make_generated_quiz() -> GeneratedQuiz:
    """Crea una respuesta simulada del generador LLM."""
    return GeneratedQuiz(
        title="Evaluación Adaptativa de Algoritmos",
        questions=[
            GeneratedQuestion(
                text="¿Qué complejidad temporal tiene la búsqueda binaria?",
                bloom_level=BloomLevel.REMEMBER,
                score=5,
                explanation="La búsqueda binaria divide el espacio a la mitad en cada paso.",
                answers=[
                    GeneratedAnswer(text="O(n)", is_correct=False),
                    GeneratedAnswer(text="O(log n)", is_correct=True),
                    GeneratedAnswer(text="O(n^2)", is_correct=False),
                ],
            ),
            GeneratedQuestion(
                text="Analice el impacto de usar listas enlazadas en lugar de arreglos.",
                bloom_level=BloomLevel.ANALYZE,
                score=10,
                explanation="Las listas enlazadas permiten inserción dinámica.",
                answers=[
                    GeneratedAnswer(text="Mejora el acceso aleatorio", is_correct=False),
                    GeneratedAnswer(text="Facilita inserción dinámica sin reasignar memoria contigua", is_correct=True),
                ],
            ),
        ],
    )


def make_mocks(**kwargs) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Crea mocks para context_retriever, quiz_generator, quiz_repository y stats_repository."""
    retriever = MagicMock()
    retriever.get_context_from_course = AsyncMock(
        return_value=kwargs.get("course_context", "Texto de contexto académico simulado.")
    )
    retriever.get_context_from_documents = AsyncMock(
        return_value=kwargs.get("doc_context", "Texto de contexto simulado recuperado.")
    )

    generator = MagicMock()
    generator.generate_quiz_from_context = AsyncMock(
        return_value=kwargs.get("generated_quiz", make_generated_quiz())
    )

    repository = MagicMock()
    repository.save = AsyncMock(return_value=None)

    stats_repository = MagicMock()
    stats_repository.get_bloom_stats_by_course = AsyncMock(return_value=[])

    return retriever, generator, repository, stats_repository


class TestCU05GenerarCuestionarioPersonalizado:
    """Pruebas unitarias asociadas al caso de uso CU05."""

    @pytest.mark.asyncio
    async def test_generate_quiz_from_documents_success(self) -> None:
        """Flujo principal CU05: Solicitud de práctica a partir de material indexado."""
        retriever, generator, repository, stats_repo = make_mocks()
        service = QuizGenerationService(
            context_retriever=retriever,
            quiz_generator=generator,
            quiz_repository=repository,
            stats_repository=stats_repo,
        )

        quiz = await service.generate_quiz_from_documents(
            title="Práctica Unidad 1",
            document_ids=[101, 102],
            query_text="Algoritmos de búsqueda",
            num_questions=2,
            user_id=5,
            course_id=1,
            bloom_levels=[BloomLevel.REMEMBER, BloomLevel.ANALYZE],
        )

        retriever.get_context_from_documents.assert_called_once_with(
            document_ids=[101, 102],
            query_text="Algoritmos de búsqueda",
            limit=5,
            course_id=1,
        )
        generator.generate_quiz_from_context.assert_called_once()
        repository.save.assert_called_once()

        assert isinstance(quiz, QuizAggregate)
        assert quiz.title == "Práctica Unidad 1"
        assert len(quiz.questions) == 2
        assert quiz.questions[0].bloom_level == BloomLevel.REMEMBER
        assert quiz.questions[1].bloom_level == BloomLevel.ANALYZE

    @pytest.mark.asyncio
    async def test_generate_quiz_from_course_success(self) -> None:
        """Generación de cuestionario a nivel del curso con consulta semántica RAG."""
        retriever, generator, repository, stats_repo = make_mocks()
        service = QuizGenerationService(
            context_retriever=retriever,
            quiz_generator=generator,
            quiz_repository=repository,
            stats_repository=stats_repo,
        )

        generated_quiz_dto = await service.generate_quiz_from_course(
            course_id=1,
            query_text=None,
            num_questions=2,
            user_id=5,
            bloom_levels=[BloomLevel.REMEMBER],
        )

        retriever.get_context_from_course.assert_called_once()
        assert generated_quiz_dto.title == "Evaluación Adaptativa de Algoritmos"
        assert len(generated_quiz_dto.questions) == 2

    @pytest.mark.asyncio
    async def test_generate_quiz_handles_llm_failure_propagation(self) -> None:
        """Flujo alternativo 5a: Caída o timeout del servicio LLM."""
        retriever, generator, repository, stats_repo = make_mocks()
        generator.generate_quiz_from_context = AsyncMock(
            side_effect=RuntimeError("El motor de IA está saturado en este momento.")
        )

        service = QuizGenerationService(
            context_retriever=retriever,
            quiz_generator=generator,
            quiz_repository=repository,
            stats_repository=stats_repo,
        )

        with pytest.raises(RuntimeError, match="saturado"):
            await service.generate_quiz_from_documents(
                title="Práctica Fallida",
                document_ids=[101],
                query_text="Conceptos",
                num_questions=2,
                user_id=5,
                course_id=1,
                bloom_levels=[BloomLevel.REMEMBER],
            )

        repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_quiz_from_documents_exceeds_max_questions_raises_error(self) -> None:
        """Verifica que al solicitar más de 25 preguntas se lance ValueError sin llamar al LLM ni guardar."""
        retriever, generator, repository, stats_repo = make_mocks()
        service = QuizGenerationService(
            context_retriever=retriever,
            quiz_generator=generator,
            quiz_repository=repository,
            stats_repository=stats_repo,
        )

        with pytest.raises(ValueError, match="El número de preguntas debe estar entre 1 y 25"):
            await service.generate_quiz_from_documents(
                title="Práctica Excesiva",
                document_ids=[101],
                query_text="Conceptos",
                num_questions=26,
                user_id=5,
                course_id=1,
                bloom_levels=[BloomLevel.REMEMBER],
            )

        generator.generate_quiz_from_context.assert_not_called()
        repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_quiz_from_course_exceeds_max_questions_raises_error(self) -> None:
        """Verifica que generate_quiz_from_course con más de 25 preguntas falle sin llamar al LLM ni guardar."""
        retriever, generator, repository, stats_repo = make_mocks()
        service = QuizGenerationService(
            context_retriever=retriever,
            quiz_generator=generator,
            quiz_repository=repository,
            stats_repository=stats_repo,
        )

        with pytest.raises(ValueError, match="El número de preguntas debe estar entre 1 y 25"):
            await service.generate_quiz_from_course(
                course_id=1,
                query_text="Conceptos",
                num_questions=26,
                user_id=5,
                bloom_levels=[BloomLevel.REMEMBER],
            )

        generator.generate_quiz_from_context.assert_not_called()
        repository.save.assert_not_called()

    def test_quiz_generation_request_schema_validation(self) -> None:
        """Verifica que el schema Pydantic rechace más de 25 preguntas y acepte valores válidos."""
        with pytest.raises(ValidationError):
            QuizGenerationRequest(
                course_id=1,
                title="Quiz Test",
                document_ids=[1],
                num_questions=26,
                bloom_levels=[BloomLevel.REMEMBER],
            )

        valid_request = QuizGenerationRequest(
            course_id=1,
            title="Quiz Test",
            document_ids=[1],
            num_questions=25,
            bloom_levels=[BloomLevel.REMEMBER],
        )
        assert valid_request.num_questions == 25

