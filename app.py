import io
import json
import os
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, redirect, render_template, request, send_file, url_for
from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import SessionLocal
from models import Asiento, AsientoLinea, CierreMes, Entidad

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "pcge_data.json")

app = Flask(__name__)

ELEMENTOS = [
    (1, "Activo Disponible y Exigible"),
    (2, "Activo Realizable"),
    (3, "Activo Inmovilizado"),
    (4, "Pasivo"),
    (5, "Patrimonio"),
    (6, "Gastos por Naturaleza"),
    (7, "Ingresos por Naturaleza"),
    (8, "Saldos Intermediarios de Gestion"),
    (9, "Gastos por Categoria"),
]

FUZZY_THRESHOLD = 65
LIMIT = 3000
TOLERANCIA = Decimal("0.01")
NIVELES_MOVIMIENTO = {4, 5}

SINONIMOS = {
    # ===== VEHICULOS =====
    "carro": "vehiculos motorizados",
    "carros": "vehiculos motorizados",
    "auto": "vehiculos motorizados",
    "autos": "vehiculos motorizados",
    "automovil": "vehiculos motorizados",
    "automoviles": "vehiculos motorizados",
    "camion": "vehiculos motorizados",
    "camiones": "vehiculos motorizados",
    "camioneta": "vehiculos motorizados",
    "camionetas": "vehiculos motorizados",
    "moto": "vehiculos motorizados",
    "motos": "vehiculos motorizados",
    "motocicleta": "vehiculos motorizados",
    "vehiculo": "vehiculos motorizados",
    "transporte vehicular": "vehiculos motorizados",

    # ===== EFECTIVO Y CAJA =====
    "plata": "efectivo",
    "dinero": "efectivo",
    "cash": "efectivo",
    "efectivo caja": "caja",
    "caja chica": "fondos fijos",
    "cheque": "cheques en transito",
    "cheques": "cheques en transito",
    "deposito": "depositos en instituciones financieras",
    "depositos": "depositos en instituciones financieras",
    "ahorro": "depositos de ahorro",
    "ahorros": "depositos de ahorro",
    "plazo fijo": "depositos a plazo",

    # ===== BANCOS =====
    "banco": "cuentas corrientes en instituciones financieras",
    "bancos": "cuentas corrientes en instituciones financieras",
    "cuenta corriente": "cuentas corrientes operativas",
    "transferencia": "cuentas corrientes operativas",
    "transferencias": "cuentas corrientes operativas",
    "bcp": "cuentas corrientes operativas",
    "bbva": "cuentas corrientes operativas",
    "scotiabank": "cuentas corrientes operativas",
    "interbank": "cuentas corrientes operativas",

    # ===== CLIENTES / COBRAR =====
    "cliente": "cuentas por cobrar comerciales",
    "clientes": "cuentas por cobrar comerciales",
    "cobrar": "cuentas por cobrar comerciales",
    "por cobrar": "cuentas por cobrar comerciales",
    "deudor": "cuentas por cobrar comerciales",
    "deudores": "cuentas por cobrar comerciales",
    "letra": "letras por cobrar",
    "letras": "letras por cobrar",
    "factura por cobrar": "facturas por cobrar",
    "facturas por cobrar": "facturas por cobrar",
    "boleta por cobrar": "boletas por cobrar",

    # ===== PROVEEDORES / PAGAR =====
    "proveedor": "cuentas por pagar comerciales",
    "proveedores": "cuentas por pagar comerciales",
    "pagar": "cuentas por pagar comerciales",
    "por pagar": "cuentas por pagar comerciales",
    "acreedor": "cuentas por pagar diversas",
    "acreedores": "cuentas por pagar diversas",
    "factura por pagar": "facturas por pagar",
    "facturas por pagar": "facturas por pagar",

    # ===== EXISTENCIAS / INVENTARIO =====
    "mercaderia": "mercaderias",
    "mercaderias": "mercaderias",
    "inventario": "mercaderias",
    "inventarios": "mercaderias",
    "stock": "mercaderias",
    "producto": "productos terminados",
    "productos": "productos terminados",
    "materia prima": "materias primas",
    "materias primas": "materias primas",
    "insumo": "materiales auxiliares",
    "insumos": "materiales auxiliares",
    "envase": "envases",
    "embalaje": "embalajes",

    # ===== ACTIVO FIJO =====
    "laptop": "equipo para procesamiento de informacion",
    "laptops": "equipo para procesamiento de informacion",
    "computadora": "equipo para procesamiento de informacion",
    "computadoras": "equipo para procesamiento de informacion",
    "pc": "equipo para procesamiento de informacion",
    "cpu": "equipo para procesamiento de informacion",
    "monitor": "equipo para procesamiento de informacion",
    "impresora": "equipo para procesamiento de informacion",
    "software": "programas de computadora",
    "programa": "programas de computadora",
    "licencia": "programas de computadora",
    "licencias": "programas de computadora",
    "mueble": "muebles",
    "muebles": "muebles",
    "escritorio": "muebles",
    "silla": "muebles",
    "sillas": "muebles",
    "estante": "muebles",
    "estantes": "muebles",
    "maquinaria": "maquinarias y equipos de explotacion",
    "maquina": "maquinarias y equipos de explotacion",
    "equipo": "equipos diversos",
    "equipos": "equipos diversos",
    "herramienta": "unidades de reemplazo",
    "herramientas": "unidades de reemplazo",
    "terreno": "terrenos",
    "terrenos": "terrenos",
    "lote": "terrenos",
    "edificio": "edificaciones",
    "edificios": "edificaciones",
    "local": "edificaciones",
    "oficina": "edificaciones",
    "almacen": "edificaciones",
    "deposito local": "edificaciones",
    "casa": "edificaciones",

    # ===== TRIBUTOS =====
    "iva": "impuesto general a las ventas",
    "igv": "impuesto general a las ventas",
    "renta": "impuesto a las ganancias",
    "impuesto a la renta": "impuesto a las ganancias",
    "ir": "impuesto a las ganancias",
    "sunat": "tributos contraprestaciones y aportes al sistema publico",
    "essalud": "essalud",
    "snp": "sistema nacional de pensiones",
    "onp": "sistema nacional de pensiones",
    "arbitrios": "gobiernos locales",
    "predial": "gobiernos locales",
    "detraccion": "fondos sujetos a restriccion",
    "detracciones": "fondos sujetos a restriccion",
    "retencion": "fondos sujetos a restriccion",
    "retenciones": "fondos sujetos a restriccion",
    "percepcion": "fondos sujetos a restriccion",

    # ===== PLANILLA / REMUNERACIONES =====
    "planilla": "remuneraciones y participaciones por pagar",
    "sueldo": "remuneraciones",
    "sueldos": "remuneraciones",
    "salario": "remuneraciones",
    "salarios": "remuneraciones",
    "trabajador": "remuneraciones por pagar",
    "trabajadores": "remuneraciones por pagar",
    "empleado": "remuneraciones por pagar",
    "empleados": "remuneraciones por pagar",
    "afp": "administradoras de fondos de pensiones",
    "pension": "administradoras de fondos de pensiones",
    "pensiones": "administradoras de fondos de pensiones",
    "jubilacion": "pensiones y jubilaciones",
    "cts": "compensacion por tiempo de servicios",
    "gratificacion": "gratificaciones por pagar",
    "gratificaciones": "gratificaciones por pagar",
    "vacaciones": "vacaciones por pagar",
    "bono": "otras remuneraciones",
    "bonos": "otras remuneraciones",
    "comision": "comisiones",
    "comisiones": "comisiones",
    "directorio": "dietas del directorio",
    "dieta": "dietas del directorio",

    # ===== SERVICIOS BASICOS =====
    "luz": "energia electrica",
    "electricidad": "energia electrica",
    "energia": "energia electrica",
    "recibo luz": "energia electrica",
    "agua": "agua",
    "recibo agua": "agua",
    "sedapal": "agua",
    "telefono": "telefono",
    "celular": "telefono",
    "movil": "telefono",
    "fijo": "telefono",
    "linea telefonica": "telefono",
    "internet": "internet",
    "wifi": "internet",
    "cable": "internet",
    "tv cable": "internet",
    "correo": "correos",
    "mensajeria": "correos",

    # ===== TRANSPORTE / FLETES =====
    "gasolina": "combustibles",
    "petroleo": "combustibles",
    "diesel": "combustibles",
    "gnv": "combustibles",
    "glp": "combustibles",
    "combustible": "combustibles",
    "flete": "transporte",
    "fletes": "transporte",
    "envio": "transporte",
    "envios": "transporte",
    "delivery": "transporte",
    "courier": "transporte",
    "pasaje": "transporte",
    "pasajes": "transporte",
    "taxi": "transporte",
    "uber": "transporte",
    "peaje": "transporte",
    "estacionamiento": "transporte",
    "parking": "transporte",

    # ===== ALQUILER =====
    "alquiler": "alquileres",
    "alquileres": "alquileres",
    "arriendo": "alquileres",
    "renta local": "alquileres",
    "merced conductiva": "alquileres",

    # ===== PUBLICIDAD / MARKETING =====
    "publicidad": "publicidad publicaciones relaciones publicas",
    "marketing": "publicidad publicaciones relaciones publicas",
    "anuncio": "publicidad publicaciones relaciones publicas",
    "anuncios": "publicidad publicaciones relaciones publicas",
    "promocion": "publicidad publicaciones relaciones publicas",

    # ===== SERVICIOS PROFESIONALES =====
    "honorario": "honorarios de directores",
    "honorarios": "honorarios de directores",
    "recibo honorarios": "honorarios de directores",
    "rh": "honorarios de directores",
    "contador": "asesoria y consultoria",
    "abogado": "asesoria y consultoria",
    "asesor": "asesoria y consultoria",
    "consultor": "asesoria y consultoria",
    "asesoria": "asesoria y consultoria",
    "consultoria": "asesoria y consultoria",
    "mantenimiento": "mantenimiento y reparaciones",
    "reparacion": "mantenimiento y reparaciones",
    "reparaciones": "mantenimiento y reparaciones",
    "limpieza": "servicios basicos",
    "vigilancia": "servicios basicos",
    "seguridad": "servicios basicos",
    "guardiania": "servicios basicos",

    # ===== GASTOS DIVERSOS =====
    "utiles": "suministros",
    "oficina utiles": "suministros",
    "papeleria": "suministros",
    "capacitacion": "capacitacion",
    "curso": "capacitacion",
    "cursos": "capacitacion",
    "seguro": "seguros",
    "seguros": "seguros",
    "poliza": "seguros",
    "polizas": "seguros",
    "donacion": "otros gastos de gestion",
    "donaciones": "otros gastos de gestion",
    "multa": "sanciones administrativas",
    "multas": "sanciones administrativas",
    "sancion": "sanciones administrativas",

    # ===== VENTAS / INGRESOS =====
    "venta": "mercaderias",
    "ventas": "mercaderias",
    "ingreso": "ingresos",
    "ingresos": "ingresos",
    "factura": "mercaderias",
    "facturas": "mercaderias",
    "boleta": "mercaderias",
    "boletas": "mercaderias",
    "nota credito": "descuentos rebajas y bonificaciones concedidos",
    "nota de credito": "descuentos rebajas y bonificaciones concedidos",
    "nc": "descuentos rebajas y bonificaciones concedidos",
    "devolucion": "descuentos rebajas y bonificaciones concedidos",
    "devoluciones": "descuentos rebajas y bonificaciones concedidos",
    "exportacion": "venta de exportacion",
    "exportaciones": "venta de exportacion",

    # ===== CAPITAL / PATRIMONIO =====
    "capital": "capital social",
    "aporte": "capital social",
    "aportes": "capital social",
    "socio": "accionistas",
    "socios": "accionistas",
    "accionista": "accionistas",
    "accionistas": "accionistas",
    "duenos": "accionistas",
    "utilidad": "resultados acumulados",
    "utilidades": "resultados acumulados",
    "perdida": "resultados acumulados",
    "perdidas": "resultados acumulados",
    "dividendo": "dividendos por pagar",
    "dividendos": "dividendos por pagar",
    "reserva": "reservas",
    "reservas": "reservas",
    "excedente": "excedente de revaluacion",

    # ===== OBLIGACIONES / DEUDAS =====
    "deuda": "obligaciones financieras",
    "deudas": "obligaciones financieras",
    "prestamo": "prestamos de instituciones financieras",
    "prestamos": "prestamos de instituciones financieras",
    "credito bancario": "prestamos de instituciones financieras",
    "sobregiro": "sobregiros bancarios",
    "leasing": "contratos de arrendamiento financiero",
    "arrendamiento financiero": "contratos de arrendamiento financiero",
    "hipoteca": "obligaciones financieras",
    "bono emision": "bonos emitidos",
    "pagare": "obligaciones emitidas",

    # ===== INTERESES / FINANCIEROS =====
    "interes": "intereses",
    "intereses": "intereses",
    "cambio": "diferencia de cambio",
    "diferencia cambio": "diferencia de cambio",
    "ganancia cambio": "ganancia por diferencia de cambio",
    "perdida cambio": "perdida por diferencia de cambio",

    # ===== DEPRECIACION =====
    "depreciacion": "depreciacion",
    "amortizacion": "amortizacion",
    "desvalorizacion": "desvalorizacion",

    # ===== OTROS =====
    "garantia": "fondos en garantia",
    "fianza": "fondos en garantia",
    "adelanto": "anticipos",
    "adelantos": "anticipos",
    "anticipo": "anticipos",
    "anticipos": "anticipos",
    "deposito garantia": "depositos otorgados en garantia",
    "regalia": "regalias",
    "regalias": "regalias",
    "patente": "patentes",
    "marca": "marcas",
    "franquicia": "franquicias",
}


def normalizar(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()


with open(DATA_FILE, encoding="utf-8") as f:
    CUENTAS = json.load(f)
for c in CUENTAS:
    c["_norm"] = normalizar(c["descripcion"])
CUENTAS.sort(key=lambda c: c["codigo"])
CUENTAS_POR_CODIGO = {c["codigo"]: c for c in CUENTAS}


def buscar_cuentas(q, elemento, niveles=None):
    base = CUENTAS
    if elemento:
        base = [c for c in base if str(c["elemento"]) == elemento]
    if niveles:
        base = [c for c in base if c["nivel"] in niveles]

    if not q:
        return base[:LIMIT]

    qn = normalizar(q)
    terminos = [qn]
    if qn in SINONIMOS:
        terminos.append(normalizar(SINONIMOS[qn]))
    # Tambien buscar sinonimos por palabra individual (ej: "compra de carro" -> agrega "vehiculos motorizados")
    palabras = qn.split()
    for p in palabras:
        if p in SINONIMOS and p != qn:
            terminos.append(normalizar(SINONIMOS[p]))
    # Eliminar duplicados preservando orden
    seen = set()
    terminos = [t for t in terminos if not (t in seen or seen.add(t))]

    # Rankear por calidad de match:
    # 0: codigo exacto
    # 1: codigo empieza con la query (ej "94" -> "94", "941", "9411")
    # 2: descripcion empieza con query
    # 3: codigo contiene query
    # 4: descripcion contiene query
    def rank(c):
        cod = c["codigo"]
        desc = c["_norm"]
        for t in terminos:
            if cod == t:
                return (0, c["nivel"], len(cod))
            if cod.startswith(t):
                return (1, c["nivel"], len(cod))
            if desc.startswith(t):
                return (2, c["nivel"], len(desc))
            if t in cod:
                return (3, c["nivel"], len(cod))
            if t in desc:
                return (4, c["nivel"], len(desc))
        return None

    puntuados = []
    vistos = set()
    for c in base:
        if c["codigo"] in vistos:
            continue
        r = rank(c)
        if r is not None:
            puntuados.append((r, c))
            vistos.add(c["codigo"])

    puntuados.sort(key=lambda x: x[0])
    exactos = [c for _, c in puntuados]

    if exactos or len(qn) < 3:
        return exactos[:LIMIT]

    difusos = sorted(
        ((fuzz.partial_ratio(qn, c["_norm"]), c) for c in base),
        key=lambda x: -x[0],
    )
    return [c for score, c in difusos if score >= FUZZY_THRESHOLD][:LIMIT]


def to_json(c, favoritas=None):
    out = {
        "codigo": c["codigo"],
        "descripcion": c["descripcion"],
        "nivel": c["nivel"],
        "elemento": c["elemento"],
        "elemento_nombre": c["elemento_nombre"],
    }
    if favoritas is not None:
        out["es_favorita"] = c["codigo"] in favoritas
    return out


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    elemento = request.args.get("elemento", "").strip()
    resultados = buscar_cuentas(q, elemento)

    # Agrupar por elemento para la vista acordeon
    grupos = {}
    for c in resultados:
        e = c["elemento"]
        if e not in grupos:
            grupos[e] = {"numero": e, "nombre": c["elemento_nombre"], "cuentas": []}
        grupos[e]["cuentas"].append(c)
    grupos_lista = [grupos[k] for k in sorted(grupos.keys())]

    return render_template(
        "index.html",
        resultados=resultados,
        grupos=grupos_lista,
        elementos=ELEMENTOS,
        q=q,
        elemento_sel=elemento,
        total=len(resultados),
        buscando=(bool(q) or bool(elemento)),
    )


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip()
    elemento = request.args.get("elemento", "").strip()
    solo_mov = request.args.get("solo_movimiento", "").strip() == "1"
    niveles_raw = request.args.get("niveles", "").strip()
    niveles = None
    if niveles_raw:
        try:
            niveles = {int(n) for n in niveles_raw.split(",") if n.strip()}
        except ValueError:
            abort(400, "Parametro niveles invalido.")
        if not niveles:
            niveles = None
    resultados = buscar_cuentas(q, elemento, niveles)
    if solo_mov and not niveles:
        resultados = [c for c in resultados if c["nivel"] in NIVELES_MOVIMIENTO]

    # Priorizar cuentas favoritas al inicio (si hay)
    try:
        with open(os.path.join(BASE_DIR, "favoritas.json"), encoding="utf-8") as f:
            favs = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        favs = set()
    if favs:
        favs_match = [c for c in resultados if c["codigo"] in favs]
        resto = [c for c in resultados if c["codigo"] not in favs]
        resultados = favs_match + resto

    return {
        "total": len(resultados),
        "resultados": [to_json(c, favoritas=favs) for c in resultados],
    }


def _mes_cerrado(session: Session, fecha: date) -> bool:
    row = session.execute(
        select(CierreMes).where(CierreMes.year == fecha.year, CierreMes.month == fecha.month)
    ).scalar_one_or_none()
    return row is not None


def _meses_cerrados_set(session: Session):
    rows = session.execute(select(CierreMes.year, CierreMes.month)).all()
    return {(y, m) for (y, m) in rows}


def _generar_numero(session: Session, fecha: date) -> str:
    prefijo = f"{fecha.year:04d}-{fecha.month:02d}-"
    stmt = select(Asiento.numero).where(Asiento.numero.like(prefijo + "%"))
    numeros = session.execute(stmt).scalars().all()
    max_sufijo = 0
    for n in numeros:
        try:
            v = int(n.split("-")[-1])
            if v > max_sufijo:
                max_sufijo = v
        except (ValueError, IndexError):
            continue
    siguiente = max_sufijo + 1
    return f"{prefijo}{siguiente:04d}"


def _parse_decimal(val) -> Decimal:
    if val is None or val == "":
        return Decimal("0")
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Valor numerico invalido: {val!r}")


def _validar_y_construir_lineas(data_lineas):
    errores = []
    lineas = []

    total_debe = Decimal("0")
    total_haber = Decimal("0")
    lineas_movimiento = 0
    for i, raw in enumerate(data_lineas, start=1):
        codigo = (raw.get("cuenta_codigo") or "").strip()
        glosa_linea = (raw.get("glosa_linea") or "").strip()
        try:
            debe = _parse_decimal(raw.get("debe"))
            haber = _parse_decimal(raw.get("haber"))
        except ValueError as e:
            errores.append(f"Linea {i}: {e}")
            continue

        if not codigo:
            errores.append(f"Linea {i}: falta cuenta.")
            continue
        cuenta = CUENTAS_POR_CODIGO.get(codigo)
        if not cuenta:
            errores.append(f"Linea {i}: cuenta {codigo} no existe en PCGE.")
            continue

        es_movimiento = cuenta["nivel"] in NIVELES_MOVIMIENTO
        tiene_monto = debe > 0 or haber > 0

        if not es_movimiento:
            if tiene_monto:
                errores.append(f"Linea {i}: cuenta {codigo} (nivel {cuenta['nivel']}) es titulo jerarquico y no puede tener monto.")
                continue
            lineas.append({
                "orden": i,
                "cuenta_codigo": codigo,
                "glosa_linea": glosa_linea,
                "debe": Decimal("0"),
                "haber": Decimal("0"),
                "es_titulo": True,
            })
            continue

        if not tiene_monto:
            errores.append(f"Linea {i}: cuenta {codigo} (nivel {cuenta['nivel']}) requiere monto en debe o haber.")
            continue
        if debe > 0 and haber > 0:
            errores.append(f"Linea {i}: no puede tener debe y haber a la vez.")
            continue
        if debe < 0 or haber < 0:
            errores.append(f"Linea {i}: montos no pueden ser negativos.")
            continue

        total_debe += debe
        total_haber += haber
        lineas_movimiento += 1
        lineas.append({
            "orden": i,
            "cuenta_codigo": codigo,
            "glosa_linea": glosa_linea,
            "debe": debe,
            "haber": haber,
            "es_titulo": False,
        })

    if lineas_movimiento < 2:
        errores.append("El asiento debe tener al menos 2 lineas de movimiento (nivel 4 o 5).")
    if not errores and abs(total_debe - total_haber) > TOLERANCIA:
        errores.append(f"El asiento no cuadra: debe={total_debe} haber={total_haber} diferencia={total_debe - total_haber}.")

    return lineas, errores


@app.route("/asientos")
def asientos_listado():
    year_f = request.args.get("year", type=int)
    month_f = request.args.get("month", type=int)
    desde_f = request.args.get("desde", "").strip()
    hasta_f = request.args.get("hasta", "").strip()
    ruc_f = request.args.get("ruc", "").strip()
    filtro_info = None
    with SessionLocal() as session:
        stmt = select(Asiento).order_by(Asiento.fecha.desc(), Asiento.id.desc())
        if ruc_f:
            stmt = stmt.where(Asiento.ruc_tercero == ruc_f)
            filtro_info = {"tipo": "ruc", "label": f"RUC {ruc_f}", "ruc": ruc_f}
        if year_f and month_f:
            from calendar import monthrange
            desde_d = date(year_f, month_f, 1)
            hasta_d = date(year_f, month_f, monthrange(year_f, month_f)[1])
            stmt = stmt.where(Asiento.fecha >= desde_d, Asiento.fecha <= hasta_d)
            filtro_info = {"tipo": "mes", "label": f"{year_f}-{month_f:02d}", "year": year_f, "month": month_f}
        else:
            if desde_f:
                try:
                    stmt = stmt.where(Asiento.fecha >= datetime.strptime(desde_f, "%Y-%m-%d").date())
                except ValueError:
                    pass
            if hasta_f:
                try:
                    stmt = stmt.where(Asiento.fecha <= datetime.strptime(hasta_f, "%Y-%m-%d").date())
                except ValueError:
                    pass
            if desde_f or hasta_f:
                filtro_info = {"tipo": "rango", "label": f"{desde_f or '…'} a {hasta_f or '…'}"}
        if not filtro_info:
            stmt = stmt.limit(500)
        rows = session.execute(stmt).scalars().all()

        # Agrupar asientos relacionados: misma fecha + mismo correlativo base,
        # o mismo documento, o misma glosa base (sin prefijo N) y sin sufijo [MIXTO: ...])
        import re
        def grupo_key(a):
            # 1) Correlativo con sufijo -N: ej "2026-11-0008-1", "2026-11-0008-2" -> base "2026-11-0008"
            corr = (a.numero_correlativo or "").strip()
            if corr:
                m = re.match(r"^(.+?)-(\d+)$", corr)
                if m:
                    base_corr = m.group(1)
                    # Solo agrupar si la base parece correlativo (YYYY-MM-NNNN)
                    if re.match(r"^\d{4}-\d{2}-\d+$", base_corr):
                        return ("corr", a.fecha.isoformat(), base_corr)
            # 2) Documento
            doc = (a.numero_documento or "").strip()
            if doc:
                return ("doc", a.fecha.isoformat(), doc)
            # 3) Glosa base: quita "N) tipo - ", "Cancelacion saldo pendiente - " y sufijo " [MIXTO: ...]"
            glosa = (a.glosa or "").strip()
            glosa_base = re.sub(r"^\d+\)\s*[A-Za-z]+\s*(parcial\s*)?-\s*", "", glosa)
            glosa_base = re.sub(r"^Cancelacion\s+saldo\s+pendiente\s*-\s*", "", glosa_base, flags=re.IGNORECASE)
            glosa_base = re.sub(r"\s*\[MIXTO:[^\]]*\]\s*$", "", glosa_base)
            return ("glosa", a.fecha.isoformat(), glosa_base or f"solo-{a.id}")

        grupos = {}
        orden_grupos = []
        for a in rows:
            k = grupo_key(a)
            if k not in grupos:
                grupos[k] = []
                orden_grupos.append(k)
            grupos[k].append(a)

        cerrados = _meses_cerrados_set(session)
        operaciones = []
        for k in orden_grupos:
            asientos = sorted(grupos[k], key=lambda a: a.id)
            total_debe = sum(
                sum((l.debe for l in a.lineas), Decimal("0")) for a in asientos
            )
            # Glosa consolidada: la del primer asiento (sin el "N) tipo - ")
            import re
            glosa_primera = (asientos[0].glosa or "").strip()
            titulo = re.sub(r"^\d+\)\s*[A-Za-z]+\s*-\s*", "", glosa_primera) or glosa_primera or "Operacion"
            f = asientos[0].fecha
            # Detectar si es mixto: buscar sufijo [MIXTO: X% contado ... Y% credito ...] en alguna glosa
            mixto_info = None
            for a in asientos:
                m = re.search(r"\[MIXTO:\s*(\d+(?:\.\d+)?)%\s*contado\s*S/\s*([\d.,]+)\s*-\s*(\d+(?:\.\d+)?)%\s*credito\s*S/\s*([\d.,]+)\]", a.glosa or "")
                if m:
                    monto_credito_original = Decimal(m.group(4).replace(",", ""))
                    # Detectar si es compra (4212 en haber en algun asiento) o venta (1212 en debe)
                    tipo_op = None
                    cuenta_credito = None
                    for aa in asientos:
                        for ll in aa.lineas:
                            if ll.cuenta_codigo == "4212" and ll.haber > 0:
                                tipo_op = "compra"
                                cuenta_credito = "4212"
                            elif ll.cuenta_codigo == "1212" and ll.debe > 0:
                                tipo_op = "venta"
                                cuenta_credito = "1212"
                        if tipo_op:
                            break
                    # Calcular saldo pendiente: monto credito original - cancelaciones posteriores
                    # Una cancelacion posterior es un asiento con cuenta_credito en el lado contrario
                    cancelado = Decimal("0")
                    for aa in asientos:
                        g = aa.glosa or ""
                        # Si la glosa contiene "Cancelacion saldo" (los nuevos que creamos aqui)
                        # o es una cancelacion posterior sin [MIXTO] (contado)
                        if "Cancelacion saldo" in g or "Cancelacion pendiente" in g:
                            for ll in aa.lineas:
                                if ll.cuenta_codigo == cuenta_credito:
                                    if tipo_op == "compra" and ll.debe > 0:
                                        cancelado += ll.debe
                                    elif tipo_op == "venta" and ll.haber > 0:
                                        cancelado += ll.haber
                    saldo_pendiente = monto_credito_original - cancelado
                    mixto_info = {
                        "pct_contado": m.group(1),
                        "monto_contado": m.group(2),
                        "pct_credito": m.group(3),
                        "monto_credito": m.group(4),
                        "tipo_op": tipo_op,
                        "cuenta_credito": cuenta_credito,
                        "saldo_pendiente": f"{saldo_pendiente:.2f}" if tipo_op else None,
                        "cancelado": f"{cancelado:.2f}",
                        "correlativo_base": re.sub(r"-\d+$", "", (asientos[0].numero_correlativo or "")) if asientos[0].numero_correlativo else "",
                        "ruc": asientos[0].ruc_tercero or "",
                        "razon_social": asientos[0].razon_social_tercero or "",
                        "fecha": asientos[0].fecha.isoformat(),
                        "glosa_base": re.sub(r"\s*\[MIXTO:[^\]]*\]\s*$", "", re.sub(r"^\d+\)\s*[A-Za-z]+\s*(parcial\s*)?-\s*", "", asientos[0].glosa or "")),
                    }
                    break
            operaciones.append({
                "key": "|".join(k),
                "titulo": titulo,
                "fecha": f,
                "n_asientos": len(asientos),
                "numero_documento": asientos[0].numero_documento,
                "ruc_tercero": asientos[0].ruc_tercero,
                "razon_social_tercero": asientos[0].razon_social_tercero,
                "numero_correlativo_base": (asientos[0].numero_correlativo or "").split("-")[0] if asientos[0].numero_correlativo else "",
                "total_debe": total_debe,
                "asientos": asientos,
                "ids": [a.id for a in asientos],
                "cerrado": (f.year, f.month) in cerrados,
                "mixto": mixto_info,
            })
    total_debe_filtro = Decimal("0")
    total_haber_filtro = Decimal("0")
    for op in operaciones:
        for a in op["asientos"]:
            for l in a.lineas:
                total_debe_filtro += l.debe
                total_haber_filtro += l.haber
    return render_template(
        "asientos_listado.html",
        operaciones=operaciones,
        filtro_info=filtro_info,
        total_debe_filtro=total_debe_filtro,
        total_haber_filtro=total_haber_filtro,
    )


@app.route("/asientos/nuevo")
def asientos_nuevo():
    editar_id = request.args.get("editar", type=int)
    asiento_edit = None
    if editar_id:
        with SessionLocal() as session:
            a = session.get(Asiento, editar_id)
            if a and not a.anulado_por_id and not a.reversa_de_id:
                asiento_edit = {
                    "id": a.id,
                    "numero": a.numero,
                    "fecha": a.fecha.isoformat(),
                    "glosa": a.glosa or "",
                    "moneda": a.moneda,
                    "tipo_cambio": str(a.tipo_cambio),
                    "codigo_libro": a.codigo_libro or "",
                    "numero_correlativo": a.numero_correlativo or "",
                    "numero_documento": a.numero_documento or "",
                    "ruc_tercero": a.ruc_tercero or "",
                    "razon_social_tercero": a.razon_social_tercero or "",
                    "lineas": [
                        {
                            "cuenta_codigo": l.cuenta_codigo,
                            "glosa_linea": l.glosa_linea or "",
                            "debe": float(l.debe),
                            "haber": float(l.haber),
                            "es_titulo": l.es_titulo,
                        } for l in a.lineas
                    ],
                }
    return render_template(
        "asiento_form.html",
        hoy=date.today().isoformat(),
        elementos=ELEMENTOS,
        asiento_edit=asiento_edit,
    )


@app.route("/asientos", methods=["POST"])
def asientos_crear():
    payload = request.get_json(silent=True) or {}
    fecha_str = (payload.get("fecha") or "").strip()
    glosa = (payload.get("glosa") or "").strip()
    moneda = (payload.get("moneda") or "PEN").strip().upper()
    tipo_cambio_raw = payload.get("tipo_cambio") or "1"
    codigo_libro = (payload.get("codigo_libro") or "").strip() or None
    numero_correlativo = (payload.get("numero_correlativo") or "").strip() or None
    numero_documento = (payload.get("numero_documento") or "").strip() or None
    ruc_tercero = (payload.get("ruc_tercero") or "").strip() or None
    razon_social_tercero = (payload.get("razon_social_tercero") or "").strip() or None
    if ruc_tercero and not _validar_ruc(ruc_tercero):
        return {"ok": False, "errores": ["RUC del tercero invalido (11 digitos + check digit)."]}, 400
    data_lineas = payload.get("lineas") or []

    errores = []
    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return {"ok": False, "errores": ["Fecha invalida (formato YYYY-MM-DD)."]}, 400
    if fecha_obj > date.today():
        errores.append("La fecha no puede ser futura.")

    try:
        tipo_cambio = _parse_decimal(tipo_cambio_raw)
        if tipo_cambio <= 0:
            errores.append("Tipo de cambio debe ser positivo.")
    except ValueError as e:
        errores.append(str(e))
        tipo_cambio = Decimal("1")

    lineas, errs = _validar_y_construir_lineas(data_lineas)
    errores.extend(errs)
    if errores:
        return {"ok": False, "errores": errores}, 400

    with SessionLocal() as session:
        with session.begin():
            if _mes_cerrado(session, fecha_obj):
                return {"ok": False, "errores": [f"El mes {fecha_obj.year}-{fecha_obj.month:02d} esta cerrado. No se puede crear asientos en ese periodo."]}, 400
            numero = _generar_numero(session, fecha_obj)
            asiento = Asiento(
                numero=numero,
                fecha=fecha_obj,
                glosa=glosa,
                moneda=moneda,
                tipo_cambio=tipo_cambio,
                codigo_libro=codigo_libro,
                numero_correlativo=numero_correlativo,
                numero_documento=numero_documento,
                ruc_tercero=ruc_tercero,
                razon_social_tercero=razon_social_tercero,
            )
            for l in lineas:
                asiento.lineas.append(AsientoLinea(**l))
            session.add(asiento)
        session.refresh(asiento)
        return {"ok": True, "id": asiento.id, "numero": asiento.numero}


@app.route("/asientos/<int:asiento_id>")
def asientos_detalle(asiento_id):
    with SessionLocal() as session:
        asiento = session.get(Asiento, asiento_id)
        if not asiento:
            abort(404)
        total_debe = sum((l.debe for l in asiento.lineas), Decimal("0"))
        total_haber = sum((l.haber for l in asiento.lineas), Decimal("0"))
        lineas_render = [
            {
                "orden": l.orden,
                "cuenta_codigo": l.cuenta_codigo,
                "cuenta_desc": CUENTAS_POR_CODIGO.get(l.cuenta_codigo, {}).get("descripcion", ""),
                "glosa_linea": l.glosa_linea,
                "debe": l.debe,
                "haber": l.haber,
                "es_titulo": l.es_titulo,
            }
            for l in asiento.lineas
        ]
        return render_template(
            "asiento_detalle.html",
            asiento=asiento,
            lineas=lineas_render,
            total_debe=total_debe,
            total_haber=total_haber,
        )


@app.route("/asientos/<int:asiento_id>", methods=["DELETE"])
def asientos_eliminar(asiento_id):
    with SessionLocal() as session:
        with session.begin():
            a = session.get(Asiento, asiento_id)
            if not a:
                return {"ok": False, "error": "Asiento no encontrado."}, 404
            if a.anulado_por_id:
                return {"ok": False, "error": "El asiento ya tiene una reversa; no se puede eliminar."}, 400
            if _mes_cerrado(session, a.fecha):
                return {"ok": False, "error": f"El mes {a.fecha.year}-{a.fecha.month:02d} esta cerrado. No se puede eliminar asientos de ese periodo."}, 400
            for l in list(a.lineas):
                session.delete(l)
            session.delete(a)
        return {"ok": True}


@app.route("/operaciones/eliminar", methods=["POST"])
def operaciones_eliminar():
    """Elimina varios asientos a la vez (una operacion completa)."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return {"ok": False, "error": "Lista de ids vacia."}, 400
    try:
        ids = [int(x) for x in ids]
    except (ValueError, TypeError):
        return {"ok": False, "error": "ids invalidos."}, 400

    with SessionLocal() as session:
        with session.begin():
            eliminados = 0
            bloqueados = 0
            for aid in ids:
                a = session.get(Asiento, aid)
                if not a or a.anulado_por_id:
                    continue
                if _mes_cerrado(session, a.fecha):
                    bloqueados += 1
                    continue
                for l in list(a.lineas):
                    session.delete(l)
                session.delete(a)
                eliminados += 1
        if bloqueados and not eliminados:
            return {"ok": False, "error": f"{bloqueados} asiento(s) estan en un mes cerrado y no se pueden eliminar."}, 400
        return {"ok": True, "eliminados": eliminados, "bloqueados": bloqueados}


@app.route("/asientos/<int:asiento_id>", methods=["PUT"])
def asientos_editar(asiento_id):
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as session:
        a = session.get(Asiento, asiento_id)
        if not a:
            return {"ok": False, "error": "Asiento no encontrado."}, 404
        if a.anulado_por_id or a.reversa_de_id:
            return {"ok": False, "error": "No se puede editar un asiento anulado o de reversa."}, 400

        fecha_str = (payload.get("fecha") or "").strip()
        try:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            return {"ok": False, "errores": ["Fecha invalida (YYYY-MM-DD)."]}, 400
        if fecha_obj > date.today():
            return {"ok": False, "errores": ["La fecha no puede ser futura."]}, 400

        try:
            tipo_cambio = _parse_decimal(payload.get("tipo_cambio") or "1")
            if tipo_cambio <= 0:
                return {"ok": False, "errores": ["Tipo de cambio debe ser positivo."]}, 400
        except ValueError as e:
            return {"ok": False, "errores": [str(e)]}, 400

        lineas, errs = _validar_y_construir_lineas(payload.get("lineas") or [])
        if errs:
            return {"ok": False, "errores": errs}, 400

        if _mes_cerrado(session, a.fecha):
            return {"ok": False, "errores": [f"El mes {a.fecha.year}-{a.fecha.month:02d} esta cerrado. No se puede editar asientos de ese periodo."]}, 400
        if _mes_cerrado(session, fecha_obj):
            return {"ok": False, "errores": [f"El mes destino {fecha_obj.year}-{fecha_obj.month:02d} esta cerrado."]}, 400

        session.rollback()
        with session.begin():
            a.fecha = fecha_obj
            a.glosa = (payload.get("glosa") or "").strip()
            a.moneda = (payload.get("moneda") or "PEN").strip().upper()
            a.tipo_cambio = tipo_cambio
            a.codigo_libro = (payload.get("codigo_libro") or "").strip() or None
            a.numero_correlativo = (payload.get("numero_correlativo") or "").strip() or None
            a.numero_documento = (payload.get("numero_documento") or "").strip() or None
            nuevo_ruc = (payload.get("ruc_tercero") or "").strip() or None
            if nuevo_ruc and not _validar_ruc(nuevo_ruc):
                raise ValueError("RUC del tercero invalido.")
            a.ruc_tercero = nuevo_ruc
            a.razon_social_tercero = (payload.get("razon_social_tercero") or "").strip() or None
            for l in list(a.lineas):
                session.delete(l)
            session.flush()
            for l in lineas:
                a.lineas.append(AsientoLinea(**l))
        session.refresh(a)
        return {"ok": True, "id": a.id, "numero": a.numero}


@app.route("/asientos/<int:asiento_id>/reversa", methods=["POST"])
def asientos_reversa(asiento_id):
    with SessionLocal() as session:
        with session.begin():
            original = session.get(Asiento, asiento_id)
            if not original:
                abort(404)
            if original.anulado_por_id:
                return {"ok": False, "error": "El asiento ya tiene una reversa."}, 400
            if original.reversa_de_id:
                return {"ok": False, "error": "Un asiento de reversa no se puede reversar."}, 400
            if _mes_cerrado(session, date.today()):
                return {"ok": False, "error": f"El mes actual {date.today().year}-{date.today().month:02d} esta cerrado. No se puede generar reversas."}, 400

            numero = _generar_numero(session, date.today())
            reversa = Asiento(
                numero=numero,
                fecha=date.today(),
                glosa=f"REVERSA de {original.numero}: {original.glosa}",
                moneda=original.moneda,
                tipo_cambio=original.tipo_cambio,
                reversa_de_id=original.id,
            )
            for l in original.lineas:
                reversa.lineas.append(AsientoLinea(
                    orden=l.orden,
                    cuenta_codigo=l.cuenta_codigo,
                    glosa_linea=l.glosa_linea,
                    debe=l.haber,
                    haber=l.debe,
                    es_titulo=l.es_titulo,
                ))
            session.add(reversa)
            session.flush()
            original.anulado_por_id = reversa.id
        session.refresh(reversa)
        return {"ok": True, "id": reversa.id, "numero": reversa.numero}


@app.route("/operaciones/cancelar-saldo", methods=["POST"])
def operaciones_cancelar_saldo():
    """Crea un asiento de cancelacion de saldo pendiente para una operacion mixta.

    Payload esperado:
      - correlativo_base: str (ej "2026-11-0008") -> se usa para enlazar
      - cuenta_credito: "4212" (compra) o "1212" (venta)
      - monto: Decimal/str - monto a cancelar
      - medio: "efectivo" | "banco" -> 1011 o 1041
      - fecha: YYYY-MM-DD (opcional, default hoy)
      - glosa_base: str - glosa descriptiva de la operacion original
      - ruc / razon_social: opcionales para persistir en el asiento
    """
    payload = request.get_json(silent=True) or {}
    correlativo_base = (payload.get("correlativo_base") or "").strip()
    cuenta_credito = (payload.get("cuenta_credito") or "").strip()
    medio_in = (payload.get("medio") or "efectivo").strip()
    glosa_base = (payload.get("glosa_base") or "").strip() or "Operacion"
    ruc = (payload.get("ruc") or "").strip()
    razon_social = (payload.get("razon_social") or "").strip()

    if cuenta_credito not in ("4212", "1212"):
        return {"ok": False, "error": "Cuenta de credito invalida."}, 400
    if medio_in not in ("efectivo", "banco"):
        return {"ok": False, "error": "Medio de pago invalido."}, 400
    try:
        monto = _parse_decimal(payload.get("monto") or "0")
    except ValueError as e:
        return {"ok": False, "error": str(e)}, 400
    if monto <= 0:
        return {"ok": False, "error": "El monto debe ser positivo."}, 400

    fecha_str = (payload.get("fecha") or "").strip() or date.today().isoformat()
    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return {"ok": False, "error": "Fecha invalida (YYYY-MM-DD)."}, 400
    if fecha_obj > date.today():
        return {"ok": False, "error": "La fecha no puede ser futura."}, 400

    cuenta_medio = "1041" if medio_in == "banco" else "1011"
    tipo_op = "compra" if cuenta_credito == "4212" else "venta"
    glosa_asiento = f"Cancelacion saldo pendiente - {glosa_base}"

    import re
    with SessionLocal() as session:
        if _mes_cerrado(session, fecha_obj):
            return {"ok": False, "error": f"El mes {fecha_obj.year}-{fecha_obj.month:02d} esta cerrado."}, 400

        # Buscar el siguiente sufijo del correlativo base para que caiga en la misma operacion
        correlativo_final = ""
        if correlativo_base and re.match(r"^\d{4}-\d{2}-\d+$", correlativo_base):
            existentes = session.execute(
                select(Asiento.numero_correlativo).where(
                    Asiento.numero_correlativo.like(correlativo_base + "-%")
                )
            ).scalars().all()
            maxsuf = 0
            for c in existentes:
                m = re.match(r"^.+-(\d+)$", c or "")
                if m:
                    try:
                        maxsuf = max(maxsuf, int(m.group(1)))
                    except ValueError:
                        pass
            correlativo_final = f"{correlativo_base}-{maxsuf + 1}"

        session.rollback()
        with session.begin():
            numero = _generar_numero(session, fecha_obj)
            asiento = Asiento(
                numero=numero,
                fecha=fecha_obj,
                glosa=glosa_asiento,
                moneda="PEN",
                tipo_cambio=Decimal("1"),
                codigo_libro="05",
                numero_correlativo=correlativo_final,
                ruc_tercero=ruc or None,
                razon_social_tercero=razon_social or None,
            )
            if tipo_op == "compra":
                # Pago a proveedor: 4212 Debe (bajo cuenta por pagar) / 1011|1041 Haber
                asiento.lineas.append(AsientoLinea(
                    orden=1, cuenta_codigo=cuenta_credito,
                    glosa_linea="Cancelacion saldo pendiente",
                    debe=monto, haber=Decimal("0"), es_titulo=False,
                ))
                asiento.lineas.append(AsientoLinea(
                    orden=2, cuenta_codigo=cuenta_medio,
                    glosa_linea=f"Pago desde {'banco' if medio_in == 'banco' else 'caja'}",
                    debe=Decimal("0"), haber=monto, es_titulo=False,
                ))
            else:
                # Cobro de cliente: 1011|1041 Debe / 1212 Haber (bajo cuenta por cobrar)
                asiento.lineas.append(AsientoLinea(
                    orden=1, cuenta_codigo=cuenta_medio,
                    glosa_linea=f"Cobro en {'banco' if medio_in == 'banco' else 'caja'}",
                    debe=monto, haber=Decimal("0"), es_titulo=False,
                ))
                asiento.lineas.append(AsientoLinea(
                    orden=2, cuenta_codigo=cuenta_credito,
                    glosa_linea="Cancelacion saldo pendiente",
                    debe=Decimal("0"), haber=monto, es_titulo=False,
                ))
            session.add(asiento)
            session.flush()
            asiento_id = asiento.id
            asiento_numero = asiento.numero
        return {"ok": True, "id": asiento_id, "numero": asiento_numero}


@app.route("/dashboard")
def dashboard():
    """Dashboard con estadisticas simples del mes."""
    with SessionLocal() as session:
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)
        asientos = session.execute(
            select(Asiento).order_by(Asiento.fecha.desc(), Asiento.id.desc())
        ).scalars().all()

        total_asientos = len(asientos)
        asientos_mes = [a for a in asientos if a.fecha >= inicio_mes and not a.reversa_de_id]
        total_movido_mes = Decimal("0")
        for a in asientos_mes:
            total_movido_mes += sum((l.debe for l in a.lineas), Decimal("0"))

        ultima_op = asientos[0] if asientos else None
        if ultima_op:
            import re
            ultima_glosa = re.sub(r"^\d+\)\s*[A-Za-z]+\s*-\s*", "", ultima_op.glosa or "") or "Operacion"
        else:
            ultima_glosa = None

        # Totales por tipo (venta/compra/otro) via heuristica: cuentas 70 = venta, 60/63 = compra
        ventas_mes = Decimal("0")
        compras_mes = Decimal("0")
        igv_ventas_mes = Decimal("0")
        igv_compras_mes = Decimal("0")
        for a in asientos_mes:
            es_venta = any(l.cuenta_codigo.startswith("70") or l.cuenta_codigo.startswith("75") for l in a.lineas)
            es_compra = any(l.cuenta_codigo.startswith("60") or l.cuenta_codigo.startswith("63") for l in a.lineas)
            for l in a.lineas:
                if l.cuenta_codigo.startswith("70") or l.cuenta_codigo.startswith("75"):
                    ventas_mes += l.haber
                elif l.cuenta_codigo.startswith("60") or l.cuenta_codigo.startswith("63"):
                    compras_mes += l.debe
                # IGV: cuenta 4011* (debito en ventas al haber, credito en compras al debe)
                if l.cuenta_codigo.startswith("4011"):
                    if es_venta and l.haber > 0:
                        igv_ventas_mes += l.haber
                    if es_compra and l.debe > 0:
                        igv_compras_mes += l.debe

        igv_por_pagar = igv_ventas_mes - igv_compras_mes

    return render_template(
        "dashboard.html",
        total_asientos=total_asientos,
        asientos_mes=len(asientos_mes),
        total_movido_mes=total_movido_mes,
        ultima_op=ultima_op,
        ultima_glosa=ultima_glosa,
        ventas_mes=ventas_mes,
        compras_mes=compras_mes,
        igv_ventas_mes=igv_ventas_mes,
        igv_compras_mes=igv_compras_mes,
        igv_por_pagar=igv_por_pagar,
        hoy=hoy,
    )


@app.route("/reportes/libro-diario")
def libro_diario():
    """Libro Diario: todos los asientos en orden cronologico con sus lineas."""
    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()
    numero_filtro = request.args.get("numero", "").strip()

    with SessionLocal() as session:
        asientos = session.execute(
            select(Asiento).order_by(Asiento.fecha, Asiento.id)
        ).scalars().all()

        filas = []
        total_debe = Decimal("0")
        total_haber = Decimal("0")

        for a in asientos:
            if fecha_desde:
                try:
                    if a.fecha < datetime.strptime(fecha_desde, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            if fecha_hasta:
                try:
                    if a.fecha > datetime.strptime(fecha_hasta, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            if numero_filtro and numero_filtro.lower() not in (a.numero or "").lower():
                continue

            lineas = []
            sub_d = Decimal("0")
            sub_h = Decimal("0")
            for l in a.lineas:
                if l.es_titulo:
                    continue
                lineas.append({
                    "cuenta": l.cuenta_codigo,
                    "descripcion": CUENTAS_POR_CODIGO.get(l.cuenta_codigo, {}).get("descripcion", ""),
                    "glosa": l.glosa_linea or "",
                    "debe": l.debe,
                    "haber": l.haber,
                })
                sub_d += l.debe
                sub_h += l.haber

            if not lineas:
                continue

            filas.append({
                "id": a.id,
                "fecha": a.fecha,
                "numero": a.numero,
                "glosa": a.glosa,
                "documento": a.numero_documento or "",
                "ruc": a.ruc_tercero or "",
                "razon_social": a.razon_social_tercero or "",
                "codigo_libro": a.codigo_libro or "",
                "lineas": lineas,
                "sub_debe": sub_d,
                "sub_haber": sub_h,
            })
            total_debe += sub_d
            total_haber += sub_h

    return render_template(
        "libro_diario.html",
        filas=filas,
        total_debe=total_debe,
        total_haber=total_haber,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        numero_filtro=numero_filtro,
        hoy=date.today().isoformat(),
    )


@app.route("/reportes/libro-mayor")
def libro_mayor():
    """Libro Mayor: movimientos agrupados por cuenta."""
    cuenta_filtro = request.args.get("cuenta", "").strip()
    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()

    with SessionLocal() as session:
        asientos = session.execute(
            select(Asiento).order_by(Asiento.fecha, Asiento.id)
        ).scalars().all()

        por_cuenta = {}
        for a in asientos:
            if fecha_desde:
                try:
                    if a.fecha < datetime.strptime(fecha_desde, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            if fecha_hasta:
                try:
                    if a.fecha > datetime.strptime(fecha_hasta, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            for l in a.lineas:
                if l.es_titulo:
                    continue
                if cuenta_filtro and not l.cuenta_codigo.startswith(cuenta_filtro):
                    continue
                k = l.cuenta_codigo
                if k not in por_cuenta:
                    por_cuenta[k] = {
                        "codigo": k,
                        "descripcion": CUENTAS_POR_CODIGO.get(k, {}).get("descripcion", "(desconocida)"),
                        "movs": [],
                        "total_debe": Decimal("0"),
                        "total_haber": Decimal("0"),
                    }
                por_cuenta[k]["movs"].append({
                    "fecha": a.fecha,
                    "numero": a.numero,
                    "asiento_id": a.id,
                    "glosa": l.glosa_linea or a.glosa,
                    "debe": l.debe,
                    "haber": l.haber,
                })
                por_cuenta[k]["total_debe"] += l.debe
                por_cuenta[k]["total_haber"] += l.haber

        for k in por_cuenta:
            por_cuenta[k]["saldo"] = por_cuenta[k]["total_debe"] - por_cuenta[k]["total_haber"]

        cuentas_ord = sorted(por_cuenta.values(), key=lambda x: x["codigo"])

    return render_template(
        "libro_mayor.html",
        cuentas=cuentas_ord,
        cuenta_filtro=cuenta_filtro,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        hoy=date.today().isoformat(),
    )


@app.route("/reportes/por-ruc")
def reporte_por_ruc():
    """Compras y ventas agrupadas por RUC del tercero (base DAOT)."""
    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()
    with SessionLocal() as session:
        asientos = _filtrar_asientos_rango(session, fecha_desde, fecha_hasta)
        por_ruc = {}
        for a in asientos:
            if not a.ruc_tercero:
                continue
            k = a.ruc_tercero
            if k not in por_ruc:
                por_ruc[k] = {
                    "ruc": k,
                    "razon_social": a.razon_social_tercero or "",
                    "n_ops": 0,
                    "compras": Decimal("0"),
                    "ventas": Decimal("0"),
                    "ultima_fecha": a.fecha,
                }
            por_ruc[k]["n_ops"] += 1
            if a.fecha > por_ruc[k]["ultima_fecha"]:
                por_ruc[k]["ultima_fecha"] = a.fecha
            if not por_ruc[k]["razon_social"] and a.razon_social_tercero:
                por_ruc[k]["razon_social"] = a.razon_social_tercero
            # Heuristica: 60xx/63xx en debe = compra, 70xx en haber = venta
            for l in a.lineas:
                if l.cuenta_codigo.startswith("60") or l.cuenta_codigo.startswith("63"):
                    por_ruc[k]["compras"] += l.debe
                elif l.cuenta_codigo.startswith("70"):
                    por_ruc[k]["ventas"] += l.haber
        filas = sorted(por_ruc.values(), key=lambda x: -(x["compras"] + x["ventas"]))
        total_compras = sum((f["compras"] for f in filas), Decimal("0"))
        total_ventas = sum((f["ventas"] for f in filas), Decimal("0"))
    return render_template(
        "reporte_por_ruc.html",
        filas=filas,
        total_compras=total_compras,
        total_ventas=total_ventas,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        hoy=date.today().isoformat(),
    )


@app.route("/reportes/balance")
def balance_comprobacion():
    """Balance de comprobacion: todas las cuentas con sus totales y saldos."""
    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()

    with SessionLocal() as session:
        asientos = session.execute(
            select(Asiento).order_by(Asiento.fecha, Asiento.id)
        ).scalars().all()

        por_cuenta = {}
        for a in asientos:
            if fecha_desde:
                try:
                    if a.fecha < datetime.strptime(fecha_desde, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            if fecha_hasta:
                try:
                    if a.fecha > datetime.strptime(fecha_hasta, "%Y-%m-%d").date():
                        continue
                except ValueError:
                    pass
            for l in a.lineas:
                if l.es_titulo:
                    continue
                k = l.cuenta_codigo
                if k not in por_cuenta:
                    por_cuenta[k] = {
                        "codigo": k,
                        "descripcion": CUENTAS_POR_CODIGO.get(k, {}).get("descripcion", "(desconocida)"),
                        "elemento": CUENTAS_POR_CODIGO.get(k, {}).get("elemento", 0),
                        "total_debe": Decimal("0"),
                        "total_haber": Decimal("0"),
                    }
                por_cuenta[k]["total_debe"] += l.debe
                por_cuenta[k]["total_haber"] += l.haber

        for k in por_cuenta:
            saldo = por_cuenta[k]["total_debe"] - por_cuenta[k]["total_haber"]
            por_cuenta[k]["saldo_deudor"] = saldo if saldo > 0 else Decimal("0")
            por_cuenta[k]["saldo_acreedor"] = -saldo if saldo < 0 else Decimal("0")

        cuentas_ord = sorted(por_cuenta.values(), key=lambda x: x["codigo"])
        total_debe = sum((c["total_debe"] for c in cuentas_ord), Decimal("0"))
        total_haber = sum((c["total_haber"] for c in cuentas_ord), Decimal("0"))
        total_saldo_deudor = sum((c["saldo_deudor"] for c in cuentas_ord), Decimal("0"))
        total_saldo_acreedor = sum((c["saldo_acreedor"] for c in cuentas_ord), Decimal("0"))

    return render_template(
        "balance_comprobacion.html",
        cuentas=cuentas_ord,
        total_debe=total_debe,
        total_haber=total_haber,
        total_saldo_deudor=total_saldo_deudor,
        total_saldo_acreedor=total_saldo_acreedor,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        hoy=date.today().isoformat(),
    )


def _filtrar_asientos_rango(session, fecha_desde, fecha_hasta):
    asientos = session.execute(
        select(Asiento).order_by(Asiento.fecha, Asiento.id)
    ).scalars().all()
    desde_d = None
    hasta_d = None
    if fecha_desde:
        try:
            desde_d = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_hasta:
        try:
            hasta_d = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        except ValueError:
            pass
    out = []
    for a in asientos:
        if desde_d and a.fecha < desde_d:
            continue
        if hasta_d and a.fecha > hasta_d:
            continue
        out.append(a)
    return out


@app.route("/reportes/libro-mayor/excel")
def libro_mayor_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    cuenta_filtro = request.args.get("cuenta", "").strip()
    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()

    with SessionLocal() as session:
        asientos = _filtrar_asientos_rango(session, fecha_desde, fecha_hasta)
        por_cuenta = {}
        for a in asientos:
            for l in a.lineas:
                if l.es_titulo:
                    continue
                if cuenta_filtro and not l.cuenta_codigo.startswith(cuenta_filtro):
                    continue
                k = l.cuenta_codigo
                if k not in por_cuenta:
                    por_cuenta[k] = {
                        "codigo": k,
                        "descripcion": CUENTAS_POR_CODIGO.get(k, {}).get("descripcion", ""),
                        "movs": [],
                        "total_debe": Decimal("0"),
                        "total_haber": Decimal("0"),
                    }
                por_cuenta[k]["movs"].append((a.fecha, a.numero, l.glosa_linea or a.glosa, l.debe, l.haber))
                por_cuenta[k]["total_debe"] += l.debe
                por_cuenta[k]["total_haber"] += l.haber
        cuentas_ord = sorted(por_cuenta.values(), key=lambda x: x["codigo"])

    wb = Workbook()
    ws = wb.active
    ws.title = "Libro Mayor"
    thin = Side(border_style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    sep_fill = PatternFill("solid", fgColor="EAF0F7")
    sep_font = Font(bold=True, color="1E3A5F", size=11)

    ws["A1"] = "LIBRO MAYOR"
    ws["A1"].font = Font(bold=True, size=14, color="1E3A5F")
    ws.merge_cells("A1:F1")
    ws["A1"].alignment = Alignment(horizontal="center")
    rango = f"Desde {fecha_desde or '-'} hasta {fecha_hasta or '-'}"
    if cuenta_filtro:
        rango += f" | Cuenta: {cuenta_filtro}"
    ws["A2"] = rango
    ws.merge_cells("A2:F2")
    ws["A2"].font = Font(italic=True, color="666666")

    row = 4
    for c in cuentas_ord:
        ws.cell(row=row, column=1, value=f"{c['codigo']} — {c['descripcion']}")
        ws.cell(row=row, column=1).font = sep_font
        for col in range(1, 7):
            ws.cell(row=row, column=col).fill = sep_fill
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        row += 1
        headers = ["Fecha", "Asiento", "Glosa", "Debe", "Haber", "Saldo"]
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            cell.border = border
        row += 1
        saldo = Decimal("0")
        for (f, numero, glosa, debe, haber) in c["movs"]:
            saldo += debe - haber
            ws.cell(row=row, column=1, value=f.isoformat()).border = border
            ws.cell(row=row, column=2, value=numero).border = border
            ws.cell(row=row, column=3, value=glosa).border = border
            ws.cell(row=row, column=4, value=float(debe)).border = border
            ws.cell(row=row, column=4).number_format = "#,##0.00"
            ws.cell(row=row, column=5, value=float(haber)).border = border
            ws.cell(row=row, column=5).number_format = "#,##0.00"
            ws.cell(row=row, column=6, value=float(saldo)).border = border
            ws.cell(row=row, column=6).number_format = "#,##0.00"
            row += 1
        # subtotal
        ws.cell(row=row, column=3, value="Subtotal").font = Font(bold=True)
        ws.cell(row=row, column=3).alignment = Alignment(horizontal="right")
        ws.cell(row=row, column=4, value=float(c["total_debe"])).font = Font(bold=True)
        ws.cell(row=row, column=4).number_format = "#,##0.00"
        ws.cell(row=row, column=5, value=float(c["total_haber"])).font = Font(bold=True)
        ws.cell(row=row, column=5).number_format = "#,##0.00"
        ws.cell(row=row, column=6, value=float(c["total_debe"] - c["total_haber"])).font = Font(bold=True)
        ws.cell(row=row, column=6).number_format = "#,##0.00"
        for col in range(3, 7):
            ws.cell(row=row, column=col).border = border
        row += 2

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 42
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"libro_mayor_{date.today().isoformat()}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/reportes/balance/excel")
def balance_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    fecha_desde = request.args.get("desde", "").strip()
    fecha_hasta = request.args.get("hasta", "").strip()

    with SessionLocal() as session:
        asientos = _filtrar_asientos_rango(session, fecha_desde, fecha_hasta)
        por_cuenta = {}
        for a in asientos:
            for l in a.lineas:
                if l.es_titulo:
                    continue
                k = l.cuenta_codigo
                if k not in por_cuenta:
                    por_cuenta[k] = {
                        "codigo": k,
                        "descripcion": CUENTAS_POR_CODIGO.get(k, {}).get("descripcion", ""),
                        "elemento": CUENTAS_POR_CODIGO.get(k, {}).get("elemento", 0),
                        "total_debe": Decimal("0"),
                        "total_haber": Decimal("0"),
                    }
                por_cuenta[k]["total_debe"] += l.debe
                por_cuenta[k]["total_haber"] += l.haber
        cuentas_ord = sorted(por_cuenta.values(), key=lambda x: x["codigo"])

    wb = Workbook()
    ws = wb.active
    ws.title = "Balance"
    thin = Side(border_style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    ws["A1"] = "BALANCE DE COMPROBACION"
    ws["A1"].font = Font(bold=True, size=14, color="1E3A5F")
    ws.merge_cells("A1:G1")
    ws["A1"].alignment = Alignment(horizontal="center")
    ws["A2"] = f"Desde {fecha_desde or '-'} hasta {fecha_hasta or '-'}"
    ws.merge_cells("A2:G2")
    ws["A2"].font = Font(italic=True, color="666666")

    headers = ["Codigo", "Descripcion", "Elem", "Debe", "Haber", "Saldo Deudor", "Saldo Acreedor"]
    row = 4
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    row = 5
    tot_d = tot_h = tot_sd = tot_sa = Decimal("0")
    for c in cuentas_ord:
        saldo = c["total_debe"] - c["total_haber"]
        sd = saldo if saldo > 0 else Decimal("0")
        sa = -saldo if saldo < 0 else Decimal("0")
        ws.cell(row=row, column=1, value=c["codigo"]).border = border
        ws.cell(row=row, column=2, value=c["descripcion"]).border = border
        ws.cell(row=row, column=3, value=c["elemento"]).border = border
        ws.cell(row=row, column=3).alignment = Alignment(horizontal="center")
        ws.cell(row=row, column=4, value=float(c["total_debe"])).border = border
        ws.cell(row=row, column=4).number_format = "#,##0.00"
        ws.cell(row=row, column=5, value=float(c["total_haber"])).border = border
        ws.cell(row=row, column=5).number_format = "#,##0.00"
        ws.cell(row=row, column=6, value=float(sd) if sd > 0 else None).border = border
        ws.cell(row=row, column=6).number_format = "#,##0.00"
        ws.cell(row=row, column=7, value=float(sa) if sa > 0 else None).border = border
        ws.cell(row=row, column=7).number_format = "#,##0.00"
        tot_d += c["total_debe"]
        tot_h += c["total_haber"]
        tot_sd += sd
        tot_sa += sa
        row += 1

    ws.cell(row=row, column=3, value="TOTALES").font = Font(bold=True, size=12, color="1E3A5F")
    ws.cell(row=row, column=3).alignment = Alignment(horizontal="right")
    ws.cell(row=row, column=4, value=float(tot_d)).font = Font(bold=True)
    ws.cell(row=row, column=4).number_format = "#,##0.00"
    ws.cell(row=row, column=5, value=float(tot_h)).font = Font(bold=True)
    ws.cell(row=row, column=5).number_format = "#,##0.00"
    ws.cell(row=row, column=6, value=float(tot_sd)).font = Font(bold=True)
    ws.cell(row=row, column=6).number_format = "#,##0.00"
    ws.cell(row=row, column=7, value=float(tot_sa)).font = Font(bold=True)
    ws.cell(row=row, column=7).number_format = "#,##0.00"
    for col in range(3, 8):
        ws.cell(row=row, column=col).border = border

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 42
    ws.column_dimensions["C"].width = 6
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 15

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"balance_comprobacion_{date.today().isoformat()}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _resumen_anual(session, year: int):
    """Devuelve dict con desglose mensual, por elemento y top cuentas para `year`."""
    desde = date(year, 1, 1)
    hasta = date(year, 12, 31)
    asientos = session.execute(
        select(Asiento).where(Asiento.fecha >= desde, Asiento.fecha <= hasta).order_by(Asiento.fecha, Asiento.id)
    ).scalars().all()
    cerrados = _meses_cerrados_set(session)

    meses = []
    for m in range(1, 13):
        meses.append({
            "mes": m,
            "nombre": ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][m-1],
            "total_debe": Decimal("0"),
            "total_haber": Decimal("0"),
            "num_asientos": 0,
            "cerrado": (year, m) in cerrados,
        })

    por_elemento = {}
    por_cuenta = {}
    total_debe_anual = Decimal("0")
    total_haber_anual = Decimal("0")

    for a in asientos:
        m_idx = a.fecha.month - 1
        meses[m_idx]["num_asientos"] += 1
        for l in a.lineas:
            if l.es_titulo:
                continue
            meses[m_idx]["total_debe"] += l.debe
            meses[m_idx]["total_haber"] += l.haber
            total_debe_anual += l.debe
            total_haber_anual += l.haber

            info = CUENTAS_POR_CODIGO.get(l.cuenta_codigo, {})
            e = info.get("elemento", 0)
            if e not in por_elemento:
                por_elemento[e] = {
                    "elemento": e,
                    "nombre": info.get("elemento_nombre", f"Elemento {e}"),
                    "total_debe": Decimal("0"),
                    "total_haber": Decimal("0"),
                }
            por_elemento[e]["total_debe"] += l.debe
            por_elemento[e]["total_haber"] += l.haber

            k = l.cuenta_codigo
            if k not in por_cuenta:
                por_cuenta[k] = {
                    "codigo": k,
                    "descripcion": info.get("descripcion", "(desconocida)"),
                    "elemento": e,
                    "total_debe": Decimal("0"),
                    "total_haber": Decimal("0"),
                }
            por_cuenta[k]["total_debe"] += l.debe
            por_cuenta[k]["total_haber"] += l.haber

    for m in meses:
        m["diferencia"] = m["total_debe"] - m["total_haber"]
        m["cuadra"] = abs(m["diferencia"]) < Decimal("0.01")
        m["total_movido"] = m["total_debe"]

    for e in por_elemento.values():
        e["saldo"] = e["total_debe"] - e["total_haber"]

    elementos_ord = sorted(por_elemento.values(), key=lambda x: x["elemento"])
    top_cuentas = sorted(
        por_cuenta.values(),
        key=lambda x: x["total_debe"] + x["total_haber"],
        reverse=True,
    )[:10]
    for c in top_cuentas:
        c["movimiento"] = c["total_debe"] + c["total_haber"]

    diferencia_anual = total_debe_anual - total_haber_anual
    return {
        "year": year,
        "meses": meses,
        "elementos": elementos_ord,
        "top_cuentas": top_cuentas,
        "total_debe": total_debe_anual,
        "total_haber": total_haber_anual,
        "diferencia": diferencia_anual,
        "cuadra": abs(diferencia_anual) < Decimal("0.01"),
        "num_asientos": len(asientos),
    }


@app.route("/reportes/anual")
def reporte_anual():
    """Reporte anual consolidado: cuadre global + desglose mensual + por elemento."""
    year_arg = request.args.get("year", "").strip()
    try:
        year = int(year_arg) if year_arg else date.today().year
    except ValueError:
        year = date.today().year

    with SessionLocal() as session:
        anios_rows = session.execute(
            select(func.extract("year", Asiento.fecha)).distinct()
        ).all()
        anios = sorted({int(y[0]) for y in anios_rows if y[0] is not None}, reverse=True)
        if date.today().year not in anios:
            anios.insert(0, date.today().year)
        if year not in anios:
            anios.append(year)
            anios = sorted(set(anios), reverse=True)

        resumen = _resumen_anual(session, year)

    return render_template(
        "reporte_anual.html",
        resumen=resumen,
        year=year,
        anios=anios,
    )


@app.route("/reportes/anual/excel")
def reporte_anual_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    year_arg = request.args.get("year", "").strip()
    try:
        year = int(year_arg) if year_arg else date.today().year
    except ValueError:
        year = date.today().year

    with SessionLocal() as session:
        resumen = _resumen_anual(session, year)
        asientos_year = session.execute(
            select(Asiento).where(
                Asiento.fecha >= date(year, 1, 1),
                Asiento.fecha <= date(year, 12, 31),
            ).order_by(Asiento.fecha, Asiento.id)
        ).scalars().all()

        asientos_por_mes = {m: [] for m in range(1, 13)}
        for a in asientos_year:
            td = sum((l.debe for l in a.lineas if not l.es_titulo), Decimal("0"))
            th = sum((l.haber for l in a.lineas if not l.es_titulo), Decimal("0"))
            asientos_por_mes[a.fecha.month].append({
                "fecha": a.fecha.isoformat(),
                "numero": a.numero,
                "glosa": a.glosa or "",
                "ruc": a.ruc_tercero or "",
                "total_debe": td,
                "total_haber": th,
            })

    wb = Workbook()
    thin = Side(border_style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    # Hoja resumen
    ws = wb.active
    ws.title = "Resumen anual"
    ws["A1"] = f"REPORTE ANUAL {year}"
    ws["A1"].font = Font(bold=True, size=14, color="1E3A5F")
    ws.merge_cells("A1:E1")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws["A3"] = "Mes"
    ws["B3"] = "Asientos"
    ws["C3"] = "Debe"
    ws["D3"] = "Haber"
    ws["E3"] = "Diferencia"
    ws["F3"] = "Cuadra"
    ws["G3"] = "Cerrado"
    for col in range(1, 8):
        c = ws.cell(row=3, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center")
        c.border = border

    row = 4
    for m in resumen["meses"]:
        ws.cell(row=row, column=1, value=m["nombre"]).border = border
        ws.cell(row=row, column=2, value=m["num_asientos"]).border = border
        ws.cell(row=row, column=3, value=float(m["total_debe"])).border = border
        ws.cell(row=row, column=3).number_format = "#,##0.00"
        ws.cell(row=row, column=4, value=float(m["total_haber"])).border = border
        ws.cell(row=row, column=4).number_format = "#,##0.00"
        ws.cell(row=row, column=5, value=float(m["diferencia"])).border = border
        ws.cell(row=row, column=5).number_format = "#,##0.00"
        ws.cell(row=row, column=6, value="Si" if m["cuadra"] else "NO").border = border
        ws.cell(row=row, column=7, value="Si" if m["cerrado"] else "").border = border
        row += 1

    ws.cell(row=row, column=1, value="TOTAL").font = Font(bold=True)
    ws.cell(row=row, column=2, value=resumen["num_asientos"]).font = Font(bold=True)
    ws.cell(row=row, column=3, value=float(resumen["total_debe"])).font = Font(bold=True)
    ws.cell(row=row, column=3).number_format = "#,##0.00"
    ws.cell(row=row, column=4, value=float(resumen["total_haber"])).font = Font(bold=True)
    ws.cell(row=row, column=4).number_format = "#,##0.00"
    ws.cell(row=row, column=5, value=float(resumen["diferencia"])).font = Font(bold=True)
    ws.cell(row=row, column=5).number_format = "#,##0.00"
    ws.cell(row=row, column=6, value="Si" if resumen["cuadra"] else "NO").font = Font(bold=True)
    for col in range(1, 8):
        ws.cell(row=row, column=col).border = border

    # Por elemento
    row += 3
    ws.cell(row=row, column=1, value="POR ELEMENTO PCGE").font = Font(bold=True, size=12, color="1E3A5F")
    row += 1
    ws.cell(row=row, column=1, value="Elem").fill = header_fill
    ws.cell(row=row, column=2, value="Nombre").fill = header_fill
    ws.cell(row=row, column=3, value="Debe").fill = header_fill
    ws.cell(row=row, column=4, value="Haber").fill = header_fill
    ws.cell(row=row, column=5, value="Saldo").fill = header_fill
    for col in range(1, 6):
        c = ws.cell(row=row, column=col)
        c.font = header_font
        c.alignment = Alignment(horizontal="center")
        c.border = border
    row += 1
    for e in resumen["elementos"]:
        ws.cell(row=row, column=1, value=e["elemento"]).border = border
        ws.cell(row=row, column=2, value=e["nombre"]).border = border
        ws.cell(row=row, column=3, value=float(e["total_debe"])).border = border
        ws.cell(row=row, column=3).number_format = "#,##0.00"
        ws.cell(row=row, column=4, value=float(e["total_haber"])).border = border
        ws.cell(row=row, column=4).number_format = "#,##0.00"
        ws.cell(row=row, column=5, value=float(e["saldo"])).border = border
        ws.cell(row=row, column=5).number_format = "#,##0.00"
        row += 1

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 10

    # Una hoja por mes con asientos
    nombres_mes = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    for m_idx in range(1, 13):
        asientos_m = asientos_por_mes[m_idx]
        if not asientos_m:
            continue
        ws_m = wb.create_sheet(title=f"{m_idx:02d}-{nombres_mes[m_idx-1]}")
        ws_m["A1"] = f"{nombres_mes[m_idx-1]} {year}"
        ws_m["A1"].font = Font(bold=True, size=14, color="1E3A5F")
        ws_m.merge_cells("A1:F1")
        headers = ["Fecha", "Numero", "Glosa", "RUC", "Debe", "Haber"]
        for col, h in enumerate(headers, start=1):
            c = ws_m.cell(row=3, column=col, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center")
            c.border = border
        r = 4
        tot_d = tot_h = Decimal("0")
        for a in asientos_m:
            ws_m.cell(row=r, column=1, value=a["fecha"]).border = border
            ws_m.cell(row=r, column=2, value=a["numero"]).border = border
            ws_m.cell(row=r, column=3, value=a["glosa"]).border = border
            ws_m.cell(row=r, column=4, value=a["ruc"]).border = border
            ws_m.cell(row=r, column=5, value=float(a["total_debe"])).border = border
            ws_m.cell(row=r, column=5).number_format = "#,##0.00"
            ws_m.cell(row=r, column=6, value=float(a["total_haber"])).border = border
            ws_m.cell(row=r, column=6).number_format = "#,##0.00"
            tot_d += a["total_debe"]
            tot_h += a["total_haber"]
            r += 1
        ws_m.cell(row=r, column=4, value="TOTAL").font = Font(bold=True)
        ws_m.cell(row=r, column=5, value=float(tot_d)).font = Font(bold=True)
        ws_m.cell(row=r, column=5).number_format = "#,##0.00"
        ws_m.cell(row=r, column=6, value=float(tot_h)).font = Font(bold=True)
        ws_m.cell(row=r, column=6).number_format = "#,##0.00"
        for col in range(4, 7):
            ws_m.cell(row=r, column=col).border = border
        ws_m.column_dimensions["A"].width = 12
        ws_m.column_dimensions["B"].width = 14
        ws_m.column_dimensions["C"].width = 46
        ws_m.column_dimensions["D"].width = 14
        ws_m.column_dimensions["E"].width = 14
        ws_m.column_dimensions["F"].width = 14

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"reporte_anual_{year}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _validar_ruc(ruc: str) -> bool:
    """Valida formato RUC peruano: 11 digitos + check digit."""
    ruc = (ruc or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        return False
    if ruc[:2] not in ("10", "15", "17", "20"):
        return False
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(ruc[i]) * pesos[i] for i in range(10))
    resto = suma % 11
    check = 11 - resto
    if check == 10:
        check = 0
    elif check == 11:
        check = 1
    return check == int(ruc[10])


def _consultar_sunat_online(ruc: str):
    """Consulta RUC en apis.net.pe. Devuelve dict o None si falla."""
    import urllib.request
    import urllib.error

    token = os.environ.get("APIS_NET_PE_TOKEN", "").strip()
    # v2 requiere token; v1 es publico (limitado pero suficiente)
    if token:
        url = f"https://api.apis.net.pe/v2/sunat/ruc?numero={ruc}"
    else:
        url = f"https://api.apis.net.pe/v1/ruc?numero={ruc}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


@app.route("/entidades")
def entidades_vista():
    q = request.args.get("q", "").strip()
    with SessionLocal() as session:
        stmt = select(Entidad).order_by(Entidad.razon_social)
        if q:
            qn = f"%{q.lower()}%"
            stmt = stmt.where(
                (func.lower(Entidad.razon_social).like(qn)) |
                (Entidad.ruc.like(f"%{q}%")) |
                (func.lower(Entidad.nombre_comercial).like(qn))
            )
        rows = session.execute(stmt).scalars().all()
        entidades = [
            {
                "id": e.id,
                "ruc": e.ruc,
                "razon_social": e.razon_social,
                "nombre_comercial": e.nombre_comercial or "",
                "estado": e.estado or "",
                "condicion": e.condicion or "",
                "direccion": e.direccion or "",
                "distrito": e.distrito or "",
                "provincia": e.provincia or "",
                "departamento": e.departamento or "",
                "tipo": e.tipo or "",
                "nota": e.nota or "",
                "updated_at": e.updated_at,
            }
            for e in rows
        ]
    return render_template("entidades.html", entidades=entidades, q=q)


@app.route("/sunat/ruc/<ruc>")
def sunat_consultar(ruc):
    """Consulta un RUC: primero mira cache local, si no, consulta API externa."""
    ruc = ruc.strip()
    if not _validar_ruc(ruc):
        return {"ok": False, "error": "RUC invalido (debe tener 11 digitos y check digit valido)."}, 400

    forzar = request.args.get("refresh") == "1"
    with SessionLocal() as session:
        with session.begin():
            cached = session.execute(select(Entidad).where(Entidad.ruc == ruc)).scalar_one_or_none()
            if cached and not forzar:
                return {
                    "ok": True,
                    "fuente": "cache",
                    "data": {
                        "ruc": cached.ruc,
                        "razon_social": cached.razon_social,
                        "nombre_comercial": cached.nombre_comercial,
                        "estado": cached.estado,
                        "condicion": cached.condicion,
                        "direccion": cached.direccion,
                        "distrito": cached.distrito,
                        "provincia": cached.provincia,
                        "departamento": cached.departamento,
                        "ubigeo": cached.ubigeo,
                        "tipo": cached.tipo,
                        "nota": cached.nota,
                    },
                }

            data = _consultar_sunat_online(ruc)
            if not data:
                if cached:
                    return {
                        "ok": True,
                        "fuente": "cache_fallback",
                        "aviso": "No se pudo consultar SUNAT en linea; mostrando datos en cache.",
                        "data": {
                            "ruc": cached.ruc,
                            "razon_social": cached.razon_social,
                            "estado": cached.estado,
                            "condicion": cached.condicion,
                            "direccion": cached.direccion,
                        },
                    }
                return {"ok": False, "error": "No se pudo consultar SUNAT. Verifica tu conexion o el token APIS_NET_PE_TOKEN."}, 502

            # Normalizar respuesta: apis.net.pe v2 usa razonSocial/estado/condicion/direccion/etc
            def pick(*keys):
                for k in keys:
                    v = data.get(k)
                    if v:
                        return str(v).strip()
                return None

            razon_social = pick("razonSocial", "nombre") or ""
            if not razon_social:
                return {"ok": False, "error": "La API externa no devolvio razon social."}, 502

            if cached:
                cached.razon_social = razon_social
                cached.nombre_comercial = pick("nombreComercial")
                cached.estado = pick("estado")
                cached.condicion = pick("condicion")
                cached.direccion = pick("direccion")
                cached.distrito = pick("distrito")
                cached.provincia = pick("provincia")
                cached.departamento = pick("departamento")
                cached.ubigeo = pick("ubigeo")
                cached.tipo = pick("tipo", "tipoContribuyente")
                cached.updated_at = datetime.utcnow()
                e = cached
            else:
                e = Entidad(
                    ruc=ruc,
                    razon_social=razon_social,
                    nombre_comercial=pick("nombreComercial"),
                    estado=pick("estado"),
                    condicion=pick("condicion"),
                    direccion=pick("direccion"),
                    distrito=pick("distrito"),
                    provincia=pick("provincia"),
                    departamento=pick("departamento"),
                    ubigeo=pick("ubigeo"),
                    tipo=pick("tipo", "tipoContribuyente"),
                )
                session.add(e)
            session.flush()
            return {
                "ok": True,
                "fuente": "sunat",
                "data": {
                    "ruc": e.ruc,
                    "razon_social": e.razon_social,
                    "nombre_comercial": e.nombre_comercial,
                    "estado": e.estado,
                    "condicion": e.condicion,
                    "direccion": e.direccion,
                    "distrito": e.distrito,
                    "provincia": e.provincia,
                    "departamento": e.departamento,
                    "ubigeo": e.ubigeo,
                    "tipo": e.tipo,
                },
            }


@app.route("/entidades/<int:entidad_id>", methods=["PUT"])
def entidades_editar(entidad_id):
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as session:
        with session.begin():
            e = session.get(Entidad, entidad_id)
            if not e:
                return {"ok": False, "error": "Entidad no encontrada."}, 404
            if "nota" in payload:
                e.nota = (payload.get("nota") or "").strip() or None
            if "razon_social" in payload:
                rs = (payload.get("razon_social") or "").strip()
                if rs:
                    e.razon_social = rs
            e.updated_at = datetime.utcnow()
        return {"ok": True}


@app.route("/entidades/<int:entidad_id>", methods=["DELETE"])
def entidades_eliminar(entidad_id):
    with SessionLocal() as session:
        with session.begin():
            e = session.get(Entidad, entidad_id)
            if not e:
                return {"ok": False, "error": "Entidad no encontrada."}, 404
            session.delete(e)
        return {"ok": True}


@app.route("/importar", methods=["GET"])
def importar_vista():
    return render_template("importar.html")


@app.route("/importar/plantilla")
def importar_plantilla():
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla"
    ws["A1"] = "PLANTILLA DE IMPORTACION — Libro Diario"
    ws["A1"].font = Font(bold=True, size=12, color="1E3A5F")
    ws.merge_cells("A1:F1")
    ws["A2"] = "Reglas: una fila por linea. Agrupa lineas de un mismo asiento repitiendo Fecha + Documento (o Fecha + Glosa si no hay Documento)."
    ws.merge_cells("A2:F2")
    ws["A2"].font = Font(italic=True, color="666666")

    headers = ["Fecha (YYYY-MM-DD)", "Documento", "Glosa", "Cuenta (codigo PCGE)", "Debe", "Haber"]
    fill = PatternFill("solid", fgColor="1E3A5F")
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fill
        c.alignment = Alignment(horizontal="center")

    ejemplo = [
        ("2026-01-15", "F001-123", "Venta de mercaderia", "1212", 118.00, 0),
        ("2026-01-15", "F001-123", "Venta de mercaderia", "4011", 0, 18.00),
        ("2026-01-15", "F001-123", "Venta de mercaderia", "7011", 0, 100.00),
    ]
    for i, row in enumerate(ejemplo, start=5):
        for j, val in enumerate(row, start=1):
            ws.cell(row=i, column=j, value=val)

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 36
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="plantilla_importacion_libro_diario.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _parsear_excel_importacion(fileobj):
    """Devuelve (asientos, errores). Cada asiento = {fecha, documento, glosa, lineas:[...], total_debe, total_haber}."""
    from openpyxl import load_workbook

    try:
        wb = load_workbook(fileobj, data_only=True)
    except Exception as e:
        return [], [f"No se pudo leer el archivo: {e}"]
    ws = wb.active
    errores = []

    # Buscar fila de headers: primera fila que tenga "Fecha" en col A
    header_row = None
    for row in range(1, 15):
        v = ws.cell(row=row, column=1).value
        if v and "fecha" in str(v).lower():
            header_row = row
            break
    if header_row is None:
        return [], ["No se encontro la fila de headers (debe comenzar con 'Fecha ...' en columna A)."]

    grupos = {}
    orden = []
    for i, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
        if not row or all(v in (None, "") for v in row[:6]):
            continue
        fecha_v, doc_v, glosa_v, cuenta_v, debe_v, haber_v = (list(row) + [None] * 6)[:6]
        linea_num = i
        if not fecha_v:
            errores.append(f"Fila {linea_num}: falta fecha.")
            continue
        if isinstance(fecha_v, datetime):
            fecha_d = fecha_v.date()
        elif isinstance(fecha_v, date):
            fecha_d = fecha_v
        else:
            try:
                fecha_d = datetime.strptime(str(fecha_v).strip()[:10], "%Y-%m-%d").date()
            except ValueError:
                errores.append(f"Fila {linea_num}: fecha invalida '{fecha_v}'. Usa YYYY-MM-DD.")
                continue

        cuenta = str(cuenta_v or "").strip()
        if not cuenta:
            errores.append(f"Fila {linea_num}: falta cuenta.")
            continue
        if cuenta not in CUENTAS_POR_CODIGO:
            errores.append(f"Fila {linea_num}: cuenta {cuenta} no existe en PCGE.")
            continue
        nivel = CUENTAS_POR_CODIGO[cuenta]["nivel"]
        if nivel not in NIVELES_MOVIMIENTO:
            errores.append(f"Fila {linea_num}: cuenta {cuenta} es nivel {nivel}; solo niveles 4 o 5.")
            continue

        try:
            debe = _parse_decimal(debe_v or 0)
            haber = _parse_decimal(haber_v or 0)
        except ValueError as e:
            errores.append(f"Fila {linea_num}: {e}")
            continue
        if debe < 0 or haber < 0:
            errores.append(f"Fila {linea_num}: montos no pueden ser negativos.")
            continue
        if debe > 0 and haber > 0:
            errores.append(f"Fila {linea_num}: no puede tener debe y haber a la vez.")
            continue
        if debe == 0 and haber == 0:
            errores.append(f"Fila {linea_num}: ingresa monto en debe o haber.")
            continue

        doc = str(doc_v or "").strip()
        glosa = str(glosa_v or "").strip()
        key = (fecha_d.isoformat(), doc) if doc else (fecha_d.isoformat(), f"g:{glosa}")
        if key not in grupos:
            grupos[key] = {
                "fecha": fecha_d,
                "documento": doc or None,
                "glosa": glosa or "Importado",
                "lineas": [],
                "total_debe": Decimal("0"),
                "total_haber": Decimal("0"),
            }
            orden.append(key)
        grupos[key]["lineas"].append({
            "cuenta_codigo": cuenta,
            "glosa_linea": glosa,
            "debe": debe,
            "haber": haber,
            "cuenta_desc": CUENTAS_POR_CODIGO[cuenta]["descripcion"],
            "fila_excel": linea_num,
        })
        grupos[key]["total_debe"] += debe
        grupos[key]["total_haber"] += haber

    asientos = [grupos[k] for k in orden]

    for a in asientos:
        if len(a["lineas"]) < 2:
            errores.append(f"Asiento del {a['fecha']} doc={a['documento'] or '-'}: necesita al menos 2 lineas.")
        if abs(a["total_debe"] - a["total_haber"]) > TOLERANCIA:
            errores.append(f"Asiento del {a['fecha']} doc={a['documento'] or '-'}: no cuadra (debe={a['total_debe']} haber={a['total_haber']}).")
    return asientos, errores


@app.route("/importar/preview", methods=["POST"])
def importar_preview():
    f = request.files.get("archivo")
    if not f:
        return {"ok": False, "error": "No se recibio archivo."}, 400
    asientos, errores = _parsear_excel_importacion(f)
    data = []
    for a in asientos:
        data.append({
            "fecha": a["fecha"].isoformat(),
            "documento": a["documento"] or "",
            "glosa": a["glosa"],
            "total_debe": float(a["total_debe"]),
            "total_haber": float(a["total_haber"]),
            "cuadra": abs(a["total_debe"] - a["total_haber"]) <= TOLERANCIA and len(a["lineas"]) >= 2,
            "lineas": [
                {
                    "cuenta": l["cuenta_codigo"],
                    "cuenta_desc": l["cuenta_desc"],
                    "glosa": l["glosa_linea"],
                    "debe": float(l["debe"]),
                    "haber": float(l["haber"]),
                } for l in a["lineas"]
            ],
        })
    return {"ok": True, "asientos": data, "errores": errores}


@app.route("/importar/ejecutar", methods=["POST"])
def importar_ejecutar():
    f = request.files.get("archivo")
    if not f:
        return {"ok": False, "error": "No se recibio archivo."}, 400
    asientos, errores = _parsear_excel_importacion(f)
    if errores:
        return {"ok": False, "errores": errores}, 400
    if not asientos:
        return {"ok": False, "error": "No hay asientos para importar."}, 400

    creados = 0
    with SessionLocal() as session:
        meses_cerrados = _meses_cerrados_set(session)
        for a in asientos:
            if (a["fecha"].year, a["fecha"].month) in meses_cerrados:
                return {"ok": False, "error": f"El asiento del {a['fecha']} cae en un mes cerrado ({a['fecha'].year}-{a['fecha'].month:02d}). Importacion abortada."}, 400
        try:
            with session.begin():
                for a in asientos:
                    numero = _generar_numero(session, a["fecha"])
                    asiento = Asiento(
                        numero=numero,
                        fecha=a["fecha"],
                        glosa=a["glosa"],
                        moneda="PEN",
                        tipo_cambio=Decimal("1"),
                        numero_documento=a["documento"],
                    )
                    for i, l in enumerate(a["lineas"], start=1):
                        asiento.lineas.append(AsientoLinea(
                            orden=i,
                            cuenta_codigo=l["cuenta_codigo"],
                            glosa_linea=l["glosa_linea"],
                            debe=l["debe"],
                            haber=l["haber"],
                            es_titulo=False,
                        ))
                    session.add(asiento)
                    creados += 1
        except Exception as e:
            return {"ok": False, "error": f"Error al importar: {e}"}, 500
    return {"ok": True, "creados": creados}


@app.route("/cierres")
def cierres_list():
    with SessionLocal() as session:
        rows = session.execute(
            select(CierreMes).order_by(CierreMes.year.desc(), CierreMes.month.desc())
        ).scalars().all()
        cierres = [
            {
                "id": c.id,
                "year": c.year,
                "month": c.month,
                "label": f"{c.year}-{c.month:02d}",
                "cerrado_at": c.cerrado_at,
                "cerrado_por": c.cerrado_por or "",
                "nota": c.nota or "",
            }
            for c in rows
        ]
    hoy = date.today()
    return render_template("cierres.html", cierres=cierres, hoy=hoy)


@app.route("/cierres", methods=["POST"])
def cierres_crear():
    data = request.get_json(silent=True) or {}
    try:
        year = int(data.get("year"))
        month = int(data.get("month"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "year/month invalidos."}, 400
    if not (1 <= month <= 12):
        return {"ok": False, "error": "month fuera de rango."}, 400
    nota = (data.get("nota") or "").strip() or None
    cerrado_por = (data.get("cerrado_por") or "").strip() or None

    primer_dia = date(year, month, 1)
    if primer_dia > date.today().replace(day=1):
        return {"ok": False, "error": "No se puede cerrar un mes futuro."}, 400

    with SessionLocal() as session:
        with session.begin():
            existe = session.execute(
                select(CierreMes).where(CierreMes.year == year, CierreMes.month == month)
            ).scalar_one_or_none()
            if existe:
                return {"ok": False, "error": "Ese mes ya esta cerrado."}, 400
            c = CierreMes(year=year, month=month, cerrado_por=cerrado_por, nota=nota)
            session.add(c)
        return {"ok": True}


@app.route("/cierres/<int:cierre_id>", methods=["DELETE"])
def cierres_reabrir(cierre_id):
    with SessionLocal() as session:
        with session.begin():
            c = session.get(CierreMes, cierre_id)
            if not c:
                return {"ok": False, "error": "Cierre no encontrado."}, 404
            session.delete(c)
        return {"ok": True}


@app.route("/favoritas", methods=["GET"])
def favoritas_list():
    """Lee cuentas marcadas como favoritas (de archivo local)."""
    try:
        with open(os.path.join(BASE_DIR, "favoritas.json"), encoding="utf-8") as f:
            favs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        favs = []
    return {"favoritas": favs}


@app.route("/favoritas", methods=["POST"])
def favoritas_toggle():
    """Agrega/quita una cuenta de favoritas."""
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        return {"ok": False, "error": "Falta codigo."}, 400
    path = os.path.join(BASE_DIR, "favoritas.json")
    try:
        with open(path, encoding="utf-8") as f:
            favs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        favs = []
    if codigo in favs:
        favs.remove(codigo)
        accion = "removed"
    else:
        favs.append(codigo)
        accion = "added"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(favs, f)
    return {"ok": True, "accion": accion, "favoritas": favs}


@app.route("/operaciones/excel")
def operacion_excel():
    """Exporta a Excel una operacion (varios asientos relacionados).
    Params: ids=1,2,3 (lista de ids separados por coma)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    ids_raw = request.args.get("ids", "").strip()
    if not ids_raw:
        abort(400, "Faltan los ids de los asientos.")
    try:
        ids = [int(x) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        abort(400, "ids invalidos.")
    if not ids:
        abort(400, "No hay asientos para exportar.")

    with SessionLocal() as session:
        asientos = [session.get(Asiento, i) for i in ids]
        asientos = [a for a in asientos if a is not None]
        if not asientos:
            abort(404)

        wb = Workbook()
        ws = wb.active
        ws.title = "Libro Diario"

        thin = Side(border_style="thin", color="999999")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        header_fill = PatternFill("solid", fgColor="1E3A5F")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        sep_fill = PatternFill("solid", fgColor="EAF0F7")
        sep_font = Font(bold=True, color="1E3A5F", size=11)
        total_font = Font(bold=True)

        # Titulo de la operacion
        import re
        titulo_op = re.sub(r"^\d+\)\s*[A-Za-z]+\s*-\s*", "", asientos[0].glosa or "") or "Operacion"
        ws["A1"] = "LIBRO DIARIO - FORMATO SUNAT 5.1"
        ws["A1"].font = Font(bold=True, size=14, color="1E3A5F")
        ws.merge_cells("A1:F1")
        ws["A1"].alignment = Alignment(horizontal="center")
        ws["A2"] = f"Operacion: {titulo_op}"
        ws["A2"].font = Font(bold=True, size=11)
        ws.merge_cells("A2:F2")
        tercero = f"  |  Tercero: {asientos[0].ruc_tercero} - {asientos[0].razon_social_tercero}" if asientos[0].ruc_tercero else ""
        ws["A3"] = f"Fecha: {asientos[0].fecha.isoformat()}  |  Documento: {asientos[0].numero_documento or '-'}{tercero}  |  {len(asientos)} asiento(s)"
        ws.merge_cells("A3:F3")
        ws["A3"].font = Font(italic=True, color="666666")

        row = 5
        gran_total_d = Decimal("0")
        gran_total_h = Decimal("0")

        for idx, a in enumerate(asientos, start=1):
            # Separador del sub-asiento
            ws.cell(row=row, column=1, value=f"———  {idx}) {a.glosa}  ———")
            ws.cell(row=row, column=1).font = sep_font
            ws.cell(row=row, column=1).alignment = Alignment(horizontal="center")
            for c in range(1, 7):
                ws.cell(row=row, column=c).fill = sep_fill
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            row += 1

            headers = ["#", "Cuenta", "Descripcion", "Glosa linea", "Debe", "Haber"]
            for c, h in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=c, value=h)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
                cell.border = border
            row += 1

            tot_d = Decimal("0")
            tot_h = Decimal("0")
            for l in a.lineas:
                desc = CUENTAS_POR_CODIGO.get(l.cuenta_codigo, {}).get("descripcion", "")
                ws.cell(row=row, column=1, value=l.orden).border = border
                ws.cell(row=row, column=2, value=l.cuenta_codigo).border = border
                ws.cell(row=row, column=3, value=desc).border = border
                ws.cell(row=row, column=4, value=l.glosa_linea).border = border
                ws.cell(row=row, column=5, value=float(l.debe)).border = border
                ws.cell(row=row, column=5).number_format = "#,##0.00"
                ws.cell(row=row, column=6, value=float(l.haber)).border = border
                ws.cell(row=row, column=6).number_format = "#,##0.00"
                tot_d += l.debe
                tot_h += l.haber
                row += 1

            # Subtotal del asiento
            ws.cell(row=row, column=4, value="Subtotal").font = total_font
            ws.cell(row=row, column=4).alignment = Alignment(horizontal="right")
            ws.cell(row=row, column=5, value=float(tot_d)).font = total_font
            ws.cell(row=row, column=5).number_format = "#,##0.00"
            ws.cell(row=row, column=6, value=float(tot_h)).font = total_font
            ws.cell(row=row, column=6).number_format = "#,##0.00"
            for c in range(4, 7):
                ws.cell(row=row, column=c).border = border
            row += 2
            gran_total_d += tot_d
            gran_total_h += tot_h

        # Gran total
        ws.cell(row=row, column=4, value="TOTAL OPERACION").font = Font(bold=True, size=12, color="1E3A5F")
        ws.cell(row=row, column=4).alignment = Alignment(horizontal="right")
        ws.cell(row=row, column=5, value=float(gran_total_d)).font = Font(bold=True, size=12)
        ws.cell(row=row, column=5).number_format = "#,##0.00"
        ws.cell(row=row, column=6, value=float(gran_total_h)).font = Font(bold=True, size=12)
        ws.cell(row=row, column=6).number_format = "#,##0.00"

        # Anchos de columna
        ws.column_dimensions["A"].width = 5
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 36
        ws.column_dimensions["D"].width = 32
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 14

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", titulo_op)[:40] or "operacion"
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"operacion_{safe_title}_{asientos[0].fecha.isoformat()}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


@app.route("/asientos/<int:asiento_id>/excel")
def asientos_excel(asiento_id):
    from openpyxl import Workbook

    with SessionLocal() as session:
        asiento = session.get(Asiento, asiento_id)
        if not asiento:
            abort(404)
        wb = Workbook()
        ws = wb.active
        ws.title = asiento.numero
        ws.append(["Numero", asiento.numero])
        ws.append(["Fecha", asiento.fecha.isoformat()])
        ws.append(["Glosa", asiento.glosa])
        ws.append(["Moneda", asiento.moneda])
        ws.append([])
        ws.append(["Orden", "Cuenta", "Descripcion", "Glosa linea", "Debe", "Haber"])
        total_debe = Decimal("0")
        total_haber = Decimal("0")
        for l in asiento.lineas:
            desc = CUENTAS_POR_CODIGO.get(l.cuenta_codigo, {}).get("descripcion", "")
            ws.append([l.orden, l.cuenta_codigo, desc, l.glosa_linea, float(l.debe), float(l.haber)])
            total_debe += l.debe
            total_haber += l.haber
        ws.append(["", "", "", "TOTAL", float(total_debe), float(total_haber)])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"asiento_{asiento.numero}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _tipo_doc_sunat(numero_documento: str) -> str:
    """Devuelve el codigo SUNAT Tabla 10 segun el prefijo serie del numero de documento.
    F = 01 Factura, B = 03 Boleta, 07 NC, 08 ND, sino 00."""
    if not numero_documento:
        return ""
    s = numero_documento.strip().upper()
    if s.startswith("F"):
        return "01"
    if s.startswith("B"):
        return "03"
    if s.startswith("FC") or s.startswith("BC") or "NC" in s[:3]:
        return "07"
    if s.startswith("FD") or s.startswith("BD") or "ND" in s[:3]:
        return "08"
    return "00"


def _parse_serie_numero(numero_documento: str):
    """Separa 'F001-2559' -> ('F001', '2559'). Si no hay guion, todo va a 'numero'."""
    if not numero_documento:
        return ("", "")
    s = numero_documento.strip()
    if "-" in s:
        serie, num = s.split("-", 1)
        return (serie.strip(), num.strip())
    return ("", s)


def _registro_compras_ventas(session, year: int, month: int):
    """Construye las filas del Registro de Compras (8.1) y Ventas (14.1) del mes."""
    from calendar import monthrange
    inicio = date(year, month, 1)
    fin = date(year, month, monthrange(year, month)[1])
    rows = session.execute(
        select(Asiento).where(
            Asiento.fecha >= inicio,
            Asiento.fecha <= fin,
            Asiento.reversa_de_id.is_(None),
            Asiento.anulado_por_id.is_(None),
        ).order_by(Asiento.fecha, Asiento.id)
    ).scalars().all()

    # Agrupar por numero_documento + ruc para consolidar los asientos que forman una sola operacion
    compras_grp = {}
    ventas_grp = {}
    for a in rows:
        base = Decimal("0")
        igv = Decimal("0")
        es_compra = False
        es_venta = False
        for l in a.lineas:
            if l.es_titulo:
                continue
            c = l.cuenta_codigo
            if c.startswith("60") or c.startswith("63"):
                base += l.debe
                es_compra = True
            elif c.startswith("70") or c.startswith("75"):
                base += l.haber
                es_venta = True
            if c.startswith("4011") or c.startswith("40111"):
                # IGV: debe para compras, haber para ventas
                igv += (l.debe if l.debe > 0 else l.haber)

        if not (es_compra or es_venta):
            continue
        key = (a.numero_documento or f"__sindoc_{a.id}", a.ruc_tercero or "")
        destino = compras_grp if es_compra else ventas_grp
        if key not in destino:
            serie, num = _parse_serie_numero(a.numero_documento or "")
            destino[key] = {
                "fecha": a.fecha,
                "fecha_venc": None,
                "tipo_doc": _tipo_doc_sunat(a.numero_documento or ""),
                "serie": serie,
                "numero": num,
                "numero_documento": a.numero_documento or "",
                "ruc": a.ruc_tercero or "",
                "razon_social": a.razon_social_tercero or "",
                "base": Decimal("0"),
                "igv": Decimal("0"),
                "exonerado": Decimal("0"),
            }
        destino[key]["base"] += base
        destino[key]["igv"] += igv

    def _finalize(d):
        filas = []
        for i, v in enumerate(sorted(d.values(), key=lambda x: (x["fecha"], x["numero_documento"])), 1):
            v["n"] = i
            v["importe_total"] = v["base"] + v["igv"]
            filas.append(v)
        totales = {
            "base": sum((f["base"] for f in filas), Decimal("0")),
            "igv": sum((f["igv"] for f in filas), Decimal("0")),
            "exonerado": sum((f["exonerado"] for f in filas), Decimal("0")),
            "total": sum((f["importe_total"] for f in filas), Decimal("0")),
        }
        return filas, totales

    compras, totales_c = _finalize(compras_grp)
    ventas, totales_v = _finalize(ventas_grp)
    return {
        "compras": compras,
        "ventas": ventas,
        "totales_compras": totales_c,
        "totales_ventas": totales_v,
    }


@app.route("/reportes/registros")
def reporte_registros():
    """Registro de Compras (8.1) y Ventas (14.1) del periodo (year + month)."""
    try:
        year = int(request.args.get("year", date.today().year))
        month = int(request.args.get("month", date.today().month))
    except ValueError:
        year, month = date.today().year, date.today().month
    if month < 1 or month > 12:
        month = date.today().month

    meses_nombres = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                     "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    with SessionLocal() as session:
        data = _registro_compras_ventas(session, year, month)

    return render_template(
        "registros_mes.html",
        year=year,
        month=month,
        mes_nombre=meses_nombres[month - 1],
        **data,
    )


@app.route("/reportes/registros/excel")
def reporte_registros_excel():
    """Exporta Registros 8.1 y 14.1 a Excel con formato SUNAT."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    try:
        year = int(request.args.get("year", date.today().year))
        month = int(request.args.get("month", date.today().month))
    except ValueError:
        year, month = date.today().year, date.today().month

    meses_nombres = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
                     "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
    with SessionLocal() as session:
        data = _registro_compras_ventas(session, year, month)

    wb = Workbook()
    thin = Side(border_style="thin", color="666666")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    title_font = Font(bold=True, size=13, color="1E3A5F")
    totals_fill = PatternFill("solid", fgColor="EAF0F7")
    totals_font = Font(bold=True, size=10)

    # ===== HOJA 1: COMPRAS 8.1 =====
    ws = wb.active
    ws.title = "8.1 Compras"
    ws["A1"] = f"FORMATO 8.1: REGISTRO DE COMPRAS"
    ws["A1"].font = title_font
    ws.merge_cells("A1:N1")
    ws["A2"] = f"PERIODO: {meses_nombres[month-1]} {year}"
    ws["A2"].font = Font(bold=True, size=10)
    ws.merge_cells("A2:N2")

    headers_c = [
        "N° CORR.", "FECHA EMISION", "FECHA VENC/PAGO",
        "TIPO DOC (T.10)", "N° SERIE", "N° COMPROBANTE",
        "TIPO DOC (T.2)", "N° DOCUMENTO", "RAZON SOCIAL",
        "BASE IMPONIBLE", "IGV", "COMPRAS EXONERADAS",
        "IMPORTE TOTAL", "GLOSA"
    ]
    for col, h in enumerate(headers_c, 1):
        c = ws.cell(row=4, column=col, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    row = 5
    for f in data["compras"]:
        vals = [
            f["n"], f["fecha"].strftime("%d/%m/%Y"),
            f["fecha_venc"].strftime("%d/%m/%Y") if f["fecha_venc"] else "",
            f["tipo_doc"], f["serie"], f["numero"],
            "6" if f["ruc"] else "", f["ruc"], f["razon_social"],
            float(f["base"]), float(f["igv"]), float(f["exonerado"]),
            float(f["importe_total"]), ""
        ]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=v)
            c.border = border
            if col in (10, 11, 12, 13):
                c.number_format = "#,##0.00"
                c.alignment = Alignment(horizontal="right")
            elif col in (1, 2, 3, 4, 5, 6, 7, 8):
                c.alignment = Alignment(horizontal="center")
        row += 1

    # Totales compras
    if data["compras"]:
        ws.cell(row=row, column=9, value="TOTALES:").font = totals_font
        ws.cell(row=row, column=9).alignment = Alignment(horizontal="right")
        for col, key in [(10, "base"), (11, "igv"), (12, "exonerado"), (13, "total")]:
            c = ws.cell(row=row, column=col, value=float(data["totales_compras"][key]))
            c.font = totals_font
            c.fill = totals_fill
            c.number_format = "#,##0.00"
            c.border = border
            c.alignment = Alignment(horizontal="right")

    widths_c = [8, 13, 13, 10, 10, 15, 10, 15, 35, 15, 12, 15, 15, 25]
    for i, w in enumerate(widths_c, 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)].width = w

    # ===== HOJA 2: VENTAS 14.1 =====
    ws2 = wb.create_sheet("14.1 Ventas")
    ws2["A1"] = f"FORMATO 14.1: REGISTRO DE VENTAS E INGRESOS"
    ws2["A1"].font = title_font
    ws2.merge_cells("A1:M1")
    ws2["A2"] = f"PERIODO: {meses_nombres[month-1]} {year}"
    ws2["A2"].font = Font(bold=True, size=10)
    ws2.merge_cells("A2:M2")

    headers_v = [
        "N° CORR.", "FECHA EMISION", "FECHA VENC/PAGO",
        "TIPO DOC (T.10)", "N° SERIE", "NUMERO",
        "TIPO DOC (T.2)", "N° DOCUMENTO", "RAZON SOCIAL",
        "BASE IMPONIBLE", "IGV Y/O IPM",
        "IMPORTE TOTAL", "GLOSA"
    ]
    for col, h in enumerate(headers_v, 1):
        c = ws2.cell(row=4, column=col, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    row = 5
    for f in data["ventas"]:
        vals = [
            f["n"], f["fecha"].strftime("%d/%m/%Y"),
            f["fecha_venc"].strftime("%d/%m/%Y") if f["fecha_venc"] else "",
            f["tipo_doc"], f["serie"], f["numero"],
            "6" if (f["ruc"] and len(f["ruc"]) == 11) else ("1" if f["ruc"] else ""),
            f["ruc"], f["razon_social"],
            float(f["base"]), float(f["igv"]),
            float(f["importe_total"]), ""
        ]
        for col, v in enumerate(vals, 1):
            c = ws2.cell(row=row, column=col, value=v)
            c.border = border
            if col in (10, 11, 12):
                c.number_format = "#,##0.00"
                c.alignment = Alignment(horizontal="right")
            elif col in (1, 2, 3, 4, 5, 6, 7, 8):
                c.alignment = Alignment(horizontal="center")
        row += 1

    if data["ventas"]:
        ws2.cell(row=row, column=9, value="TOTALES:").font = totals_font
        ws2.cell(row=row, column=9).alignment = Alignment(horizontal="right")
        for col, key in [(10, "base"), (11, "igv"), (12, "total")]:
            c = ws2.cell(row=row, column=col, value=float(data["totales_ventas"][key]))
            c.font = totals_font
            c.fill = totals_fill
            c.number_format = "#,##0.00"
            c.border = border
            c.alignment = Alignment(horizontal="right")

    widths_v = [8, 13, 13, 10, 10, 15, 10, 15, 35, 15, 12, 15, 25]
    for i, w in enumerate(widths_v, 1):
        ws2.column_dimensions[chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)].width = w

    # ===== HOJA 3: RESUMEN IGV =====
    ws3 = wb.create_sheet("Resumen IGV")
    ws3["A1"] = f"RESUMEN IGV — {meses_nombres[month-1]} {year}"
    ws3["A1"].font = title_font
    ws3.merge_cells("A1:B1")

    igv_ventas = data["totales_ventas"]["igv"]
    igv_compras = data["totales_compras"]["igv"]
    igv_pagar = igv_ventas - igv_compras

    filas_resumen = [
        ("IGV de Ventas (debito fiscal)", float(igv_ventas)),
        ("IGV de Compras (credito fiscal)", float(igv_compras)),
        ("IGV por pagar (ventas - compras)", float(igv_pagar)),
        ("", ""),
        ("Total Base Ventas", float(data["totales_ventas"]["base"])),
        ("Total Base Compras", float(data["totales_compras"]["base"])),
        ("Utilidad bruta aproximada", float(data["totales_ventas"]["base"] - data["totales_compras"]["base"])),
    ]
    for i, (label, val) in enumerate(filas_resumen, start=3):
        ws3.cell(row=i, column=1, value=label).font = Font(bold=True, size=10)
        c = ws3.cell(row=i, column=2, value=val)
        if isinstance(val, (int, float)):
            c.number_format = "#,##0.00"
            c.alignment = Alignment(horizontal="right")
        if "por pagar" in label.lower() or "Utilidad" in label:
            ws3.cell(row=i, column=1).fill = totals_fill
            c.fill = totals_fill
    ws3.column_dimensions["A"].width = 40
    ws3.column_dimensions["B"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"Registros_{year}_{month:02d}_{meses_nombres[month-1]}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
