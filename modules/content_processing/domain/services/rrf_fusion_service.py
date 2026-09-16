from typing import Sequence
from modules.content_processing.infrastructure.models.document_chunk_model import DocumentChunkModel


class RRFFusionService:
    """
    Domain service to fuse multiple ranked lists of chunks using
    Reciprocal Rank Fusion (RRF), standardizing dense vector search
    and lexical search score combinations.
    """

    DEFAULT_RRF_K: int = 60

    @classmethod
    def fuse(
        cls,
        *,
        dense_chunks: Sequence[DocumentChunkModel],
        lexical_chunks: Sequence[DocumentChunkModel],
        top_k: int = 5,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> list[DocumentChunkModel]:
        """
        Fuses dense and lexical candidate chunks using the RRF formula:
            RRF_score(d) = sum(1.0 / (rrf_k + rank(d)))
        
        Args:
            dense_chunks: Ranked chunks from dense vector similarity search.
            lexical_chunks: Ranked chunks from lexical full-text search.
            top_k: Number of highest ranking fused chunks to return.
            rrf_k: Smoothing constant (default 60).

        Returns:
            Deduplicated list of top_k DocumentChunkModel instances ordered by fused score descending.
        """
        if not dense_chunks and not lexical_chunks:
            return []

        scores: dict[int, float] = {}
        chunk_map: dict[int, DocumentChunkModel] = {}

        # Score dense ranked candidates (1-based rank)
        for rank, chunk in enumerate(dense_chunks, start=1):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))

        # Score lexical ranked candidates (1-based rank)
        for rank, chunk in enumerate(lexical_chunks, start=1):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))

        # Sort chunk IDs by score descending
        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        return [chunk_map[cid] for cid in sorted_ids[:top_k]]
