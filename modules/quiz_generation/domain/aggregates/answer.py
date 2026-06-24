from dataclasses import dataclass


@dataclass(slots=True)
class AnswerAggregate:
    text: str = ""
    is_correct: bool = False

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("text is required")
