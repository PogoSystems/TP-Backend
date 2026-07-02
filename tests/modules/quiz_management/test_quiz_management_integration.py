from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from core.db.database import get_db
from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.quiz_generation.domain.aggregates.answer import AnswerAggregate
from modules.quiz_generation.domain.aggregates.question import QuestionAggregate
from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate
from modules.quiz_generation.infrastructure.repositories.quiz_persistence_repository import QuizPersistenceRepository
from modules.quiz_management.application.services.quiz_attempt_service import QuizAttemptService
from modules.analytics.infrastructure.facades.stats_update_facade import StatsUpdateFacade
from modules.quiz_management.infrastructure.repositories.quiz_attempt_repository import QuizAttemptRepository
from modules.quiz_management.schemas.request_schemas import AnswerSubmission, SubmitQuizRequest
from modules.quiz_management.infrastructure.facades.quiz_read_facade import QuizReadFacade
from modules.quiz_management.infrastructure.models import QuizAttemptModel, QuestionAttemptModel


@pytest.mark.asyncio
async def test_quiz_management_submit_flow_persists_attempt_and_question_attempts() -> None:
    async for session in get_db():
        unique_suffix = uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid4(),
            name=f"Quiz_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"quiz_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        course = CourseModel(name="Course Quiz", description="Integration test course", user_id=user.id)
        session.add(course)
        await session.flush()

        quiz = QuizAggregate(
            user_id=user.id,
            course_id=course.id,
            title="Integration Quiz",
            questions=[
                QuestionAggregate(
                    text="What is Kanban?",
                    bloom_level="remember",
                    score=2,
                    explanation="Method",
                    answers=[
                        AnswerAggregate(text="A board", is_correct=False),
                        AnswerAggregate(text="A workflow method", is_correct=True),
                    ],
                )
            ],
        )
        persisted_quiz = await QuizPersistenceRepository(session).save(quiz)
        await session.flush()

        assert persisted_quiz.id is not None
        assert persisted_quiz.questions[0].id is not None
        assert persisted_quiz.questions[0].answers[1].id is not None

        request = SubmitQuizRequest(
            started_at=datetime(2026, 7, 1, 3, 23, 3, 474000, tzinfo=timezone.utc),
            answers=[
                AnswerSubmission(
                    question_id=persisted_quiz.questions[0].id,
                    selected_answer_id=persisted_quiz.questions[0].answers[1].id,
                )
            ],
        )

        service = QuizAttemptService(
            quiz_read=QuizReadFacade(session),
            attempt_repository=QuizAttemptRepository(session),
            stats_updater=StatsUpdateFacade(session),
        )

        result = await service.submit_quiz(
            quiz_id=persisted_quiz.id,
            user_id=user.id,
            request=request,
        )

        assert result.total_score == 2
        assert len(result.question_results) == 1
        assert result.question_results[0].is_correct is True
        assert result.question_results[0].score_obtained == 2

        attempt_row = await session.get(QuizAttemptModel, result.attempt_id)
        assert attempt_row is not None
        assert attempt_row.total_score == 2

        question_attempt_rows = (
            await session.execute(
                select(QuestionAttemptModel).where(QuestionAttemptModel.quiz_attempt_id == result.attempt_id)
            )
        ).scalars().all()
        assert len(question_attempt_rows) == 1
        assert question_attempt_rows[0].selected_answer_id == persisted_quiz.questions[0].answers[1].id
        assert question_attempt_rows[0].quiz_attempt_id == result.attempt_id

        await session.rollback()


