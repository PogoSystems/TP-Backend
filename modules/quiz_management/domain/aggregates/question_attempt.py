from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class QuestionAttemptAggregate:
    id: int | None = None
    quiz_attempt_id: int = 0
    question_id: int = 0
    selected_answer_id: int | None = None
    is_correct: bool | None = None
    score_obtained: int | None = None
    answered_at: datetime | None = None
