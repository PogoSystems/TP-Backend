import pytest

from modules.content_processing.domain.value_objects.prepared_content import (
    RawContent,
    StructuredSection,
    PreparedDocument,
)


def test_raw_content_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="title is required"):
        RawContent(
            title="",
            storage_key="carpet/doc.pdf",
            document_type="pdf",
            markdown="text",
            page_count=1,
        )


def test_structured_section_requires_heading_and_text() -> None:
    with pytest.raises(ValueError, match="heading is required"):
        StructuredSection(index=0, heading="", level=1, text="Body")
    with pytest.raises(ValueError, match="text is required"):
        StructuredSection(index=0, heading="Intro", level=1, text="")


def test_prepared_document_requires_sections() -> None:
    raw = RawContent(
        title="Doc",
        storage_key="carpet/doc.pdf",
        document_type="pdf",
        markdown="text",
        page_count=1,
    )
    with pytest.raises(ValueError, match="sections are required"):
        PreparedDocument(raw=raw, normalized_text="text", sections=[])