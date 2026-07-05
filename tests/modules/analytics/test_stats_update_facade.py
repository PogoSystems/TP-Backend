from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.analytics.infrastructure.facades.stats_update_facade import StatsUpdateFacade
from modules.quiz_management.domain.ports.stats_update_port import QuestionAttemptSummary


class TestStatsUpdateFacade:
    """Unit tests for StatsUpdateFacade"""

    @pytest.mark.asyncio
    async def test_update_stats_after_submit_increments_course_stats(self) -> None:
        """Test that update_stats_after_submit increments course stats correctly"""
        session_mock = MagicMock()
        facade = StatsUpdateFacade(session_mock)

        # Mock repository
        repo_mock = AsyncMock()
        facade._repo = repo_mock

        # Prepare test data
        summaries = [
            QuestionAttemptSummary(
                bloom_level="remember",
                is_correct=True,
            ),
            QuestionAttemptSummary(
                bloom_level="understand",
                is_correct=False,
            ),
            QuestionAttemptSummary(
                bloom_level="remember",
                is_correct=True,
            ),
        ]

        await facade.update_stats_after_submit(course_id=5, question_summaries=summaries)

        # Should increment course stats with 3 attempted, 2 correct
        repo_mock.increment_course_stats.assert_awaited_once_with(
            course_id=5,
            attempted=3,
            correct=2,
        )

    @pytest.mark.asyncio
    async def test_update_stats_after_submit_updates_bloom_stats_bulk(self) -> None:
        """Test that update_stats_after_submit calls increment_bloom_stats_bulk with correct data"""
        session_mock = MagicMock()
        facade = StatsUpdateFacade(session_mock)
        repo_mock = AsyncMock()
        facade._repo = repo_mock

        summaries = [
            QuestionAttemptSummary(
                bloom_level="remember",
                is_correct=True,
            ),
            QuestionAttemptSummary(
                bloom_level="remember",
                is_correct=False,
            ),
            QuestionAttemptSummary(
                bloom_level="apply",
                is_correct=True,
            ),
        ]

        await facade.update_stats_after_submit(course_id=10, question_summaries=summaries)

        # Verify increment_bloom_stats_bulk was called with correct data
        repo_mock.increment_bloom_stats_bulk.assert_awaited_once()
        call_kwargs = repo_mock.increment_bloom_stats_bulk.call_args.kwargs

        assert call_kwargs["course_id"] == 10
        # "remember": 2 attempted, 1 correct
        # "apply": 1 attempted, 1 correct
        assert call_kwargs["bloom_counts"]["remember"] == (2, 1)
        assert call_kwargs["bloom_counts"]["apply"] == (1, 1)

    @pytest.mark.asyncio
    async def test_update_stats_after_submit_groups_bloom_levels(self) -> None:
        """Test that bloom levels are grouped correctly before DB call"""
        session_mock = MagicMock()
        facade = StatsUpdateFacade(session_mock)
        repo_mock = AsyncMock()
        facade._repo = repo_mock

        # Multiple questions with same bloom level
        summaries = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="remember", is_correct=False),
            QuestionAttemptSummary(bloom_level="understand", is_correct=True),
        ]

        await facade.update_stats_after_submit(course_id=1, question_summaries=summaries)

        call_kwargs = repo_mock.increment_bloom_stats_bulk.call_args.kwargs
        # Should group "remember" as 3 attempts, 2 correct
        # Should group "understand" as 1 attempt, 1 correct
        assert call_kwargs["bloom_counts"]["remember"] == (3, 2)
        assert call_kwargs["bloom_counts"]["understand"] == (1, 1)
        assert len(call_kwargs["bloom_counts"]) == 2

    @pytest.mark.asyncio
    async def test_update_stats_after_submit_handles_empty_summaries(self) -> None:
        """Test that facade handles empty question summaries"""
        session_mock = MagicMock()
        facade = StatsUpdateFacade(session_mock)
        repo_mock = AsyncMock()
        facade._repo = repo_mock

        await facade.update_stats_after_submit(course_id=1, question_summaries=[])

        # Should still call increment_course_stats with 0 attempted/correct
        repo_mock.increment_course_stats.assert_awaited_once_with(
            course_id=1,
            attempted=0,
            correct=0,
        )
        # Should call increment_bloom_stats_bulk with empty dict
        repo_mock.increment_bloom_stats_bulk.assert_awaited_once_with(
            course_id=1,
            bloom_counts={},
        )

    @pytest.mark.asyncio
    async def test_update_stats_after_submit_all_incorrect_answers(self) -> None:
        """Test update_stats when all answers are incorrect"""
        session_mock = MagicMock()
        facade = StatsUpdateFacade(session_mock)
        repo_mock = AsyncMock()
        facade._repo = repo_mock

        summaries = [
            QuestionAttemptSummary(bloom_level="apply", is_correct=False),
            QuestionAttemptSummary(bloom_level="analyze", is_correct=False),
        ]

        await facade.update_stats_after_submit(course_id=3, question_summaries=summaries)

        # 2 attempted, 0 correct
        repo_mock.increment_course_stats.assert_awaited_once_with(
            course_id=3,
            attempted=2,
            correct=0,
        )

        call_kwargs = repo_mock.increment_bloom_stats_bulk.call_args.kwargs
        assert call_kwargs["bloom_counts"]["apply"] == (1, 0)
        assert call_kwargs["bloom_counts"]["analyze"] == (1, 0)





