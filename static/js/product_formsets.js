// Generic helper to add new inline formset rows on the product form
(function(){
  function addRow(prefix){
    const totalEl = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const container = document.getElementById(`${prefix}Container`);
    const template = document.getElementById(`template-${prefix}`);
    if (!totalEl || !container || !template) return;
    const idx = parseInt(totalEl.value, 10);
    const html = template.innerHTML.replace(/__prefix__/g, String(idx));
    const tmp = document.createElement('div');
    tmp.innerHTML = html.trim();
    const row = tmp.firstElementChild;
    // Ensure mobile file pickers have accept attributes
    row.querySelectorAll('input[type="file"]').forEach(inp => {
      if (prefix === 'images' && !inp.accept) inp.accept = 'image/*';
      if (prefix === 'videos' && !inp.accept) inp.accept = 'video/*';
    });
    container.appendChild(row);
    totalEl.value = String(idx + 1);
  }

  document.addEventListener('click', function(e){
    const btn = e.target.closest('.add-formset');
    if (!btn) return;
    const prefix = btn.getAttribute('data-formset');
    if (prefix) addRow(prefix);
  });

  // Remove row: check DELETE if present; otherwise clear inputs and hide row
  document.addEventListener('click', function(e){
    const rm = e.target.closest('.remove-formset');
    if (!rm) return;
    const row = rm.closest('.formset-item');
    if (!row) return;
    const prefix = row.getAttribute('data-prefix');
    const index = row.getAttribute('data-index');
    const delName = `${prefix}-${index}-DELETE`;
    const delInput = row.querySelector(`input[name="${delName}"]`);
    if (delInput){
      delInput.checked = true;
    } else {
      // Clear inputs so Django treats it as empty
      row.querySelectorAll('input, select, textarea').forEach(inp => {
        if (inp.type === 'file'){
          try { inp.value = ''; } catch(_) {
            const clone = inp.cloneNode(true); inp.parentNode.replaceChild(clone, inp);
          }
        } else if (inp.tagName === 'SELECT') {
          inp.selectedIndex = 0;
        } else if (inp.type === 'checkbox' || inp.type === 'radio') {
          inp.checked = false;
        } else {
          inp.value = '';
        }
      });
    }
    row.classList.add('d-none');
  });
})();
