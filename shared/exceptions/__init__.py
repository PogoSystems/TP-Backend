class CourseNotFoundError(Exception):
    """Se lanza cuando un curso no existe en el sistema."""

    def __init__(self, course_id: int) -> None:
        super().__init__(f"Course with id={course_id} was not found.")
        self.course_id = course_id


class DocumentNotFoundError(Exception):
    """Se lanza cuando uno o más documentos no existen en el sistema."""

    def __init__(self, document_ids: list[int]) -> None:
        super().__init__(f"Documents with ids={document_ids} were not found.")
        self.document_ids = document_ids


class DocumentProcessingError(Exception):
    """Se lanza cuando falla el procesamiento de un documento."""

    def __init__(self, document_id: int, reason: str) -> None:
        super().__init__(f"Failed to process document id={document_id}: {reason}")
        self.document_id = document_id
