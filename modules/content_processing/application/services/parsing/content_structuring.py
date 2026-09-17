import io
import re

from modules.content_processing.domain.value_objects.prepared_content import StructuredSection

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def structure_sections(normalized_text: str) -> list[StructuredSection]:
    """Split normalized markdown into structured sections by heading."""
    sections: list[StructuredSection] = []
    current_heading = "Preamble"
    current_level = 0
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, sections, current_heading, current_level
        content = "\n".join(buffer).strip()
        if content:
            sections.append(
                StructuredSection(
                    index=len(sections),
                    heading=current_heading,
                    level=current_level,
                    text=content,
                )
            )
        buffer = []

    for line in io.StringIO(normalized_text):
        line = line.rstrip("\r\n")
        match = HEADING_RE.match(line)
        if match:
            flush()
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            continue
        buffer.append(line)

    flush()
    return sections