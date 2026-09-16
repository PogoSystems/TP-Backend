from modules.content_processing.domain.services.rrf_fusion_service import RRFFusionService
from modules.content_processing.infrastructure.models.document_chunk_model import DocumentChunkModel


def _make_dummy_chunk(chunk_id: int, content: str = "test") -> DocumentChunkModel:
    chunk = DocumentChunkModel()
    chunk.id = chunk_id
    chunk.raw_content = content
    chunk.enriched_content = content
    chunk.token_count = 10
    chunk.heading_path = []
    chunk.chunk_index = chunk_id
    chunk.document_id = 1
    return chunk


def test_rrf_both_empty():
    res = RRFFusionService.fuse(dense_chunks=[], lexical_chunks=[], top_k=5)
    assert res == []


def test_rrf_dense_only():
    c1 = _make_dummy_chunk(1)
    c2 = _make_dummy_chunk(2)
    res = RRFFusionService.fuse(dense_chunks=[c1, c2], lexical_chunks=[], top_k=2)
    assert [c.id for c in res] == [1, 2]


def test_rrf_lexical_only():
    c1 = _make_dummy_chunk(1)
    c2 = _make_dummy_chunk(2)
    res = RRFFusionService.fuse(dense_chunks=[], lexical_chunks=[c2, c1], top_k=2)
    assert [c.id for c in res] == [2, 1]


def test_rrf_joint_boost():
    # c1 is rank 2 in dense, but rank 1 in lexical -> should beat c2 which is only rank 1 in dense
    c1 = _make_dummy_chunk(1)
    c2 = _make_dummy_chunk(2)
    c3 = _make_dummy_chunk(3)

    dense = [c2, c1]  # c2 rank 1, c1 rank 2
    lexical = [c1, c3]  # c1 rank 1, c3 rank 2

    # RRF score for c1 = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.032522
    # RRF score for c2 = 1/(60+1) = 0.016393
    # RRF score for c3 = 1/(60+2) = 0.016129
    res = RRFFusionService.fuse(dense_chunks=dense, lexical_chunks=lexical, top_k=3)
    assert [c.id for c in res] == [1, 2, 3]


def test_rrf_top_k_limiting():
    chunks = [_make_dummy_chunk(i) for i in range(1, 10)]
    res = RRFFusionService.fuse(dense_chunks=chunks, lexical_chunks=[], top_k=3)
    assert len(res) == 3
    assert [c.id for c in res] == [1, 2, 3]
