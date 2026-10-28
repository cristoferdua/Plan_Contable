from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Date,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Asiento(Base):
    __tablename__ = "asiento"

    id = Column(Integer, primary_key=True)
    numero = Column(String(20), nullable=False, unique=True)
    fecha = Column(Date, nullable=False)
    glosa = Column(String(500), nullable=False, default="")
    moneda = Column(String(3), nullable=False, default="PEN")
    tipo_cambio = Column(Numeric(10, 4), nullable=False, default=Decimal("1"))
    codigo_libro = Column(String(10), nullable=True)
    numero_correlativo = Column(String(20), nullable=True)
    numero_documento = Column(String(30), nullable=True)
    reversa_de_id = Column(Integer, ForeignKey("asiento.id"), nullable=True)
    anulado_por_id = Column(Integer, ForeignKey("asiento.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    lineas = relationship(
        "AsientoLinea",
        back_populates="asiento",
        cascade="all, delete-orphan",
        order_by="AsientoLinea.orden",
    )

    __table_args__ = (
        Index("ix_asiento_fecha", "fecha"),
    )


class AsientoLinea(Base):
    __tablename__ = "asiento_linea"

    id = Column(Integer, primary_key=True)
    asiento_id = Column(Integer, ForeignKey("asiento.id", ondelete="CASCADE"), nullable=False)
    orden = Column(Integer, nullable=False)
    cuenta_codigo = Column(String(10), nullable=False)
    glosa_linea = Column(String(500), nullable=False, default="")
    debe = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    haber = Column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    es_titulo = Column(Boolean, nullable=False, default=False)

    asiento = relationship("Asiento", back_populates="lineas")

    __table_args__ = (
        CheckConstraint(
            "(es_titulo = TRUE AND debe = 0 AND haber = 0) OR (debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0)",
            name="ck_linea_debe_xor_haber",
        ),
        UniqueConstraint("asiento_id", "orden", name="uq_linea_asiento_orden"),
        Index("ix_linea_cuenta", "cuenta_codigo"),
    )
