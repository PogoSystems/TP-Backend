from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class QuestionAggregate:
    id: int | None = None
    quiz_id: int = 0
    text: str = ""
    bloom_level: str = ""
    score: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
