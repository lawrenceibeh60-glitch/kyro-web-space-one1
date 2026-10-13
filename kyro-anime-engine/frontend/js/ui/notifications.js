// frontend/js/ui/notifications.js
export function toast(msg, kind = 'info', ms = 2500) {
  const host = document.getElementById('toasts');
  if (!host) return;
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  host.append(el);
  setTimeout(() => el.remove(), ms);
}
