from pathlib import Path

from modules.content_processing.application.services.content_preparation_service import (
    ContentPreparationService,
)
from modules.content_processing.domain.value_objects.prepared_content import PreparedDocument
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore


class StubExtractor:
    def extract_markdown(self, path: Path) -> tuple[str, int]:
        return "# Title\nIntro.\n\n## Section\nBody text.", 2


def test_local_document_store_writes_file(tmp_path: Path) -> None:
    store = LocalDocumentStore(base_path=tmp_path)
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4 fake")

    storage_key = store.store_pdf(source)
    stored_path = tmp_path / storage_key

    assert stored_path.exists()


def test_preparation_service_builds_prepared_document(tmp_path: Path) -> None:
    store = LocalDocumentStore(base_path=tmp_path)
    service = ContentPreparationService(document_store=store, extractor=StubExtractor())

    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4 fake")

    prepared = service.prepare_pdf(source_path=source, title="Doc")

    assert isinstance(prepared, PreparedDocument)
    assert prepared.raw.document_type == "pdf"
    assert prepared.sections[0].metadata["storage_key"].endswith(".pdf")
    assert prepared.sections[-1].metadata["document_title"] == "Doc"