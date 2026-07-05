from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class AchievementAggregate:
    id: int | None = None
    name: str = ""
    img_url: str = ""
    description: str = ""
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")
        if not self.img_url:
            raise ValueError("img_url is required")
        if not self.description:
            raise ValueError("description is required")