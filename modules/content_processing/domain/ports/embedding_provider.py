from typing import Protocol


class EmbeddingProvider(Protocol):
    """
    Contract for embedding generation providers. It tells what they have to
    implement
    """
    async def generate_embeddings(self,
                                  texts:list[str]
                                  )-> list[list[float]]:
        """
        Generate embeddings for a list of texts
        """