from sqlalchemy import Sequence
from modules.quiz_generation.infrastructure.models import question_model
from shared.exceptions import DocumentNotFoundError
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.quiz_generation.domain.aggregates.quiz import QuizAggregate
from modules.quiz_generation.domain.aggregates.question import QuestionAggregate
from modules.quiz_generation.domain.aggregates.answer import AnswerAggregate

from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel
from modules.quiz_generation.infrastructure.models.question_model import QuestionModel
from modules.quiz_generation.infrastructure.models.answer_model import AnswerModel


class QuizPersistenceRepository:
    """Repositorio de solo escritura para quiz_generation.

    Satisface QuizPersistencePort: únicamente persiste quizzes recién
    generados por el LLM. No realiza lecturas ni modificaciones posteriores,
    esa responsabilidad pertenece a quiz_management.

    Accede a QuizModel (definido en quiz_management) porque ambos módulos
    comparten la misma base de datos en el monolito. Al separar en
    microservicios, este repositorio sería reemplazado por una llamada
    HTTP/gRPC al endpoint de persistencia de quiz_management.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, quiz: QuizAggregate) -> QuizAggregate:
        """Persiste un quiz generado y retorna el aggregate con el ID asignado."""

        # get the max score
        max_score = sum(q.score for q in quiz.questions)

        # Persistencia del quiz
        model = self._to_quiz_model(quiz, max_score=max_score)
        self._session.add(model)
        await self._session.flush()
        quiz.id = model.id
        quiz.max_score = max_score

        # Persistencia de las preguntas
        for q in quiz.questions:
            question_model = self._to_question_model(q, model.id)
            self._session.add(question_model)
            await self._session.flush()
            q.id = question_model.id
            # Persistencia de las respuestas
            for a in q.answers:
                answer_model = self._to_answer_model(a, question_model.id)
                self._session.add(answer_model)
                await self._session.flush()
                a.id = answer_model.id

        return quiz

    async def get_quiz_by_id(self, quiz_id: int) -> QuizAggregate:
        """Retorna un quiz por su ID."""
        
        quiz_query = select(QuizModel).where(QuizModel.id == quiz_id)

        quiz = await self._session.execute(quiz_query)
        quiz_model = quiz.scalar_one_or_none()
        if quiz_model is None:
            raise ValueError(f"Quiz with ID {quiz_id} not found")
        questions_query = select(QuestionModel).where(QuestionModel.quiz_id == quiz_id)
        questions = await self._session.execute(questions_query)
        questions_models = questions.scalars().all()

        answers_query = select(AnswerModel).where(AnswerModel.question_id.in_([q.id for q in questions_models]))
        answers = await self._session.execute(answers_query)
        answers_models = answers.scalars().all()

        return self._to_quiz_aggregate(quiz_model, questions_models, answers_models)

    async def get_quizzes_by_course_id(self, course_id: int) -> list[QuizAggregate]:
        """Retorna todos los quizes de un curso."""
        query = select(QuizModel).where(QuizModel.course_id == course_id)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._to_aggregate(model) for model in models]

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_aggregate(model: QuizModel) -> QuizAggregate:
        return QuizAggregate(
            id=model.id,
            user_id=model.user_id,
            course_id=model.course_id,
            title=model.title,
            created_at=model.created_at.replace(tzinfo=timezone.utc),
        )

    @staticmethod
    def _to_quiz_aggregate(model: QuizModel, questions:Sequence[QuestionModel], answers:Sequence[AnswerModel]) -> QuizAggregate:
        return QuizAggregate(
            id=model.id,
            user_id=model.user_id,
            course_id=model.course_id,
            title=model.title,
            created_at=model.created_at.replace(tzinfo=timezone.utc),
            questions = [QuizPersistenceRepository._to_question_aggregate(q, answers) for q in questions],
        )
    
    @staticmethod
    def _to_question_aggregate(model:QuestionModel, answers:Sequence[AnswerModel]) -> QuestionAggregate:
        return QuestionAggregate(
            id=model.id,
            text=model.text,
            bloom_level=model.bloom_level,
            score=model.score,
            explanation=model.explanation,
            answers = [QuizPersistenceRepository._to_answer_aggregate(a) for a in answers if a.question_id == model.id]
        )
    
    @staticmethod
    def _to_answer_aggregate(model:AnswerModel) -> AnswerAggregate:
        return AnswerAggregate(
            id=model.id,
            text=model.text,
            is_correct=model.is_correct,
        )


    @staticmethod
    def _to_quiz_model(aggregate: QuizAggregate, max_score: int) -> QuizModel:
        return QuizModel(
            user_id=aggregate.user_id,
            course_id=aggregate.course_id,
            title=aggregate.title,
            max_score = max_score
        )

    @staticmethod
    def _to_question_model(aggregate: QuestionAggregate, quiz_id: int) -> QuestionModel:
        return QuestionModel(
            quiz_id=quiz_id,
            text=aggregate.text,
            bloom_level=aggregate.bloom_level,
            score=aggregate.score,
            explanation=aggregate.explanation,
        )
    
    @staticmethod
    def _to_answer_model(aggregate: AnswerAggregate, question_id: int) -> AnswerModel:
        return AnswerModel(
            question_id=question_id,
            text=aggregate.text,
            is_correct=aggregate.is_correct,
        )
    