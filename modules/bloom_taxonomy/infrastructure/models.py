from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base


class BloomLevelModel(Base):
    __tablename__ = "bloom_level"

    level: Mapped[str] = mapped_column(String(20), primary_key=True)