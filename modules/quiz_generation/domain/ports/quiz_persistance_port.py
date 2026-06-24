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