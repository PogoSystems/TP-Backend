from pydantic import BaseModel


class BloomStatsResponse(BaseModel):
    """
    Global metric
    Represents how the user performs in each Bloom level across all courses
    """
    bloom_level: str
    questions_attempted: int
    questions_correct: int
    percentage: float

class CoursePerformanceResponse(BaseModel):
    """
    Global metric
    Represents the progress of a user in a specific course
    """
    course_id: int
    course_name: str
    quizzes_completed: int
    accuracy_percentage: float

class UserDashboardResponse(BaseModel):
    """
    Global analytics dashboard for a single user
    """
    quizzes_completed: int
    questions_attempted: int
    questions_correct: int
    dominant_level: str | None
    dominant_percentage: float
    dominant_correct: int
    weak_level: str | None
    weak_percentage: float
    weak_correct: int
    bloom_breakdown: list[BloomStatsResponse]
    course_performance: list[CoursePerformanceResponse]
    overall_accuracy:float
    most_practiced_level: str | None
    most_practiced_attempted: int


class CourseAnalyticsResponse(BaseModel):
    """
    Analytics metrics for a single course
    """
    course_id: int
    dominant_level: str | None
    dominant_percentage: float
    dominant_correct: int
    weak_level: str | None
    weak_percentage: float
    weak_correct: int
    bloom_breakdown: list[BloomStatsResponse]