class CourseNotFoundError(Exception):
    """Se lanza cuando un curso no existe en el sistema."""

    def __init__(self, course_id: int) -> None:
        super().__init__(f"Course with id={course_id} was not found.")
        self.course_id = course_id

class CourseForbiddenError(Exception):
    """Se lanza cuando el curso no está asociado al usuario"""

    def __init__(self, course_id: int, user_id: int) -> None:
        self.course_id = course_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is not allowed to access course {course_id}.")

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

class TopicNotInSyllabusError(ValueError):
    """Excepción lanzada cuando el tema no se encuentra en el sílabo del curso."""
    def __init__(self, message="El tema solicitado no se encuentra dentro del sílabo del curso."):
        super().__init__(message)

class NoSyllabusError(ValueError):
    def __init__(self, message="No se encontró un silabo para el curso"):
        super().__init__(message)


class InvalidFileTypeError(Exception):
    def __init__(self, content_type: str):
        super().__init__(f"File type not allowed: {content_type}")
        self.content_type = content_type


class FileTooLargeError(Exception):
    def __init__(self, size: int):
        super().__init__(f"File too large: {size} bytes")
        self.size = size

class DocumentForbiddenError(Exception):
    def __init__(self):
        super().__init__("You are not allowed to access this document")


class SingleDocumentNotFoundError(Exception):
    def __init__(self, document_id: int):
        super().__init__(f"Document {document_id} not found")
        self.document_id = document_id