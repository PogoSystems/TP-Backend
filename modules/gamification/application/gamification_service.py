from sqlalchemy.ext.asyncio import AsyncSession

from modules.gamification.infrastructure.repositories.gamification_query_repository import GamificationQueryRepository
from modules.gamification.schemas.response_schemas import (
    GamificationResponse,
    StatsResponse,
    AchievementResponse,
)


class GamificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GamificationQueryRepository(session)

    async def get_user_gamification_data(self, user_id: int) -> GamificationResponse:
        await self._repo.ensure_user_achievements(user_id)
        
        stats_data = await self._repo.get_user_stats(user_id)
        achievements_data = await self._repo.get_achievements(user_id)

        stats_response = StatsResponse(
            current_streak=stats_data["current_streak"],
            best_streak=stats_data["best_streak"],
            highest_score=stats_data["highest_score"],
            achievements_unlocked=stats_data["achievements_unlocked"],
            achievements_total=stats_data["achievements_total"],
        )

        achievements_response = [
            AchievementResponse(**ach) for ach in achievements_data
        ]

        return GamificationResponse(
            stats=stats_response,
            weekly_activity=None,
            achievements=achievements_response,
        )
