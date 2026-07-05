from datetime import datetime

from pydantic import BaseModel

class RecentQuizAttemptResponse(BaseModel):
    id: int | None = None
    quiz_id: int | None = None
    quiz_title: str | None = None
    total_score: int | None = None
    submitted_at: datetime | None = None
    total_quizzes_completed: int

class BloomBreakdownResult(BaseModel):
    """
    The model of the bloom breakdown
    what's the performance for each bloom level inside a specific attempt
    """
    bloom_level: str
    correct: int
    total_attempted_questions: int

class QuestionAttemptResult(BaseModel):
    """
    The model of the questions after the correction of the answer to the quiz.
    """
    question_id: int
    selected_answer_id: int
    is_correct: bool
    score_obtained:int
    bloom_level:str

class AttemptResultResponse(BaseModel):
    """
    The model of the attempt. What is going to be returned to the frontend
    """
    attempt_id: int
    quiz_id: int
    total_score: int
    submitted_at: datetime
    question_results: list[QuestionAttemptResult]
    bloom_breakdown: list[BloomBreakdownResult]