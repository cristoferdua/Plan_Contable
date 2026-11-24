import uuid
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
    Text,
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
    ruc_tercero = Column(String(11), nullable=True)
    razon_social_tercero = Column(String(300), nullable=True)
    reversa_de_id = Column(Integer, ForeignKey("asiento.id"), nullable=True)
    anulado_por_id = Column(Integer, ForeignKey("asiento.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ---- Campos SUNAT (PLE 5.1 / Registros) ----
    # Tipo de asiento para el correlativo PLE: A = apertura, M = movimiento, C = cierre
    tipo_asiento = Column(String(1), nullable=False, default="M")
    # Asientos generados por el sistema: 'destino', 'cierre_resultados', 'cierre_balance', 'apertura'
    origen = Column(String(30), nullable=True)
    tipo_comprobante = Column(String(2), nullable=True)      # Tabla 10
    serie_comprobante = Column(String(20), nullable=True)
    numero_comprobante = Column(String(20), nullable=True)
    fecha_emision = Column(Date, nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    tipo_doc_tercero = Column(String(1), nullable=True)      # Tabla 2
    # Comprobante que modifica (notas de credito / debito)
    ref_tipo_comprobante = Column(String(2), nullable=True)
    ref_serie = Column(String(20), nullable=True)
    ref_numero = Column(String(20), nullable=True)
    ref_fecha = Column(Date, nullable=True)
    # Detracciones / retenciones / percepciones
    detraccion_monto = Column(Numeric(15, 2), nullable=True)
    detraccion_constancia = Column(String(30), nullable=True)
    detraccion_fecha = Column(Date, nullable=True)
    sujeto_retencion = Column(Boolean, nullable=False, default=False)
    percepcion_monto = Column(Numeric(15, 2), nullable=True)
    # Estado PLE: 1 = del periodo, 8 = de periodo anterior no anotada, 9 = correccion
    estado_ple = Column(String(1), nullable=False, default="1")
    creado_por = Column(String(80), nullable=True)
    modificado_por = Column(String(80), nullable=True)
    modificado_at = Column(DateTime, nullable=True)
    # Agrupa los asientos de una misma operacion (provision + destino + cancelacion...).
    operacion_id = Column(String(36), nullable=True, default=lambda: str(uuid.uuid4()))

    lineas = relationship(
        "AsientoLinea",
        back_populates="asiento",
        cascade="all, delete-orphan",
        order_by="AsientoLinea.orden",
    )

    __table_args__ = (
        Index("ix_asiento_fecha", "fecha"),
        Index("ix_asiento_operacion_id", "operacion_id"),
    )


class Entidad(Base):
    __tablename__ = "entidad"

    id = Column(Integer, primary_key=True)
    ruc = Column(String(11), nullable=False, unique=True)
    razon_social = Column(String(300), nullable=False, default="")
    nombre_comercial = Column(String(300), nullable=True)
    estado = Column(String(40), nullable=True)
    condicion = Column(String(40), nullable=True)
    direccion = Column(String(300), nullable=True)
    distrito = Column(String(100), nullable=True)
    provincia = Column(String(100), nullable=True)
    departamento = Column(String(100), nullable=True)
    ubigeo = Column(String(10), nullable=True)
    tipo = Column(String(30), nullable=True)
    nota = Column(String(300), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_entidad_razon_social", "razon_social"),
    )


class CierreMes(Base):
    __tablename__ = "cierre_mes"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    cerrado_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    cerrado_por = Column(String(80), nullable=True)
    nota = Column(String(300), nullable=True)

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_cierre_year_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_cierre_month"),
    )


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False, default="")
    password_hash = Column(String(300), nullable=False)
    # admin: todo | contador: registra, cierra meses y ejercicio | asistente: registra | lectura: solo ver
    rol = Column(String(20), nullable=False, default="asistente")
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ultimo_login = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("rol IN ('admin','contador','asistente','lectura')", name="ck_usuario_rol"),
    )


class Auditoria(Base):
    """Bitacora inalterable: la app solo inserta, nunca actualiza ni borra."""
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    usuario = Column(String(80), nullable=True)
    accion = Column(String(40), nullable=False)
    entidad = Column(String(40), nullable=False)
    entidad_id = Column(Integer, nullable=True)
    motivo = Column(String(500), nullable=True)
    antes = Column(Text, nullable=True)     # JSON
    despues = Column(Text, nullable=True)   # JSON
    ip = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_auditoria_entidad", "entidad", "entidad_id"),
        Index("ix_auditoria_fecha", "fecha"),
    )


class Config(Base):
    """Configuracion de la empresa (clave/valor)."""
    __tablename__ = "config"

    clave = Column(String(60), primary_key=True)
    valor = Column(Text, nullable=True)


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
    # Importe en moneda extranjera (USD) cuando el asiento no es en PEN.
    importe_me = Column(Numeric(15, 2), nullable=True)

    asiento = relationship("Asiento", back_populates="lineas")

    __table_args__ = (
        CheckConstraint(
            "(es_titulo = TRUE AND debe = 0 AND haber = 0) OR (debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0)",
            name="ck_linea_debe_xor_haber",
        ),
        UniqueConstraint("asiento_id", "orden", name="uq_linea_asiento_orden"),
        Index("ix_linea_cuenta", "cuenta_codigo"),
    )
