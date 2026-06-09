from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DateTime, Integer, ForeignKey, TEXT, func, ARRAY, JSON
from sqlalchemy.orm import Mapped, mapped_column


from core.db.base import Base


class DocumentChunkModel (Base):
    __tablename__ = 'document_chunk'

    id: Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer,ForeignKey("content_document.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    raw_content: Mapped[str] = mapped_column(TEXT, nullable=False)
    enriched_content: Mapped[str] = mapped_column(TEXT, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=False)
    embedding: Mapped[list[float| None]] = mapped_column(VECTOR(768),nullable=True)
    token_count: Mapped[int] = mapped_column(Integer,nullable=False)
    #chunk_metadata: Mapped[dict] = mapped_column(JSON,nullable=False,default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
