import pytest
from modules.quiz_management.domain.aggregates.question_attempt import QuestionAttemptAggregate


def test_question_attempt_requires_quiz_attempt_and_question() -> None:
    with pytest.raises(ValueError, match="quiz_attempt_id is required"):
        QuestionAttemptAggregate(quiz_attempt_id=0, question_id=1)
    with pytest.raises(ValueError, match="question_id is required"):
        QuestionAttemptAggregate(quiz_attempt_id=1, question_id=0)


def test_question_attempt_defaults() -> None:
    aggregate = QuestionAttemptAggregate(quiz_attempt_id=1, question_id=1)
    assert aggregate.quiz_attempt_id == 1