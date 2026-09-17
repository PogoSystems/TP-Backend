from pathlib import Path
import mammoth


class DocxContentExtractor:
    def extract_markdown(self, path: Path) -> tuple[str, int]:
        """Extract clean Markdown and estimated page count from a DOCX file."""
        with open(path, "rb") as docx_file:
            result = mammoth.convert_to_markdown(docx_file)
            markdown = result.value.strip()

        words = len(markdown.split())
        page_count = max(1, words // 350)
        return markdown, page_count
