// AJAX handlers for user staff/active toggles on Users list
(function(){
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  const container = document.getElementById('listContainer');
  if (!container) return;
  const endpoint = container.getAttribute('data-endpoint');
  const tbody = document.getElementById('listTbody');
  const form = container.querySelector('form');

  async function refresh(){
    if (!endpoint || !tbody) return;
    const params = new URLSearchParams(new FormData(form)).toString();
    const resp = await fetch(`${endpoint}${params ? ('?' + params) : ''}`, {credentials:'same-origin'});
    if (resp.ok){
      const data = await resp.json();
      tbody.innerHTML = data.rows_html;
    }
  }

  document.addEventListener('submit', async function(ev){
    const t = ev.target;
    if (!t.classList.contains('user-toggle-form')) return;
    ev.preventDefault();
    ev.stopPropagation();
    try {
      await fetch(t.action, {
        method: 'POST',
        headers: {'X-Requested-With':'XMLHttpRequest','X-CSRFToken': getCookie('csrftoken')},
        body: new URLSearchParams(new FormData(t)),
        credentials: 'same-origin'
      });
    } catch(e) {}
    refresh();
  });

  // Prevent row click when clicking buttons inside the row
  document.addEventListener('click', function(ev){
    const btn = ev.target.closest('.user-toggle-form button');
    if (btn){ ev.stopPropagation(); }
    // Filter pills
    const pill = ev.target.closest('.filter-pills .nav-link');
    if (pill){ ev.preventDefault();
      const val = pill.getAttribute('data-value');
      const target = pill.closest('.filter-pills').getAttribute('data-target');
      if (target === 'staff'){ form.querySelector('#inputStaff').value = val; }
      if (target === 'active'){ form.querySelector('#inputActive').value = val; }
      // Update active classes
      pill.closest('.filter-pills').querySelectorAll('.nav-link').forEach(a=>a.classList.remove('active'));
      pill.classList.add('active');
      // Submit (list_ajax will intercept)
      form.dispatchEvent(new Event('submit', {cancelable:true}));
    }
    // Clear chips
    const chip = ev.target.closest('.filter-chip');
    if (chip){ const kind = chip.getAttribute('data-clear');
      if (kind === 'staff'){ form.querySelector('#inputStaff').value = 'all'; }
      if (kind === 'active'){ form.querySelector('#inputActive').value = 'all'; }
      if (kind === 'q'){ const q = form.elements['q']; if (q){ q.value=''; } }
      form.dispatchEvent(new Event('submit', {cancelable:true}));
    }
    // Clear search button
    if (ev.target && ev.target.id === 'clearSearch'){
      const q = form.elements['q']; if (q){ q.value=''; }
      form.dispatchEvent(new Event('submit', {cancelable:true}));
    }
  });
})();
