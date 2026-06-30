from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class BloomStatsAggregate:
    id: int | None = None
    course_id: int = 0
    bloom_level: str = ""
    questions_attempted: int = 0
    questions_correct: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.course_id <= 0:
            raise ValueError("course_id is required")
        if not self.bloom_level:
            raise ValueError("bloom_level is required")
