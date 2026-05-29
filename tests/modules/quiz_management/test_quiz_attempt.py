import pytest
from modules.quiz_management.domain.aggregates.quiz_attempt import QuizAttemptAggregate


def test_quiz_attempt_requires_user_and_quiz() -> None:
    with pytest.raises(ValueError, match="user_id is required"):
        QuizAttemptAggregate(user_id=0, quiz_id=1)
    with pytest.raises(ValueError, match="quiz_id is required"):
        QuizAttemptAggregate(user_id=1, quiz_id=0)


def test_quiz_attempt_defaults() -> None:
    aggregate = QuizAttemptAggregate(user_id=1, quiz_id=1)
    assert aggregate.created_at is not None