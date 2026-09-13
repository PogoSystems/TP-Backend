from datetime import datetime

from pydantic import BaseModel, Field


class AnswerSubmission(BaseModel):
    question_id:int = Field(..., gt=0)
    selected_answer_id:int = Field(..., gt=0)

class SubmitQuizRequest(BaseModel):
    """
    The model of the info that needs to be submitted from the frontend to the backend when a user submits a quiz.
    """
    started_at: datetime = Field(..., description="Timestamp de cuando el usuario comenzó el quiz (enviado desde el frontend).")
    expected_correct_answers: int = Field(..., ge=0, description="Cantidad estimada de respuestas correctas que el estudiante creyó que obtendría antes de iniciar (obligatorio).")
    answers: list[AnswerSubmission] = Field(..., description="Lista de respuestas seleccionadas por el usuario.")