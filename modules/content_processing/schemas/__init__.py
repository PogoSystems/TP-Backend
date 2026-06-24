from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    course_id: int
    user_id: int
    title: str
    document_type: str
    syllabus: bool
    processing_status: str
    created_at: datetime

    model_config = {"from_attributes": True}