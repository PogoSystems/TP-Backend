from uuid import UUID

from modules.iam.domain.aggregates import UserAggregate, user
from modules.iam.infrastructure.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def complete_profile(self, *, auth_id:str, email:str, name:str, last_name:str, college:str, major:str) -> UserAggregate:
        auth_uui = UUID(auth_id)
        existing_profile = await self._repository.find_by_auth_id(auth_uui)

        # if the user already has a profile, return it, otherwise create a new one
        if existing_profile is not None:
            return existing_profile

        user = UserAggregate(
            auth_id=auth_uui,
            email=email,
            name=name,
            last_name=last_name,
            college=college,
            major=major
        )
        return await self._repository.create_from_auth(user)