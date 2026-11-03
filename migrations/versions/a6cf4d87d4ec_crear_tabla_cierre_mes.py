"""crear tabla cierre_mes

Revision ID: a6cf4d87d4ec
Revises: 7543ff00c506
Create Date: 2026-11-02 22:27:49.792032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6cf4d87d4ec'
down_revision: Union[str, None] = '7543ff00c506'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cierre_mes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("cerrado_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("cerrado_por", sa.String(length=80), nullable=True),
        sa.Column("nota", sa.String(length=300), nullable=True),
        sa.UniqueConstraint("year", "month", name="uq_cierre_year_month"),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_cierre_month"),
    )


def downgrade() -> None:
    op.drop_table("cierre_mes")
