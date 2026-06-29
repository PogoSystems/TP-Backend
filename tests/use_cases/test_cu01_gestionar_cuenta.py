"""Tests unitarios para Casos de Uso - CU01: Gestionar Cuenta y Perfil (IAM)."""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
import pytest

from modules.iam.application.services.user_service import UserService
from modules.iam.domain.aggregates.user import UserAggregate


def make_user(
    auth_id=None,
    email: str = "estudiante@universidad.edu.pe",
    name: str = "Juan",
    last_name: str = "Pérez",
    college: str = "Ingeniería",
    major: str = "Sistemas",
) -> UserAggregate:
    """Crea un UserAggregate de prueba."""
    return UserAggregate(
        auth_id=auth_id or uuid4(),
        email=email,
        name=name,
        last_name=last_name,
        college=college,
        major=major,
    )


def make_repository(**kwargs) -> MagicMock:
    """Crea un mock del repositorio de usuarios."""
    repo = MagicMock()
    repo.find_by_auth_id = AsyncMock(return_value=kwargs.get("find_by_auth_id", None))
    repo.save_from_auth = AsyncMock(return_value=kwargs.get("save_from_auth", None))
    return repo


class TestCU01GestionarCuenta:
    """Pruebas asociadas al caso de uso CU01."""

    def test_user_creation_success(self) -> None:
        user = make_user()
        assert user.name == "Juan"
        assert user.last_name == "Pérez"
        assert user.college == "Ingeniería"
        assert user.major == "Sistemas"
        assert user.email == "estudiante@universidad.edu.pe"

    def test_missing_email_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="email is required"):
            make_user(email="")

    def test_missing_college_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="college is required"):
            make_user(college="")

    def test_missing_major_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="major is required"):
            make_user(major="")

    @pytest.mark.asyncio
    async def test_complete_profile_creates_new_user(self) -> None:
        """Flujo principal CU01: Creación y registro de perfil inicial."""
        auth_id = uuid4()
        expected_user = make_user(auth_id=auth_id)
        repo = make_repository(find_by_auth_id=None, save_from_auth=expected_user)
        service = UserService(repo)

        user = await service.complete_profile(
            auth_id=str(auth_id),
            email="estudiante@universidad.edu.pe",
            name="Juan",
            last_name="Pérez",
            college="Ingeniería",
            major="Sistemas",
        )

        repo.find_by_auth_id.assert_called_once()
        repo.save_from_auth.assert_called_once()
        assert user.email == "estudiante@universidad.edu.pe"
        assert user.college == "Ingeniería"

    @pytest.mark.asyncio
    async def test_complete_profile_returns_existing_user(self) -> None:
        """Retorna usuario existente si ya se encontraba registrado."""
        auth_id = uuid4()
        existing_user = make_user(auth_id=auth_id)
        repo = make_repository(find_by_auth_id=existing_user)
        service = UserService(repo)

        user = await service.complete_profile(
            auth_id=str(auth_id),
            email="estudiante@universidad.edu.pe",
            name="Juan",
            last_name="Pérez",
            college="Ingeniería",
            major="Sistemas",
        )

        repo.find_by_auth_id.assert_called_once()
        repo.save_from_auth.assert_not_called()
        assert user == existing_user
