from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.gamification.application.gamification_service import GamificationService
from modules.gamification.schemas.response_schemas import GamificationResponse
from modules.iam.api.dependencies import CurrentUserId

router = APIRouter(prefix="/gamification", tags=["gamification"])


def get_gamification_service(
    session: Annotated[AsyncSession, Depends(get_db)]
) -> GamificationService:
    return GamificationService(session)


GamificationSvc = Annotated[GamificationService, Depends(get_gamification_service)]


@router.get(
    "/me",
    response_model=GamificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtiene la información de gamificación del usuario autenticado",
)
async def get_user_gamification(
    service: GamificationSvc, current_user_id: CurrentUserId
) -> GamificationResponse:
    return await service.get_user_gamification_data(current_user_id)
