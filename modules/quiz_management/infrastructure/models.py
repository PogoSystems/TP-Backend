from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base

class QuizAttemptModel(Base):
    __tablename__ = "quiz_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz.id"), index=True)
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class QuestionAttemptModel(Base):
    __tablename__ = "question_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_attempt.id"), index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), index=True)
    selected_answer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("answer.id"), index=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score_obtained: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class QuizSourceDocumentModel(Base):
    __tablename__ = "quiz_source_document"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz.id"), index=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_document.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)