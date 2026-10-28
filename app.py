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
LIMIT = 500
TOLERANCIA = Decimal("0.01")
NIVELES_MOVIMIENTO = {4, 5}

SINONIMOS = {
    "luz": "energia electrica",
    "electricidad": "energia electrica",
    "planilla": "remuneraciones",
    "sueldos": "remuneraciones",
    "salario": "remuneraciones",
    "afp": "administradoras de fondos de pensiones",
    "pension": "administradoras de fondos de pensiones",
    "jubilacion": "pensiones y jubilaciones",
    "gasolina": "combustibles",
    "petroleo": "combustibles",
    "diesel": "combustibles",
    "flete": "transporte",
    "caja chica": "fondos fijos",
    "banco": "cuentas corrientes en instituciones financieras",
    "cliente": "cuentas por cobrar comerciales",
    "clientes": "cuentas por cobrar comerciales",
    "proveedor": "cuentas por pagar comerciales",
    "proveedores": "cuentas por pagar comerciales",
    "detraccion": "fondos sujetos a restriccion",
    "detracciones": "fondos sujetos a restriccion",
    "renta": "impuesto a las ganancias",
    "iva": "impuesto general a las ventas",
    "utilidad": "resultados acumulados",
    "utilidades": "resultados acumulados",
    "celular": "telefono",
    "cts": "compensacion por tiempo de servicios",
    "gratificacion": "gratificaciones por pagar",
    "mercaderia": "mercaderias",
    "deuda": "obligaciones financieras",
    "prestamo": "obligaciones financieras",
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


def buscar_cuentas(q, elemento):
    base = CUENTAS
    if elemento:
        base = [c for c in base if str(c["elemento"]) == elemento]

    if not q:
        return base[:LIMIT]

    qn = normalizar(q)
    terminos = [qn]
    if qn in SINONIMOS:
        terminos.append(normalizar(SINONIMOS[qn]))

    exactos = []
    vistos = set()
    for c in base:
        if c["codigo"] in vistos:
            continue
        if any(t in c["_norm"] or t in c["codigo"] for t in terminos):
            exactos.append(c)
            vistos.add(c["codigo"])
    if exactos or len(qn) < 3:
        return exactos[:LIMIT]

    puntuados = ((fuzz.partial_ratio(qn, c["_norm"]), c) for c in base)
    difusos = sorted(
        (x for x in puntuados if x[0] >= FUZZY_THRESHOLD),
        key=lambda x: -x[0],
    )
    return [c for _, c in difusos][:LIMIT]


def to_json(c):
    return {
        "codigo": c["codigo"],
        "descripcion": c["descripcion"],
        "nivel": c["nivel"],
        "elemento": c["elemento"],
        "elemento_nombre": c["elemento_nombre"],
    }


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    elemento = request.args.get("elemento", "").strip()
    resultados = buscar_cuentas(q, elemento)

    return render_template(
        "index.html",
        resultados=resultados,
        elementos=ELEMENTOS,
        q=q,
        elemento_sel=elemento,
        total=len(resultados),
    )


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip()
    elemento = request.args.get("elemento", "").strip()
    solo_mov = request.args.get("solo_movimiento", "").strip() == "1"
    resultados = buscar_cuentas(q, elemento)
    if solo_mov:
        resultados = [c for c in resultados if c["nivel"] in NIVELES_MOVIMIENTO]
    return {
        "total": len(resultados),
        "resultados": [to_json(c) for c in resultados],
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
            select(Asiento).order_by(Asiento.fecha.desc(), Asiento.id.desc()).limit(200)
        ).scalars().all()
        totales = {}
        for a in rows:
            td = sum((l.debe for l in a.lineas), Decimal("0"))
            totales[a.id] = td
    return render_template("asientos_listado.html", asientos=rows, totales=totales)


@app.route("/asientos/nuevo")
def asientos_nuevo():
    return render_template(
        "asiento_form.html",
        hoy=date.today().isoformat(),
        elementos=ELEMENTOS,
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
