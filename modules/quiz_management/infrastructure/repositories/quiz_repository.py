from datetime import timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate
from modules.quiz_management.infrastructure.models import QuizModel


class QuizRepository:
    """Repositorio de lectura y gestión para quiz_management.

    Satisface QuizRepositoryPort: consulta, lista y elimina quizzes
    ya persistidos por quiz_generation. No crea quizzes nuevos.

    Al separar en microservicios, este módulo consumiría los datos
    mediante la API de quiz_generation en lugar de acceder a la BD
    directamente.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, quiz_id: int) -> QuizAggregate | None:
        """Retorna el aggregate del quiz o None si no existe."""
        model = await self._session.get(QuizModel, quiz_id)
        if model is None:
            return None
        return self._to_aggregate(model)

    async def find_all_by_course(
        self, course_id: int, offset: int, limit: int
    ) -> list[QuizAggregate]:
        """Lista quizzes de un curso con paginación por offset/limit."""
        stmt = (
            select(QuizModel)
            .where(QuizModel.course_id == course_id)
            .offset(offset)
            .limit(limit)
            .order_by(QuizModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_aggregate(m) for m in result.scalars().all()]

    async def find_all_by_user(
        self, user_id: int, offset: int, limit: int
    ) -> list[QuizAggregate]:
        """Lista quizzes de un usuario con paginación por offset/limit."""
        stmt = (
            select(QuizModel)
            .where(QuizModel.user_id == user_id)
            .offset(offset)
            .limit(limit)
            .order_by(QuizModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_aggregate(m) for m in result.scalars().all()]

    async def delete(self, quiz_id: int) -> None:
        """Elimina el quiz con el ID dado."""
        stmt = delete(QuizModel).where(QuizModel.id == quiz_id)
        await self._session.execute(stmt)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_aggregate(model: QuizModel) -> QuizAggregate:
        return QuizAggregate(
            id=model.id,
            user_id=model.user_id,
            course_id=model.course_id,
            title=model.title,
            created_at=model.created_at.replace(tzinfo=timezone.utc),
        )
