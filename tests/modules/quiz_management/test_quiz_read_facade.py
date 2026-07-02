from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.quiz_management.infrastructure.facades.quiz_read_facade import QuizReadFacade


class TestQuizReadFacade:
    @pytest.mark.asyncio
    async def test_get_answer_validations_returns_mapping_from_query_rows(self) -> None:
        session = MagicMock()
        result = MagicMock()
        result.all.return_value = [
            SimpleNamespace(id=214, is_correct=True, score=1),
            SimpleNamespace(id=216, is_correct=False, score=2),
        ]
        session.execute = AsyncMock(return_value=result)

        facade = QuizReadFacade(session)
        validations = await facade.get_answer_validations(quiz_id=16, answer_ids=[214, 216])

        assert set(validations) == {214, 216}
        assert validations[214].answer_id == 214
        assert validations[214].is_correct is True
        assert validations[214].question_score == 1
        assert validations[216].is_correct is False
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_answer_validations_uses_join_and_filters_by_quiz(self) -> None:
        session = MagicMock()
        result = MagicMock()
        result.all.return_value = []
        session.execute = AsyncMock(return_value=result)

        facade = QuizReadFacade(session)
        await facade.get_answer_validations(quiz_id=99, answer_ids=[1, 2, 3])

        stmt = session.execute.await_args.args[0]
        assert "answer" in str(stmt).lower()
        assert "question" in str(stmt).lower()

