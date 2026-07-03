from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.quiz_generation.infrastructure.models.answer_model import AnswerModel
from modules.quiz_generation.infrastructure.models.question_model import QuestionModel
from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel
from modules.quiz_management.domain.ports.quiz_read_port import AnswerValidation


class QuizReadFacade:
    """
    Implements the "interface" of quiz read port in the infrastructure layer.
    It is used to validate the answers of a quiz.
    """
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_answer_validations(self, quiz_id:int,answer_ids:list[int]
                                     ) -> dict[int, AnswerValidation]:

        """
        Makes one JOIN between the answer and the question to obtain
        is_correct and score in only one query
        """
        stmt=(
            select(AnswerModel.id, AnswerModel.is_correct,QuestionModel.score, QuestionModel.bloom_level)
            .join(QuestionModel, AnswerModel.question_id == QuestionModel.id)
            .where(
        QuestionModel.quiz_id == quiz_id,
                   AnswerModel.id.in_(answer_ids))
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        # Return a dictionary to have a O(1)
        return{
            row.id: AnswerValidation(
                answer_id=row.id,
                is_correct=row.is_correct,
                question_score=row.score,
                bloom_level=row.bloom_level
            )
            for row in rows
        }