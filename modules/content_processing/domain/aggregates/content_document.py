from dataclasses import dataclass, field
from datetime import datetime, timezone

from modules.content_processing.domain.value_objects.processing_status import ProcessingStatus


@dataclass(slots=True)
class ContentDocumentAggregate:
    id: int | None = None
    course_id: int = 0
    user_id: int = 0
    title: str = ""
    storage_key: str = ""
    document_type: str = ""
    syllabus: bool = False
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processed_at:datetime | None = None
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    ALLOWED_TYPES = {"pdf", "docx"}

    def __post_init__(self) -> None:
        if self.course_id <= 0:
            raise ValueError("course_id is required")
        if self.user_id <= 0:
            raise ValueError("user_id is required")
        if not self.title:
            raise ValueError("title is required")
        if not self.storage_key:
            raise ValueError("storage_key is required")

    """
    The changes of status are business rules
    """
    def mark_processing(self) -> None:
        self.processing_status = ProcessingStatus.PROCESSING

    def mark_completed(self) -> None:
        self.processing_status = ProcessingStatus.COMPLETED

    def mark_failed(self) -> None:
        self.processing_status = ProcessingStatus.FAILED

    @property
    def is_processed(self) -> bool:
        return self.processing_status == ProcessingStatus.COMPLETED