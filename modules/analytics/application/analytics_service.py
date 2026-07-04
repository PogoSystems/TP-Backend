import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.repositories.progress_query_repository import ProgressQueryRepository
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository
from modules.analytics.schemas.response_schemas import UserDashboardResponse, BloomStatsResponse, \
    CoursePerformanceResponse, ProgressResponse, ProgressPoint
from modules.analytics.application.utils import pct

class AnalyticsService:

    def __init__(self, session: AsyncSession) -> None:
        self._repo = StatsQueryRepository(session)
        self._progress_repo = ProgressQueryRepository(session)

    async def get_user_dashboard(self, user_id: int) -> UserDashboardResponse:
        """
        Use the stats from a specific user to calculate the metrics
        """

        # asyncio execute all the queries at the same time
        # this helps to reduce the time of execution, since the queries are independent
        totals, bloom_rows, course_rows = await asyncio.gather(
            self._repo.get_user_totals(user_id),
            self._repo.get_bloom_breakdown(user_id),
            self._repo.get_course_performance(user_id),
        )

        # from each row (bloom level), create a BloomStatsResponse object with the stats from that level
        bloom_breakdown = [
            BloomStatsResponse(
                bloom_level=row.bloom_level,
                questions_attempted=row.questions_attempted,
                questions_correct=row.questions_correct,
                percentage=pct(row.questions_correct, row.questions_attempted),
            )
            for row in bloom_rows
        ]

        # if a level doesn't have any questions
        active = [b for b in bloom_breakdown if b.questions_attempted > 0]

        # levels with more/less correct answers
        dominant_level = max(active, key=lambda b: b.percentage, default=None)
        weak_level = min(active, key=lambda b: b.percentage, default=None)
        most_practiced = max(active, key=lambda b: b.questions_attempted, default=None)

        # course performance (global)
        course_performance = [
            CoursePerformanceResponse(
                course_id=row.course_id,
                course_name=row.course_name,
                quizzes_completed=row.quizzes_completed,
                accuracy_percentage=pct(row.questions_correct, row.questions_attempted,
                )
            )
            for row in course_rows
        ]

        total_attempted = totals["questions_attempted"]
        total_correct = totals["questions_correct"]
        quizzes_completed = totals["quizzes_completed"]
        overall_accuracy = pct(total_correct, total_attempted)
        return UserDashboardResponse(
            quizzes_completed=quizzes_completed,
            questions_attempted=total_attempted,
            questions_correct=total_correct,
            dominant_level=dominant_level.bloom_level if dominant_level else None,
            dominant_percentage=dominant_level.percentage if dominant_level else 0.0,
            dominant_correct=dominant_level.questions_correct if dominant_level else 0,
            weak_level=weak_level.bloom_level if weak_level else None,
            weak_percentage=weak_level.percentage if weak_level else 0.0,
            weak_correct=weak_level.questions_correct if weak_level else 0,
            bloom_breakdown=bloom_breakdown,
            course_performance=course_performance,
            overall_accuracy=overall_accuracy,
            most_practiced_level=most_practiced.bloom_level if most_practiced else None,
            most_practiced_attempted=most_practiced.questions_attempted if most_practiced else 0,
        )

    async def get_user_progress(self, user_id: int, granularity: str, course_id: int | None = None
                                ) -> ProgressResponse:
        rows = await self._progress_repo.get_progress(user_id=user_id,granularity=granularity,course_id=course_id)

        return ProgressResponse(
            granularity=granularity,
            points=[
                ProgressPoint(
                    label=row.period.date().isoformat(),
                    accuracy=round(float(row.accuracy), 1) if row.accuracy is not None else 0.0,
                )
                for row in rows
            ],
        )
