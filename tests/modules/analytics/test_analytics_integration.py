from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from core.db.database import get_db
from modules.analytics.application.analytics_service import AnalyticsService
from modules.analytics.application.course_analytics_service import CourseAnalyticsService
from modules.analytics.infrastructure.models import CourseStatsModel, BloomStatsModel
from modules.analytics.infrastructure.repositories.stats_command_repository import StatsCommandRepository
from modules.analytics.infrastructure.repositories.stats_query_repository import StatsQueryRepository
from modules.analytics.infrastructure.facades.stats_update_facade import StatsUpdateFacade
from modules.course_management.infrastructure.models import CourseModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.quiz_management.domain.ports.stats_update_port import QuestionAttemptSummary


@pytest.mark.asyncio
async def test_analytics_integration_stats_workflow() -> None:
    """Test complete workflow: update stats and read them"""
    async for session in get_db():
        # Setup: Create user and course
        unique_suffix = uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid4(),
            name=f"Analytics_User_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"analytics_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        course = CourseModel(
            name="Analytics Test Course",
            description="Course for analytics integration test",
            user_id=user.id,
        )
        session.add(course)
        await session.flush()

        # Step 1: Update stats after quiz submission
        facade = StatsUpdateFacade(session)
        summaries = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="understand", is_correct=False),
            QuestionAttemptSummary(bloom_level="apply", is_correct=True),
        ]
        await facade.update_stats_after_submit(course_id=course.id, question_summaries=summaries)
        await session.flush()

        # Step 2: Verify stats were persisted
        course_stats = await session.get(CourseStatsModel, None)
        stmt = select(CourseStatsModel).where(CourseStatsModel.course_id == course.id)
        result = await session.execute(stmt)
        course_stats = result.scalar_one_or_none()

        assert course_stats is not None
        assert course_stats.quizzes_completed == 1
        assert course_stats.questions_attempted == 4
        assert course_stats.questions_correct == 3

        # Step 3: Read user analytics
        service = AnalyticsService(session)
        dashboard = await service.get_user_dashboard(user_id=user.id)

        assert dashboard.quizzes_completed == 1
        assert dashboard.questions_attempted == 4
        assert dashboard.questions_correct == 3
        assert dashboard.overall_accuracy == 75.0

        # Bloom breakdown should have 3 entries
        assert len(dashboard.bloom_breakdown) == 3
        remember_stats = next(b for b in dashboard.bloom_breakdown if b.bloom_level == "remember")
        assert remember_stats.questions_attempted == 2
        assert remember_stats.questions_correct == 2
        assert remember_stats.percentage == 100.0

        understand_stats = next(b for b in dashboard.bloom_breakdown if b.bloom_level == "understand")
        assert understand_stats.questions_attempted == 1
        assert understand_stats.questions_correct == 0
        assert understand_stats.percentage == 0.0

        apply_stats = next(b for b in dashboard.bloom_breakdown if b.bloom_level == "apply")
        assert apply_stats.questions_attempted == 1
        assert apply_stats.questions_correct == 1
        assert apply_stats.percentage == 100.0

        # Dominant level should be "remember" or "apply" (both 100%)
        assert dashboard.dominant_level in ["remember", "apply"]
        assert dashboard.dominant_percentage == 100.0

        # Weak level should be "understand" (0%)
        assert dashboard.weak_level == "understand"
        assert dashboard.weak_percentage == 0.0

        # Step 4: Test course-specific analytics
        course_service = CourseAnalyticsService(session)
        course_dashboard = await course_service.get_course_dashboard(course_id=course.id, user_id=user.id)

        assert course_dashboard.course_id == course.id
        assert len(course_dashboard.bloom_breakdown) == 3
        assert course_dashboard.dominant_level in ["remember", "apply"]

        await session.rollback()


@pytest.mark.asyncio
async def test_analytics_integration_multiple_quiz_submissions() -> None:
    """Test stats accumulation across multiple quiz submissions"""
    async for session in get_db():
        # Setup
        unique_suffix = uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid4(),
            name=f"Analytics_Multi_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"analytics_multi_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        course = CourseModel(
            name="Analytics Multi-Quiz Test",
            description="Test multiple submissions",
            user_id=user.id,
        )
        session.add(course)
        await session.flush()

        # First submission
        facade = StatsUpdateFacade(session)
        summaries1 = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="understand", is_correct=True),
        ]
        await facade.update_stats_after_submit(course_id=course.id, question_summaries=summaries1)
        await session.flush()

        # Second submission (should accumulate)
        summaries2 = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=False),
            QuestionAttemptSummary(bloom_level="apply", is_correct=True),
        ]
        await facade.update_stats_after_submit(course_id=course.id, question_summaries=summaries2)
        await session.flush()

        # Verify stats are accumulated
        service = AnalyticsService(session)
        dashboard = await service.get_user_dashboard(user_id=user.id)

        # Should have 2 quizzes, 4 questions total, 3 correct
        assert dashboard.quizzes_completed == 2
        assert dashboard.questions_attempted == 4
        assert dashboard.questions_correct == 3
        assert dashboard.overall_accuracy == 75.0

        await session.rollback()


@pytest.mark.asyncio
async def test_analytics_integration_multiple_courses() -> None:
    """Test analytics across multiple courses"""
    async for session in get_db():
        # Setup
        unique_suffix = uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid4(),
            name=f"Analytics_MultiCourse_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"analytics_multicourse_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        course1 = CourseModel(
            name="Course Python",
            description="Python course",
            user_id=user.id,
        )
        session.add(course1)
        await session.flush()

        course2 = CourseModel(
            name="Course Data Science",
            description="Data Science course",
            user_id=user.id,
        )
        session.add(course2)
        await session.flush()

        # Submit quiz in course 1
        facade = StatsUpdateFacade(session)
        summaries1 = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
        ]
        await facade.update_stats_after_submit(course_id=course1.id, question_summaries=summaries1)
        await session.flush()

        # Submit quiz in course 2
        summaries2 = [
            QuestionAttemptSummary(bloom_level="apply", is_correct=False),
            QuestionAttemptSummary(bloom_level="analyze", is_correct=True),
        ]
        await facade.update_stats_after_submit(course_id=course2.id, question_summaries=summaries2)
        await session.flush()

        # Get user dashboard
        service = AnalyticsService(session)
        dashboard = await service.get_user_dashboard(user_id=user.id)

        # Aggregate stats: 2 quizzes, 3 questions, 2 correct
        assert dashboard.quizzes_completed == 2
        assert dashboard.questions_attempted == 3
        assert dashboard.questions_correct == 2
        assert dashboard.overall_accuracy == 66.7

        # Check course performance
        assert len(dashboard.course_performance) == 2
        course_perf = {cp.course_id: cp for cp in dashboard.course_performance}

        assert course_perf[course1.id].quizzes_completed == 1
        assert course_perf[course1.id].accuracy_percentage == 100.0

        assert course_perf[course2.id].quizzes_completed == 1
        assert course_perf[course2.id].accuracy_percentage == 50.0

        await session.rollback()


@pytest.mark.asyncio
async def test_analytics_integration_bloom_stats_persistence() -> None:
    """Test that bloom stats are persisted and retrieved correctly"""
    async for session in get_db():
        # Setup
        unique_suffix = uuid4().hex[:8]
        user = UserModel(
            auth_id=uuid4(),
            name=f"Analytics_Bloom_{unique_suffix}",
            last_name="Tester",
            college="Test University",
            major="Software Engineering",
            email=f"analytics_bloom_{unique_suffix}@test.com",
        )
        session.add(user)
        await session.flush()

        course = CourseModel(
            name="Bloom Test Course",
            description="Test bloom level tracking",
            user_id=user.id,
        )
        session.add(course)
        await session.flush()

        # Submit questions for each bloom level
        facade = StatsUpdateFacade(session)
        summaries = [
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="remember", is_correct=True),
            QuestionAttemptSummary(bloom_level="understand", is_correct=False),
            QuestionAttemptSummary(bloom_level="apply", is_correct=True),
            QuestionAttemptSummary(bloom_level="analyze", is_correct=False),
            QuestionAttemptSummary(bloom_level="evaluate", is_correct=True),
            QuestionAttemptSummary(bloom_level="create", is_correct=False),
        ]
        await facade.update_stats_after_submit(course_id=course.id, question_summaries=summaries)
        await session.flush()

        # Verify bloom stats exist in DB
        stmt = select(BloomStatsModel).where(BloomStatsModel.course_id == course.id)
        result = await session.execute(stmt)
        bloom_models = result.scalars().all()

        assert len(bloom_models) == 6  # 6 different bloom levels
        bloom_dict = {b.bloom_level: b for b in bloom_models}

        assert bloom_dict["remember"].questions_attempted == 2
        assert bloom_dict["remember"].questions_correct == 2

        assert bloom_dict["understand"].questions_attempted == 1
        assert bloom_dict["understand"].questions_correct == 0

        assert bloom_dict["apply"].questions_attempted == 1
        assert bloom_dict["apply"].questions_correct == 1

        await session.rollback()

