"""Tablas SUNAT y generacion de archivos del Programa de Libros Electronicos (PLE).

Estructuras implementadas (verificar contra el anexo vigente de SUNAT antes de
presentar; SUNAT actualiza los formatos periodicamente):

  5.1  Libro Diario                                  -> LE...050100...
  5.3  Libro Diario - Detalle del Plan Contable      -> LE...050300...
  6.1  Libro Mayor                                   -> LE...060100...

Cada registro es una linea con los campos separados y terminados por "|".
"""
import re
from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------- Tablas

# Tabla 10 - Tipo de comprobante de pago o documento (los de uso frecuente)
TABLA_10 = {
    "00": "Otros",
    "01": "Factura",
    "02": "Recibo por honorarios",
    "03": "Boleta de venta",
    "04": "Liquidacion de compra",
    "05": "Boleto de transporte aereo",
    "07": "Nota de credito",
    "08": "Nota de debito",
    "12": "Ticket o cinta de maquina registradora",
    "14": "Recibo de servicios publicos",
    "50": "Declaracion Unica de Aduanas (DUA)",
    "91": "Comprobante de no domiciliado",
}

# Tabla 2 - Tipo de documento de identidad
TABLA_2 = {
    "0": "Doc. tributario no domiciliado sin RUC",
    "1": "DNI",
    "4": "Carnet de extranjeria",
    "6": "RUC",
    "7": "Pasaporte",
    "A": "Cedula diplomatica de identidad",
}

# Tabla 4 - Moneda (ISO 4217)
TABLA_4 = {"PEN": "Soles", "USD": "Dolares americanos"}

# Codigos de libro PLE (6 digitos)
LIBRO_DIARIO = "050100"
LIBRO_DIARIO_PLAN = "050300"
LIBRO_MAYOR = "060100"

ESTADOS_PLE = {
    "1": "Operacion del periodo",
    "8": "Operacion de un periodo anterior no anotada",
    "9": "Correccion de una operacion de un periodo anterior",
}


# ---------------------------------------------------------------- Helpers

def tipo_comprobante_desde_documento(numero_documento: str) -> str:
    """Deduce el tipo (Tabla 10) desde la serie SOLO como respaldo cuando el
    usuario no lo eligio. Las notas de credito/debito electronicas pueden usar
    series que empiezan con F o B, asi que el dato correcto es el que se elige
    en el formulario; esto es una aproximacion para datos antiguos.

    Se revisan primero los prefijos largos (FC/BC/FD/BD) y despues F/B; el
    orden inverso hacia que las notas nunca se detectaran.
    """
    if not numero_documento:
        return ""
    s = numero_documento.strip().upper()
    if s.startswith(("FC", "BC")) or s[:3].find("NC") >= 0:
        return "07"
    if s.startswith(("FD", "BD")) or s[:3].find("ND") >= 0:
        return "08"
    if s.startswith("E001"):
        return "02"  # recibo por honorarios electronico
    if s.startswith("F"):
        return "01"
    if s.startswith("B"):
        return "03"
    return "00"


def separar_serie_numero(numero_documento: str):
    """'F001-2559' -> ('F001', '2559'). Sin guion todo va a numero."""
    if not numero_documento:
        return ("", "")
    s = numero_documento.strip()
    if "-" in s:
        serie, num = s.split("-", 1)
        return (serie.strip().upper(), num.strip())
    return ("", s)


def tipo_doc_desde_numero(doc: str) -> str:
    """Tabla 2 a partir del numero: 11 digitos = RUC, 8 digitos = DNI."""
    if not doc:
        return ""
    if doc.isdigit() and len(doc) == 11:
        return "6"
    if doc.isdigit() and len(doc) == 8:
        return "1"
    return ""


def datos_comprobante(asiento):
    """Devuelve (tipo, serie, numero) del asiento usando los campos explicitos
    y, si faltan, deduciendolos del numero_documento."""
    serie_d, num_d = separar_serie_numero(asiento.numero_documento or "")
    tipo = asiento.tipo_comprobante or tipo_comprobante_desde_documento(asiento.numero_documento or "")
    serie = asiento.serie_comprobante or serie_d
    numero = asiento.numero_comprobante or num_d
    return tipo, serie, numero


_LIMPIA = re.compile(r"[|\r\n\t]+")


def _txt(valor, max_len=None):
    s = "" if valor is None else str(valor)
    s = _LIMPIA.sub(" ", s).strip()
    if max_len:
        s = s[:max_len]
    return s


def _fecha(d):
    return d.strftime("%d/%m/%Y") if d else ""


def _monto(d):
    return f"{Decimal(d or 0):.2f}"


def periodo_ple(year: int, month: int) -> str:
    return f"{year:04d}{month:02d}00"


def nombre_archivo(ruc: str, year: int, month: int, libro: str, con_info: bool, moneda: str = "PEN") -> str:
    """LE + RUC + AAAAMM00 + libro(6) + oportunidad(2) + O + I + M + G .txt

    O: indicador de operaciones (1 = empresa con operaciones)
    I: indicador de contenido   (1 = con informacion, 0 = sin informacion)
    M: moneda                   (1 = soles, 2 = dolares)
    G: generado por PLE         (1)
    """
    ruc = (ruc or "").strip() or "00000000000"
    i = "1" if con_info else "0"
    m = "2" if moneda == "USD" else "1"
    return f"LE{ruc}{year:04d}{month:02d}00{libro}001{i}{m}1.txt"


# ---------------------------------------------------------------- Formatos

def _campos_linea_diario(asiento, linea, correlativo, year, month):
    """21 campos comunes a los formatos 5.1 y 6.1."""
    tipo, serie, numero = datos_comprobante(asiento)
    tipo_doc = asiento.tipo_doc_tercero or tipo_doc_desde_numero(asiento.ruc_tercero or "")
    glosa = linea.glosa_linea or asiento.glosa or "Asiento " + (asiento.numero or "")
    return [
        periodo_ple(year, month),                       # 1  Periodo
        _txt(asiento.numero, 40),                       # 2  CUO
        correlativo,                                    # 3  Correlativo (A/M/C + n)
        _txt(linea.cuenta_codigo, 24),                  # 4  Cuenta contable
        "",                                             # 5  Unidad de operacion
        "",                                             # 6  Centro de costos
        _txt(asiento.moneda or "PEN", 3),               # 7  Moneda (Tabla 4)
        _txt(tipo_doc, 1),                              # 8  Tipo doc identidad emisor (Tabla 2)
        _txt(asiento.ruc_tercero, 15),                  # 9  Numero doc identidad emisor
        _txt(tipo or "00", 2),                          # 10 Tipo comprobante (Tabla 10)
        _txt(serie, 20),                                # 11 Serie
        _txt(numero or asiento.numero, 20),             # 12 Numero comprobante
        _fecha(asiento.fecha),                          # 13 Fecha contable
        _fecha(asiento.fecha_vencimiento),              # 14 Fecha de vencimiento
        _fecha(asiento.fecha_emision or asiento.fecha), # 15 Fecha de la operacion o emision
        _txt(glosa, 200),                               # 16 Glosa
        "",                                             # 17 Glosa referencial
        _monto(linea.debe),                             # 18 Debe
        _monto(linea.haber),                            # 19 Haber
        "",                                             # 20 Dato estructurado
        _txt(asiento.estado_ple or "1", 1),             # 21 Estado de la operacion
    ]


def _linea(campos):
    return "|".join(campos) + "|"


def generar_5_1(asientos, year, month):
    """Libro Diario formato 5.1. `asientos` ordenados por fecha/id."""
    filas = []
    for a in asientos:
        n = 0
        for l in a.lineas:
            if l.es_titulo:
                continue
            n += 1
            correlativo = f"{(a.tipo_asiento or 'M')}{n:09d}"
            filas.append(_linea(_campos_linea_diario(a, l, correlativo, year, month)))
    return filas


def generar_6_1(asientos, year, month):
    """Libro Mayor formato 6.1: mismos campos, ordenado por cuenta."""
    items = []
    for a in asientos:
        n = 0
        for l in a.lineas:
            if l.es_titulo:
                continue
            n += 1
            correlativo = f"{(a.tipo_asiento or 'M')}{n:09d}"
            items.append((l.cuenta_codigo, a.fecha, a.id, n, a, l, correlativo))
    items.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return [_linea(_campos_linea_diario(a, l, c, year, month)) for *_, a, l, c in items]


def generar_5_3(cuentas_usadas, cuentas_por_codigo, year, month):
    """Detalle del plan contable utilizado (codigo 01 = PCGE en Tabla 17)."""
    filas = []
    for cod in sorted(cuentas_usadas):
        desc = (cuentas_por_codigo.get(cod) or {}).get("descripcion", "")
        filas.append(_linea([
            periodo_ple(year, month),   # 1 Periodo
            _txt(cod, 24),              # 2 Codigo de cuenta
            _txt(desc, 100),            # 3 Descripcion
            "01",                       # 4 Codigo del plan de cuentas (Tabla 17: PCGE)
            "",                         # 5 Descripcion del plan (solo si codigo 99)
            "",                         # 6 Codigo cuenta corporativa
            "",                         # 7 Descripcion cuenta corporativa
            "1",                        # 8 Estado
        ]))
    return filas


def contenido_archivo(filas):
    """Texto final: lineas con CRLF, codificado como lo espera el PLE."""
    if not filas:
        return b""
    return ("\r\n".join(filas) + "\r\n").encode("utf-8")
