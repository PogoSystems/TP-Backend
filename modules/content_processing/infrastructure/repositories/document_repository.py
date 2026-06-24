from datetime import datetime, timezone

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.content_processing.domain.aggregates import ContentDocumentAggregate
from modules.content_processing.domain.value_objects.processing_status import ProcessingStatus
from modules.content_processing.infrastructure.models import ContentDocumentModel


class DocumentRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session=session


    async def save(self, document:ContentDocumentAggregate) -> ContentDocumentAggregate:
        model = self._to_model(document)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_aggregate(model)

    async def find_by_id(self, document_id: int) -> ContentDocumentAggregate| None:
        model = await self._session.get(ContentDocumentModel, document_id)
        return self._to_aggregate(model) if model else None

    async def find_all_by_course(self, course_id:int, user_id:int) -> list[ContentDocumentAggregate]:
        smtm=(select(ContentDocumentModel)
              .where(ContentDocumentModel.course_id==course_id, ContentDocumentModel.user_id==user_id)
            .order_by(ContentDocumentModel.created_at.desc())
            )
        result= await self._session.execute(smtm)
        return [self._to_aggregate(m) for m in result.scalars().all()]

    async def find_by_ids(self, document_ids: list[int]) -> list[ContentDocumentAggregate]:
        """Retrieve multiple documents by a list of IDs in a single query."""
        stmt = ( #select statements
            select(ContentDocumentModel)
            .where(ContentDocumentModel.id.in_(document_ids))
        )
        result = await self._session.execute(stmt)
        return [self._to_aggregate(m) for m in result.scalars().all()]

    async def update_status(self, document_id: int, status: ProcessingStatus) -> None:
        """Update the processing status (and processed_at if COMPLETED) of a document."""
        values: dict = {"processing_status": status.value}
        if status == ProcessingStatus.COMPLETED:
            # Usamos replace(tzinfo=None) para crear un naive datetime en UTC
            # y así evitar el error de asyncpg con TIMESTAMP WITHOUT TIME ZONE
            values["processed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            update(ContentDocumentModel)
            .where(ContentDocumentModel.id == document_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete_by_id(self, document_id:int) -> None:
        smtm= delete(ContentDocumentModel).where(ContentDocumentModel.id==document_id)
        await self._session.execute(smtm)
        await self._session.flush()

    @staticmethod
    def _to_aggregate (model: ContentDocumentModel) -> ContentDocumentAggregate:
        return ContentDocumentAggregate(
            id=model.id,
            course_id=model.course_id,
            user_id=model.user_id,
            title=model.title,
            document_type=model.document_type,
            storage_key=model.storage_key,
            syllabus=model.syllabus,
            processing_status=ProcessingStatus(model.processing_status), # to make the convertion of value to processing status object
            processed_at=model.processed_at,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_model(aggregate: ContentDocumentAggregate) -> ContentDocumentModel:
        return ContentDocumentModel(
            course_id=aggregate.course_id,
            user_id=aggregate.user_id,
            title=aggregate.title,
            document_type=aggregate.document_type,
            storage_key=aggregate.storage_key,
            syllabus=aggregate.syllabus,
            processing_status=aggregate.processing_status.value, # to extract the value of the enum
        )