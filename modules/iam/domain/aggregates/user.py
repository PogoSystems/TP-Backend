from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(slots=True)
class UserAggregate:
    auth_id:UUID #the id that identifies the user in the supabase auth
    name: str
    last_name: str
    college:str
    major:str
    email: str
    id: int | None = None
    created_at: datetime = field(
    default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.auth_id:
            raise ValueError("auth_id is required")
        if not self.email:
            raise ValueError("email is required")
        if not self.college:
            raise ValueError("college is required")
        if not self.major:
            raise ValueError("major is required")
