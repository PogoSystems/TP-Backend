from dataclasses import dataclass, field
from datetime import datetime


ALLOWED_BLOOM_LEVELS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


@dataclass(slots=True)
class QuestionAggregate:
    id: int | None = None
    quiz_id: int = 0
    text: str = ""
    bloom_level: str = ""
    score: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.quiz_id <= 0:
            raise ValueError("quiz_id is required")
        if not self.text:
            raise ValueError("text is required")
        if self.bloom_level not in ALLOWED_BLOOM_LEVELS:
            raise ValueError(f"bloom_level must be one of {sorted(ALLOWED_BLOOM_LEVELS)}")
        if self.score <= 0:
            raise ValueError("score must be positive")
