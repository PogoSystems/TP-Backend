from dataclasses import dataclass


@dataclass(slots=True)
class AnswerAggregate:
    id: int | None = None
    question_id: int = 0
    text: str = ""
    is_correct: bool = False

    def __post_init__(self) -> None:
        if self.question_id <= 0:
            raise ValueError("question_id is required")
        if not self.text:
            raise ValueError("text is required")
