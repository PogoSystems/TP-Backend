import pytest
from modules.iam.domain.aggregates.user import UserAggregate


def test_user_requires_username_and_email() -> None:
    with pytest.raises(ValueError, match="username is required"):
        UserAggregate(username="", email="user@example.com")
    with pytest.raises(ValueError, match="email is required"):
        UserAggregate(username="user", email="")


def test_user_defaults() -> None:
    aggregate = UserAggregate(username="user", email="user@example.com")
    assert aggregate.created_at is not None
