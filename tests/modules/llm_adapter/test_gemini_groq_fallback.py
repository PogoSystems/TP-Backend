from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from google.genai.errors import APIError

from core.settings import settings
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import GeminiQuizGenerator
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz, GeneratedQuestion, GeneratedAnswer
from shared.value_objects.Bloom import BloomLevel


DUMMY_QUIZ_JSON = """
{
    "title": "Test Quiz",
    "questions": [
        {
            "text": "¿Qué es una User Story?",
            "bloom_level": "remember",
            "score": 10,
            "explanation": "Es una explicación breve.",
            "answers": [
                {"text": "Una breve descripción de requerimiento", "is_correct": true},
                {"text": "Un diagrama UML", "is_correct": false}
            ]
        }
    ]
}
"""


@pytest.mark.asyncio
async def test_fallback_triggered_on_503(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_123")
    monkeypatch.setattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")

    mock_gemini_client = MagicMock()
    # Simulate Gemini 503 error
    error_503 = APIError(503, {"error": {"code": 503, "message": "This model is currently experiencing high demand. 503 UNAVAILABLE"}})
    mock_gemini_client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    generator = GeminiQuizGenerator(client=mock_gemini_client)

    # Mock AsyncGroq
    mock_groq_instance = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = f"```json\n{DUMMY_QUIZ_JSON}\n```"
    mock_completion = MagicMock(choices=[mock_choice])
    mock_groq_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("groq.AsyncGroq", return_value=mock_groq_instance) as mock_groq_cls:
        quiz = await generator.generate_quiz_from_context(
            context_text="Dummy context",
            num_questions=1,
            bloom_levels=[BloomLevel.REMEMBER],
        )

        assert isinstance(quiz, GeneratedQuiz)
        assert quiz.title == "Test Quiz"
        assert len(quiz.questions) == 1
        assert quiz.questions[0].bloom_level == BloomLevel.REMEMBER
        mock_groq_cls.assert_called_once_with(api_key="gsk_test_key_123")
        mock_groq_instance.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_fallback_without_groq_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    mock_gemini_client = MagicMock()
    error_503 = APIError(503, {"error": {"code": 503, "message": "503 UNAVAILABLE"}})
    mock_gemini_client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    generator = GeminiQuizGenerator(client=mock_gemini_client)

    with pytest.raises(RuntimeError, match="Gemini API error"):
        await generator.generate_quiz_from_context(
            context_text="Dummy context",
            num_questions=1,
            bloom_levels=[],
        )


@pytest.mark.asyncio
async def test_no_fallback_on_400_error(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_123")

    mock_gemini_client = MagicMock()
    error_400 = APIError(400, {"error": {"code": 400, "message": "Bad Request"}})
    mock_gemini_client.aio.models.generate_content = AsyncMock(side_effect=error_400)


    generator = GeminiQuizGenerator(client=mock_gemini_client)

    with pytest.raises(RuntimeError, match="Gemini API error"):
        await generator.generate_quiz_from_context(
            context_text="Dummy context",
            num_questions=1,
            bloom_levels=[],
        )
