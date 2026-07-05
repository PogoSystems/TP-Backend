from dataclasses import dataclass


ALLOWED_BLOOM_LEVELS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


@dataclass(slots=True)
class BloomLevelAggregate:
    level: str = ""

    def __post_init__(self) -> None:
        if self.level not in ALLOWED_BLOOM_LEVELS:
            raise ValueError(f"level must be one of {sorted(ALLOWED_BLOOM_LEVELS)}")