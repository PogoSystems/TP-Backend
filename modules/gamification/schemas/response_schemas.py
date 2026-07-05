from datetime import datetime
from pydantic import BaseModel


class StatsResponse(BaseModel):
    current_streak: int
    best_streak: int
    highest_score: int
    achievements_unlocked: int
    achievements_total: int


class AchievementResponse(BaseModel):
    id: int
    name: str
    description: str
    img_url: str
    unlocked: bool
    unlocked_at: datetime | None
    progress_current: int | None
    progress_target: int | None


class GamificationResponse(BaseModel):
    stats: StatsResponse
    weekly_activity: list[bool] | None
    achievements: list[AchievementResponse]

class RecentAchievementResponse(BaseModel):
    achievement: AchievementResponse | None
    current_streak: int
