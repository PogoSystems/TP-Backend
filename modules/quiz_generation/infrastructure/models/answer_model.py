from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base

class AnswerModel(Base):
    __tablename__ = "answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)