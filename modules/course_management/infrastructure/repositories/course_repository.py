from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from modules.course_management.domain.aggregates.course import CourseAggregate
from modules.course_management.infrastructure.models import CourseModel


class CourseRepository:
    """Implementación SQLAlchemy async del repositorio de cursos.

    Gestiona la persistencia de `CourseAggregate` usando `CourseModel` como
    capa ORM. Mantiene el mapeo ORM↔Domain aislado en métodos privados.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def save(self, course: CourseAggregate) -> CourseAggregate:
        """Persiste un nuevo curso y retorna el aggregate con el ID asignado."""
        model = self._to_model(course)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_aggregate(model)

    async def find_by_id(self, course_id: int) -> CourseAggregate | None:
        """Retorna el aggregate del curso o None si no existe."""
        model = await self._session.get(CourseModel, course_id)
        if model is None:
            return None
        return self._to_aggregate(model)

    async def find_all_by_user(
        self, user_id: int, offset: int, limit: int
    ) -> list[CourseAggregate]:
        """Lista cursos de un usuario con paginación por offset/limit.

        Evita N+1 al cargar todos los registros en una sola consulta.
        """
        stmt = (
            select(CourseModel)
            .where(CourseModel.user_id == user_id)
            .offset(offset)
            .limit(limit)
            .order_by(CourseModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_aggregate(m) for m in result.scalars().all()]

    async def update(self, course: CourseAggregate) -> CourseAggregate:
        """Actualiza un curso existente y retorna el aggregate actualizado."""
        model = await self._session.get(CourseModel, course.id)
        if model is None:
            return course  # El servicio ya validó la existencia; no debería llegar aquí.
        model.name = course.name
        model.description = course.description
        model.max_score = course.max_score
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_aggregate(model)

    async def delete(self, course_id: int) -> None:
        """Elimina el curso con el ID dado."""
        stmt = delete(CourseModel).where(CourseModel.id == course_id)
        await self._session.execute(stmt)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_aggregate(model: CourseModel) -> CourseAggregate:
        return CourseAggregate(
            id=model.id,
            name=model.name,
            description=model.description,
            user_id=model.user_id,
            max_score=model.max_score,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_model(aggregate: CourseAggregate) -> CourseModel:
        return CourseModel(
            name=aggregate.name,
            description=aggregate.description,
            user_id=aggregate.user_id,
            max_score=aggregate.max_score,
        )
