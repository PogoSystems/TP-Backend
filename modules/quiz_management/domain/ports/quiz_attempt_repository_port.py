from typing import Protocol

from modules.quiz_management.domain.aggregates import QuizAttemptAggregate, QuestionAttemptAggregate


class QuizAttemptRepositoryPort(Protocol):

    async def save_attempt(self, attempt: QuizAttemptAggregate, question_attempts: list[QuestionAttemptAggregate]
                          )-> QuizAttemptAggregate:
        """
        Saves a quiz attempt and its associated question attempts.
        Returns the saved QuizAttemptAggregate with updated IDs.
        """
        ...

    async def get_recent_attempt(self, user_id: int) -> dict | None:
        ...