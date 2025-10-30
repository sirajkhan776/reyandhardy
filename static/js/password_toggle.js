(function(){
  function toggle(btn){
    const targetId = btn.getAttribute('data-target');
    let input = targetId ? document.getElementById(targetId) : null;
    if (!input){
      const group = btn.closest('.input-group');
      if (group) input = group.querySelector('input[type="password"], input[type="text"]');
    }
    if (!input) return;
    if (input.type === 'password'){
      input.type = 'text';
      const icon = btn.querySelector('i'); if (icon){ icon.classList.remove('bi-eye'); icon.classList.add('bi-eye-slash'); }
      btn.setAttribute('aria-label','Hide password');
    } else {
      input.type = 'password';
      const icon = btn.querySelector('i'); if (icon){ icon.classList.remove('bi-eye-slash'); icon.classList.add('bi-eye'); }
      btn.setAttribute('aria-label','Show password');
    }
  }
  document.addEventListener('click', function(ev){
    const btn = ev.target.closest('.toggle-password');
    if (!btn) return;
    ev.preventDefault();
    ev.stopPropagation();
    toggle(btn);
  });
})();
