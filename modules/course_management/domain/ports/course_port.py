from typing import Protocol

from modules.course_management.domain.aggregates.course import CourseAggregate


class CourseRepositoryPort(Protocol):
    """Interfaz (Puerto) que define el contrato de acceso a datos para cursos.

    La capa de aplicación depende de este protocolo, no de la implementación
    concreta de SQLAlchemy, manteniendo el dominio libre de infraestructura.
    """

    async def save(self, course: CourseAggregate) -> CourseAggregate:
        """Persiste un nuevo curso y retorna el aggregate con el ID asignado."""
        ...

    async def find_by_id(self, course_id: int) -> CourseAggregate | None:
        """Retorna el aggregate del curso o None si no existe."""
        ...

    async def find_all_by_user(
        self, user_id: int, offset: int, limit: int
    ) -> list[CourseAggregate]:
        """Lista cursos de un usuario con soporte de paginación por offset/limit."""
        ...

    async def update(self, course: CourseAggregate) -> CourseAggregate:
        """Actualiza un curso existente y retorna el aggregate actualizado."""
        ...

    async def delete(self, course_id: int) -> None:
        """Elimina el curso con el ID dado."""
        ...
