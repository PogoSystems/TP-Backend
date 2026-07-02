from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.quiz_management.application.services.quiz_attempt_service import QuizAttemptService
from modules.quiz_management.domain.aggregates import QuestionAttemptAggregate, QuizAttemptAggregate
from modules.quiz_management.domain.ports.quiz_read_port import AnswerValidation
from modules.quiz_management.schemas.request_schemas import AnswerSubmission, SubmitQuizRequest


def make_request() -> SubmitQuizRequest:
    return SubmitQuizRequest(
        started_at=datetime(2026, 7, 1, 3, 23, 3, 474000, tzinfo=timezone.utc),
        answers=[
            AnswerSubmission(question_id=60, selected_answer_id=214),
            AnswerSubmission(question_id=61, selected_answer_id=216),
        ],
    )


class TestQuizAttemptService:
    @pytest.mark.asyncio
    async def test_submit_quiz_calculates_score_and_persists_attempt(self) -> None:
        quiz_read = MagicMock()
        quiz_read.get_answer_validations = AsyncMock(
            return_value={
                214: AnswerValidation(answer_id=214, is_correct=True, question_score=1, bloom_level="remember"),
                216: AnswerValidation(answer_id=216, is_correct=False, question_score=2, bloom_level="remember"),
            }
        )
        quiz_read.get_course_id_for_quiz = AsyncMock(return_value=1)

        saved_attempt = QuizAttemptAggregate(id=99, user_id=2, quiz_id=16, total_score=1)
        repo = MagicMock()
        repo.save_attempt = AsyncMock(return_value=saved_attempt)

        stats_updater = MagicMock()
        stats_updater.update_stats_after_submit = AsyncMock()

        service = QuizAttemptService(quiz_read=quiz_read, attempt_repository=repo, stats_updater=stats_updater)

        result = await service.submit_quiz(quiz_id=16, user_id=2, request=make_request())

        quiz_read.get_answer_validations.assert_awaited_once_with(16, [214, 216])
        repo.save_attempt.assert_awaited_once()

        saved_attempt_arg, question_attempts_arg = repo.save_attempt.await_args.args
        assert isinstance(saved_attempt_arg, QuizAttemptAggregate)
        assert saved_attempt_arg.user_id == 2
        assert saved_attempt_arg.quiz_id == 16
        assert saved_attempt_arg.total_score == 1
        assert len(question_attempts_arg) == 2
        assert all(isinstance(item, QuestionAttemptAggregate) for item in question_attempts_arg)

        assert result.attempt_id == 99
        assert result.quiz_id == 16
        assert result.total_score == 1
        assert len(result.question_results) == 2
        assert result.question_results[0].question_id == 60
        assert result.question_results[0].selected_answer_id == 214
        assert result.question_results[0].is_correct is True
        assert result.question_results[0].score_obtained == 1
        assert result.question_results[1].question_id == 61
        assert result.question_results[1].selected_answer_id == 216
        assert result.question_results[1].is_correct is False
        assert result.question_results[1].score_obtained == 0

    @pytest.mark.asyncio
    async def test_submit_quiz_rejects_answers_not_belonging_to_quiz(self) -> None:
        quiz_read = MagicMock()
        quiz_read.get_answer_validations = AsyncMock(
                return_value={214: AnswerValidation(answer_id=214, is_correct=True, question_score=1, bloom_level="remember")}
        )
        quiz_read.get_course_id_for_quiz = AsyncMock(return_value=1)
        repo = MagicMock()
        repo.save_attempt = AsyncMock()
        stats_updater = MagicMock()
        stats_updater.update_stats_after_submit = AsyncMock()
        service = QuizAttemptService(quiz_read=quiz_read, attempt_repository=repo, stats_updater=stats_updater)

        request = SubmitQuizRequest(
            started_at=datetime(2026, 7, 1, 3, 23, 3, 474000, tzinfo=timezone.utc),
            answers=[AnswerSubmission(question_id=60, selected_answer_id=999)],
        )

        with pytest.raises(ValueError) as exc_info:
            await service.submit_quiz(quiz_id=16, user_id=2, request=request)

        assert "doesn't belongs" in str(exc_info.value)
        repo.save_attempt.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_quiz_uses_current_time_for_submitted_at_and_results(self) -> None:
        quiz_read = MagicMock()
        quiz_read.get_answer_validations = AsyncMock(
            return_value={214: AnswerValidation(answer_id=214, is_correct=True, question_score=3, bloom_level="remember")}
        )
        quiz_read.get_course_id_for_quiz = AsyncMock(return_value=1)
        repo = MagicMock()
        repo.save_attempt = AsyncMock(return_value=QuizAttemptAggregate(id=1, user_id=2, quiz_id=16, total_score=3))
        stats_updater = MagicMock()
        stats_updater.update_stats_after_submit = AsyncMock()
        service = QuizAttemptService(quiz_read=quiz_read, attempt_repository=repo, stats_updater=stats_updater)

        request = SubmitQuizRequest(
            started_at=datetime(2026, 7, 1, 3, 23, 3, 474000, tzinfo=timezone.utc),
            answers=[AnswerSubmission(question_id=60, selected_answer_id=214)],
        )

        result = await service.submit_quiz(quiz_id=16, user_id=2, request=request)

        assert result.attempt_id == 1
        assert result.total_score == 3
        assert len(result.question_results) == 1
        assert result.question_results[0].question_id == 60
        assert result.question_results[0].selected_answer_id == 214
        assert result.question_results[0].is_correct is True
        assert result.question_results[0].score_obtained == 3
