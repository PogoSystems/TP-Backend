from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.analytics.application.analytics_service import AnalyticsService
from modules.analytics.application.course_analytics_service import CourseAnalyticsService
from modules.analytics.application.metacognition_service import MetacognitionService
from modules.analytics.schemas.response_schemas import (
    BloomMetacognitionResponse,
    BloomStatsResponse,
    CourseAnalyticsResponse,
    CourseMetacognitionResponse,
    MetacognitionProgressResponse,
    MetacognitionSummaryResponse,
    ProgressResponse,
    UserDashboardResponse,
)
from modules.iam.api.dependencies import CurrentUserId

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_analytics_service(session: Annotated[AsyncSession, Depends(get_db)]
                          ) -> AnalyticsService:
    return AnalyticsService(session)

def get_course_analytics_service(session: Annotated[AsyncSession, Depends(get_db)]
                             ) -> CourseAnalyticsService:
    return CourseAnalyticsService(session)

def get_metacognition_service(session: Annotated[AsyncSession, Depends(get_db)]
                              ) -> MetacognitionService:
    return MetacognitionService(session)


AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]
CourseAnalyticsSvc = Annotated[CourseAnalyticsService, Depends(get_course_analytics_service)]
MetacognitionSvc = Annotated[MetacognitionService, Depends(get_metacognition_service)]

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
    "/summary/bloom",
    response_model=list[BloomStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Resumen del nivel cognitivo de Bloom",
)
async def get_bloom_summary(service: AnalyticsSvc, current_user_id: CurrentUserId) -> list[BloomStatsResponse]:
    return await service.get_bloom_summary(current_user_id)

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


@router.get(
    "/metacognition/summary",
    response_model=MetacognitionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Resumen global de precisión metacognitiva y sesgo del estudiante",
)
async def get_metacognition_summary(
    service: MetacognitionSvc,
    current_user_id: CurrentUserId,
) -> MetacognitionSummaryResponse:
    return await service.get_summary(current_user_id)


@router.get(
    "/metacognition/course/{course_id}",
    response_model=CourseMetacognitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Metacognición detallada e historial de intentos por curso",
)
async def get_course_metacognition(
    course_id: int,
    service: MetacognitionSvc,
    current_user_id: CurrentUserId,
) -> CourseMetacognitionResponse:
    return await service.get_course_detail(current_user_id, course_id)


@router.get(
    "/metacognition/bloom",
    response_model=list[BloomMetacognitionResponse],
    status_code=status.HTTP_200_OK,
    summary="Comparativa metacognitiva proporcional por nivel de Bloom",
)
async def get_bloom_metacognition(
    service: MetacognitionSvc,
    current_user_id: CurrentUserId,
    course_id: int | None = Query(default=None),
) -> list[BloomMetacognitionResponse]:
    return await service.get_bloom_breakdown(current_user_id, course_id=course_id)


@router.get(
    "/metacognition/progress",
    response_model=MetacognitionProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Evolución temporal de la precisión y brecha metacognitiva",
)
async def get_metacognition_progress(
    service: MetacognitionSvc,
    current_user_id: CurrentUserId,
    granularity: str = Query(default="week"),
    course_id: int | None = Query(default=None),
) -> MetacognitionProgressResponse:
    try:
        return await service.get_progress(
            user_id=current_user_id,
            granularity=granularity,
            course_id=course_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))