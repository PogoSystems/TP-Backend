from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.models import CourseStatsModel, BloomStatsModel


class StatsCommandRepository:
    """
    Repository for only write operations in the database
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment_course_stats(self, course_id: int, attempted: int, correct: int,
                                     ) -> None:
        """
        on_conflict_do_update == UPSERT
        This validates if the course stats table already exists.
        If not, creates one.
        If yes, updates the counters.
        Makes only one query
        """
        now = datetime.now(timezone.utc)
        stmt = (
            insert(CourseStatsModel)
            .values(
                course_id=course_id,
                quizzes_completed=1,
                questions_attempted=attempted,
                questions_correct=correct,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_course_stats_course_id",
                set_={
                    "quizzes_completed": CourseStatsModel.quizzes_completed + 1,
                    "questions_attempted": CourseStatsModel.questions_attempted + attempted,
                    "questions_correct": CourseStatsModel.questions_correct + correct,
                    "updated_at": now,
                },
            )
        )
        await self._session.execute(stmt)

    async def increment_bloom_stats_bulk(self, course_id: int, bloom_counts: dict[str, tuple[int, int]],  # bloom_level → (attempted, correct)
                                         ) -> None:
        """
        UPSERT for multiple bloom levels.
        It groups multiple levels and makes the upsert (SELECT+UPDATE)
        in a single query per level, maximum 6 queries (one per Bloom level).
        """
        now = datetime.now(timezone.utc)
        for bloom_level, (attempted, correct) in bloom_counts.items():
            stmt = (
                insert(BloomStatsModel)
                .values(
                    course_id=course_id,
                    bloom_level=bloom_level,
                    questions_attempted=attempted,
                    questions_correct=correct,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_bloom_stats_course_bloom",
                    set_={
                        "questions_attempted": BloomStatsModel.questions_attempted + attempted,
                        "questions_correct": BloomStatsModel.questions_correct + correct,
                        "updated_at": now,
                    },
                )
            )
            await self._session.execute(stmt)