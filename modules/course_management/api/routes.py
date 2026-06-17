from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.course_management.application.services.course_service import CourseService
from modules.course_management.infrastructure.repositories.course_repository import (
    CourseRepository,
)
from modules.course_management.schemas import CourseCreate, CourseResponse, CourseUpdate
from shared.exceptions import CourseNotFoundError

router = APIRouter(prefix="/courses", tags=["courses"])


# ------------------------------------------------------------------
# Dependency injection helpers
# ------------------------------------------------------------------


def get_course_service(session: Annotated[AsyncSession, Depends(get_db)]) -> CourseService:
    """Construye el servicio inyectando el repositorio concreto."""
    repository = CourseRepository(session)
    return CourseService(repository)


CourseSvc = Annotated[CourseService, Depends(get_course_service)]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo curso",
)
async def create_course(payload: CourseCreate, service: CourseSvc) -> CourseResponse:
    """Crea un curso y retorna la representación completa del recurso creado."""
    course = await service.create_course(payload)
    assert course.id is not None
    return CourseResponse(
        id=course.id,
        name=course.name,
        description=course.description,
        user_id=course.user_id,
        max_score=course.max_score,
        created_at=course.created_at,
    )


@router.get(
    "",
    response_model=list[CourseResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar cursos de un usuario",
)
async def list_courses(
    service: CourseSvc,
    user_id: int = Query(..., gt=0, description="ID del usuario propietario"),
    page: int = Query(1, ge=1, description="Número de página (inicia en 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Cantidad de resultados por página"),
) -> list[CourseResponse]:
    """Retorna los cursos del usuario indicado con paginación."""
    courses = await service.list_courses(user_id=user_id, page=page, page_size=page_size)
    return [
        CourseResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            user_id=c.user_id,
            max_score=c.max_score,
            created_at=c.created_at,
        )
        for c in courses
    ]


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener un curso por ID",
)
async def get_course(course_id: int, service: CourseSvc) -> CourseResponse:
    """Retorna el detalle de un curso específico."""
    try:
        course = await service.get_course(course_id)
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    assert course.id is not None
    return CourseResponse(
        id=course.id,
        name=course.name,
        description=course.description,
        user_id=course.user_id,
        max_score=course.max_score,
        created_at=course.created_at,
    )


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente un curso",
)
async def update_course(
    course_id: int, payload: CourseUpdate, service: CourseSvc
) -> CourseResponse:
    """Actualiza solo los campos enviados en el body (PATCH semántico)."""
    try:
        course = await service.update_course(course_id, payload)
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    assert course.id is not None
    return CourseResponse(
        id=course.id,
        name=course.name,
        description=course.description,
        user_id=course.user_id,
        max_score=course.max_score,
        created_at=course.created_at,
    )


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un curso",
)
async def delete_course(course_id: int, service: CourseSvc) -> None:
    """Elimina permanentemente el curso indicado."""
    try:
        await service.delete_course(course_id)
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
