from modules.quiz_generation.schemas.response_schemas import QuizzesByCourseResponse, QuizSummaryResponse
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient

from core.db.database import get_db
from core.settings import settings
from core.supabase import get_supabase_client
from modules.content_processing.application.services.content_retrieval_facade import ContentRetrievalFacade
from modules.content_processing.infrastructure.storage.supabase_storage import SupabaseStorageAdapter
from modules.iam.api.dependencies import CurrentUserId
from modules.llm_adapter.infrastructure.providers.gemini_embedding_provider import GeminiEmbeddingProvider
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import GeminiQuizGenerator
from modules.quiz_generation.infrastructure.repositories.quiz_persistence_repository import QuizPersistenceRepository
from modules.quiz_generation.application.services.quiz_generation_service import QuizGenerationService
from modules.quiz_generation.schemas.response_schemas import QuizResponse, QuestionResponse, AnswerResponse, QuizzesByCourseResponse, QuizSummaryResponse
from modules.quiz_generation.schemas.request_schemas import QuizGenerationRequest
from shared.exceptions import DocumentNotFoundError, DocumentProcessingError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def get_quiz_generation_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    supabase: Annotated[AsyncClient, Depends(get_supabase_client)],
) -> QuizGenerationService:
    """Dependency injection factory for QuizGenerationService."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    embedding_provider = GeminiEmbeddingProvider(client=client)
    quiz_generator = GeminiQuizGenerator(client=client)

    storage = SupabaseStorageAdapter(supabase)
    
    context_retriever = ContentRetrievalFacade(
        session=session,
        embedding_provider=embedding_provider,
        storage=storage,
    )

    quiz_repository = QuizPersistenceRepository(session)

    return QuizGenerationService(
        context_retriever=context_retriever,
        quiz_generator=quiz_generator,
        quiz_repository=quiz_repository,

    )


QuizSvc = Annotated[QuizGenerationService, Depends(get_quiz_generation_service)]


@router.post(
    "",
    response_model=QuizResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar un cuestionario a partir de documentos",
    description=(
        "Recibe una lista de IDs de documentos y genera un cuestionario usando RAG. "
        "Los documentos en estado PENDING se procesan automáticamente antes de la generación."
    ),
)
async def generate_quiz(
    request: QuizGenerationRequest,
    service: QuizSvc,
    current_user_id: CurrentUserId
) -> QuizResponse:
    try:
        quiz = await service.generate_quiz_from_documents(
            title=request.title,
            document_ids=request.document_ids,
            query_text=request.query_text,
            num_questions=request.num_questions,
            user_id= current_user_id,
            course_id=request.course_id,
            bloom_levels = request.bloom_levels,
        )
        assert quiz.id is not None
        assert quiz.title is not None
        assert quiz.questions is not None
 
        question_responses = []
        for q in quiz.questions:
            assert q.id is not None, "Question ID must not be None"
            answer_responses = []
            for a in q.answers:
                assert a.id is not None, "Answer ID must not be None"
                answer_responses.append(
                    AnswerResponse(
                        id=a.id,
                        text=a.text,
                        is_correct=a.is_correct
                    )
                )
            question_responses.append(
                QuestionResponse(
                    id=q.id,
                    text=q.text,
                    bloom_level=q.bloom_level,
                    score=q.score,
                    explanation=q.explanation,
                    answers=answer_responses
                )
            )

        return QuizResponse(
            id=quiz.id,
            title=quiz.title,
            user_id=quiz.user_id,
            course_id=quiz.course_id,
            created_at=quiz.created_at,
            questions=question_responses
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error("Quiz generation runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

@router.get(
    "/{quiz_id}",
    response_model=QuizResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener un cuestionario por su ID",
    description=(
        "Recibe un ID de cuestionario y retorna el cuestionario correspondiente."
    ),
)
async def get_quiz_by_id(
    quiz_id: int,
    service: QuizSvc,
) -> QuizResponse:
    try:
        quiz = await service.get_quiz_by_id(quiz_id=quiz_id)
        assert quiz.id is not None
        assert quiz.title is not None
        assert quiz.questions is not None

        question_responses = []
        for q in quiz.questions:
            assert q.id is not None, "Question ID must not be None"
            answer_responses = []
            for a in q.answers:
                assert a.id is not None, "Answer ID must not be None"
                answer_responses.append(
                    AnswerResponse(
                        id=a.id,
                        text=a.text,
                        is_correct=a.is_correct
                    )
                )
            question_responses.append(
                QuestionResponse(
                    id=q.id,
                    text=q.text,
                    bloom_level=q.bloom_level,
                    score=q.score,
                    explanation=q.explanation,
                    answers=answer_responses
                )
            )

        assert quiz.id is not None
        assert quiz.title is not None
        return QuizResponse(
            id=quiz.id,
            title=quiz.title,
            user_id=quiz.user_id,
            course_id=quiz.course_id,
            created_at=quiz.created_at,
            questions=question_responses
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=QuizzesByCourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener todos los cuestionarios de un curso",
    description=(
        "Recibe un ID de curso y retorna todos los cuestionarios correspondientes."
    ),
)
async def get_quizzes_by_course_id(
    course_id: int,
    service: QuizSvc,
) -> QuizzesByCourseResponse:
    """
    Retrieves all quizzes for a given course ID.
    """
    quizzes = await service.get_quizzes_by_course_id(course_id=course_id)
    
    summaries: list[QuizSummaryResponse] = []
    for quiz in quizzes:
        assert quiz.id is not None
        assert quiz.title is not None
        summaries.append(
            QuizSummaryResponse(
                id=quiz.id,
                title=quiz.title,
                created_at=quiz.created_at,
            )
        )
        
    return QuizzesByCourseResponse(quizzes=summaries)
