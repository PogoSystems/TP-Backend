from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class QuizAggregate:
    id: int | None = None
    user_id: int = 0
    course_id: int = 0
    title: str | None = None
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id is required")
        if self.course_id <= 0:
            raise ValueError("course_id is required")
