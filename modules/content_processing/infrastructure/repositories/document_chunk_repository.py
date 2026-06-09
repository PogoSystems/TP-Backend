from sqlalchemy.ext.asyncio import AsyncSession

from modules.content_processing.domain.value_objects.embedded_chunk import EmbeddedChunk
from modules.content_processing.infrastructure.models import DocumentChunkModel


class DocumentChunkRepository:
    """
    Repository for the persistence of the document chunks in the database
    """
    def __init__(self,
                 session: AsyncSession
                 ) -> None:
        self._session = session

    """
    Save a collection of embedded chunks
    """
    async def save_all(self,
                       *,
                       document_id:int,
                       chunks: list[EmbeddedChunk]
                       ) -> None :

        # maps the values of the embedded chunks to the document chunk model
        models = [
            DocumentChunkModel(
                document_id=document_id,
                chunk_index=embedded.chunk.chunk_index,
                raw_content=embedded.chunk.raw_content,
                enriched_content=embedded.chunk.enriched_text,
                heading_path=embedded.chunk.heading_path,
                embedding=embedded.embedding,
                token_count=embedded.chunk.token_count,
            )
            for embedded in chunks
        ]

        # SQLAlchemy performs the insert operation
        self._session.add_all(models)