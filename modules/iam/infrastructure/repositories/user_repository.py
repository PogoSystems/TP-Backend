from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.iam.domain.aggregates import UserAggregate
from modules.iam.infrastructure.models.user_model import UserModel


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session=session

    async def find_by_auth_id(self, auth_id:UUID) -> UserAggregate | None:
        stmt= select(UserModel).where(UserModel.auth_id == auth_id) # build the query
        result= await self._session.execute(stmt) #send the query to the bd
        model =result.scalar_one_or_none() #return the result from the query

        if model is None:
            return None
        return self._to_aggregate(model)

    async def create_from_auth(self, user: UserAggregate) -> UserAggregate:
        model = self._to_model(user)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_aggregate(model)


    @staticmethod
    def _to_aggregate(model:UserModel) -> UserAggregate:
        return UserAggregate(
            id=model.id,
            auth_id=model.auth_id,
            name=model.name,
            last_name=model.last_name,
            college=model.college,
            major=model.major,
            email=model.email,
            created_at=model.created_at
        )

    @staticmethod
    def _to_model(aggregate: UserAggregate) -> UserModel:
        return UserModel(
            auth_id=aggregate.auth_id,
            name=aggregate.name,
            last_name=aggregate.last_name,
            college=aggregate.college,
            major=aggregate.major,
            email=aggregate.email,
        )

