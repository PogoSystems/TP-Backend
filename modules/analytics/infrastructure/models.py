from datetime import datetime

from sqlalchemy import DateTime, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class CourseStatsModel(Base):
    __tablename__ = "course_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("course.id"), nullable=False, index=True)
    quizzes_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", name="uq_course_stats_course_id"),
    )


class BloomStatsModel(Base):
    __tablename__ = "bloom_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("course.id"), nullable=False, index=True)
    bloom_level: Mapped[str] = mapped_column(String(20), nullable=False)
    questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "bloom_level", name="uq_bloom_stats_course_bloom"),
    )