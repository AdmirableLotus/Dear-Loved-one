// Minimal UX helpers for Dear Loved One
document.addEventListener('DOMContentLoaded', () => {
  // 1) Set a sensible default/min for the "send_at" field (+5 minutes from now)
  const sendAt = document.querySelector('input[name="send_at"]');
  if (sendAt) {
    const pad = n => String(n).padStart(2, '0');
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5, 0, 0);
    const local = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
    sendAt.min = local;
    if (!sendAt.value) sendAt.value = local;
  }

  // 2) Confirm before deleting a scheduled/sent message
  document.querySelectorAll('form[action*="/delete"]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm('Delete this message?')) e.preventDefault();
    });
  });

  // 3) Auto-dismiss flash messages after a few seconds
  setTimeout(() => {
    document.querySelectorAll('article.card').forEach(el => {
      if (el.classList.contains('ok') || el.classList.contains('error')) {
        el.style.transition = 'opacity .4s ease';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 400);
      }
    });
  }, 4000);
});
   