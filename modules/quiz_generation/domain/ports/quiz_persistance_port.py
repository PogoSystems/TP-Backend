from typing import Protocol

from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate

class QuizPersistencePort(Protocol):
    """Puerto de persistencia para quiz_generation.

    Define el contrato mínimo que necesita el servicio de generación:
    únicamente guardar el quiz creado por el LLM.
    La implementación concreta vive en quiz_management/infrastructure.
    """

    async def save(self, quiz: QuizAggregate) -> QuizAggregate:
        """Persiste un quiz generado y retorna el aggregate con el ID asignado."""
        ...
    
    async def get_quiz_by_id(self, quiz_id: int) -> QuizAggregate:
        """Retorna un quiz por su ID."""
        ...
    
    async def get_quizzes_by_course_id(self, course_id: int) -> list[QuizAggregate]:
        """Retorna todos los quizes de un curso."""
        ...