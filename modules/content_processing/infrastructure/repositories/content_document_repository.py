from sqlalchemy.ext.asyncio import AsyncSession

from modules.content_processing.domain.aggregates import ContentDocumentAggregate
from modules.content_processing.infrastructure.models import ContentDocumentModel


class ContentDocumentRepository:
    """
    Repository for the persistence of the content document in the database
    """
    def __init__(self,
                 session: AsyncSession
                 ) -> None:
        self._session = session

    """
    Save the content document in the database
    """
    async def save_document(self,
                            document: ContentDocumentAggregate
                            ) -> ContentDocumentAggregate:

        # Maps the values of the content document aggregate to the content document model
        model = ContentDocumentModel(
            course_id=document.course_id,
            user_id=document.user_id,
            title=document.title,
            storage_key=document.storage_key,
        )
        self._session.add(model)

        await self._session.flush()

        # it returns all the values for future scenarios, not only the id of the document
        return ContentDocumentAggregate(
            id=model.id,
            course_id=model.course_id,
            user_id=model.user_id,
            title=model.title,
            storage_key=model.storage_key,
            created_at=model.created_at,
        )