from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.domain.aggregates.bloom_stats import BloomStatsAggregate
from modules.analytics.domain.aggregates.course_stats import CourseStatsAggregate
from modules.analytics.infrastructure.models import BloomStatsModel, CourseStatsModel


class StatsRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_course_stats(self, course_id: int) -> CourseStatsAggregate:
        model = await self._session.get(CourseStatsModel, None)
        # Busca por course_id, no por PK
        stmt = select(CourseStatsModel).where(CourseStatsModel.course_id == course_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = CourseStatsModel(course_id=course_id)
            self._session.add(model)
            await self._session.flush()

        return self._to_course_aggregate(model)

    async def save_course_stats(self, stats: CourseStatsAggregate) -> None:
        stmt = select(CourseStatsModel).where(CourseStatsModel.course_id == stats.course_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return
        model.quizzes_completed = stats.quizzes_completed
        model.questions_attempted = stats.questions_attempted
        model.questions_correct = stats.questions_correct
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def get_or_create_bloom_stats(
        self, course_id: int, bloom_level: str
    ) -> BloomStatsAggregate:
        stmt = select(BloomStatsModel).where(
            BloomStatsModel.course_id == course_id,
            BloomStatsModel.bloom_level == bloom_level,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = BloomStatsModel(course_id=course_id, bloom_level=bloom_level)
            self._session.add(model)
            await self._session.flush()

        return self._to_bloom_aggregate(model)

    async def save_bloom_stats(self, stats: BloomStatsAggregate) -> None:
        stmt = select(BloomStatsModel).where(
            BloomStatsModel.course_id == stats.course_id,
            BloomStatsModel.bloom_level == stats.bloom_level,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return
        model.questions_attempted = stats.questions_attempted
        model.questions_correct = stats.questions_correct
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def get_course_stats(self, course_id: int) -> CourseStatsAggregate | None:
        stmt = select(CourseStatsModel).where(CourseStatsModel.course_id == course_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_course_aggregate(model) if model else None

    async def get_all_bloom_stats(self, course_id: int) -> list[BloomStatsAggregate]:
        stmt = select(BloomStatsModel).where(BloomStatsModel.course_id == course_id)
        result = await self._session.execute(stmt)
        return [self._to_bloom_aggregate(m) for m in result.scalars().all()]

    @staticmethod
    def _to_course_aggregate(model: CourseStatsModel) -> CourseStatsAggregate:
        return CourseStatsAggregate(
            id=model.id,
            course_id=model.course_id,
            quizzes_completed=model.quizzes_completed,
            questions_attempted=model.questions_attempted,
            questions_correct=model.questions_correct,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_bloom_aggregate(model: BloomStatsModel) -> BloomStatsAggregate:
        return BloomStatsAggregate(
            id=model.id,
            course_id=model.course_id,
            bloom_level=model.bloom_level,
            questions_attempted=model.questions_attempted,
            questions_correct=model.questions_correct,
            updated_at=model.updated_at,
        )