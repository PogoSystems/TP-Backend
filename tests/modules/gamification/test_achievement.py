import pytest
from modules.gamification.domain.aggregates.achievement import AchievementAggregate


def test_achievement_requires_name_and_description() -> None:
    with pytest.raises(ValueError, match="name is required"):
        AchievementAggregate(name="", description="desc", img_url="https://img")
    with pytest.raises(ValueError, match="description is required"):
        AchievementAggregate(name="Starter", description="", img_url="https://img")


def test_achievement_defaults() -> None:
    aggregate = AchievementAggregate(name="Starter", description="desc", img_url="https://img")
    assert aggregate.created_at is not None