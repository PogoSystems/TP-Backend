import pytest
from modules.quiz_management.domain.aggregates.quiz import QuizAggregate


def test_quiz_requires_user_and_course() -> None:
    with pytest.raises(ValueError, match="user_id is required"):
        QuizAggregate(user_id=0, course_id=1, title="Midterm")
    with pytest.raises(ValueError, match="course_id is required"):
        QuizAggregate(user_id=1, course_id=0, title="Midterm")


def test_quiz_defaults() -> None:
    aggregate = QuizAggregate(user_id=1, course_id=1, title="Midterm")
    assert aggregate.created_at is not None
