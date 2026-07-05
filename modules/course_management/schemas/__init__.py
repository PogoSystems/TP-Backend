from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    """DTO para crear un nuevo curso."""

    name: str = Field(..., min_length=1, max_length=255, description="Nombre del curso")
    description: str | None = Field(None, description="Descripción opcional del curso")
    max_score: int | None = Field(None, ge=0, description="Puntuación máxima alcanzable")


class CourseUpdate(BaseModel):
    """DTO para actualización parcial (PATCH) de un curso.
    Todos los campos son opcionales; solo los campos enviados serán actualizados.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    max_score: int | None = Field(None, ge=0)


class CourseResponse(BaseModel):
    """Representación pública de un curso devuelta por la API."""

    id: int
    name: str
    description: str | None
    user_id: int
    max_score: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

class TopCoursesResponse(BaseModel):
    courses: list[CourseResponse]
    total_courses: int
