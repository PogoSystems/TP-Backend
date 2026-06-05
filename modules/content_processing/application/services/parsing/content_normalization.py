import re


def normalize_markdown(markdown: str) -> str:
    """Normalize whitespace and line-break hyphenation in extracted markdown."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()