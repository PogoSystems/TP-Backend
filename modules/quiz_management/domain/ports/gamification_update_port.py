from typing import Protocol, Any

class GamificationUpdatePort(Protocol):
    async def update_gamification(self, user_id: int, action_type: str, context: dict[str, Any]) -> None:
        """
        Actualiza los datos de gamificación (streak, score, achievements)
        basado en el contexto de la acción.
        Debe aislar sus propios errores de BD para no afectar la transacción principal.
        """
        ...
