"""add expected_correct_answers to quiz_attempt

Revision ID: c7e3f819a4d2
Revises: 5fb52686cd0a
Create Date: 2026-09-13 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e3f819a4d2'
down_revision: Union[str, Sequence[str], None] = '5fb52686cd0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('quiz_attempt', sa.Column('expected_correct_answers', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quiz_attempt', 'expected_correct_answers')
