# Guía de estudio: cómo funciona Plan Contable

Guía para que el grupo entienda el sistema de punta a punta: la contabilidad que aplica, qué hace cada módulo, cómo se conectan entre sí y cómo está construido por dentro.

> El [MANUAL.md](MANUAL.md) explica **qué botón presionar**. Esta guía explica **por qué** el sistema funciona así. Úsenlas juntas: lean aquí el concepto y prueben en la app con el manual al lado.

---

## Índice

1. [La idea en una frase](#1-la-idea-en-una-frase)
2. [Conceptos contables que hay que dominar](#2-conceptos-contables-que-hay-que-dominar)
3. [Mapa del sistema](#3-mapa-del-sistema)
4. [Una operación de principio a fin](#4-una-operación-de-principio-a-fin)
5. [Cada módulo en detalle](#5-cada-módulo-en-detalle)
6. [Asientos típicos para practicar](#6-asientos-típicos-para-practicar)
7. [Las reglas del sistema y su porqué](#7-las-reglas-del-sistema-y-su-porqué)
8. [Cómo está hecho por dentro](#8-cómo-está-hecho-por-dentro)
9. [Plan de estudio en 5 sesiones](#9-plan-de-estudio-en-5-sesiones)
10. [Preguntas de repaso (con respuestas)](#10-preguntas-de-repaso-con-respuestas)
11. [Glosario](#11-glosario)

---

## 1. La idea en una frase

**Todo en el sistema nace de un asiento contable.** Los libros, el balance, los estados financieros, los registros de compras y ventas, el dashboard y los archivos para SUNAT son solo *formas distintas de leer los mismos asientos*. Si entienden el asiento, entienden el sistema.

```
            ┌──────────────── ASIENTOS (partida doble) ────────────────┐
            │                                                          │
   Libro diario   Libro mayor   Balance   Estados financieros   Registros   PLE SUNAT   Dashboard
   (en orden)     (por cuenta)  (saldos)  (agrupado por PCGE)   (compras/   (.txt)      (resumen)
                                                                ventas)
```

---

## 2. Conceptos contables que hay que dominar

### 2.1 El PCGE

El **Plan Contable General Empresarial** es la lista oficial de cuentas que usan las empresas en Perú. El sistema trae las **1,666 cuentas** del PCGE.

Las cuentas se ordenan por **elemento** (el primer dígito):

| Elemento | Nombre | Ejemplos | Naturaleza |
|---|---|---|---|
| 1 | Activo disponible y exigible | 1011 Caja, 1041 Banco, 1212 Facturas por cobrar | Deudora |
| 2 | Activo realizable | 2011 Mercaderías, 2411 Materias primas | Deudora |
| 3 | Activo inmovilizado | 33411 Vehículos, 33611 Equipo de cómputo, 39 Depreciación acumulada | Deudora (la 39 es acreedora) |
| 4 | Pasivo | 40111 IGV, 4212 Facturas por pagar, 4111 Sueldos por pagar | Acreedora |
| 5 | Patrimonio | 5011 Capital, 59 Resultados acumulados | Acreedora |
| 6 | Gastos por naturaleza | 6011 Compra de mercaderías, 6361 Luz, 6211 Sueldos | Deudora |
| 7 | Ingresos | 70121 Venta de mercaderías, 7581 Ganancia por diferencia de cambio | Acreedora |
| 8 | Saldos intermediarios y resultado | 89 Determinación del resultado | — |
| 9 | Contabilidad analítica (gastos por función) | 94 Administración, 95 Ventas | Deudora |

**Elementos 1 a 5 = Balance** (lo que la empresa tiene y debe). **Elementos 6 a 9 = Resultados** (lo que gana y gasta en el año).

### 2.2 Niveles de las cuentas

El código se va haciendo más específico con cada dígito:

```
4     Pasivo                                  (elemento)
40    Tributos por pagar                      nivel 2  → solo título
401   Gobierno central                        nivel 3  → solo título
4011  IGV                                     nivel 4  → lleva montos
40111 IGV – Cuenta propia                     nivel 5  → lleva montos
```

**Regla del sistema:** solo llevan montos las cuentas de **nivel 4 o 5**, y las de nivel 3 que **no tienen subcuentas** (ej. 417 AFP, 424 Honorarios por pagar). A estas se les llama **cuentas de movimiento**. Las demás son títulos para agrupar.

### 2.3 Partida doble

Cada operación afecta **al menos dos cuentas**, y la suma del **Debe** siempre es igual a la del **Haber**.

- **Debe** = columna izquierda. Aumenta activos y gastos.
- **Haber** = columna derecha. Aumenta pasivos, patrimonio e ingresos.

Truco para recordarlo: *el activo y el gasto "crecen" por el Debe; todo lo demás crece por el Haber*.

### 2.4 El asiento contable

Un asiento es el registro de una operación. Tiene una **cabecera** (fecha, glosa, comprobante, tercero) y varias **líneas** (cuenta + Debe o Haber).

```
Asiento 2026-10-0001   Fecha: 20/10/2026   Glosa: Venta de mercadería F001-100
┌────────┬────────────────────────────┬──────────┬──────────┐
│ Cuenta │ Descripción                │   Debe   │  Haber   │
├────────┼────────────────────────────┼──────────┼──────────┤
│ 1212   │ Facturas por cobrar        │ 1,180.00 │          │
│ 40111  │ IGV – Cuenta propia        │          │   180.00 │
│ 70121  │ Venta de mercaderías       │          │ 1,000.00 │
├────────┼────────────────────────────┼──────────┼──────────┤
│        │ Totales                    │ 1,180.00 │ 1,180.00 │  ← cuadra
└────────┴────────────────────────────┴──────────┴──────────┘
```

### 2.5 El IGV

El **Impuesto General a las Ventas** es 18 % (o 10.5 % para algunas MYPE de restaurantes y hoteles; se configura en el sistema).

- Cuando **vendes**, cobras IGV: es una **deuda con SUNAT** → Haber 40111.
- Cuando **compras**, pagas IGV: es **crédito fiscal** a tu favor → Debe 40111.
- **IGV por pagar del mes** = IGV de ventas − IGV de compras. El dashboard lo muestra.

### 2.6 Saldo de una cuenta

**Saldo = total Debe − total Haber.** Si sale positivo es **saldo deudor**; si es negativo, **saldo acreedor**. Una cuenta de activo normalmente tiene saldo deudor; una de pasivo, acreedor. Si una cuenta tiene el saldo "al revés", vale la pena revisarla.

---

## 3. Mapa del sistema

El menú lateral está ordenado igual que el trabajo de un contador:

| Grupo | Módulos | Para qué |
|---|---|---|
| **General** | Dashboard, Buscar cuentas | Ver el resumen y consultar el PCGE |
| **Operaciones** | Lista de asientos, Crear asiento | **Registrar** (aquí entra toda la información) |
| **Reportes** | Libro diario, Libro mayor, Balance, Reporte anual, Registros por mes, Reporte por RUC, Estados financieros | **Leer** los asientos de distintas formas |
| **SUNAT** | Libros electrónicos (PLE), Destino y cierre anual | **Cumplir** con SUNAT y cerrar el año |
| **Mantenimiento** | Entidades, Cierres de mes, Importar Excel, Auditoría, Usuarios, Configuración | **Controlar** y configurar |

Fíjense que **solo un grupo escribe datos contables** (Operaciones, más Importar Excel y los asientos automáticos de destino y cierre). Todo lo demás **lee**.

---

## 4. Una operación de principio a fin

Sigamos **una compra de mercadería** por todos los módulos. Es el mejor ejercicio para entender cómo se conecta todo.

**Situación:** el 15/10/2026 compramos mercadería por S/ 1,000 + IGV al crédito al proveedor RUASHKA PERÚ S.A.C. (RUC 20542653958), factura F001-555. El 30/10 le pagamos por banco.

### Paso 1. Registrar (Crear asiento → Usar plantilla → Compra de inventario)

La plantilla arma **dos asientos de una vez** (se guardan los dos o ninguno):

**Asiento A: provisión de la compra**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 6011 Mercaderías (compra) | 1,000.00 | |
| 40111 IGV – Cuenta propia | 180.00 | |
| 4212 Facturas por pagar – Emitidas | | 1,180.00 |

**Asiento B: ingreso al almacén** (el gasto 60 se convierte en existencia 20)
| Cuenta | Debe | Haber |
|---|---:|---:|
| 2011 Mercaderías | 1,000.00 | |
| 6111 Variación de mercaderías | | 1,000.00 |

### Paso 2. El pago (Pago a proveedor, el 30/10)

| Cuenta | Debe | Haber |
|---|---:|---:|
| 4212 Facturas por pagar | 1,180.00 | |
| 1041 Cuentas corrientes (banco) | | 1,180.00 |

### Paso 3. Dónde aparece cada cosa

| Módulo | Qué van a ver |
|---|---|
| **Lista de asientos** | Una sola **operación** con 3 asientos agrupados (el sistema los une por un identificador de operación) |
| **Libro diario** | Los 3 asientos en orden de fecha, con sus líneas |
| **Libro mayor** | La cuenta 4212 con un Haber de 1,180 y un Debe de 1,180 → **saldo 0** (ya no debemos nada) |
| **Balance** | 2011 con saldo deudor 1,000 (tenemos mercadería), 1041 bajó 1,180 |
| **Registros por mes** | La factura F001-555 en el **Registro de Compras** de octubre: base 1,000, IGV 180 |
| **Reporte por RUC** | Se suma 1,180 a las compras de RUASHKA |
| **Dashboard** | Sube "Compras del mes" y baja el "IGV por pagar" (crédito fiscal de 180) |
| **Estados financieros** | Activo: inventario +1,000; efectivo −1,180. IGV: menos deuda con SUNAT |
| **PLE 5.1 / 6.1** | Cada línea de los 3 asientos en el .txt del Libro Diario y del Mayor |

**Ejercicio para el grupo:** registren esta operación en la app y verifiquen cada fila de esta tabla.

---

## 5. Cada módulo en detalle

Para cada módulo: **qué hace**, **qué concepto contable aplica** y **en qué fijarse al estudiarlo**.

### 5.1 Dashboard
- **Qué hace:** resumen del mes elegido: ventas, compras, IGV por pagar, número de asientos, gráficos mes a mes, liquidez (caja y bancos, por cobrar, por pagar) y los principales clientes y proveedores.
- **Concepto:** lectura gerencial; no es un reporte oficial.
- **Fíjense en:** las compras se estiman con las cuentas 60 y 63, por eso es "orientativo". La **liquidez** sale de los saldos de las cuentas 10, 12 y 42.

### 5.2 Buscar cuentas
- **Qué hace:** buscador del PCGE por código o descripción. Entiende sinónimos ("luz" → energía eléctrica, "carro" → vehículos) y errores de tipeo.
- **Concepto:** el catálogo de cuentas y sus niveles.
- **Fíjense en:** abran un elemento y vean cómo se anidan los niveles 2 → 3 → 4 → 5.

### 5.3 Crear asiento
- **Qué hace:** el formulario principal. Cabecera, datos SUNAT del comprobante y líneas.
- **Concepto:** partida doble. **El botón Guardar solo se activa cuando Debe = Haber.**
- **Fíjense en:**
  - Solo acepta **cuentas de movimiento**.
  - Una línea lleva monto en Debe **o** en Haber, nunca en ambos.
  - La fecha **no puede ser futura** ni caer en un **mes cerrado**.
  - En dólares, los montos se convierten a soles con el tipo de cambio (el botón SUNAT lo trae).
  - Avisa si el **comprobante ya existe** (mismo documento y RUC).

### 5.4 Plantillas
- **Qué hace:** arma el asiento a partir de preguntas simples (¿qué compraste?, ¿al contado o al crédito?). También entiende texto libre: *"compré una laptop en 3500 al contado"*.
- **Concepto:** cada tipo de operación tiene un **asiento modelo**. La plantilla aplica el modelo.
- **Fíjense en:** la **vista previa** explica *por qué* usa cada cuenta. Es una excelente herramienta de estudio: prueben varias plantillas solo para leer la explicación, sin guardar.

### 5.5 Lista de asientos
- **Qué hace:** historial agrupado por **operación** (ej. venta + cobranza juntas), con filtros, exportar a Excel y anular.
- **Concepto:** una operación comercial puede generar varios asientos.
- **Fíjense en:** las operaciones **mixtas** (parte contado, parte crédito) muestran el **saldo pendiente** y se cancelan con un clic.

### 5.6 Detalle de un asiento
- **Qué hace:** muestra un asiento completo, quién lo registró, y permite editar, anular, ver historial y exportar.
- **Fíjense en:** editar **pide motivo** y no deja mover el asiento a otro mes.

### 5.7 Libro diario
- **Qué hace:** todos los asientos en **orden cronológico**.
- **Concepto:** es el libro principal y obligatorio; registra *cuándo* pasó cada cosa.
- **Fíjense en:** los totales de arriba: **Total Debe = Total Haber**, diferencia 0.00.

### 5.8 Libro mayor
- **Qué hace:** los mismos movimientos, pero **agrupados por cuenta**, con su saldo.
- **Concepto:** responde *¿cuánto hay en cada cuenta?* (ej. ¿cuánto tengo en el banco?, ¿cuánto le debo a proveedores?).
- **Fíjense en:** se puede filtrar por prefijo: `42` muestra todas las cuentas por pagar.

### 5.9 Balance de comprobación
- **Qué hace:** por cada cuenta, la **suma del Debe**, la **suma del Haber**, y el **saldo deudor o acreedor**.
- **Concepto:** comprueba que la contabilidad cuadra. Si la suma de saldos deudores ≠ suma de saldos acreedores, hay un error.
- **Fíjense en:** el mensaje "Totales cuadran correctamente". No incluye los asientos de cierre del ejercicio (si no, al 31/12 todo saldría en cero).

### 5.10 Reporte anual
- **Qué hace:** el año completo: cuadre global, una tarjeta por mes (cuadra / no cuadra), totales por elemento del PCGE y las cuentas con más movimiento.
- **Fíjense en:** es la forma más rápida de detectar un mes con problemas.

### 5.11 Registros por mes (Compras y Ventas)
- **Qué hace:** el **Registro de Compras** (formato SUNAT 8.1) y el **Registro de Ventas** (14.1) del mes: comprobante, tercero, base, IGV, total.
- **Concepto:** son los registros tributarios; sirven para comparar con la propuesta del **SIRE** de SUNAT.
- **Fíjense en:** las notas de crédito salen **en negativo**, y el sistema avisa los comprobantes con datos SUNAT incompletos.

### 5.12 Reporte por RUC
- **Qué hace:** compras y ventas acumuladas **por cliente o proveedor**.
- **Concepto:** útil para la **DAOT** (declaración anual de operaciones con terceros).

### 5.13 Estados financieros
- **Qué hace:**
  - **Estado de Situación Financiera:** Activo = Pasivo + Patrimonio.
  - **Estado de Resultados por naturaleza:** ingresos (70, 75…) menos gastos (60–68).
  - **Estado de Resultados por función:** solo si la empresa usa la clase 9.
- **Concepto:** los informes finales que resumen la salud de la empresa.
- **Fíjense en:** la etiqueta verde **"Activo = Pasivo + Patrimonio"**: es la ecuación contable fundamental.

### 5.14 Libros electrónicos (PLE)
- **Qué hace:** genera los **.txt** para el programa PLE de SUNAT: **5.1** Libro Diario, **5.3** Plan de cuentas usado, **6.1** Libro Mayor.
- **Concepto:** la obligación de llevar los libros en formato electrónico.
- **Fíjense en:** las **validaciones** antes de descargar (mes cerrado, RUC de la empresa, asientos que cuadren) y el **nombre del archivo**, que sigue la nomenclatura de SUNAT (`LE` + RUC + periodo + libro…).

### 5.15 Destino y cierre anual
- **Asientos de destino (clase 9):** reparten los gastos 62–68 por **función** (ej. 60 % Administración 94, 40 % Ventas 95), contra la cuenta **79**.
- **Cierre del ejercicio** (desde el 1 de enero siguiente), en 4 pasos automáticos:
  1. Cierra las cuentas de resultado (6, 7, 8, 9) contra la **89**.
  2. Pasa el resultado de la 89 a la **59** (utilidades o pérdidas acumuladas).
  3. Cierra las cuentas de balance (1 a 5).
  4. Crea el **asiento de apertura** al 01/01 del año siguiente.
- **Fíjense en:** por qué después del cierre todas las cuentas quedan en cero y la apertura las "revive" para el nuevo año.

### 5.16 Entidades
- **Qué hace:** catálogo de clientes y proveedores. Consulta un RUC en SUNAT (razón social, estado, condición, dirección) y lo guarda.
- **Fíjense en:** "ACTIVO" y "HABIDO" son datos de SUNAT; un proveedor "NO HABIDO" es una alerta.

### 5.17 Cierres de mes
- **Qué hace:** **bloquea** un mes: nadie puede crear, editar ni anular asientos en ese periodo.
- **Concepto:** una vez presentada la información a SUNAT, no se puede cambiar el pasado.
- **Fíjense en:** cerrar lo hace el contador o el admin; **reabrir solo el admin, con motivo**.

### 5.18 Importar Excel
- **Qué hace:** carga masiva: descargar plantilla → llenarla → subirla → revisar la vista previa → confirmar.
- **Fíjense en:** si **un** asiento cae en un mes cerrado, **no se importa nada** (todo o nada).

### 5.19 Auditoría
- **Qué hace:** bitácora de todo: altas, ediciones (con datos antes y después), anulaciones, cierres, reaperturas, descargas PLE e inicios de sesión.
- **Concepto:** **trazabilidad**: saber quién hizo qué, cuándo y por qué.
- **Fíjense en:** nadie puede modificarla ni borrarla, ni siquiera el administrador.

### 5.20 Usuarios
- **Qué hace:** crear usuarios, asignar rol, cambiar contraseña, activar o desactivar.
- **Roles:** Administrador (todo), Contador (registra, cierra meses, PLE, ejercicio), Asistente (registra asientos), Solo lectura (consulta).
- **Fíjense en:** los usuarios **no se eliminan**, se desactivan, para no perder la auditoría.

### 5.21 Configuración
- **Qué hace:** RUC y razón social de la empresa, tasa de IGV, si usa la clase 9 y la distribución de los destinos (deben sumar 100 %).

---

## 6. Asientos típicos para practicar

Montos de ejemplo con IGV 18 %. Intenten armarlos primero ustedes y después comparen con la plantilla del sistema.

**Venta al crédito (S/ 2,000 + IGV)**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 1212 Facturas por cobrar | 2,360.00 | |
| 40111 IGV | | 360.00 |
| 70121 Venta de mercaderías | | 2,000.00 |

**Cobranza de esa venta**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 1041 Banco | 2,360.00 | |
| 1212 Facturas por cobrar | | 2,360.00 |

**Recibo de luz (S/ 300 + IGV, pagado al contado)**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 6361 Energía eléctrica | 300.00 | |
| 40111 IGV | 54.00 | |
| 1041 Banco | | 354.00 |

**Planilla (sueldo bruto S/ 2,000, afiliado a ONP)**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 6211 Sueldos | 2,000.00 | |
| 4032 ONP (13 %) | | 260.00 |
| 4111 Sueldos por pagar | | 1,740.00 |
| 6271 EsSalud (9 %) | 180.00 | |
| 4031 EsSalud por pagar | | 180.00 |

**Depreciación mensual de una computadora**
| Cuenta | Debe | Haber |
|---|---:|---:|
| 68 Depreciación (cuenta según el activo) | X | |
| 39 Depreciación acumulada | | X |

**Anulación (reversa)** de cualquiera de los anteriores: las mismas cuentas con **Debe y Haber invertidos**.

---

## 7. Las reglas del sistema y su porqué

| Regla | Por qué existe |
|---|---|
| Ningún asiento se guarda si no cuadra | Es la base de la partida doble; un asiento descuadrado arruina todos los reportes |
| Solo cuentas de movimiento llevan montos | Las cuentas título solo agrupan; si llevaran montos, los totales se duplicarían |
| **Los asientos nunca se borran, se anulan con una reversa** | SUNAT exige **correlatividad** (no puede faltar un número) y la auditoría exige rastro. La reversa deja el saldo en cero sin borrar la historia |
| Si el mes está cerrado, la reversa va en el mes actual con estado PLE 9 | Lo ya presentado no se toca; la corrección se declara en el periodo en que se hace |
| La fecha no puede ser futura | No se registra lo que todavía no pasó |
| Un asiento editado no puede cambiar de mes | Cambiaría la información de un periodo que quizás ya se declaró |
| Las operaciones de varios asientos se guardan todas o ninguna | Evita dejar una compra registrada a medias (ej. con provisión pero sin ingreso a almacén) |
| Las notas de crédito deben indicar qué comprobante modifican | Requisito de SUNAT para el registro de ventas |
| Los libros siempre están en soles | La moneda funcional en Perú es el sol; el importe en dólares se guarda aparte |
| Los usuarios se desactivan, no se borran | La auditoría necesita saber quién fue cada usuario |

---

## 8. Cómo está hecho por dentro

### 8.1 Tecnologías

| Parte | Tecnología |
|---|---|
| Lenguaje | Python 3 |
| Servidor web | Flask |
| Base de datos | SQLite (archivo `plan_contable.db`); en un servidor puede ser PostgreSQL |
| Acceso a datos | SQLAlchemy (clases Python que representan las tablas) |
| Cambios de estructura de la base | Alembic (migraciones) |
| Pantallas | HTML con plantillas Jinja2, CSS y JavaScript sin frameworks |

### 8.2 Archivos principales

| Archivo | Qué contiene |
|---|---|
| `app.py` | La aplicación: rutas (cada URL), creación y anulación de asientos, reportes, dashboard |
| `models.py` | Las **tablas** de la base de datos |
| `contabilidad.py` | PLE, destino, cierre del ejercicio, estados financieros, configuración |
| `auth.py` | Inicio de sesión, usuarios, roles y auditoría |
| `sunat.py` | Consultas a SUNAT (RUC y tipo de cambio) |
| `arranque.py` | Al iniciar: respaldo automático y actualización de la base |
| `pcge_data.json` | El catálogo de las 1,666 cuentas del PCGE |
| `static/plantillas.js` | Las plantillas de asientos y el intérprete de texto libre |
| `templates/` | Una página HTML por pantalla |

### 8.3 Las tablas de la base de datos

```
Asiento ──────< AsientoLinea          (un asiento tiene muchas líneas)
  numero (AAAA-MM-NNNN)                 cuenta_codigo
  fecha, glosa                          debe, haber
  datos del comprobante y tercero       glosa de la línea
  operacion_id  (agrupa asientos de una misma operación)
  anulado / asiento de reversa

Usuario       usuarios y su rol
Auditoria     bitácora de cambios (solo se inserta, nunca se modifica)
CierreMes     meses bloqueados
Entidad       clientes y proveedores consultados en SUNAT
Config        datos de la empresa, IGV, clase 9
```

Las cuentas del PCGE **no están en la base**: se leen de `pcge_data.json` al iniciar.

### 8.4 Qué pasa al presionar "Guardar asiento"

1. El navegador envía el asiento (cabecera + líneas) al servidor.
2. El servidor **valida**: que cada cuenta exista y sea de movimiento, que Debe = Haber, que la fecha no sea futura ni de un mes cerrado, que el comprobante no esté duplicado.
3. Si todo está bien, genera el **número correlativo** (`2026-10-0001`, el siguiente del mes), guarda el asiento y sus líneas, y registra el alta en la **auditoría**.
4. Responde al navegador, que muestra el asiento guardado.

Los reportes no guardan nada: cada vez que abren uno, el sistema **lee los asientos y calcula** los totales en ese momento.

---

## 9. Plan de estudio en 5 sesiones

| Sesión | Tema | Práctica en la app |
|---|---|---|
| **1** | PCGE, elementos, niveles, Debe y Haber (secciones 2 y 3) | Explorar *Buscar cuentas*: encontrar 5 cuentas de cada elemento y decir su naturaleza |
| **2** | El asiento y las plantillas (secciones 5.3 y 5.4) | Registrar una venta y una compra con plantilla; leer la vista previa de 5 plantillas distintas |
| **3** | Los reportes (secciones 4 y 5.7 a 5.13) | Seguir la compra de la sección 4 por todos los reportes y llenar la tabla del paso 3 |
| **4** | SUNAT y controles (secciones 5.14 a 5.19 y 7) | Anular un asiento y ver la reversa; cerrar un mes e intentar registrar en él; revisar la auditoría |
| **5** | Cómo está hecho (sección 8) y repaso | Responder las preguntas de la sección 10 sin mirar las respuestas |

> Para practicar sin miedo, usen una copia de la base de datos o una instalación aparte, no la base real de la empresa.

---

## 10. Preguntas de repaso (con respuestas)

Intenten responder antes de abrir cada respuesta.

<details><summary><b>1.</b> ¿Por qué la cuenta 40 no puede llevar montos pero la 40111 sí?</summary>

La 40 es de nivel 2 (título que agrupa). Solo llevan montos las cuentas de movimiento: nivel 4 o 5, o nivel 3 sin subcuentas.
</details>

<details><summary><b>2.</b> En una venta, ¿el IGV va al Debe o al Haber? ¿Y en una compra?</summary>

Venta: Haber (es una deuda con SUNAT). Compra: Debe (es crédito fiscal a favor de la empresa).
</details>

<details><summary><b>3.</b> ¿Qué diferencia hay entre el libro diario y el libro mayor si tienen los mismos datos?</summary>

El diario ordena por fecha (qué pasó y cuándo). El mayor agrupa por cuenta (cuánto hay en cada cuenta y su saldo).
</details>

<details><summary><b>4.</b> Me equivoqué en un asiento de un mes ya cerrado. ¿Qué hace el sistema si lo anulo?</summary>

Crea una reversa (mismas cuentas, Debe y Haber invertidos) en el mes actual con estado PLE 9 (corrección), y marca el original como anulado. Nunca lo borra.
</details>

<details><summary><b>5.</b> ¿Por qué el sistema no deja borrar asientos?</summary>

Por la correlatividad que exige SUNAT (no pueden faltar números) y por trazabilidad: la auditoría debe mostrar qué pasó.
</details>

<details><summary><b>6.</b> ¿Para qué sirve el asiento 2011 / 6111 después de una compra de mercadería?</summary>

Es el ingreso al almacén: convierte la compra (gasto de la cuenta 60, compensado con la 61) en una existencia del activo (cuenta 20).
</details>

<details><summary><b>7.</b> ¿Qué comprueba el balance de comprobación?</summary>

Que la suma del Debe sea igual a la del Haber, y que los saldos deudores sumen lo mismo que los acreedores. Si no, hay un error de registro.
</details>

<details><summary><b>8.</b> ¿Qué ecuación debe cumplir el Estado de Situación Financiera?</summary>

Activo = Pasivo + Patrimonio.
</details>

<details><summary><b>9.</b> ¿Cuáles son los 4 pasos del cierre del ejercicio?</summary>

1) Cerrar las cuentas de resultado (6, 7, 8, 9) contra la 89. 2) Pasar el resultado de la 89 a la 59. 3) Cerrar las cuentas de balance (1 a 5). 4) Asiento de apertura al 01/01 siguiente.
</details>

<details><summary><b>10.</b> ¿Qué tres archivos genera el PLE y qué contiene cada uno?</summary>

5.1 Libro Diario (cada línea de cada asiento), 5.3 detalle del plan contable (las cuentas usadas) y 6.1 Libro Mayor (los movimientos ordenados por cuenta).
</details>

<details><summary><b>11.</b> ¿Qué pasa si importo un Excel con 50 asientos y uno cae en un mes cerrado?</summary>

No se importa ninguno: la importación es todo o nada.
</details>

<details><summary><b>12.</b> ¿Quién puede reabrir un mes cerrado y qué se le exige?</summary>

Solo el administrador, y debe escribir un motivo, que queda en la auditoría.
</details>

<details><summary><b>13.</b> ¿Dónde están guardadas las 1,666 cuentas del PCGE?</summary>

En el archivo `pcge_data.json`, no en la base de datos. El sistema las carga al iniciar.
</details>

<details><summary><b>14.</b> Si registro una venta, ¿en qué reportes aparece?</summary>

En todos: lista de asientos, libro diario, libro mayor, balance, reporte anual, registro de ventas, reporte por RUC, estados financieros, dashboard y PLE. Todos leen los mismos asientos.
</details>

---

## 11. Glosario

| Término | Significado |
|---|---|
| **Asiento** | Registro contable de una operación, con al menos dos líneas que cuadran |
| **Glosa** | Descripción breve de la operación o de una línea |
| **Correlativo** | Número consecutivo del asiento (`AAAA-MM-NNNN`) |
| **Cuenta de movimiento** | Cuenta que puede llevar montos (nivel 4–5, o nivel 3 sin subcuentas) |
| **Saldo deudor / acreedor** | Debe mayor que Haber / Haber mayor que Debe |
| **Crédito fiscal** | IGV pagado en compras, que se descuenta del IGV de ventas |
| **Provisión** | Registrar una obligación o derecho antes de pagarlo o cobrarlo (ej. la factura por pagar) |
| **Reversa** | Asiento con las mismas cuentas y Debe/Haber invertidos que anula otro |
| **Operación** | Conjunto de asientos que pertenecen a un mismo hecho (ej. compra + ingreso a almacén + pago) |
| **Tercero** | Cliente o proveedor de la operación, identificado por su RUC o DNI |
| **Destino** | Reparto de los gastos por función (clase 9) contra la cuenta 79 |
| **Ejercicio** | El año contable (01/01 al 31/12) |
| **PLE** | Programa de Libros Electrónicos de SUNAT |
| **SIRE** | Sistema de SUNAT que propone los registros de compras y ventas |
| **DAOT** | Declaración anual de operaciones con terceros |
| **Detracción** | Porcentaje que el cliente deposita en la cuenta del Banco de la Nación del proveedor en ciertos servicios |
| **Estado PLE** | 1 = del periodo; 8 = de un periodo anterior no anotado; 9 = corrección de un periodo anterior |
| **Auditoría** | Bitácora inalterable de quién hizo qué, cuándo y por qué |
