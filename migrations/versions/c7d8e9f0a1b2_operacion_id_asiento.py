"""operacion_id en asiento: agrupa los asientos de una misma operacion

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-11-24
"""
import re
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill(conn):
    """Asigna operacion_id a los asientos existentes.

    Recorre por id y agrupa asientos consecutivos de la misma fecha + documento
    (o correlativo base). Un asiento cuya glosa empieza con "1)" abre una
    operacion nueva aunque coincida el documento: asi dos compras registradas
    con el mismo comprobante dejan de mezclarse.
    """
    rows = conn.execute(sa.text(
        "SELECT id, fecha, glosa, numero_correlativo, numero_documento "
        "FROM asiento WHERE operacion_id IS NULL ORDER BY id"
    )).fetchall()
    abiertas = {}  # clave -> operacion_id vigente
    for id_, fecha, glosa, corr, doc in rows:
        glosa = (glosa or "").strip()
        corr = (corr or "").strip()
        doc = (doc or "").strip()
        m = re.match(r"^(\d{4}-\d{2}-\d+)-\d+$", corr)
        if m:
            clave = ("corr", str(fecha), m.group(1))
        elif doc:
            clave = ("doc", str(fecha), doc)
        else:
            base = re.sub(r"^\d+\)\s*[A-Za-z]+\s*(parcial\s*)?-\s*", "", glosa)
            base = re.sub(r"\s*\[MIXTO:[^\]]*\]\s*$", "", base)
            clave = ("glosa", str(fecha), base or f"solo-{id_}")
        if re.match(r"^1\)", glosa) or clave not in abiertas:
            abiertas[clave] = str(uuid.uuid4())
        conn.execute(sa.text("UPDATE asiento SET operacion_id = :o WHERE id = :i"),
                     {"o": abiertas[clave], "i": id_})


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("asiento")}
    if "operacion_id" not in cols:
        with op.batch_alter_table("asiento") as b:
            b.add_column(sa.Column("operacion_id", sa.String(36), nullable=True))
    idx = {i["name"] for i in insp.get_indexes("asiento")}
    if "ix_asiento_operacion_id" not in idx:
        op.create_index("ix_asiento_operacion_id", "asiento", ["operacion_id"])
    _backfill(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_asiento_operacion_id", table_name="asiento")
    with op.batch_alter_table("asiento") as b:
        b.drop_column("operacion_id")
