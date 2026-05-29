import pytest
from modules.gamification.domain.aggregates.user_achievement import UserAchievementAggregate


def test_user_achievement_requires_ids() -> None:
    with pytest.raises(ValueError, match="user_id is required"):
        UserAchievementAggregate(user_id=0, achievement_id=1)
    with pytest.raises(ValueError, match="achievement_id is required"):
        UserAchievementAggregate(user_id=1, achievement_id=0)