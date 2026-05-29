import pytest
from modules.bloom_taxonomy.domain.aggregates.bloom_level import BloomLevelAggregate


def test_bloom_level_requires_valid_level() -> None:
    with pytest.raises(ValueError, match="level must be one of"):
        BloomLevelAggregate(level="invalid")


def test_bloom_level_defaults() -> None:
    aggregate = BloomLevelAggregate(level="remember")
    assert aggregate.level == "remember"