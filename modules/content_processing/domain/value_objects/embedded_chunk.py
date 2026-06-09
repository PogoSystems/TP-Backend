from dataclasses import dataclass

from modules.content_processing.domain.value_objects.chunk import Chunk


@dataclass(slots=True)
class EmbeddedChunk:
    """Value object that represents an embedded chunk"""
    chunk: Chunk # original chunk
    embedding: list[float] # vector generated for the embedding model

    def __post_init__(self) -> None:
        if not self.chunk:
            raise ValueError("chunk cannot be empty")
        if not self.embedding:
            raise ValueError("embedding cannot be empty")
