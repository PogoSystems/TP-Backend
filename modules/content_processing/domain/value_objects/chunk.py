from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    """Value object that represent a single chunk of a document"""
    document_title:str
    chunk_index: int
    heading_path: list[str]
    raw_content: str # Original text from the section slice of the json file
    enriched_text: str # Text after the context injection for thhe embedding generation
    token_count: int # for observability
    metadata: dict[str, str | int | float] # for vector filtering

    def __post_init__(self)->None:
        if not self.document_title:
            raise ValueError("document_title cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if not self.heading_path:
            raise ValueError("heading_path cannot be empty")
        if not self.raw_content:
            raise ValueError("raw_content cannot be empty")
        if not self.enriched_text:
            raise ValueError("enriched_text cannot be empty")
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")


@dataclass(slots=True)
class ChunkedDocument:
    """Value object that represents a document that has been split into chunks"""
    document_title: str
    chunks: list[Chunk]

    def __post_init__(self)->None:
        if not self.document_title:
            raise ValueError("document_title cannot be empty")
        if not self.chunks:
            raise ValueError("chunks cannot be empty")