from sqlalchemy.ext.asyncio import AsyncSession

from modules.quiz_management.domain.aggregates import QuizAttemptAggregate, QuestionAttemptAggregate
from modules.quiz_management.infrastructure.models import QuizAttemptModel, QuestionAttemptModel


class QuizAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_attempt(self, attempt: QuizAttemptAggregate, question_attempts: list[QuestionAttemptAggregate]
                           ) -> QuizAttemptAggregate :
        """
        Persist a quiz attempt
        """

        # first save the quiz attempt to get its ID and because without a quiz attempt,
        # there is not a question_attempt
        attempt_model= QuizAttemptModel(
            user_id= attempt.user_id,
            quiz_id = attempt.quiz_id,
            total_score= attempt.total_score,
            expected_correct_answers=attempt.expected_correct_answers,
            started_at= attempt.started_at,
            submitted_at= attempt.submitted_at,
        )

        self._session.add(attempt_model)
        await self._session.flush()
        attempt.id = attempt_model.id

        for qa in question_attempts:
            qa_model= QuestionAttemptModel(
                quiz_attempt_id= attempt_model.id,
                question_id= qa.question_id,
                selected_answer_id=qa.selected_answer_id,
                is_correct= qa.is_correct,
                score_obtained=qa.score_obtained,
                answered_at= qa.answered_at
            )
            self._session.add(qa_model)

        await self._session.flush()
        return attempt

    async def get_recent_attempt(self, user_id: int) -> dict | None:
        from sqlalchemy import select, func
        from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel

        count_stmt = select(func.count(QuizAttemptModel.id)).where(QuizAttemptModel.user_id == user_id)
        count_res = await self._session.execute(count_stmt)
        total_quizzes = count_res.scalar() or 0

        stmt = (
            select(QuizAttemptModel, QuizModel.title)
            .join(QuizModel, QuizAttemptModel.quiz_id == QuizModel.id)
            .where(QuizAttemptModel.user_id == user_id)
            .order_by(QuizAttemptModel.submitted_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row:
            attempt, title = row
            return {
                "id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "quiz_title": title,
                "total_score": attempt.total_score,
                "submitted_at": attempt.submitted_at,
                "total_quizzes_completed": total_quizzes
            }
        return {"total_quizzes_completed": total_quizzes}