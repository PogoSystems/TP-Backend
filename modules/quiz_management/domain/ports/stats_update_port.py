from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class QuestionAttemptSummary:
    """
    The information that analytics needs about a question attempt
    """
    bloom_level:str
    is_correct:bool

class StatsUpdatePort(Protocol):
    async def update_stats_after_submit(self, course_id:int, question_summaries:list[QuestionAttemptSummary]) -> None:
        """
        Update the course and bloom stats after a quiz submission.
        This method is called after a quiz is submitted, and it updates the course stats and bloom stats based on the question summaries provided.
        """
        ...