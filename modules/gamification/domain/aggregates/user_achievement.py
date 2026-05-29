from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserAchievementAggregate:
    user_id: int = 0
    achievement_id: int = 0
    unlocked_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id is required")
        if self.achievement_id <= 0:
            raise ValueError("achievement_id is required")