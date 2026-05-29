from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CourseAggregate:
    id: int | None = None
    name: str = ""
    description: str | None = None
    user_id: int = 0
    max_score: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")
        if self.user_id <= 0:
            raise ValueError("user_id is required")
