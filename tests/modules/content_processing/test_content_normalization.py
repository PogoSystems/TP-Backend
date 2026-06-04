from modules.content_processing.application.services.content_normalization import normalize_markdown


def test_normalize_markdown_cleans_whitespace_and_hyphens() -> None:
    raw = "Intro exam-\nple\n\nMore   text.\n\n\nEnd."
    normalized = normalize_markdown(raw)
    assert normalized == "Intro example\n\nMore text.\n\nEnd."