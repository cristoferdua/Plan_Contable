/* =====================================================================
   Plantillas de asientos contables (PCGE) + interprete de lenguaje natural
   ---------------------------------------------------------------------
   - Plantillas.crear(ctx)      -> { clave: { nombre, campos, build(d) } }
   - Plantillas.TARJETAS        -> tarjetas del modal, agrupadas
   - Plantillas.interpretar(t)  -> sugerencias a partir de un texto libre
   Funciones puras (sin DOM) para poder probarlas con Node.
   Cada linea: { codigo, debe, haber, g (glosa), why (por que esta cuenta) }
   ===================================================================== */
(function (root) {
  'use strict';

  function round2(n) { return Math.round((Number(n) + Number.EPSILON) * 100) / 100; }
  function money(n) {
    return Number(n || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // ------------------------------------------------------------------ Catalogos
  // Todos los codigos estan verificados contra pcge_data.json (PCGE 2019) y son de
  // nivel de movimiento. "g" = grupo que se muestra en el selector.

  // Compras de inventario: cuenta de compra (60), almacen (2x) y variacion (61)
  var INVENTARIOS = {
    mercaderia:    { g: 'Inventarios', t: 'Mercaderia para revender', compra: '6011', almacen: '20111', variacion: '6111' },
    materia_prima: { g: 'Inventarios', t: 'Materias primas / insumos de produccion', compra: '602', almacen: '24111', variacion: '6121' },
    mat_aux:       { g: 'Inventarios', t: 'Materiales auxiliares', compra: '6031', almacen: '251', variacion: '6131' },
    suministros:   { g: 'Inventarios', t: 'Suministros (utiles, limpieza, combustible)', compra: '6032', almacen: '2524', variacion: '6132' },
    repuestos:     { g: 'Inventarios', t: 'Repuestos', compra: '6033', almacen: '253', variacion: '6133' },
    envases:       { g: 'Inventarios', t: 'Envases', compra: '6041', almacen: '261', variacion: '6141' },
    embalajes:     { g: 'Inventarios', t: 'Embalajes (cajas, bolsas)', compra: '6042', almacen: '262', variacion: '6142' }
  };

  // Activos fijos: cuenta del activo, tasa maxima de depreciacion tributaria,
  // cuenta de gasto por depreciacion (68) y de depreciacion acumulada (39).
  // tasa 0 / gasto null = no se deprecia (terrenos).
  var ACTIVOS = {
    terreno:      { g: 'Inmuebles', t: 'Terreno', cuenta: '33111', tasa: 0, gasto: null, acum: null },
    edificacion:  { g: 'Inmuebles', t: 'Edificacion (local, oficina, almacen)', cuenta: '33211', tasa: 5, gasto: '68312', acum: '39512' },
    vehiculo:     { g: 'Unidades de transporte', t: 'Vehiculo motorizado (carro, camioneta, moto)', cuenta: '33411', tasa: 20, gasto: '68314', acum: '39514' },
    vehiculo_nm:  { g: 'Unidades de transporte', t: 'Vehiculo no motorizado (remolque, carreta, bicicleta)', cuenta: '33421', tasa: 20, gasto: '68314', acum: '39514' },
    maquinaria:   { g: 'Maquinaria', t: 'Maquinaria y equipo de explotacion', cuenta: '33311', tasa: 10, gasto: '68313', acum: '39513' },
    muebles:      { g: 'Muebles y enseres', t: 'Muebles (escritorio, sillas, estantes)', cuenta: '33511', tasa: 10, gasto: '68315', acum: '39515' },
    enseres:      { g: 'Muebles y enseres', t: 'Enseres (menaje, utensilios)', cuenta: '33521', tasa: 10, gasto: '68315', acum: '39515' },
    computo:      { g: 'Equipos diversos', t: 'Equipo de computo (laptop, PC, impresora)', cuenta: '33611', tasa: 25, gasto: '68316', acum: '39516' },
    comunicacion: { g: 'Equipos diversos', t: 'Equipo de comunicacion (celular, radio, central)', cuenta: '33621', tasa: 10, gasto: '68316', acum: '39516' },
    seguridad:    { g: 'Equipos diversos', t: 'Equipo de seguridad (camaras, alarmas, extintores)', cuenta: '33631', tasa: 10, gasto: '68316', acum: '39516' },
    otros_equipos:{ g: 'Equipos diversos', t: 'Otros equipos (aire acondicionado, electrodomesticos)', cuenta: '33691', tasa: 10, gasto: '68316', acum: '39516' },
    software:     { g: 'Intangibles', t: 'Software / licencia permanente de programa', cuenta: '34311', tasa: 10, gasto: '68613', acum: '39613' },
    licencia:     { g: 'Intangibles', t: 'Licencia o concesion (derecho de uso)', cuenta: '34121', tasa: 10, gasto: '68611', acum: '39611' }
  };

  // Servicios y gastos (clases 62, 63, 64 y 65).
  // sinIgv: el concepto nunca lleva IGV (tributos, multas, donaciones).
  // nota: advertencia que se muestra en la vista previa.
  var SERVICIOS = {
    // 636 Servicios basicos
    luz:          { g: 'Servicios basicos', t: 'Luz / energia electrica', cuenta: '6361' },
    agua:         { g: 'Servicios basicos', t: 'Agua y desague', cuenta: '6363' },
    gas:          { g: 'Servicios basicos', t: 'Gas (natural o balon)', cuenta: '6362' },
    telefono:     { g: 'Servicios basicos', t: 'Telefono fijo y celular', cuenta: '6364' },
    internet:     { g: 'Servicios basicos', t: 'Internet', cuenta: '6365' },
    radio:        { g: 'Servicios basicos', t: 'Radio (comunicacion)', cuenta: '6366' },
    cable:        { g: 'Servicios basicos', t: 'Cable / TV de paga', cuenta: '6367' },
    // 635 Alquileres
    alq_terreno:  { g: 'Alquileres', t: 'Alquiler de terreno', cuenta: '6351' },
    alq_local:    { g: 'Alquileres', t: 'Alquiler de local, oficina o almacen', cuenta: '6352',
                    nota: 'Si el arrendador es persona natural sin negocio, retienes el 5% de renta de 1ra categoria (Formulario 1683).' },
    alq_maquina:  { g: 'Alquileres', t: 'Alquiler de maquinaria y equipo', cuenta: '6353' },
    alq_vehiculo: { g: 'Alquileres', t: 'Alquiler de vehiculo', cuenta: '6354' },
    alq_muebles:  { g: 'Alquileres', t: 'Alquiler de muebles y enseres', cuenta: '6355' },
    alq_equipos:  { g: 'Alquileres', t: 'Alquiler de equipos diversos (computo, impresoras)', cuenta: '6356' },
    // 631 Transporte, correos y viajes
    flete:        { g: 'Transporte y viajes', t: 'Transporte de carga / flete / courier', cuenta: '63111' },
    pasajes:      { g: 'Transporte y viajes', t: 'Pasajes, taxi, movilidad', cuenta: '63112' },
    correos:      { g: 'Transporte y viajes', t: 'Correo postal / mensajeria', cuenta: '6312' },
    alojamiento:  { g: 'Transporte y viajes', t: 'Hospedaje (viajes de trabajo)', cuenta: '6313' },
    alimentacion: { g: 'Transporte y viajes', t: 'Alimentacion (viajes de trabajo)', cuenta: '6314' },
    otros_viaje:  { g: 'Transporte y viajes', t: 'Otros gastos de viaje (peajes, estacionamiento)', cuenta: '6315' },
    // 632 Asesoria y consultoria
    asesoria:     { g: 'Asesoria y consultoria', t: 'Asesoria administrativa / consultoria', cuenta: '6321' },
    legal:        { g: 'Asesoria y consultoria', t: 'Asesoria legal y tributaria / notaria', cuenta: '6322' },
    contable:     { g: 'Asesoria y consultoria', t: 'Servicio contable / auditoria', cuenta: '6323' },
    marketing:    { g: 'Asesoria y consultoria', t: 'Asesoria de marketing (mercadotecnia)', cuenta: '6324' },
    ambiental:    { g: 'Asesoria y consultoria', t: 'Asesoria medioambiental', cuenta: '6325' },
    investigacion:{ g: 'Asesoria y consultoria', t: 'Investigacion y desarrollo', cuenta: '6326' },
    ases_produccion:{ g: 'Asesoria y consultoria', t: 'Asesoria de produccion', cuenta: '6327' },
    resp_social:  { g: 'Asesoria y consultoria', t: 'Responsabilidad social', cuenta: '6328' },
    ases_otros:   { g: 'Asesoria y consultoria', t: 'Otras asesorias (sistemas, seguridad, RR.HH.)', cuenta: '6329' },
    // 633 / 634 Produccion y mantenimiento
    maquila:      { g: 'Produccion y mantenimiento', t: 'Produccion encargada a terceros (maquila)', cuenta: '633' },
    mantenimiento:{ g: 'Produccion y mantenimiento', t: 'Mantenimiento y reparacion de activos (local, vehiculo, equipos)', cuenta: '6343' },
    mant_software:{ g: 'Produccion y mantenimiento', t: 'Mantenimiento de software / intangibles', cuenta: '6344' },
    // 637 Publicidad
    publicidad:   { g: 'Publicidad', t: 'Publicidad (anuncios, redes sociales, volantes)', cuenta: '6371' },
    publicaciones:{ g: 'Publicidad', t: 'Publicaciones (avisos en diarios, revistas)', cuenta: '6372' },
    rrpp:         { g: 'Publicidad', t: 'Relaciones publicas / eventos', cuenta: '6373' },
    // 639 Otros servicios
    bancarios:    { g: 'Otros servicios', t: 'Comisiones y gastos bancarios', cuenta: '6391',
                    nota: 'La mayoria de comisiones bancarias estan exoneradas de IGV: revisa si el cargo lo detalla.' },
    laboratorio:  { g: 'Otros servicios', t: 'Gastos de laboratorio (analisis, ensayos)', cuenta: '6392' },
    // 62 Gastos de personal
    capacitacion: { g: 'Personal', t: 'Capacitacion del personal (cursos, talleres)', cuenta: '624' },
    atencion_personal: { g: 'Personal', t: 'Atencion al personal (refrigerios, uniformes, agasajos)', cuenta: '625' },
    sctr:         { g: 'Personal', t: 'SCTR (seguro complementario de trabajo de riesgo)', cuenta: '6273' },
    vida_ley:     { g: 'Personal', t: 'Seguro vida ley', cuenta: '6274', sinIgv: true },
    eps:          { g: 'Personal', t: 'EPS / seguro de salud privado', cuenta: '6275' },
    // 64 Tributos
    itf:          { g: 'Tributos y municipalidad', t: 'ITF (impuesto a las transacciones financieras)', cuenta: '6412', sinIgv: true },
    predial:      { g: 'Tributos y municipalidad', t: 'Impuesto predial', cuenta: '6431', sinIgv: true },
    arbitrios:    { g: 'Tributos y municipalidad', t: 'Arbitrios municipales (limpieza, serenazgo, parques)', cuenta: '6432', sinIgv: true },
    vehicular:    { g: 'Tributos y municipalidad', t: 'Impuesto al patrimonio vehicular', cuenta: '6433', sinIgv: true },
    licencia_func:{ g: 'Tributos y municipalidad', t: 'Licencia de funcionamiento / tramites municipales', cuenta: '6434', sinIgv: true },
    trib_otros:   { g: 'Tributos y municipalidad', t: 'Otros tributos municipales (anuncios, Defensa Civil)', cuenta: '6439', sinIgv: true },
    interes_trib: { g: 'Tributos y municipalidad', t: 'Intereses moratorios de SUNAT', cuenta: '6451', sinIgv: true,
                    nota: 'Los intereses moratorios y multas tributarias NO son deducibles para el impuesto a la renta.' },
    multa_trib:   { g: 'Tributos y municipalidad', t: 'Multas tributarias (SUNAT)', cuenta: '6453', sinIgv: true,
                    nota: 'Las multas tributarias NO son deducibles para el impuesto a la renta (adicion en la DJ anual).' },
    // 65 Otros gastos de gestion
    seguros:      { g: 'Otros gastos de gestion', t: 'Seguros (polizas, SOAT, robo, incendio)', cuenta: '651' },
    regalias:     { g: 'Otros gastos de gestion', t: 'Regalias (uso de marcas, franquicias)', cuenta: '652' },
    suscripciones:{ g: 'Otros gastos de gestion', t: 'Suscripciones (software en la nube, hosting, revistas)', cuenta: '653' },
    licencias:    { g: 'Otros gastos de gestion', t: 'Licencias y derechos de vigencia (anuales)', cuenta: '654' },
    sum_gasto:    { g: 'Otros gastos de gestion', t: 'Suministros de consumo inmediato (sin pasar por almacen)', cuenta: '656' },
    donaciones:   { g: 'Otros gastos de gestion', t: 'Donaciones', cuenta: '6591', sinIgv: true,
                    nota: 'Las donaciones solo son deducibles si el donatario esta calificado por SUNAT (limite 10% de la renta neta).' },
    sanciones:    { g: 'Otros gastos de gestion', t: 'Multas y sanciones administrativas (municipales, SUNAFIL)', cuenta: '6592', sinIgv: true,
                    nota: 'Las multas y sanciones NO son deducibles para el impuesto a la renta.' },
    gestion_otros:{ g: 'Otros gastos de gestion', t: 'Otros gastos de gestion', cuenta: '6593' },
    otro:         { g: 'Otra cuenta', t: 'Otra cuenta (buscar en el plan contable)', cuenta: null }
  };

  // Que se vende: cuentas de ingreso (70), costo de ventas (69) y almacen.
  var VENDIDO = {
    mercaderia: { t: 'Mercaderia (compras para revender)', local: '70121', exp: '70111', costoLocal: '69121', costoExp: '69111', almacen: '20111', nc: '70911', ncExp: '70901' },
    productos:  { t: 'Productos terminados (los fabricas tu)', local: '70221', exp: '70211', costoLocal: '69221', costoExp: '69211', almacen: '21111', nc: '70931', ncExp: '70921' },
    servicios:  { t: 'Servicios', local: '70321', exp: '70311', costoLocal: null, costoExp: null, almacen: null, nc: '70941', ncExp: '70941' }
  };

  // Opciones de un catalogo para un <select>. Incluye el codigo PCGE y el grupo.
  function opciones(cat, filtro) {
    return Object.keys(cat).filter(function (k) { return !filtro || filtro(cat[k]); }).map(function (k) {
      var c = cat[k], cod = c.cuenta || c.compra || c.local;
      return { v: k, t: c.t + (cod ? '  ·  ' + cod : ''), g: c.g };
    });
  }

  var MEDIO = { efectivo: '1011', banco: '1041' };

  // Monto ingresado como valor sin IGV o como total con IGV. Con el total, el IGV es la
  // diferencia (asi base + IGV = total exacto, como en el comprobante).
  function montos(d, tasa) {
    var m = round2(d.base);
    if (d.ingreso === 'total' && tasa > 0) {
      var b = round2(m / (1 + tasa));
      return { base: b, igv: round2(m - b), total: m };
    }
    var i = round2(m * tasa);
    return { base: m, igv: i, total: round2(m + i) };
  }

  // ------------------------------------------------------------------ Campos comunes
  var F = {
    doc: function (label, ph, req) {
      return { id: 'numero_documento', label: label, tipo: 'text', req: req !== false, placeholder: ph || 'F001-1234' };
    },
    tipoCpCompra: { id: 'tipo_cp', label: 'Tipo de comprobante', tipo: 'select', opts: [
      { v: '01', t: '01 - Factura' }, { v: '03', t: '03 - Boleta de venta' },
      { v: '12', t: '12 - Ticket de maquina registradora' }, { v: '14', t: '14 - Recibo de servicios publicos' }
    ]},
    tipoCpVenta: { id: 'tipo_cp', label: 'Tipo de comprobante emitido', tipo: 'select', opts: [
      { v: '01', t: '01 - Factura' }, { v: '03', t: '03 - Boleta de venta' }
    ]},
    conIgv: { id: 'con_igv', label: 'El comprobante tiene IGV?', tipo: 'select', opts: [
      { v: 'si', t: 'Si, tiene IGV' }, { v: 'no', t: 'No (exonerado, inafecto o proveedor RUS)' }
    ]},
    forma: function (verbo) {
      return { id: 'forma', label: verbo, tipo: 'select', opts: [
        { v: 'contado', t: 'Al contado (100% ahora)' },
        { v: 'credito', t: 'Al credito (100% despues)' },
        { v: 'mixto', t: 'Mixto (parte contado, parte credito)' }
      ]};
    },
    medio: function (label) {
      return { id: 'medio', label: label || 'Caja o banco?', tipo: 'select', showIf: { forma: ['contado', 'mixto'] }, opts: [
        { v: 'efectivo', t: 'Caja (efectivo)' }, { v: 'banco', t: 'Banco (transferencia, Yape/Plin, tarjeta)' }
      ]};
    },
    pct: { id: 'pct_contado', label: '% pagado al contado (el resto queda al credito)', tipo: 'num', showIf: { forma: 'mixto' }, placeholder: '40' },
    ingreso: { id: 'ingreso', label: 'El monto que ingresas es...', tipo: 'select', opts: [
      { v: 'base', t: 'Valor sin IGV (base imponible)' }, { v: 'total', t: 'Total del comprobante (IGV incluido)' }] },
    glosa: function (ph) { return { id: 'glosa', label: 'Glosa / detalle', tipo: 'text', placeholder: ph || '' }; }
  };

  // Asiento de pago o cobro segun forma (contado / mixto). Devuelve { asiento, sufijo }
  // El sufijo [MIXTO: ...] lo usa la lista de asientos para calcular el saldo pendiente.
  function cancelacion(d, total, cuentaCxc, esCompra, g, n) {
    var monto = 0, sufijo = '', pct = 0;
    if (d.forma === 'contado') monto = total;
    else if (d.forma === 'mixto') {
      pct = Math.min(Math.max(Number(d.pct_contado) || 0, 0), 100);
      monto = round2(total * pct / 100);
      sufijo = ' [MIXTO: ' + pct + '% contado S/ ' + money(monto) + ' - ' + round2(100 - pct) +
               '% credito S/ ' + money(round2(total - monto)) + ']';
    }
    if (monto <= 0) return { asiento: null, sufijo: sufijo };
    var medio = MEDIO[d.medio] || '1011';
    var parcial = d.forma === 'mixto' ? 'parcial ' : '';
    var lineas = esCompra
      ? [{ codigo: cuentaCxc, debe: monto, haber: 0, g: g, why: 'Baja la deuda con el proveedor' },
         { codigo: medio, debe: 0, haber: monto, g: 'Pago', why: 'Sale el dinero de ' + (medio === '1041' ? 'banco' : 'caja') }]
      : [{ codigo: medio, debe: monto, haber: 0, g: 'Cobro', why: 'Entra el dinero a ' + (medio === '1041' ? 'banco' : 'caja') },
         { codigo: cuentaCxc, debe: 0, haber: monto, g: g, why: 'Baja lo que el cliente te debe' }];
    return { asiento: { glosa: n + ') Cancelacion ' + parcial + '- ' + g + sufijo, lineas: lineas }, sufijo: sufijo };
  }

  // ------------------------------------------------------------------ Plantillas
  function crear(ctx) {
    ctx = ctx || {};
    var IGV = typeof ctx.igv === 'number' ? ctx.igv : 0.18;
    var usa9 = !!ctx.usaClase9;
    var notaDestino = usa9 ? 'El destino a la clase 9 de este gasto se genera a fin de mes en "Destino y cierre anual".' : null;

    return {
      // ================================================== VENTAS
      venta: {
        nombre: 'Venta',
        campos: [
          F.tipoCpVenta,
          F.doc('N° de comprobante emitido (serie-numero)', 'F001-2559 o B001-4588'),
          { id: 'que_vendes', label: 'Que vendes?', tipo: 'select', opts: opciones(VENDIDO) },
          { id: 'tipo_venta', label: 'Tipo de venta', tipo: 'select', opts: [
            { v: 'local', t: 'Venta local (en Peru)' }, { v: 'exportacion', t: 'Exportacion (sin IGV)' }] },
          { id: 'con_igv', label: 'La venta tiene IGV?', tipo: 'select', showIf: { tipo_venta: 'local' }, opts: [
            { v: 'si', t: 'Si (' + round2(IGV * 100) + '%)' }, { v: 'no', t: 'No (exonerada / inafecta)' }] },
          F.ingreso,
          { id: 'base', label: 'Monto', tipo: 'num', req: true, placeholder: '1000.00' },
          { id: 'costo', label: 'Costo de lo vendido (opcional, registra el costo de ventas)', tipo: 'num', showIf: { que_vendes: ['mercaderia', 'productos'] }, placeholder: '600.00' },
          F.forma('Como te paga el cliente?'), F.medio('Donde entra el dinero?'), F.pct,
          F.glosa('Venta segun factura F001-...')
        ],
        build: function (d) {
          var exp = d.tipo_venta === 'exportacion';
          var tasa = (!exp && d.con_igv !== 'no') ? IGV : 0;
          var mt = montos(d, tasa), base = mt.base, igv = mt.igv, total = mt.total;
          var v = VENDIDO[d.que_vendes] || VENDIDO.mercaderia;
          var queTxt = v.t.split(' (')[0].toLowerCase();
          var g = d.glosa || (exp ? 'Venta de exportacion' : 'Venta');
          var lineas = [{ codigo: '1212', debe: total, haber: 0, g: g, why: 'El cliente te debe el total del comprobante' }];
          if (igv > 0) lineas.push({ codigo: '40111', debe: 0, haber: igv, g: 'IGV de la venta', why: 'IGV que cobras y debes pagar a SUNAT' });
          lineas.push({ codigo: exp ? v.exp : v.local, debe: 0, haber: base, g: g,
                        why: 'Venta de ' + queTxt + (exp ? ' al exterior (exportacion)' : ' en el pais') });
          var asientos = [{ glosa: '1) Provision - ' + g, lineas: lineas }];
          var notas = [];
          if (v.almacen && d.costo > 0) {
            asientos.push({ glosa: (asientos.length + 1) + ') Costo de ventas - ' + g, lineas: [
              { codigo: exp ? v.costoExp : v.costoLocal, debe: round2(d.costo), haber: 0, g: 'Costo de lo vendido', why: 'Costo de ' + queTxt + ' vendida (gasto)' },
              { codigo: v.almacen, debe: 0, haber: round2(d.costo), g: 'Salida de almacen', why: 'Sale del almacen' }
            ]});
          } else if (v.almacen) {
            notas.push('Sin costo de ventas: el margen real no se vera hasta registrar la salida de almacen (69 / ' + v.almacen.slice(0, 2) + ').');
          }
          var c = cancelacion(d, total, '1212', false, g, asientos.length + 1);
          if (c.asiento) asientos.push(c.asiento);
          if (c.sufijo) asientos[0].glosa += c.sufijo;
          if (exp) notas.push('Exportacion: registra la operacion en USD con el tipo de cambio y adjunta la DAM de exportacion.');
          return { asientos: asientos, notas: notas, sunat: { tipo_comprobante: d.tipo_cp } };
        }
      },

      nota_credito: {
        nombre: 'Nota de credito (devolucion o descuento a un cliente)',
        campos: [
          F.doc('N° de la nota de credito (serie-numero)', 'FC01-15'),
          { id: 'ref_doc', label: 'Comprobante que modifica (serie-numero)', tipo: 'text', req: true, placeholder: 'F001-2559' },
          { id: 'ref_tipo', label: 'Tipo del comprobante que modifica', tipo: 'select', opts: [
            { v: '01', t: '01 - Factura' }, { v: '03', t: '03 - Boleta' }] },
          { id: 'ref_fecha', label: 'Fecha del comprobante que modifica', tipo: 'date' },
          { id: 'que_vendes', label: 'Que se habia vendido?', tipo: 'select', opts: opciones(VENDIDO) },
          { id: 'exportacion', label: 'La venta original fue...', tipo: 'select', opts: [
            { v: 'no', t: 'Venta local' }, { v: 'si', t: 'Exportacion' }] },
          { id: 'motivo', label: 'Motivo', tipo: 'select', opts: [
            { v: 'devolucion', t: 'Devolucion de mercaderia' }, { v: 'descuento', t: 'Descuento o bonificacion posterior' },
            { v: 'anulacion', t: 'Anulacion de la operacion' }] },
          F.conIgv, F.ingreso,
          { id: 'base', label: 'Monto', tipo: 'num', req: true, placeholder: '500.00' },
          { id: 'reembolso', label: 'Como se compensa al cliente?', tipo: 'select', opts: [
            { v: 'credito', t: 'Se descuenta de lo que el cliente debe' },
            { v: 'efectivo', t: 'Se le devuelve efectivo (caja)' }, { v: 'banco', t: 'Transferencia desde banco' }] },
          F.glosa('NC por devolucion de F001-...')
        ],
        build: function (d) {
          var mt = montos(d, d.con_igv === 'no' ? 0 : IGV), base = mt.base, igv = mt.igv, total = mt.total;
          var g = d.glosa || ('Nota de credito ' + (d.motivo || '') + ' de ' + (d.ref_doc || ''));
          var vnc = VENDIDO[d.que_vendes] || VENDIDO.mercaderia;
          var lineas = [{ codigo: d.exportacion === 'si' ? vnc.ncExp : vnc.nc, debe: base, haber: 0, g: g, why: 'Devoluciones sobre ventas: reduce la venta original' }];
          if (igv > 0) lineas.push({ codigo: '40111', debe: igv, haber: 0, g: 'IGV de la NC', why: 'Se reduce el IGV que debias por la venta' });
          var cta = d.reembolso === 'efectivo' ? '1011' : d.reembolso === 'banco' ? '1041' : '1212';
          lineas.push({ codigo: cta, debe: 0, haber: total, g: g, why: cta === '1212' ? 'El cliente te debe menos' : 'Devuelves el dinero' });
          var ref = (d.ref_doc || '').toUpperCase().split('-');
          return {
            asientos: [{ glosa: g, lineas: lineas }],
            notas: ['Si devolvieron mercaderia, registra tambien su reingreso al almacen (20 / 69).'],
            sunat: { tipo_comprobante: '07', ref_tipo_comprobante: d.ref_tipo || '01', ref_serie: ref[0] || '',
                     ref_numero: ref.slice(1).join('-'), ref_fecha: d.ref_fecha || '' }
          };
        }
      },

      cobranza: {
        nombre: 'Cobranza de factura',
        campos: [
          { id: 'monto', label: 'Monto cobrado', tipo: 'num', req: true, placeholder: '1180.00' },
          { id: 'destino', label: 'Donde entra el dinero?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco' }, { v: 'efectivo', t: 'Caja (efectivo)' }] },
          F.glosa('Cobranza factura F001-...')
        ],
        build: function (d) {
          var m = round2(d.monto), medio = MEDIO[d.destino] || '1041', g = d.glosa || 'Cobranza de factura';
          return { asientos: [{ glosa: g, lineas: [
            { codigo: medio, debe: m, haber: 0, g: g, why: 'Entra el dinero' },
            { codigo: '1212', debe: 0, haber: m, g: g, why: 'Baja la cuenta por cobrar del cliente' }] }] };
        }
      },

      anticipo: {
        nombre: 'Anticipo (adelanto)',
        campos: [
          { id: 'tipo', label: 'Que tipo de anticipo?', tipo: 'select', opts: [
            { v: 'recibido', t: 'Recibo un adelanto de un cliente' }, { v: 'otorgado', t: 'Doy un adelanto a un proveedor' }] },
          F.doc('N° de la factura de anticipo (serie-numero)', 'F001-2600'),
          { id: 'con_igv', label: 'La operacion tiene IGV?', tipo: 'select', showIf: { tipo: 'recibido' }, opts: [
            { v: 'si', t: 'Si' }, { v: 'no', t: 'No' }] },
          { id: 'monto', label: 'Monto total del anticipo', tipo: 'num', req: true, placeholder: '1180.00' },
          { id: 'medio', label: 'Caja o banco?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco' }, { v: 'efectivo', t: 'Caja (efectivo)' }] },
          F.glosa('Anticipo segun contrato ...')
        ],
        build: function (d) {
          var total = round2(d.monto), medio = MEDIO[d.medio] || '1041';
          if (d.tipo === 'otorgado') {
            var g1 = d.glosa || 'Anticipo a proveedor';
            return {
              asientos: [{ glosa: g1, lineas: [
                { codigo: '422', debe: total, haber: 0, g: g1, why: 'Anticipos otorgados: el proveedor te debe el bien o servicio' },
                { codigo: medio, debe: 0, haber: total, g: g1, why: 'Sale el dinero' }] }],
              notas: ['Cuando el proveedor emita la factura, registrala con la plantilla Compra y aplica el anticipo (Debe 4212 / Haber 422).']
            };
          }
          var base = d.con_igv === 'no' ? total : round2(total / (1 + IGV)), igv = round2(total - base);
          var g = d.glosa || 'Anticipo recibido de cliente';
          var l = [{ codigo: '1212', debe: total, haber: 0, g: g, why: 'Factura de anticipo por cobrar' }];
          if (igv > 0) l.push({ codigo: '40111', debe: 0, haber: igv, g: 'IGV del anticipo', why: 'El anticipo esta gravado con IGV al emitir la factura' });
          l.push({ codigo: '122', debe: 0, haber: base, g: g, why: 'Anticipos recibidos: le debes el bien o servicio al cliente' });
          return {
            asientos: [
              { glosa: '1) Factura de anticipo - ' + g, lineas: l },
              { glosa: '2) Cobro del anticipo - ' + g, lineas: [
                { codigo: medio, debe: total, haber: 0, g: g, why: 'Entra el dinero' },
                { codigo: '1212', debe: 0, haber: total, g: g, why: 'Se cobra la factura de anticipo' }] }
            ],
            notas: ['Al emitir la factura final, descuenta el anticipo (Debe 122) y emite la factura por la diferencia.'],
            sunat: { tipo_comprobante: '01' }
          };
        }
      },

      // ================================================== COMPRAS Y GASTOS
      compra: {
        nombre: 'Compra',
        campos: [
          { id: 'categoria', label: 'Que compraste?', tipo: 'select', opts: [
            { v: 'inventario', t: 'Inventario (mercaderia, insumos, suministros)' },
            { v: 'activo', t: 'Activo fijo (vehiculo, computadora, muebles, maquinaria)' },
            { v: 'servicio', t: 'Servicio o gasto con factura' }] },
          { id: 'sub_inv', label: 'Tipo de inventario', tipo: 'select', showIf: { categoria: 'inventario' }, opts: opciones(INVENTARIOS) },
          { id: 'sub_act', label: 'Tipo de activo', tipo: 'select', showIf: { categoria: 'activo' }, opts: opciones(ACTIVOS) },
          { id: 'detalle_activo', label: 'Descripcion del activo (marca, modelo, placa o serie)', tipo: 'text', showIf: { categoria: 'activo' }, placeholder: 'Toyota Hilux 2026, placa ABC-123' },
          { id: 'sub_serv', label: 'Tipo de servicio', tipo: 'select', showIf: { categoria: 'servicio' }, opts: opciones(SERVICIOS) },
          { id: 'cuenta_otro', label: 'Cuenta contable (busca por codigo o nombre)', tipo: 'cuenta', showIf: { sub_serv: 'otro' }, placeholder: 'Ej: 6592 o "vigilancia"', elemento: '6' },
          F.tipoCpCompra,
          F.doc('N° comprobante del proveedor (serie-numero)', 'F001-1234'),
          F.conIgv, F.ingreso,
          { id: 'base', label: 'Monto', tipo: 'num', req: true, placeholder: '1000.00' },
          { id: 'detraccion', label: 'Esta sujeta a detraccion?', tipo: 'select', opts: [
            { v: '0', t: 'No' }, { v: '12', t: 'Si - 12% (mayoria de servicios)' }, { v: '10', t: 'Si - 10%' },
            { v: '4', t: 'Si - 4%' }, { v: '1.5', t: 'Si - 1.5%' }] },
          F.forma('Como pagas?'), F.medio('Con que pagas?'), F.pct,
          F.glosa('Compra segun factura F001-...')
        ],
        build: function (d) {
          var sinIgvServ = d.categoria === 'servicio' && SERVICIOS[d.sub_serv] && SERVICIOS[d.sub_serv].sinIgv;
          var mt = montos(d, (d.con_igv === 'no' || sinIgvServ) ? 0 : IGV), base = mt.base, igv = mt.igv, total = mt.total;
          var g = d.glosa || 'Compra';
          var asientos = [], notas = [], prov = [];
          var cat = d.categoria || 'inventario';
          if (sinIgvServ && d.con_igv !== 'no') notas.push('Este concepto no lleva IGV: se registro sin IGV.');

          if (cat === 'activo') {
            var a = ACTIVOS[d.sub_act] || ACTIVOS.computo;
            if (d.detalle_activo) g = (d.glosa || ('Compra de ' + a.t.split(' (')[0].toLowerCase())) + ' - ' + d.detalle_activo;
            prov.push({ codigo: a.cuenta, debe: base, haber: 0, g: g,
                        why: a.tasa > 0 ? 'Activo fijo: va directo a la clase 3 (no a gastos). Se deprecia hasta ' + a.tasa + '% anual'
                                        : 'Activo fijo: va directo a la clase 3. Los terrenos no se deprecian' });
            if (a.gasto) notas.push('Registra la depreciacion mensual con la plantilla "Depreciacion" (' + a.gasto + ' / ' + a.acum + ').');
            if (d.sub_act === 'terreno' || d.sub_act === 'edificacion') {
              notas.push('La compra de inmuebles a una empresa constructora (primera venta) esta gravada con IGV solo en la parte de la construccion; el terreno no paga IGV.');
            }
            if (d.sub_act === 'vehiculo') {
              notas.push('Vehiculos de categoria A2, A3 y A4: si los usa la administracion, la depreciacion es deducible solo hasta un costo de 30 UIT. Confirmalo con tu contador.');
              notas.push('El IGV es credito fiscal solo si el vehiculo se usa en el giro del negocio.');
            }
          } else if (cat === 'servicio') {
            var s = SERVICIOS[d.sub_serv] || SERVICIOS.otro;
            var cta = s.cuenta || (d.cuenta_otro || '').trim();
            prov.push({ codigo: cta || '????', debe: base, haber: 0, g: g, why: 'Gasto: ' + s.t });
            if (s.nota) notas.push(s.nota);
            if (notaDestino) notas.push(notaDestino);
          } else {
            var inv = INVENTARIOS[d.sub_inv] || INVENTARIOS.mercaderia;
            prov.push({ codigo: inv.compra, debe: base, haber: 0, g: g, why: 'Compra de ' + inv.t.toLowerCase() + ' (cuenta 60)' });
          }
          if (igv > 0) prov.push({ codigo: '40111', debe: igv, haber: 0, g: 'IGV credito fiscal', why: 'IGV que pagaste y descuentas del IGV de tus ventas' });
          prov.push({ codigo: '4212', debe: 0, haber: total, g: g, why: 'Le debes al proveedor el total del comprobante' });
          asientos.push({ glosa: '1) Provision - ' + g, lineas: prov });

          if (cat === 'inventario') {
            var i2 = INVENTARIOS[d.sub_inv] || INVENTARIOS.mercaderia;
            asientos.push({ glosa: '2) Ingreso a almacen - ' + g, lineas: [
              { codigo: i2.almacen, debe: base, haber: 0, g: g, why: 'Entra al almacen (inventario)' },
              { codigo: i2.variacion, debe: 0, haber: base, g: g, why: 'Variacion de existencias: neutraliza la cuenta 60' }] });
          }

          // Detraccion: el comprador deposita el % en la cuenta del proveedor en el Banco de la Nacion.
          // SUNAT exige el monto redondeado a enteros.
          var pctDet = Number(d.detraccion) || 0;
          var det = pctDet > 0 ? Math.round(total * pctDet / 100) : 0;
          var pagable = round2(total - det);
          var c = cancelacion(d, pagable, '4212', true, g, asientos.length + 1);
          if (c.asiento) asientos.push(c.asiento);
          if (c.sufijo) asientos[0].glosa += c.sufijo;
          if (det > 0) {
            if (d.forma === 'credito') {
              notas.push('Detraccion de S/ ' + money(det) + ': depositala en el Banco de la Nacion al pagar (Debe 4212 / Haber 1041) y anota la constancia.');
            } else {
              asientos.push({ glosa: (asientos.length + 1) + ') Deposito de detraccion - ' + g, lineas: [
                { codigo: '4212', debe: det, haber: 0, g: 'Detraccion ' + pctDet + '%', why: 'Parte de la deuda se paga depositando la detraccion' },
                { codigo: '1041', debe: 0, haber: det, g: 'Deposito Banco de la Nacion', why: 'Deposito en la cuenta de detracciones del proveedor' }] });
              notas.push('Anota el N° de constancia de deposito en "Detraccion, retencion y percepcion".');
            }
          }
          return { asientos: asientos, notas: notas,
                   sunat: { tipo_comprobante: d.tipo_cp, detraccion_monto: det > 0 ? String(det) : '' } };
        }
      },

      gasto: {
        nombre: 'Pago de servicio o gasto',
        campos: [
          { id: 'sub_serv', label: 'Que pagaste?', tipo: 'select', opts: opciones(SERVICIOS) },
          { id: 'cuenta_otro', label: 'Cuenta contable (busca por codigo o nombre)', tipo: 'cuenta', showIf: { sub_serv: 'otro' }, placeholder: 'Ej: 6592 o "vigilancia"', elemento: '6' },
          F.tipoCpCompra,
          F.doc('N° del comprobante o recibo', 'S001-77', false),
          F.conIgv,
          { id: 'monto', label: 'Total pagado (con IGV si tiene)', tipo: 'num', req: true, placeholder: '150.00' },
          { id: 'desde', label: 'Como lo pagas?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco (transferencia, debito, Yape/Plin)' }, { v: 'efectivo', t: 'Caja (efectivo)' },
            { v: 'credito', t: 'Queda pendiente de pago' }] },
          F.glosa('Recibo de luz de octubre')
        ],
        build: function (d) {
          var s = SERVICIOS[d.sub_serv] || SERVICIOS.otro;
          var cta = s.cuenta || (d.cuenta_otro || '').trim() || '????';
          var sinIgv = d.con_igv === 'no' || !!s.sinIgv;
          var total = round2(d.monto), base = sinIgv ? total : round2(total / (1 + IGV)), igv = round2(total - base);
          var g = d.glosa || s.t;
          var pago = d.desde === 'credito' ? '4212' : (MEDIO[d.desde] || '1041');
          var l = [{ codigo: cta, debe: base, haber: 0, g: g, why: 'Gasto: ' + s.t }];
          if (igv > 0) l.push({ codigo: '40111', debe: igv, haber: 0, g: 'IGV credito fiscal', why: 'IGV incluido en el total (' + round2(IGV * 100) + '%)' });
          l.push({ codigo: pago, debe: 0, haber: total, g: g,
                   why: pago === '4212' ? 'Queda como deuda con el proveedor' : 'Sale el dinero de ' + (pago === '1041' ? 'banco' : 'caja') });
          var notas = [];
          if (s.sinIgv && d.con_igv !== 'no') notas.push('Este concepto no lleva IGV: se registro el total como gasto.');
          if (s.nota) notas.push(s.nota);
          if (notaDestino) notas.push(notaDestino);
          if (igv > 0 && !d.numero_documento) notas.push('Sin N° de comprobante el IGV no se podra usar como credito fiscal.');
          return { asientos: [{ glosa: g, lineas: l }], notas: notas, sunat: { tipo_comprobante: d.tipo_cp } };
        }
      },

      honorarios: {
        nombre: 'Recibo por honorarios (4ta categoria)',
        campos: [
          F.doc('N° del recibo por honorarios electronico', 'E001-123'),
          { id: 'sub_hon', label: 'Que servicio presto?', tipo: 'select', opts: [
            { g: 'Asesoria y consultoria', v: '6321', t: 'Asesoria / consultoria administrativa  ·  6321' },
            { g: 'Asesoria y consultoria', v: '6322', t: 'Asesoria legal o tributaria / abogado  ·  6322' },
            { g: 'Asesoria y consultoria', v: '6323', t: 'Servicio contable / auditoria  ·  6323' },
            { g: 'Asesoria y consultoria', v: '6324', t: 'Marketing  ·  6324' },
            { g: 'Asesoria y consultoria', v: '6326', t: 'Investigacion y desarrollo  ·  6326' },
            { g: 'Asesoria y consultoria', v: '6327', t: 'Asesoria de produccion (ingeniero, tecnico)  ·  6327' },
            { g: 'Asesoria y consultoria', v: '6329', t: 'Otras asesorias (sistemas, programador, RR.HH.)  ·  6329' },
            { g: 'Otros servicios', v: '6343', t: 'Mantenimiento / reparacion de activos  ·  6343' },
            { g: 'Otros servicios', v: '6344', t: 'Mantenimiento de software  ·  6344' },
            { g: 'Otros servicios', v: '6371', t: 'Publicidad / diseno grafico  ·  6371' },
            { g: 'Otros servicios', v: '6373', t: 'Eventos / relaciones publicas  ·  6373' },
            { g: 'Otros servicios', v: '624', t: 'Capacitacion al personal (instructor)  ·  624' },
            { g: 'Otros servicios', v: '63112', t: 'Movilidad / chofer  ·  63112' }] },
          { id: 'bruto', label: 'Monto bruto del recibo', tipo: 'num', req: true, placeholder: '2000.00' },
          { id: 'retener', label: 'Retencion del 8%', tipo: 'select', opts: [
            { v: 'auto', t: 'Automatica (si el recibo supera S/ 1,500)' }, { v: 'no', t: 'No retener (tiene suspension de 4ta)' }] },
          { id: 'forma', label: 'Como pagas?', tipo: 'select', opts: [
            { v: 'contado', t: 'Pago ahora' }, { v: 'credito', t: 'Queda por pagar' }] },
          F.medio('Con que pagas?'),
          F.glosa('Honorarios por asesoria de ...')
        ],
        build: function (d) {
          var bruto = round2(d.bruto);
          var ret = (d.retener !== 'no' && bruto > 1500) ? round2(bruto * 0.08) : 0;
          var neto = round2(bruto - ret), g = d.glosa || 'Recibo por honorarios';
          var l = [{ codigo: d.sub_hon || '6321', debe: bruto, haber: 0, g: g, why: 'Gasto por el servicio del profesional independiente' }];
          if (ret > 0) l.push({ codigo: '40172', debe: 0, haber: ret, g: 'Retencion 4ta categoria 8%', why: 'Retienes el 8% y lo pagas a SUNAT en el PLAME' });
          l.push({ codigo: '424', debe: 0, haber: neto, g: g, why: 'Honorarios por pagar (neto de retencion)' });
          var asientos = [{ glosa: '1) Provision - ' + g, lineas: l }];
          if (d.forma !== 'credito') {
            var medio = MEDIO[d.medio] || '1041';
            asientos.push({ glosa: '2) Pago - ' + g, lineas: [
              { codigo: '424', debe: neto, haber: 0, g: g, why: 'Se cancela la deuda' },
              { codigo: medio, debe: 0, haber: neto, g: g, why: 'Sale el dinero' }] });
          }
          var notas = ['El recibo por honorarios no va al registro de compras: se declara en el PLAME (4ta categoria).'];
          if (d.retener === 'no' && bruto > 1500) notas.push('Pide y guarda la constancia de suspension de retenciones del profesional.');
          return { asientos: asientos, notas: notas, sunat: { tipo_comprobante: '02' } };
        }
      },

      importacion: {
        nombre: 'Importacion (DUA / DAM)',
        campos: [
          F.doc('N° de la DAM (serie-numero)', '118-2026-10-012345'),
          { id: 'sub_inv', label: 'Que importaste?', tipo: 'select', opts: opciones(INVENTARIOS) },
          { id: 'cif', label: 'Valor CIF en soles (FOB + flete + seguro)', tipo: 'num', req: true, placeholder: '20000.00' },
          { id: 'advalorem', label: 'Ad valorem (%)', tipo: 'select', opts: [
            { v: '0', t: '0%' }, { v: '6', t: '6%' }, { v: '11', t: '11%' }] },
          { id: 'percepcion', label: 'Percepcion del IGV (%)', tipo: 'select', opts: [
            { v: '3.5', t: '3.5% (importador habitual)' }, { v: '10', t: '10% (primera importacion / no habido)' },
            { v: '5', t: '5% (bienes usados)' }, { v: '0', t: 'No aplica' }] },
          F.glosa('Importacion segun DAM ...')
        ],
        build: function (d) {
          var inv = INVENTARIOS[d.sub_inv] || INVENTARIOS.mercaderia;
          var cif = round2(d.cif), adv = round2(cif * (Number(d.advalorem) || 0) / 100);
          var igv = round2((cif + adv) * 0.18);                          // IGV 16% + IPM 2% en aduana
          var perc = round2((cif + adv + igv) * (Number(d.percepcion) || 0) / 100);
          var g = d.glosa || 'Importacion';
          var tributos = [];
          if (adv > 0) tributos.push({ codigo: '60913', debe: adv, haber: 0, g: 'Ad valorem', why: 'Derechos aduaneros: forman parte del costo' });
          tributos.push({ codigo: '40111', debe: igv, haber: 0, g: 'IGV + IPM de importacion', why: 'IGV pagado en aduana: credito fiscal' });
          if (perc > 0) tributos.push({ codigo: '40113', debe: perc, haber: 0, g: 'Percepcion IGV', why: 'Percepcion: se descuenta del IGV a pagar' });
          tributos.push({ codigo: '1041', debe: 0, haber: round2(adv + igv + perc), g: 'Pago de tributos de importacion', why: 'Pagas los tributos en aduana' });
          return {
            asientos: [
              { glosa: '1) Compra al exterior - ' + g, lineas: [
                { codigo: inv.compra, debe: cif, haber: 0, g: g, why: 'Valor CIF de lo importado' },
                { codigo: '4212', debe: 0, haber: cif, g: 'Proveedor del exterior', why: 'Le debes al proveedor del exterior' }] },
              { glosa: '2) Tributos de importacion - ' + g, lineas: tributos },
              { glosa: '3) Ingreso a almacen - ' + g, lineas: [
                { codigo: inv.almacen, debe: round2(cif + adv), haber: 0, g: g, why: 'Entra al almacen al costo (CIF + ad valorem)' },
                { codigo: inv.variacion, debe: 0, haber: round2(cif + adv), g: g, why: 'Variacion de existencias' }] }
            ],
            notas: ['Si la factura del proveedor esta en dolares, registra el asiento 1 en USD con su tipo de cambio.',
                    'Agentes de aduana, almacenaje y fletes locales se registran aparte con la plantilla Compra (servicio).'],
            sunat: { tipo_comprobante: '50' }
          };
        }
      },

      pago_prov: {
        nombre: 'Pago a proveedor',
        campos: [
          { id: 'monto', label: 'Monto pagado', tipo: 'num', req: true, placeholder: '1180.00' },
          { id: 'desde', label: 'De donde pagas?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco' }, { v: 'efectivo', t: 'Caja (efectivo)' }] },
          F.glosa('Pago factura F001-...')
        ],
        build: function (d) {
          var m = round2(d.monto), medio = MEDIO[d.desde] || '1041', g = d.glosa || 'Pago a proveedor';
          return { asientos: [{ glosa: g, lineas: [
            { codigo: '4212', debe: m, haber: 0, g: g, why: 'Baja la deuda con el proveedor' },
            { codigo: medio, debe: 0, haber: m, g: g, why: 'Sale el dinero' }] }] };
        }
      },

      // ================================================== PERSONAL
      planilla: {
        nombre: 'Planilla / sueldos',
        campos: [
          { id: 'bruto', label: 'Total de remuneraciones brutas del mes', tipo: 'num', req: true, placeholder: '3000.00' },
          { id: 'regimen', label: 'Sistema de pensiones', tipo: 'select', opts: [
            { v: 'onp', t: 'ONP (13%)' }, { v: 'afp', t: 'AFP' }] },
          { id: 'afp_pct', label: '% total AFP (aporte 10% + prima + comision)', tipo: 'num', showIf: { regimen: 'afp' }, placeholder: '11.37' },
          { id: 'renta5', label: 'Retencion de renta de 5ta categoria (si corresponde)', tipo: 'num', placeholder: '0.00' },
          { id: 'pagar', label: 'Pagas los sueldos ahora?', tipo: 'select', opts: [
            { v: 'si', t: 'Si, registrar tambien el pago' }, { v: 'no', t: 'No, quedan por pagar' }] },
          { id: 'medio', label: 'Con que pagas?', tipo: 'select', showIf: { pagar: 'si' }, opts: [
            { v: 'banco', t: 'Banco (deposito en cuenta sueldo)' }, { v: 'efectivo', t: 'Caja (efectivo)' }] },
          F.glosa('Planilla de octubre')
        ],
        build: function (d) {
          var bruto = round2(d.bruto), afp = d.regimen === 'afp';
          var pct = afp ? (Number(d.afp_pct) || 0) : 13;
          var pens = round2(bruto * pct / 100), r5 = round2(d.renta5 || 0), neto = round2(bruto - pens - r5);
          var essalud = round2(bruto * 0.09), g = d.glosa || 'Planilla de remuneraciones';
          var l = [{ codigo: '6211', debe: bruto, haber: 0, g: g, why: 'Gasto por sueldos (bruto)' },
                   { codigo: afp ? '417' : '4032', debe: 0, haber: pens, g: (afp ? 'AFP ' : 'ONP ') + pct + '%',
                     why: 'Descuento al trabajador que pagas a la ' + (afp ? 'AFP' : 'ONP') }];
          if (r5 > 0) l.push({ codigo: '40173', debe: 0, haber: r5, g: 'Renta 5ta categoria', why: 'Retencion de renta que pagas a SUNAT' });
          l.push({ codigo: '4111', debe: 0, haber: neto, g: 'Neto a pagar', why: 'Lo que recibe el trabajador' });
          var asientos = [
            { glosa: '1) Planilla - ' + g, lineas: l },
            { glosa: '2) Aporte EsSalud - ' + g, lineas: [
              { codigo: '6271', debe: essalud, haber: 0, g: 'EsSalud 9%', why: 'Aporte del empleador (gasto de la empresa)' },
              { codigo: '4031', debe: 0, haber: essalud, g: 'EsSalud por pagar', why: 'Lo pagas a SUNAT en el PLAME' }] }
          ];
          if (d.pagar !== 'no') {
            var medio = MEDIO[d.medio] || '1041';
            asientos.push({ glosa: '3) Pago de sueldos - ' + g, lineas: [
              { codigo: '4111', debe: neto, haber: 0, g: g, why: 'Se cancelan los sueldos por pagar' },
              { codigo: medio, debe: 0, haber: neto, g: g, why: 'Sale el dinero' }] });
          }
          var notas = ['EsSalud se calcula sobre la remuneracion, con base minima de una RMV por trabajador.',
                       'Gratificaciones, vacaciones y CTS se provisionan aparte (6214/4114, 6215/4115, 6291/4151).'];
          if (afp && !(Number(d.afp_pct) > 0)) notas.unshift('Indica el % total de la AFP del trabajador.');
          return { asientos: asientos, notas: notas };
        }
      },

      // ================================================== BANCOS Y FINANCIAMIENTO
      caja_banco: {
        nombre: 'Deposito o retiro (caja / banco)',
        campos: [
          { id: 'monto', label: 'Monto', tipo: 'num', req: true, placeholder: '2000.00' },
          { id: 'direccion', label: 'Direccion del movimiento', tipo: 'select', opts: [
            { v: 'cb', t: 'De caja -> a banco (deposito)' }, { v: 'bc', t: 'De banco -> a caja (retiro)' }] },
          F.glosa('Deposito en BCP')
        ],
        build: function (d) {
          var m = round2(d.monto), cb = d.direccion !== 'bc', g = d.glosa || (cb ? 'Deposito de caja a banco' : 'Retiro de banco a caja');
          return { asientos: [{ glosa: g, lineas: [
            { codigo: cb ? '1041' : '1011', debe: m, haber: 0, g: g, why: cb ? 'Entra al banco' : 'Entra a caja' },
            { codigo: cb ? '1011' : '1041', debe: 0, haber: m, g: g, why: cb ? 'Sale de caja' : 'Sale del banco' }] }] };
        }
      },

      prestamo: {
        nombre: 'Prestamo bancario recibido',
        campos: [
          { id: 'monto', label: 'Monto del prestamo', tipo: 'num', req: true, placeholder: '10000.00' },
          { id: 'comision', label: 'Comisiones o gastos descontados (opcional)', tipo: 'num', placeholder: '0.00' },
          F.glosa('Prestamo BCP N° ...')
        ],
        build: function (d) {
          var m = round2(d.monto), com = round2(d.comision || 0), g = d.glosa || 'Prestamo bancario';
          var l = [{ codigo: '1041', debe: round2(m - com), haber: 0, g: g, why: 'Entra el dinero del prestamo al banco' }];
          if (com > 0) l.push({ codigo: '6391', debe: com, haber: 0, g: 'Comisiones del prestamo', why: 'Gastos bancarios descontados' });
          l.push({ codigo: '4511', debe: 0, haber: m, g: g, why: 'Deuda con la entidad financiera' });
          return { asientos: [{ glosa: g, lineas: l }],
                   notas: ['Registra cada cuota con la plantilla "Cuota de prestamo" (capital + intereses).',
                           'Para el estado financiero, la parte que vence en mas de 12 meses es pasivo no corriente.'] };
        }
      },

      cuota_prestamo: {
        nombre: 'Cuota de prestamo',
        campos: [
          { id: 'capital', label: 'Amortizacion de capital', tipo: 'num', req: true, placeholder: '800.00' },
          { id: 'interes', label: 'Intereses', tipo: 'num', placeholder: '120.00' },
          { id: 'otros', label: 'Seguro de desgravamen / comisiones', tipo: 'num', placeholder: '0.00' },
          { id: 'medio', label: 'De donde pagas?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco (debito automatico)' }, { v: 'efectivo', t: 'Caja' }] },
          F.glosa('Cuota 3/24 prestamo BCP')
        ],
        build: function (d) {
          var cap = round2(d.capital), int_ = round2(d.interes || 0), otros = round2(d.otros || 0);
          var total = round2(cap + int_ + otros), g = d.glosa || 'Cuota de prestamo';
          var l = [{ codigo: '4511', debe: cap, haber: 0, g: 'Amortizacion de capital', why: 'Baja la deuda del prestamo' }];
          if (int_ > 0) l.push({ codigo: '67311', debe: int_, haber: 0, g: 'Intereses', why: 'Gasto financiero por intereses' });
          if (otros > 0) l.push({ codigo: '6391', debe: otros, haber: 0, g: 'Seguros y comisiones', why: 'Gastos bancarios' });
          l.push({ codigo: MEDIO[d.medio] || '1041', debe: 0, haber: total, g: g, why: 'Sale el pago de la cuota' });
          return { asientos: [{ glosa: g, lineas: l }] };
        }
      },

      diferencia_cambio: {
        nombre: 'Diferencia de cambio',
        campos: [
          { id: 'tipo', label: 'Resultado', tipo: 'select', opts: [
            { v: 'ganancia', t: 'Ganancia por diferencia de cambio' }, { v: 'perdida', t: 'Perdida por diferencia de cambio' }] },
          { id: 'cuenta', label: 'Cuenta en dolares que se ajusta', tipo: 'select', opts: [
            { v: '1041', t: '1041 Banco (cuenta en dolares)' }, { v: '1212', t: '1212 Clientes (facturas en dolares)' },
            { v: '4212', t: '4212 Proveedores (facturas en dolares)' }] },
          { id: 'monto', label: 'Monto de la diferencia en soles', tipo: 'num', req: true, placeholder: '85.40' },
          F.glosa('Ajuste por diferencia de cambio al cierre de mes')
        ],
        build: function (d) {
          var m = round2(d.monto), g = d.glosa || 'Diferencia de cambio', gan = d.tipo !== 'perdida';
          var cta = d.cuenta || '1041';
          return { asientos: [{ glosa: g, lineas: gan
            ? [{ codigo: cta, debe: m, haber: 0, g: g, why: 'Ajuste del saldo en dolares al tipo de cambio de cierre' },
               { codigo: '7581', debe: 0, haber: m, g: g, why: 'Ingreso por diferencia de cambio' }]
            : [{ codigo: '6581', debe: m, haber: 0, g: g, why: 'Gasto por diferencia de cambio' },
               { codigo: cta, debe: 0, haber: m, g: g, why: 'Ajuste del saldo en dolares al tipo de cambio de cierre' }] }],
            notas: ['Usa el tipo de cambio de cierre publicado por la SBS: compra para activos y venta para pasivos.'] };
        }
      },

      // ================================================== ACTIVOS
      depreciacion: {
        nombre: 'Depreciacion / amortizacion mensual',
        campos: [
          { id: 'activo', label: 'Tipo de activo', tipo: 'select', opts: opciones(ACTIVOS, function (a) { return a.tasa > 0; }) },
          { id: 'costo', label: 'Costo del activo (sin IGV)', tipo: 'num', req: true, placeholder: '60000.00' },
          { id: 'tasa', label: 'Tasa anual % (vacio = maxima tributaria)', tipo: 'num', placeholder: '20' },
          { id: 'meses', label: 'Meses a registrar', tipo: 'num', placeholder: '1' },
          F.glosa('Depreciacion de octubre')
        ],
        build: function (d) {
          var a = ACTIVOS[d.activo] || ACTIVOS.vehiculo;
          var tasa = Number(d.tasa) > 0 ? Number(d.tasa) : a.tasa, meses = Number(d.meses) > 0 ? Number(d.meses) : 1;
          var monto = round2(round2(d.costo) * tasa / 100 / 12 * meses);
          var g = d.glosa || ('Depreciacion ' + a.t.split(' (')[0].toLowerCase());
          var notas = [];
          if (tasa > a.tasa) notas.push('La tasa supera el maximo tributario (' + a.tasa + '%): el exceso no es deducible para el impuesto a la renta.');
          return { asientos: [{ glosa: g, lineas: [
            { codigo: a.gasto, debe: monto, haber: 0, g: g, why: 'Gasto del periodo: ' + tasa + '% anual / 12 x ' + meses + ' mes(es)' },
            { codigo: a.acum, debe: 0, haber: monto, g: g, why: 'Depreciacion acumulada: reduce el valor del activo' }] }], notas: notas };
        }
      },

      // ================================================== PATRIMONIO
      capital: {
        nombre: 'Aporte de capital',
        campos: [
          { id: 'tipo_soc', label: 'Tipo de empresa', tipo: 'select', opts: [
            { v: 'acciones', t: 'S.A. / S.A.C. (acciones)' }, { v: 'participaciones', t: 'S.R.L. / E.I.R.L. (participaciones)' }] },
          { id: 'monto', label: 'Monto aportado', tipo: 'num', req: true, placeholder: '5000.00' },
          { id: 'destino', label: 'Donde entra el dinero?', tipo: 'select', opts: [
            { v: 'banco', t: 'Banco' }, { v: 'efectivo', t: 'Caja (efectivo)' }] },
          F.glosa('Aporte de capital de ...')
        ],
        build: function (d) {
          var m = round2(d.monto), g = d.glosa || 'Aporte de capital';
          var cap = d.tipo_soc === 'participaciones' ? '5012' : '5011';
          return { asientos: [
            { glosa: '1) Suscripcion del aporte - ' + g, lineas: [
              { codigo: '1421', debe: m, haber: 0, g: g, why: 'El socio se compromete a aportar (suscripcion por cobrar)' },
              { codigo: cap, debe: 0, haber: m, g: g, why: 'Aumenta el capital social' }] },
            { glosa: '2) Pago del aporte - ' + g, lineas: [
              { codigo: MEDIO[d.destino] || '1041', debe: m, haber: 0, g: g, why: 'Entra el dinero' },
              { codigo: '1421', debe: 0, haber: m, g: g, why: 'Se cobra la suscripcion' }] }
          ], notas: ['Los aportes en bienes (vehiculos, equipos) se registran contra la cuenta del activo en lugar de caja o banco.'] };
        }
      }
    };
  }

  // ------------------------------------------------------------------ Tarjetas del modal
  var TARJETAS = [
    { grupo: 'Ventas e ingresos', items: [
      { tpl: 'venta', t: 'Venta', ds: 'Factura o boleta, con o sin IGV, local o exportacion. Opcional: costo de ventas.', ic: 'point_of_sale', c: '#1e8449' },
      { tpl: 'nota_credito', t: 'Nota de credito', ds: 'Devolucion, descuento o anulacion de una venta.', ic: 'keyboard_return', c: '#c0392b' },
      { tpl: 'cobranza', t: 'Cobranza de factura', ds: 'El cliente paga una factura pendiente.', ic: 'account_balance_wallet', c: '#1e8449' },
      { tpl: 'anticipo', t: 'Anticipo de cliente', ds: 'Te adelantan dinero antes de entregar.', ic: 'savings', c: '#1e8449', preset: { tipo: 'recibido' } }
    ]},
    { grupo: 'Compras y gastos', items: [
      { tpl: 'compra', t: 'Compra de inventario', ds: 'Mercaderia, insumos, suministros, repuestos, envases.', ic: 'inventory_2', c: '#2c5282', preset: { categoria: 'inventario' } },
      { tpl: 'compra', t: 'Compra de activo fijo', ds: 'Vehiculo, computadora, celular, muebles, maquinaria, software.', ic: 'directions_car', c: '#2c5282', preset: { categoria: 'activo' } },
      { tpl: 'compra', t: 'Servicio con factura', ds: 'Publicidad, asesoria, mantenimiento, fletes... con o sin detraccion.', ic: 'handyman', c: '#2c5282', preset: { categoria: 'servicio' } },
      { tpl: 'gasto', t: 'Pago de servicio', ds: 'Luz, agua, internet, alquiler: pagas el recibo en el momento.', ic: 'payments', c: '#e67e22' },
      { tpl: 'honorarios', t: 'Recibo por honorarios', ds: 'Profesional independiente, con retencion del 8%.', ic: 'badge', c: '#e67e22' },
      { tpl: 'importacion', t: 'Importacion', ds: 'DAM: valor CIF, ad valorem, IGV y percepcion.', ic: 'local_shipping', c: '#2c5282' },
      { tpl: 'pago_prov', t: 'Pago a proveedor', ds: 'Pagas una factura pendiente.', ic: 'credit_card', c: '#c0392b' },
      { tpl: 'anticipo', t: 'Anticipo a proveedor', ds: 'Adelantas dinero antes de recibir el bien.', ic: 'outbox', c: '#c0392b', preset: { tipo: 'otorgado' } }
    ]},
    { grupo: 'Personal', items: [
      { tpl: 'planilla', t: 'Planilla / sueldos', ds: 'Sueldo bruto, ONP/AFP, renta 5ta, EsSalud y pago.', ic: 'groups', c: '#5b4b8a' }
    ]},
    { grupo: 'Bancos y financiamiento', items: [
      { tpl: 'caja_banco', t: 'Deposito o retiro', ds: 'Mueves efectivo entre caja y banco.', ic: 'account_balance', c: '#2c5282' },
      { tpl: 'prestamo', t: 'Prestamo recibido', ds: 'El banco te desembolsa un prestamo.', ic: 'request_quote', c: '#7c4a0f' },
      { tpl: 'cuota_prestamo', t: 'Cuota de prestamo', ds: 'Capital + intereses + seguros.', ic: 'event_repeat', c: '#7c4a0f' },
      { tpl: 'diferencia_cambio', t: 'Diferencia de cambio', ds: 'Ajuste de saldos en dolares al cierre.', ic: 'currency_exchange', c: '#7c4a0f' }
    ]},
    { grupo: 'Activos y patrimonio', items: [
      { tpl: 'depreciacion', t: 'Depreciacion mensual', ds: 'Gasto 68 / depreciacion acumulada 39 segun el activo.', ic: 'trending_down', c: '#5b4b8a' },
      { tpl: 'capital', t: 'Aporte de capital', ds: 'Los socios aportan dinero (acciones o participaciones).', ic: 'corporate_fare', c: '#2c5282' }
    ]}
  ];

  // ------------------------------------------------------------------ Interprete de texto libre
  function normalizar(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9%.,/\-\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }

  // Cada regla: palabras (raices) -> plantilla + valores iniciales. "p" = peso.
  var OBJETOS = [
    // Activos fijos
    { k: ['carro', 'auto ', 'autos', 'automovil', 'camioneta', 'moto', 'vehiculo', 'camion', 'furgon', 'mototaxi', 'minivan', 'pickup', 'station wagon'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'vehiculo' }, et: 'Activo fijo: vehiculo' },
    { k: ['laptop', 'computadora', ' pc', 'impresora', 'servidor', 'notebook', 'tablet', 'monitor', 'macbook', 'computador'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'computo' }, et: 'Activo fijo: equipo de computo' },
    { k: ['celular', 'smartphone', 'iphone', 'radio', 'central telefonica'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'comunicacion' }, et: 'Activo fijo: equipo de comunicacion' },
    { k: ['escritorio', 'silla', 'mueble', 'estante', 'mesa', 'armario', 'vitrina', 'anaquel', 'archivador'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'muebles' }, et: 'Activo fijo: muebles' },
    { k: ['maquina', 'maquinaria', 'horno', 'torno', 'compresora', 'generador', 'montacarga', 'cocina industrial', 'congeladora', 'refrigeradora industrial'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'maquinaria' }, et: 'Activo fijo: maquinaria' },
    { k: ['software', 'licencia perpetua', 'sistema contable', 'erp'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'software' }, et: 'Intangible: software' },
    // Inventarios
    { k: ['mercaderia', 'productos para', 'para revender', 'para vender', 'stock', 'abarrotes', 'existencias'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'mercaderia' }, et: 'Inventario: mercaderia' },
    { k: ['materia prima', 'materias primas', 'insumo', 'harina', 'tela ', 'telas'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'materia_prima' }, et: 'Inventario: materias primas' },
    { k: ['utiles', 'papel', 'limpieza', 'toner', 'combustible', 'gasolina', 'petroleo', 'diesel', 'lubricante'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'suministros' }, et: 'Inventario: suministros' },
    { k: ['repuesto', 'llanta', 'neumatico'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'repuestos' }, et: 'Inventario: repuestos' },
    { k: ['envase', 'botella'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'envases' }, et: 'Inventario: envases' },
    { k: ['embalaje', 'bolsas', 'cajas de carton', 'cinta de embalaje'], tpl: 'compra', preset: { categoria: 'inventario', sub_inv: 'embalajes' }, et: 'Inventario: embalajes' },
    // Servicios (se pagan con la plantilla "Pago de servicio")
    { k: ['luz', 'electricidad', 'energia electrica', 'enel', 'luz del sur', 'hidrandina'], tpl: 'gasto', preset: { sub_serv: 'luz', tipo_cp: '14' }, et: 'Servicio: luz' },
    { k: ['agua', 'sedapal'], tpl: 'gasto', preset: { sub_serv: 'agua', tipo_cp: '14' }, et: 'Servicio: agua' },
    { k: ['gas natural', 'calidda', 'balon de gas'], tpl: 'gasto', preset: { sub_serv: 'gas' }, et: 'Servicio: gas' },
    { k: ['internet', 'wifi', 'fibra optica'], tpl: 'gasto', preset: { sub_serv: 'internet' }, et: 'Servicio: internet' },
    { k: ['telefono', 'linea fija', 'plan movil', 'recarga'], tpl: 'gasto', preset: { sub_serv: 'telefono' }, et: 'Servicio: telefono' },
    { k: ['alquiler de local', 'alquiler del local', 'alquiler de oficina', 'alquiler', 'arriendo', 'renta del local'], tpl: 'gasto', preset: { sub_serv: 'alq_local', tipo_cp: '01' }, et: 'Servicio: alquiler de local' },
    { k: ['alquiler de camioneta', 'alquiler de auto', 'alquiler de vehiculo', 'alquiler de carro'], tpl: 'gasto', preset: { sub_serv: 'alq_vehiculo', tipo_cp: '01' }, et: 'Servicio: alquiler de vehiculo', p: 4 },
    { k: ['flete', 'courier', 'envio', 'transporte de carga', 'olva', 'shalom', 'encomienda'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'flete' }, et: 'Servicio: transporte de carga' },
    { k: ['taxi', 'pasaje', 'movilidad', 'uber', 'cabify', 'bus'], tpl: 'gasto', preset: { sub_serv: 'pasajes' }, et: 'Servicio: pasajes / movilidad' },
    { k: ['hotel', 'hospedaje', 'alojamiento'], tpl: 'gasto', preset: { sub_serv: 'alojamiento', tipo_cp: '01' }, et: 'Viaje: hospedaje' },
    { k: ['almuerzo', 'comida', 'menu', 'viatico', 'cena', 'desayuno'], tpl: 'gasto', preset: { sub_serv: 'alimentacion', tipo_cp: '01' }, et: 'Viaje: alimentacion' },
    { k: ['contador', 'contabilidad', 'auditoria'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'contable' }, et: 'Servicio: contable' },
    { k: ['abogado', 'legal', 'notario', 'notaria', 'tributaria'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'legal' }, et: 'Servicio: legal / tributario' },
    { k: ['asesoria', 'consultoria', 'consultor'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'asesoria' }, et: 'Servicio: asesoria' },
    { k: ['publicidad', 'anuncio', 'facebook ads', 'google ads', 'meta ads', 'tiktok ads', 'volantes', 'banner'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'publicidad' }, et: 'Servicio: publicidad' },
    { k: ['mantenimiento', 'reparacion', 'arreglo', 'servicio tecnico'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'mantenimiento' }, et: 'Servicio: mantenimiento' },
    { k: ['seguro', 'poliza', 'soat'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'seguros' }, et: 'Servicio: seguros' },
    { k: ['comision bancaria', 'mantenimiento de cuenta', 'gastos bancarios'], tpl: 'gasto', preset: { sub_serv: 'bancarios', tipo_cp: '12' }, et: 'Gasto bancario', p: 4 },
    { k: ['itf', 'impuesto a las transacciones'], tpl: 'gasto', preset: { sub_serv: 'itf', con_igv: 'no' }, et: 'Tributo: ITF', p: 5 },
    { k: ['predial', 'autovaluo'], tpl: 'gasto', preset: { sub_serv: 'predial', con_igv: 'no' }, et: 'Tributo: impuesto predial', p: 5 },
    { k: ['arbitrio', 'serenazgo', 'limpieza publica'], tpl: 'gasto', preset: { sub_serv: 'arbitrios', con_igv: 'no' }, et: 'Tributo: arbitrios', p: 5 },
    { k: ['patrimonio vehicular'], tpl: 'gasto', preset: { sub_serv: 'vehicular', con_igv: 'no' }, et: 'Tributo: patrimonio vehicular', p: 6 },
    { k: ['licencia de funcionamiento', 'defensa civil', 'itse'], tpl: 'gasto', preset: { sub_serv: 'licencia_func', con_igv: 'no' }, et: 'Tramite municipal', p: 5 },
    { k: ['multa de sunat', 'multa tributaria', 'multa sunat'], tpl: 'gasto', preset: { sub_serv: 'multa_trib', con_igv: 'no' }, et: 'Multa tributaria', p: 6 },
    { k: ['multa', 'papeleta', 'sancion', 'sunafil'], tpl: 'gasto', preset: { sub_serv: 'sanciones', con_igv: 'no' }, et: 'Multa / sancion', p: 4 },
    { k: ['donacion', ' done ', 'donamos'], tpl: 'gasto', preset: { sub_serv: 'donaciones', con_igv: 'no' }, et: 'Donacion', p: 5 },
    { k: ['cable', 'directv', 'tv de paga', 'television'], tpl: 'gasto', preset: { sub_serv: 'cable' }, et: 'Servicio: cable / TV' },
    { k: ['peaje', 'estacionamiento', 'cochera'], tpl: 'gasto', preset: { sub_serv: 'otros_viaje' }, et: 'Viaje: peajes / estacionamiento' },
    { k: ['capacitacion', ' curso', 'seminario', 'diplomado'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'capacitacion' }, et: 'Personal: capacitacion' },
    { k: ['refrigerio', 'uniforme', 'agasajo', 'canasta navidena', 'panetones'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'atencion_personal' }, et: 'Personal: atencion al personal' },
    { k: ['sctr'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'sctr' }, et: 'Personal: SCTR', p: 5 },
    { k: ['vida ley'], tpl: 'gasto', preset: { sub_serv: 'vida_ley', con_igv: 'no' }, et: 'Personal: seguro vida ley', p: 6 },
    { k: [' eps ', 'seguro de salud'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'eps' }, et: 'Personal: EPS' },
    { k: ['maquila', 'confeccion por terceros', 'servicio de produccion'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'maquila' }, et: 'Produccion encargada a terceros' },
    { k: ['laboratorio', 'analisis de muestras'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'laboratorio' }, et: 'Servicio: laboratorio' },
    { k: ['camara', 'camaras de seguridad', 'alarma', 'extintor'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'seguridad' }, et: 'Activo fijo: equipo de seguridad' },
    { k: ['aire acondicionado', 'refrigeradora', 'microondas', 'televisor'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'otros_equipos' }, et: 'Activo fijo: otros equipos' },
    { k: ['terreno', 'lote de terreno'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'terreno' }, et: 'Activo fijo: terreno', p: 4 },
    { k: ['compra de local', 'compre un local', 'compre una oficina', 'inmueble', 'edificio'], tpl: 'compra', preset: { categoria: 'activo', sub_act: 'edificacion' }, et: 'Activo fijo: edificacion', p: 4 },
    { k: ['suscripcion', 'office 365', 'microsoft 365', 'google workspace', 'canva', 'saas', 'hosting', 'dominio'], tpl: 'compra', preset: { categoria: 'servicio', sub_serv: 'suscripciones' }, et: 'Servicio: suscripcion' }
  ];

  // Operaciones que no dependen del objeto. "verbo" indica la familia de la frase.
  var OPERACIONES = [
    { k: ['planilla', 'sueldo', 'salario', 'remuneracion', 'trabajadores', 'pago al personal'], tpl: 'planilla', et: 'Planilla de sueldos', p: 5 },
    { k: ['recibo por honorarios', 'rxh', 'honorario', 'recibo de honorarios'], tpl: 'honorarios', et: 'Recibo por honorarios', p: 6 },
    { k: ['importe', 'importacion', 'importamos', 'dua', 'dam ', 'aduana', 'del extranjero', 'de china', 'de estados unidos'], tpl: 'importacion', et: 'Importacion', p: 5 },
    { k: ['nota de credito', 'devolucion', 'devolvio', 'devolvieron', 'anule la factura', 'anulacion de factura'], tpl: 'nota_credito', et: 'Nota de credito', p: 6 },
    { k: ['cuota del prestamo', 'cuota de prestamo', 'pague el prestamo', 'pago del prestamo', 'amortizacion del prestamo', 'cuota del credito'], tpl: 'cuota_prestamo', et: 'Cuota de prestamo', p: 7 },
    { k: ['prestamo', 'desembolso', 'credito bancario', 'financiamiento'], tpl: 'prestamo', et: 'Prestamo recibido', p: 4 },
    { k: ['deposite', 'deposito de caja', 'lleve al banco', 'depositamos'], tpl: 'caja_banco', preset: { direccion: 'cb' }, et: 'Deposito de caja a banco', p: 4 },
    { k: ['retire', 'retiro del banco', 'saque del banco', 'retiramos'], tpl: 'caja_banco', preset: { direccion: 'bc' }, et: 'Retiro de banco a caja', p: 4 },
    { k: ['aporte', 'aporto', 'capital social', 'aumento de capital'], tpl: 'capital', et: 'Aporte de capital', p: 5 },
    { k: ['adelanto del cliente', 'anticipo del cliente', 'anticipo de cliente', 'me adelantaron', 'nos adelantaron', 'me dieron un adelanto'], tpl: 'anticipo', preset: { tipo: 'recibido' }, et: 'Anticipo de cliente', p: 7 },
    { k: ['adelanto al proveedor', 'anticipo al proveedor', 'anticipo a proveedor', 'le adelante', 'adelante al proveedor'], tpl: 'anticipo', preset: { tipo: 'otorgado' }, et: 'Anticipo a proveedor', p: 7 },
    { k: ['depreciacion', 'depreciar', 'amortizacion de intangible'], tpl: 'depreciacion', et: 'Depreciacion', p: 6 },
    { k: ['diferencia de cambio', 'diferencia cambiaria'], tpl: 'diferencia_cambio', et: 'Diferencia de cambio', p: 7 },
    { k: ['cobre', 'cobramos', 'me pagaron', 'nos pagaron', 'me pago el cliente', 'cobranza', 'cliente pago', 'el cliente me pago'], tpl: 'cobranza', et: 'Cobranza a cliente', p: 4 },
    { k: ['pague al proveedor', 'pago al proveedor', 'pague la factura', 'cancele la factura', 'pague lo que debia', 'pague la deuda'], tpl: 'pago_prov', et: 'Pago a proveedor', p: 5 },
    { k: ['vendi', 'vendimos', 'venta', 'facture', 'facturamos', 'emiti factura', 'emiti boleta'], tpl: 'venta', et: 'Venta', p: 3, verbo: 'venta' },
    { k: ['exporte', 'exportacion', 'exportamos'], tpl: 'venta', preset: { tipo_venta: 'exportacion' }, et: 'Venta de exportacion', p: 5, verbo: 'venta' }
  ];
  var VERBO_COMPRA = ['compre', 'compramos', 'compra', 'adquiri', 'adquirimos', 'me vendieron', 'nos vendieron', 'pedido al proveedor'];
  var VERBO_PAGO = ['pague', 'pagamos', 'pago de', 'pago del', 'cancele'];

  function contiene(texto, palabra) { return (' ' + texto + ' ').indexOf(palabra.indexOf(' ') === 0 ? palabra : palabra) >= 0; }
  function coincide(texto, lista) {
    for (var i = 0; i < lista.length; i++) { if (contiene(' ' + texto + ' ', lista[i])) return lista[i]; }
    return null;
  }

  function extraerMonto(t) {
    // "50 mil", "50k", "s/ 5,000.50", "5000", "1.500" (punto de miles)
    var m = t.match(/(\d+(?:[.,]\d+)?)\s*(mil|k)\b/);
    if (m) return Math.round(parseFloat(m[1].replace(',', '.')) * 1000 * 100) / 100;
    var limpio = t.replace(/\b[a-z]{1,2}\d{2,3}-\d+\b/g, ' ')          // series F001-123, E001-5
                  .replace(/\b\d{3}-\d{4}-\d{2}-\d+\b/g, ' ')           // N° de DAM
                  .replace(/\b(10|15|17|20)\d{9}\b/g, ' ')              // RUC
                  .replace(/\b\d+(?:[.,]\d+)?\s*%/g, ' ')               // porcentajes
                  .replace(/\b(19|20)\d{2}\b(?!\s*(soles|s\/))/g, ' ');  // anios sueltos
    var nums = limpio.match(/\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{1,3}(?:\.\d{3})+(?!\d)|\d+(?:[.,]\d{1,2})?/g);
    if (!nums) return null;
    var valores = nums.map(function (n) {
      if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(n)) return parseFloat(n.replace(/,/g, ''));
      if (/^\d{1,3}(\.\d{3})+$/.test(n)) return parseFloat(n.replace(/\./g, ''));
      return parseFloat(n.replace(',', '.'));
    }).filter(function (v) { return v > 0; });
    if (!valores.length) return null;
    return Math.max.apply(null, valores);
  }

  function interpretar(texto, ctx) {
    ctx = ctx || {};
    var IGV = typeof ctx.igv === 'number' ? ctx.igv : 0.18;
    var t = normalizar(texto);
    if (t.length < 3) return [];
    var datos = {}, detalles = [];

    // ---- Datos generales
    var monto = extraerMonto(t);
    var credito = coincide(t, ['al credito', 'a credito', 'credito de', 'a plazos', 'fiado', 'por pagar', 'quedo debiendo', 'le debo', 'pendiente de pago']);
    var mitad = coincide(t, ['mitad', '50%']);
    var pctM = t.match(/(\d{1,2})\s*%\s*(al contado|contado|de inicial|inicial|adelantado)/) || t.match(/(?:inicial|adelanto) de(?:l)? (\d{1,2})\s*%/);
    var banco = coincide(t, ['transferencia', 'banco', 'yape', 'plin', 'deposito', 'tarjeta', 'cheque', 'bcp', 'bbva', 'interbank', 'scotiabank']);
    var efectivo = coincide(t, ['efectivo', 'caja', 'cash', 'en mano']);
    if (pctM || (mitad && credito)) {
      datos.forma = 'mixto'; datos.pct_contado = pctM ? pctM[1] : '50';
      detalles.push('Pago mixto: ' + datos.pct_contado + '% al contado');
    } else if (credito) { datos.forma = 'credito'; detalles.push('Al credito'); }
    else if (banco || efectivo) { datos.forma = 'contado'; detalles.push('Al contado'); }
    if (banco) { datos.medio = 'banco'; datos.desde = 'banco'; datos.destino = 'banco'; detalles.push('Por banco'); }
    else if (efectivo) { datos.medio = 'efectivo'; datos.desde = 'efectivo'; datos.destino = 'efectivo'; detalles.push('En efectivo'); }

    var doc = (texto || '').toUpperCase().match(/\b([FBE][A-Z0-9]{3})\s*-\s*(\d{1,8})\b/);
    if (doc) { datos.numero_documento = doc[1] + '-' + doc[2]; detalles.push('Comprobante ' + datos.numero_documento); }
    if (coincide(t, ['boleta'])) { datos.tipo_cp = '03'; }
    else if (coincide(t, ['factura'])) { datos.tipo_cp = '01'; }
    else if (coincide(t, ['ticket'])) { datos.tipo_cp = '12'; }
    var ruc = t.match(/\b((10|15|17|20)\d{9})\b/);
    if (ruc) { datos.ruc = ruc[1]; detalles.push('RUC ' + ruc[1]); }
    var sinIgv = coincide(t, ['sin igv', 'exonerad', 'inafect', 'rus', 'nuevo rus']);
    var masIgv = coincide(t, ['mas igv', '+ igv', 'mas el igv', 'sin incluir igv', 'antes de igv', 'valor de venta']);
    if (sinIgv) { datos.con_igv = 'no'; detalles.push('Sin IGV'); }

    // ---- Candidatos
    var candidatos = {};
    function sumar(tpl, preset, et, peso) {
      var clave = tpl + '|' + JSON.stringify(preset || {});
      if (!candidatos[clave]) candidatos[clave] = { tpl: tpl, preset: Object.assign({}, preset || {}), etiquetas: [], score: 0 };
      candidatos[clave].score += peso;
      if (et && candidatos[clave].etiquetas.indexOf(et) < 0) candidatos[clave].etiquetas.push(et);
    }
    var esCompra = !!coincide(t, VERBO_COMPRA);
    var esPago = !!coincide(t, VERBO_PAGO);

    OPERACIONES.forEach(function (r) {
      var hit = coincide(t, r.k);
      if (hit) sumar(r.tpl, r.preset, r.et, (r.p || 3) + hit.length / 20);
    });
    OBJETOS.forEach(function (r) {
      var hit = coincide(t, r.k);
      if (!hit) return;
      var peso = (r.p || 3) + hit.length / 20;
      if (esCompra && r.tpl === 'compra') peso += 3;
      if (esPago && r.tpl === 'gasto') peso += 2;
      // "pague el carro / la laptop" sigue siendo una compra del activo
      if (esPago && r.tpl === 'compra' && r.preset.categoria !== 'servicio') peso += 2;
      sumar(r.tpl, r.preset, r.et, peso);
    });
    // Solo verbo, sin objeto reconocido
    if (esCompra && !Object.keys(candidatos).some(function (k) { return candidatos[k].tpl === 'compra'; })) {
      sumar('compra', { categoria: 'inventario', sub_inv: 'mercaderia' }, 'Compra (no reconoci que compraste: revisa el tipo)', 1.5);
    }
    if (esPago && !Object.keys(candidatos).length) sumar('pago_prov', {}, 'Pago a proveedor', 1);

    var lista = Object.keys(candidatos).map(function (k) { return candidatos[k]; })
      .sort(function (a, b) { return b.score - a.score; }).slice(0, 3);

    // ---- Completar valores segun la plantilla elegida
    lista.forEach(function (c) {
      var p = c.preset, notas = [];
      Object.keys(datos).forEach(function (k) { if (p[k] === undefined) p[k] = datos[k]; });
      if (monto) {
        if (c.tpl === 'venta' || c.tpl === 'compra' || c.tpl === 'nota_credito') {
          var conIgv = p.con_igv !== 'no' && p.tipo_venta !== 'exportacion';
          p.base = String(monto);
          if (conIgv && !masIgv) {
            p.ingreso = 'total';
            notas.push('Tome S/ ' + money(monto) + ' como total con IGV (si es el valor sin IGV, cambialo en el formulario)');
          } else {
            p.ingreso = 'base';
            notas.push('Valor sin IGV: S/ ' + money(monto));
          }
        } else if (c.tpl === 'planilla') { p.bruto = String(monto); notas.push('Sueldos brutos: S/ ' + money(monto)); }
        else if (c.tpl === 'honorarios') { p.bruto = String(monto); notas.push('Honorario bruto: S/ ' + money(monto)); }
        else if (c.tpl === 'importacion') { p.cif = String(monto); notas.push('Valor CIF: S/ ' + money(monto)); }
        else if (c.tpl === 'depreciacion') { p.costo = String(monto); notas.push('Costo del activo: S/ ' + money(monto)); }
        else if (c.tpl === 'cuota_prestamo') { p.capital = String(monto); notas.push('Revisa cuanto es capital y cuanto intereses'); }
        else { p.monto = String(monto); notas.push('Monto: S/ ' + money(monto)); }
      }
      if (c.tpl === 'honorarios') { delete p.tipo_cp; }
      if (c.tpl === 'planilla') {
        if (coincide(t, ['afp', 'prima', 'integra', 'profuturo', 'habitat'])) { p.regimen = 'afp'; notas.push('AFP: indica el % total'); }
        else if (coincide(t, ['onp'])) p.regimen = 'onp';
        if (p.forma === 'credito') p.pagar = 'no';
      }
      c.detalles = c.etiquetas.concat(detalles).concat(notas);
      // Confianza: alta si hubo operacion u objeto claro + monto
      c.confianza = c.score >= 6 && monto ? 'alta' : c.score >= 3 ? 'media' : 'baja';
    });
    return lista;
  }

  var API = { crear: crear, TARJETAS: TARJETAS, interpretar: interpretar, normalizar: normalizar,
              extraerMonto: extraerMonto, INVENTARIOS: INVENTARIOS, ACTIVOS: ACTIVOS, SERVICIOS: SERVICIOS, VENDIDO: VENDIDO, round2: round2 };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.Plantillas = API;
})(this);
