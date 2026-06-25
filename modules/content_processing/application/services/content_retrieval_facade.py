import logging

from sqlalchemy.ext.asyncio import AsyncSession

from modules.content_processing.application.services.document_processing_service import DocumentProcessingService
from modules.content_processing.domain.aggregates.content_document import ContentDocumentAggregate
from modules.content_processing.domain.ports.embedding_provider import EmbeddingProvider
from modules.content_processing.domain.ports.storage_port import StoragePort
from modules.content_processing.domain.value_objects.processing_status import ProcessingStatus
from modules.content_processing.infrastructure.repositories.document_chunk_repository import DocumentChunkRepository
from modules.content_processing.infrastructure.repositories.document_repository import DocumentRepository
from shared.exceptions import DocumentNotFoundError

logger = logging.getLogger(__name__)


class ContentRetrievalFacade:
    """
    Facade that implements ContextRetrievalPort for the quiz_generation module.
    Encapsulates all logic related to document fetching, processing orchestration,
    embeddings generation, and similarity search, returning clean contextual text.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        storage: StoragePort | None = None,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._storage = storage
        self._chunk_repo = DocumentChunkRepository(session)
        self._doc_repo = DocumentRepository(session)

    async def get_context_from_course(self, course_id: int, query_text: str, limit: int) -> str:
        """
        Generates query embedding and performs similarity search across all documents
        in a given course. Returns concatenated chunks as text.
        """
        # Generate embeddings for query text
        query_embeddings = await self._embedding_provider.generate_embeddings([query_text])
        if not query_embeddings:
            raise ValueError("Failed to generate embedding for query text")
        query_vector = query_embeddings[0]

        # Similarity search in database
        chunks = await self._chunk_repo.similarity_search(
            query_vector=query_vector,
            course_id=course_id,
            limit=limit,
        )

        if not chunks:
            raise ValueError(f"No relevant chunks found in database for course {course_id} and query '{query_text}'")

        # Combine retrieved context
        context_parts = [chunk.enriched_content for chunk in chunks]
        return "\n\n=== FRAGMENT ===\n".join(context_parts)

    async def get_context_from_documents(self, document_ids: list[int], query_text: str, limit: int, course_id:int,) -> str:
        """
        1. Fetches documents from DB and validates existence.
        2. Processes PENDING/FAILED documents.
        3. Performs similarity search filtered by document_ids.
        4. Returns concatenated chunks as text.
        """
        # Fetch documents from database
        documents = await self._doc_repo.find_by_ids(document_ids)

        # Validate all requested IDs exist
        found_ids = {doc.id for doc in documents}
        missing_ids = [doc_id for doc_id in document_ids if doc_id not in found_ids]
        if missing_ids:
            raise DocumentNotFoundError(missing_ids)

        # Classify and process documents by status
        syllabus_doc = await self._doc_repo.find_syllabus_by_course(course_id)
        if syllabus_doc:
            await self._ensure_documents_processed([syllabus_doc])
        else:
            from shared.exceptions import NoSyllabusError
            raise NoSyllabusError()

        await self._ensure_documents_processed(documents)

        # Generate embedding for the query in batch
        syllabus_query = f"{query_text} objetivos competencias resultados de aprendizaje temario"
        
        query_embeddings = await self._embedding_provider.generate_embeddings([
            query_text,      # Vector 0
            syllabus_query   # Vector 1
        ])
        
        if not query_embeddings or len(query_embeddings) < 2:
            raise ValueError("Failed to generate embeddings for queries")
            
        query_vector = query_embeddings[0]
        syllabus_query_vector = query_embeddings[1]

        # Validate that the topic is valid for the course
        syllabus_chunks = await self._chunk_repo.check_topic_in_syllabus(
            query_vector=query_vector,
            course_id=course_id,
            distance_threshold=0.38,
            limit=3
        )

        # DEPURACIÓN: Ver qué está devolviendo el syllabus
        print("\n\n--- DEPURACIÓN DE SÍLABO ---")
        for i, chunk in enumerate(syllabus_chunks):
            print(f"Chunk {i+1}: {chunk.enriched_content[:200]}...") # Imprime los primeros 200 caracteres
        print("----------------------------\n\n")
        
        # If no syllabus chunks are found, raise an error
        if not syllabus_chunks:
            from shared.exceptions import TopicNotInSyllabusError
            raise TopicNotInSyllabusError()

        # Extract the syllabus text
        syllabus_text = "\n\n".join([chunk.enriched_content for chunk in syllabus_chunks])

        # Similarity search filtered by document_ids
        chunks = await self._chunk_repo.similarity_search_by_document_ids(
            query_vector=query_vector,
            document_ids=document_ids,
            limit=limit,
        )

        if not chunks:
            raise ValueError(
                f"No relevant chunks found for documents {document_ids} and query '{query_text}'"
            )

        # Build context from retrieved chunks
        context_parts = [chunk.enriched_content for chunk in chunks]
        rag_text= "\n\n=== FRAGMENT ===\n".join(context_parts)

        final_context = (
            f"=== OBJETIVOS Y COMPETENCIAS DEL SÍLABO ===\n"
            f"{syllabus_text}\n\n"
            f"=== MATERIAL DE REFERENCIA PARA LAS PREGUNTAS ===\n"
            f"{rag_text}"
        )
        
        return final_context

    async def _ensure_documents_processed(
        self,
        documents: list[ContentDocumentAggregate],
    ) -> None:
        """
        Ensures all documents are in COMPLETED status.
        - COMPLETED: No action needed.
        - PENDING / FAILED: Process the document (download, extract, chunk, embed).
        - PROCESSING: Raise error (another process is working on it).
        """
        for doc in documents:
            if doc.processing_status == ProcessingStatus.COMPLETED:
                continue

            if doc.processing_status == ProcessingStatus.PROCESSING:
                raise ValueError(
                    f"Document id={doc.id} is currently being processed. Please try again later."
                )

            # PENDING or FAILED → process the document
            if self._storage is None:
                raise ValueError(
                    "Storage adapter is required to process PENDING documents."
                )

            processing_service = DocumentProcessingService(
                session=self._session,
                storage=self._storage,
                embedding_provider=self._embedding_provider,
            )
            await processing_service.process_document(doc)
            await self._session.commit()
