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
from models import Asiento, AsientoLinea

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


def _generar_numero(session: Session, fecha: date) -> str:
    prefijo = f"{fecha.year:04d}-{fecha.month:02d}-"
    stmt = select(func.count()).select_from(Asiento).where(Asiento.numero.like(prefijo + "%"))
    siguiente = session.execute(stmt).scalar_one() + 1
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
    with SessionLocal() as session:
        rows = session.execute(
            select(Asiento).order_by(Asiento.fecha.desc(), Asiento.id.desc()).limit(500)
        ).scalars().all()

        # Agrupar asientos relacionados: misma fecha + mismo documento (o misma glosa base si no hay doc).
        def grupo_key(a):
            doc = (a.numero_documento or "").strip()
            if doc:
                return ("doc", a.fecha.isoformat(), doc)
            # fallback: glosa base (sin el "1) Provision - " prefix)
            glosa = (a.glosa or "").strip()
            # quitar prefijos "1) ", "2) " etc.
            import re
            glosa_base = re.sub(r"^\d+\)\s*[A-Za-z]+\s*-\s*", "", glosa)
            return ("glosa", a.fecha.isoformat(), glosa_base or f"solo-{a.id}")

        grupos = {}
        orden_grupos = []
        for a in rows:
            k = grupo_key(a)
            if k not in grupos:
                grupos[k] = []
                orden_grupos.append(k)
            grupos[k].append(a)

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
            operaciones.append({
                "key": "|".join(k),
                "titulo": titulo,
                "fecha": asientos[0].fecha,
                "n_asientos": len(asientos),
                "numero_documento": asientos[0].numero_documento,
                "numero_correlativo_base": (asientos[0].numero_correlativo or "").split("-")[0] if asientos[0].numero_correlativo else "",
                "total_debe": total_debe,
                "asientos": asientos,
                "ids": [a.id for a in asientos],
            })
    return render_template("asientos_listado.html", operaciones=operaciones)


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
            for aid in ids:
                a = session.get(Asiento, aid)
                if not a or a.anulado_por_id:
                    continue
                for l in list(a.lineas):
                    session.delete(l)
                session.delete(a)
                eliminados += 1
        return {"ok": True, "eliminados": eliminados}


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

        with session.begin():
            a.fecha = fecha_obj
            a.glosa = (payload.get("glosa") or "").strip()
            a.moneda = (payload.get("moneda") or "PEN").strip().upper()
            a.tipo_cambio = tipo_cambio
            a.codigo_libro = (payload.get("codigo_libro") or "").strip() or None
            a.numero_correlativo = (payload.get("numero_correlativo") or "").strip() or None
            a.numero_documento = (payload.get("numero_documento") or "").strip() or None
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
        for a in asientos_mes:
            for l in a.lineas:
                if l.cuenta_codigo.startswith("70") or l.cuenta_codigo.startswith("75"):
                    ventas_mes += l.haber
                elif l.cuenta_codigo.startswith("60") or l.cuenta_codigo.startswith("63"):
                    compras_mes += l.debe

    return render_template(
        "dashboard.html",
        total_asientos=total_asientos,
        asientos_mes=len(asientos_mes),
        total_movido_mes=total_movido_mes,
        ultima_op=ultima_op,
        ultima_glosa=ultima_glosa,
        ventas_mes=ventas_mes,
        compras_mes=compras_mes,
        hoy=hoy,
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
        ws["A3"] = f"Fecha: {asientos[0].fecha.isoformat()}  |  Documento: {asientos[0].numero_documento or '-'}  |  {len(asientos)} asiento(s)"
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
