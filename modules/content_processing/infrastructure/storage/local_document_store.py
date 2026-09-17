from pathlib import Path
from uuid import uuid4


class LocalDocumentStore:
    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or (Path(__file__).resolve().parent.parent / "carpet")

    def store_document(self, source_path: Path) -> str:
        """Persist a document into the local carpet and return a relative storage key."""
        self._base_path.mkdir(parents=True, exist_ok=True)
        suffix = source_path.suffix.lower() or ".bin"
        file_name = f"{uuid4().hex}{suffix}"
        destination = self._base_path / file_name
        destination.write_bytes(source_path.read_bytes())
        return file_name

    def store_pdf(self, source_path: Path) -> str:
        """Persist a PDF into the local carpet and return a relative storage key."""
        return self.store_document(source_path)