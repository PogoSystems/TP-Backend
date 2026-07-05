from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class QuestionAttemptAggregate:
    id: int | None = None
    quiz_attempt_id: int | None = None
    question_id: int = 0
    selected_answer_id: int | None = None
    is_correct: bool | None = None
    score_obtained: int | None = None
    answered_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.question_id <= 0:
            raise ValueError("question_id is required")
        if self.selected_answer_id <= 0:
            raise ValueError("selected_answer_id is required")
