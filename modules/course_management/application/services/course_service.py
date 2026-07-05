from modules.course_management.domain.aggregates.course import CourseAggregate
from modules.course_management.domain.ports.course_port import CourseRepositoryPort
from modules.course_management.schemas import CourseCreate, CourseUpdate
from shared.exceptions import CourseNotFoundError, CourseForbiddenError


class CourseService:
    """Servicio de aplicación para la gestión de cursos.

    Contiene todos los casos de uso del módulo `course_management`.
    Depende del puerto `CourseRepositoryPort`, no de implementaciones concretas.
    """

    def __init__(self, repository: CourseRepositoryPort) -> None:
        self._repository = repository

    async def create_course(self, data: CourseCreate, current_user_id:int) -> CourseAggregate:
        """Crea un nuevo curso validando las reglas de negocio del aggregate."""
        course = CourseAggregate(
            name=data.name,
            description=data.description,
            user_id=current_user_id,
            max_score=data.max_score,
        )
        return await self._repository.save(course)

    async def get_course(self, course_id: int, current_user_id:int) -> CourseAggregate:
        """Obtiene un curso por ID.

        Raises:
            CourseNotFoundError: Si el curso no existe.
        """
        course = await self._repository.find_by_id(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        if course.user_id != current_user_id:
            raise CourseForbiddenError(course_id,current_user_id)

        return course

    async def count_courses(self, current_user_id: int) -> int:
        return await self._repository.count_by_user(current_user_id)

    async def list_courses(
        self, current_user_id:int, page: int, page_size: int
    ) -> list[CourseAggregate]:
        """Lista los cursos de un usuario con paginación basada en páginas."""
        offset = (page - 1) * page_size
        return await self._repository.find_all_by_user(
            user_id=current_user_id, offset=offset, limit=page_size
        )

    async def update_course(
        self, course_id: int, data: CourseUpdate,current_user_id:int
    ) -> CourseAggregate:
        """Actualización parcial (PATCH) de un curso.

        Solo modifica los campos incluidos en `data`; los demás se mantienen intactos.

        Raises:
            CourseNotFoundError: Si el curso no existe.
        """
        existing = await self._repository.find_by_id(course_id)
        if existing is None:
            raise CourseNotFoundError(course_id)
        if existing.user_id != current_user_id:
            raise CourseForbiddenError(course_id,current_user_id)

        updated = CourseAggregate(
            id=existing.id,
            name=data.name if data.name is not None else existing.name,
            description=data.description if data.description is not None else existing.description,
            user_id=current_user_id,
            max_score=data.max_score if data.max_score is not None else existing.max_score,
            created_at=existing.created_at,
        )
        return await self._repository.update(updated)

    async def delete_course(self, course_id: int, current_user_id:int) -> None:
        """Elimina un curso.

        Verifica la existencia antes de delegar al repositorio.

        Raises:
            CourseNotFoundError: Si el curso no existe.
        """
        existing = await self._repository.find_by_id(course_id)
        if existing is None:
            raise CourseNotFoundError(course_id)
        if existing.user_id != current_user_id:
            raise CourseForbiddenError(course_id,current_user_id)
        await self._repository.delete(course_id)
