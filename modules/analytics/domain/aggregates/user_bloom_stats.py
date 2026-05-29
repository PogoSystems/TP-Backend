from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class UserBloomStatsAggregate:
    id: int | None = None
    user_id: int = 0
    course_id: int | None = None
    correct_questions: int = 0
    incorrect_questions: int = 0
    max_score: int = 0
    remember_percentage: float | None = None
    understand_percentage: float | None = None
    apply_percentage: float | None = None
    analyze_percentage: float | None = None
    evaluate_percentage: float | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id is required")