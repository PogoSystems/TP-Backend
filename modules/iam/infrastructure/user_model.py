from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from core.db.base import Base

class User(Base):
    __tablename__ = "user"
    id = Column(UUID, primary_key=True)