"""Tests unitarios para Casos de Uso - CU02: Gestionar Asignaturas y Sílabos y CU03: Gestionar Material de Estudio."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from modules.content_processing.application.services.document_service import DocumentService
from modules.content_processing.domain.aggregates.content_document import ContentDocumentAggregate
from modules.course_management.domain.aggregates.course import CourseAggregate
from shared.exceptions import (
    InvalidFileTypeError,
    FileTooLargeError,
    CourseNotFoundError,
    CourseForbiddenError,
)


def make_course(course_id: int = 1, user_id: int = 10, name: str = "Algoritmos") -> CourseAggregate:
    """Crea un CourseAggregate de prueba."""
    return CourseAggregate(
        id=course_id,
        user_id=user_id,
        name=name,
    )


def make_document(
    doc_id: int = 1,
    course_id: int = 1,
    user_id: int = 10,
    title: str = "silabo.pdf",
    syllabus: bool = True,
) -> ContentDocumentAggregate:
    """Crea un ContentDocumentAggregate de prueba."""
    return ContentDocumentAggregate(
        id=doc_id,
        course_id=course_id,
        user_id=user_id,
        title=title,
        document_type="pdf",
        storage_key=f"{user_id}/{course_id}/uuid.pdf",
        syllabus=syllabus,
    )


def make_mocks(**kwargs) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Crea mocks para doc_repo, course_repo y storage."""
    doc_repo = MagicMock()
    doc_repo.save = AsyncMock(return_value=kwargs.get("save_doc", None))
    doc_repo.find_by_id = AsyncMock(return_value=kwargs.get("find_doc", None))
    doc_repo.find_all_by_course = AsyncMock(return_value=kwargs.get("list_docs", []))
    doc_repo.delete_by_id = AsyncMock(return_value=None)

    course_repo = MagicMock()
    course_repo.find_by_id = AsyncMock(return_value=kwargs.get("find_course", None))

    storage = MagicMock()
    storage.upload = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=None)

    return doc_repo, course_repo, storage


class TestCU02GestionarSilabos:
    """Pruebas asociadas al caso de uso CU02: Carga y procesamiento de sílabos."""

    @pytest.mark.asyncio
    async def test_upload_syllabus_pdf_success(self) -> None:
        """Flujo principal CU02: Carga exitosa de un sílabo PDF oficial."""
        course = make_course(course_id=1, user_id=10)
        expected_doc = make_document(syllabus=True)
        doc_repo, course_repo, storage = make_mocks(find_course=course, save_doc=expected_doc)

        service = DocumentService(doc_repo, course_repo, storage)
        result = await service.upload_document(
            filename="silabo_2026.pdf",
            content_type="application/pdf",
            file_data=b"%PDF-1.4 mock content",
            course_id=1,
            syllabus=True,
            current_user_id=10,
        )

        storage.upload.assert_called_once()
        doc_repo.save.assert_called_once()
        assert result.syllabus is True

    @pytest.mark.asyncio
    async def test_upload_syllabus_unsupported_format_raises_exception(self) -> None:
        """Flujo alternativo 3a: Rechazo de formato no soportado."""
        course = make_course(course_id=1, user_id=10)
        doc_repo, course_repo, storage = make_mocks(find_course=course)

        service = DocumentService(doc_repo, course_repo, storage)

        with pytest.raises(InvalidFileTypeError):
            await service.upload_document(
                filename="silabo.exe",
                content_type="application/x-msdownload",
                file_data=b"bad file",
                course_id=1,
                syllabus=True,
                current_user_id=10,
            )

        storage.upload.assert_not_called()


class TestCU03GestionarMaterialEstudio:
    """Pruebas asociadas al caso de uso CU03: Carga de material de estudio."""

    @pytest.mark.asyncio
    async def test_upload_study_material_success(self) -> None:
        """Flujo principal CU03: Carga exitosa de material de estudio para RAG."""
        course = make_course(course_id=1, user_id=10)
        expected_doc = make_document(title="unidad1.pdf", syllabus=False)
        doc_repo, course_repo, storage = make_mocks(find_course=course, save_doc=expected_doc)

        service = DocumentService(doc_repo, course_repo, storage)
        result = await service.upload_document(
            filename="unidad1.pdf",
            content_type="application/pdf",
            file_data=b"%PDF content",
            course_id=1,
            syllabus=False,
            current_user_id=10,
        )

        assert result.title == "unidad1.pdf"
        assert result.syllabus is False

    @pytest.mark.asyncio
    async def test_upload_material_exceeds_max_size_raises_exception(self) -> None:
        """Flujo alternativo 3a: Superación del límite de almacenamiento (10MB)."""
        course = make_course(course_id=1, user_id=10)
        doc_repo, course_repo, storage = make_mocks(find_course=course)

        service = DocumentService(doc_repo, course_repo, storage)
        large_data = b"X" * (11 * 1024 * 1024)

        with pytest.raises(FileTooLargeError):
            await service.upload_document(
                filename="gran_libro.pdf",
                content_type="application/pdf",
                file_data=large_data,
                course_id=1,
                syllabus=False,
                current_user_id=10,
            )

    @pytest.mark.asyncio
    async def test_upload_material_course_not_found_raises_exception(self) -> None:
        """Validación de existencia de asignatura antes de asociar material."""
        doc_repo, course_repo, storage = make_mocks(find_course=None)
        service = DocumentService(doc_repo, course_repo, storage)

        with pytest.raises(CourseNotFoundError):
            await service.upload_document(
                filename="material.pdf",
                content_type="application/pdf",
                file_data=b"data",
                course_id=999,
                syllabus=False,
                current_user_id=10,
            )

    @pytest.mark.asyncio
    async def test_upload_material_forbidden_user_raises_exception(self) -> None:
        """Validación de pertenencia de la asignatura al estudiante."""
        course = make_course(course_id=1, user_id=10)
        doc_repo, course_repo, storage = make_mocks(find_course=course)
        service = DocumentService(doc_repo, course_repo, storage)

        with pytest.raises(CourseForbiddenError):
            await service.upload_document(
                filename="material.pdf",
                content_type="application/pdf",
                file_data=b"data",
                course_id=1,
                syllabus=False,
                current_user_id=99,
            )
