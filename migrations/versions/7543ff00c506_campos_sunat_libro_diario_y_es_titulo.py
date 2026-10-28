"""campos sunat libro diario y es_titulo

Revision ID: 7543ff00c506
Revises: ea9387279af4
Create Date: 2026-10-28 16:21:35.806195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7543ff00c506'
down_revision: Union[str, None] = 'ea9387279af4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('asiento', sa.Column('codigo_libro', sa.String(length=10), nullable=True))
    op.add_column('asiento', sa.Column('numero_correlativo', sa.String(length=20), nullable=True))
    op.add_column('asiento', sa.Column('numero_documento', sa.String(length=30), nullable=True))
    op.add_column(
        'asiento_linea',
        sa.Column('es_titulo', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.alter_column('asiento_linea', 'es_titulo', server_default=None)

    op.drop_constraint('ck_linea_debe_xor_haber', 'asiento_linea', type_='check')
    op.create_check_constraint(
        'ck_linea_debe_xor_haber',
        'asiento_linea',
        '(es_titulo = TRUE AND debe = 0 AND haber = 0) OR (debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0)',
    )


def downgrade() -> None:
    op.drop_constraint('ck_linea_debe_xor_haber', 'asiento_linea', type_='check')
    op.create_check_constraint(
        'ck_linea_debe_xor_haber',
        'asiento_linea',
        '(debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0)',
    )
    op.drop_column('asiento_linea', 'es_titulo')
    op.drop_column('asiento', 'numero_documento')
    op.drop_column('asiento', 'numero_correlativo')
    op.drop_column('asiento', 'codigo_libro')
