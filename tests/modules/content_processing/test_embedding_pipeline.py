from pathlib import Path
import uuid

import pytest
from sqlalchemy import select

from google import genai

from core.db.database import get_db
from core.settings import settings
from modules.content_processing.domain.aggregates import ContentDocumentAggregate

from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor
from modules.content_processing.application.services.parsing.content_preparation_service import ContentPreparationService
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore

from modules.content_processing.application.services.chunking.chunking_service import ChunkingService
from modules.content_processing.infrastructure.tokenizers.token_counter import TokenCounter

from modules.content_processing.application.services.embedding.embedding_generation_service import EmbeddingGenerationService
from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.llm_adapter.infrastructure.providers.gemini_embedding_provider import GeminiEmbeddingProvider

from modules.content_processing.infrastructure.repositories.document_repository import DocumentRepository
from modules.content_processing.infrastructure.repositories.document_chunk_repository import DocumentChunkRepository

from modules.content_processing.infrastructure.models.content_document_model import ContentDocumentModel


@pytest.mark.asyncio
async def test_full_embedding_persistence_pipeline(tmp_path: Path) -> None:
    """
    Pipeline completo:

    PDF
      ↓
    Document
      ↓
    Chunks
      ↓
    Embeddings
      ↓
    PostgreSQL (document + chunks)
    """

    # -------------------------------
    # DB session
    # -------------------------------
    async for session in get_db():
        # -------------------------------
        # STEP 1: Create user with unique email
        # -------------------------------
        unique_suffix = uuid.uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid.uuid4(),
            name=f"test_user_{unique_suffix}",
            last_name="TestLastName",
            college="Test College",
            major="Test Major",
            email=f"test_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        # -------------------------------
        # STEP 2: Create course
        # -------------------------------
        course = CourseModel(
            name="Test Course",
            description="Course for testing embeddings",
            user_id=user.id,
        )
        session.add(course)
        await session.flush()

        # -------------------------------
        # STEP 3: Load PDF fixture
        # -------------------------------
        current_dir = Path(__file__).parent
        pdf_path = current_dir / "fixtures" / "muestra.pdf"

        assert pdf_path.exists()

        store = LocalDocumentStore(base_path=tmp_path)
        extractor = PdfContentExtractor()

        preparation_service = ContentPreparationService(
            document_store=store,
            extractor=extractor,
        )

        prepared_doc = preparation_service.prepare_pdf(
            source_path=pdf_path,
            title="Documento Real",
        )

        # -------------------------------
        # STEP 4: Save content document
        # -------------------------------
        doc_repo = DocumentRepository(session)

        saved_doc = await doc_repo.save(
            ContentDocumentAggregate(
                course_id=course.id,
                user_id=user.id,
                title=prepared_doc.raw.title,
                storage_key=prepared_doc.raw.storage_key,
                document_type=prepared_doc.raw.document_type,
            )
        )

        # -------------------------------
        # STEP 5: Chunking
        # -------------------------------
        chunking_service = ChunkingService(
            token_counter=TokenCounter(),
            max_chunk_tokens=512,
            chunk_overlap=64,
        )

        chunked_doc = chunking_service.chunk_document(prepared_doc)

        assert chunked_doc.chunks

        # -------------------------------
        # STEP 6: Embeddings
        # -------------------------------
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        provider = GeminiEmbeddingProvider(client=client)

        embedding_service = EmbeddingGenerationService(
            embedding_provider=provider
        )

        embedded_chunks = await embedding_service.generate_embeddings(
            chunked_doc.chunks
        )

        assert len(embedded_chunks) == len(chunked_doc.chunks)
        # -------------------------------
        # STEP 6.1: Debug inspection
        # -------------------------------

        print("\n")
        print("=" * 100)
        print("EMBEDDINGS DEBUG")
        print("=" * 100)

        for i, embedded_chunk in enumerate(embedded_chunks[:3]):
            print("\n")
            print("-" * 80)
            print(f"Chunk index: {embedded_chunk.chunk.chunk_index}")
            print(f"Token count: {embedded_chunk.chunk.token_count}")

            print("\nRAW CONTENT:")
            print(embedded_chunk.chunk.raw_content[:500])

            print("\nENRICHED CONTENT:")
            print(embedded_chunk.chunk.enriched_text[:500])

            print("\nEMBEDDING (first 20 dims):")
            print(embedded_chunk.embedding[:20])

            print(f"\nEmbedding norm check (len): {len(embedded_chunk.embedding)}")
        # -------------------------------
        # STEP 7: Save chunks + embeddings
        # -------------------------------
        assert saved_doc.id is not None
        chunk_repo = DocumentChunkRepository(session)

        await chunk_repo.save_all(
            document_id=saved_doc.id,
            chunks=embedded_chunks,
        )

        await session.flush()
        # -------------------------------
        # STEP 8: Verification
        # -------------------------------
        result = await session.execute(
            select(ContentDocumentModel).where(
                ContentDocumentModel.id == saved_doc.id
            )
        )

        db_doc = result.scalar_one_or_none()

        assert db_doc is not None

        print("\nPIPELINE COMPLETED SUCCESSFULLY")
        print(f"Document ID: {db_doc.id}")
        print(f"Title: {db_doc.title}")

        await session.rollback()

    # Clean up the database engine pool to prevent "Event loop is closed" errors during teardown
    from core.db.database import engine
    await engine.dispose()