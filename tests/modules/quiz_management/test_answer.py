import pytest
from modules.quiz_management.domain.aggregates.answer import AnswerAggregate


def test_answer_requires_question_and_text() -> None:
    with pytest.raises(ValueError, match="question_id is required"):
        AnswerAggregate(question_id=0, text="42", is_correct=True)
    with pytest.raises(ValueError, match="text is required"):
        AnswerAggregate(question_id=1, text="", is_correct=True)


def test_answer_defaults() -> None:
    aggregate = AnswerAggregate(question_id=1, text="42", is_correct=True)
    assert aggregate.question_id == 1
