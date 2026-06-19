from pydantic import BaseModel, Field


class QuizGenerationRequest(BaseModel):
    """Request body for the POST /quizzes endpoint."""

    document_ids: list[int] = Field(
        ...,
        min_length=1,
        description="List of content_document IDs to use as source material for quiz generation.",
    )
    query_text: str | None = Field(
        default="",
        description="Search query to find relevant chunks via similarity search. If empty, a generic query will be used.",
    )
    num_questions: int = Field(
        ...,
        gt=0,
        description="Number of questions to generate in the quiz.",
    )
