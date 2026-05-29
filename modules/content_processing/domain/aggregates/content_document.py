from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ContentDocumentAggregate:
    id: int | None = None
    course_id: int = 0
    user_id: int = 0
    title: str = ""
    storage_key: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.course_id <= 0:
            raise ValueError("course_id is required")
        if self.user_id <= 0:
            raise ValueError("user_id is required")
        if not self.title:
            raise ValueError("title is required")
        if not self.storage_key:
            raise ValueError("storage_key is required")
