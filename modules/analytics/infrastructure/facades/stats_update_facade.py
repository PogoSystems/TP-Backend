from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.domain.ports.stats_command_repository import StatsCommandRepository
from modules.analytics.infrastructure.repositories.stats_repository import StatsRepository
from modules.quiz_management.domain.ports.stats_update_port import QuestionAttemptSummary


class StatsUpdateFacade:

    def __init__(self, session: AsyncSession) -> None:
        self._repo = StatsCommandRepository(session)


    async def update_stats_after_submit(self, course_id:int, question_summaries: list[QuestionAttemptSummary]
                                        ) -> None:
        attempted = len(question_summaries)
        correct = sum(1 for q in question_summaries if q.is_correct)


        await self._repo.increment_course_stats(
            course_id=course_id,
            attempted=attempted,
            correct=correct,
        )

        #  Make a group of the bloom levels before any access to the db
        bloom_counts: dict[str, tuple[int, int]] = {}
        for summary in question_summaries:
            lvl = summary.bloom_level
            prev_attempted, prev_correct = bloom_counts.get(lvl, (0, 0))
            bloom_counts[lvl] = (
                prev_attempted + 1,
                prev_correct + (1 if summary.is_correct else 0)
            )

        await self._repo.increment_bloom_stats_bulk(course_id=course_id, bloom_counts=bloom_counts)