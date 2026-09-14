from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.analytics.application.analytics_service import AnalyticsService
from modules.analytics.application.course_analytics_service import CourseAnalyticsService
from modules.analytics.schemas.response_schemas import UserDashboardResponse, CourseAnalyticsResponse


class TestAnalyticsService:
    """Unit tests for AnalyticsService"""

    @pytest.mark.asyncio
    async def test_get_user_dashboard_calculates_metrics_correctly(self) -> None:
        """Test that get_user_dashboard aggregates user stats correctly"""
        # Mock repository
        repo_mock = AsyncMock()

        # Mock totals
        repo_mock.get_user_totals = AsyncMock(
            return_value={
                "questions_attempted": 10,
                "questions_correct": 7,
                "quizzes_completed": 2,
            }
        )

        # Mock bloom breakdown
        bloom_rows = [
            SimpleNamespace(
                bloom_level="remember",
                questions_attempted=3,
                questions_correct=3,
            ),
            SimpleNamespace(
                bloom_level="understand",
                questions_attempted=4,
                questions_correct=3,
            ),
            SimpleNamespace(
                bloom_level="apply",
                questions_attempted=3,
                questions_correct=1,
            ),
        ]
        repo_mock.get_bloom_breakdown = AsyncMock(return_value=bloom_rows)

        # Mock course performance
        course_rows = [
            SimpleNamespace(
                course_id=1,
                course_name="Python Basics",
                quizzes_completed=1,
                questions_attempted=5,
                questions_correct=4,
            ),
            SimpleNamespace(
                course_id=2,
                course_name="Python Advanced",
                quizzes_completed=1,
                questions_attempted=5,
                questions_correct=3,
            ),
        ]
        repo_mock.get_course_performance = AsyncMock(return_value=course_rows)

        # Create service with mocked session
        session_mock = MagicMock()
        service = AnalyticsService(session_mock)
        service._repo = repo_mock

        # Call service
        result = await service.get_user_dashboard(user_id=1)

        # Assertions
        assert isinstance(result, UserDashboardResponse)
        assert result.quizzes_completed == 2
        assert result.questions_attempted == 10
        assert result.questions_correct == 7
        assert result.overall_accuracy == 70.0
        assert result.dominant_level == "remember"
        assert result.dominant_percentage == 100.0
        assert result.weak_level == "apply"
        assert result.weak_percentage == 33.3
        assert result.most_practiced_level == "understand"
        assert result.most_practiced_attempted == 4
        assert len(result.bloom_breakdown) == 3
        assert len(result.course_performance) == 2

    @pytest.mark.asyncio
    async def test_get_user_dashboard_handles_no_stats(self) -> None:
        """Test that get_user_dashboard handles users with no stats"""
        repo_mock = AsyncMock()
        repo_mock.get_user_totals = AsyncMock(
            return_value={
                "questions_attempted": 0,
                "questions_correct": 0,
                "quizzes_completed": 0,
            }
        )
        repo_mock.get_bloom_breakdown = AsyncMock(return_value=[])
        repo_mock.get_course_performance = AsyncMock(return_value=[])

        session_mock = MagicMock()
        service = AnalyticsService(session_mock)
        service._repo = repo_mock

        result = await service.get_user_dashboard(user_id=999)

        assert result.quizzes_completed == 0
        assert result.questions_attempted == 0
        assert result.questions_correct == 0
        assert result.overall_accuracy == 0.0
        assert result.dominant_level is None
        assert result.weak_level is None
        assert result.most_practiced_level is None

    @pytest.mark.asyncio
    async def test_get_user_dashboard_filters_inactive_bloom_levels(self) -> None:
        """Test that levels with 0 attempts are filtered out"""
        repo_mock = AsyncMock()
        repo_mock.get_user_totals = AsyncMock(
            return_value={
                "questions_attempted": 5,
                "questions_correct": 3,
                "quizzes_completed": 1,
            }
        )

        bloom_rows = [
            SimpleNamespace(
                bloom_level="remember",
                questions_attempted=5,
                questions_correct=3,
            ),
            SimpleNamespace(
                bloom_level="understand",
                questions_attempted=0,  # inactive
                questions_correct=0,
            ),
        ]
        repo_mock.get_bloom_breakdown = AsyncMock(return_value=bloom_rows)
        repo_mock.get_course_performance = AsyncMock(return_value=[])

        session_mock = MagicMock()
        service = AnalyticsService(session_mock)
        service._repo = repo_mock

        result = await service.get_user_dashboard(user_id=1)

        # Only "remember" level should be considered for dominant/weak/most_practiced
        assert result.dominant_level == "remember"
        assert result.weak_level == "remember"
        assert result.most_practiced_level == "remember"


class TestCourseAnalyticsService:
    """Unit tests for CourseAnalyticsService"""

    @pytest.mark.asyncio
    async def test_get_course_dashboard_calculates_bloom_stats(self) -> None:
        """Test that get_course_dashboard calculates course-specific stats"""
        repo_mock = AsyncMock()

        bloom_rows = [
            SimpleNamespace(
                bloom_level="remember",
                questions_attempted=5,
                questions_correct=5,
            ),
            SimpleNamespace(
                bloom_level="apply",
                questions_attempted=4,
                questions_correct=2,
            ),
        ]
        repo_mock.get_bloom_stats_by_course = AsyncMock(return_value=bloom_rows)

        session_mock = MagicMock()
        service = CourseAnalyticsService(session_mock)
        service._repo = repo_mock

        result = await service.get_course_dashboard(course_id=1, user_id=2)

        assert isinstance(result, CourseAnalyticsResponse)
        assert result.course_id == 1
        assert result.dominant_level == "remember"
        assert result.dominant_percentage == 100.0
        assert result.weak_level == "apply"
        assert result.weak_percentage == 50.0
        assert len(result.bloom_breakdown) == 2
        repo_mock.get_bloom_stats_by_course.assert_awaited_once_with(2, 1)

    @pytest.mark.asyncio
    async def test_get_course_dashboard_handles_no_stats(self) -> None:
        """Test that get_course_dashboard handles courses with no stats"""
        repo_mock = AsyncMock()
        repo_mock.get_bloom_stats_by_course = AsyncMock(return_value=[])

        session_mock = MagicMock()
        service = CourseAnalyticsService(session_mock)
        service._repo = repo_mock

        result = await service.get_course_dashboard(course_id=1, user_id=2)

        assert result.course_id == 1
        assert result.dominant_level is None
        assert result.weak_level is None
        assert len(result.bloom_breakdown) == 0

    @pytest.mark.asyncio
    async def test_get_course_dashboard_calculates_percentages_correctly(self) -> None:
        """Test percentage calculations for different scenarios"""
        repo_mock = AsyncMock()

        bloom_rows = [
            SimpleNamespace(
                bloom_level="remember",
                questions_attempted=10,
                questions_correct=8,
            ),
            SimpleNamespace(
                bloom_level="understand",
                questions_attempted=5,
                questions_correct=2,
            ),
            SimpleNamespace(
                bloom_level="create",
                questions_attempted=3,
                questions_correct=3,
            ),
        ]
        repo_mock.get_bloom_stats_by_course = AsyncMock(return_value=bloom_rows)

        session_mock = MagicMock()
        service = CourseAnalyticsService(session_mock)
        service._repo = repo_mock

        result = await service.get_course_dashboard(course_id=5, user_id=3)

        percentages = {b.bloom_level: b.percentage for b in result.bloom_breakdown}
        assert percentages["remember"] == 80.0
        assert percentages["understand"] == 40.0
        assert percentages["create"] == 100.0
        assert result.dominant_level == "create"
        assert result.weak_level == "understand"

