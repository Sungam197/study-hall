// Dark mode — initialize before paint (also called early from <head> inline script)
(function () {
  var stored = localStorage.getItem('studyhall-theme');
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  if ((stored === 'dark') || (!stored && prefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();

// Inject theme toggle button once DOM is ready
function _injectThemeToggle() {
  if (document.getElementById('themeToggle')) return;
  var btn = document.createElement('button');
  btn.id = 'themeToggle';
  btn.className = 'theme-toggle';
  btn.setAttribute('aria-label', 'Toggle dark mode');
  btn.innerHTML =
    '<svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>' +
    '<svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  btn.addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('studyhall-theme', isDark ? 'light' : 'dark');
  });
  document.body.appendChild(btn);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _injectThemeToggle);
} else {
  _injectThemeToggle();
}

// Ripple effect on every .btn click
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.btn');
  if (!btn || btn.disabled) return;
  const rect = btn.getBoundingClientRect();
  const d = Math.max(rect.width, rect.height);
  const r = document.createElement('span');
  r.className = 'ripple';
  Object.assign(r.style, {
    width: d + 'px', height: d + 'px',
    left: (e.clientX - rect.left - d / 2) + 'px',
    top:  (e.clientY - rect.top  - d / 2) + 'px',
  });
  btn.appendChild(r);
  r.addEventListener('animationend', () => r.remove());
});

// Stagger-animate a list of elements into view
function staggerIn(selector, delayMs = 90) {
  document.querySelectorAll(selector).forEach((el, i) => {
    el.style.animationDelay = (i * delayMs) + 'ms';
    el.classList.add('visible');
  });
}

// Sidebar toggle
function _initSidebar() {
  var menuBtn      = document.getElementById('menuBtn');
  var overlay      = document.getElementById('sidebarOverlay');
  var closeBtn     = document.getElementById('sidebarClose');

  if (!menuBtn) return;

  function open()  { document.body.classList.add('sidebar-open'); }
  function close() { document.body.classList.remove('sidebar-open'); }

  menuBtn.addEventListener('click', open);
  if (overlay)  overlay.addEventListener('click', close);
  if (closeBtn) closeBtn.addEventListener('click', close);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initSidebar);
} else {
  _initSidebar();
}
