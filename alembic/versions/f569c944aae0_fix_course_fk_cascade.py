"""fix course fk cascade

Revision ID: f569c944aae0
Revises: f89e6d492bb9
Create Date: 2026-06-25 23:54:50.799670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f569c944aae0'
down_revision: Union[str, Sequence[str], None] = 'f89e6d492bb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_constraint(
        "content_document_course_id_fkey",
        "content_document",
        type_="foreignkey"
    )

    op.create_foreign_key(
        "content_document_course_id_fkey",
        "content_document",
        "course",
        ["course_id"],
        ["id"],
        ondelete="CASCADE"
    )
def downgrade() -> None:
    """Downgrade schema."""
    pass
