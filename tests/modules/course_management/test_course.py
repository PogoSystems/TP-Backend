import pytest
from modules.course_management.domain.aggregates.course import CourseAggregate


def test_course_requires_name_and_user() -> None:
    with pytest.raises(ValueError, match="name is required"):
        CourseAggregate(name="", user_id=1)
    with pytest.raises(ValueError, match="user_id is required"):
        CourseAggregate(name="Calculus", user_id=0)


def test_course_defaults() -> None:
    aggregate = CourseAggregate(name="Calculus", user_id=1)
    assert aggregate.created_at is not None
