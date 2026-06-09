from sqlalchemy.ext.asyncio import AsyncSession
from core.settings import settings
from modules.content_processing.domain.ports.embedding_provider import EmbeddingProvider
from modules.content_processing.infrastructure.repositories.document_chunk_repository import DocumentChunkRepository
from modules.quiz_generation.domain.ports.quiz_generator_port import QuizGeneratorPort
from modules.quiz_generation.schemas.generation_schemas import GeneratedQuiz


class QuizGenerationService:
    """
    Application Service responsible for orchestrating the RAG Quiz Generation.
    Retrieves relevant database chunks using query embedding and requests
    Gemini to generate the quiz.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        quiz_generator: QuizGeneratorPort,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._quiz_generator = quiz_generator
        self._chunk_repo = DocumentChunkRepository(session)

    async def generate_quiz(
        self,
        *,
        course_id: int,
        query_text: str,
        num_questions: int,
        prompt_instruction: str,
    ) -> GeneratedQuiz:
        """
        Executes RAG Quiz Generation:
        1. Generates embedding for the search query.
        2. Retrieves the top relevant chunks for the course.
        3. Prepares context text by concatenating retrieved content.
        4. Calls LLM adapter to generate the quiz structured JSON.
        """
        # Step 1: Generate embeddings for query text
        query_embeddings = await self._embedding_provider.generate_embeddings([query_text])
        if not query_embeddings:
            raise ValueError("Failed to generate embedding for query text")
        query_vector = query_embeddings[0]

        # Step 2: Similarity search in database
        chunks = await self._chunk_repo.similarity_search(
            query_vector=query_vector,
            course_id=course_id,
            limit=settings.TOP_K_RETRIEVAL,
        )

        if not chunks:
            raise ValueError(f"No relevant chunks found in database for course {course_id} and query '{query_text}'")

        # Step 3: Combine retrieved context
        context_parts = []
        for chunk in chunks:
            # We use enriched_content because it contains context injection (Title + heading path)
            context_parts.append(chunk.enriched_content)

        context_text = "\n\n=== FRAGMENT ===\n".join(context_parts)

        # Step 4: Call LLM adapter using the port
        generated_quiz = await self._quiz_generator.generate_quiz_from_context(
            context_text=context_text,
            num_questions=num_questions,
            prompt_instruction=prompt_instruction,
        )

        return generated_quiz
