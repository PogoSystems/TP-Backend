from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from modules.quiz_generation.domain.aggregates.answer import AnswerAggregate
from shared.value_objects.Bloom import BloomLevel




@dataclass(slots=True)
class QuestionAggregate:
    id: int | None = None
    text: str = ""
    bloom_level: str = ""
    score: int = 0
    explanation: str = ""
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )
    answers: list["AnswerAggregate"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("text is required")
        if self.bloom_level not in [item.value for item in BloomLevel]:
            raise ValueError(f"bloom_level must be one of {[item.value for item in BloomLevel]}")
        if self.score <= 0:
            raise ValueError("score must be positive")
