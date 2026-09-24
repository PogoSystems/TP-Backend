"""
Extractor asíncrono de muestras de base de datos (PostgreSQL / Supabase).
Permite recuperar cuestionarios existentes, sus preguntas, opciones,
explicaciones y los fragmentos de contexto (document_chunk) asociados.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import SessionLocal
from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel
from modules.quiz_generation.infrastructure.models.question_model import QuestionModel
from modules.quiz_generation.infrastructure.models.answer_model import AnswerModel
from modules.quiz_management.infrastructure.models import QuizSourceDocumentModel
from modules.content_processing.infrastructure.models.content_document_model import ContentDocumentModel
from modules.content_processing.infrastructure.models.document_chunk_model import DocumentChunkModel

logger = logging.getLogger(__name__)


class DbSampleExtractor:
    """
    Servicio de extracción de muestras reales desde Supabase/PostgreSQL.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self._external_session = session

    async def get_quizzes_summary(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retorna la lista de cuestionarios disponibles en la base de datos con metadata.
        """
        async def _query(session: AsyncSession):
            stmt = select(QuizModel).order_by(QuizModel.id.desc()).limit(limit)
            result = await session.execute(stmt)
            quizzes = result.scalars().all()

            summary = []
            for q in quizzes:
                q_stmt = select(QuestionModel).where(QuestionModel.quiz_id == q.id)
                q_res = await session.execute(q_stmt)
                questions = q_res.scalars().all()

                summary.append({
                    "quiz_id": q.id,
                    "title": q.title or f"Quiz #{q.id}",
                    "course_id": q.course_id,
                    "user_id": q.user_id,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                    "total_questions": len(questions),
                })
            return summary

        if self._external_session:
            return await _query(self._external_session)
        async with SessionLocal() as session:
            return await _query(session)

    async def extract_quiz_with_context(self, quiz_id: int) -> Optional[Dict[str, Any]]:
        """
        Extrae un cuestionario completo (preguntas, respuestas, explicaciones)
        y lo vincula con el contexto textual recuperado desde los chunks de sus documentos fuente.
        """
        async def _query(session: AsyncSession):
            # 1. Obtener Quiz
            q_stmt = select(QuizModel).where(QuizModel.id == quiz_id)
            q_res = await session.execute(q_stmt)
            quiz = q_res.scalar_one_or_none()
            if not quiz:
                return None

            # 2. Obtener Preguntas y Respuestas
            questions_stmt = select(QuestionModel).where(QuestionModel.quiz_id == quiz.id).order_by(QuestionModel.id)
            questions_res = await session.execute(questions_stmt)
            questions_models = questions_res.scalars().all()

            questions_data = []
            for qm in questions_models:
                ans_stmt = select(AnswerModel).where(AnswerModel.question_id == qm.id)
                ans_res = await session.execute(ans_stmt)
                answers = ans_res.scalars().all()

                correct_answers = [a.text for a in answers if a.is_correct]
                all_answers = [{"text": a.text, "is_correct": a.is_correct} for a in answers]

                questions_data.append({
                    "question_id": qm.id,
                    "text": qm.text,
                    "bloom_level": qm.bloom_level.lower() if qm.bloom_level else "remember",
                    "score": qm.score,
                    "explanation": qm.explanation,
                    "answers": all_answers,
                    "correct_answers": correct_answers,
                })

            # 3. Obtener Documentos Fuente (Document Chunks)
            # Primero intentar mediante QuizSourceDocumentModel
            src_stmt = select(QuizSourceDocumentModel.document_id).where(QuizSourceDocumentModel.quiz_id == quiz.id)
            src_res = await session.execute(src_stmt)
            doc_ids = src_res.scalars().all()

            # Si no hay asociación explícita, recuperar documentos del mismo curso
            if not doc_ids:
                doc_stmt = select(ContentDocumentModel.id).where(ContentDocumentModel.course_id == quiz.course_id)
                doc_res = await session.execute(doc_stmt)
                doc_ids = doc_res.scalars().all()

            # 4. Recuperar Chunks de los documentos
            chunks_data = []
            if doc_ids:
                chunks_stmt = select(DocumentChunkModel).where(
                    DocumentChunkModel.document_id.in_(doc_ids)
                ).order_by(DocumentChunkModel.document_id, DocumentChunkModel.chunk_index)
                chunks_res = await session.execute(chunks_stmt)
                chunk_models = chunks_res.scalars().all()

                for c in chunk_models:
                    chunks_data.append({
                        "chunk_id": c.id,
                        "document_id": c.document_id,
                        "chunk_index": c.chunk_index,
                        "heading_path": " > ".join(c.heading_path) if c.heading_path else "",
                        "content": c.enriched_content or c.raw_content,
                    })

            full_context_text = "\n\n".join([
                f"[Fragmento #{c['chunk_index']} - {c['heading_path']}]:\n{c['content']}"
                for c in chunks_data
            ])

            return {
                "quiz_id": quiz.id,
                "title": quiz.title or f"Quiz #{quiz.id}",
                "course_id": quiz.course_id,
                "user_id": quiz.user_id,
                "questions": questions_data,
                "chunks_count": len(chunks_data),
                "chunks": chunks_data,
                "context_text": full_context_text,
            }

        if self._external_session:
            return await _query(self._external_session)
        async with SessionLocal() as session:
            return await _query(session)

    async def get_all_existing_questions(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Extrae un lote plano de preguntas registradas en BD para análisis de Bloom.
        """
        async def _query(session: AsyncSession):
            stmt = select(QuestionModel).order_by(QuestionModel.id.desc()).limit(limit)
            result = await session.execute(stmt)
            questions = result.scalars().all()

            output = []
            for q in questions:
                ans_stmt = select(AnswerModel).where(AnswerModel.question_id == q.id)
                ans_res = await session.execute(ans_stmt)
                answers = ans_res.scalars().all()

                output.append({
                    "question_id": q.id,
                    "quiz_id": q.quiz_id,
                    "text": q.text,
                    "bloom_level": q.bloom_level.lower() if q.bloom_level else "remember",
                    "explanation": q.explanation,
                    "answers": [a.text for a in answers],
                    "correct_answers": [a.text for a in answers if a.is_correct],
                })
            return output

        if self._external_session:
            return await _query(self._external_session)
        async with SessionLocal() as session:
            return await _query(session)
