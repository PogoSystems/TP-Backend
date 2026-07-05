from datetime import datetime
from pydantic import BaseModel, Field
from modules.quiz_generation.domain.aggregates.question import BloomLevel

class AnswerResponse(BaseModel):
    id: int = Field(description="The unique identifier of the answer.")
    text: str = Field(description="The text content of the answer choice.")
    is_correct: bool = Field(description="True if this is the correct answer, False otherwise.")

class QuestionResponse(BaseModel):
    id: int = Field(description="The unique identifier of the question.")
    text: str = Field(description="The text content of the question.")
    bloom_level: str = Field(description="The cognitive level of the question according to Bloom's Taxonomy.")
    score: int = Field(description="The weight or score points allocated to this question.")
    explanation: str = Field(description="Explanation or feedback about the answer.")
    answers: list[AnswerResponse] = Field(description="List of answer choices for this question.")

class QuizResponse(BaseModel):
    id: int = Field(description="The unique identifier of the quiz.")
    title: str = Field(description="The title of the generated quiz.")
    user_id: int = Field(description="ID of the user who owns the quiz.")
    course_id: int = Field(description="ID of the course the quiz belongs to.")
    created_at: datetime = Field(description="Timestamp when the quiz was generated.")
    questions: list[QuestionResponse] = Field(description="List of questions included in the quiz.")

class QuizSummaryResponse(BaseModel):
    id: int = Field(description="The unique identifier of the quiz.")
    title: str = Field(description="The title of the generated quiz.")
    created_at: datetime = Field(description="Timestamp when the quiz was generated.")

class QuizzesByCourseResponse(BaseModel):
    quizzes: list[QuizSummaryResponse] = Field(description="List of quizzes belonging to the course.")