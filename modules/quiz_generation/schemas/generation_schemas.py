from pydantic import BaseModel, Field, field_validator
from modules.quiz_generation.domain.aggregates.question import BloomLevel


class GeneratedAnswer(BaseModel):
    text: str = Field(description="The text content of the answer choice.")
    is_correct: bool = Field(description="True if this is the correct answer, False otherwise.")


class GeneratedQuestion(BaseModel):
    text: str = Field(description="The text content of the question.")
    bloom_level: BloomLevel = Field(description="The cognitive level of the question according to Bloom's Taxonomy.")
    score: int = Field(description="The weight or score points allocated to this question according to the complexity of the question (must be positive).")
    explanation: str = Field(description="Explanation or feedback about why the correct answer is right and why others are wrong.")
    answers: list[GeneratedAnswer] = Field(description="List of answer choices for this question.")

    @field_validator("score")
    @classmethod
    def validate_score(cls, val: int) -> int:
        if val <= 0:
            raise ValueError("score must be positive")
        return val

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, val: list[GeneratedAnswer]) -> list[GeneratedAnswer]:
        if not val:
            raise ValueError("answers list cannot be empty")
        correct_count = sum(1 for ans in val if ans.is_correct)
        if correct_count != 1:
            raise ValueError(f"A question must have exactly one correct answer. Found {correct_count} correct answers.")
        return val


class GeneratedQuiz(BaseModel):
    title: str = Field(description="The title of the generated quiz.")
    questions: list[GeneratedQuestion] = Field(description="List of questions included in the quiz.")
