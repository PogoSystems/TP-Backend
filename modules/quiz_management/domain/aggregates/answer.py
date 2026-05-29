from dataclasses import dataclass


@dataclass(slots=True)
class AnswerAggregate:
    id: int | None = None
    question_id: int = 0
    text: str = ""
    is_correct: bool = False
