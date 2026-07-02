from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def increment(self, attempted: int, correct: int) -> None:
        """
        Increment the course stats counter after every submit
        """
        self.quizzes_completed += 1
        self.questions_attempted += attempted
        self.questions_correct += correct
        self.updated_at = datetime.now(timezone.utc)
