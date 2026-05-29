from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class QuizAttemptAggregate:
    id: int | None = None
    user_id: int = 0
    quiz_id: int = 0
    total_score: int | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
