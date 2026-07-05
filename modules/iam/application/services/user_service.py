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

    async def edit_profile(self, *, auth_id: str, name: str | None = None, last_name: str | None = None, college: str | None = None, major: str | None = None) -> UserAggregate:
        auth_uuid = UUID(auth_id)
        existing_profile = await self._repository.find_by_auth_id(auth_uuid)
        
        if existing_profile is None:
            raise ValueError("User profile not found")
            
        existing_profile.update_profile(name=name, last_name=last_name, college=college, major=major)
        return await self._repository.update(existing_profile)

    async def get_profile(self, auth_id: str) -> UserAggregate:
        auth_uuid = UUID(auth_id)
        profile = await self._repository.find_by_auth_id(auth_uuid)
        if profile is None:
            raise ValueError("User profile not found")
        return profile