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
from modules.quiz_generation.schemas.response_schemas import QuizResponse, QuestionResponse, AnswerResponse
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
 
        return QuizResponse(
            id=quiz.id,
            title=quiz.title,
            user_id=quiz.user_id,
            course_id=quiz.course_id,
            created_at=quiz.created_at,
            questions=[
                QuestionResponse(
                    id=q.id,
                    text=q.text,
                    bloom_level=q.bloom_level,
                    score=q.score,
                    explanation=q.explanation,
                    answers=[
                        AnswerResponse(
                            id=a.id,
                            text=a.text,
                        ) for a in q.answers
                    ]
                ) for q in quiz.questions
            ]
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
