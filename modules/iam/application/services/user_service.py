from uuid import UUID

from modules.iam.domain.aggregates import UserAggregate
from modules.iam.domain.ports.user_repository_port import UserRepositoryPort


class UserService:
    def __init__(self, repository: UserRepositoryPort) -> None:
        self._repository = repository

    async def complete_profile(self, *, auth_id:str, email:str, name:str, last_name:str, college:str, major:str) -> UserAggregate:
        auth_uuid = UUID(auth_id)
        existing_profile = await self._repository.find_by_auth_id(auth_uuid)

        # if the user already has a profile, return it, otherwise create a new one
        if existing_profile is not None:
            return existing_profile

        user = UserAggregate(
            auth_id=auth_uuid,
            email=email,
            name=name,
            last_name=last_name,
            college=college,
            major=major
        )
        return await self._repository.save_from_auth(user)