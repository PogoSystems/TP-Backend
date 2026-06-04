from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class QuizSourceDocumentAggregate:
    id: int | None = None
    quiz_id: int = 0
    document_id: int = 0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.quiz_id <= 0:
            raise ValueError("quiz_id is required")
        if self.document_id <= 0:
            raise ValueError("document_id is required")