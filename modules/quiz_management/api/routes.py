from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.analytics.infrastructure.facades.stats_update_facade import StatsUpdateFacade
from modules.gamification.infrastructure.facades.gamification_update_facade import GamificationUpdateFacade
from modules.iam.api.dependencies import CurrentUserId
from modules.quiz_management.application.services.quiz_attempt_service import QuizAttemptService
from modules.quiz_management.infrastructure.facades.quiz_read_facade import QuizReadFacade
from modules.quiz_management.infrastructure.repositories.quiz_attempt_repository import QuizAttemptRepository
from modules.quiz_management.schemas.request_schemas import SubmitQuizRequest
from modules.quiz_management.schemas.response_schemas import AttemptResultResponse, RecentQuizAttemptResponse

router = APIRouter(prefix="/quizzes", tags=["quiz-attempts"])


def get_quiz_attempt_service(session: Annotated[AsyncSession, Depends(get_db)],
                             ) -> QuizAttemptService:
    return QuizAttemptService(
        quiz_read=QuizReadFacade(session),
        attempt_repository=QuizAttemptRepository(session),
        stats_updater=StatsUpdateFacade(session),
        gamification_updater=GamificationUpdateFacade(session)
    )


AttemptSvc = Annotated[QuizAttemptService, Depends(get_quiz_attempt_service)]


@router.post(
    "/{quiz_id}/submit",
    response_model=AttemptResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar el intento de un quiz",
)

async def submit_quiz(quiz_id: int, request: SubmitQuizRequest, service: AttemptSvc, current_user_id: CurrentUserId,
                      ) -> AttemptResultResponse:
    try:
        return await service.submit_quiz(
            quiz_id=quiz_id,
            user_id=current_user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get(
    "/recent",
    response_model=RecentQuizAttemptResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Obtener el último intento de quiz completado",
)
async def get_recent_attempt(service: AttemptSvc, current_user_id: CurrentUserId) -> RecentQuizAttemptResponse | None:
    attempt_dict = await service.get_recent_attempt(current_user_id)
    if attempt_dict:
        return RecentQuizAttemptResponse(**attempt_dict)
    return None