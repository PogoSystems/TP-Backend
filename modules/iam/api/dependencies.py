from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from modules.iam.infrastructure.repositories.user_repository import UserRepository
from shared.middleware.auth import AuthenticatedUser, get_current_user


async def get_current_user_id(auth_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
                              session: Annotated[AsyncSession, Depends(get_db)]) -> int:

    repository = UserRepository(session)
    user = await repository.find_by_auth_id(UUID(auth_user.auth_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perfil incompleto. Completa tu registro antes de continuar.",
        )

    assert user.id is not None
    return user.id

#this represents the user that makes the request
#can be called in the endpoints to get the user id of the user that makes the request
CurrentUserId=Annotated[int,Depends(get_current_user_id)]

