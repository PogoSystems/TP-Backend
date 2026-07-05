from pathlib import Path

import fitz
import pymupdf4llm


class PdfContentExtractor:
    def extract_markdown(self, path: Path) -> tuple[str, int]:
        """Extract markdown text and page count from a PDF."""
        markdown = pymupdf4llm.to_markdown(str(path))
        with fitz.open(str(path)) as pdf:
            page_count = pdf.page_count
        return markdown, page_count