from typing import Protocol


class ContextRetrievalPort(Protocol):
    """
    Port that defines the contract for retrieving relevant textual context
    for quiz generation, abstracting away the underlying storage, embeddings,
    and document processing mechanisms.
    """

    async def get_context_from_course(
        self,
        course_id: int,
        query_text: str,
        limit: int,
    ) -> str:
        """
        Retrieves relevant context by searching across all documents in a course.
        """
        ...

    async def get_context_from_documents(
        self,
        document_ids: list[int],
        query_text: str,
        limit: int,
    ) -> str:
        """
        Retrieves relevant context by searching only within the specified documents.
        Ensures documents are fully processed before searching.
        """
        ...
