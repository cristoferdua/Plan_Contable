"""Configuracion de empresa, PLE, tipo de cambio, asientos de destino,
cierre/apertura del ejercicio y estados financieros."""
import io
import json
import os
from calendar import monthrange
from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request, send_file
from sqlalchemy import select

import sunat
from auth import (ROLES_CIERRE, config_get, config_set, registrar, requiere_rol,
                  snapshot_asiento, usuario_actual)
from db import SessionLocal
from models import Asiento, AsientoLinea, CierreMes

bp = Blueprint("contabilidad", __name__)

# Dependencias que vienen de app.py (se inyectan en init_app para evitar import circular)
_deps = {}

CERO = Decimal("0")
ORIGENES_CIERRE = ("cierre_resultados", "cierre_resultado_59", "cierre_balance")
DESTINO_PREFIJOS = ("62", "63", "64", "65", "66", "67", "68")


class _Abortar(Exception):
    pass


def init_app(app, cuentas_por_codigo, mes_cerrado, generar_numero, validar_ruc):
    _deps.update(cuentas=cuentas_por_codigo, mes_cerrado=mes_cerrado, generar_numero=generar_numero,
                 validar_ruc=validar_ruc)
    app.register_blueprint(bp)


def _cuenta_desc(cod):
    return (_deps["cuentas"].get(cod) or {}).get("descripcion", "")


def _cuenta_movimiento(cod):
    c = _deps["cuentas"].get(cod)
    return bool(c) and (c["nivel"] in (4, 5) or (c.get("hoja") and c["nivel"] >= 3))


def _int_arg(nombre, default):
    try:
        return int(request.args.get(nombre, default))
    except (TypeError, ValueError):
        return default


def empresa():
    return {
        "ruc": config_get("empresa_ruc", "") or "",
        "razon_social": config_get("empresa_razon_social", "") or "",
        "usa_clase9": (config_get("usa_clase9", "0") == "1"),
        "destino": json.loads(config_get("destino_distribucion", "") or '[{"cuenta": "9411", "pct": 100}]'),
        "tasa_igv": config_get("tasa_igv", "18") or "18",
    }


# ======================================================================
# Configuracion de empresa
# ======================================================================

@bp.route("/configuracion")
@requiere_rol("admin")
def configuracion():
    return render_template("configuracion.html", emp=empresa())


@bp.route("/configuracion", methods=["POST"])
@requiere_rol("admin")
def configuracion_guardar():
    d = request.get_json(silent=True) or {}
    ruc = (d.get("ruc") or "").strip()
    if ruc and not _deps["validar_ruc"](ruc):
        return {"ok": False, "error": "RUC de la empresa invalido."}, 400
    distrib = d.get("destino") or []
    total = Decimal("0")
    limpio = []
    for item in distrib:
        cta = (item.get("cuenta") or "").strip()
        try:
            pct = Decimal(str(item.get("pct") or 0))
        except Exception:
            return {"ok": False, "error": "Porcentaje invalido."}, 400
        if not cta:
            continue
        if not cta.startswith("9") or not _cuenta_movimiento(cta):
            return {"ok": False, "error": f"La cuenta de destino {cta} debe ser de la clase 9 y de nivel 4 o 5."}, 400
        total += pct
        limpio.append({"cuenta": cta, "pct": float(pct)})
    usa9 = bool(d.get("usa_clase9"))
    tasa = str(d.get("tasa_igv") or "18").strip()
    if tasa not in ("18", "10.5"):
        return {"ok": False, "error": "Tasa de IGV invalida (18 o 10.5)."}, 400
    if usa9 and (not limpio or total != 100):
        return {"ok": False, "error": "La distribucion de destino debe sumar 100%."}, 400
    antes = empresa()
    with SessionLocal() as s:
        with s.begin():
            config_set(s, "empresa_ruc", ruc)
            config_set(s, "empresa_razon_social", (d.get("razon_social") or "").strip())
            config_set(s, "usa_clase9", "1" if usa9 else "0")
            config_set(s, "destino_distribucion", json.dumps(limpio))
            config_set(s, "tasa_igv", tasa)
            registrar(s, "editar", "config", None, antes=antes, despues=empresa_dict(ruc, d, usa9, limpio))
    return {"ok": True}


def empresa_dict(ruc, d, usa9, limpio):
    return {"ruc": ruc, "razon_social": d.get("razon_social"), "usa_clase9": usa9, "destino": limpio}


# ======================================================================
# Tipo de cambio SUNAT
# ======================================================================

@bp.route("/tipo-cambio")
def tipo_cambio():
    """Tipo de cambio publicado por SUNAT para una fecha (via apis.net.pe).
    Para registrar operaciones en moneda extranjera se usa el de VENTA."""
    import urllib.error
    import urllib.request
    fecha = (request.args.get("fecha") or date.today().isoformat()).strip()
    try:
        date.fromisoformat(fecha)
    except ValueError:
        return {"ok": False, "error": "Fecha invalida."}, 400
    token = os.environ.get("APIS_NET_PE_TOKEN", "").strip()
    if token:
        url = f"https://api.apis.net.pe/v2/sunat/tipo-cambio?date={fecha}"
    else:
        url = f"https://api.apis.net.pe/v1/tipo-cambio-sunat?fecha={fecha}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return {"ok": False, "error": "No se pudo consultar el tipo de cambio. Ingresalo manualmente."}, 502
    venta = data.get("venta", data.get("precioVenta"))
    compra = data.get("compra", data.get("precioCompra"))
    if venta is None:
        return {"ok": False, "error": "SUNAT no publico tipo de cambio para esa fecha."}, 404
    return {"ok": True, "fecha": fecha, "venta": str(venta), "compra": str(compra) if compra is not None else None}


# ======================================================================
# PLE
# ======================================================================

def _asientos_periodo(s, year, month):
    ini = date(year, month, 1)
    fin = date(year, month, monthrange(year, month)[1])
    return s.execute(
        select(Asiento).where(Asiento.fecha >= ini, Asiento.fecha <= fin).order_by(Asiento.fecha, Asiento.id)
    ).scalars().all()


def _validar_periodo_ple(s, asientos, year, month, emp):
    """Observaciones que impedirian o afectarian la presentacion."""
    obs = []
    if not emp["ruc"]:
        obs.append({"nivel": "error", "msg": "Configura el RUC de la empresa (Configuracion) para nombrar los archivos."})
    if not _deps["mes_cerrado"](s, date(year, month, 1)):
        obs.append({"nivel": "aviso", "msg": "El periodo no esta cerrado: los asientos aun pueden cambiar despues de generar el archivo."})
    for a in asientos:
        movs = [l for l in a.lineas if not l.es_titulo]
        d = sum((l.debe for l in movs), CERO)
        h = sum((l.haber for l in movs), CERO)
        if d != h:
            obs.append({"nivel": "error", "msg": f"Asiento {a.numero} no cuadra (debe {d} / haber {h})."})
        for l in movs:
            if not _deps["cuentas"].get(l.cuenta_codigo):
                obs.append({"nivel": "error", "msg": f"Asiento {a.numero}: la cuenta {l.cuenta_codigo} no esta en el plan de cuentas."})
        if a.moneda != "PEN" and any(l.importe_me is None for l in movs):
            obs.append({"nivel": "aviso", "msg": f"Asiento {a.numero} en {a.moneda} sin importe en moneda extranjera."})
    return obs


@bp.route("/ple")
@requiere_rol("admin", "contador")
def ple():
    hoy = date.today()
    year = _int_arg("year", hoy.year)
    month = _int_arg("month", hoy.month)
    if not 1 <= month <= 12:
        month = hoy.month
    emp = empresa()
    with SessionLocal() as s:
        asientos = _asientos_periodo(s, year, month)
        obs = _validar_periodo_ple(s, asientos, year, month, emp)
        n_lineas = sum(1 for a in asientos for l in a.lineas if not l.es_titulo)
        cuentas = {l.cuenta_codigo for a in asientos for l in a.lineas if not l.es_titulo}
    con_info = bool(asientos)
    archivos = [
        {"formato": "5.1", "nombre": "Libro Diario", "registros": n_lineas,
         "archivo": sunat.nombre_archivo(emp["ruc"], year, month, sunat.LIBRO_DIARIO, con_info)},
        {"formato": "5.3", "nombre": "Libro Diario - Detalle del plan contable", "registros": len(cuentas),
         "archivo": sunat.nombre_archivo(emp["ruc"], year, month, sunat.LIBRO_DIARIO_PLAN, con_info)},
        {"formato": "6.1", "nombre": "Libro Mayor", "registros": n_lineas,
         "archivo": sunat.nombre_archivo(emp["ruc"], year, month, sunat.LIBRO_MAYOR, con_info)},
    ]
    return render_template("ple.html", year=year, month=month, archivos=archivos, obs=obs,
                           n_asientos=len(asientos), emp=emp)


@bp.route("/ple/descargar")
@requiere_rol("admin", "contador")
def ple_descargar():
    year = _int_arg("year", date.today().year)
    month = _int_arg("month", date.today().month)
    formato = request.args.get("formato", "5.1")
    if not 1 <= month <= 12 or formato not in ("5.1", "5.3", "6.1"):
        return {"ok": False, "error": "Parametros invalidos."}, 400
    emp = empresa()
    with SessionLocal() as s:
        asientos = _asientos_periodo(s, year, month)
        if formato == "5.1":
            filas = sunat.generar_5_1(asientos, year, month)
            libro = sunat.LIBRO_DIARIO
        elif formato == "6.1":
            filas = sunat.generar_6_1(asientos, year, month)
            libro = sunat.LIBRO_MAYOR
        else:
            usadas = {l.cuenta_codigo for a in asientos for l in a.lineas if not l.es_titulo}
            filas = sunat.generar_5_3(usadas, _deps["cuentas"], year, month)
            libro = sunat.LIBRO_DIARIO_PLAN
        nombre = sunat.nombre_archivo(emp["ruc"], year, month, libro, bool(filas))
        registrar(s, "exportar_ple", "periodo", None,
                  despues={"formato": formato, "periodo": f"{year}-{month:02d}", "archivo": nombre, "registros": len(filas)})
        s.commit()
    return send_file(io.BytesIO(sunat.contenido_archivo(filas)), as_attachment=True,
                     download_name=nombre, mimetype="text/plain")


# ======================================================================
# Saldos
# ======================================================================

def _saldos(s, hasta, desde=None, excluir_asiento_ids=()):
    """{cuenta: debe - haber} acumulado hasta `hasta` (inclusive)."""
    stmt = (
        select(AsientoLinea.cuenta_codigo, AsientoLinea.debe, AsientoLinea.haber, Asiento.id)
        .join(Asiento, Asiento.id == AsientoLinea.asiento_id)
        .where(Asiento.fecha <= hasta, AsientoLinea.es_titulo.is_(False))
    )
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    out = {}
    excl = set(excluir_asiento_ids)
    for cod, d, h, aid in s.execute(stmt).all():
        if aid in excl:
            continue
        out[cod] = out.get(cod, CERO) + Decimal(d) - Decimal(h)
    return {k: v for k, v in out.items() if v != 0}


def _es_resultado(cod):
    return cod[0] in "679" or (cod[0] == "8" and not cod.startswith("89"))


def _ids_cierre(s, year):
    return [a for a in s.execute(
        select(Asiento.id).where(Asiento.origen.in_(ORIGENES_CIERRE),
                                 Asiento.fecha == date(year, 12, 31),
                                 Asiento.anulado_por_id.is_(None))
    ).scalars().all()]


# ======================================================================
# Asientos de destino (clase 9 / 79)
# ======================================================================

def _estado_destino_mes(s, year, month):
    ini = date(year, month, 1)
    fin = date(year, month, monthrange(year, month)[1])
    filas = s.execute(
        select(AsientoLinea.cuenta_codigo, AsientoLinea.debe, AsientoLinea.haber, Asiento.origen)
        .join(Asiento, Asiento.id == AsientoLinea.asiento_id)
        .where(Asiento.fecha >= ini, Asiento.fecha <= fin, AsientoLinea.es_titulo.is_(False))
    ).all()
    gasto = CERO
    destinado = CERO
    for cod, d, h, origen in filas:
        if origen is None and cod.startswith(DESTINO_PREFIJOS):
            gasto += Decimal(d) - Decimal(h)
        elif cod.startswith("79"):
            destinado += Decimal(h) - Decimal(d)
    return gasto, destinado


@bp.route("/ejercicio/destino", methods=["POST"])
@requiere_rol(*ROLES_CIERRE)
def generar_destino():
    """Genera (o completa) el asiento de destino del mes: Debe 9x / Haber 79
    por la diferencia entre los gastos 62-68 del mes y lo ya destinado."""
    d = request.get_json(silent=True) or {}
    try:
        year, month = int(d.get("year")), int(d.get("month"))
        date(year, month, 1)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Periodo invalido."}, 400
    emp = empresa()
    if not emp["usa_clase9"]:
        return {"ok": False, "error": "La empresa no usa cuentas de la clase 9 (ver Configuracion)."}, 400
    fecha = min(date(year, month, monthrange(year, month)[1]), date.today())
    if fecha < date(year, month, 1):
        return {"ok": False, "error": "No se puede generar destino de un mes futuro."}, 400
    with SessionLocal() as s:
        with s.begin():
            if _deps["mes_cerrado"](s, fecha):
                return {"ok": False, "error": f"El mes {year}-{month:02d} esta cerrado."}, 400
            gasto, destinado = _estado_destino_mes(s, year, month)
            delta = gasto - destinado
            if delta == 0:
                return {"ok": True, "mensaje": "El destino del mes ya esta completo.", "id": None}
            monto = abs(delta)
            a = Asiento(
                numero=_deps["generar_numero"](s, fecha), fecha=fecha,
                glosa=f"Asiento de destino {year}-{month:02d} (gastos 62-68 a clase 9)",
                moneda="PEN", tipo_cambio=Decimal("1"), codigo_libro="05",
                tipo_asiento="M", origen="destino", creado_por=usuario_actual(),
            )
            orden = 1
            asignado = CERO
            distrib = emp["destino"]
            for i, item in enumerate(distrib):
                if i == len(distrib) - 1:
                    parte = monto - asignado
                else:
                    parte = (monto * Decimal(str(item["pct"])) / 100).quantize(Decimal("0.01"))
                asignado += parte
                if parte == 0:
                    continue
                a.lineas.append(AsientoLinea(
                    orden=orden, cuenta_codigo=item["cuenta"], glosa_linea="Destino de gastos",
                    debe=parte if delta > 0 else CERO, haber=CERO if delta > 0 else parte))
                orden += 1
            a.lineas.append(AsientoLinea(
                orden=orden, cuenta_codigo="7911", glosa_linea="Cargas imputables a cuentas de costos y gastos",
                debe=CERO if delta > 0 else monto, haber=monto if delta > 0 else CERO))
            s.add(a)
            s.flush()
            registrar(s, "crear", "asiento", a.id, despues=snapshot_asiento(a), motivo="Destino automatico")
            out = {"ok": True, "id": a.id, "numero": a.numero, "monto": str(delta)}
        return out


# ======================================================================
# Cierre y apertura del ejercicio
# ======================================================================

def _cierre_existente(s, year):
    return s.execute(
        select(Asiento).where(Asiento.origen == "cierre_resultados",
                              Asiento.fecha == date(year, 12, 31),
                              Asiento.anulado_por_id.is_(None))
    ).scalars().first()


def _nuevo_asiento(s, fecha, glosa, tipo, origen):
    return Asiento(
        numero=_deps["generar_numero"](s, fecha), fecha=fecha, glosa=glosa, moneda="PEN",
        tipo_cambio=Decimal("1"), codigo_libro="05", tipo_asiento=tipo, origen=origen,
        creado_por=usuario_actual(),
    )


def _agregar_lineas_saldo(a, saldos, glosa, invertir=True):
    """Agrega lineas que cancelan (invertir=True) o reabren cada saldo."""
    orden = len(a.lineas) + 1
    for cod in sorted(saldos):
        v = saldos[cod]
        if v == 0:
            continue
        deudor = v > 0
        if invertir:
            deudor = not deudor
        a.lineas.append(AsientoLinea(orden=orden, cuenta_codigo=cod, glosa_linea=glosa,
                                     debe=abs(v) if deudor else CERO, haber=CERO if deudor else abs(v)))
        orden += 1


@bp.route("/ejercicio/cierre", methods=["POST"])
@requiere_rol(*ROLES_CIERRE)
def cerrar_ejercicio():
    """Genera al 31/12: (1) cierre de cuentas de resultado contra 89,
    (2) traslado del resultado de 89 a 59, (3) cierre de cuentas de balance;
    y al 01/01 del anio siguiente (4) el asiento de apertura."""
    d = request.get_json(silent=True) or {}
    try:
        year = int(d.get("year"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Anio invalido."}, 400
    fin = date(year, 12, 31)
    apertura_f = date(year + 1, 1, 1)
    if fin >= date.today():
        return {"ok": False, "error": f"El ejercicio {year} aun no termina."}, 400
    try:
        with SessionLocal() as s:
            with s.begin():
                if _cierre_existente(s, year):
                    raise _Abortar(f"El ejercicio {year} ya esta cerrado.")
                if _deps["mes_cerrado"](s, fin):
                    raise _Abortar(f"Diciembre {year} esta cerrado: reabrelo para registrar los asientos de cierre.")
                if _deps["mes_cerrado"](s, apertura_f):
                    raise _Abortar(f"Enero {year + 1} esta cerrado: no se puede registrar la apertura.")
                previos = s.execute(select(Asiento.id).where(Asiento.fecha < date(year, 1, 1)).limit(1)).first()
                if previos and not _cierre_existente(s, year - 1):
                    raise _Abortar(f"Primero cierra el ejercicio {year - 1}: hay asientos anteriores a {year}.")
                emp = empresa()
                if emp["usa_clase9"]:
                    pendientes = []
                    for m in range(1, 13):
                        g, dd = _estado_destino_mes(s, year, m)
                        if g != dd:
                            pendientes.append(f"{m:02d}")
                    if pendientes:
                        raise _Abortar("Faltan asientos de destino en los meses: " + ", ".join(pendientes) + ".")

                saldos = _saldos(s, fin)
                if not saldos:
                    raise _Abortar(f"No hay saldos en el ejercicio {year}.")

                # (1) Cierre de cuentas de resultado
                res = {k: v for k, v in saldos.items() if _es_resultado(k)}
                resultado = -sum(res.values(), CERO)  # positivo = utilidad
                c1 = _nuevo_asiento(s, fin, f"Cierre de cuentas de resultado del ejercicio {year}", "C", "cierre_resultados")
                _agregar_lineas_saldo(c1, res, "Cierre de cuentas de resultado")
                if resultado != 0:
                    cta89 = "8911" if resultado > 0 else "8921"
                    c1.lineas.append(AsientoLinea(
                        orden=len(c1.lineas) + 1, cuenta_codigo=cta89,
                        glosa_linea="Utilidad del ejercicio" if resultado > 0 else "Perdida del ejercicio",
                        debe=CERO if resultado > 0 else -resultado, haber=resultado if resultado > 0 else CERO))
                if len(c1.lineas) >= 2:
                    s.add(c1)
                    s.flush()
                    registrar(s, "crear", "asiento", c1.id, despues=snapshot_asiento(c1), motivo=f"Cierre del ejercicio {year}")

                # (2) Traslado de 89 a 59
                if resultado != 0:
                    c2 = _nuevo_asiento(s, fin, f"Traslado del resultado {year} a resultados acumulados", "C", "cierre_resultado_59")
                    if resultado > 0:
                        c2.lineas += [
                            AsientoLinea(orden=1, cuenta_codigo="8911", glosa_linea="Utilidad del ejercicio", debe=resultado, haber=CERO),
                            AsientoLinea(orden=2, cuenta_codigo="5911", glosa_linea="Utilidades acumuladas", debe=CERO, haber=resultado),
                        ]
                    else:
                        perd = -resultado
                        c2.lineas += [
                            AsientoLinea(orden=1, cuenta_codigo="5921", glosa_linea="Perdidas acumuladas", debe=perd, haber=CERO),
                            AsientoLinea(orden=2, cuenta_codigo="8921", glosa_linea="Perdida del ejercicio", debe=CERO, haber=perd),
                        ]
                    s.add(c2)
                    s.flush()
                    registrar(s, "crear", "asiento", c2.id, despues=snapshot_asiento(c2), motivo=f"Cierre del ejercicio {year}")

                # (3) Cierre de cuentas de balance y (4) apertura
                balance = {k: v for k, v in _saldos(s, fin).items() if k[0] in "12345"}
                if sum(balance.values(), CERO) != 0:
                    raise _Abortar("Las cuentas de balance no cuadran despues del cierre de resultados; revisa los asientos.")
                ids = []
                if balance:
                    c3 = _nuevo_asiento(s, fin, f"Cierre de cuentas de balance del ejercicio {year}", "C", "cierre_balance")
                    _agregar_lineas_saldo(c3, balance, "Cierre de cuentas de balance")
                    s.add(c3)
                    s.flush()
                    registrar(s, "crear", "asiento", c3.id, despues=snapshot_asiento(c3), motivo=f"Cierre del ejercicio {year}")

                    ap = _nuevo_asiento(s, apertura_f, f"Asiento de apertura del ejercicio {year + 1}", "A", "apertura")
                    _agregar_lineas_saldo(ap, balance, "Saldo inicial", invertir=False)
                    s.add(ap)
                    s.flush()
                    registrar(s, "crear", "asiento", ap.id, despues=snapshot_asiento(ap), motivo=f"Apertura del ejercicio {year + 1}")
                    ids = [c3.id, ap.id]
                out = {"ok": True, "resultado": str(resultado), "asientos": ids}
    except _Abortar as e:
        return {"ok": False, "error": str(e)}, 400
    return out


@bp.route("/ejercicio")
@requiere_rol("admin", "contador")
def ejercicio():
    hoy = date.today()
    year = _int_arg("year", hoy.year)
    emp = empresa()
    with SessionLocal() as s:
        meses = []
        for m in range(1, 13):
            if date(year, m, 1) > hoy:
                break
            g, dd = _estado_destino_mes(s, year, m)
            meses.append({"month": m, "gasto": g, "destinado": dd, "pendiente": g - dd,
                          "cerrado": _deps["mes_cerrado"](s, date(year, m, 1))})
        cierre = _cierre_existente(s, year)
        cierre_info = {"id": cierre.id, "numero": cierre.numero} if cierre else None
        hasta = min(date(year, 12, 31), hoy)
        res = {k: v for k, v in _saldos(s, hasta, excluir_asiento_ids=_ids_cierre(s, year)).items() if _es_resultado(k)}
        resultado = -sum(res.values(), CERO)
    return render_template("ejercicio.html", year=year, meses=meses, emp=emp, cierre=cierre_info,
                           resultado=resultado, puede_cerrar=date(year, 12, 31) < hoy)


# ======================================================================
# Estados financieros
# ======================================================================

ESF_ACTIVO = [
    ("Activo corriente", [
        ("Efectivo y equivalentes de efectivo", ["10"]),
        ("Inversiones financieras", ["11"]),
        ("Cuentas por cobrar comerciales", ["12", "13"]),
        ("Otras cuentas por cobrar", ["14", "15", "16", "17"]),
        ("Servicios y otros contratados por anticipado", ["18"]),
        ("Estimacion de cuentas de cobranza dudosa", ["19"]),
        ("Inventarios", ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29"]),
    ]),
    ("Activo no corriente", [
        ("Activos financieros y propiedades de inversion", ["30", "31"]),
        ("Activos por derecho de uso", ["32"]),
        ("Propiedades, planta y equipo", ["33"]),
        ("Intangibles", ["34"]),
        ("Activos biologicos", ["35"]),
        ("Desvalorizacion de activo inmovilizado", ["36"]),
        ("Activo diferido", ["37"]),
        ("Otros activos", ["38"]),
        ("Depreciacion y amortizacion acumulada", ["39"]),
    ]),
]
ESF_PASIVO = [
    ("Pasivo", [
        ("Tributos y aportes por pagar", ["40"]),
        ("Remuneraciones y participaciones por pagar", ["41"]),
        ("Cuentas por pagar comerciales", ["42", "43"]),
        ("Cuentas por pagar a accionistas y directores", ["44"]),
        ("Obligaciones financieras", ["45"]),
        ("Cuentas por pagar diversas", ["46", "47"]),
        ("Provisiones", ["48"]),
        ("Pasivo diferido", ["49"]),
    ]),
    ("Patrimonio", [
        ("Capital", ["50"]),
        ("Acciones de inversion", ["51"]),
        ("Capital adicional", ["52"]),
        ("Resultados no realizados", ["56"]),
        ("Excedente de revaluacion", ["57"]),
        ("Reservas", ["58"]),
        ("Resultados acumulados", ["59"]),
    ]),
]

ER_NATURALEZA = [
    ("Ventas netas", ["70", "74"], 1),
    ("Otros ingresos de gestion", ["75"], 1),
    ("Variacion de la produccion y produccion inmovilizada", ["71", "72"], 1),
    ("Compras y variacion de existencias", ["60", "61"], 1),
    ("Costo de ventas", ["69"], 1),
    ("Gastos de personal", ["62"], 1),
    ("Servicios prestados por terceros", ["63"], 1),
    ("Gastos por tributos", ["64"], 1),
    ("Otros gastos de gestion", ["65"], 1),
    ("Perdida por medicion de activos a valor razonable", ["66"], 1),
    ("Valuacion, deterioro y provisiones", ["68"], 1),
    ("Descuentos, rebajas y bonificaciones obtenidos", ["73"], 1),
    ("Ganancia por medicion de activos a valor razonable", ["76"], 1),
    ("Ingresos financieros", ["77"], 1),
    ("Cargas cubiertas por provisiones", ["78"], 1),
    ("Gastos financieros", ["67"], 1),
]
ER_IMPUESTOS = [("Participaciones e impuesto a la renta", ["80", "81", "82", "83", "84", "85", "86", "87", "88"])]

ER_FUNCION = [
    ("Ventas netas", ["70", "74"]),
    ("Costo de ventas", ["69"]),
    ("UTILIDAD BRUTA", None),
    ("Gastos de administracion", ["94"]),
    ("Gastos de ventas", ["95"]),
    ("Otros ingresos operativos", ["73", "75", "76", "78"]),
    ("RESULTADO DE OPERACION", None),
    ("Ingresos financieros", ["77"]),
    ("Gastos financieros", ["97"]),
    ("Otros gastos (no destinados)", ["91", "92", "93", "96", "98", "99"]),
    ("RESULTADO ANTES DE IMPUESTOS", None),
    ("Participaciones e impuesto a la renta", ["80", "81", "82", "83", "84", "85", "86", "87", "88"]),
    ("RESULTADO DEL EJERCICIO", None),
]


def _suma(saldos, prefijos):
    return sum((v for k, v in saldos.items() if k[:2] in prefijos), CERO)


def _estados(s, year, hasta):
    excl = _ids_cierre(s, year)
    acumulado = _saldos(s, hasta, excluir_asiento_ids=excl)
    del_anio = _saldos(s, hasta, desde=date(year, 1, 1), excluir_asiento_ids=excl)

    # Estado de Situacion Financiera (saldos acumulados)
    def secciones(definicion, signo):
        out = []
        for titulo, rubros in definicion:
            filas = [{"nombre": n, "cuentas": ", ".join(p), "monto": signo * _suma(acumulado, p)} for n, p in rubros]
            filas = [f for f in filas if f["monto"] != 0]
            out.append({"titulo": titulo, "filas": filas, "total": sum((f["monto"] for f in filas), CERO)})
        return out
    activo = secciones(ESF_ACTIVO, 1)
    pasivo_pat = secciones(ESF_PASIVO, -1)
    resultado_acum = -sum((v for k, v in acumulado.items() if _es_resultado(k)), CERO)
    pasivo_pat[1]["filas"].append({"nombre": "Resultado del ejercicio", "cuentas": "6, 7, 8, 9", "monto": resultado_acum})
    pasivo_pat[1]["total"] += resultado_acum
    total_activo = sum((x["total"] for x in activo), CERO)
    total_pp = sum((x["total"] for x in pasivo_pat), CERO)

    # Estado de Resultados por naturaleza (solo movimientos del ejercicio)
    er = []
    for nombre, pref, _ in ER_NATURALEZA:
        v = -_suma(del_anio, pref)
        if v != 0:
            er.append({"nombre": nombre, "cuentas": ", ".join(pref), "monto": v})
    antes_imp = sum((f["monto"] for f in er), CERO)
    imp = -_suma(del_anio, ER_IMPUESTOS[0][1])
    resultado = antes_imp + imp

    # Estado de Resultados por funcion
    erf = []
    acum = CERO
    for nombre, pref in ER_FUNCION:
        if pref is None:
            erf.append({"nombre": nombre, "monto": acum, "subtotal": True})
        else:
            v = -_suma(del_anio, pref)
            acum += v
            if v != 0:
                erf.append({"nombre": nombre, "cuentas": ", ".join(pref), "monto": v, "subtotal": False})
    return {
        "activo": activo, "pasivo_pat": pasivo_pat, "total_activo": total_activo, "total_pp": total_pp,
        "cuadra": total_activo == total_pp,
        "er": er, "antes_imp": antes_imp, "impuestos": imp, "resultado": resultado,
        "erf": erf, "usa_funcion": any(k[:2] in ("69", "94", "95", "97") for k in del_anio),
    }


@bp.route("/reportes/estados-financieros")
def estados_financieros():
    hoy = date.today()
    year = _int_arg("year", hoy.year)
    hasta_raw = request.args.get("hasta", "").strip()
    try:
        hasta = date.fromisoformat(hasta_raw) if hasta_raw else min(date(year, 12, 31), hoy)
    except ValueError:
        hasta = min(date(year, 12, 31), hoy)
    if hasta.year != year:
        hasta = min(date(year, 12, 31), hoy)
    with SessionLocal() as s:
        data = _estados(s, year, hasta)
    return render_template("estados_financieros.html", year=year, hasta=hasta, emp=empresa(), **data)
