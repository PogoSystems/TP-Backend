from datetime import datetime

from pydantic import BaseModel


class QuestionAttemptResult(BaseModel):
    """
    The model of the questions after the correction of the answer to the quiz.
    """
    question_id: int
    selected_answer_id: int
    is_correct: bool
    score_obtained:int

class AttemptResultResponse(BaseModel):
    """
    The model of the attempt. What is going to be returned to the frontend
    """
    attempt_id: int
    quiz_id: int
    total_score: int
    submitted_at: datetime
    question_results: list[QuestionAttemptResult]