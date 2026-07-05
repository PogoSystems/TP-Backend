from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from modules.quiz_management.infrastructure.models import QuizAttemptModel
from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel

VALID_GRANULARITIES = {"week", "month", "year"}

class ProgressQueryRepository:
    """
    Read-only repository
    """
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_progress(self,user_id: int,granularity: str,course_id: int | None = None
                           ) -> list:
        if granularity not in VALID_GRANULARITIES:
            raise ValueError(f"granularity must be one of {VALID_GRANULARITIES}")

        period = func.date_trunc(granularity, QuizAttemptModel.submitted_at).label("period")

        # accuracy = SUM(total_score) / SUM(max_score) * 100
        # group by period of time to combine multiple attempts in the same week for a user correctly.
        # with SUM/SUM it weights quizzes by their maximum possible score
        accuracy = (
                func.sum(QuizAttemptModel.total_score).cast(Float)
                / func.nullif(func.sum(QuizModel.max_score), 0)
                * 100
        ).label("accuracy")

        stmt = (
            select(period, accuracy)
            .join(QuizModel, QuizAttemptModel.quiz_id == QuizModel.id) # to get the max_score
            .where(
                QuizAttemptModel.user_id == user_id,
                QuizAttemptModel.submitted_at.isnot(None),
                QuizModel.max_score.isnot(None),
                QuizModel.max_score > 0,
            )
        )

        if course_id is not None:
            stmt = stmt.where(QuizModel.course_id == course_id)

        stmt = stmt.group_by(period).order_by(period)

        result = await self._session.execute(stmt)
        return list(result.all())