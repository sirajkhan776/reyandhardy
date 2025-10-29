// Generic AJAX list search: used by Products, Categories, Banners, Coupons
(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const debounce = (fn, ms=300) => { let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), ms); }; };

  const container = document.getElementById('listContainer');
  if (!container) return;
  const endpoint = container.getAttribute('data-endpoint');
  if (!endpoint) return;

  const form = container.querySelector('form');
  const tbody = document.getElementById('listTbody');

  async function refresh(){
    if (!form || !tbody) return;
    container.classList.add('loading');
    const params = new URLSearchParams(new FormData(form)).toString();
    const url = `${endpoint}${params ? ('?' + params) : ''}`;
    const resp = await fetch(url, {credentials: 'same-origin'});
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.rows_html) tbody.innerHTML = data.rows_html;
    container.classList.remove('loading');
  }

  if (form){
    form.addEventListener('submit', function(ev){ ev.preventDefault(); refresh(); });
    const q = form.elements['q'];
    if (q){ q.addEventListener('input', debounce(()=>refresh(), 250)); }
    // Auto-refresh when selects change (filters)
    form.querySelectorAll('select').forEach(sel => sel.addEventListener('change', refresh));
  }
})();
