from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from modules.content_processing.domain.value_objects.embedded_chunk import EmbeddedChunk
from modules.content_processing.infrastructure.models import DocumentChunkModel, ContentDocumentModel


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

    async def similarity_search(
        self,
        *,
        query_vector: list[float],
        course_id: int | None = None,
        limit: int = 5
    ) -> list[DocumentChunkModel]:
        """
        Retrieves the top K chunks most similar to the query_vector.
        Optionally filters by course_id through joining ContentDocumentModel.
        """
        stmt = select(DocumentChunkModel)
        if course_id is not None:
            stmt = stmt.join(ContentDocumentModel).where(
                ContentDocumentModel.course_id == course_id
            )
        stmt = stmt.order_by(
            DocumentChunkModel.embedding.cosine_distance(query_vector)
        ).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_document_ids(
        self,
        document_ids: list[int],
    ) -> list[DocumentChunkModel]:
        """Retrieve all chunks belonging to the given document IDs."""
        stmt = (
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id.in_(document_ids))
            .order_by(DocumentChunkModel.document_id, DocumentChunkModel.chunk_index)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def similarity_search_by_document_ids(
        self,
        *,
        query_vector: list[float],
        document_ids: list[int],
        limit: int = 5,
    ) -> list[DocumentChunkModel]:
        """
        Retrieves the top K chunks most similar to the query_vector,
        filtered to only include chunks from the given document IDs.
        Filters at the DB level with WHERE document_id IN (...) for scalability.
        """
        stmt = (
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id.in_(document_ids))
            .order_by(DocumentChunkModel.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def check_topic_in_syllabus(
        self,
        query_vector: list[float],
        course_id:int,
        distance_threshold: float,
        limit: int,
        query_text: str,
        )->list[DocumentChunkModel]:
        """
        Verifica si el topic (representado por query_vector) es semánticamente 
        cercano a algún documento marcado como syllabus dentro del curso.
        Retorna True si existe al menos un chunk cuya distancia sea menor al umbral.
        """
        distance_expr = DocumentChunkModel.embedding.cosine_distance(query_vector)
        stmt = (
            select(DocumentChunkModel)
            .join(ContentDocumentModel)
            .where(
                ContentDocumentModel.course_id == course_id,
                ContentDocumentModel.syllabus == True,
            )
        )
        
        if query_text != "Resumen principal, conceptos clave y temas principales.":
            stmt = stmt.where(distance_expr < distance_threshold)
            
        stmt = stmt.order_by(distance_expr).limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all()) # Devuelve una lista de chunks (o vacía)

    async def lexical_search(
        self,
        *,
        query_text: str,
        course_id: int | None = None,
        limit: int = 15,
    ) -> list[DocumentChunkModel]:
        """
        Performs full-text lexical search on enriched_content using PostgreSQL
        to_tsvector/plainto_tsquery and ts_rank_cd ranking in Spanish.
        Optionally filters by course_id through ContentDocumentModel.
        """
        if not query_text or not query_text.strip():
            return []

        ts_vector = func.to_tsvector("spanish", DocumentChunkModel.enriched_content)
        ts_query = func.plainto_tsquery("spanish", query_text)
        rank_expr = func.ts_rank_cd(ts_vector, ts_query)

        stmt = select(DocumentChunkModel).where(ts_vector.op("@@")(ts_query))

        if course_id is not None:
            stmt = stmt.join(ContentDocumentModel).where(
                ContentDocumentModel.course_id == course_id
            )

        stmt = stmt.order_by(desc(rank_expr)).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def lexical_search_by_document_ids(
        self,
        *,
        query_text: str,
        document_ids: list[int],
        limit: int = 15,
    ) -> list[DocumentChunkModel]:
        """
        Performs full-text lexical search on enriched_content for specific document IDs
        using PostgreSQL to_tsvector/plainto_tsquery and ts_rank_cd ranking in Spanish.
        """
        if not query_text or not query_text.strip() or not document_ids:
            return []

        ts_vector = func.to_tsvector("spanish", DocumentChunkModel.enriched_content)
        ts_query = func.plainto_tsquery("spanish", query_text)
        rank_expr = func.ts_rank_cd(ts_vector, ts_query)

        stmt = (
            select(DocumentChunkModel)
            .where(
                DocumentChunkModel.document_id.in_(document_ids),
                ts_vector.op("@@")(ts_query),
            )
            .order_by(desc(rank_expr))
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())