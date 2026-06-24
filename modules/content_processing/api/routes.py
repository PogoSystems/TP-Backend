from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient

from core.db.database import get_db
from core.supabase import get_supabase_client
from modules.content_processing.application.services.document_service import DocumentService
from modules.content_processing.infrastructure.repositories.document_repository import DocumentRepository
from modules.content_processing.infrastructure.storage.supabase_storage import SupabaseStorageAdapter
from modules.content_processing.schemas import DocumentResponse


router = APIRouter(prefix="/documents", tags=["documents"])

def get_document_service(session: Annotated[AsyncSession, Depends(get_db)], supabase: Annotated[AsyncClient, Depends(get_supabase_client)],) -> DocumentService:
    return DocumentService(
        repository=DocumentRepository(session),
        storage=SupabaseStorageAdapter(supabase),
    )

DocSvc = Annotated[DocumentService, Depends(get_document_service)]

# TODO: REPLACE THE TEMP_USER_ID IN UPLOAD_DOCUMENT, LIST_DOCUMENTS AND DELETE DOCUMENTS WHEN AUTHENTICATION IS IMPLEMENTED, IT SHOULD RECEIVE THE JWT TOKEN AND EXTRACT THE USER ID FROM IT
TEMP_USER_ID=1
@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir un nuevo documento para un curso")


async def upload_document(service: DocSvc, file: UploadFile = File(...), course_id: int = Form(...)) -> DocumentResponse:
    data = await file.read()
    try:
        doc = await service.upload_document(
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            file_data=data,
            course_id=course_id,
            current_user_id=TEMP_USER_ID
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    assert doc.id is not None
    return DocumentResponse(
        id=doc.id,
        course_id=doc.course_id,
        user_id=doc.user_id,
        title=doc.title,
        document_type=doc.document_type,
        processing_status=doc.processing_status.value,
        created_at=doc.created_at,
        syllabus=doc.syllabus
    )

@router.get(
    "/courses/{course_id}",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar documentos por curso"
)
async def list_documents(course_id: int, service:DocSvc) -> list[DocumentResponse]:
    documents = await service.list_documents(course_id, TEMP_USER_ID)
    return [
        DocumentResponse(
            id=d.id,
            course_id=d.course_id,
            user_id=d.user_id,
            title=d.title,
            document_type=d.document_type,
            processing_status=d.processing_status.value,
            created_at=d.created_at,
            syllabus = d.syllabus
        )
        for d in documents if d.id is not None
    ]

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un documento"
)
async def delete_document(document_id:int, service:DocSvc) -> None:
    try:
        await service.delete_document(document_id, TEMP_USER_ID)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))