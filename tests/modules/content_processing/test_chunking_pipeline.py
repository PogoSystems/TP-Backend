import dataclasses
import json
from pathlib import Path

from modules.content_processing.infrastructure.extractors.pdf_extractor import (
    PdfContentExtractor,
)
from modules.content_processing.application.services.parsing.content_preparation_service import (
    ContentPreparationService,
)
from modules.content_processing.infrastructure.storage.local_document_store import (
    LocalDocumentStore,
)

from modules.content_processing.application.services.chunking.chunking_service import (
    ChunkingService,
)
from modules.content_processing.infrastructure.tokenizers.token_counter import (
    TokenCounter,
)


def test_chunking_service_with_real_pdf(tmp_path: Path) -> None:
    """
    Integration test:

    PDF
        ↓
    PdfContentExtractor
        ↓
    ContentPreparationService
        ↓
    PreparedDocument
        ↓
    ChunkingService
        ↓
    ChunkedDocument
    """

    # Locate the real PDF fixture
    current_dir = Path(__file__).parent
    pdf_path = current_dir / "fixtures" / "muestra.pdf"

    assert pdf_path.exists(), (
        "Missing test PDF in fixtures folder"
    )

    # -------------------------------
    # STEP 1: Parse and prepare document
    # -------------------------------

    store = LocalDocumentStore(base_path=tmp_path)

    extractor = PdfContentExtractor()

    preparation_service = ContentPreparationService(
        document_store=store,
        extractor=extractor,
    )

    prepared_doc = preparation_service.prepare_pdf(
        source_path=pdf_path,
        title="Documento Real",
    )

    # Verify preparation succeeded
    assert prepared_doc.sections
    assert prepared_doc.raw.document_type == "pdf"

    # -------------------------------
    # STEP 2: Chunk document
    # -------------------------------

    chunking_service = ChunkingService(
        token_counter=TokenCounter(),

        # Use a small value during testing
        # so chunk splitting is easier to verify
        max_chunk_tokens=100,
    )

    chunked_doc = chunking_service.chunk_document(
        prepared_doc
    )

    # -------------------------------
    # STEP 3: Assertions
    # -------------------------------

    assert len(chunked_doc.chunks) > 0

    print("\n")
    print("=" * 100)
    print("CHUNKING RESULTS")
    print("=" * 100)

    print(f"Document title: {chunked_doc.document_title}")
    print(f"Total chunks: {len(chunked_doc.chunks)}")

    # Show first chunks for quick inspection
    for chunk in chunked_doc.chunks[:5]:

        print("\n")
        print("-" * 80)

        print(f"Chunk ID: {chunk.chunk_id}")

        print(
            f"Heading Path: "
            f"{' > '.join(chunk.heading_path)}"
        )

        print(f"Chunk Index: {chunk.chunk_index}")
        print(f"Token Count: {chunk.token_count}")

        print("\nMetadata:")
        print(chunk.metadata)

        print("\nEnriched Text Preview:")
        print(chunk.enriched_text[:500])

    # -------------------------------
    # STEP 4: Export complete result
    # -------------------------------

    output_file = pdf_path.with_name(
        f"{pdf_path.stem}_chunks.json"
    )

    def object_to_dict(obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)

        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        if hasattr(obj, "dict"):
            return obj.dict()

        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return str(obj)

    json_data = json.dumps(
        object_to_dict(chunked_doc),
        indent=4,
        ensure_ascii=False,
        default=str,
    )

    output_file.write_text(
        json_data,
        encoding="utf-8",
    )

    print("\n")
    print(
        f"✅ Chunk inspection file generated:\n"
    )