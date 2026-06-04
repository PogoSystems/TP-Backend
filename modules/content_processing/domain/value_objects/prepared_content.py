from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class RawContent:
    title: str
    storage_key: str
    document_type: str
    markdown: str
    page_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("title is required")
        if not self.storage_key:
            raise ValueError("storage_key is required")
        if not self.document_type:
            raise ValueError("document_type is required")
        if not self.markdown:
            raise ValueError("markdown is required")
        if self.page_count <= 0:
            raise ValueError("page_count must be positive")


@dataclass(slots=True)
class StructuredSection:
    index: int
    heading: str
    level: int
    text: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.heading:
            raise ValueError("heading is required")
        if not self.text:
            raise ValueError("text is required")
        if self.level < 0 or self.level > 6:
            raise ValueError("level must be between 0 and 6")


@dataclass(slots=True)
class PreparedDocument:
    raw: RawContent
    normalized_text: str
    sections: list[StructuredSection]

    def __post_init__(self) -> None:
        if not self.normalized_text:
            raise ValueError("normalized_text is required")
        if not self.sections:
            raise ValueError("sections are required")