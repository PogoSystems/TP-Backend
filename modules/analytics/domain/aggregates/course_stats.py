from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CourseStatsAggregate:
    id: int | None = None
    course_id: int = 0
    quizzes_completed: int = 0
    questions_attempted: int = 0
    questions_correct: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.course_id <= 0:
            raise ValueError("course_id is required")
