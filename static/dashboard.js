/* Dashboard: graficos SVG sin dependencias (funciona offline). */
(function () {
  'use strict';

  var dataEl = document.getElementById('dashData');
  if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var SVGNS = 'http://www.w3.org/2000/svg';
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var noAnim = reduceMotion;

  // ---------- Formato ----------
  var nf2 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nf0 = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 });
  function money(v) { return 'S/ ' + nf2.format(v); }
  function compact(v) {
    var a = Math.abs(v), s = v < 0 ? '-' : '';
    if (a >= 1e6) return s + trim(a / 1e6) + 'M';
    if (a >= 1e4) return s + trim(a / 1e3) + 'K';
    return s + nf0.format(a);
  }
  function trim(x) { return (Math.round(x * 10) / 10).toString().replace(/\.0$/, ''); }

  function cssVar(name) {
    var root = document.getElementById('dash');
    return getComputedStyle(root).getPropertyValue(name).trim();
  }

  function el(tag, attrs, parent) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function h(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  // Ticks "limpios" entre min y max
  function niceScale(min, max, count) {
    if (max === min) { max = min + 1; }
    var span = max - min;
    var step = Math.pow(10, Math.floor(Math.log10(span / count)));
    var err = (count * step) / span;
    if (err <= 0.15) step *= 10; else if (err <= 0.35) step *= 5; else if (err <= 0.75) step *= 2;
    var lo = Math.floor(min / step) * step;
    var hi = Math.ceil(max / step) * step;
    var ticks = [];
    for (var t = lo; t <= hi + step / 2; t += step) ticks.push(Math.round(t * 100) / 100);
    return { lo: lo, hi: hi, ticks: ticks };
  }

  // Barra con extremo de datos redondeado (4px) y base recta
  function barPath(x, y0, y1, w, r) {
    var up = y1 <= y0;
    var hgt = Math.abs(y0 - y1);
    r = Math.min(r, w / 2, hgt);
    if (hgt < 0.5) return '';
    if (up) {
      return 'M' + x + ',' + y0 + 'V' + (y1 + r) + 'Q' + x + ',' + y1 + ' ' + (x + r) + ',' + y1 +
        'H' + (x + w - r) + 'Q' + (x + w) + ',' + y1 + ' ' + (x + w) + ',' + (y1 + r) + 'V' + y0 + 'Z';
    }
    return 'M' + x + ',' + y0 + 'V' + (y1 - r) + 'Q' + x + ',' + y1 + ' ' + (x + r) + ',' + y1 +
      'H' + (x + w - r) + 'Q' + (x + w) + ',' + y1 + ' ' + (x + w) + ',' + (y1 - r) + 'V' + y0 + 'Z';
  }

  // ---------- Tooltip ----------
  var tip = document.getElementById('vizTooltip');
  function showTip(title, rows, evt, anchor) {
    tip.textContent = '';
    tip.appendChild(h('div', 'tt-title', title));
    rows.forEach(function (r) {
      var row = h('div', 'tt-row');
      var key = h('span', 'tt-key');
      key.style.background = r.color || 'transparent';
      row.appendChild(key);
      row.appendChild(h('span', 'tt-name', r.name));
      row.appendChild(h('b', '', r.value));
      tip.appendChild(row);
    });
    tip.hidden = false;
    var x, y;
    if (evt && evt.clientX !== undefined && evt.type !== 'focus') { x = evt.clientX; y = evt.clientY; }
    else { var b = anchor.getBoundingClientRect(); x = b.left + b.width / 2; y = b.top; }
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var left = x + 14, top = y - th - 12;
    if (left + tw > window.innerWidth - 8) left = x - tw - 14;
    if (top < 8) top = y + 16;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hideTip() { tip.hidden = true; }

  // ---------- Columnas agrupadas: ventas vs compras ----------
  function renderColumns(container, serie, series) {
    container.textContent = '';
    var W = container.clientWidth || 600, H = 260;
    var m = { t: 12, r: 8, b: 26, l: 46 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b;
    var vals = [];
    serie.forEach(function (p) { series.forEach(function (s) { vals.push(p[s.key]); }); });
    var sc = niceScale(Math.min(0, Math.min.apply(null, vals)), Math.max(0, Math.max.apply(null, vals)), 4);
    var y = function (v) { return m.t + ih - ((v - sc.lo) / (sc.hi - sc.lo)) * ih; };
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, height: H });

    sc.ticks.forEach(function (t) {
      el('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), 'class': t === 0 ? 'baseline' : 'grid' }, svg);
      el('text', { x: m.l - 8, y: y(t) + 4, 'text-anchor': 'end', 'class': 'tick' }, svg).textContent = compact(t);
    });

    var band = iw / serie.length;
    var gap = 2;
    var bw = Math.max(4, Math.min(16, (band * 0.62 - gap) / series.length));
    var groupW = bw * series.length + gap * (series.length - 1);

    serie.forEach(function (p, i) {
      var bx = m.l + band * i;
      if (p.mes === D.month) el('rect', { x: bx + 2, y: m.t, width: band - 4, height: ih, rx: 8, 'class': 'band-sel' }, svg);
      var hover = el('rect', { x: bx + 2, y: m.t, width: band - 4, height: ih, rx: 8, 'class': 'band-hover' }, svg);
      var gx = bx + (band - groupW) / 2;
      series.forEach(function (s, j) {
        var d = barPath(gx + j * (bw + gap), y(0), y(p[s.key]), bw, 4);
        if (!d) return;
        var bar = el('path', { d: d, fill: 'var(' + s.color + ')', 'class': 'bar' + (noAnim ? '' : ' bar-grow') }, svg);
        if (!noAnim) bar.style.animationDelay = (i * 35) + 'ms';
      });
      el('text', {
        x: bx + band / 2, y: H - 8, 'text-anchor': 'middle', 'class': 'tick',
        'font-weight': p.mes === D.month ? 700 : null,
      }, svg).textContent = p.label;

      var hit = el('rect', { x: bx, y: m.t, width: band, height: ih + m.b, 'class': 'hit', tabindex: 0,
        'aria-label': p.label + ': ' + series.map(function (s) { return s.name + ' ' + money(p[s.key]); }).join(', ') }, svg);
      var show = function (e) {
        hover.style.opacity = '.05';
        var rows = series.map(function (s) { return { name: s.name, value: money(p[s.key]), color: cssVar(s.color) }; });
        rows.push({ name: 'Resultado', value: money(p.ventas - p.compras) });
        showTip(p.label + ' ' + D.year + ' · ' + p.asientos + ' asientos', rows, e, hit);
      };
      var hide = function () { hover.style.opacity = '0'; hideTip(); };
      hit.addEventListener('pointermove', show);
      hit.addEventListener('focus', show);
      hit.addEventListener('pointerleave', hide);
      hit.addEventListener('blur', hide);
      hit.addEventListener('click', function () {
        window.location.href = '/dashboard?year=' + D.year + '&month=' + p.mes;
      });
    });
    container.appendChild(svg);
  }

  // ---------- Linea: resultado mensual ----------
  function renderLine(container, serie, key, colorVar, name) {
    container.textContent = '';
    var W = container.clientWidth || 600, H = 240;
    var m = { t: 16, r: 18, b: 26, l: 46 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b;
    var vals = serie.map(function (p) { return p[key]; });
    var sc = niceScale(Math.min(0, Math.min.apply(null, vals)), Math.max(0, Math.max.apply(null, vals)), 4);
    var step = iw / (serie.length - 1);
    var x = function (i) { return m.l + step * i; };
    var y = function (v) { return m.t + ih - ((v - sc.lo) / (sc.hi - sc.lo)) * ih; };
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, height: H });

    sc.ticks.forEach(function (t) {
      el('line', { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), 'class': t === 0 ? 'baseline' : 'grid' }, svg);
      el('text', { x: m.l - 8, y: y(t) + 4, 'text-anchor': 'end', 'class': 'tick' }, svg).textContent = compact(t);
    });
    serie.forEach(function (p, i) {
      if (i % (W < 420 ? 2 : 1) === 0)
        el('text', { x: x(i), y: H - 8, 'text-anchor': 'middle', 'class': 'tick', 'font-weight': p.mes === D.month ? 700 : null }, svg).textContent = p.label;
    });

    // Solo hasta el ultimo mes con datos (o el mes seleccionado si es el anio en curso)
    var last = 0;
    serie.forEach(function (p, i) { if (p.asientos > 0) last = i; });
    last = Math.max(last, D.month - 1);
    var pts = serie.slice(0, last + 1).map(function (p, i) { return [x(i), y(p[key])]; });
    var dLine = pts.map(function (pt, i) { return (i ? 'L' : 'M') + pt[0].toFixed(1) + ',' + pt[1].toFixed(1); }).join('');
    var dArea = dLine + 'L' + pts[pts.length - 1][0] + ',' + y(0) + 'L' + pts[0][0] + ',' + y(0) + 'Z';
    el('path', { d: dArea, fill: 'var(' + colorVar + ')', opacity: 0.1 }, svg);
    var line = el('path', { d: dLine, fill: 'none', stroke: 'var(' + colorVar + ')', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, svg);

    // Marcador del mes seleccionado + etiqueta
    var si = Math.min(D.month - 1, pts.length - 1);
    var sel = pts[si];
    el('circle', { cx: sel[0], cy: sel[1], r: 5, fill: 'var(' + colorVar + ')', stroke: 'var(--d-surface)', 'stroke-width': 2 }, svg);
    var lbl = el('text', { x: sel[0], y: sel[1] - 12, 'text-anchor': si === 0 ? 'start' : (si >= serie.length - 2 ? 'end' : 'middle'), 'class': 'end-label' }, svg);
    lbl.textContent = compact(serie[si][key]);

    var cross = el('line', { x1: 0, x2: 0, y1: m.t, y2: m.t + ih, 'class': 'crosshair', visibility: 'hidden' }, svg);
    var dot = el('circle', { r: 5, fill: 'var(' + colorVar + ')', stroke: 'var(--d-surface)', 'stroke-width': 2, visibility: 'hidden' }, svg);
    var hit = el('rect', { x: m.l - step / 2, y: m.t, width: iw + step, height: ih, fill: 'transparent', tabindex: 0,
      'aria-label': name + ' por mes. Usa las flechas para recorrer.' }, svg);
    var cur = si;
    function focusIdx(i, e) {
      cur = Math.max(0, Math.min(serie.length - 1, i));
      var p = serie[cur];
      cross.setAttribute('x1', x(cur)); cross.setAttribute('x2', x(cur));
      cross.setAttribute('visibility', 'visible');
      if (cur <= last) {
        dot.setAttribute('cx', x(cur)); dot.setAttribute('cy', y(p[key]));
        dot.setAttribute('visibility', 'visible');
      } else dot.setAttribute('visibility', 'hidden');
      showTip(p.label + ' ' + D.year, [
        { name: name, value: money(p[key]), color: cssVar(colorVar) },
        { name: 'Ventas', value: money(p.ventas) },
        { name: 'Compras', value: money(p.compras) },
      ], e, dot.getAttribute('visibility') === 'visible' ? dot : cross);
    }
    hit.addEventListener('pointermove', function (e) {
      var r = svg.getBoundingClientRect();
      var px = (e.clientX - r.left) * (W / r.width);
      focusIdx(Math.round((px - m.l) / step), e);
    });
    hit.addEventListener('focus', function () { focusIdx(cur); });
    hit.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { focusIdx(cur + 1); e.preventDefault(); }
      if (e.key === 'ArrowLeft') { focusIdx(cur - 1); e.preventDefault(); }
    });
    function off() { cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); hideTip(); }
    hit.addEventListener('pointerleave', off);
    hit.addEventListener('blur', off);
    container.appendChild(svg);

    if (!noAnim && line.getTotalLength) {
      var len = line.getTotalLength();
      line.style.strokeDasharray = len;
      line.style.setProperty('--len', len);
      line.classList.add('line-draw');
    }
  }

  // ---------- Barras horizontales (rankings) ----------
  function renderHBars(container, items, colorVar, emptyMsg, sub) {
    container.textContent = '';
    if (!items.length) {
      var empty = h('div', 'viz-empty');
      empty.appendChild(h('span', 'ic', 'bar_chart'));
      empty.appendChild(h('p', '', emptyMsg));
      container.appendChild(empty);
      return;
    }
    var max = Math.max.apply(null, items.map(function (i) { return i.total; }));
    var total = items.reduce(function (a, i) { return a + i.total; }, 0);
    var ul = h('ul', 'hb-list');
    items.forEach(function (it, idx) {
      var li = h('li', 'hb-row');
      li.tabIndex = 0;
      var name = h('span', 'hb-name', it.nombre);
      if (sub && it[sub]) name.appendChild(h('small', '', it[sub]));
      name.title = it.nombre;
      var pct = total ? Math.round((it.total / total) * 100) : 0;
      var val = h('span', 'hb-val', compact(it.total));
      val.appendChild(h('small', '', pct + '%'));
      var track = h('span', 'hb-track');
      var fill = h('span', 'hb-fill');
      fill.style.display = 'block';
      fill.style.width = Math.max(2, (it.total / max) * 100) + '%';
      fill.style.background = 'var(' + colorVar + ')';
      fill.style.animationDelay = (idx * 60) + 'ms';
      track.appendChild(fill);
      li.appendChild(name); li.appendChild(val); li.appendChild(track);
      var show = function (e) {
        showTip(it.nombre, [
          { name: 'Importe', value: money(it.total), color: cssVar(colorVar) },
          { name: 'Participación', value: pct + '%' },
        ], e, li);
      };
      li.addEventListener('pointermove', show);
      li.addEventListener('focus', show);
      li.addEventListener('pointerleave', hideTip);
      li.addEventListener('blur', hideTip);
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  // ---------- Sparklines de KPIs ----------
  function renderSpark(svg, values, colorVar) {
    svg.textContent = '';
    var W = 96, H = 30, pad = 3;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    var upto = Math.max(D.month, 1);
    var v = values.slice(0, upto);
    if (v.length < 2) return;
    var min = Math.min.apply(null, v), max = Math.max.apply(null, v);
    if (max === min) { max += 1; min -= 1; }
    var step = (W - pad * 2) / 11;
    var pts = v.map(function (val, i) { return [pad + i * step, pad + (H - pad * 2) * (1 - (val - min) / (max - min))]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join('');
    el('path', { d: d, fill: 'none', stroke: 'var(--d-axis)', 'stroke-width': 1.5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, svg);
    var lp = pts[pts.length - 1];
    if (pts.length >= 2) {
      var pp = pts[pts.length - 2];
      el('path', { d: 'M' + pp[0] + ',' + pp[1] + 'L' + lp[0] + ',' + lp[1], fill: 'none', stroke: 'var(' + colorVar + ')', 'stroke-width': 2, 'stroke-linecap': 'round' }, svg);
    }
    el('circle', { cx: lp[0], cy: lp[1], r: 3.5, fill: 'var(' + colorVar + ')', stroke: 'var(--d-surface)', 'stroke-width': 1.5 }, svg);
  }

  // ---------- Deltas vs mes anterior ----------
  function renderDeltas() {
    document.querySelectorAll('[data-delta]').forEach(function (n) {
      var a = parseFloat(n.dataset.actual), p = parseFloat(n.dataset.previo);
      var upGood = n.dataset.upGood;
      var isCount = n.dataset.count === '1';
      n.textContent = '';
      var span = h('span', 'delta');
      var diff = a - p;
      var ic = h('span', 'ic', diff > 0 ? 'arrow_upward' : diff < 0 ? 'arrow_downward' : 'remove');
      span.appendChild(ic);
      var txt;
      if (p === 0 && a === 0) txt = 'Sin cambios';
      else if (p === 0) txt = (isCount ? '+' + nf0.format(diff) : 'Nuevo');
      else {
        var pct = (diff / Math.abs(p)) * 100;
        txt = (pct > 0 ? '+' : '') + (Math.abs(pct) >= 100 ? nf0.format(pct) : trim(pct)) + '%';
      }
      span.appendChild(document.createTextNode(txt + ' '));
      span.appendChild(h('small', '', 'vs mes anterior'));
      if (diff !== 0 && upGood !== 'neutral') {
        var good = (diff > 0) === (upGood === '1');
        span.classList.add(good ? 'is-good' : 'is-bad');
      }
      span.title = 'Mes anterior: ' + (isCount ? nf0.format(p) : money(p));
      n.appendChild(span);
    });
  }

  // ---------- Contador animado del hero ----------
  function countUp() {
    var n = document.querySelector('[data-countup]');
    if (!n || reduceMotion) return;
    var target = parseFloat(n.dataset.countup);
    if (!isFinite(target) || target === 0) return;
    var t0 = null, dur = 900;
    function frame(ts) {
      if (!t0) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur);
      var e = 1 - Math.pow(1 - k, 3);
      n.textContent = money(target * e);
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // ---------- Tablas alternativas ----------
  function buildTable(id, headers, rows, foot) {
    var wrap = document.getElementById(id);
    if (!wrap) return;
    wrap.textContent = '';
    var t = h('table'), thead = h('thead'), tr = h('tr');
    headers.forEach(function (x) { tr.appendChild(h('th', '', x)); });
    thead.appendChild(tr); t.appendChild(thead);
    var tb = h('tbody');
    rows.forEach(function (r) {
      var row = h('tr');
      r.forEach(function (c) { row.appendChild(h('td', '', c)); });
      tb.appendChild(row);
    });
    t.appendChild(tb);
    if (foot) {
      var tf = h('tfoot'), fr = h('tr');
      foot.forEach(function (c) { fr.appendChild(h('td', '', c)); });
      tf.appendChild(fr); t.appendChild(tf);
    }
    wrap.appendChild(t);
  }
  function sum(key) { return D.serie.reduce(function (a, p) { return a + p[key]; }, 0); }

  document.querySelectorAll('[data-table-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var tbl = document.getElementById(btn.dataset.tableToggle);
      var body = tbl.previousElementSibling;
      var on = tbl.hidden;
      tbl.hidden = !on;
      body.hidden = on;
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.querySelector('.ic').textContent = on ? 'bar_chart' : 'table_rows';
      btn.title = on ? 'Ver como gráfico' : 'Ver como tabla';
    });
  });

  // ---------- Render ----------
  var vacio = D.serie.every(function (p) { return p.asientos === 0; });

  function emptyState(container, msg) {
    container.textContent = '';
    var e = h('div', 'viz-empty');
    e.appendChild(h('span', 'ic', 'query_stats'));
    e.appendChild(h('p', '', msg));
    var a = h('a', 'dash-btn-cta sm');
    a.href = '/asientos/nuevo';
    a.appendChild(h('span', 'ic', 'add'));
    a.appendChild(document.createTextNode(' Registrar operación'));
    e.appendChild(a);
    container.appendChild(e);
  }

  var cVC = document.getElementById('chartVentasCompras');
  var cMG = document.getElementById('chartMargen');

  function renderAll() {
    if (vacio) {
      emptyState(cVC, 'Aún no hay movimientos en ' + D.year + '.');
      emptyState(cMG, 'El resultado mensual aparecerá cuando registres ventas o compras.');
    } else {
      renderColumns(cVC, D.serie, [
        { key: 'ventas', name: 'Ventas', color: '--s-ventas' },
        { key: 'compras', name: 'Compras', color: '--s-compras' },
      ]);
      renderLine(cMG, D.serie, 'margen', '--s-margen', 'Resultado');
    }
  }

  renderAll();
  noAnim = true;
  renderHBars(document.getElementById('chartClientes'), D.clientes, '--s-ventas', 'Sin ventas con RUC registradas en ' + D.year + '.');
  renderHBars(document.getElementById('chartProveedores'), D.proveedores, '--s-compras', 'Sin compras con RUC registradas en ' + D.year + '.');
  renderHBars(document.getElementById('chartGastos'), D.gastos, '--s-asientos', 'Sin gastos registrados en ' + D.year + '.', 'codigo');

  var sparkCfg = { ventas: '--s-ventas', compras: '--s-compras', igv: '--s-margen', asientos: '--s-asientos' };
  document.querySelectorAll('[data-spark]').forEach(function (svg) {
    var k = svg.dataset.spark;
    renderSpark(svg, D.serie.map(function (p) { return k === 'asientos' ? p.asientos : p[k]; }), sparkCfg[k]);
  });

  buildTable('tbl-vc', ['Mes', 'Ventas', 'Compras', 'Resultado', 'Asientos'],
    D.serie.map(function (p) { return [p.label, nf2.format(p.ventas), nf2.format(p.compras), nf2.format(p.margen), String(p.asientos)]; }),
    ['Total', nf2.format(sum('ventas')), nf2.format(sum('compras')), nf2.format(sum('margen')), String(sum('asientos'))]);
  buildTable('tbl-mg', ['Mes', 'Resultado', 'IGV neto'],
    D.serie.map(function (p) { return [p.label, nf2.format(p.margen), nf2.format(p.igv)]; }),
    ['Total', nf2.format(sum('margen')), nf2.format(sum('igv'))]);

  renderDeltas();
  countUp();

  // Re-render al cambiar tamano
  var lastW = cVC.clientWidth;
  var rt;
  window.addEventListener('resize', function () {
    clearTimeout(rt);
    rt = setTimeout(function () {
      if (Math.abs(cVC.clientWidth - lastW) > 4) { lastW = cVC.clientWidth; renderAll(); }
    }, 120);
  });
})();
