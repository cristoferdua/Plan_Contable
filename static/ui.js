(function () {
  'use strict';

  var UI = {};

  // ====== TOAST ======
  function ensureToastContainer() {
    var c = document.getElementById('toast-container');
    if (c) return c;
    c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
    return c;
  }

  var ICONS = {
    success: 'check_circle',
    error: 'error',
    warning: 'warning',
    info: 'info'
  };

  UI.toast = function (opts) {
    if (typeof opts === 'string') opts = { msg: opts };
    opts = opts || {};
    var type = opts.type || 'info';
    var title = opts.title || '';
    var msg = opts.msg || '';
    var duration = opts.duration === undefined ? 3500 : opts.duration;

    var c = ensureToastContainer();
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML =
      '<span class="toast-ic">' + ICONS[type] + '</span>' +
      '<div class="toast-body">' +
        (title ? '<div class="toast-title">' + escapeHtml(title) + '</div>' : '') +
        '<div class="toast-msg">' + escapeHtml(msg) + '</div>' +
      '</div>' +
      '<button class="toast-close" aria-label="Cerrar">&times;</button>';
    c.appendChild(t);

    var removed = false;
    function remove() {
      if (removed) return;
      removed = true;
      t.classList.add('leaving');
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 220);
    }
    t.querySelector('.toast-close').addEventListener('click', remove);
    if (duration > 0) setTimeout(remove, duration);
    return { close: remove };
  };

  UI.success = function (msg, title) { return UI.toast({ type: 'success', msg: msg, title: title }); };
  UI.error = function (msg, title) { return UI.toast({ type: 'error', msg: msg, title: title, duration: 5000 }); };
  UI.warning = function (msg, title) { return UI.toast({ type: 'warning', msg: msg, title: title, duration: 4500 }); };
  UI.info = function (msg, title) { return UI.toast({ type: 'info', msg: msg, title: title }); };

  // ====== CONFIRM ======
  UI.confirm = function (opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var type = opts.type || 'warning';
      var icon = opts.icon || (type === 'danger' ? 'delete' : type === 'warning' ? 'warning' : type === 'success' ? 'check' : 'help');
      var title = opts.title || 'Confirmar';
      var msg = opts.msg || opts.message || '';
      var confirmText = opts.confirmText || 'Confirmar';
      var cancelText = opts.cancelText || 'Cancelar';
      var confirmClass = opts.confirmClass || (type === 'danger' ? 'danger' : 'primary');

      var backdrop = document.createElement('div');
      backdrop.className = 'ui-modal-backdrop';
      backdrop.innerHTML =
        '<div class="ui-modal ' + type + '" role="dialog" aria-modal="true">' +
          '<div class="ui-modal-icon">' + icon + '</div>' +
          '<h3>' + escapeHtml(title) + '</h3>' +
          '<p>' + escapeHtml(msg) + '</p>' +
          '<div class="ui-modal-actions">' +
            '<button type="button" class="ui-cancel">' + escapeHtml(cancelText) + '</button>' +
            '<button type="button" class="' + confirmClass + ' ui-ok">' + escapeHtml(confirmText) + '</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(backdrop);

      function close(result) {
        backdrop.classList.add('leaving');
        setTimeout(function () {
          if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
        }, 180);
        document.removeEventListener('keydown', onKey);
        resolve(result);
      }
      function onKey(e) {
        if (e.key === 'Escape') close(false);
        if (e.key === 'Enter') close(true);
      }
      backdrop.querySelector('.ui-ok').addEventListener('click', function () { close(true); });
      backdrop.querySelector('.ui-cancel').addEventListener('click', function () { close(false); });
      backdrop.addEventListener('click', function (e) { if (e.target === backdrop) close(false); });
      document.addEventListener('keydown', onKey);
      setTimeout(function () { backdrop.querySelector('.ui-ok').focus(); }, 30);
    });
  };

  // ====== PROMPT (texto obligatorio, ej. motivo de anulacion) ======
  // Devuelve el texto ingresado o null si se cancela.
  UI.prompt = function (opts) {
    opts = opts || {};
    var minLen = opts.minLength || 0;
    return new Promise(function (resolve) {
      var type = opts.type || 'warning';
      var backdrop = document.createElement('div');
      backdrop.className = 'ui-modal-backdrop';
      backdrop.innerHTML =
        '<div class="ui-modal ' + type + '" role="dialog" aria-modal="true">' +
          '<div class="ui-modal-icon">' + (opts.icon || 'edit_note') + '</div>' +
          '<h3>' + escapeHtml(opts.title || 'Ingresa un valor') + '</h3>' +
          '<p>' + escapeHtml(opts.msg || '') + '</p>' +
          '<textarea class="ui-prompt-input" rows="3" maxlength="500" placeholder="' + escapeHtml(opts.placeholder || '') + '" ' +
            'style="width:100%;margin:.2rem 0 .3rem;padding:.55rem .65rem;border-radius:8px;border:1px solid #cbd5e1;font:inherit;resize:vertical;"></textarea>' +
          '<div class="ui-prompt-err" style="color:#c0392b;font-size:.78rem;min-height:1em;"></div>' +
          '<div class="ui-modal-actions">' +
            '<button type="button" class="ui-cancel">' + escapeHtml(opts.cancelText || 'Cancelar') + '</button>' +
            '<button type="button" class="' + (type === 'danger' ? 'danger' : 'primary') + ' ui-ok">' + escapeHtml(opts.confirmText || 'Aceptar') + '</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(backdrop);
      var input = backdrop.querySelector('.ui-prompt-input');
      var err = backdrop.querySelector('.ui-prompt-err');
      function close(result) {
        backdrop.classList.add('leaving');
        setTimeout(function () { if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop); }, 180);
        document.removeEventListener('keydown', onKey);
        resolve(result);
      }
      function ok() {
        var v = input.value.trim();
        if (v.length < minLen) { err.textContent = 'Minimo ' + minLen + ' caracteres.'; input.focus(); return; }
        close(v);
      }
      function onKey(e) { if (e.key === 'Escape') close(null); }
      backdrop.querySelector('.ui-ok').addEventListener('click', ok);
      backdrop.querySelector('.ui-cancel').addEventListener('click', function () { close(null); });
      document.addEventListener('keydown', onKey);
      setTimeout(function () { input.focus(); }, 30);
    });
  };

  // ====== DRAFT (localStorage) ======
  UI.draft = {
    save: function (key, data) {
      try {
        localStorage.setItem('draft:' + key, JSON.stringify({
          data: data,
          savedAt: Date.now()
        }));
      } catch (e) {}
    },
    load: function (key) {
      try {
        var raw = localStorage.getItem('draft:' + key);
        if (!raw) return null;
        return JSON.parse(raw);
      } catch (e) { return null; }
    },
    clear: function (key) {
      try { localStorage.removeItem('draft:' + key); } catch (e) {}
    },
    exists: function (key) {
      try { return !!localStorage.getItem('draft:' + key); } catch (e) { return false; }
    }
  };

  // ====== Indicator "Guardado" ======
  var _indTimer = null;
  var _indEl = null;
  UI.showSavedIndicator = function (text) {
    if (_indEl) {
      try { _indEl.parentNode.removeChild(_indEl); } catch (e) {}
    }
    if (_indTimer) clearTimeout(_indTimer);
    _indEl = document.createElement('div');
    _indEl.className = 'draft-saved-ind';
    _indEl.innerHTML = '<span class="ic">cloud_done</span>' + escapeHtml(text || 'Borrador guardado');
    document.body.appendChild(_indEl);
    _indTimer = setTimeout(function () {
      if (_indEl) _indEl.classList.add('hiding');
      setTimeout(function () {
        if (_indEl && _indEl.parentNode) _indEl.parentNode.removeChild(_indEl);
        _indEl = null;
      }, 400);
    }, 1800);
  };

  // ====== THEME (dark/light) ======
  UI.theme = {
    get: function () {
      return document.documentElement.getAttribute('data-theme') || 'light';
    },
    set: function (t) {
      document.documentElement.setAttribute('data-theme', t);
      try { localStorage.setItem('theme', t); } catch (e) {}
      UI.theme._updateToggles();
    },
    toggle: function () {
      UI.theme.set(UI.theme.get() === 'dark' ? 'light' : 'dark');
    },
    _updateToggles: function () {
      var t = UI.theme.get();
      document.querySelectorAll('.theme-toggle').forEach(function (btn) {
        btn.textContent = t === 'dark' ? 'light_mode' : 'dark_mode';
        btn.title = t === 'dark' ? 'Modo claro' : 'Modo oscuro';
      });
    }
  };

  // Aplicar tema guardado antes de que se vea nada
  try {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  } catch (e) {}

  // Inicializar botones toggle al cargar
  function initThemeToggles() {
    UI.theme._updateToggles();
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      if (btn._themeInited) return;
      btn._themeInited = true;
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        UI.theme.toggle();
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeToggles);
  } else {
    initThemeToggles();
  }

  // ====== LOADING helpers ======
  UI.loading = {
    show: function () {
      if (document.getElementById('page-loading')) return;
      var el = document.createElement('div');
      el.id = 'page-loading';
      el.className = 'page-loading';
      el.innerHTML = '<div class="spinner"></div>';
      document.body.appendChild(el);
    },
    hide: function () {
      var el = document.getElementById('page-loading');
      if (el) el.remove();
    },
    btn: function (btn, on) {
      if (!btn) return;
      if (on) btn.classList.add('loading');
      else btn.classList.remove('loading');
    }
  };

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  window.UI = UI;
})();
