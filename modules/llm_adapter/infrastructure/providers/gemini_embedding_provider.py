from google import genai
from google.genai import types

from core.settings import settings
from modules.content_processing.domain.ports.embedding_provider import EmbeddingProvider


class GeminiEmbeddingProvider (EmbeddingProvider):
    """
    Implementation of Gemini of the embedding provider
    """
    def __init__(self,
                 *,
                 client:genai.Client
                 ) -> None:
        self._client = client # Gemini SDK client
        self._model=settings.EMBEDDING_MODEL # Embedding model

    async def generate_embeddings(self,
                                 texts: list[str]
                                 ) -> list[list[float]]:
        """
        Generate the embeddings using the embedding model of Gemini
        """
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=768
            ),
        )

        if response.embeddings is None:
            raise ValueError("Gemini did not return embeddings")

        embedding_vectors: list[list[float]] = []

        for embedding_response in response.embeddings:
            if embedding_response.values is None:
                raise ValueError("Gemini returned an empty embedding")

            embedding_vectors.append(embedding_response.values)

        return embedding_vectors