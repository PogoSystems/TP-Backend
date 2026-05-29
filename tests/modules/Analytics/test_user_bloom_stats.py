import pytest
from modules.analytics.domain.aggregates.user_bloom_stats import UserBloomStatsAggregate


def test_user_bloom_stats_requires_user() -> None:
    with pytest.raises(ValueError, match="user_id is required"):
        UserBloomStatsAggregate(user_id=0)


def test_user_bloom_stats_defaults() -> None:
    aggregate = UserBloomStatsAggregate(user_id=1)
    assert aggregate.correct_questions == 0