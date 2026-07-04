from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.analytics.application.analytics_service import AnalyticsService
from modules.analytics.application.course_analytics_service import CourseAnalyticsService
from modules.analytics.schemas.response_schemas import UserDashboardResponse, \
    CourseAnalyticsResponse, ProgressResponse
from modules.iam.api.dependencies import CurrentUserId

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(session: Annotated[AsyncSession, Depends(get_db)]
                          ) -> AnalyticsService:
    return AnalyticsService(session)

def get_course_analytics_service(session: Annotated[AsyncSession, Depends(get_db)]
                             ) -> CourseAnalyticsService:
    return CourseAnalyticsService(session)


AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]
CourseAnalyticsSvc= Annotated[CourseAnalyticsService, Depends(get_course_analytics_service)]

@router.get(
    "/me",
    response_model=UserDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard de progreso general del usuario autenticado",
)
async def get_user_dashboard(service: AnalyticsSvc,current_user_id: CurrentUserId
                             ) -> UserDashboardResponse:
    return await service.get_user_dashboard(current_user_id)

@router.get(
    "/course/{course_id}",
    response_model=CourseAnalyticsResponse,
    summary="Analytics detallado por curso",
)
async def get_course_analytics(course_id: int, service: CourseAnalyticsSvc, current_user_id: CurrentUserId
                               ) -> CourseAnalyticsResponse:
    return await service.get_course_dashboard(course_id, current_user_id)


@router.get(
    "/progress",
    response_model=ProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Progreso del usuario en el tiempo",
)
async def get_user_progress(service: AnalyticsSvc, current_user_id: CurrentUserId, granularity: str = Query(default="week"), course_id: int | None = Query(default=None)) -> ProgressResponse:
    try:
        return await service.get_user_progress(
            user_id=current_user_id,
            granularity=granularity,
            course_id=course_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))