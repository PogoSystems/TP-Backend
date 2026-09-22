from pathlib import Path

from modules.content_processing.application.services.parsing.content_metadata import enhance_section_metadata
from modules.content_processing.application.services.parsing.content_normalization import normalize_markdown
from modules.content_processing.application.services.parsing.content_structuring import structure_sections
from modules.content_processing.domain.value_objects.prepared_content import PreparedDocument, RawContent
from typing import Any
from modules.content_processing.infrastructure.extractors.document_extractor import DocumentContentExtractor
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore


class ContentPreparationService:
    def __init__(
        self,
        *,
        document_store: LocalDocumentStore,
        extractor: Any | None = None,
    ) -> None:
        self._document_store = document_store
        self._extractor = extractor or DocumentContentExtractor()

    def prepare_document(
        self,
        *,
        source_path: Path,
        title: str,
        document_type: str | None = None,
    ) -> PreparedDocument:
        """Store a document locally and prepare structured content for chunking."""
        doc_type = (document_type or source_path.suffix.lstrip(".")).lower()
        storage_key = self._document_store.store_document(source_path)

        try:
            markdown, page_count = self._extractor.extract_markdown(source_path, document_type=doc_type)
        except TypeError:
            markdown, page_count = self._extractor.extract_markdown(source_path)

        raw = RawContent(
            title=title,
            storage_key=storage_key,
            document_type=doc_type,
            markdown=markdown,
            page_count=page_count,
        )
        normalized = normalize_markdown(markdown)
        sections = structure_sections(normalized)
        enriched_sections = enhance_section_metadata(
            sections=sections,
            storage_key=storage_key,
            document_title=title,
            document_type=doc_type,
        )
        return PreparedDocument(raw=raw, normalized_text=normalized, sections=enriched_sections)

    def prepare_pdf(self, *, source_path: Path, title: str) -> PreparedDocument:
        """Store a PDF locally and prepare structured content for chunking (backward compatibility)."""
        return self.prepare_document(source_path=source_path, title=title, document_type="pdf")