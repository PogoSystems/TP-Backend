from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class UserAggregate:
    id: int | None = None
    username: str = ""
    email: str = ""
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.username:
            raise ValueError("username is required")
        if not self.email:
            raise ValueError("email is required")
