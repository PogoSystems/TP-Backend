from pydantic import BaseModel, Field


class QuizGenerationRequest(BaseModel):
    """Request body for the POST /quizzes endpoint."""

    #TODO: change user_id to user_id from the token
    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user who owns the course.",
    )

    course_id: int = Field(
        ...,
        gt=0,
        description="ID of the course from which to generate the quiz.",
    )

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
