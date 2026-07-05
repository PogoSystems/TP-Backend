"""Tests unitarios para CourseAggregate.

Estos tests son puramente de dominio: no requieren base de datos ni frameworks externos.
"""

import pytest
from datetime import datetime, timezone

from modules.course_management.domain.aggregates.course import CourseAggregate


class TestCourseAggregateCreation:
    """Pruebas de creación válida del aggregate."""

    def test_create_course_valid_minimal(self) -> None:
        """Un curso con name y user_id válidos se crea sin errores."""
        course = CourseAggregate(name="Cálculo I", user_id=1)

        assert course.name == "Cálculo I"
        assert course.user_id == 1

    def test_create_course_valid_full(self) -> None:
        """Un curso con todos los campos opcionales se crea correctamente."""
        course = CourseAggregate(
            name="Álgebra Lineal",
            description="Fundamentos de álgebra",
            user_id=5,
            max_score=100,
        )

        assert course.name == "Álgebra Lineal"
        assert course.description == "Fundamentos de álgebra"
        assert course.user_id == 5
        assert course.max_score == 100

    def test_course_defaults(self) -> None:
        """description y max_score son None por defecto."""
        course = CourseAggregate(name="Física", user_id=2)

        assert course.description is None
        assert course.max_score is None

    def test_course_id_is_none_by_default(self) -> None:
        """El ID es None antes de ser persistido."""
        course = CourseAggregate(name="Química", user_id=3)

        assert course.id is None

    def test_course_created_at_is_set_automatically(self) -> None:
        """created_at se asigna automáticamente con timezone UTC."""
        course = CourseAggregate(name="Historia", user_id=4)

        assert isinstance(course.created_at, datetime)
        assert course.created_at.tzinfo is not None


class TestCourseAggregateValidation:
    """Pruebas de las reglas de negocio del aggregate."""

    def test_empty_name_raises_value_error(self) -> None:
        """Un nombre vacío debe lanzar ValueError."""
        with pytest.raises(ValueError, match="name is required"):
            CourseAggregate(name="", user_id=1)

    def test_invalid_user_id_zero_raises_value_error(self) -> None:
        """user_id=0 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            CourseAggregate(name="Programación", user_id=0)

    def test_invalid_user_id_negative_raises_value_error(self) -> None:
        """user_id negativo debe lanzar ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            CourseAggregate(name="Programación", user_id=-1)
