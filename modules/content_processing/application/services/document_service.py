from modules.content_processing.domain.aggregates.content_document import ContentDocumentAggregate
from modules.content_processing.domain.ports.document_repository import DocumentRepositoryPort
from modules.content_processing.domain.ports.storage_port import StoragePort
from modules.content_processing.infrastructure.storage.storage_key_builder import StorageKeyBuilder
from modules.course_management.domain.ports.course_port import CourseRepositoryPort
from shared.exceptions import InvalidFileTypeError, FileTooLargeError, DocumentNotFoundError, DocumentForbiddenError, \
    SingleDocumentNotFoundError, CourseNotFoundError, CourseForbiddenError

ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB


class DocumentService:

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        course_repository: CourseRepositoryPort,
        storage: StoragePort,
    ) -> None:
        self._course_repository = course_repository
        self._repository = repository
        self._storage = storage

    async def upload_document(
        self,
        *,
        filename: str,
        content_type: str,
        file_data: bytes,
        course_id: int,
        syllabus: bool,
        current_user_id: int, # this comes from the JWT token of the authentication
    ) -> ContentDocumentAggregate:
    
        # Validations
        doc_type = ALLOWED_CONTENT_TYPES.get(content_type)
        if not doc_type:
            raise InvalidFileTypeError(content_type)
        if len(file_data) > MAX_FILE_SIZE:
            raise FileTooLargeError(len(file_data))

        course = await self._course_repository.find_by_id(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)

        if course.user_id != current_user_id:
            raise CourseForbiddenError(course_id,current_user_id)

        key = StorageKeyBuilder.build(current_user_id,course_id, filename) # Build the storage_key of the document
        await self._storage.upload(key, file_data, content_type)

        document = ContentDocumentAggregate(
            course_id=course_id,
            title=filename,
            document_type=doc_type,
            storage_key=key,
            user_id=current_user_id,
            syllabus=syllabus,
        )
        return await self._repository.save(document)

    async def list_documents(self, course_id: int, user_id: int) -> list[ContentDocumentAggregate]:
        return await self._repository.find_all_by_course(course_id, user_id)

    async def delete_document(self, document_id: int, user_id: int) -> None:
        document = await self._repository.find_by_id(document_id)

        if document is None:
            raise SingleDocumentNotFoundError(document_id)

        if document.user_id != user_id:
            raise DocumentForbiddenError()

        await self._storage.delete(document.storage_key)
        await self._repository.delete_by_id(document_id)