from dataclasses import dataclass
from typing import Protocol


@dataclass (frozen=True)
class AnswerValidation:
    """
    What quiz_management needs to know of the answer
    """
    answer_id:int
    is_correct:bool
    question_score:int


class QuizReadPort(Protocol):
    """
    Only reading port to validate the answers of a quiz
    quiz_management is going to use this port to validate the answers.
    """
    async def get_answer_validations(self, quiz_id:int, answer_ids:list[int]
                                     )-> dict[int,AnswerValidation]:
        ... # it asks for the quiz_id to validate if the answers are from that specific quiz