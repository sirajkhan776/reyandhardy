// AJAX enhancements for Orders page: filter/sort/search and inline status update without page reload
(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

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
    }
  }

  function hookRowStatus(){
    // Reattach after refresh
    $$('form.order-status-form select[name="status"]').forEach(function(sel){
      sel.addEventListener('change', async function(){
        const form = sel.closest('form');
        if (!form) return;
        try {
          await fetch(form.action, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': getCookie('csrftoken'),
            },
            body: new URLSearchParams(new FormData(form)),
            credentials: 'same-origin',
          });
        } catch (e) {}
        refreshList();
      });
    });
  }

  // initial hooks
  hookFilters();
  hookRowStatus();
})();

