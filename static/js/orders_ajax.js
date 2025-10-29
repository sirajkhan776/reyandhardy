// AJAX enhancements for Orders page: filter/sort/search and inline status update without page reload
(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));
  const debounce = (fn, ms=300) => { let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), ms); }; };

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function params(){
    const status = $('#statusFilter') ? $('#statusFilter').value : 'all';
    const sort = $('#sortSelect') ? $('#sortSelect').value : 'newest';
    const q = (document.querySelector('form[action=""]').elements['q'] || {value:''}).value || '';
    const usp = new URLSearchParams();
    if (status && status !== 'all') usp.set('status', status);
    if (sort && sort !== 'newest') usp.set('sort', sort);
    if (q) usp.set('q', q);
    return usp.toString();
  }

  async function refreshList(){
    const query = params();
    const url = `/dashboard/orders/partial/${query ? ('?' + query) : ''}`;
    const resp = await fetch(url, {credentials:'same-origin'});
    if (!resp.ok) return;
    const data = await resp.json();
    const tbody = $('#ordersTbody');
    const summary = $('#ordersSummary');
    if (tbody) tbody.innerHTML = data.rows_html;
    if (summary) summary.innerHTML = data.summary_html;
    hookRowStatus();
  }

  function hookFilters(){
    const filterForm = document.querySelector('form[action=""]');
    if (filterForm){
      filterForm.addEventListener('submit', function(ev){ ev.preventDefault(); refreshList(); });
      const statusFilter = $('#statusFilter', filterForm);
      if (statusFilter){ statusFilter.addEventListener('change', function(){ refreshList(); }); }
      const sortSelect = $('#sortSelect', filterForm);
      if (sortSelect){ sortSelect.addEventListener('change', function(){ refreshList(); }); }
      const qInput = filterForm.elements['q'];
      if (qInput){ qInput.addEventListener('input', debounce(()=>refreshList(), 250)); }
    }
  }

  function hookRowStatus(){
    // Reattach after refresh
    $$('form.order-status-form select[name="status"]').forEach(function(sel){
      sel.addEventListener('change', async function(){
        const form = sel.closest('form');
        if (!form) return;
        try {
          const resp = await fetch(form.action, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCookie('csrftoken'),
            },
            body: new URLSearchParams(new FormData(form)),
            credentials: 'same-origin',
          });
          let msg = 'Updated';
          if (resp && resp.ok){
            const data = await resp.json().catch(()=>({}));
            if (data && data.ok){ msg = `Updated to ${data.status_display || data.status || ''}`.trim(); showChip('success', msg); }
            else { showChip('warning', 'Update may not have applied'); }
          } else {
            showChip('error', 'Failed to update status');
          }
        } catch (e) {}
        refreshList();
      });
    });
  }

  function showChip(kind, text){
    const container = document.getElementById('chip-messages');
    if (!container) return;
    const map = { success: 'chip-success', info: 'chip-info', warning: 'chip-warning', error: 'chip-error', danger: 'chip-danger' };
    const cls = map[kind] || 'chip-info';
    const el = document.createElement('div');
    el.className = `chip-msg ${cls}`;
    el.setAttribute('role','status');
    el.setAttribute('aria-live','polite');
    el.innerHTML = `<span class="chip-dot"></span><span class="chip-text"></span><button class="chip-close" aria-label="Close">&times;</button>`;
    el.querySelector('.chip-text').textContent = text;
    const close = () => { el.remove(); };
    el.querySelector('.chip-close').addEventListener('click', close);
    container.appendChild(el);
    setTimeout(close, 3000);
  }

  // initial hooks
  hookFilters();
  hookRowStatus();
})();
