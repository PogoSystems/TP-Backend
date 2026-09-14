from enum import Enum
from pathlib import Path
import uuid
import pytest
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
from modules.content_processing.infrastructure.repositories.document_repository import DocumentRepository
from modules.content_processing.infrastructure.repositories.document_chunk_repository import DocumentChunkRepository

from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.llm_adapter.infrastructure.providers.gemini_embedding_provider import GeminiEmbeddingProvider
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import GeminiQuizGenerator
from modules.quiz_generation.application.services.quiz_generation_service import QuizGenerationService
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz

from modules.quiz_generation.infrastructure.repositories.quiz_persistence_repository import QuizPersistenceRepository 
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository 

from shared.value_objects.Bloom import BloomLevel


@pytest.mark.asyncio
async def test_rag_quiz_generation_pipeline(tmp_path: Path) -> None:
    """
    Test the entire RAG pipeline from PDF ingestion to Quiz Generation using Gemini.
    """
    async for session in get_db():
        # 1. Create a dummy user
        unique_suffix = uuid.uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid.uuid4(),
            name=f"RAG_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"tester_{unique_suffix}@rag.com",
        )

        session.add(user)
        await session.flush()

        # 2. Create a dummy course
        course = CourseModel(
            name="RAG Quiz Testing Course",
            description="Course designed to test RAG quiz generation capabilities",
            user_id=user.id,
        )
        session.add(course)
        await session.flush()

        # 3. Load PDF fixture (located in content_processing)
        current_dir = Path(__file__).parent
        pdf_path = current_dir.parent / "content_processing" / "fixtures" / "muestra.pdf"
        assert pdf_path.exists(), f"Expected fixture PDF not found at {pdf_path}"

        store = LocalDocumentStore(base_path=tmp_path)
        extractor = PdfContentExtractor()
        preparation_service = ContentPreparationService(document_store=store, extractor=extractor)

        prepared_doc = preparation_service.prepare_pdf(
            source_path=pdf_path,
            title="User Stories Reference Doc",
        )

        # 4. Save content document
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

        # 5. Chunking
        chunking_service = ChunkingService(
            token_counter=TokenCounter(),
            max_chunk_tokens=512,
            chunk_overlap=64,
        )
        chunked_doc = chunking_service.chunk_document(prepared_doc)
        assert chunked_doc.chunks

        # 6. Generate Embeddings for Chunks
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embedding_provider = GeminiEmbeddingProvider(client=client)
        embedding_service = EmbeddingGenerationService(embedding_provider=embedding_provider)

        embedded_chunks = await embedding_service.generate_embeddings(chunked_doc.chunks)
        assert len(embedded_chunks) == len(chunked_doc.chunks)

        # 7. Save Chunks to Database
        assert saved_doc.id is not None
        chunk_repo = DocumentChunkRepository(session)
        await chunk_repo.save_all(
            document_id=saved_doc.id,
            chunks=embedded_chunks,
        )
        await session.flush()

        # 8. Setup Facade & Quiz Generation Service
        quiz_generator = GeminiQuizGenerator(client=client)
        from modules.content_processing.application.services.content_retrieval_facade import ContentRetrievalFacade
        from modules.content_processing.domain.ports.storage_port import StoragePort
        
        class MockStorage(StoragePort):
            async def upload(self, key: str, data: bytes, content_type: str) -> str: return ""
            async def download(self, key: str) -> bytes: return b""
            async def delete(self, key: str) -> None: pass

        
        content_facade = ContentRetrievalFacade(
            session=session,
            embedding_provider=embedding_provider,
            storage=MockStorage()
        )

        repository = QuizPersistenceRepository(session)
        stats_repository = StatsQueryRepository(session)
        
        quiz_generation_service = QuizGenerationService(
            context_retriever=content_facade,
            quiz_generator=quiz_generator,
            quiz_repository=repository,
            stats_repository=stats_repository,
        )

        # 9. Execute Quiz Generation (RAG)
        # Search query: "User stories"
        generated_quiz = await quiz_generation_service.generate_quiz_from_course(
            course_id=course.id,
            query_text="User stories",
            num_questions=5,
            user_id=user.id,
            bloom_levels=[BloomLevel.REMEMBER]
        )

        directorio_actual = Path(__file__).parent
        generated_quiz_path = directorio_actual / "fixtures" / "generated_quiz.json"
        
        generated_quiz_path.write_text(generated_quiz.model_dump_json(indent=4), encoding="utf-8")
        
        # 10. Assertions & Validation
        assert isinstance(generated_quiz, GeneratedQuiz)
        assert generated_quiz.title != ""
        assert len(generated_quiz.questions) == 5

        for i, question in enumerate(generated_quiz.questions):
            assert question.text != ""
            assert question.bloom_level.value in [e.value for e in BloomLevel]
            assert question.score > 0
            assert question.explanation != ""
            assert len(question.answers) >= 2

            # Exactly one correct answer choice
            correct_answers = [ans for ans in question.answers if ans.is_correct]
            assert len(correct_answers) == 1
            assert correct_answers[0].text != ""

        # Rollback everything to prevent polluting the Supabase database
        await session.rollback()
        print("\n[SUCCESS] RAG Quiz Generation Integration Test Passed Successfully!")