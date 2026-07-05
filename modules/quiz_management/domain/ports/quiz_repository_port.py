from typing import Protocol

from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate


class QuizRepositoryPort(Protocol):
    """Puerto de lectura/gestión para quiz_management.

    Define el contrato que necesita el servicio de gestión de quizzes:
    consultar, actualizar y eliminar quizzes ya creados por quiz_generation.
    La creación (save) NO es responsabilidad de este módulo.
    """

    async def find_by_id(self, quiz_id: int) -> QuizAggregate | None:
        """Retorna el aggregate del quiz o None si no existe."""
        ...

    async def find_all_by_course(
        self, course_id: int, offset: int, limit: int
    ) -> list[QuizAggregate]:
        """Lista quizzes de un curso con paginación por offset/limit."""
        ...

    async def find_all_by_user(
        self, user_id: int, offset: int, limit: int
    ) -> list[QuizAggregate]:
        """Lista quizzes de un usuario con paginación por offset/limit."""
        ...

    async def delete(self, quiz_id: int) -> None:
        """Elimina el quiz con el ID dado."""
        ...
