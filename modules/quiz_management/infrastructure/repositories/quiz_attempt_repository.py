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