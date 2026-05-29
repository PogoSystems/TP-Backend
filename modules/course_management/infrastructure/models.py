from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class CourseModel(Base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
