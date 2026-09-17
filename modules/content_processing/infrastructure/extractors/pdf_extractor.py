from pathlib import Path

import fitz
import pymupdf4llm


class PdfContentExtractor:
    def extract_markdown(self, path: Path) -> tuple[str, int]:
        """Extract markdown text and page count from a PDF."""
        with fitz.open(str(path)) as pdf:
            page_count = pdf.page_count
            markdown = pymupdf4llm.to_markdown(pdf)

        # Liberar la caché interna de MuPDF en C
        fitz.TOOLS.store_shrink(100)

        return markdown, page_count