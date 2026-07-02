from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository
from modules.analytics.schemas.response_schemas import CourseAnalyticsResponse, BloomStatsResponse
from modules.analytics.application.utils import pct

class CourseAnalyticsService:

    def __init__(self, session: AsyncSession) -> None:
        self._repo = StatsQueryRepository(session)

    async def get_course_dashboard(self, course_id: int, user_id: int ) -> CourseAnalyticsResponse:

        bloom_rows = await self._repo.get_bloom_stats_by_course(user_id, course_id)

        bloom_breakdown = [
            BloomStatsResponse(
                bloom_level=r.bloom_level,
                questions_attempted=r.questions_attempted,
                questions_correct=r.questions_correct,
                percentage=pct(r.questions_correct, r.questions_attempted),
            )
            for r in bloom_rows
        ]

        active = [b for b in bloom_breakdown if b.questions_attempted > 0]

        dominant_level = max(active, key=lambda b: b.percentage, default=None)
        weak_level = min(active, key=lambda b: b.percentage, default=None)

        return CourseAnalyticsResponse(
            course_id=course_id,
            dominant_level=dominant_level.bloom_level if dominant_level else None,
            dominant_percentage=dominant_level.percentage if dominant_level else 0.0,
            dominant_correct=dominant_level.questions_correct if dominant_level else 0,
            weak_level=weak_level.bloom_level if weak_level else None,
            weak_percentage=weak_level.percentage if weak_level else 0.0,
            weak_correct=weak_level.questions_correct if weak_level else 0,
            bloom_breakdown=bloom_breakdown,
        )
