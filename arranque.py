"""Preparacion de la base de datos al iniciar la aplicacion.

1. Respaldo automatico (solo SQLite): copia la base a respaldos/ y conserva las ultimas N.
2. Esquema al dia, sin comandos manuales:
   - SQLite nueva:            crea las tablas y la marca en la ultima migracion.
   - SQLite con migraciones:  aplica las migraciones pendientes.
   - PostgreSQL:              aplica las migraciones pendientes.

Variables de entorno opcionales:
   AUTO_MIGRAR=0       desactiva el paso 2 (por defecto activo).
   RESPALDOS_MAX=30    cuantos respaldos conservar (0 desactiva los respaldos).
"""
import glob
import logging
import os
import sqlite3
from datetime import datetime

from sqlalchemy import inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_RESPALDOS = os.path.join(BASE_DIR, "respaldos")
log = logging.getLogger("arranque")


def _ruta_sqlite(engine):
    db = engine.url.database
    if not db or db == ":memory:":
        return None
    return db if os.path.isabs(db) else os.path.abspath(db)


def respaldar_sqlite(engine):
    """Copia consistente de la base (API de backup de SQLite, segura aunque este en uso)."""
    maximo = int(os.environ.get("RESPALDOS_MAX", "30") or 0)
    ruta = _ruta_sqlite(engine)
    if maximo <= 0 or not ruta or not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        return None
    os.makedirs(DIR_RESPALDOS, exist_ok=True)
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    destino = os.path.join(DIR_RESPALDOS, f"{nombre}_{datetime.now():%Y%m%d_%H%M%S}.db")
    origen = sqlite3.connect(ruta)
    copia = sqlite3.connect(destino)
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    # Conservar solo los ultimos "maximo" respaldos de esta base.
    existentes = sorted(glob.glob(os.path.join(DIR_RESPALDOS, f"{nombre}_*.db")))
    for viejo in existentes[:-maximo]:
        try:
            os.remove(viejo)
        except OSError:
            pass
    return destino


def _alembic_config():
    from alembic.config import Config
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "migrations"))
    return cfg


def preparar_base_de_datos(engine, metadata):
    from alembic import command

    if engine.dialect.name == "sqlite":
        destino = respaldar_sqlite(engine)
        if destino:
            print(f" * Respaldo creado: {os.path.relpath(destino, BASE_DIR)}")

    if os.environ.get("AUTO_MIGRAR", "1").strip() == "0":
        if engine.dialect.name == "sqlite":
            metadata.create_all(engine)
        return

    cfg = _alembic_config()
    tablas = set(inspect(engine).get_table_names())

    if engine.dialect.name != "sqlite":
        command.upgrade(cfg, "head")
        return

    if "alembic_version" in tablas:
        command.upgrade(cfg, "head")
        metadata.create_all(engine)     # tablas nuevas sin migracion propia (no toca las existentes)
        return

    if "asiento" not in tablas:
        # Base nueva: crear todo desde los modelos y registrar la version actual.
        metadata.create_all(engine)
        command.stamp(cfg, "head")
        print(" * Base de datos nueva creada.")
        return

    # Base antigua sin control de versiones: crear lo que falte y avisar si hay columnas pendientes.
    metadata.create_all(engine)
    insp = inspect(engine)
    faltan = []
    for tabla in metadata.sorted_tables:
        cols = {c["name"] for c in insp.get_columns(tabla.name)}
        faltan += [f"{tabla.name}.{c.name}" for c in tabla.columns if c.name not in cols]
    if faltan:
        print(" ! La base no tiene control de versiones y le faltan columnas: " + ", ".join(faltan))
        print(" ! Restaura un respaldo reciente o pide ayuda al responsable tecnico.")
    else:
        command.stamp(cfg, "head")
