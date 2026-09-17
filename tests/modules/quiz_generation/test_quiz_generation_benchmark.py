import os
from pathlib import Path
import uuid
import pytest
from google import genai

from core.db.database import get_db
from core.settings import settings
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository
from modules.content_processing.application.services.chunking.chunking_service import ChunkingService
from modules.content_processing.application.services.content_retrieval_facade import ContentRetrievalFacade
from modules.content_processing.application.services.embedding.embedding_generation_service import (
    EmbeddingGenerationService,
)
from modules.content_processing.application.services.parsing.content_preparation_service import (
    ContentPreparationService,
)
from modules.content_processing.domain.aggregates import ContentDocumentAggregate
from modules.content_processing.domain.ports.storage_port import StoragePort
from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor
from modules.content_processing.infrastructure.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from modules.content_processing.infrastructure.repositories.document_repository import (
    DocumentRepository,
)
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore
from modules.content_processing.infrastructure.tokenizers.token_counter import TokenCounter
from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.llm_adapter.infrastructure.providers.gemini_embedding_provider import (
    GeminiEmbeddingProvider,
)
from modules.llm_adapter.infrastructure.providers.gemini_quiz_generator import GeminiQuizGenerator
from modules.quiz_generation.application.services.quiz_generation_service import (
    QuizGenerationService,
)
from modules.quiz_generation.infrastructure.repositories.quiz_persistence_repository import (
    QuizPersistenceRepository,
)
from tests.modules.quiz_generation.pipeline_profiler import PipelineMemoryProfiler
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz
from shared.value_objects.Bloom import BloomLevel


class _MockStorage(StoragePort):
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        return ""

    async def download(self, key: str) -> bytes:
        return b""

    async def delete(self, key: str) -> None:
        pass


@pytest.fixture
def quiz_benchmark_reporter():
    """
    Fixture que perfila la memoria y tiempo del pipeline completo de generación de cuestionarios
    y genera un reporte en formato Markdown al finalizar la prueba.
    """
    profiler = PipelineMemoryProfiler("Pipeline RAG de Generación de Cuestionarios")
    profiler.start_profiling()

    yield profiler

    profiler.stop_profiling()

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    report_path = fixtures_dir / "quiz_pipeline_benchmark_report.md"

    report_markdown = profiler.generate_markdown_report(output_path=report_path)

    # Imprimir en consola para visibilidad inmediata si pytest se ejecuta con -s
    print("\n" + "=" * 80)
    print(f"REPORTE GENERADO EN: {report_path}")
    print("=" * 80)
    print(report_markdown)
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_rag_quiz_generation_benchmark(
    quiz_benchmark_reporter: PipelineMemoryProfiler,
    tmp_path: Path,
) -> None:
    """
    Ejecuta el pipeline RAG completo midiendo memoria y tiempo por cada etapa y método.
    """
    profiler = quiz_benchmark_reporter

    # Cargar documento de prueba
    current_dir = Path(__file__).parent
    pdf_path = current_dir.parent / "content_processing" / "fixtures" / "muestra.pdf"
    assert pdf_path.exists(), f"No se encontró el PDF fixture en: {pdf_path}"

    file_size_kb = pdf_path.stat().st_size / 1024
    profiler.set_result_data("Archivo procesado", pdf_path.name)
    profiler.set_result_data("Tamaño del archivo", f"{file_size_kb:.2f} KB")

    async for session in get_db():
        # 1. Setup de Usuario y Curso
        with profiler.track_step("1. Setup de Usuario y Curso (BD)"):
            unique_suffix = uuid.uuid4().hex[:8]
            user = UserModel(
                auth_id=uuid.uuid4(),
                name=f"Bench_{unique_suffix}",
                last_name="Tester",
                college="Test University",
                major="Software Engineering",
                email=f"bench_{unique_suffix}@rag.com",
            )
            session.add(user)
            await session.flush()

            course = CourseModel(
                name="Benchmark Quiz Course",
                description="Curso para benchmark de memoria del pipeline RAG",
                user_id=user.id,
            )
            session.add(course)
            await session.flush()

        # 2. Parseo y Extracción de PDF con PyMuPDF
        with profiler.track_step("2. Parseo y Estructuración PDF (ContentPreparationService)"):
            store = LocalDocumentStore(base_path=tmp_path)
            extractor = PdfContentExtractor()
            preparation_service = ContentPreparationService(document_store=store, extractor=extractor)
            prepared_doc = preparation_service.prepare_pdf(
                source_path=pdf_path,
                title="User Stories Reference Doc",
            )
            profiler.set_result_data("Páginas del PDF", prepared_doc.raw.page_count)
            profiler.set_result_data("Secciones detectadas", len(prepared_doc.sections))

        # 3. Guardado del Documento de Contenido en BD
        with profiler.track_step("3. Persistencia de Metadatos Documento (DocumentRepository)"):
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

        # 4. Segmentación Semántica (Chunking)
        with profiler.track_step("4. Segmentación Semántica (ChunkingService)"):
            chunking_service = ChunkingService(
                token_counter=TokenCounter(),
                max_chunk_tokens=512,
                chunk_overlap=64,
            )
            chunked_doc = chunking_service.chunk_document(prepared_doc)
            profiler.set_result_data("Chunks generados", len(chunked_doc.chunks))

        # 5. Generación de Embeddings Vectoriales (Gemini API)
        with profiler.track_step("5. Generación de Embeddings (GeminiEmbeddingProvider)"):
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            embedding_provider = GeminiEmbeddingProvider(client=client)
            embedding_service = EmbeddingGenerationService(embedding_provider=embedding_provider)
            embedded_chunks = await embedding_service.generate_embeddings(chunked_doc.chunks)
            profiler.set_result_data("Embeddings generados", len(embedded_chunks))

        # 6. Persistencia de Chunks en BD (PGVector)
        with profiler.track_step("6. Persistencia de Chunks en BD (DocumentChunkRepository)"):
            assert saved_doc.id is not None
            chunk_repo = DocumentChunkRepository(session)
            await chunk_repo.save_all(
                document_id=saved_doc.id,
                chunks=embedded_chunks,
            )
            await session.flush()

        # 7. Configuración de Facade & Servicios RAG
        with profiler.track_step("7. Setup de Facade y Servicios RAG"):
            quiz_generator = GeminiQuizGenerator(client=client)
            content_facade = ContentRetrievalFacade(
                session=session,
                embedding_provider=embedding_provider,
                storage=_MockStorage(),
            )
            quiz_repo = QuizPersistenceRepository(session)
            stats_repo = StatsQueryRepository(session)

            quiz_generation_service = QuizGenerationService(
                context_retriever=content_facade,
                quiz_generator=quiz_generator,
                quiz_repository=quiz_repo,
                stats_repository=stats_repo,
            )

        # 8. Búsqueda RAG y Generación del Cuestionario con LLM
        with profiler.track_step("8. Generación de Cuestionario RAG (GeminiQuizGenerator)"):
            generated_quiz = await quiz_generation_service.generate_quiz_from_course(
                course_id=course.id,
                query_text="User stories",
                num_questions=5,
                user_id=user.id,
                bloom_levels=[BloomLevel.REMEMBER],
            )
            profiler.set_result_data("Título del Cuestionario", generated_quiz.title)
            profiler.set_result_data("Preguntas generadas", len(generated_quiz.questions))

        # Validaciones de integridad del resultado
        assert isinstance(generated_quiz, GeneratedQuiz)
        assert len(generated_quiz.questions) == 5

        # 9. Prueba explícita de Garbage Collection
        profiler.evaluate_gc()

        # Rollback para no ensuciar la base de datos
        await session.rollback()
