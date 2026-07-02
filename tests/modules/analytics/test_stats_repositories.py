from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from modules.analytics.infrastructure.repositories.stats_command_repository import StatsCommandRepository
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository
from modules.analytics.infrastructure.models import CourseStatsModel, BloomStatsModel
from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel


class TestStatsCommandRepository:
    """Unit tests for StatsCommandRepository (write operations)"""

    @pytest.mark.asyncio
    async def test_increment_course_stats_creates_new_entry(self) -> None:
        """Test that increment_course_stats creates a new entry if it doesn't exist"""
        session_mock = AsyncMock()
        repo = StatsCommandRepository(session_mock)

        await repo.increment_course_stats(course_id=1, attempted=5, correct=3)

        session_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_bloom_stats_bulk_calls_execute_for_each_level(self) -> None:
        """Test that increment_bloom_stats_bulk executes one statement per bloom level"""
        session_mock = AsyncMock()
        repo = StatsCommandRepository(session_mock)

        bloom_counts = {
            "remember": (3, 3),
            "understand": (4, 2),
            "apply": (2, 1),
        }

        await repo.increment_bloom_stats_bulk(course_id=1, bloom_counts=bloom_counts)

        # Should execute 3 times (one per bloom level)
        assert session_mock.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_increment_bloom_stats_bulk_handles_empty_dict(self) -> None:
        """Test that increment_bloom_stats_bulk handles empty bloom_counts"""
        session_mock = AsyncMock()
        repo = StatsCommandRepository(session_mock)

        await repo.increment_bloom_stats_bulk(course_id=1, bloom_counts={})

        # Should not execute any statements
        session_mock.execute.assert_not_called()


class TestStatsQueryRepository:
    """Unit tests for StatsQueryRepository (read operations)"""

    @pytest.mark.asyncio
    async def test_get_user_totals_aggregates_correctly(self) -> None:
        """Test that get_user_totals returns aggregated stats"""
        session_mock = AsyncMock()

        # Mock result
        result_mock = MagicMock()
        result_mock.mappings().one.return_value = {
            "quizzes_completed": 5,
            "questions_attempted": 20,
            "questions_correct": 15,
        }
        session_mock.execute = AsyncMock(return_value=result_mock)

        repo = StatsQueryRepository(session_mock)
        result = await repo.get_user_totals(user_id=1)

        assert result["quizzes_completed"] == 5
        assert result["questions_attempted"] == 20
        assert result["questions_correct"] == 15

    @pytest.mark.asyncio
    async def test_get_bloom_breakdown_returns_list(self) -> None:
        """Test that get_bloom_breakdown returns a list of bloom stats"""
        session_mock = AsyncMock()

        # Mock result rows
        result_mock = MagicMock()
        result_mock.all.return_value = [
            (("remember", 10, 8),),
            (("understand", 8, 6),),
        ]
        session_mock.execute = AsyncMock(return_value=result_mock)

        repo = StatsQueryRepository(session_mock)
        result = await repo.get_bloom_breakdown(user_id=1)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_course_performance_returns_course_list(self) -> None:
        """Test that get_course_performance returns courses with stats"""
        session_mock = AsyncMock()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            (("1", "Course 1", "2", "10", "8"),),
            (("2", "Course 2", "1", "5", "3"),),
        ]
        session_mock.execute = AsyncMock(return_value=result_mock)

        repo = StatsQueryRepository(session_mock)
        result = await repo.get_course_performance(user_id=1)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bloom_stats_by_course_filters_by_course(self) -> None:
        """Test that get_bloom_stats_by_course filters by course_id"""
        session_mock = AsyncMock()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            (("remember", 5, 4),),
        ]
        session_mock.execute = AsyncMock(return_value=result_mock)

        repo = StatsQueryRepository(session_mock)
        result = await repo.get_bloom_stats_by_course(user_id=1, course_id=5)

        assert isinstance(result, list)
        assert len(result) == 1

