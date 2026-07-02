from pydantic import BaseModel


class BloomLevelStatsResponse(BaseModel):
    bloom_level: str
    questions_attempted: int
    questions_correct: int
    percentage: float

class CoursePerformanceResponse(BaseModel):
    course_id: int
    course_name: str
    quizzes_completed: int
    accuracy_percentage: float

class UserDashboardResponse(BaseModel):
    quizzes_completed: int
    questions_attempted: int
    questions_correct: int
    dominant_level: str | None
    dominant_percentage: float
    dominant_correct: int
    weak_level: str | None
    weak_percentage: float
    weak_correct: int
    bloom_breakdown: list[BloomLevelStatsResponse]
    course_performance: list[CoursePerformanceResponse]
    overall_accuracy:float
    most_practiced_level: str | None
    most_practiced_attempted: int