from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from modules.gamification.infrastructure.models import AchievementModel, UserAchievementModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.course_management.infrastructure.models import CourseModel


class GamificationQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_stats(self, user_id: int) -> dict:
        user_stmt = select(UserModel.current_streak, UserModel.best_streak).where(UserModel.id == user_id)
        user_res = await self._session.execute(user_stmt)
        user_row = user_res.first()
        current_streak = user_row.current_streak if user_row else 0
        best_streak = user_row.best_streak if user_row else 0

        course_stmt = select(func.sum(CourseModel.max_score)).where(CourseModel.user_id == user_id)
        course_res = await self._session.execute(course_stmt)
        highest_score = course_res.scalar() or 0

        unlocked_stmt = select(func.count(UserAchievementModel.achievement_id)).where(
            UserAchievementModel.user_id == user_id, 
            UserAchievementModel.unlocked_at.isnot(None)
        )
        unlocked_res = await self._session.execute(unlocked_stmt)
        achievements_unlocked = unlocked_res.scalar() or 0

        total_stmt = select(func.count(AchievementModel.id))
        total_res = await self._session.execute(total_stmt)
        achievements_total = total_res.scalar() or 0

        return {
            "current_streak": current_streak,
            "best_streak": best_streak,
            "highest_score": int(highest_score),
            "achievements_unlocked": achievements_unlocked,
            "achievements_total": achievements_total
        }

    async def ensure_user_achievements(self, user_id: int) -> None:
        all_stmt = select(AchievementModel.id)
        all_res = await self._session.execute(all_stmt)
        all_ids = {row[0] for row in all_res.all()}

        user_stmt = select(UserAchievementModel.achievement_id).where(UserAchievementModel.user_id == user_id)
        user_res = await self._session.execute(user_stmt)
        user_ids = {row[0] for row in user_res.all()}

        missing_ids = all_ids - user_ids
        if missing_ids:
            new_records = [
                UserAchievementModel(user_id=user_id, achievement_id=ach_id, progress=0)
                for ach_id in missing_ids
            ]
            self._session.add_all(new_records)
            await self._session.flush()

    async def get_achievements(self, user_id: int) -> list[dict]:
        await self.ensure_user_achievements(user_id)
        stmt = (
            select(
                AchievementModel.id,
                AchievementModel.name,
                AchievementModel.description,
                AchievementModel.img_url,
                AchievementModel.required_progress,
                UserAchievementModel.progress,
                UserAchievementModel.unlocked_at
            )
            .outerjoin(UserAchievementModel, 
                       (AchievementModel.id == UserAchievementModel.achievement_id) & 
                       (UserAchievementModel.user_id == user_id))
            .order_by(AchievementModel.id)
        )
        res = await self._session.execute(stmt)
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "img_url": row.img_url,
                "unlocked": row.unlocked_at is not None,
                "unlocked_at": row.unlocked_at,
                "progress_current": row.progress if row.progress is not None else None,
                "progress_target": row.required_progress if row.required_progress > 0 else None,
            }
            for row in res.all()
        ]

    async def get_recent_achievement(self, user_id: int) -> dict | None:
        from modules.iam.infrastructure.models.user_model import UserModel
        
        user_stmt = select(UserModel.current_streak).where(UserModel.id == user_id)
        user_res = await self._session.execute(user_stmt)
        user_row = user_res.first()
        streak = user_row.current_streak if user_row else 0

        stmt = (
            select(
                AchievementModel.id,
                AchievementModel.name,
                AchievementModel.description,
                AchievementModel.img_url,
                UserAchievementModel.unlocked_at
            )
            .join(UserAchievementModel, AchievementModel.id == UserAchievementModel.achievement_id)
            .where(UserAchievementModel.user_id == user_id, UserAchievementModel.unlocked_at.isnot(None))
            .order_by(UserAchievementModel.unlocked_at.desc())
            .limit(1)
        )
        res = await self._session.execute(stmt)
        row = res.first()
        if row:
            return {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "img_url": row.img_url,
                "unlocked": True,
                "unlocked_at": row.unlocked_at,
                "progress_current": None,
                "progress_target": None,
                "current_streak": streak
            }
        return {"current_streak": streak}
