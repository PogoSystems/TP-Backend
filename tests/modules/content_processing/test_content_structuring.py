from modules.content_processing.application.services import structure_sections


def test_structure_sections_creates_preamble_and_headings() -> None:
    markdown = "Lead paragraph.\n\n# Title\nIntro.\n\n## Section A\nA text.\n\n## Section B\nB text."
    sections = structure_sections(markdown)

    assert [section.heading for section in sections] == [
        "Preamble",
        "Title",
        "Section A",
        "Section B",
    ]
    assert sections[0].text == "Lead paragraph."
    assert sections[2].level == 2