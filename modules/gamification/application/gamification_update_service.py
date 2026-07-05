from typing import Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import logging

from modules.iam.infrastructure.models.user_model import UserModel
from modules.course_management.infrastructure.models import CourseModel
from modules.gamification.infrastructure.models import UserAchievementModel, AchievementModel
from modules.gamification.application.achievement_evaluators import AchievementRegistry

logger = logging.getLogger(__name__)

class GamificationUpdateService:
    
    async def process_action(self, user_id: int, action_type: str, context: dict[str, Any], session: AsyncSession) -> None:
        """Processes gamification updates for a given action."""
        await self._update_streak(user_id, session)
        if action_type == "quiz_submitted":
            await self._update_highest_score(user_id, context, session)
            
        await self._evaluate_achievements(user_id, action_type, context, session)

    async def _update_streak(self, user_id: int, session: AsyncSession) -> None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = now.date()
        
        if user.last_streak_date:
            last_date = user.last_streak_date.date()
            if last_date == today:
                # Already updated today
                return
            elif last_date == today - timedelta(days=1):
                # Streak continues
                user.current_streak += 1
            else:
                # Streak broken
                user.current_streak = 1
        else:
            # First time
            user.current_streak = 1
            
        user.last_streak_date = now
        user.streak_updated_at = now
        
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak

    async def _update_highest_score(self, user_id: int, context: dict[str, Any], session: AsyncSession) -> None:
        course_id = context.get("course_id")
        total_score = context.get("total_score", 0)
        
        if course_id is None:
            return
            
        stmt = select(CourseModel).where(CourseModel.id == course_id, CourseModel.user_id == user_id)
        res = await session.execute(stmt)
        course = res.scalar_one_or_none()
        
        if course:
            current_max = course.max_score or 0
            if total_score > current_max:
                course.max_score = total_score

    async def _evaluate_achievements(self, user_id: int, action_type: str, context: dict[str, Any], session: AsyncSession) -> None:
        evaluators = AchievementRegistry.get_evaluators_for_action(action_type)
        if not evaluators:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        ach_ids = [e.get_achievement_id() for e in evaluators]
        
        # Obtenemos los requisitos de progreso de los logros que vamos a evaluar
        stmt_ach = select(AchievementModel.id, AchievementModel.required_progress).where(AchievementModel.id.in_(ach_ids))
        res_ach = await session.execute(stmt_ach)
        ach_requirements = {row.id: row.required_progress for row in res_ach.all()}

        # Obtenemos los registros de usuario solo para estos logros
        stmt = select(UserAchievementModel).where(
            UserAchievementModel.user_id == user_id,
            UserAchievementModel.achievement_id.in_(ach_ids)
        )
        res = await session.execute(stmt)
        user_achievements = {ua.achievement_id: ua for ua in res.scalars()}

        for evaluator in evaluators:
            ach_id = evaluator.get_achievement_id()
            ua = user_achievements.get(ach_id)
            
            if ua and ua.unlocked_at:
                continue
                
            try:
                is_unlocked, progress_added = await evaluator.evaluate(user_id, context, session)
                req_progress = ach_requirements.get(ach_id, 1) 
                
                if progress_added > 0 or is_unlocked:
                    if not ua:
                        ua = UserAchievementModel(
                            user_id=user_id,
                            achievement_id=ach_id,
                            progress=progress_added,
                        )
                        session.add(ua)
                        user_achievements[ach_id] = ua
                    else:
                        ua.progress += progress_added
                        
                    # Desbloqueamos si el evaluador dice True, o si se alcanzó el progreso requerido
                    if is_unlocked or (req_progress > 0 and ua.progress >= req_progress):
                        ua.unlocked_at = now
            except Exception as e:
                logger.error(f"Error evaluating achievement {ach_id} for user {user_id}: {e}")

