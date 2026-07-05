from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class QuizAttemptAggregate:
    id: int | None = None
    user_id: int = 0
    quiz_id: int = 0
    total_score: int | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id is required")
        if self.quiz_id <= 0:
            raise ValueError("quiz_id is required")