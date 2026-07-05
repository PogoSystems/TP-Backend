import logging
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from modules.content_processing.application.services.chunking.chunking_service import ChunkingService
from modules.content_processing.application.services.embedding.embedding_generation_service import EmbeddingGenerationService
from modules.content_processing.application.services.parsing.content_metadata import enhance_section_metadata
from modules.content_processing.application.services.parsing.content_normalization import normalize_markdown
from modules.content_processing.application.services.parsing.content_structuring import structure_sections
from modules.content_processing.domain.aggregates.content_document import ContentDocumentAggregate
from modules.content_processing.domain.ports.embedding_provider import EmbeddingProvider
from modules.content_processing.domain.ports.storage_port import StoragePort
from modules.content_processing.domain.value_objects.prepared_content import PreparedDocument, RawContent
from modules.content_processing.domain.value_objects.processing_status import ProcessingStatus
from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor
from modules.content_processing.infrastructure.repositories.document_chunk_repository import DocumentChunkRepository
from modules.content_processing.infrastructure.repositories.document_repository import DocumentRepository
from modules.content_processing.infrastructure.tokenizers.token_counter import TokenCounter
from shared.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Application service that orchestrates the full processing pipeline
    for a PENDING document: download → extract → chunk → embed → persist.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: StoragePort,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._session = session
        self._storage = storage
        self._embedding_provider = embedding_provider
        self._doc_repo = DocumentRepository(session)
        self._chunk_repo = DocumentChunkRepository(session)
        self._extractor = PdfContentExtractor()
        self._token_counter = TokenCounter()
        self._chunking_service = ChunkingService(
            token_counter=self._token_counter,
            max_chunk_tokens=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self._embedding_service = EmbeddingGenerationService(
            embedding_provider=embedding_provider,
        )

    async def process_document(self, document: ContentDocumentAggregate) -> None:
        """
        Execute the full processing pipeline for a single document:
        1. Mark as PROCESSING
        2. Download file from Supabase Storage
        3. Extract markdown (PDF only for MVP)
        4. Normalize and structure
        5. Chunk
        6. Generate embeddings
        7. Persist chunks
        8. Mark as COMPLETED
        """
        assert document.id is not None

        try:
            # Step 1: Mark as processing
            await self._doc_repo.update_status(document.id, ProcessingStatus.PROCESSING)

            # Step 2: Download from Supabase Storage
            file_bytes = await self._storage.download(document.storage_key)

            # Step 3: Extract markdown (write to temp file for PyMuPDF)
            markdown, page_count = self._extract_markdown_from_bytes(
                file_bytes=file_bytes,
                document_type=document.document_type,
            )

            # Step 4: Normalize and structure
            raw = RawContent(
                title=document.title,
                storage_key=document.storage_key,
                document_type=document.document_type,
                markdown=markdown,
                page_count=page_count,
            )
            normalized = normalize_markdown(markdown)
            sections = structure_sections(normalized)
            enriched_sections = enhance_section_metadata(
                sections=sections,
                storage_key=document.storage_key,
                document_title=document.title,
                document_type=document.document_type,
            )
            prepared_doc = PreparedDocument(
                raw=raw,
                normalized_text=normalized,
                sections=enriched_sections,
            )

            # Step 5: Chunk
            chunked_doc = self._chunking_service.chunk_document(prepared_doc)

            # Step 6: Generate embeddings
            embedded_chunks = await self._embedding_service.generate_embeddings(chunked_doc.chunks)

            # Step 7: Persist chunks
            await self._chunk_repo.save_all(
                document_id=document.id,
                chunks=embedded_chunks,
            )

            # Step 8: Mark as completed
            await self._doc_repo.update_status(document.id, ProcessingStatus.COMPLETED)

            logger.info(
                "Document id=%d processed successfully: %d chunks created",
                document.id,
                len(embedded_chunks),
            )

        except Exception as exc:
            # Mark the document as failed so it can be retried later
            await self._doc_repo.update_status(document.id, ProcessingStatus.FAILED)
            logger.error("Failed to process document id=%d: %s", document.id, exc)
            raise DocumentProcessingError(document.id, str(exc)) from exc

    def _extract_markdown_from_bytes(
        self,
        *,
        file_bytes: bytes,
        document_type: str,
    ) -> tuple[str, int]:
        """
        Write file bytes to a temporary file and extract markdown.
        Only PDF is supported for the MVP.
        """
        if document_type != "pdf":
            raise ValueError(f"Unsupported document type for processing: {document_type}")

        suffix = f".{document_type}"
        tmp_path = None
        
        # En Windows, NamedTemporaryFile no puede ser abierto por otro proceso 
        # mientras siga abierto por el bloque 'with'. Por eso usamos delete=False, 
        # lo cerramos, extraemos y luego lo borramos manualmente.
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(file_bytes)
            tmp.flush()
            tmp.close()  # Importante: cerrar el archivo antes de leerlo
            
            tmp_path = Path(tmp.name)
            return self._extractor.extract_markdown(tmp_path)
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
