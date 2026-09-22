from pydantic import BaseModel, Field
from shared.value_objects.Bloom import BloomLevel

class QuizGenerationRequest(BaseModel):
    """Request body for the POST /quizzes endpoint."""

    course_id: int = Field(
        ...,
        gt=0,
        description="ID of the course from which to generate the quiz.",
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Title of the quiz.",
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
        le=25,
        description="Number of questions to generate in the quiz (maximum 25).",
    )

    bloom_levels: list[BloomLevel] = Field(
        ...,
        description="Bloom taxonomy level for the questions.",
    )
