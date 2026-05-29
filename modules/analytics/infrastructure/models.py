from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class UserBloomStatsModel(Base):
    __tablename__ = "user_bloom_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    correct_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remember_percentage: Mapped[float | None] = mapped_column(Numeric(2, 10), nullable=True)
    understand_percentage: Mapped[float | None] = mapped_column(Numeric(2, 10), nullable=True)
    apply_percentage: Mapped[float | None] = mapped_column(Numeric(2, 10), nullable=True)
    analyze_percentage: Mapped[float | None] = mapped_column(Numeric(2, 10), nullable=True)
    evaluate_percentage: Mapped[float | None] = mapped_column(Numeric(2, 10), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)