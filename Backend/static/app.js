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
