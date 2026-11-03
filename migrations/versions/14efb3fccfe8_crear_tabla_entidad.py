"""crear tabla entidad

Revision ID: 14efb3fccfe8
Revises: a6cf4d87d4ec
Create Date: 2026-11-02 23:07:10.932216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14efb3fccfe8'
down_revision: Union[str, None] = 'a6cf4d87d4ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entidad",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ruc", sa.String(length=11), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("nombre_comercial", sa.String(length=300), nullable=True),
        sa.Column("estado", sa.String(length=40), nullable=True),
        sa.Column("condicion", sa.String(length=40), nullable=True),
        sa.Column("direccion", sa.String(length=300), nullable=True),
        sa.Column("distrito", sa.String(length=100), nullable=True),
        sa.Column("provincia", sa.String(length=100), nullable=True),
        sa.Column("departamento", sa.String(length=100), nullable=True),
        sa.Column("ubigeo", sa.String(length=10), nullable=True),
        sa.Column("tipo", sa.String(length=30), nullable=True),
        sa.Column("nota", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_entidad_razon_social", "entidad", ["razon_social"])


def downgrade() -> None:
    op.drop_index("ix_entidad_razon_social", table_name="entidad")
    op.drop_table("entidad")
