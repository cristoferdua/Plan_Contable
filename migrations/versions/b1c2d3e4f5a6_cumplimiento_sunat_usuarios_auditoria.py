"""cumplimiento SUNAT: usuarios, auditoria, config, campos PLE/registros

Revision ID: b1c2d3e4f5a6
Revises: 46f12026a5cb
Create Date: 2026-11-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "46f12026a5cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ASIENTO_COLS = [
    sa.Column("tipo_asiento", sa.String(1), nullable=False, server_default="M"),
    sa.Column("origen", sa.String(30), nullable=True),
    sa.Column("tipo_comprobante", sa.String(2), nullable=True),
    sa.Column("serie_comprobante", sa.String(20), nullable=True),
    sa.Column("numero_comprobante", sa.String(20), nullable=True),
    sa.Column("fecha_emision", sa.Date(), nullable=True),
    sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
    sa.Column("tipo_doc_tercero", sa.String(1), nullable=True),
    sa.Column("ref_tipo_comprobante", sa.String(2), nullable=True),
    sa.Column("ref_serie", sa.String(20), nullable=True),
    sa.Column("ref_numero", sa.String(20), nullable=True),
    sa.Column("ref_fecha", sa.Date(), nullable=True),
    sa.Column("detraccion_monto", sa.Numeric(15, 2), nullable=True),
    sa.Column("detraccion_constancia", sa.String(30), nullable=True),
    sa.Column("detraccion_fecha", sa.Date(), nullable=True),
    sa.Column("sujeto_retencion", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("percepcion_monto", sa.Numeric(15, 2), nullable=True),
    sa.Column("estado_ple", sa.String(1), nullable=False, server_default="1"),
    sa.Column("creado_por", sa.String(80), nullable=True),
    sa.Column("modificado_por", sa.String(80), nullable=True),
    sa.Column("modificado_at", sa.DateTime(), nullable=True),
]


def upgrade() -> None:
    with op.batch_alter_table("asiento") as b:
        for col in ASIENTO_COLS:
            b.add_column(col.copy())
    with op.batch_alter_table("asiento_linea") as b:
        b.add_column(sa.Column("importe_me", sa.Numeric(15, 2), nullable=True))

    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False, server_default="asistente"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ultimo_login", sa.DateTime(), nullable=True),
        sa.CheckConstraint("rol IN ('admin','contador','asistente','lectura')", name="ck_usuario_rol"),
    )
    op.create_table(
        "auditoria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fecha", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("usuario", sa.String(80), nullable=True),
        sa.Column("accion", sa.String(40), nullable=False),
        sa.Column("entidad", sa.String(40), nullable=False),
        sa.Column("entidad_id", sa.Integer(), nullable=True),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("antes", sa.Text(), nullable=True),
        sa.Column("despues", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
    )
    op.create_index("ix_auditoria_entidad", "auditoria", ["entidad", "entidad_id"])
    op.create_index("ix_auditoria_fecha", "auditoria", ["fecha"])
    op.create_table(
        "config",
        sa.Column("clave", sa.String(60), primary_key=True),
        sa.Column("valor", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("config")
    op.drop_index("ix_auditoria_fecha", table_name="auditoria")
    op.drop_index("ix_auditoria_entidad", table_name="auditoria")
    op.drop_table("auditoria")
    op.drop_table("usuario")
    with op.batch_alter_table("asiento_linea") as b:
        b.drop_column("importe_me")
    with op.batch_alter_table("asiento") as b:
        for col in reversed(ASIENTO_COLS):
            b.drop_column(col.name)
