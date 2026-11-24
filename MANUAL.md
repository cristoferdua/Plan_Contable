# Manual del sistema Plan Contable (PCGE)

Guía de cada apartado del sistema, en el mismo orden del menú lateral.

---

## Índice

1. [Acceso: inicio de sesión y usuarios](#1-acceso-inicio-de-sesión-y-usuarios)
2. [General](#2-general)
3. [Operaciones](#3-operaciones)
4. [Reportes](#4-reportes)
5. [SUNAT](#5-sunat)
6. [Mantenimiento](#6-mantenimiento)
7. [Flujo de trabajo mensual recomendado](#7-flujo-de-trabajo-mensual-recomendado)
8. [Reglas importantes del sistema](#8-reglas-importantes-del-sistema)

---

## 1. Acceso: inicio de sesión y usuarios

| Pantalla | Qué hace |
|---|---|
| **Crear administrador** (`/setup`) | Solo aparece la primera vez, cuando todavía no hay usuarios. Crea el usuario administrador principal. |
| **Iniciar sesión** (`/login`) | Todas las pantallas exigen iniciar sesión. Cada persona debe usar su propio usuario para que la auditoría registre quién hizo cada cambio. |
| **Salir** | Botón en la barra superior (junto a tu nombre). Cierra la sesión. |

### Roles

| Rol | Puede |
|---|---|
| **Administrador** | Todo: usuarios, configuración, reabrir meses, cierres, PLE, auditoría. |
| **Contador** | Registrar asientos, cerrar meses, generar destinos, cerrar el ejercicio, descargar el PLE y ver la auditoría. |
| **Asistente** | Registrar, editar y anular asientos. |
| **Solo lectura** | Consultar pantallas y reportes; no puede modificar nada. |

---

## 2. General

### Dashboard (`/dashboard`)
Resumen visual del mes elegido:
- **Indicadores**: ventas, compras, margen, IGV del mes y cantidad de asientos, comparados con el mes anterior.
- **Gráficos**: ventas frente a compras mes a mes, resultado mensual y "¿en qué se gasta?" (gastos por cuenta).
- **Liquidez**: saldos de efectivo (10), cuentas por cobrar (12) y por pagar (42).
- **Top clientes y top proveedores** por monto.
- **Últimas operaciones** registradas y accesos rápidos.

> Las cifras del dashboard son orientativas: las compras se estiman con las cuentas 60 y 63. Para cifras oficiales usa los reportes y los estados financieros.

### Buscar cuentas (`/`)
Catálogo completo del Plan Contable General Empresarial:
- Busca por **código** (ej. `4011`) o por **descripción** (ej. "ventas").
- Entiende **sinónimos** de uso común: "luz" encuentra *energía eléctrica*, "planilla" encuentra *remuneraciones*, "carro" encuentra *vehículos*, etc.
- Tolera **errores de tipeo** ("vnetas" encuentra "ventas").
- Puedes **filtrar por elemento** (1 al 9) y marcar cuentas como **favoritas**, que luego aparecen primero al buscar desde el formulario de asientos.

---

## 3. Operaciones

### Lista de asientos (`/asientos`)
Muestra los asientos agrupados por **operación**. Por ejemplo, una venta y su cobranza aparecen juntas.
- Cada operación se identifica internamente, así que dos compras distintas con el **mismo número de comprobante** aparecen separadas. La cancelación de un saldo queda dentro de su operación aunque se registre en otra fecha.
- **Filtros**: por mes, por rango de fechas o por RUC del tercero.
- **Operaciones mixtas** (parte al contado y parte al crédito): muestra el **saldo pendiente** y permite registrar la **cancelación del saldo** (pago o cobro) en un clic.
- **Anular**: crea un asiento de reversa por cada asiento de la operación (ver [Reglas importantes](#8-reglas-importantes-del-sistema)). Pide el motivo.
- **Exportar a Excel** una operación completa.

### Crear asiento (`/asientos/nuevo`)
Formulario para registrar asientos contables con partida doble.

**Datos del asiento**
- **Fecha**: no puede ser futura ni caer en un mes cerrado.
- **Moneda y tipo de cambio**: si la operación es en **USD**, escribe los montos en dólares; el sistema los convierte a soles con el tipo de cambio y guarda también el importe en dólares. El botón **SUNAT** trae el tipo de cambio *venta* publicado por SUNAT para la fecha.
- **N° documento** (ej. `F001-1234`), **RUC del tercero** (el botón **SUNAT** consulta la razón social), código de libro y correlativo.

**Comprobante y datos SUNAT**
- **Tipo de comprobante** (Tabla 10 de SUNAT): factura, boleta, nota de crédito, recibo por honorarios, etc. Si se deja vacío, se deduce de la serie (F = factura, B = boleta).
- **Documento de identidad del tercero** (Tabla 2): RUC, DNI, carné de extranjería, pasaporte…
- **Fechas de emisión y vencimiento** del comprobante.
- **Estado PLE**: 1 = operación del mes; 8 = operación de un mes anterior que no se anotó; 9 = corrección de un mes anterior.
- **Comprobante que modifica**: aparece solo en **notas de crédito o débito** y es obligatorio para ellas.
- **Detracción, retención y percepción**: monto y constancia de depósito de la detracción, si está sujeto a retención del IGV y el monto de la percepción.

**Detalle (líneas)**
- Cada línea lleva una cuenta, una glosa y un monto en **Debe** o en **Haber** (nunca en ambos).
- Llevan montos las cuentas de **nivel 4 o 5** y también las de nivel 3 que **no tienen subcuentas** en el PCGE (por ejemplo 417 AFP, 424 Honorarios por pagar, 422 Anticipos otorgados, 122 Anticipos recibidos). Las demás cuentas de nivel 2 o 3 solo sirven como títulos.
- El botón **Guardar** se habilita solo cuando el asiento **cuadra** (Debe = Haber). El atajo "cuadrar en última línea" completa la diferencia.
- Atajos: `Enter` pasa a la siguiente línea y `Ctrl + Enter` guarda.
- El formulario guarda un **borrador** automático por si cierras la página.
- **Comprobante duplicado**: si el N° de documento y el RUC ya están registrados en otro asiento vigente, el sistema avisa antes de guardar. Puedes cancelar o registrarlo igual si es otra operación.
- **Guardar como plantilla**: guarda las líneas actuales como plantilla de la empresa (por ejemplo "Alquiler mensual del local"). Aparece después en "Usar plantilla", en el grupo *Plantillas de mi empresa*.

**Plantillas ("Usar plantilla")**
Arman el asiento por ti. Hay tres formas de elegir una plantilla:

1. **Escribir la operación con tus palabras**, por ejemplo *"compré una camioneta en 120 mil al crédito factura F001-555"*. El sistema sugiere la plantilla y deja llenos el tipo de compra, el monto, la forma de pago, el comprobante y el RUC. Con `Enter` se abre la primera sugerencia. **Siempre revisa los datos antes de aplicarla**: la sugerencia es una ayuda, no una decisión contable.
2. **Elegir una tarjeta**, que están agrupadas en Ventas, Compras y gastos, Personal, Bancos y Activos.
3. **Usar una plantilla de la empresa** guardada antes.

La **vista previa** muestra cada cuenta con su nombre, el motivo por el que se usa y los avisos importantes: detracción, límites tributarios de vehículos, PLAME, etc. Las listas largas (por ejemplo, *¿Qué pagaste?*) están **agrupadas** y tienen un **buscador**: escribe "agua" o "predial" y pulsa `Enter`. Cada opción muestra su **cuenta PCGE**. La opción **Otra cuenta** abre un buscador del plan contable por código o por nombre, y avisa si la cuenta elegida tiene subcuentas.

Las operaciones de varios asientos (por ejemplo, provisión, ingreso a almacén y pago) se guardan **todas juntas o ninguna**: si un asiento tiene un error, no queda nada guardado a medias.

Al aplicar la plantilla, los datos SUNAT (tipo de comprobante, documento del tercero, fecha de emisión, comprobante que modifica y detracción) se copian solos al bloque **Comprobante y datos SUNAT**.

En las ventas, compras y notas de crédito puedes ingresar el monto como **valor sin IGV** o como **total del comprobante**. Con el total, el IGV se calcula por diferencia, así que el asiento coincide exactamente con el comprobante.

| Plantilla | Qué registra |
|---|---|
| Venta | Pregunta **qué vendes**: mercadería (70121 / 70111), productos fabricados (70221 / 70211) o servicios (70321 / 70311). Factura o boleta con IGV, sin IGV o de exportación. Opcionalmente registra el **costo de ventas** (691 / 692 contra 20 / 21). Puede ser al contado, al crédito o mixta |
| Nota de crédito | Devolución, descuento o anulación de una venta, según lo vendido (709). Pide el comprobante que modifica |
| Cobranza de factura | Cobro de una venta al crédito |
| Anticipo de cliente / a proveedor | Factura de anticipo (122) o adelanto entregado (422) |
| Compra de inventario | Mercadería, materias primas, materiales auxiliares, suministros, repuestos, envases y embalajes. Registra la cuenta 60 y el ingreso al almacén (20/24/25/26 contra 61) |
| Compra de activo fijo | Terreno (33111, no se deprecia), edificación (33211), vehículo motorizado y no motorizado (33411 / 33421), maquinaria (33311), muebles (33511), enseres (33521), cómputo (33611), comunicación (33621), equipo de seguridad (33631), otros equipos (33691), software (34311) y licencias (34121). Avisa la tasa de depreciación y, en vehículos, el límite tributario |
| Servicio con factura | Más de 60 conceptos agrupados: servicios básicos (636), alquileres (635), transporte y viajes (631), asesorías (632), mantenimiento (634), publicidad (637), personal (62), tributos (64) y otros gastos de gestión (65). Admite detracción (12 %, 10 %, 4 %, 1.5 %, redondeada a enteros) |
| Pago de servicio | Los mismos conceptos (luz 6361, agua 6363, teléfono 6364, internet 6365, predial 6431, arbitrios 6432…), con el IGV separado como crédito fiscal. Los conceptos que **nunca llevan IGV** (tributos, multas, donaciones, vida ley) se registran sin IGV, y la vista previa avisa si son **no deducibles** |
| Recibo por honorarios | Gasto según el servicio (13 tipos) + retención de 4ta categoría del 8 % si supera S/ 1,500 (40172) + honorarios por pagar (424) |
| Importación | Valor CIF, ad valorem, IGV e IPM de aduana, percepción e ingreso al almacén |
| Pago a proveedor | Pago de una compra al crédito |
| Planilla / sueldos | Sueldo bruto (6211), ONP 13 % (4032) o AFP (417), renta de 5ta (40173), neto (4111), EsSalud 9 % (6271 / 4031) y el pago |
| Depósito o retiro | Traslados entre caja y banco |
| Préstamo recibido / Cuota de préstamo | Desembolso (4511) y cuotas con capital, intereses (67311) y seguros |
| Diferencia de cambio | Ganancia (7581) o pérdida (6581) al ajustar saldos en dólares |
| Depreciación mensual | Gasto 68 contra depreciación acumulada 39, según el tipo de activo (software: 68613 / 39613) |
| Aporte de capital | Suscripción (1421) y pago, contra acciones (5011) o participaciones (5012) |

> Las plantillas usan la **tasa de IGV** de *Configuración* (18 % o 10.5 %). Si la empresa usa la clase 9, el destino de los gastos se genera a fin de mes desde *Destino y cierre anual*; las plantillas ya no lo crean por su cuenta.

### Detalle de un asiento (`/asientos/<id>`)
Muestra la cabecera, los datos SUNAT, quién lo registró o editó y sus líneas. Desde aquí puedes:
- **Editar**: pide el motivo del cambio y no permite mover el asiento a otro mes.
- **Anular (crear reversa)**: pide el motivo.
- **Historial**: ver en la auditoría todos los cambios del asiento (para admin y contador).
- **Exportar a Excel**.

---

## 4. Reportes

| Reporte | Qué muestra |
|---|---|
| **Libro diario** (`/reportes/libro-diario`) | Todos los asientos en orden cronológico con sus líneas y totales. Filtra por fechas o por número de asiento. |
| **Libro mayor** (`/reportes/libro-mayor`) | Movimientos agrupados por cuenta, con el saldo de cada una. Filtra por cuenta (o por prefijo, ej. `42`) y por fechas. Exportable a Excel. |
| **Balance** (`/reportes/balance`) | Balance de comprobación: sumas del Debe y del Haber y saldos deudor y acreedor de cada cuenta. No incluye los asientos de cierre del ejercicio, para que al 31/12 no todo aparezca en cero. Exportable a Excel. |
| **Reporte anual** (`/reportes/anual`) | Consolidado del año: cuadre global, desglose mes por mes, totales por elemento del PCGE y las 10 cuentas con más movimiento. Exportable a Excel. |
| **Registros por mes** (`/reportes/registros`) | **Registro de Compras** y **Registro de Ventas** del mes: comprobante, tercero, base gravada, IGV, no gravadas, total, moneda, documento que modifica y detracción. Las notas de crédito salen en negativo. **Avisa los comprobantes con datos SUNAT incompletos.** Exportable a Excel (incluye un resumen de IGV por pagar). Sirve para comparar con la propuesta del SIRE de SUNAT. |
| **Reporte por RUC** (`/reportes/por-ruc`) | Compras y ventas acumuladas por cada proveedor o cliente. Útil para la DAOT. |
| **Estados financieros** (`/reportes/estados-financieros`) | **Estado de Situación Financiera** (activo, pasivo y patrimonio, con la comprobación de que cuadra), **Estado de Resultados por naturaleza** y **Estado de Resultados por función** (si usas la clase 9). Se elige el año y la fecha de corte; se puede imprimir o guardar en PDF. |

---

## 5. SUNAT

*Visible solo para administrador y contador.*

### Libros electrónicos (PLE) (`/ple`)
Genera los archivos **.txt** que se cargan en el **Programa de Libros Electrónicos (PLE) de SUNAT** para validarlos y enviarlos.

| Formato | Archivo |
|---|---|
| **5.1** | Libro Diario: cada línea de cada asiento del mes |
| **5.3** | Libro Diario, detalle del plan contable: las cuentas usadas en el mes |
| **6.1** | Libro Mayor: los mismos movimientos, ordenados por cuenta |

- Elige el año y el mes, revisa las **validaciones** (mes no cerrado, asientos descuadrados, cuentas inexistentes, falta del RUC de la empresa) y descarga cada archivo.
- El nombre del archivo sigue la nomenclatura de SUNAT (`LE` + RUC + periodo + libro + indicadores). Si el mes no tuvo operaciones, el archivo sale vacío con el indicador "sin información".
- Cada descarga queda registrada en la auditoría.

> Cierra el mes antes de descargar. Valida siempre los archivos en el PLE vigente antes de enviarlos, porque SUNAT actualiza los formatos periódicamente.

### Destino y cierre anual (`/ejercicio`)

**Asientos de destino** (solo si la empresa usa la clase 9, ver *Configuración*)
- Muestra mes a mes los gastos de las cuentas **62 a 68** frente a lo ya destinado (cuenta **79**).
- El botón **Generar** crea el asiento *Debe 9x / Haber 7911* por la diferencia, repartido según los porcentajes configurados (ej. 60 % en 94 Administración y 40 % en 95 Ventas). Si después registras más gastos, vuelves a generar y solo se agrega la diferencia.

**Cierre del ejercicio** (se habilita desde el 1 de enero del año siguiente)
Antes de cerrar, registra el impuesto a la renta, las participaciones, la depreciación y los ajustes, y genera los destinos pendientes. El cierre crea automáticamente:
1. **Cierre de las cuentas de resultado** (6, 7, 8 y 9) contra la 89.
2. **Traslado del resultado** de la 89 a la 59 (utilidades o pérdidas acumuladas).
3. **Cierre de las cuentas de balance** (1 a 5).
4. **Asiento de apertura** al 01/01 del año siguiente.

En el PLE, los asientos de cierre usan el correlativo **C** y la apertura el correlativo **A**. Para deshacer un cierre, se anulan esos asientos (queda en la auditoría).

---

## 6. Mantenimiento

| Apartado | Qué hace |
|---|---|
| **Entidades** (`/entidades`) | Catálogo de clientes y proveedores. Consulta un RUC en SUNAT (razón social, estado, condición, dirección) y lo guarda para reutilizarlo. |
| **Cierres de mes** (`/cierres`) | Cierra un mes para **bloquearlo**: no se pueden crear, editar ni anular asientos en ese periodo. Cerrar lo puede hacer el contador o el admin. **Reabrir solo lo puede hacer el administrador, con un motivo obligatorio** que queda en la auditoría. |
| **Importar Excel** (`/importar`) | Carga masiva de asientos: 1) descarga la plantilla, 2) súbela llena, 3) revisa la previsualización (indica qué asientos no cuadran) y 4) confirma. Si algún asiento cae en un mes cerrado, la importación se cancela completa. |
| **Auditoría** (`/auditoria`) | Bitácora de todo lo que pasa en el sistema: altas, ediciones (con los datos anteriores y los nuevos), anulaciones, cierres, reaperturas, exportaciones PLE e inicios de sesión. Muestra el usuario, la fecha y el motivo. **Nadie puede modificarla ni borrarla.** Filtra por entidad, ID y usuario. *(Admin y contador.)* |
| **Usuarios** (`/usuarios`) | Crear usuarios, cambiar su rol, cambiar su contraseña y activarlos o desactivarlos. Los usuarios no se eliminan para no perder la trazabilidad. *(Solo admin.)* |
| **Configuración** (`/configuracion`) | **RUC y razón social** de la empresa (necesarios para el PLE y los estados financieros), la **tasa de IGV** (18 % general o 10.5 % para MYPE de restaurantes y hoteles), si la empresa **usa la clase 9** y la **distribución de los destinos** (cuentas 9xxx y porcentajes, que deben sumar 100 %). *(Solo admin.)* |

---

## 7. Flujo de trabajo mensual recomendado

1. **Registrar** las operaciones del mes en *Crear asiento* (mejor con plantillas), completando los **datos SUNAT** del comprobante.
2. Revisar **Registros por mes**: corregir los comprobantes con datos incompletos y comparar con la propuesta del **SIRE**.
3. Si usas la clase 9, **generar el destino** del mes en *Destino y cierre anual*.
4. Revisar el **Balance** y el **Libro mayor**.
5. **Cerrar el mes** en *Cierres de mes*.
6. Descargar los **.txt del PLE** (5.1, 5.3 y 6.1), validarlos y enviarlos en el programa de SUNAT.
7. **A fin de año**: registrar los ajustes y el impuesto a la renta, revisar los **Estados financieros** y ejecutar el **cierre del ejercicio**.

---

## 8. Reglas importantes del sistema

- **Partida doble obligatoria**: ningún asiento se guarda si el Debe y el Haber no son iguales.
- **Los asientos nunca se borran.** Para corregir un error se **anula**: el sistema crea un asiento de **reversa** (Debe y Haber invertidos) y marca el original como anulado. Así se conserva la trazabilidad y la correlatividad que exige SUNAT. Si el mes del asiento sigue abierto, la reversa va en ese mismo mes; si ya está cerrado, va en el mes actual con estado PLE 9 (corrección).
- **Ediciones con historial**: toda edición pide un motivo y guarda los datos anteriores en la auditoría. Un asiento no puede moverse a otro mes.
- **Meses cerrados**: bloquean cualquier cambio en ese periodo hasta que un administrador los reabra con motivo.
- **Asientos del sistema** (destino, cierre y apertura): no se editan; si hay que corregirlos, se anulan y se vuelven a generar.
- **Notas de crédito y débito**: deben indicar el comprobante que modifican.
- **Moneda extranjera**: los libros siempre quedan en soles; el importe original en dólares se guarda aparte.
