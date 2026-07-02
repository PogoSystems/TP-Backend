from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.analytics.application.analytics_service import AnalyticsService
from modules.analytics.schemas.response_schemas import UserDashboardResponse, BloomLevelStatsResponse
from modules.iam.api.dependencies import CurrentUserId

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(session: Annotated[AsyncSession, Depends(get_db)]
                          ) -> AnalyticsService:
    return AnalyticsService(session)


AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get(
    "/me",
    response_model=UserDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard de progreso general del usuario autenticado",
)
async def get_user_dashboard(service: AnalyticsSvc,current_user_id: CurrentUserId
                             ) -> UserDashboardResponse:
    return await service.get_user_dashboard(current_user_id)