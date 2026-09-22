from collections import defaultdict
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from modules.analytics.infrastructure.repositories.metacognition_query_repository import MetacognitionQueryRepository
from modules.analytics.schemas.response_schemas import (
    BloomMetacognitionResponse,
    CourseMetacognitionResponse,
    MetacognitionCourseSummary,
    MetacognitionProgressPoint,
    MetacognitionProgressResponse,
    MetacognitionRecentAttempt,
    MetacognitionSummaryResponse,
)


class MetacognitionService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MetacognitionQueryRepository(session)

    @staticmethod
    def _determine_bias(gap: float, accuracy: float | None = None) -> str:
        if gap > 0.5:
            return "overconfident"
        elif gap < -0.5:
            return "underconfident"
        if accuracy is not None and accuracy < 75.0:
            return "variable"
        return "calibrated"

    @staticmethod
    def _calculate_accuracy(expected: float, actual: float, total: int) -> float:
        if total <= 0:
            return 0.0
        acc = 100.0 - (abs(expected - actual) / total * 100.0)
        return round(max(0.0, min(100.0, acc)), 1)

    async def get_summary(self, user_id: int) -> MetacognitionSummaryResponse:
        attempts = await self._repo.get_raw_attempts(user_id)
        if not attempts:
            return MetacognitionSummaryResponse(
                calibration_accuracy_percentage=0.0,
                average_expected=0.0,
                average_actual=0.0,
                bias="calibrated",
                bias_gap=0.0,
                total_evaluated_quizzes=0,
                course_breakdown=[],
            )

        total_quizzes = len(attempts)
        sum_expected = sum(a["expected_correct"] for a in attempts)
        sum_actual = sum(a["actual_correct"] for a in attempts)
        avg_expected = round(sum_expected / total_quizzes, 1)
        avg_actual = round(sum_actual / total_quizzes, 1)
        bias_gap = round(avg_expected - avg_actual, 1)
        accuracies = [
            self._calculate_accuracy(a["expected_correct"], a["actual_correct"], a["total_questions"])
            for a in attempts
        ]
        overall_accuracy = round(sum(accuracies) / total_quizzes, 1)
        bias = self._determine_bias(bias_gap, overall_accuracy)

        # Agrupación por curso
        by_course = defaultdict(list)
        for a in attempts:
            by_course[(a["course_id"], a["course_name"])].append(a)

        breakdown = []
        for (c_id, c_name), c_attempts in by_course.items():
            c_accs = [
                self._calculate_accuracy(a["expected_correct"], a["actual_correct"], a["total_questions"])
                for a in c_attempts
            ]
            c_gap = (sum(a["expected_correct"] for a in c_attempts) - sum(a["actual_correct"] for a in c_attempts)) / len(c_attempts)
            c_accuracy = round(sum(c_accs) / len(c_attempts), 1)
            breakdown.append(
                MetacognitionCourseSummary(
                    course_id=c_id,
                    course_name=c_name,
                    quizzes_evaluated=len(c_attempts),
                    calibration_accuracy_percentage=c_accuracy,
                    bias=self._determine_bias(c_gap, c_accuracy),
                )
            )

        breakdown.sort(key=lambda c: c.course_name)

        return MetacognitionSummaryResponse(
            calibration_accuracy_percentage=overall_accuracy,
            average_expected=avg_expected,
            average_actual=avg_actual,
            bias=bias,
            bias_gap=bias_gap,
            total_evaluated_quizzes=total_quizzes,
            course_breakdown=breakdown,
        )

    async def get_course_detail(self, user_id: int, course_id: int) -> CourseMetacognitionResponse:
        attempts = await self._repo.get_raw_attempts(user_id, course_id=course_id)
        if not attempts:
            course_name = await self._repo.get_course_name(course_id) or ""
            return CourseMetacognitionResponse(
                course_id=course_id,
                course_name=course_name,
                calibration_accuracy_percentage=0.0,
                average_expected=0.0,
                average_actual=0.0,
                bias="calibrated",
                quizzes_evaluated=0,
                recent_attempts=[],
            )

        course_name = attempts[0]["course_name"]
        total_quizzes = len(attempts)
        avg_expected = round(sum(a["expected_correct"] for a in attempts) / total_quizzes, 1)
        avg_actual = round(sum(a["actual_correct"] for a in attempts) / total_quizzes, 1)
        bias_gap = round(avg_expected - avg_actual, 1)

        accuracies = [
            self._calculate_accuracy(a["expected_correct"], a["actual_correct"], a["total_questions"])
            for a in attempts
        ]

        recent = [
            MetacognitionRecentAttempt(
                quiz_id=a["quiz_id"],
                quiz_title=a["quiz_title"],
                submitted_at=a["submitted_at"],
                total_questions=a["total_questions"],
                expected_correct=a["expected_correct"],
                actual_correct=int(a["actual_correct"]),
                gap=round(float(a["expected_correct"] - a["actual_correct"]), 1),
                calibration_accuracy=self._calculate_accuracy(
                    a["expected_correct"], a["actual_correct"], a["total_questions"]
                ),
            )
            for a in attempts[:3]
        ]

        course_accuracy = round(sum(accuracies) / total_quizzes, 1)

        return CourseMetacognitionResponse(
            course_id=course_id,
            course_name=course_name,
            calibration_accuracy_percentage=course_accuracy,
            average_expected=avg_expected,
            average_actual=avg_actual,
            bias=self._determine_bias(bias_gap, course_accuracy),
            quizzes_evaluated=total_quizzes,
            recent_attempts=recent,
        )

    async def get_bloom_breakdown(self, user_id: int, course_id: int | None = None) -> list[BloomMetacognitionResponse]:
        rows = await self._repo.get_raw_bloom_data(user_id, course_id=course_id)
        if not rows:
            return []

        bloom_data = defaultdict(lambda: {"attempted": 0, "actual": 0, "expected": 0.0})
        for r in rows:
            lvl = r["bloom_level"]
            count_q = r["bloom_questions_count"]
            tot_att = r["attempt_total_questions"]
            exp_att = r["expected_correct_answers"]

            bloom_data[lvl]["attempted"] += count_q
            bloom_data[lvl]["actual"] += int(r["bloom_actual_correct"])
            if tot_att > 0:
                bloom_data[lvl]["expected"] += count_q * (exp_att / tot_att)

        results = []
        for lvl, data in bloom_data.items():
            att = data["attempted"]
            act = int(data["actual"])
            exp = round(data["expected"], 1)
            gap = exp - act
            acc = self._calculate_accuracy(exp, act, att)
            results.append(
                BloomMetacognitionResponse(
                    bloom_level=str(lvl.value if hasattr(lvl, "value") else lvl),
                    questions_attempted=att,
                    actual_correct=act,
                    expected_correct=exp,
                    calibration_accuracy=acc,
                    bias=self._determine_bias(gap, acc),
                )
            )

        return sorted(results, key=lambda x: x.bloom_level)

    async def get_progress(self, user_id: int, granularity: str = "week", course_id: int | None = None) -> MetacognitionProgressResponse:
        if granularity not in ("week", "month"):
            raise ValueError("granularity must be 'week' or 'month'")

        attempts = await self._repo.get_raw_attempts(user_id, course_id=course_id)
        if not attempts:
            return MetacognitionProgressResponse(granularity=granularity, points=[])

        grouped = defaultdict(list)
        for a in attempts:
            dt = a["submitted_at"]
            if granularity == "month":
                key = dt.strftime("%Y-%m-01")
            else:
                monday = dt.date() - timedelta(days=dt.weekday())
                key = monday.strftime("%Y-%m-%d")
            grouped[key].append(a)

        points = []
        for period in sorted(grouped.keys()):
            pts = grouped[period]
            cnt = len(pts)
            avg_exp = round(sum(p["expected_correct"] for p in pts) / cnt, 1)
            avg_act = round(sum(p["actual_correct"] for p in pts) / cnt, 1)
            accs = [
                self._calculate_accuracy(p["expected_correct"], p["actual_correct"], p["total_questions"])
                for p in pts
            ]
            points.append(
                MetacognitionProgressPoint(
                    period=period,
                    avg_expected=avg_exp,
                    avg_actual=avg_act,
                    calibration_accuracy=round(sum(accs) / cnt, 1),
                    quizzes_count=cnt,
                )
            )

        return MetacognitionProgressResponse(granularity=granularity, points=points)
