import concurrent.futures
from pathlib import Path

import fitz
import pymupdf4llm


def _extract_pdf_worker(path_str: str) -> tuple[str, int]:
    """Worker ejecutado en un proceso separado para que el SO reclame la memoria de C al morir el subproceso."""
    with fitz.open(path_str) as pdf:
        page_count = pdf.page_count
        markdown = pymupdf4llm.to_markdown(
            pdf,
            write_images=False,
            embed_images=False,
            use_ocr=False,
        )

    fitz.TOOLS.store_shrink(100)
    return markdown, page_count


class PdfContentExtractor:
    def __init__(self, *, use_subprocess: bool = True) -> None:
        self._use_subprocess = use_subprocess

    def extract_markdown(self, path: Path) -> tuple[str, int]:
        """Extract markdown text and page count from a PDF in an isolated process to reclaim C memory."""
        resolved_path = str(Path(path).resolve())
        if self._use_subprocess:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                return executor.submit(_extract_pdf_worker, resolved_path).result()
        return _extract_pdf_worker(resolved_path)