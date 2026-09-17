from pathlib import Path

from modules.content_processing.infrastructure.extractors.docx_extractor import DocxContentExtractor
from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor
from modules.content_processing.infrastructure.extractors.pptx_extractor import PptxContentExtractor
from shared.exceptions import InvalidFileTypeError


class DocumentContentExtractor:
    """Caja negra que extrae Markdown y conteo de páginas de archivos PDF, DOCX y PPTX."""

    def __init__(
        self,
        *,
        pdf_extractor: PdfContentExtractor | None = None,
        docx_extractor: DocxContentExtractor | None = None,
        pptx_extractor: PptxContentExtractor | None = None,
    ) -> None:
        self._pdf_extractor = pdf_extractor or PdfContentExtractor()
        self._docx_extractor = docx_extractor or DocxContentExtractor()
        self._pptx_extractor = pptx_extractor or PptxContentExtractor()

    def extract_markdown(self, path: Path, document_type: str | None = None) -> tuple[str, int]:
        kind = (document_type or path.suffix.lstrip(".")).lower()
        if kind == "pdf":
            return self._pdf_extractor.extract_markdown(path)
        elif kind in ("docx", "doc"):
            return self._docx_extractor.extract_markdown(path)
        elif kind in ("pptx", "ppt"):
            return self._pptx_extractor.extract_markdown(path)
        else:
            raise InvalidFileTypeError(f"Formato no soportado para extracción de contenido: {kind}")
