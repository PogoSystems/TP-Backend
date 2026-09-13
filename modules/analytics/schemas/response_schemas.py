from datetime import datetime
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

class ProgressPoint(BaseModel):
    label: str
    accuracy: float

class ProgressResponse(BaseModel):
    granularity: str
    points: list[ProgressPoint]


# Metacognition Schemas

class MetacognitionCourseSummary(BaseModel):
    course_id: int
    course_name: str
    quizzes_evaluated: int
    calibration_accuracy_percentage: float
    bias: str


class MetacognitionSummaryResponse(BaseModel):
    calibration_accuracy_percentage: float
    average_expected: float
    average_actual: float
    bias: str
    bias_gap: float
    total_evaluated_quizzes: int
    course_breakdown: list[MetacognitionCourseSummary]


class MetacognitionRecentAttempt(BaseModel):
    quiz_id: int
    quiz_title: str
    submitted_at: datetime
    total_questions: int
    expected_correct: int
    actual_correct: int
    gap: float
    calibration_accuracy: float


class CourseMetacognitionResponse(BaseModel):
    course_id: int
    course_name: str
    calibration_accuracy_percentage: float
    average_expected: float
    average_actual: float
    bias: str
    quizzes_evaluated: int
    recent_attempts: list[MetacognitionRecentAttempt]


class BloomMetacognitionResponse(BaseModel):
    bloom_level: str
    questions_attempted: int
    actual_correct: int
    expected_correct: float
    calibration_accuracy: float
    bias: str


class MetacognitionProgressPoint(BaseModel):
    period: str
    avg_expected: float
    avg_actual: float
    calibration_accuracy: float
    quizzes_count: int


class MetacognitionProgressResponse(BaseModel):
    granularity: str
    points: list[MetacognitionProgressPoint]