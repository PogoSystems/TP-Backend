from datetime import datetime, timezone

from modules.quiz_management.domain.aggregates import QuestionAttemptAggregate, QuizAttemptAggregate
from modules.quiz_management.domain.ports.quiz_attempt_repository_port import QuizAttemptRepositoryPort
from modules.quiz_management.domain.ports.quiz_read_port import QuizReadPort
from modules.quiz_management.domain.ports.stats_update_port import StatsUpdatePort, QuestionAttemptSummary
from modules.quiz_management.schemas.request_schemas import SubmitQuizRequest
from modules.quiz_management.schemas.response_schemas import AttemptResultResponse, QuestionAttemptResult


class QuizAttemptService:
    """
    Define the pipeline of to submit of a quiz attempt
    """
    def __init__(self,*, quiz_read: QuizReadPort,
                 attempt_repository: QuizAttemptRepositoryPort,
                 stats_updater: StatsUpdatePort) -> None:
        self._quiz_read = quiz_read
        self._attempt_repository = attempt_repository
        self._stats_updater = stats_updater


    async def submit_quiz(self,*, quiz_id:int, user_id:int, request:SubmitQuizRequest
                          ) -> AttemptResultResponse:

        # get all the answer_ids from the request
        answer_ids =[answer.selected_answer_id for answer in request.answers]
        # validates this answers with the ones in the bd using the facade
        validations = await self._quiz_read.get_answer_validations(quiz_id, answer_ids)

        # verifies that all the answer_ids belongs to the actual quiz
        missing_Answer = [aid for aid in answer_ids if aid not in validations]
        if missing_Answer:
            raise ValueError(
                f"This answers doesn't belongs to the quiz {quiz_id}: {missing_Answer}"
            )

        # build the question_attempt and calculates the total score
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        question_attempts: list[QuestionAttemptAggregate] = []
        total_score = 0

        for submission in request.answers:
            validation = validations[submission.selected_answer_id]
            score_obtained = validation.question_score if validation.is_correct else 0
            total_score += score_obtained

            question_attempts.append(
                QuestionAttemptAggregate(
                    question_id=submission.question_id,
                    selected_answer_id=submission.selected_answer_id,
                    is_correct=validation.is_correct,
                    score_obtained=score_obtained,
                    answered_at=now
                )
            )

        # creates a quiz_attempt
        attempt = QuizAttemptAggregate(
            user_id=user_id,
            quiz_id=quiz_id,
            total_score=total_score,
            started_at = request.started_at.replace(tzinfo=None),
            submitted_at=now,
        )

        #save the attempt in the database
        saved_attempt = await self._attempt_repository.save_attempt(attempt, question_attempts)

        #update the metrics of analytics
        course_id= await self._quiz_read.get_course_id_for_quiz(quiz_id)
        if course_id is not None:
            summaries = [
                QuestionAttemptSummary(
                    bloom_level=validations[s.selected_answer_id].bloom_level,
                    is_correct=validations[s.selected_answer_id].is_correct,
                )
                for s in request.answers
            ]
            await self._stats_updater.update_stats_after_submit(course_id=course_id, question_summaries=summaries)

        # build the response
        return AttemptResultResponse(
            attempt_id=saved_attempt.id,
            quiz_id=quiz_id,
            total_score=total_score,
            submitted_at=now,
            question_results=[
                QuestionAttemptResult(
                    question_id=qa.question_id,
                    selected_answer_id=qa.selected_answer_id,
                    is_correct=qa.is_correct,
                    score_obtained=qa.score_obtained,
                )
                for qa in question_attempts
            ],
        )