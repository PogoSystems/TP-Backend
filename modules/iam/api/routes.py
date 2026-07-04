from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated

from core.db.database import get_db
from modules.iam.application.services.user_service import UserService
from modules.iam.infrastructure.repositories.user_repository import UserRepository
from modules.iam.schemas import UserResponse, CompleteProfileRequest, EditProfileRequest
from shared.middleware.auth import get_current_user, AuthenticatedUser

router=APIRouter(prefix="/auth", tags=["auth"])

def get_user_service(session: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)

UserSvc = Annotated[UserService, Depends(get_user_service)]
AuthUser= Annotated[AuthenticatedUser, Depends(get_current_user)]

@router.post(
    "/complete-profile",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_profile(payload: CompleteProfileRequest, auth_user: AuthUser, service: UserSvc) -> UserResponse:
    try:
        user = await service.complete_profile(
            auth_id=auth_user.auth_id,
            email=auth_user.email,
            name=payload.name,
            last_name=payload.last_name,
            college=payload.college,
            major=payload.major,
        )
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception))

    return UserResponse(
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        college=user.college,
        major=user.major,
    )

@router.put(
    "/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_profile(payload: EditProfileRequest, auth_user: AuthUser, service: UserSvc) -> UserResponse:
    try:
        user = await service.edit_profile(
            auth_id=auth_user.auth_id,
            name=payload.name,
            last_name=payload.last_name,
            college=payload.college,
            major=payload.major,
        )
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception))

    return UserResponse(
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        college=user.college,
        major=user.major,
    )

@router.get(
    "/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_profile(auth_user: AuthUser, service: UserSvc) -> UserResponse:
    try:
        user = await service.get_profile(auth_id=auth_user.auth_id)
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exception))

    return UserResponse(
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        college=user.college,
        major=user.major,
    )