from pathlib import Path

from modules.content_processing.application.services.content_metadata import enhance_section_metadata
from modules.content_processing.application.services.content_normalization import normalize_markdown
from modules.content_processing.application.services.content_structuring import structure_sections
from modules.content_processing.domain.value_objects.prepared_content import PreparedDocument, RawContent
from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore


class ContentPreparationService:
    def __init__(
        self,
        *,
        document_store: LocalDocumentStore,
        extractor: PdfContentExtractor,
    ) -> None:
        self._document_store = document_store
        self._extractor = extractor

    def prepare_pdf(self, *, source_path: Path, title: str) -> PreparedDocument:
        """Store a PDF locally and prepare structured content for chunking."""
        storage_key = self._document_store.store_pdf(source_path)
        markdown, page_count = self._extractor.extract_markdown(source_path)
        raw = RawContent(
            title=title,
            storage_key=storage_key,
            document_type="pdf",
            markdown=markdown,
            page_count=page_count,
        )
        normalized = normalize_markdown(markdown)
        sections = structure_sections(normalized)
        enriched_sections = enhance_section_metadata(
            sections=sections,
            storage_key=storage_key,
            document_title=title,
            document_type="pdf",
        )
        return PreparedDocument(raw=raw, normalized_text=normalized, sections=enriched_sections)