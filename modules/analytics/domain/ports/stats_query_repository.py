from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.models import CourseStatsModel, BloomStatsModel


class StatsQueryRepository:
    """
    Repository for only read queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_aggregated_stats_by_user(self, user_id: int) -> dict:
        """
        Add course_stats and bloom_stats of all the courses to a user in one query.
        One for all the courses and one for the bloom level.
        """
        # Total stats for the user (sum of all courses)
        from modules.course_management.infrastructure.models import CourseModel

        totals_stmt = (
            select(
                func.sum(CourseStatsModel.quizzes_completed).label("quizzes_completed"),
                func.sum(CourseStatsModel.questions_attempted).label("questions_attempted"),
                func.sum(CourseStatsModel.questions_correct).label("questions_correct"),
            )
            .join(CourseModel, CourseStatsModel.course_id == CourseModel.id)
            .where(CourseModel.user_id == user_id)
        )
        totals_result = await self._session.execute(totals_stmt)
        totals = totals_result.one()

        # Bloom stats for all the courses
        bloom_stmt = (
            select(
                BloomStatsModel.bloom_level,
                func.sum(BloomStatsModel.questions_attempted).label("questions_attempted"),
                func.sum(BloomStatsModel.questions_correct).label("questions_correct"),
            )
            .join(CourseModel, BloomStatsModel.course_id == CourseModel.id)
            .where(CourseModel.user_id == user_id)
            .group_by(BloomStatsModel.bloom_level)
        )
        bloom_result = await self._session.execute(bloom_stmt)
        bloom_rows = bloom_result.all()

        return {
            "totals": totals,
            "bloom": bloom_rows,
        }