from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

class AchievementEvaluator(ABC):
    """Base class for all achievement evaluators."""
    
    @abstractmethod
    def get_achievement_id(self) -> int:
        pass
        
    @abstractmethod
    def supported_actions(self) -> list[str]:
        pass

    @abstractmethod
    async def evaluate(self, user_id: int, context: dict[str, Any], session: AsyncSession) -> tuple[bool, int]:
        """
        Evaluates if the achievement should be updated based on context.
        Returns a tuple: (is_unlocked, progress_added)
        """
        pass

class AchievementRegistry:
    _evaluators: list[AchievementEvaluator] = []

    @classmethod
    def register(cls, evaluator: AchievementEvaluator) -> None:
        cls._evaluators.append(evaluator)

    @classmethod
    def get_evaluators_for_action(cls, action_type: str) -> list[AchievementEvaluator]:
        return [e for e in cls._evaluators if action_type in e.supported_actions()]

class FirstQuizEvaluator(AchievementEvaluator):
    def get_achievement_id(self) -> int:
        return 1
    
    def supported_actions(self) -> list[str]:
        return ["quiz_submitted"]
    
    async def evaluate(self, user_id: int, context: dict[str, Any], session: AsyncSession) -> tuple[bool, int]:
        return True, 1

AchievementRegistry.register(FirstQuizEvaluator())

class CorrectAnswers25(AchievementEvaluator):
    def get_achievement_id(self) -> int:
         return 2# ID of the achievement in DB

    def supported_actions(self)-> list[str]:
        return ["quiz_submitted"]

    async def evaluate(self, user_id: int, context: dict[str, Any], session: AsyncSession) -> tuple[bool, int]:
        correct_answers: int = context.get("correct_count", 0)
        if correct_answers >0:
            return True, correct_answers
        return False, 0
AchievementRegistry.register(CorrectAnswers25())


class PerfectScoreEvaluator(AchievementEvaluator):
    def get_achievement_id(self) -> int:
        return 3 # ID of the achievement in DB
        
    def supported_actions(self) -> list[str]:
        return ["quiz_submitted"]
        
    async def evaluate(self, user_id: int, context: dict[str, Any], session: AsyncSession) -> tuple[bool, int]:
      #Extraemos los datos que mandamos desde quiz_management
      #Lógica del logro:
        if context.get("correct_count") == context.get("total_questions") and context.get("total_questions", 0) > 0:
            return True, 1
        return False, 0
AchievementRegistry.register(PerfectScoreEvaluator())
