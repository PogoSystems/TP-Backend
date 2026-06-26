from typing import Protocol
from uuid import UUID

from modules.iam.domain.aggregates import UserAggregate


class UserRepositoryPort(Protocol):
    async def find_by_auth_id(self, auth_id: UUID) -> UserAggregate | None:
        ...

    async def save_from_auth(self, user: UserAggregate) -> UserAggregate:
        ...