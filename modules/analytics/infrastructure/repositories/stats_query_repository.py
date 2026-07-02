from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.models import BloomStatsModel, CourseStatsModel
from modules.course_management.infrastructure.models import CourseModel


class StatsQueryRepository:
    """
    Query only repository to build the analytics dashboard
    """
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_totals(self, user_id: int) -> dict:
        """
        Return the aggregated metrics for the given user
        """
        # coalesce is for, if sum is null (no stats yet), return 0 instead
        totals_stmt = (
            select(
                func.coalesce(func.sum(CourseStatsModel.quizzes_completed), 0).label("quizzes_completed"),
                func.coalesce(func.sum(CourseStatsModel.questions_attempted), 0).label("questions_attempted"),
                func.coalesce(func.sum(CourseStatsModel.questions_correct), 0).label("questions_correct"),
            )
            .join(CourseModel, CourseStatsModel.course_id == CourseModel.id)
            .where(CourseModel.user_id == user_id)
        )
        result = await self._session.execute(totals_stmt)
        return dict(result.mappings().one()) # return the single aggregated row as a dictionary.

    async def get_bloom_breakdown(self, user_id: int) -> list:
        """
        Get the bloom_stats for each level for all the courses of the user
        """
        stmt = (
            select(
                BloomStatsModel.bloom_level,
                func.sum(BloomStatsModel.questions_attempted).label("questions_attempted"),
                func.sum(BloomStatsModel.questions_correct).label("questions_correct"),
            )
            .join(CourseModel, BloomStatsModel.course_id == CourseModel.id)
            .where(CourseModel.user_id == user_id)
            .group_by(BloomStatsModel.bloom_level)
        )
        result = await self._session.execute(stmt)
        return list(result.all()) # to the result a list

    async def get_course_performance(self, user_id: int) -> list:
        """
        Get the performance for each course of the user
        """
        stmt = (
            select(
                CourseModel.id.label("course_id"),
                CourseModel.name.label("course_name"),
                func.coalesce(CourseStatsModel.quizzes_completed, 0).label("quizzes_completed"),
                func.coalesce(CourseStatsModel.questions_attempted, 0).label("questions_attempted"),
                func.coalesce(CourseStatsModel.questions_correct, 0).label("questions_correct"),
            )
            .outerjoin(CourseStatsModel, CourseStatsModel.course_id == CourseModel.id)
            .where(CourseModel.user_id == user_id)
            .order_by(CourseModel.name)
        )
        result = await self._session.execute(stmt)
        return list(result.all())


    async def get_bloom_stats_by_course(self, user_id: int, course_id: int) -> list:
        """
        Get the bloom_stats for a single course of the user
        """
        stmt = (
            select(
                BloomStatsModel.bloom_level,
                func.sum(BloomStatsModel.questions_attempted).label("questions_attempted"),
                func.sum(BloomStatsModel.questions_correct).label("questions_correct"),
            )
            .join(CourseModel, CourseModel.id == BloomStatsModel.course_id)
            .where(
                CourseModel.user_id == user_id,
                CourseModel.id == course_id
            )
            .group_by(BloomStatsModel.bloom_level)
        )
        result = await self._session.execute(stmt)
        return list(result.all())
