# Contexto del proyecto — Buscador PCGE 2026

## Qué es

App web (y versión .exe de escritorio) para buscar cuentas del **Plan Contable General
Empresarial del Perú, edición 2026**, por código o por descripción, con tolerancia a
errores de tipeo y sinónimos de jerga contable común.

## Origen de los datos

- Fuente: PDF oficial `8559200-plan-contable-general-empresarial-pcge-2026.pdf`
  (subido por el usuario), 203 páginas.
- Se extrajo el texto de las páginas 19 a 52 (sección "CATÁLOGO DE CUENTAS") con
  `pdfplumber`.
- El texto se parseó con un script (`parse.py`, usado una sola vez, no forma parte de
  la app) para separar código + descripción de cada cuenta, resolviendo:
  - Números de página sueltos (descartados).
  - Descripciones que el PDF partió en 2-3 líneas por el salto de columna/página
    (reconstruidas).
  - 1 error real de lectura del PDF (código `70992` debía ser `70902`, corregido a
    mano comparando con el patrón Terceros/Relacionadas del resto del catálogo).
- Resultado: `pcge_data.json`, **1616 cuentas** (niveles 2 a 5 dígitos), cada una con
  `codigo`, `descripcion`, `nivel`, `elemento` (1-9) y `elemento_nombre`.
- Validado: sin códigos duplicados, todo código tiene su padre inmediato en el catálogo.

## Arquitectura de la app

- **Backend**: Flask (`app.py`), single-file, sin base de datos real — el catálogo
  (1616 filas) se carga completo en memoria al arrancar desde `pcge_data.json`. No hace
  falta Postgres/SQLite persistente: es un catálogo de solo lectura que no cambia entre
  despliegues.
- **Frontend**: una sola plantilla (`templates/index.html`), sin frameworks JS, con
  `fetch` a `/buscar` y debounce de 200ms para filtrar en vivo mientras se escribe
  (sin recargar la página).
- **Búsqueda** (`buscar_cuentas` en `app.py`), en este orden:
  1. **Sinónimos**: si el texto escrito coincide con una entrada del diccionario
     `SINONIMOS` (p. ej. `luz` → `energia electrica`, `afp` → `administradoras de
     fondos de pensiones`, `planilla` → `remuneraciones`), se busca también por el
     término técnico mapeado.
  2. **Coincidencia exacta** (substring, sin distinguir mayúsculas/acentos) sobre
     código o descripción. Si hay resultados exactos, se muestran *solo* esos (no se
     mezcla con resultados aproximados).
  3. **Búsqueda difusa** (fuzzy, con `rapidfuzz.fuzz.partial_ratio`, umbral 65) — entra
     únicamente cuando no hubo ningún resultado exacto, para tolerar errores de tipeo
     (ej. "vnetas" encuentra "VENTAS").
  - Filtro adicional por elemento (1-9) combinable con el texto.
- **Versión de escritorio** (`desktop.py`): levanta el mismo Flask en un hilo y abre el
  navegador en `http://127.0.0.1:5000`. Se empaqueta a `.exe` con PyInstaller:
  ```
  pyinstaller --onefile --add-data "pcge_data.json;." --add-data "templates;templates" desktop.py
  ```

## Archivos del repo

| Archivo | Rol |
|---|---|
| `app.py` | App Flask (web + lógica de búsqueda) |
| `templates/index.html` | UI (formulario + tabla + JS de búsqueda en vivo) |
| `pcge_data.json` | Catálogo completo (1616 cuentas) |
| `desktop.py` | Entry point para la versión `.exe` |
| `requirements.txt` | `flask`, `gunicorn`, `rapidfuzz` |
| `Procfile` | `web: gunicorn app:app` (para Railway) |
| `.gitignore` | Excluye `__pycache__`, `venv`, `build/`, `dist/`, `*.spec` |

## Dónde quedó cada cosa

- **Repo**: https://github.com/Iosef296/PLAN_CONTABLE (push hecho a `main`, sin
  atribución de Claude en los commits).
- **Railway**: proyecto `carefree-tenderness`, servicio `web`, conectado al repo de
  GitHub (auto-deploy). Dominio generado: `web-production-61580.up.railway.app`.
  - Al momento de desplegar, Railway tenía un **incidente activo de plataforma**
    ("Deployments stuck in initializing", identificado 28-oct 17:49 UTC, ver
    status.railway.com) que dejó el primer deploy en estado "Queued" sin avanzar.
    No es un problema del código ni de la configuración del proyecto — hay que
    reintentar/esperar a que Railway lo resuelva.

## Cómo correr local

```
pip install -r requirements.txt
python app.py
```
Abre `http://localhost:5000`.

## Pendiente / posibles mejoras futuras

- Confirmar que el deploy en Railway termine de arrancar una vez pase el incidente.
- Ampliar el diccionario `SINONIMOS` con más jerga según lo que el usuario necesite
  buscar seguido.

## Implementacion sesion 2026-10-28 (asientos contables) — HECHO

- `desktop.py` eliminado, proyecto 100% web.
- Deps agregadas: `SQLAlchemy`, `alembic`, `psycopg2-binary`, `python-dotenv`, `openpyxl`.
- `DATABASE_URL` en `.env` local (ignorado) apuntando a Neon (region sa-east-1, pooler). **Pendiente**: setear `DATABASE_URL` como variable de entorno en Railway y **rotar la password** de `neondb_owner` porque el string original quedo en el transcript del chat.
- `models.py`: `Asiento` + `AsientoLinea` con CHECK de partida doble a nivel DB.
- `db.py`: engine y `SessionLocal`.
- Alembic en `migrations/` con `env.py` que lee `DATABASE_URL` directo (sin pasar por `alembic.ini` por el `%` del connection string). Migracion inicial `ea9387279af4` aplicada en Neon.
- Endpoints en `app.py`:
  - `GET /asientos` listado (ultimos 200).
  - `GET /asientos/nuevo` formulario.
  - `POST /asientos` crear (JSON, valida: ≥2 lineas, cuenta en PCGE nivel 4-5, debe XOR haber, cuadre ±0.01, fecha no futura). Numero autogenerado `YYYY-MM-NNNN` por mes.
  - `GET /asientos/<id>` detalle.
  - `POST /asientos/<id>/reversa` crea asiento inverso (debe↔haber), marca original anulado. No se puede reversar una reversa, ni reversar algo ya anulado.
  - `GET /asientos/<id>/excel` export openpyxl.
  - `/buscar` acepta `solo_movimiento=1` para filtrar nivel 4-5 en el autocomplete.
- Templates: `asientos_listado.html`, `asiento_form.html` (filas dinamicas, autocomplete con teclado, mutex debe/haber, totales en vivo, boton guardar bloqueado hasta cuadrar, atajo "cuadrar en ultima linea"), `asiento_detalle.html` (con boton reversa + export Excel). Nav agregada a `index.html`.
- Smoke test local: creado asiento `2026-10-0001` (1000 debe 6011 / 1000 haber 1041), export Excel 5KB OK, reversa `2026-10-0002` OK.

## Decisiones de la sesión 2026-10-28 (asientos contables)

### Alcance acordado
- Se **descarta la versión `.exe` desktop** — el proyecto queda **100% web**.
  Pendiente: borrar `desktop.py` y quitar las instrucciones de PyInstaller de este
  archivo y del README cuando se arranque la implementación.
- Se implementará un módulo de **asientos contables con partida doble** reusando el
  buscador existente para autocompletar cuentas en las líneas del asiento.

### Stack para la parte de asientos
- **BD**: Postgres en **Neon** (neon.tech, free tier). La cuenta ya la tiene el
  usuario — falta pegar el `DATABASE_URL` al proyecto cuando se arranque la
  implementación.
- **ORM**: SQLAlchemy.
- **Migraciones**: Alembic.
- **Driver**: `psycopg2-binary`.
- **Config**: `python-dotenv` + `.env` local (ignorado por git), `DATABASE_URL` como
  variable de entorno en Railway.
- Se descartó SQLite porque ya no hay `.exe` que lo justifique y Neon es Postgres puro
  (no soporta SQLite).

### Modelo de datos previsto
- `asiento(id, numero, fecha, glosa, moneda default 'PEN', tipo_cambio default 1, created_at)`
  - `numero` correlativo mensual tipo `2026-10-0001`, generado en backend dentro de
    transacción.
- `asiento_linea(id, asiento_id FK, orden, cuenta_codigo, glosa_linea, debe DECIMAL(15,2), haber DECIMAL(15,2))`
  - Constraint a nivel BD: `CHECK ((debe > 0 AND haber = 0) OR (debe = 0 AND haber > 0))`.

### Reglas de partida doble (validadas en backend, no solo UI)
1. Mínimo 2 líneas por asiento.
2. Cada línea: exactamente uno de `debe`/`haber` positivo, el otro = 0.
3. `SUM(debe) == SUM(haber)` por asiento, tolerancia ±0.01.
4. `cuenta_codigo` existe en PCGE **y** es cuenta de movimiento (nivel 4 o 5 — no
   permitir asentar en agrupadoras de 2 dígitos).
5. Fecha no futura (configurable).
6. **No se edita** un asiento guardado: se anula con un asiento de reversa
   (debe↔haber) que referencia al original. Simplifica auditoría y evita
   versionado.

### UX del formulario (planeada)
- Tabla con filas dinámicas (agregar/eliminar).
- Columna cuenta con autocomplete usando el endpoint `/buscar` existente.
- Columnas debe/haber: al tipear en una, la otra se bloquea en esa fila.
- Footer con totales en vivo (`Σ Debe | Σ Haber | Diferencia`), botón Guardar
  deshabilitado hasta que cuadre.
- Atajo "cuadrar en última línea".
- Export a Excel (openpyxl) para asiento individual o rangos.

### Orden de implementación (pendiente de arrancar)
1. Deps + conexión SQLAlchemy en `app.py` + modelos + Alembic init.
2. Primera migración contra Neon.
3. `GET /asientos/nuevo` (formulario).
4. `POST /asientos` con todas las validaciones.
5. `GET /asientos` listado + `GET /asientos/<id>` detalle.
6. Export Excel + reversa.

### Fuera de alcance del MVP de asientos
- Centros de costo / áreas / proyectos por línea.
- Multi-moneda real con revaluación.
- Libro Diario / Mayor / Balance de comprobación automáticos.
- PLE SUNAT (formato oficial).
- Multiempresa / periodos / cierre.

### Infra / tooling
- Se instaló **Playwright MCP** en el scope de usuario de Claude Code en esta laptop
  (`claude mcp add playwright --scope user -- npx @playwright/mcp@latest`,
  configurado en `C:\Users\crist\.claude.json`). Objetivo: permitir que Claude Code
  maneje el navegador para flujos tipo "crear cuenta en Neon". Requiere **reiniciar
  Claude Code** para que las herramientas `mcp__playwright__*` queden disponibles.
  La primera invocación descarga Chromium (~150 MB).
