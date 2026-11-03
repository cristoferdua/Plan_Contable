"""agregar ruc tercero a asiento

Revision ID: 46f12026a5cb
Revises: 14efb3fccfe8
Create Date: 2026-11-02 23:28:41.930064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46f12026a5cb'
down_revision: Union[str, None] = '14efb3fccfe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asiento", sa.Column("ruc_tercero", sa.String(length=11), nullable=True))
    op.add_column("asiento", sa.Column("razon_social_tercero", sa.String(length=300), nullable=True))
    op.create_index("ix_asiento_ruc_tercero", "asiento", ["ruc_tercero"])


def downgrade() -> None:
    op.drop_index("ix_asiento_ruc_tercero", table_name="asiento")
    op.drop_column("asiento", "razon_social_tercero")
    op.drop_column("asiento", "ruc_tercero")
