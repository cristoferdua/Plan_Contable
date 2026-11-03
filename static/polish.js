// Convierte selects con atributo [data-custom] en dropdowns personalizados
(function () {
  'use strict';

  function initCustomSelect(select) {
    if (select._customInited) return;
    select._customInited = true;
    select.style.display = 'none';

    var wrap = document.createElement('div');
    wrap.className = 'custom-select';
    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'custom-select-trigger';
    var list = document.createElement('div');
    list.className = 'custom-select-list';
    list.hidden = true;
    wrap.appendChild(trigger);
    wrap.appendChild(list);
    select.parentNode.insertBefore(wrap, select.nextSibling);

    function render() {
      var opts = Array.prototype.slice.call(select.options);
      var selected = select.options[select.selectedIndex];
      trigger.textContent = selected ? selected.textContent : '';
      list.innerHTML = '';
      opts.forEach(function (opt) {
        var el = document.createElement('div');
        el.className = 'custom-select-opt' + (opt.value === select.value ? ' active' : '');
        el.textContent = opt.textContent;
        el.dataset.value = opt.value;
        el.addEventListener('click', function (e) {
          e.stopPropagation();
          select.value = opt.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
          select.dispatchEvent(new Event('input', { bubbles: true }));
          close();
          render();
        });
        list.appendChild(el);
      });
    }

    function open() {
      // Cerrar otros
      document.querySelectorAll('.custom-select.open').forEach(function (w) {
        if (w !== wrap) {
          w.classList.remove('open');
          var l = w.querySelector('.custom-select-list');
          if (l) l.hidden = true;
        }
      });
      render();
      list.hidden = false;
      wrap.classList.add('open');
    }
    function close() {
      list.hidden = true;
      wrap.classList.remove('open');
    }
    function toggle() { if (list.hidden) open(); else close(); }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      toggle();
    });
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
    select.addEventListener('change', render);

    render();
  }

  function initAll() {
    document.querySelectorAll('select[data-custom]').forEach(initCustomSelect);
  }

  window.polishInitAll = initAll;
  window.initCustomSelectForElement = initCustomSelect;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
