from modules.content_processing.application.services.parsing.content_metadata import enhance_section_metadata
from modules.content_processing.domain.value_objects.prepared_content import StructuredSection


def test_enhance_section_metadata_adds_document_fields() -> None:
    sections = [
        StructuredSection(index=0, heading="Intro", level=1, text="Body", metadata={"custom": "x"})
    ]

    enriched = enhance_section_metadata(
        sections=sections,
        storage_key="carpet/doc.pdf",
        document_title="Doc",
        document_type="pdf",
    )

    assert enriched[0].metadata["storage_key"] == "carpet/doc.pdf"
    assert enriched[0].metadata["document_title"] == "Doc"
    assert enriched[0].metadata["document_type"] == "pdf"
    assert enriched[0].metadata["section_index"] == 0
    assert enriched[0].metadata["token_count"] == 1
    assert enriched[0].metadata["custom"] == "x"