import pytest
from modules.quiz_management.domain.aggregates.question import QuestionAggregate


def test_question_requires_quiz_and_text() -> None:
    with pytest.raises(ValueError, match="quiz_id is required"):
        QuestionAggregate(quiz_id=0, text="What is X?", bloom_level="remember", score=1)
    with pytest.raises(ValueError, match="text is required"):
        QuestionAggregate(quiz_id=1, text="", bloom_level="remember", score=1)


def test_question_defaults() -> None:
    aggregate = QuestionAggregate(quiz_id=1, text="What is X?", bloom_level="remember", score=1)
    assert aggregate.created_at is not None
