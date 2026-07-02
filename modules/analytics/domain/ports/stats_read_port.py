from typing import Protocol

from modules.analytics.domain.aggregates import CourseStatsAggregate, BloomStatsAggregate


class StatsReadPort(Protocol):
    async def get_course_stats(self, course_id:int) -> CourseStatsAggregate| None:
        ...

    async def get_bloom_stats(self, course_id:int) -> BloomStatsAggregate| None:
        ...