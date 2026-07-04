from typing import Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from modules.quiz_management.domain.ports.gamification_update_port import GamificationUpdatePort
from modules.gamification.application.gamification_update_service import GamificationUpdateService

logger = logging.getLogger(__name__)

class GamificationUpdateFacade(GamificationUpdatePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._service = GamificationUpdateService()

    async def update_gamification(self, user_id: int, action_type: str, context: dict[str, Any]) -> None:
        """
        Updates gamification stats safely using a nested transaction (savepoint).
        If an error occurs, it rolls back the savepoint but allows the main transaction to continue.
        """
        try:
            async with self._session.begin_nested():
                await self._service.process_action(user_id, action_type, context, self._session)
        except SQLAlchemyError as e:
            logger.error(f"Database error during gamification update for user {user_id}: {e}")
            # The begin_nested context manager automatically rolls back the savepoint on exception.
        except Exception as e:
            logger.error(f"Unexpected error during gamification update for user {user_id}: {e}")
