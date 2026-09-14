from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from modules.course_management.infrastructure.models import CourseModel
from modules.quiz_generation.infrastructure.models.question_model import QuestionModel
from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel
from modules.quiz_management.infrastructure.models import QuestionAttemptModel, QuizAttemptModel


class MetacognitionQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_raw_attempts(self, user_id: int, course_id: int | None = None) -> list[dict]:
        """
        Retorna cada intento completado que tenga predicción:
        attempt_id, quiz_id, quiz_title, course_id, course_name, submitted_at,
        expected_correct, total_questions, actual_correct
        """
        stmt = (
            select(
                QuizAttemptModel.id.label("attempt_id"),
                QuizAttemptModel.quiz_id,
                QuizModel.title.label("quiz_title"),
                CourseModel.id.label("course_id"),
                CourseModel.name.label("course_name"),
                QuizAttemptModel.submitted_at,
                QuizAttemptModel.expected_correct_answers.label("expected_correct"),
                func.count(QuestionAttemptModel.id).label("total_questions"),
                func.coalesce(func.sum(case((QuestionAttemptModel.is_correct == True, 1), else_=0)), 0).label("actual_correct"),
            )
            .join(QuizModel, QuizAttemptModel.quiz_id == QuizModel.id)
            .join(CourseModel, QuizModel.course_id == CourseModel.id)
            .join(QuestionAttemptModel, QuizAttemptModel.id == QuestionAttemptModel.quiz_attempt_id)
            .where(
                QuizAttemptModel.user_id == user_id,
                QuizAttemptModel.expected_correct_answers.isnot(None),
                QuizAttemptModel.submitted_at.isnot(None),
            )
        )
        if course_id is not None:
            stmt = stmt.where(CourseModel.id == course_id)

        stmt = stmt.group_by(
            QuizAttemptModel.id,
            QuizAttemptModel.quiz_id,
            QuizModel.title,
            CourseModel.id,
            CourseModel.name,
            QuizAttemptModel.submitted_at,
            QuizAttemptModel.expected_correct_answers,
        ).order_by(QuizAttemptModel.submitted_at.desc())

        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_raw_bloom_data(self, user_id: int, course_id: int | None = None) -> list[dict]:
        """
        Retorna preguntas agrupadas por intento y nivel de Bloom para calcular
        la distribución proporcional.
        """
        sub_total = (
            select(
                QuestionAttemptModel.quiz_attempt_id,
                func.count(QuestionAttemptModel.id).label("attempt_total_questions"),
            )
            .group_by(QuestionAttemptModel.quiz_attempt_id)
            .subquery()
        )

        stmt = (
            select(
                QuestionModel.bloom_level,
                QuizAttemptModel.expected_correct_answers,
                sub_total.c.attempt_total_questions,
                func.count(QuestionAttemptModel.id).label("bloom_questions_count"),
                func.coalesce(func.sum(case((QuestionAttemptModel.is_correct == True, 1), else_=0)), 0).label("bloom_actual_correct"),
            )
            .join(QuizAttemptModel, QuestionAttemptModel.quiz_attempt_id == QuizAttemptModel.id)
            .join(QuestionModel, QuestionAttemptModel.question_id == QuestionModel.id)
            .join(QuizModel, QuizAttemptModel.quiz_id == QuizModel.id)
            .join(sub_total, QuizAttemptModel.id == sub_total.c.quiz_attempt_id)
            .where(
                QuizAttemptModel.user_id == user_id,
                QuizAttemptModel.expected_correct_answers.isnot(None),
                QuizAttemptModel.submitted_at.isnot(None),
            )
        )
        if course_id is not None:
            stmt = stmt.where(QuizModel.course_id == course_id)

        stmt = stmt.group_by(
            QuestionModel.bloom_level,
            QuizAttemptModel.id,
            QuizAttemptModel.expected_correct_answers,
            sub_total.c.attempt_total_questions,
        )

        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_course_name(self, course_id: int) -> str | None:
        stmt = select(CourseModel.name).where(CourseModel.id == course_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
