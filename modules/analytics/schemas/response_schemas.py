from pydantic import BaseModel


class BloomLevelStatsResponse(BaseModel):
    bloom_level: str
    questions_attempted: int
    questions_correct: int
    percentage: float


class UserDashboardResponse(BaseModel):
    quizzes_completed: int
    questions_attempted: int
    questions_correct: int
    accuracy_percentage: float
    dominant_level: str | None
    dominant_percentage: float
    dominant_correct: int
    weak_level: str | None
    weak_percentage: float
    weak_correct: int
    bloom_breakdown: list[BloomLevelStatsResponse]