
from modules.content_processing.domain.ports.embedding_provider import EmbeddingProvider
from modules.content_processing.domain.value_objects.chunk import Chunk
from modules.content_processing.domain.value_objects.embedded_chunk import EmbeddedChunk


class EmbeddingGenerationService:
    """
    Coordinates the embedding generation process.
    Receives chunks and generates embeddings
    """
    def __init__(self,
                 embedding_provider: EmbeddingProvider
                 )->None:
        self._embedding_provider = embedding_provider # dependency injections


    async def generate_embeddings(self,
                                  chunks:list[Chunk]) -> list[EmbeddedChunk]:

        """
        Generates and assigns embeddings to a list of chunks. It returns a list of embedded
        """
        if not chunks:
            return []

        # only use the enriched text of the chunk for the embedding generation
        texts = [chunk.enriched_text for chunk in chunks]

        # generate embeddings in batch
        embeddings= await self._embedding_provider.generate_embeddings(texts)

        # associate each generated vector with its corresponding chunk
        embedded_chunks: list[EmbeddedChunk] = []
        for chunk, embedding_vector in zip(chunks, embeddings, strict=True):
            embedded_chunks.append(
                EmbeddedChunk(chunk=chunk, embedding=embedding_vector)
            )
            
        return embedded_chunks