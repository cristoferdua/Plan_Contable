# Plan Contable — Sistema de contabilidad PCGE

Sistema web de contabilidad para empresas peruanas, basado en el **Plan Contable General Empresarial (PCGE)**. Registra asientos con partida doble, genera los libros y reportes contables y produce los archivos del **Programa de Libros Electrónicos (PLE) de SUNAT**.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Base de datos](https://img.shields.io/badge/BD-SQLite%20%7C%20PostgreSQL-336791?logo=postgresql&logoColor=white)

---

## Contenido

- [Funcionalidades](#funcionalidades)
- [Tecnologías](#tecnologías)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecución](#ejecución)
- [Primer uso](#primer-uso)
- [Base de datos y migraciones](#base-de-datos-y-migraciones)
- [Despliegue en producción](#despliegue-en-producción)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Cómo funciona](#cómo-funciona)
- [Respaldos](#respaldos)
- [Solución de problemas](#solución-de-problemas)
- [Documentación](#documentación)

---

## Funcionalidades

**Registro contable**
- Asientos con **partida doble obligatoria**, en soles o dólares (conversión con el tipo de cambio de SUNAT).
- **Plantillas** que arman el asiento por ti: ventas, compras, servicios, honorarios, importaciones, planilla, préstamos, depreciación, capital y más. Más de 60 conceptos de gasto con su cuenta PCGE (luz 6361, agua 6363, predial 6431…).
- **Intérprete de texto libre**: escribe *"compré una laptop en 3500 al contado"* y el sistema sugiere la plantilla con los datos llenos.
- Operaciones de varios asientos (provisión + destino + cancelación) que se guardan **de forma atómica** y se agrupan en la lista.
- Aviso de **comprobante duplicado** (mismo N° de documento y RUC).
- Datos SUNAT del comprobante: tipo (Tabla 10), documento del tercero (Tabla 2), estado PLE, detracciones, retenciones y percepciones.
- Consulta de **RUC** y **tipo de cambio** en línea.
- **Importación masiva** desde Excel.

**Reportes**
- Libro diario, libro mayor y balance de comprobación.
- Registro de compras y de ventas por mes (para comparar con el SIRE).
- Reporte anual y reporte por RUC (base para la DAOT).
- **Estados financieros**: situación financiera y resultados por naturaleza y por función.
- Dashboard con indicadores, gráficos y liquidez.
- Exportación a Excel.

**SUNAT y cierres**
- Archivos **PLE 5.1, 5.3 y 6.1** con la nomenclatura oficial.
- Asientos de **destino** (clase 9) y **cierre del ejercicio** con asiento de apertura.
- **Cierre de meses** para bloquear periodos ya declarados.

**Control interno**
- Usuarios con **roles**: administrador, contador, asistente y solo lectura.
- **Auditoría** inmutable: quién creó, editó, anuló o cerró, con los datos anteriores y los nuevos.
- Los asientos **nunca se borran**: se anulan con un asiento de reversa.

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, Flask 3.1 |
| ORM y migraciones | SQLAlchemy 2.0, Alembic |
| Base de datos | SQLite (local) o PostgreSQL (producción) |
| Frontend | HTML (Jinja2), CSS y JavaScript sin frameworks |
| Búsqueda de cuentas | RapidFuzz (tolera errores de tipeo) |
| Excel | openpyxl |
| Servidor de producción | Gunicorn |
| Servicios externos | [apis.net.pe](https://apis.net.pe) (consulta RUC y tipo de cambio SUNAT) |

---

## Requisitos

- **Python 3.12** o superior
- **Git**
- *(Opcional)* PostgreSQL 14+ para producción
- *(Opcional)* Un token de [apis.net.pe](https://apis.net.pe) para consultas de RUC sin límite

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/cristoferdua/Plan_Contable.git
cd Plan_Contable
```

### 2. Crear el entorno virtual e instalar dependencias

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Crear el archivo `.env`

Copia el ejemplo y ajústalo:

```bash
cp .env.example .env        # Linux / macOS
copy .env.example .env      # Windows
```

---

## Configuración

Variables de entorno (archivo `.env` en la raíz del proyecto):

| Variable | Obligatoria | Descripción | Ejemplo |
|---|---|---|---|
| `DATABASE_URL` | **Sí** | Conexión a la base de datos | `sqlite:///plan_contable.db` |
| `SECRET_KEY` | No | Clave para firmar las sesiones. Si falta, se genera una y se guarda en la base de datos | `una-cadena-larga-y-aleatoria` |
| `APIS_NET_PE_TOKEN` | No | Token de apis.net.pe. Sin token se usa la API pública, que tiene límites | `apis-token-xxxx` |
| `PORT` | No | Puerto del servidor de desarrollo (por defecto `5000`) | `5000` |

Ejemplos de `DATABASE_URL`:

```ini
# SQLite (archivo local, ideal para una sola PC)
DATABASE_URL=sqlite:///plan_contable.db

# PostgreSQL
DATABASE_URL=postgresql://usuario:clave@localhost:5432/plan_contable
```

> El archivo `.env` y la base de datos (`*.db`) están en `.gitignore`: **nunca se suben al repositorio**.

---

## Ejecución

### Desarrollo

```bash
python app.py
```

Abre **http://127.0.0.1:5000** en el navegador. El servidor también escucha en la red local (`0.0.0.0`), así que otras PCs de la misma red pueden entrar con la IP del equipo, por ejemplo `http://192.168.1.20:5000`.

### Producción (Linux)

```bash
gunicorn app:app --bind 0.0.0.0:8000 --workers 3
```

---

## Primer uso

1. Inicia la aplicación y abre el navegador.
2. Como todavía no hay usuarios, el sistema te lleva a **Crear administrador** (`/setup`). Usa un usuario de al menos 3 caracteres y una contraseña de al menos 8.
3. Entra a **Mantenimiento → Configuración** y registra:
   - el **RUC y la razón social** de la empresa (obligatorios para el PLE y los estados financieros);
   - la **tasa de IGV** (18 % general o 10.5 % para MYPE de restaurantes y hoteles);
   - si la empresa **usa la clase 9** y la distribución de los destinos.
4. Crea los usuarios del equipo en **Mantenimiento → Usuarios**, cada uno con su rol.
5. Registra tu primer asiento en **Crear asiento → Usar plantilla**.

El uso diario de cada pantalla está explicado en el **[Manual de usuario](MANUAL.md)**.

---

## Base de datos y migraciones

El esquema está definido en `models.py` y versionado con **Alembic** (`migrations/versions/`).

### SQLite (local)

La aplicación **crea las tablas automáticamente** al iniciar. En una instalación nueva, después del primer arranque marca la base en la última versión de migraciones:

```bash
python app.py              # crea las tablas (luego Ctrl+C)
alembic stamp head         # registra la versión actual del esquema
```

Cuando actualices el código (`git pull`) y haya migraciones nuevas, aplícalas:

```bash
alembic upgrade head
```

> En SQLite **no** crees la base con `alembic upgrade head` desde cero: una migración antigua usa `ALTER COLUMN`, que SQLite no soporta. Usa el arranque de la aplicación más `alembic stamp head`.

### PostgreSQL (producción)

Las tablas se crean **solo** con migraciones:

```bash
alembic upgrade head
```

### Crear una migración nueva

Después de modificar `models.py`:

```bash
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

Revisa siempre el archivo generado antes de aplicarlo.

---

## Despliegue en producción

El proyecto incluye un `Procfile` (`web: gunicorn app:app`), compatible con Railway, Render o Heroku.

1. Crea una base **PostgreSQL** y define `DATABASE_URL` en el panel del servicio.
2. Define una `SECRET_KEY` larga y aleatoria. Si se pierde o cambia, se cierran todas las sesiones.
3. *(Opcional)* Define `APIS_NET_PE_TOKEN`.
4. Ejecuta `alembic upgrade head` como comando de *release* o una sola vez desde la consola del servicio.
5. Despliega. El servicio asigna el puerto automáticamente.

Recomendaciones:
- Sirve la aplicación **siempre con HTTPS**: maneja datos contables y contraseñas.
- Programa **respaldos automáticos** de la base de datos (ver [Respaldos](#respaldos)).

---

## Estructura del proyecto

```
Plan_Contable/
├── app.py                 # Aplicación Flask: asientos, reportes, importación, búsqueda PCGE
├── auth.py                # Usuarios, sesiones, roles y auditoría (blueprint)
├── contabilidad.py        # Configuración, tipo de cambio, PLE, destino, cierre y EEFF (blueprint)
├── sunat.py               # Tablas SUNAT (10, 2, 4) y generación de archivos PLE
├── models.py              # Modelos SQLAlchemy (asiento, línea, usuario, auditoría...)
├── db.py                  # Conexión a la base de datos (lee DATABASE_URL)
├── init_db.py             # Crea las tablas manualmente (alternativa al arranque)
├── pcge_data.json         # Catálogo PCGE: 1,666 cuentas con código, nivel y elemento
├── requirements.txt       # Dependencias de Python
├── Procfile               # Comando de arranque en producción
├── alembic.ini            # Configuración de Alembic
├── migrations/            # Migraciones de la base de datos
│   └── versions/
├── static/
│   ├── plantillas.js      # Plantillas de asientos e intérprete de texto libre
│   ├── polish.js          # Desplegable personalizado para todos los <select>
│   ├── ui.js              # Avisos, confirmaciones y diálogos
│   ├── dashboard.js       # Gráficos del dashboard
│   └── *.css              # Estilos (tema claro/oscuro, layout, componentes)
├── templates/             # Vistas Jinja2 (una por pantalla)
│   └── partials/          # Cabecera, menú lateral y pie comunes
├── MANUAL.md              # Manual de usuario
└── README.md
```

---

## Cómo funciona

### Flujo de un asiento

```
Formulario / plantilla  ──►  Validación  ──►  Transacción  ──►  Auditoría
 (asiento_form.html,         (partida doble,   (número          (registro con
  plantillas.js)              cuentas de        correlativo,     usuario, fecha
                              movimiento,       operacion_id)    y datos)
                              mes abierto)
```

1. **Captura**: el usuario llena el formulario o aplica una plantilla. La plantilla (`static/plantillas.js`) arma las líneas con las cuentas PCGE y muestra una vista previa con el motivo de cada cuenta.
2. **Validación en el servidor**:
   - el Debe debe ser igual al Haber;
   - cada cuenta debe existir y ser **de movimiento**: nivel 4 o 5, o nivel 3 sin subcuentas;
   - la fecha no puede ser futura ni caer en un **mes cerrado**;
   - el RUC o DNI del tercero se valida (dígito verificador).
3. **Guardado**: cada asiento recibe un número correlativo `AAAA-MM-NNNN`. Los asientos de una misma operación comparten un `operacion_id` y se guardan en una sola transacción (`POST /asientos/lote`): o se guardan todos o ninguno.
4. **Auditoría**: cada alta, edición, anulación o cierre queda registrado con el usuario y los datos.

### Reglas contables del sistema

- **Los asientos no se borran**: se anulan con un asiento de **reversa** (Debe y Haber invertidos), como exige la trazabilidad de SUNAT.
- **Meses cerrados**: bloquean cualquier cambio. Solo un administrador puede reabrirlos, con un motivo.
- **Moneda extranjera**: los libros quedan en soles. El importe original en dólares se guarda aparte.
- **Clase 9 (destino)**: si la empresa la usa, el destino de los gastos 62–68 se genera a fin de mes, repartido según la configuración.

### Roles

| Rol | Permisos |
|---|---|
| Administrador | Todo: usuarios, configuración y reapertura de meses |
| Contador | Registrar, cerrar meses, destino, cierre del ejercicio, PLE y auditoría |
| Asistente | Registrar, editar y anular asientos |
| Solo lectura | Consultar pantallas y reportes |

---

## Respaldos

La base de datos contiene **toda la contabilidad** y **no está en el repositorio**. Haz copias periódicas.

**SQLite**: detén la aplicación y copia el archivo:

```bash
cp plan_contable.db respaldos/plan_contable_$(date +%Y%m%d).db
```

**PostgreSQL**:

```bash
pg_dump "$DATABASE_URL" > respaldo_$(date +%Y%m%d).sql
```

Guarda las copias fuera del equipo: disco externo, USB o la nube.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `RuntimeError: DATABASE_URL no esta configurado` | Falta el archivo `.env` o la variable. Ver [Configuración](#configuración). |
| `no such column: asiento.operacion_id` (u otra columna) | La base tiene un esquema antiguo. Ejecuta `alembic upgrade head`. |
| La consulta de RUC o tipo de cambio falla | Revisa la conexión a internet o configura `APIS_NET_PE_TOKEN`. |
| Los cambios de diseño no se ven | Recarga sin caché con `Ctrl + F5`. |
| `Address already in use` | El puerto está ocupado: cierra la otra instancia o usa `PORT=5001`. |
| Olvidé la contraseña del administrador | Otro administrador puede cambiarla en **Usuarios**. Si no hay otro, contacta al responsable técnico. |

---

## Documentación

- **[Manual de usuario](MANUAL.md)**: cada pantalla del sistema, el flujo mensual recomendado y las reglas contables.
- **[Contexto del catálogo PCGE](contexto.md)**: origen y procesamiento de los datos del plan contable.

---

Desarrollado por **[cristoferdua](https://github.com/cristoferdua)**.
