"""Tests unitarios para CourseService.

El repositorio se mockea completamente para aislar la lógica de negocio del acceso a datos.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.course_management.application.services.course_service import CourseService
from modules.course_management.domain.aggregates.course import CourseAggregate
from modules.course_management.schemas import CourseCreate, CourseUpdate
from shared.exceptions import CourseNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_course(
    course_id: int = 1,
    name: str = "Cálculo I",
    description: str | None = None,
    user_id: int = 10,
    max_score: int | None = None,
) -> CourseAggregate:
    """Crea un CourseAggregate de prueba con valores por defecto."""
    return CourseAggregate(
        id=course_id,
        name=name,
        description=description,
        user_id=user_id,
        max_score=max_score,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_repository(**kwargs) -> MagicMock:
    """Crea un mock del repositorio. Permite sobrescribir métodos vía kwargs."""
    repo = MagicMock()
    repo.save = AsyncMock(return_value=kwargs.get("save", None))
    repo.find_by_id = AsyncMock(return_value=kwargs.get("find_by_id", None))
    repo.find_all_by_user = AsyncMock(return_value=kwargs.get("find_all_by_user", []))
    repo.update = AsyncMock(return_value=kwargs.get("update", None))
    repo.delete = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# create_course
# ---------------------------------------------------------------------------


class TestCreateCourse:
    @pytest.mark.asyncio
    async def test_create_course_calls_repository_and_returns_aggregate(self) -> None:
        """El servicio debe delegar la persistencia al repositorio y retornar el aggregate."""
        expected = make_course()
        repo = make_repository(save=expected)
        service = CourseService(repo)

        result = await service.create_course(
            CourseCreate(name="Cálculo I", user_id=10)
        )

        repo.save.assert_called_once()
        assert result.name == "Cálculo I"
        assert result.user_id == 10

    @pytest.mark.asyncio
    async def test_create_course_propagates_all_fields(self) -> None:
        """Los campos opcionales se pasan correctamente al aggregate."""
        expected = make_course(description="Intro al cálculo", max_score=100)
        repo = make_repository(save=expected)
        service = CourseService(repo)

        result = await service.create_course(
            CourseCreate(
                name="Cálculo I",
                user_id=10,
                description="Intro al cálculo",
                max_score=100,
            )
        )

        assert result.description == "Intro al cálculo"
        assert result.max_score == 100


# ---------------------------------------------------------------------------
# get_course
# ---------------------------------------------------------------------------


class TestGetCourse:
    @pytest.mark.asyncio
    async def test_get_existing_course_returns_aggregate(self) -> None:
        """Cuando el repositorio encuentra el curso, se retorna el aggregate."""
        expected = make_course(course_id=5)
        repo = make_repository(find_by_id=expected)
        service = CourseService(repo)

        result = await service.get_course(5)

        repo.find_by_id.assert_awaited_once_with(5)
        assert result.id == 5

    @pytest.mark.asyncio
    async def test_get_nonexistent_course_raises_course_not_found_error(self) -> None:
        """Cuando el repositorio retorna None, se lanza CourseNotFoundError."""
        repo = make_repository(find_by_id=None)
        service = CourseService(repo)

        with pytest.raises(CourseNotFoundError) as exc_info:
            await service.get_course(99)

        assert exc_info.value.course_id == 99


# ---------------------------------------------------------------------------
# list_courses
# ---------------------------------------------------------------------------


class TestListCourses:
    @pytest.mark.asyncio
    async def test_list_courses_passes_correct_offset_and_limit(self) -> None:
        """La paginación calcula correctamente el offset a partir de page y page_size."""
        repo = make_repository(find_all_by_user=[make_course(), make_course(course_id=2)])
        service = CourseService(repo)

        results = await service.list_courses(user_id=10, page=2, page_size=5)

        # page=2, page_size=5 => offset=5, limit=5
        repo.find_all_by_user.assert_awaited_once_with(user_id=10, offset=5, limit=5)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_courses_returns_empty_list_when_no_courses(self) -> None:
        """Retorna lista vacía si el usuario no tiene cursos."""
        repo = make_repository(find_all_by_user=[])
        service = CourseService(repo)

        results = await service.list_courses(user_id=99, page=1, page_size=20)

        assert results == []


# ---------------------------------------------------------------------------
# update_course
# ---------------------------------------------------------------------------


class TestUpdateCourse:
    @pytest.mark.asyncio
    async def test_update_course_applies_partial_changes(self) -> None:
        """Solo los campos enviados en CourseUpdate deben ser modificados."""
        original = make_course(name="Cálculo I", description="Descripción original", max_score=50)
        updated_aggregate = make_course(name="Cálculo II", description="Descripción original", max_score=50)

        repo = make_repository(find_by_id=original, update=updated_aggregate)
        service = CourseService(repo)

        result = await service.update_course(1, CourseUpdate(name="Cálculo II"))

        # Verificar que el aggregate pasado al repositorio tiene el nombre actualizado
        saved_aggregate: CourseAggregate = repo.update.call_args[0][0]
        assert saved_aggregate.name == "Cálculo II"
        assert saved_aggregate.description == "Descripción original"
        assert saved_aggregate.max_score == 50

    @pytest.mark.asyncio
    async def test_update_nonexistent_course_raises_course_not_found_error(self) -> None:
        """Si el curso no existe, se lanza CourseNotFoundError sin llamar a update."""
        repo = make_repository(find_by_id=None)
        service = CourseService(repo)

        with pytest.raises(CourseNotFoundError):
            await service.update_course(999, CourseUpdate(name="Nuevo nombre"))

        repo.update.assert_not_called()


# ---------------------------------------------------------------------------
# delete_course
# ---------------------------------------------------------------------------


class TestDeleteCourse:
    @pytest.mark.asyncio
    async def test_delete_existing_course_calls_repository(self) -> None:
        """El servicio llama al repositorio para eliminar el curso existente."""
        existing = make_course(course_id=3)
        repo = make_repository(find_by_id=existing)
        service = CourseService(repo)

        await service.delete_course(3)

        repo.delete.assert_awaited_once_with(3)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_course_raises_course_not_found_error(self) -> None:
        """Si el curso no existe, se lanza CourseNotFoundError sin llamar a delete."""
        repo = make_repository(find_by_id=None)
        service = CourseService(repo)

        with pytest.raises(CourseNotFoundError) as exc_info:
            await service.delete_course(42)

        assert exc_info.value.course_id == 42
        repo.delete.assert_not_called()
