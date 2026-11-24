// Desplegable personalizado (redondeado) para TODOS los <select> del sistema.
// - El <select> real sigue existiendo (oculto): formularios, onchange y .value funcionan igual.
// - Se sincroniza solo si el codigo cambia .value / .selectedIndex, las opciones o "disabled".
// - Excluir un select: atributo data-native, multiple o size > 1.
(function () {
  'use strict';

  var BUSCAR_DESDE = 12;   // con mas opciones se muestra un cuadro de busqueda
  var abierto = null;      // instancia abierta (solo una a la vez)

  function norm(t) {
    return (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  function aplicable(select) {
    return select && select.tagName === 'SELECT' && !select._customInited &&
      !select.multiple && !(select.size > 1) && !select.hasAttribute('data-native');
  }

  // Hace que asignar .value / .selectedIndex por codigo refresque el boton.
  function engancharPropiedades(select, onChange) {
    ['value', 'selectedIndex'].forEach(function (prop) {
      var desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, prop);
      if (!desc || !desc.set) return;
      Object.defineProperty(select, prop, {
        configurable: true,
        get: function () { return desc.get.call(this); },
        set: function (v) { desc.set.call(this, v); onChange(); }
      });
    });
  }

  function initCustomSelect(select) {
    if (!aplicable(select)) return;
    select._customInited = true;

    // Medir antes de ocultar para conservar el ancho del layout original.
    var rect = select.getBoundingClientRect();
    var padre = select.parentElement;
    var anchoPadre = padre ? padre.clientWidth : 0;

    var wrap = document.createElement('div');
    wrap.className = 'custom-select';
    if (select.closest('.dash-filters, .on-dark')) wrap.classList.add('on-dark');
    if (rect.width > 0 && anchoPadre > 0 && rect.width < anchoPadre - 4) {
      wrap.style.width = 'auto';
      wrap.style.minWidth = Math.round(rect.width) + 'px';
    }

    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'custom-select-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    if (select.id) trigger.id = select.id + '__btn';
    var etiqueta = select.id && document.querySelector('label[for="' + select.id + '"]');
    if (etiqueta) {
      trigger.setAttribute('aria-label', etiqueta.textContent.trim());
      etiqueta.addEventListener('click', function (e) { e.preventDefault(); trigger.focus(); });
    }

    var list = document.createElement('div');
    list.className = 'custom-select-list';
    list.setAttribute('role', 'listbox');
    list.hidden = true;

    wrap.appendChild(trigger);
    select.parentNode.insertBefore(wrap, select.nextSibling);
    document.body.appendChild(list);     // flotante: no lo recortan tarjetas ni tablas
    if (wrap.classList.contains('on-dark')) list.classList.add('on-dark');
    select.style.display = 'none';

    var filtro = '';
    var resaltado = -1;

    function opcionesVisibles() { return Array.prototype.slice.call(list.querySelectorAll('.custom-select-opt')); }

    function pintarBoton() {
      var sel = select.options[select.selectedIndex];
      trigger.textContent = sel ? sel.textContent : '';
      trigger.disabled = select.disabled;
      wrap.classList.toggle('disabled', select.disabled);
    }

    function crearOpt(opt) {
      var el = document.createElement('div');
      el.className = 'custom-select-opt' + (opt.value === select.value && opt.selected ? ' active' : '') +
                     (opt.disabled ? ' disabled' : '');
      el.setAttribute('role', 'option');
      el.textContent = opt.textContent;
      el.addEventListener('mousedown', function (e) { e.preventDefault(); });
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        if (opt.disabled) return;
        elegir(opt);
      });
      return el;
    }

    function elegir(opt) {
      var cambio = !opt.selected;
      opt.selected = true;
      pintarBoton();
      cerrar();
      trigger.focus();
      if (cambio) {
        select.dispatchEvent(new Event('input', { bubbles: true }));
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }

    function pintarLista() {
      list.innerHTML = '';
      var buscador = null;
      if (select.options.length > BUSCAR_DESDE) {
        buscador = document.createElement('input');
        buscador.type = 'text';
        buscador.className = 'custom-select-search';
        buscador.placeholder = 'Buscar...';
        buscador.value = filtro;
        buscador.addEventListener('input', function () { filtro = buscador.value; pintarOpciones(); });
        buscador.addEventListener('keydown', teclasLista);
        list.appendChild(buscador);
      }
      var cont = document.createElement('div');
      cont.className = 'custom-select-opts';
      list.appendChild(cont);

      function pintarOpciones() {
        cont.innerHTML = '';
        var f = norm(filtro.trim()), hay = 0;
        Array.prototype.forEach.call(select.children, function (node) {
          if (node.tagName === 'OPTGROUP') {
            var hijos = Array.prototype.filter.call(node.children, function (o) {
              return !f || norm(o.textContent + ' ' + node.label).indexOf(f) >= 0;
            });
            if (!hijos.length) return;
            var h = document.createElement('div');
            h.className = 'custom-select-group';
            h.textContent = node.label;
            cont.appendChild(h);
            hijos.forEach(function (o) { var el = crearOpt(o); el._opt = o; cont.appendChild(el); hay++; });
          } else if (node.tagName === 'OPTION') {
            if (f && norm(node.textContent).indexOf(f) < 0) return;
            var el = crearOpt(node); el._opt = node; cont.appendChild(el); hay++;
          }
        });
        if (!hay) {
          var v = document.createElement('div');
          v.className = 'custom-select-empty';
          v.textContent = 'Sin coincidencias';
          cont.appendChild(v);
        }
        var opts = opcionesVisibles();
        resaltado = opts.findIndex(function (o) { return o.classList.contains('active'); });
        if (f && opts.length) resaltar(0);
      }
      pintarOpciones();
      return buscador;
    }

    function resaltar(i) {
      var opts = opcionesVisibles();
      if (!opts.length) return;
      resaltado = Math.max(0, Math.min(i, opts.length - 1));
      opts.forEach(function (o, j) { o.classList.toggle('focus', j === resaltado); });
      opts[resaltado].scrollIntoView({ block: 'nearest' });
    }

    function posicionar() {
      var r = wrap.getBoundingClientRect();
      var alto = Math.min(list.scrollHeight, 320);
      var abajo = window.innerHeight - r.bottom;
      var arriba = r.top;
      list.style.minWidth = r.width + 'px';
      list.style.left = Math.max(8, Math.min(r.left, window.innerWidth - Math.max(r.width, list.offsetWidth) - 8)) + 'px';
      if (abajo < alto + 12 && arriba > abajo) {
        list.style.top = '';
        list.style.bottom = (window.innerHeight - r.top + 6) + 'px';
        list.classList.add('arriba');
      } else {
        list.style.bottom = '';
        list.style.top = (r.bottom + 6) + 'px';
        list.classList.remove('arriba');
      }
    }

    function abrir() {
      if (select.disabled) return;
      if (abierto && abierto !== api) abierto.cerrar();
      if (!list.parentNode) document.body.appendChild(list);
      filtro = '';
      var buscador = pintarLista();
      list.hidden = false;
      wrap.classList.add('open');
      trigger.setAttribute('aria-expanded', 'true');
      posicionar();
      abierto = api;
      if (buscador) setTimeout(function () { buscador.focus(); }, 0);
      var act = list.querySelector('.custom-select-opt.active');
      if (act) act.scrollIntoView({ block: 'nearest' });
    }
    function cerrar() {
      if (list.hidden) return;
      list.hidden = true;
      wrap.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
      if (abierto === api) abierto = null;
    }

    function teclasLista(e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); resaltar(resaltado + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); resaltar(resaltado - 1); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var o = opcionesVisibles()[resaltado < 0 ? 0 : resaltado];
        if (o && o._opt && !o._opt.disabled) elegir(o._opt);
      } else if (e.key === 'Escape') { e.preventDefault(); cerrar(); trigger.focus(); }
      else if (e.key === 'Tab') { cerrar(); }
    }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (list.hidden) abrir(); else cerrar();
    });
    trigger.addEventListener('keydown', function (e) {
      if (list.hidden) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault(); abrir();
        }
      } else {
        teclasLista(e);
      }
    });

    var api = { cerrar: cerrar, posicionar: posicionar, wrap: wrap, list: list };

    engancharPropiedades(select, pintarBoton);
    select.addEventListener('change', pintarBoton);
    new MutationObserver(function () {
      pintarBoton();
      if (!list.hidden) pintarLista();
    }).observe(select, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled'] });
    // Si el select sale del DOM (filas borradas, modal cerrado), retirar la lista flotante.
    select._customApi = api;

    pintarBoton();
  }

  // Cerrar al hacer clic fuera, reubicar al hacer scroll/resize.
  document.addEventListener('click', function (e) {
    if (abierto && !abierto.wrap.contains(e.target) && !abierto.list.contains(e.target)) abierto.cerrar();
  });
  window.addEventListener('resize', function () { if (abierto) abierto.cerrar(); });
  window.addEventListener('scroll', function (e) {
    if (!abierto) return;
    if (abierto.list.contains(e.target)) return;
    if (!document.body.contains(abierto.wrap)) { abierto.cerrar(); return; }
    abierto.posicionar();
  }, true);

  function initAll(root) {
    (root || document).querySelectorAll('select').forEach(initCustomSelect);
  }

  // Selects agregados despues (filas nuevas, modales de plantillas...).
  function observarNuevos() {
    var pendiente = false;
    new MutationObserver(function (muts) {
      var hay = false;
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (n) {
          if (n.nodeType === 1 && (n.tagName === 'SELECT' || n.querySelector && n.querySelector('select'))) hay = true;
        });
        m.removedNodes.forEach(function (n) {
          if (n.nodeType !== 1) return;
          var sels = n.tagName === 'SELECT' ? [n] : (n.querySelectorAll ? n.querySelectorAll('select') : []);
          Array.prototype.forEach.call(sels, function (s) {
            if (s._customApi) { s._customApi.cerrar(); if (s._customApi.list.parentNode) s._customApi.list.remove(); }
          });
        });
      });
      if (hay && !pendiente) {
        pendiente = true;
        requestAnimationFrame(function () { pendiente = false; initAll(); });
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  window.polishInitAll = function () { initAll(); };
  window.initCustomSelectForElement = initCustomSelect;

  function arrancar() { initAll(); observarNuevos(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
