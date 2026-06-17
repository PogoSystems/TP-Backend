from typing import Protocol

from modules.content_processing.domain.aggregates import ContentDocumentAggregate


class DocumentRepositoryPort(Protocol):

    """Save a document to the repository."""
    async def save(self, document: ContentDocumentAggregate) -> ContentDocumentAggregate:
        ...

    """ Get a document by document id"""
    async def find_by_id(self, document_id: int) -> ContentDocumentAggregate | None:
        ...

    """ Get a list of the documents owned by the user for course id"""
    async def find_all_by_course(self,course_id:int, user_id:int) -> list[ContentDocumentAggregate]:
        ...

    """ Delete a document by document id"""
    async def delete_by_id(self, document_id: int) -> None:
        ...