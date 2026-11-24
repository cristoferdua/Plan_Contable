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
- [Inicio rápido (Windows)](#inicio-rápido-windows)
- [Requisitos](#requisitos)
- [Instalación manual](#instalación-manual)
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
| Frontend | HTML (Jinja2), CSS y JavaScript sin frameworks; tipografía IBM Plex incluida en el proyecto |
| Búsqueda de cuentas | RapidFuzz (tolera errores de tipeo) |
| Excel | openpyxl |
| Servidor de producción | Gunicorn |
| Servicios externos | [apis.net.pe](https://apis.net.pe) (consulta RUC y tipo de cambio SUNAT) |

---

## Inicio rápido (Windows)

1. Instala **[Python 3.12](https://www.python.org/downloads/)** y marca la casilla **"Add Python to PATH"**.
2. Descarga el proyecto: botón verde **Code → Download ZIP** en GitHub y descomprímelo, o usa `git clone`.
3. Haz **doble clic en `iniciar.bat`**.

La primera vez prepara todo solo (tarda unos minutos): crea el entorno de Python, instala los componentes y crea la configuración. Luego abre el navegador en **http://127.0.0.1:5000**. Las siguientes veces arranca en segundos.

> Mantén abierta la ventana negra mientras uses el sistema. Ciérrala para apagarlo.

Cada vez que inicia, el sistema **respalda la base de datos** y **aplica los cambios de estructura** que traigan las actualizaciones. No hace falta ejecutar ningún comando.

Para **actualizar** a una versión nueva: descarga el código nuevo (o `git pull`) y vuelve a abrir `iniciar.bat`. Si cambiaron los componentes, los reinstala solo.

---

## Requisitos

- **Python 3.12** o superior
- **Git**
- *(Opcional)* PostgreSQL 14+ para producción
- *(Opcional)* Un token de [apis.net.pe](https://apis.net.pe) para consultas de RUC sin límite

---

## Instalación manual

Para Linux o macOS, o si prefieres hacerlo paso a paso.

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
| `RESPALDOS_MAX` | No | Cuántos respaldos automáticos conservar (`0` los desactiva). Por defecto `30` | `30` |
| `AUTO_MIGRAR` | No | `0` desactiva las migraciones automáticas al iniciar. Por defecto activas | `1` |

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

**No hace falta ejecutar migraciones a mano.** Al iniciar, la aplicación (`arranque.py`):

| Situación | Qué hace |
|---|---|
| Base SQLite nueva | Crea las tablas y la registra en la última versión |
| Base existente (SQLite o PostgreSQL) | Aplica las migraciones pendientes (`alembic upgrade head`) |

Si prefieres controlarlo tú (por ejemplo en un servidor con varias instancias), define `AUTO_MIGRAR=0` y ejecuta `alembic upgrade head` en cada despliegue.

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
4. Despliega. Las migraciones se aplican solas al iniciar. Si el servicio corre varias instancias a la vez, define `AUTO_MIGRAR=0` y ejecuta `alembic upgrade head` como comando de *release*.
5. Listo. El servicio asigna el puerto automáticamente.

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
├── arranque.py            # Al iniciar: respaldo automático y migraciones
├── iniciar.bat            # Inicio con doble clic en Windows
├── .env.example           # Modelo del archivo de configuración
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
│   ├── sistema.css        # Sistema visual común: colores, tipografía, cabeceras, modo oscuro
│   ├── fonts/             # IBM Plex Sans y Mono incluidas (funcionan sin internet)
│   └── *.css              # Estilos por componente (layout, desplegables, tema)
├── templates/             # Vistas Jinja2 (una por pantalla)
│   └── partials/          # Menú lateral, barra superior y cabecera de cada pantalla
├── respaldos/             # Respaldos automáticos de la base (no se suben a git)
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

La base de datos contiene **toda la contabilidad** y **no está en el repositorio**.

**Automáticos (SQLite):** cada vez que inicia la aplicación se guarda una copia en la carpeta `respaldos/`, con fecha y hora en el nombre (`plan_contable_20261124_093000.db`). Se conservan los últimos 30; puedes cambiarlo con `RESPALDOS_MAX`.

**Restaurar un respaldo:** cierra el sistema, reemplaza `plan_contable.db` por la copia elegida (renómbrala a `plan_contable.db`) y vuelve a iniciar.

**Fuera del equipo:** la carpeta `respaldos/` está en la misma PC. Copia periódicamente su contenido a un disco externo, un USB o la nube.

**PostgreSQL:** usa los respaldos del proveedor o `pg_dump`:

```bash
pg_dump "$DATABASE_URL" > respaldo_$(date +%Y%m%d).sql
```

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `RuntimeError: DATABASE_URL no esta configurado` | Falta el archivo `.env` o la variable. Ver [Configuración](#configuración). |
| `no such column: ...` | La base tiene un esquema antiguo. Reinicia el sistema (aplica las migraciones solo) o ejecuta `alembic upgrade head`. |
| `iniciar.bat` dice *"No se encontró Python"* | Instala Python 3.12 marcando **"Add Python to PATH"** y vuelve a abrirlo. |
| Me equivoqué y quiero volver a un estado anterior | Restaura un archivo de la carpeta `respaldos/` (ver [Respaldos](#respaldos)). |
| La consulta de RUC o tipo de cambio falla | Revisa la conexión a internet o configura `APIS_NET_PE_TOKEN`. |
| Los cambios de diseño no se ven | Recarga sin caché con `Ctrl + F5`. Si cambiaste plantillas (`templates/`), cierra la ventana negra y vuelve a abrir `iniciar.bat`: las plantillas se cargan al iniciar. Si aún se ve lo anterior, revisa que no quede otra ventana del sistema abierta ocupando el puerto. |
| `Address already in use` | El puerto está ocupado: cierra la otra instancia o usa `PORT=5001`. |
| Olvidé la contraseña del administrador | Otro administrador puede cambiarla en **Usuarios**. Si no hay otro, contacta al responsable técnico. |

---

## Documentación

- **[Manual de usuario](MANUAL.md)**: cada pantalla del sistema, el flujo mensual recomendado y las reglas contables.
- **[Contexto del catálogo PCGE](contexto.md)**: origen y procesamiento de los datos del plan contable.

---

Desarrollado por **[cristoferdua](https://github.com/cristoferdua)**.
