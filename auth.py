"""Usuarios, sesiones, roles y bitacora de auditoria."""
import json
import secrets
from datetime import datetime
from functools import wraps

from flask import (Blueprint, abort, g, redirect, render_template, request,
                   session as flask_session, url_for)
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from db import SessionLocal
from models import Auditoria, Config, Usuario

bp = Blueprint("auth", __name__)

ROLES = {
    "admin": "Administrador",
    "contador": "Contador",
    "asistente": "Asistente",
    "lectura": "Solo lectura",
}
ROLES_ESCRITURA = {"admin", "contador", "asistente"}
ROLES_CIERRE = {"admin", "contador"}

# Endpoints accesibles sin sesion
PUBLICOS = {"auth.login", "auth.setup", "static"}


# ---------------------------------------------------------------- Config util

def config_get(clave, default=None):
    with SessionLocal() as s:
        row = s.get(Config, clave)
        return row.valor if row and row.valor is not None else default


def config_set(s, clave, valor):
    row = s.get(Config, clave)
    if row:
        row.valor = valor
    else:
        s.add(Config(clave=clave, valor=valor))


def _secret_key():
    """SECRET_KEY de entorno; si no hay, se genera una y se guarda en la BD
    para que las sesiones sobrevivan reinicios."""
    import os
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env
    with SessionLocal() as s:
        with s.begin():
            row = s.get(Config, "secret_key")
            if not row:
                row = Config(clave="secret_key", valor=secrets.token_hex(32))
                s.add(row)
            return row.valor


# ---------------------------------------------------------------- Auditoria

def usuario_actual():
    u = getattr(g, "usuario", None)
    return u["username"] if u else None


def registrar(session, accion, entidad, entidad_id=None, antes=None, despues=None, motivo=None):
    """Inserta un registro en la bitacora dentro de la transaccion `session`."""
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64]
    except RuntimeError:
        ip = None
    session.add(Auditoria(
        usuario=usuario_actual(),
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        motivo=(motivo or None) and motivo[:500],
        antes=json.dumps(antes, default=str, ensure_ascii=False) if antes is not None else None,
        despues=json.dumps(despues, default=str, ensure_ascii=False) if despues is not None else None,
        ip=ip,
    ))


def snapshot_asiento(a):
    cols = [c.name for c in a.__table__.columns]
    data = {c: getattr(a, c) for c in cols}
    data["lineas"] = [
        {
            "orden": l.orden, "cuenta": l.cuenta_codigo, "glosa": l.glosa_linea,
            "debe": str(l.debe), "haber": str(l.haber), "importe_me": str(l.importe_me) if l.importe_me is not None else None,
            "es_titulo": l.es_titulo,
        }
        for l in a.lineas
    ]
    return data


# ---------------------------------------------------------------- Guardas

def requiere_rol(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = getattr(g, "usuario", None)
            if not u or u["rol"] not in roles:
                return _denegado()
            return fn(*a, **kw)
        return wrapper
    return deco


def _es_api():
    return request.method != "GET" or request.is_json or request.path.startswith(("/buscar", "/dashboard/data", "/sunat/"))


def _denegado():
    msg = "No tienes permisos para esta accion."
    if _es_api():
        return {"ok": False, "error": msg, "errores": [msg]}, 403
    abort(403)


def init_app(app):
    app.secret_key = _secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 10,
    )
    app.register_blueprint(bp)

    @app.before_request
    def _cargar_usuario():
        g.usuario = None
        uid = flask_session.get("uid")
        if uid:
            with SessionLocal() as s:
                u = s.get(Usuario, uid)
                if u and u.activo:
                    g.usuario = {"id": u.id, "username": u.username, "nombre": u.nombre or u.username, "rol": u.rol}
        if request.endpoint in PUBLICOS:
            return None
        if not g.usuario:
            if _es_api():
                return {"ok": False, "error": "Sesion expirada. Vuelve a iniciar sesion."}, 401
            return redirect(url_for("auth.login", next=request.full_path))
        # Usuarios de solo lectura no pueden modificar nada
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.endpoint != "auth.logout":
            if g.usuario["rol"] not in ROLES_ESCRITURA:
                return _denegado()
            # Proteccion CSRF basica: las mutaciones via fetch deben venir del mismo origen
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                return {"ok": False, "error": "Origen no permitido."}, 403
        return None

    @app.context_processor
    def _ctx():
        return {"usuario_actual": getattr(g, "usuario", None), "ROLES": ROLES}


# ---------------------------------------------------------------- Rutas

def _hay_usuarios():
    with SessionLocal() as s:
        return (s.execute(select(func.count(Usuario.id))).scalar() or 0) > 0


def _next_seguro(nxt):
    if nxt and nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return "/"


@bp.route("/login", methods=["GET", "POST"])
def login():
    if not _hay_usuarios():
        return redirect(url_for("auth.setup"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        with SessionLocal() as s:
            with s.begin():
                u = s.execute(select(Usuario).where(Usuario.username == username)).scalar_one_or_none()
                if u and u.activo and check_password_hash(u.password_hash, password):
                    u.ultimo_login = datetime.utcnow()
                    flask_session.clear()
                    flask_session["uid"] = u.id
                    flask_session.permanent = True
                    g.usuario = {"username": u.username}
                    registrar(s, "login", "usuario", u.id)
                    return redirect(_next_seguro(request.args.get("next")))
        error = "Usuario o contrasena incorrectos."
    return render_template("login.html", error=error, modo="login")


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """Primer uso: crea el usuario administrador."""
    if _hay_usuarios():
        return redirect(url_for("auth.login"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        nombre = (request.form.get("nombre") or "").strip()
        password = request.form.get("password") or ""
        if len(username) < 3 or len(password) < 8:
            error = "Usuario de al menos 3 caracteres y contrasena de al menos 8."
        else:
            with SessionLocal() as s:
                with s.begin():
                    u = Usuario(username=username, nombre=nombre or username, rol="admin",
                                password_hash=generate_password_hash(password))
                    s.add(u)
                    s.flush()
                    g.usuario = {"username": username}
                    registrar(s, "crear", "usuario", u.id, despues={"username": username, "rol": "admin"})
                    uid = u.id
            flask_session.clear()
            flask_session["uid"] = uid
            return redirect("/")
    return render_template("login.html", error=error, modo="setup")


@bp.route("/logout", methods=["POST", "GET"])
def logout():
    flask_session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/usuarios")
@requiere_rol("admin")
def usuarios():
    with SessionLocal() as s:
        rows = s.execute(select(Usuario).order_by(Usuario.username)).scalars().all()
        lista = [{"id": u.id, "username": u.username, "nombre": u.nombre, "rol": u.rol,
                  "activo": u.activo, "ultimo_login": u.ultimo_login} for u in rows]
    return render_template("usuarios.html", usuarios=lista)


@bp.route("/usuarios", methods=["POST"])
@requiere_rol("admin")
def usuarios_crear():
    d = request.get_json(silent=True) or {}
    username = (d.get("username") or "").strip().lower()
    password = d.get("password") or ""
    rol = d.get("rol") or "asistente"
    if len(username) < 3 or len(password) < 8:
        return {"ok": False, "error": "Usuario >= 3 caracteres y contrasena >= 8."}, 400
    if rol not in ROLES:
        return {"ok": False, "error": "Rol invalido."}, 400
    with SessionLocal() as s:
        with s.begin():
            if s.execute(select(Usuario).where(Usuario.username == username)).scalar_one_or_none():
                return {"ok": False, "error": "Ese usuario ya existe."}, 400
            u = Usuario(username=username, nombre=(d.get("nombre") or "").strip() or username,
                        rol=rol, password_hash=generate_password_hash(password))
            s.add(u)
            s.flush()
            registrar(s, "crear", "usuario", u.id, despues={"username": username, "rol": rol})
    return {"ok": True}


@bp.route("/usuarios/<int:uid>", methods=["PUT"])
@requiere_rol("admin")
def usuarios_editar(uid):
    d = request.get_json(silent=True) or {}
    with SessionLocal() as s:
        with s.begin():
            u = s.get(Usuario, uid)
            if not u:
                return {"ok": False, "error": "No existe."}, 404
            antes = {"rol": u.rol, "activo": u.activo, "nombre": u.nombre}
            if "rol" in d:
                if d["rol"] not in ROLES:
                    return {"ok": False, "error": "Rol invalido."}, 400
                if u.id == g.usuario["id"] and d["rol"] != "admin":
                    return {"ok": False, "error": "No puedes quitarte el rol de administrador."}, 400
                u.rol = d["rol"]
            if "activo" in d:
                if u.id == g.usuario["id"] and not d["activo"]:
                    return {"ok": False, "error": "No puedes desactivarte a ti mismo."}, 400
                u.activo = bool(d["activo"])
            if "nombre" in d:
                u.nombre = (d["nombre"] or "").strip()
            if d.get("password"):
                if len(d["password"]) < 8:
                    return {"ok": False, "error": "Contrasena >= 8 caracteres."}, 400
                u.password_hash = generate_password_hash(d["password"])
            registrar(s, "editar", "usuario", u.id, antes=antes,
                      despues={"rol": u.rol, "activo": u.activo, "nombre": u.nombre,
                               "password_cambiada": bool(d.get("password"))})
    return {"ok": True}


@bp.route("/auditoria")
@requiere_rol("admin", "contador")
def auditoria():
    entidad = request.args.get("entidad", "").strip()
    entidad_id = request.args.get("id", type=int)
    usuario = request.args.get("usuario", "").strip()
    with SessionLocal() as s:
        stmt = select(Auditoria).order_by(Auditoria.id.desc())
        if entidad:
            stmt = stmt.where(Auditoria.entidad == entidad)
        if entidad_id:
            stmt = stmt.where(Auditoria.entidad_id == entidad_id)
        if usuario:
            stmt = stmt.where(Auditoria.usuario == usuario)
        rows = s.execute(stmt.limit(500)).scalars().all()
        eventos = [{
            "id": r.id, "fecha": r.fecha, "usuario": r.usuario or "", "accion": r.accion,
            "entidad": r.entidad, "entidad_id": r.entidad_id, "motivo": r.motivo or "",
            "antes": r.antes, "despues": r.despues, "ip": r.ip or "",
        } for r in rows]
    return render_template("auditoria.html", eventos=eventos, entidad=entidad,
                           entidad_id=entidad_id or "", usuario_f=usuario)
