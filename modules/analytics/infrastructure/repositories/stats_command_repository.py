from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.models import CourseStatsModel, BloomStatsModel


class StatsCommandRepository:
    """
    Repository for write operations in the database
    """
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def increment_course_stats(self, course_id: int, attempted: int, correct: int
                                     ) -> None:
        """
        Upsert (INSERT + ON CONFLICT DO UPDATE)
        If there's not a value, it creates it. If there is, it increments the counters.
        One single query vs 3 queries (SELECT from, INSERT if it doesn't exist and UDATE if it exists)
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            insert(CourseStatsModel)
            .values(
                course_id=course_id,
                quizzes_completed=1,
                questions_attempted=attempted,
                questions_correct=correct,
                updated_at=now,
            )
            .on_conflict_do_update( # if a row with the same unique key already exists, update its counters instead of raising an error
                constraint="uq_course_stats_course_id",
                set_={ #what to do when the conflict occur
                    "quizzes_completed": CourseStatsModel.quizzes_completed + 1,
                    "questions_attempted": CourseStatsModel.questions_attempted + attempted,
                    "questions_correct": CourseStatsModel.questions_correct + correct,
                    "updated_at": now,
                },
            )
        )

        #send the query to the database to execution
        await self._session.execute(stmt)

    async def increment_bloom_stats_bulk(self, course_id: int, bloom_counts: dict[str, tuple[int, int]],  # bloom_level → (attempted, correct)
                                          ) -> None:
        """
        Group the bloom levels and makes an upsert for one unique level.
        Maximum 6 queries (one per Bloom level).
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
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