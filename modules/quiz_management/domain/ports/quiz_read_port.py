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
    bloom_level:str


class QuizReadPort(Protocol):
    """
    Only reading port to validate the answers of a quiz
    quiz_management is going to use this port to validate the answers.
    """
    async def get_answer_validations(self, quiz_id:int, answer_ids:list[int]
                                     )-> dict[int,AnswerValidation]:
        ... # it asks for the quiz_id to validate if the answers are from that specific quiz


    async def get_course_id_for_quiz(self, quiz_id: int) -> int | None:
        """
        Get the course_id for a given quiz_id to update the stats
        """
        ...