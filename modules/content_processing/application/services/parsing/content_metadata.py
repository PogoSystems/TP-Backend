from modules.content_processing.domain.value_objects.prepared_content import StructuredSection


def _token_count(text: str) -> int:
    return len(text.split())


def enhance_section_metadata(
    *,
    sections: list[StructuredSection],
    storage_key: str,
    document_title: str,
    document_type: str,
) -> list[StructuredSection]:
    """Attach document metadata to each structured section."""
    enriched: list[StructuredSection] = []
    for section in sections:
        metadata = {
            **section.metadata,
            "storage_key": storage_key,
            "document_title": document_title,
            "document_type": document_type,
            "section_index": section.index,
            "token_count": _token_count(section.text),
        }
        enriched.append(
            StructuredSection(
                index=section.index,
                heading=section.heading,
                level=section.level,
                text=section.text,
                metadata=metadata,
            )
        )
    return enriched