from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest

from modules.analytics.application.metacognition_service import MetacognitionService
from modules.analytics.schemas.response_schemas import (
    BloomMetacognitionResponse,
    CourseMetacognitionResponse,
    MetacognitionProgressResponse,
    MetacognitionSummaryResponse,
)


class TestMetacognitionService:
    @pytest.mark.asyncio
    async def test_summary_empty_state(self) -> None:
        """Verifica que sin intentos con predicción se retorne un estado neutral sin errores."""
        repo_mock = AsyncMock()
        repo_mock.get_raw_attempts = AsyncMock(return_value=[])

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        result = await service.get_summary(user_id=1)

        assert isinstance(result, MetacognitionSummaryResponse)
        assert result.calibration_accuracy_percentage == 0.0
        assert result.average_expected == 0.0
        assert result.average_actual == 0.0
        assert result.bias == "calibrated"
        assert result.bias_gap == 0.0
        assert result.total_evaluated_quizzes == 0
        assert result.course_breakdown == []

    @pytest.mark.asyncio
    async def test_summary_overconfidence_and_accuracy(self) -> None:
        """Verifica cálculos globales de precisión, brecha y sesgo sobreestimado (overconfident)."""
        repo_mock = AsyncMock()
        repo_mock.get_raw_attempts = AsyncMock(
            return_value=[
                {
                    "attempt_id": 1,
                    "quiz_id": 10,
                    "quiz_title": "Quiz 1",
                    "course_id": 101,
                    "course_name": "Matemáticas",
                    "submitted_at": datetime(2026, 3, 1, 10, 0),
                    "expected_correct": 8,
                    "total_questions": 10,
                    "actual_correct": 5,
                },
                {
                    "attempt_id": 2,
                    "quiz_id": 11,
                    "quiz_title": "Quiz 2",
                    "course_id": 101,
                    "course_name": "Matemáticas",
                    "submitted_at": datetime(2026, 3, 3, 10, 0),
                    "expected_correct": 7,
                    "total_questions": 10,
                    "actual_correct": 5,
                },
            ]
        )

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        result = await service.get_summary(user_id=1)

        assert result.total_evaluated_quizzes == 2
        assert result.average_expected == 7.5
        assert result.average_actual == 5.0
        assert result.bias_gap == 2.5
        assert result.bias == "overconfident"
        # Accuracies: (100 - 30%) = 70%, (100 - 20%) = 80% -> promedio 75.0%
        assert result.calibration_accuracy_percentage == 75.0
        assert len(result.course_breakdown) == 1
        course = result.course_breakdown[0]
        assert course.course_id == 101
        assert course.course_name == "Matemáticas"
        assert course.quizzes_evaluated == 2
        assert course.calibration_accuracy_percentage == 75.0
        assert course.bias == "overconfident"

    @pytest.mark.asyncio
    async def test_summary_variable_bias_when_low_accuracy_and_balanced_gap(self) -> None:
        """Verifica que si la brecha neta es 0 pero la precisión es baja (<75%), el sesgo sea 'variable'."""
        repo_mock = AsyncMock()
        repo_mock.get_raw_attempts = AsyncMock(
            return_value=[
                {
                    "attempt_id": 1,
                    "quiz_id": 10,
                    "quiz_title": "Quiz 1",
                    "course_id": 101,
                    "course_name": "Matemáticas",
                    "submitted_at": datetime(2026, 3, 1, 10, 0),
                    "expected_correct": 8,
                    "total_questions": 10,
                    "actual_correct": 4,  # Overconfident by 4, accuracy = 60%
                },
                {
                    "attempt_id": 2,
                    "quiz_id": 11,
                    "quiz_title": "Quiz 2",
                    "course_id": 101,
                    "course_name": "Matemáticas",
                    "submitted_at": datetime(2026, 3, 3, 10, 0),
                    "expected_correct": 4,
                    "total_questions": 10,
                    "actual_correct": 8,  # Underconfident by 4, accuracy = 60%
                },
            ]
        )

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        result = await service.get_summary(user_id=1)

        assert result.total_evaluated_quizzes == 2
        assert result.average_expected == 6.0
        assert result.average_actual == 6.0
        assert result.bias_gap == 0.0
        assert result.calibration_accuracy_percentage == 60.0
        # Debido a que la precisión es 60% (< 75%), el sesgo no debe ser 'calibrated', sino 'variable'
        assert result.bias == "variable"

    @pytest.mark.asyncio
    async def test_course_detail_empty_state_with_course_name(self) -> None:
        """Verifica que si el curso no tiene intentos, se devuelva respuesta limpia con el nombre del curso."""
        repo_mock = AsyncMock()
        repo_mock.get_raw_attempts = AsyncMock(return_value=[])
        repo_mock.get_course_name = AsyncMock(return_value="Física Clásica")

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        result = await service.get_course_detail(user_id=1, course_id=5)

        assert isinstance(result, CourseMetacognitionResponse)
        assert result.course_id == 5
        assert result.course_name == "Física Clásica"
        assert result.quizzes_evaluated == 0
        assert result.calibration_accuracy_percentage == 0.0
        assert result.bias == "calibrated"
        assert result.recent_attempts == []

    @pytest.mark.asyncio
    async def test_course_detail_with_recent_attempts(self) -> None:
        """Verifica el cálculo de metacognición para un curso específico y el mapeo de intentos recientes."""
        repo_mock = AsyncMock()
        dt = datetime(2026, 3, 2, 14, 30)
        repo_mock.get_raw_attempts = AsyncMock(
            return_value=[
                {
                    "attempt_id": 1,
                    "quiz_id": 20,
                    "quiz_title": "Quiz Cinemática",
                    "course_id": 2,
                    "course_name": "Física",
                    "submitted_at": dt,
                    "expected_correct": 5,
                    "total_questions": 5,
                    "actual_correct": 5,
                }
            ]
        )

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        result = await service.get_course_detail(user_id=1, course_id=2)

        assert result.course_id == 2
        assert result.course_name == "Física"
        assert result.quizzes_evaluated == 1
        assert result.calibration_accuracy_percentage == 100.0
        assert result.bias == "calibrated"
        assert len(result.recent_attempts) == 1
        recent = result.recent_attempts[0]
        assert recent.quiz_id == 20
        assert recent.quiz_title == "Quiz Cinemática"
        assert recent.submitted_at == dt
        assert recent.total_questions == 5
        assert recent.expected_correct == 5
        assert recent.actual_correct == 5
        assert recent.gap == 0.0
        assert recent.calibration_accuracy == 100.0

    @pytest.mark.asyncio
    async def test_bloom_breakdown_proportional_distribution(self) -> None:
        """Verifica la fórmula de cálculo proporcional de Bloom."""
        repo_mock = AsyncMock()
        # Quiz con 10 preguntas en total, predicción 8 esperadas:
        # 4 preguntas de remember, 3 correctas -> exp = 4 * (8/10) = 3.2
        # 6 preguntas de apply, 2 correctas -> exp = 6 * (8/10) = 4.8
        repo_mock.get_raw_bloom_data = AsyncMock(
            return_value=[
                {
                    "bloom_level": "remember",
                    "expected_correct_answers": 8,
                    "attempt_total_questions": 10,
                    "bloom_questions_count": 4,
                    "bloom_actual_correct": 3,
                },
                {
                    "bloom_level": "apply",
                    "expected_correct_answers": 8,
                    "attempt_total_questions": 10,
                    "bloom_questions_count": 6,
                    "bloom_actual_correct": 2,
                },
            ]
        )

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        results = await service.get_bloom_breakdown(user_id=1, course_id=10)

        assert len(results) == 2
        apply_res = next(r for r in results if r.bloom_level == "apply")
        remember_res = next(r for r in results if r.bloom_level == "remember")

        # Remember: att=4, act=3, exp=3.2, gap=0.2 (calibrated)
        assert remember_res.questions_attempted == 4
        assert remember_res.actual_correct == 3
        assert remember_res.expected_correct == 3.2
        assert remember_res.bias == "calibrated"
        assert remember_res.calibration_accuracy == 95.0

        # Apply: att=6, act=2, exp=4.8, gap=2.8 (overconfident)
        assert apply_res.questions_attempted == 6
        assert apply_res.actual_correct == 2
        assert apply_res.expected_correct == 4.8
        assert apply_res.bias == "overconfident"
        assert apply_res.calibration_accuracy == 53.3

    @pytest.mark.asyncio
    async def test_bloom_breakdown_empty_state(self) -> None:
        """Verifica que sin datos retorne una lista vacía."""
        repo_mock = AsyncMock()
        repo_mock.get_raw_bloom_data = AsyncMock(return_value=[])

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        results = await service.get_bloom_breakdown(user_id=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_progress_weekly_and_monthly(self) -> None:
        """Verifica la agrupación temporal por semana y mes."""
        repo_mock = AsyncMock()
        # 2 intentos en la misma semana: lunes 2026-03-02 y miércoles 2026-03-04
        repo_mock.get_raw_attempts = AsyncMock(
            return_value=[
                {
                    "expected_correct": 8,
                    "actual_correct": 6,
                    "total_questions": 10,
                    "submitted_at": datetime(2026, 3, 2, 10, 0),
                },
                {
                    "expected_correct": 7,
                    "actual_correct": 5,
                    "total_questions": 10,
                    "submitted_at": datetime(2026, 3, 4, 12, 0),
                },
            ]
        )

        service = MetacognitionService(MagicMock())
        service._repo = repo_mock

        # Semanal
        week_res = await service.get_progress(user_id=1, granularity="week")
        assert isinstance(week_res, MetacognitionProgressResponse)
        assert week_res.granularity == "week"
        assert len(week_res.points) == 1
        pt = week_res.points[0]
        assert pt.period == "2026-03-02"
        assert pt.quizzes_count == 2
        assert pt.avg_expected == 7.5
        assert pt.avg_actual == 5.5
        assert pt.calibration_accuracy == 80.0

        # Mensual
        month_res = await service.get_progress(user_id=1, granularity="month")
        assert len(month_res.points) == 1
        assert month_res.points[0].period == "2026-03-01"

    @pytest.mark.asyncio
    async def test_progress_invalid_granularity_raises_error(self) -> None:
        """Verifica que una granularidad no soportada lance ValueError."""
        service = MetacognitionService(MagicMock())
        with pytest.raises(ValueError, match="granularity must be 'week' or 'month'"):
            await service.get_progress(user_id=1, granularity="year")


class TestMetacognitionQueryRepository:
    @pytest.mark.asyncio
    async def test_get_raw_attempts_executes_and_returns_mappings(self) -> None:
        session_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "attempt_id": 1,
                "quiz_id": 10,
                "quiz_title": "Q1",
                "course_id": 1,
                "course_name": "C1",
                "submitted_at": datetime(2026, 1, 1),
                "expected_correct": 4,
                "total_questions": 5,
                "actual_correct": 4,
            }
        ]
        session_mock.execute.return_value = mock_result

        from modules.analytics.infrastructure.repositories.metacognition_query_repository import MetacognitionQueryRepository
        repo = MetacognitionQueryRepository(session_mock)

        res = await repo.get_raw_attempts(user_id=1, course_id=1)
        assert len(res) == 1
        assert res[0]["quiz_title"] == "Q1"
        session_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_raw_bloom_data_executes_and_returns_mappings(self) -> None:
        session_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "bloom_level": "remember",
                "expected_correct_answers": 5,
                "attempt_total_questions": 5,
                "bloom_questions_count": 3,
                "bloom_actual_correct": 3,
            }
        ]
        session_mock.execute.return_value = mock_result

        from modules.analytics.infrastructure.repositories.metacognition_query_repository import MetacognitionQueryRepository
        repo = MetacognitionQueryRepository(session_mock)

        res = await repo.get_raw_bloom_data(user_id=1, course_id=1)
        assert len(res) == 1
        assert res[0]["bloom_level"] == "remember"
        session_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_course_name_returns_scalar(self) -> None:
        session_mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "Curso Test"
        session_mock.execute.return_value = mock_result

        from modules.analytics.infrastructure.repositories.metacognition_query_repository import MetacognitionQueryRepository
        repo = MetacognitionQueryRepository(session_mock)

        name = await repo.get_course_name(course_id=1)
        assert name == "Curso Test"
        session_mock.execute.assert_called_once()


class TestMetacognitionRoutes:
    @pytest.mark.asyncio
    async def test_metacognition_routes_with_test_client(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from main import app
        from modules.analytics.api.routes import get_metacognition_service
        from modules.iam.api.dependencies import get_current_user_id

        service_mock = AsyncMock()
        service_mock.get_summary.return_value = MetacognitionSummaryResponse(
            calibration_accuracy_percentage=85.0,
            average_expected=8.0,
            average_actual=7.0,
            bias="overconfident",
            bias_gap=1.0,
            total_evaluated_quizzes=3,
            course_breakdown=[],
        )
        service_mock.get_course_detail.return_value = CourseMetacognitionResponse(
            course_id=1,
            course_name="Biología",
            calibration_accuracy_percentage=85.0,
            average_expected=8.0,
            average_actual=7.0,
            bias="overconfident",
            quizzes_evaluated=3,
            recent_attempts=[],
        )
        service_mock.get_bloom_breakdown.return_value = [
            BloomMetacognitionResponse(
                bloom_level="remember",
                questions_attempted=5,
                actual_correct=4,
                expected_correct=4.0,
                calibration_accuracy=100.0,
                bias="calibrated",
            )
        ]
        service_mock.get_progress.return_value = MetacognitionProgressResponse(
            granularity="week",
            points=[],
        )

        app.dependency_overrides[get_current_user_id] = lambda: 42
        app.dependency_overrides[get_metacognition_service] = lambda: service_mock

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Summary
                res = await ac.get("/api/v1/analytics/metacognition/summary")
                assert res.status_code == 200
                data = res.json()
                assert data["calibration_accuracy_percentage"] == 85.0
                assert data["total_evaluated_quizzes"] == 3

                # 2. Course
                res = await ac.get("/api/v1/analytics/metacognition/course/1")
                assert res.status_code == 200
                data = res.json()
                assert data["course_name"] == "Biología"

                # 3. Bloom
                res = await ac.get("/api/v1/analytics/metacognition/bloom?course_id=1")
                assert res.status_code == 200
                data = res.json()
                assert len(data) == 1
                assert data[0]["bloom_level"] == "remember"

                # 4. Progress
                res = await ac.get("/api/v1/analytics/metacognition/progress?granularity=week")
                assert res.status_code == 200
                data = res.json()
                assert data["granularity"] == "week"

                # 5. Invalid granularity error handling
                service_mock.get_progress.side_effect = ValueError("granularity must be 'week' or 'month'")
                res = await ac.get("/api/v1/analytics/metacognition/progress?granularity=century")
                assert res.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user_id, None)
            app.dependency_overrides.pop(get_metacognition_service, None)


