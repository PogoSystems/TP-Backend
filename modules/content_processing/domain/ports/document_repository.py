from typing import Protocol

from modules.content_processing.domain.aggregates import ContentDocumentAggregate
from modules.content_processing.domain.value_objects.processing_status import ProcessingStatus


class DocumentRepositoryPort(Protocol):

    """Save a document to the repository."""
    async def save(self, document: ContentDocumentAggregate) -> ContentDocumentAggregate:
        ...

    """ Get a document by document id"""
    async def find_by_id(self, document_id: int) -> ContentDocumentAggregate | None:
        ...

    """ Get multiple documents by a list of ids"""
    async def find_by_ids(self, document_ids: list[int]) -> list[ContentDocumentAggregate]:
        ...

    """ Get a list of the documents owned by the user for course id"""
    async def find_all_by_course(self,course_id:int, user_id:int) -> list[ContentDocumentAggregate]:
        ...

    """ Delete a document by document id"""
    async def delete_by_id(self, document_id: int) -> None:
        ...

    """ Update the processing status of a document"""
    async def update_status(self, document_id: int, status: ProcessingStatus) -> None:
        ...